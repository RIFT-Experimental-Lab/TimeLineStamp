"""Timelinestamp v1: a daily fingerprint of public physical measurements."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
LOCAL_DATA = ROOT.parent / "local" / "data" if ROOT.name == "repository" and (ROOT.parent / "local").is_dir() else ROOT / "data"
SLOT_SECONDS = 300
BEACON_SOURCES = ("nist", "nqsn")
NOAA_SOURCES = ("noaa_mag", "noaa_wind")
SOURCE_NAMES = {
    "nist": "NIST Beacon",
    "nqsn": "NQSN Beacon",
    "noaa_mag": "NOAA · магнитное поле",
    "noaa_wind": "NOAA · солнечный ветер",
}
NOAA_URLS = {
    "noaa_mag": "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json",
    "noaa_wind": "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json",
}
NOAA_FIELDS = {
    "noaa_mag": ("bt", "bx_gsm", "by_gsm", "bz_gsm"),
    "noaa_wind": ("proton_speed", "proton_density", "proton_temperature"),
}
LOG = logging.getLogger("timelinestamp")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # NOAA labels its UTC measurements without a timezone suffix.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def display_coefficient(digest_hex: str) -> str:
    """Map SHA-256 uniformly into six decimal digits using rejection sampling."""
    limit = (1 << 256) - ((1 << 256) % 1_000_000)
    candidate = bytes.fromhex(digest_hex)
    while int.from_bytes(candidate, "big") >= limit:
        candidate = hashlib.sha256(candidate).digest()
    return "1.%06d" % (int.from_bytes(candidate, "big") % 1_000_000)


def fetch_json(url: str) -> tuple[object, str]:
    request = Request(url, headers={"User-Agent": "Timelinestamp/1.0 (+local research project)", "Accept": "application/json"})
    with urlopen(request, timeout=15) as response:
        body = response.read(5_000_001)
        if len(body) > 5_000_000:
            raise ValueError("Response exceeds 5 MB")
    return json.loads(body), hashlib.sha256(body).hexdigest()


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS observations (
                    source TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    slot_time TEXT,
                    received_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    raw TEXT NOT NULL,
                    response_sha256 TEXT NOT NULL,
                    url TEXT NOT NULL,
                    PRIMARY KEY (source, event_time)
                );
                CREATE INDEX IF NOT EXISTS observations_time ON observations(event_time);
                CREATE TABLE IF NOT EXISTS days (
                    day TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    coefficient TEXT,
                    quality TEXT NOT NULL,
                    counts TEXT NOT NULL,
                    manifest TEXT NOT NULL
                );
            """)
            db.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('started_at',?)", (iso(utc_now()),))

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path), timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=15000")
        return db

    def started_at(self) -> datetime:
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key='started_at'").fetchone()
        return parse_utc(row["value"])

    def first_full_day(self) -> str:
        started = self.started_at()
        return (started.date() + timedelta(days=1)).isoformat()

    def has_observation(self, source: str, event_time: str) -> bool:
        with self.connect() as db:
            return db.execute("SELECT 1 FROM observations WHERE source=? AND event_time=?", (source, event_time)).fetchone() is not None

    def add_observation(self, source: str, event_time: str, slot_time: str | None,
                        payload: object, raw: object, response_sha256: str, url: str) -> None:
        with self.connect() as db:
            db.execute("""INSERT OR IGNORE INTO observations
                (source,event_time,slot_time,received_at,payload,raw,response_sha256,url)
                VALUES(?,?,?,?,?,?,?,?)""",
                (source, event_time, slot_time, iso(utc_now()), canonical(payload).decode(),
                 canonical(raw).decode(), response_sha256, url))

    def day_exists(self, day: str) -> bool:
        with self.connect() as db:
            return db.execute("SELECT 1 FROM days WHERE day=?", (day,)).fetchone() is not None

    def finalize_day(self, day: str) -> dict:
        if self.day_exists(day):
            return self.get_day(day)
        start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        start_s, end_s = iso(start), iso(end)
        with self.connect() as db:
            rows = db.execute("""SELECT source,event_time,slot_time,payload FROM observations
                WHERE event_time>=? AND event_time<? ORDER BY source,event_time""", (start_s, end_s)).fetchall()
        by_source: dict[str, dict[str, object]] = {source: {} for source in SOURCE_NAMES}
        for row in rows:
            key = row["slot_time"] if row["source"] in BEACON_SOURCES else row["event_time"]
            by_source[row["source"]][key] = json.loads(row["payload"])
        manifest: dict = {"format": "timelinestamp-v1", "day_utc": day, "sources": {}}
        counts: dict[str, dict[str, int]] = {}
        for source in BEACON_SOURCES:
            values = []
            for offset in range(0, 86400, SLOT_SECONDS):
                key = iso(start + timedelta(seconds=offset))
                values.append([key, by_source[source].get(key)])
            count = sum(value is not None for _, value in values)
            manifest["sources"][source] = values
            counts[source] = {"received": count, "expected": 288}
        for source in NOAA_SOURCES:
            values = [[key, value] for key, value in sorted(by_source[source].items())]
            manifest["sources"][source] = values
            counts[source] = {"received": len(values), "expected": 1440}
        digest = hashlib.sha256(canonical(manifest)).hexdigest()
        quantum_count = counts["nist"]["received"] + counts["nqsn"]["received"]
        quality = "unavailable" if quantum_count == 0 else "good"
        if 0 < quantum_count and (min(counts[s]["received"] for s in BEACON_SOURCES) < 230 or
                                  min(counts[s]["received"] for s in NOAA_SOURCES) < 1000):
            quality = "partial"
        coefficient = None if quality == "unavailable" else display_coefficient(digest)
        created = iso(utc_now())
        with self.connect() as db:
            db.execute("""INSERT OR IGNORE INTO days(day,created_at,digest,coefficient,quality,counts,manifest)
                VALUES(?,?,?,?,?,?,?)""", (day, created, digest, coefficient, quality,
                                           canonical(counts).decode(), canonical(manifest).decode()))
        LOG.info("Finalized %s: %s (%s)", day, coefficient, quality)
        return self.get_day(day)

    def get_day(self, day: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT day,created_at,digest,coefficient,quality,counts FROM days WHERE day=?", (day,)).fetchone()
        return dict(row) | {"counts": json.loads(row["counts"])} if row else None

    def get_manifest(self, day: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT manifest FROM days WHERE day=?", (day,)).fetchone()
        return json.loads(row["manifest"]) if row else None

    def latest_day(self) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT day FROM days ORDER BY day DESC LIMIT 1").fetchone()
        return self.get_day(row["day"]) if row else None

    def history(self, limit: int = 30) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT day FROM days ORDER BY day DESC LIMIT ?", (limit,)).fetchall()
        return [self.get_day(row["day"]) for row in rows]

    def progress(self) -> dict:
        today = utc_now().date().isoformat()
        with self.connect() as db:
            rows = db.execute("""SELECT source,COUNT(*) AS count,MAX(received_at) AS last_received
                FROM observations WHERE event_time>=? GROUP BY source""", (today + "T00:00:00Z",)).fetchall()
        return {row["source"]: {"count": row["count"], "last_received": row["last_received"]} for row in rows}

    def storage_stats(self) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT COUNT(*) AS count,MIN(event_time) AS oldest,MAX(event_time) AS newest FROM observations").fetchone()
        wal = Path(str(self.path) + "-wal")
        return {"observations": row["count"], "oldest_event": row["oldest"], "newest_event": row["newest"],
                "database_bytes": self.path.stat().st_size + (wal.stat().st_size if wal.exists() else 0),
                "free_bytes": shutil.disk_usage(self.path.parent).free}


def beacon_url(source: str, slot: datetime) -> str:
    if source == "nist":
        return "https://beacon.nist.gov/beacon/2.0/pulse/time/%d" % (int(slot.timestamp()) * 1000)
    if source == "nqsn":
        return "https://quantum-entropy.sg/beacon/2.0/pulse?timeGE=" + quote(iso(slot), safe=":")
    raise ValueError(source)


def beacon_payload(source: str, data: object, slot: datetime) -> tuple[str, dict]:
    if not isinstance(data, dict) or not isinstance(data.get("pulse"), dict):
        raise ValueError("Invalid beacon response")
    pulse = data["pulse"]
    event_time = iso(parse_utc(pulse["timeStamp"]))
    if event_time != iso(slot):
        raise ValueError("Beacon returned a different minute")
    value = pulse["localRandomValue"]
    if not isinstance(value, str) or len(value) != 128 or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise ValueError("Invalid 512-bit beacon value")
    if pulse.get("statusCode") != 0:
        raise ValueError("Beacon status is not normal")
    if not isinstance(pulse.get("pulseIndex"), int) or not isinstance(pulse.get("chainIndex"), int):
        raise ValueError("Missing beacon indices")
    return event_time, {"value": value.lower(), "chain": pulse["chainIndex"], "index": pulse["pulseIndex"]}


def noaa_payload(source: str, row: object) -> tuple[str, dict] | None:
    if not isinstance(row, dict) or row.get("active") is not True or row.get("overall_quality") != 0:
        return None
    event_time = iso(parse_utc(row["time_tag"]))
    values = {field: row.get(field) for field in NOAA_FIELDS[source]}
    if not isinstance(row.get("source"), str) or any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in values.values()):
        return None
    return event_time, {"spacecraft": row["source"], **values}


class Collector:
    def __init__(self, store: Store):
        self.store = store
        self.stop = threading.Event()
        self.last_attempt: dict[tuple[str, str], float] = {}
        self.noaa_next = 0.0

    def collect_beacons(self, now: datetime) -> None:
        # Give providers time to publish, then retry a slot for up to ten minutes.
        if len(self.last_attempt) > 100:
            self.last_attempt = {key: when for key, when in self.last_attempt.items()
                                 if now.timestamp() - when < 3600}
        newest = int((now.timestamp() - 75) // SLOT_SECONDS) * SLOT_SECONDS
        for slot_seconds in (newest - SLOT_SECONDS, newest):
            age = now.timestamp() - slot_seconds
            if not 75 <= age <= 600:
                continue
            slot = datetime.fromtimestamp(slot_seconds, timezone.utc)
            if slot < self.store.started_at() or self.store.day_exists(slot.date().isoformat()):
                continue
            event_time = iso(slot)
            for source in BEACON_SOURCES:
                if self.store.has_observation(source, event_time):
                    continue
                key = (source, event_time)
                if now.timestamp() - self.last_attempt.get(key, 0) < 90:
                    continue
                self.last_attempt[key] = now.timestamp()
                url = beacon_url(source, slot)
                try:
                    data, response_hash = fetch_json(url)
                    actual_time, payload = beacon_payload(source, data, slot)
                    self.store.add_observation(source, actual_time, event_time, payload, data, response_hash, url)
                except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                    LOG.warning("%s %s: %s", source, event_time, exc)

    def collect_noaa(self, now: datetime) -> None:
        if now.timestamp() < self.noaa_next:
            return
        # Always fetch shortly after midnight so the last hour is present
        # before the 00:15 UTC daily lock, regardless of process start time.
        midnight_fetch = now.replace(hour=0, minute=5, second=0, microsecond=0)
        if midnight_fetch <= now:
            midnight_fetch += timedelta(days=1)
        self.noaa_next = min(now.timestamp() + 3600, midnight_fetch.timestamp())
        start = self.store.started_at()
        earliest = max(start, now - timedelta(hours=24))
        for source in NOAA_SOURCES:
            url = NOAA_URLS[source]
            try:
                data, response_hash = fetch_json(url)
                if not isinstance(data, list):
                    raise ValueError("NOAA response is not a list")
                inserted = 0
                for row in data:
                    parsed = noaa_payload(source, row)
                    if parsed is None:
                        continue
                    event_time, payload = parsed
                    when = parse_utc(event_time)
                    if not earliest <= when <= now or self.store.day_exists(when.date().isoformat()):
                        continue
                    self.store.add_observation(source, event_time, None, payload, row, response_hash, url)
                    inserted += 1
                LOG.info("%s: processed %d rows", source, inserted)
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                LOG.warning("%s: %s", source, exc)
                self.noaa_next = min(self.noaa_next, now.timestamp() + 300)

    def finalize_due_days(self, now: datetime) -> None:
        if now.hour == 0 and now.minute < 15:
            return
        last_due = now.date() - timedelta(days=1)
        first = datetime.fromisoformat(self.store.first_full_day()).date()
        while first <= last_due:
            day = first.isoformat()
            if not self.store.day_exists(day):
                self.store.finalize_day(day)
            first += timedelta(days=1)

    def run(self) -> None:
        LOG.info("Collector started; first full day: %s", self.store.first_full_day())
        restart_request = self.store.path.with_suffix(self.store.path.suffix + ".restart")
        while not self.stop.is_set():
            if restart_request.exists():
                restart_request.unlink()
                LOG.info("Collector restart requested")
                return
            now = utc_now()
            try:
                self.collect_beacons(now)
                self.collect_noaa(now)
                self.finalize_due_days(utc_now())
            except Exception:
                LOG.exception("Collector cycle failed")
            self.stop.wait(30)


class Handler(BaseHTTPRequestHandler):
    store: Store

    def send_json(self, data: object, status: int = 200) -> None:
        body = canonical(data)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/status":
            self.send_json({"current": self.store.latest_day(), "history": self.store.history(),
                            "progress": self.store.progress(), "first_full_day": self.store.first_full_day(),
                            "now_utc": iso(utc_now()), "source_names": SOURCE_NAMES})
            return
        if path.startswith("/api/day/"):
            parts = path[len("/api/day/"):].split("/")
            day = parts[0]
            manifest = len(parts) == 2 and parts[1] == "manifest"
            valid_path = len(day) == 10 and (len(parts) == 1 or manifest)
            result = (self.store.get_manifest(day) if manifest else self.store.get_day(day)) if valid_path else None
            self.send_json(result if result else {"error": "Day not found"}, 200 if result else 404)
            return
        asset = {"/": ("index.html", "text/html; charset=utf-8"),
                 "/style.css": ("style.css", "text/css; charset=utf-8"),
                 "/app.js": ("app.js", "text/javascript; charset=utf-8")}.get(path)
        if asset is None:
            self.send_error(404)
            return
        body = (ROOT / "web" / asset[0]).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", asset[1])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        LOG.info("HTTP %s %s", self.address_string(), format % args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Timelinestamp daily physical fingerprint")
    parser.add_argument("--host", default="127.0.0.1", help="Web interface address (default: local only)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", type=Path, default=LOCAL_DATA / "timelinestamp.sqlite3")
    parser.add_argument("--headless", action="store_true", help="Collect without starting the local web server")
    parser.add_argument("--status", action="store_true", help="Print local collection status and exit")
    parser.add_argument("--restart", action="store_true", help="Ask the running collector to restart")
    parser.add_argument("--publish-repo", metavar="OWNER/REPO", help="Publish a small status file to GitHub Pages")
    parser.add_argument("--token-file", type=Path, default=Path.home() / ".config" / "timelinestamp" / "github-token")
    parser.add_argument("--log-file", type=Path, help="Rotating log file for unattended operation")
    parser.add_argument("--backup-dir", type=Path, help="Keep two compressed copies of the complete database")
    args = parser.parse_args()
    handlers = None
    if args.log_file:
        args.log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers = [RotatingFileHandler(args.log_file, maxBytes=2_000_000, backupCount=2, encoding="utf-8")]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)
    store = Store(args.db)
    if args.restart:
        lock_path = args.db.with_suffix(args.db.suffix + ".lock")
        with lock_path.open("w") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                args.db.with_suffix(args.db.suffix + ".restart").touch()
                print("Restart requested; the launcher will restart the collector shortly")
                return
        parser.error("Collector is not running with this database")
    if args.status:
        backups = sorted(args.backup_dir.expanduser().glob("timelinestamp-*.sqlite3.gz")) if args.backup_dir else []
        print(canonical({"now_utc": iso(utc_now()), "first_full_day": store.first_full_day(),
                         "current": store.latest_day(), "progress": store.progress(),
                         "storage": store.storage_stats(),
                         "backups": [{"file": path.name, "bytes": path.stat().st_size} for path in backups]}).decode())
        return
    lock_path = args.db.with_suffix(args.db.suffix + ".lock")
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("Collector already runs with this database")
        run_server_and_collector(args, store)


def run_server_and_collector(args: argparse.Namespace, store: Store) -> None:
    collector = Collector(store)
    publisher = None
    publisher_thread = None
    backup_worker = None
    backup_thread = None
    if args.publish_repo:
        from publish_github import GitHubPublisher
        publisher = GitHubPublisher(store, args.publish_repo, args.token_file)
        publisher_thread = threading.Thread(target=publisher.run, name="publisher", daemon=True)
        publisher_thread.start()
    if args.backup_dir:
        from backup_store import BackupWorker
        backup_worker = BackupWorker(store, args.backup_dir)
        backup_thread = threading.Thread(target=backup_worker.run, name="backup", daemon=True)
        backup_thread.start()
    try:
        if args.headless:
            collector.run()
        else:
            handler = type("TimelinestampHandler", (Handler,), {"store": store})
            thread = threading.Thread(target=collector.run, name="collector", daemon=True)
            thread.start()
            server = ThreadingHTTPServer((args.host, args.port), handler)
            server.timeout = 1
            LOG.info("Open http://%s:%d", args.host, args.port)
            try:
                while thread.is_alive():
                    server.handle_request()
            finally:
                collector.stop.set()
                server.server_close()
                thread.join(timeout=20)
    except KeyboardInterrupt:
        pass
    finally:
        collector.stop.set()
        if publisher is not None:
            publisher.stop.set()
        if backup_worker is not None:
            backup_worker.stop.set()
        if publisher_thread is not None:
            publisher_thread.join(timeout=20)
        if backup_thread is not None:
            backup_thread.join(timeout=20)


if __name__ == "__main__":
    main()
