"""Public read-only day archives. This server exposes no collector or SSH controls."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import tarfile
import tempfile
import threading
from contextlib import closing
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from timelinestamp import canonical, iso, utc_now

DAY = re.compile(r"/v1/day/(\d{4}-\d{2}-\d{2})\.tar\.gz")
MAX_UNCOMPRESSED = 512 * 1024 * 1024


class ArchiveUnavailable(ValueError):
    pass


def connect(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=15)
    db.row_factory = sqlite3.Row
    return db


def available_days(path):
    with closing(connect(path)) as db:
        return [dict(row) for row in db.execute("""SELECT d.day,d.digest,d.quality,
            COUNT(o.source) AS observations,MAX(o.received_at) AS last_received
            FROM days d JOIN observations o ON o.event_time>=d.day || 'T00:00:00Z'
            AND o.event_time<date(d.day,'+1 day') || 'T00:00:00Z'
            GROUP BY d.day ORDER BY d.day DESC""")]


def build_archive(path, day, cache_dir, max_cache_bytes=256 * 1024 * 1024):
    if date.fromisoformat(day).isoformat() != day:
        raise ArchiveUnavailable("Invalid UTC date")
    begin = day + "T00:00:00Z"
    end = (date.fromisoformat(day) + timedelta(days=1)).isoformat() + "T00:00:00Z"
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        db.execute("BEGIN")  # manifest and observations come from one SQLite snapshot
        row = db.execute("SELECT * FROM days WHERE day=?", (day,)).fetchone()
        if row is None:
            raise ArchiveUnavailable("No local sealed record/raw data for this date")
        manifest = json.loads(row["manifest"])
        if hashlib.sha256(canonical(manifest)).hexdigest() != row["digest"]:
            raise ArchiveUnavailable("Stored manifest failed its digest check")
        summary = db.execute("""SELECT COUNT(*) AS n,MAX(received_at) AS last FROM observations
            WHERE event_time>=? AND event_time<?""", (begin, end)).fetchone()
        if not summary["n"]:
            raise ArchiveUnavailable("Raw observations are unavailable for this date")
        # Additional shadow observations can arrive after the daily coefficient is sealed.
        revision = hashlib.sha256(canonical([row["digest"], summary["n"], summary["last"]])).hexdigest()
        target = cache_dir / f"{day}-{revision}.tar.gz"
        if target.exists():
            return target
        if shutil.disk_usage(cache_dir).free < MAX_UNCOMPRESSED + 32 * 1024 * 1024:
            raise ArchiveUnavailable("Insufficient free space to build an archive")
        with tempfile.TemporaryDirectory(prefix=".build-", dir=cache_dir) as temp:
            temp = Path(temp)
            observations = temp / "observations.jsonl"
            size = 0
            with observations.open("wb") as stream:
                for observation in db.execute("""SELECT source,event_time,slot_time,received_at,payload,raw,response_sha256
                    FROM observations WHERE event_time>=? AND event_time<? ORDER BY source,event_time""", (begin, end)):
                    value = dict(observation)
                    value["payload"] = json.loads(value["payload"])
                    value["raw"] = json.loads(value["raw"])
                    data = canonical(value) + b"\n"
                    size += len(data)
                    if size > MAX_UNCOMPRESSED:
                        raise ArchiveUnavailable("Day exceeds the current archive size limit")
                    stream.write(data)
            record = {key: row[key] for key in ("day", "created_at", "digest", "coefficient", "quality")}
            record["counts"] = json.loads(row["counts"])
            metadata = {"format": "timelinestamp-raw-archive-v1", "day_utc": day,
                        "captured_at": iso(utc_now()), "observations": summary["n"],
                        "last_received_at": summary["last"], "revision": revision,
                        "daily_sha256": row["digest"],
                        "notes": "manifest.json is the fixed input of the published daily hash. observations.jsonl includes stored observations, including shadow inputs not used in that hash. Late shadow inputs may appear in a newer archive revision. Stored raw fields are source entries or normalized payloads, not necessarily full HTTP responses. Request URLs and server configuration are omitted."}
            working = temp / "archive.tar.gz"
            with working.open("wb") as output, gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0) as zipped:
                with tarfile.open(fileobj=zipped, mode="w|") as tar:
                    for name, value in (("archive.json", metadata), ("record.json", record), ("manifest.json", manifest)):
                        content = canonical(value) + b"\n"
                        info = tarfile.TarInfo(name)
                        info.size = len(content)
                        info.mode = 0o644
                        tar.addfile(info, io.BytesIO(content))
                    info = tarfile.TarInfo("observations.jsonl")
                    info.size = observations.stat().st_size
                    info.mode = 0o644
                    with observations.open("rb") as stream:
                        tar.addfile(info, stream)
            if working.stat().st_size > max_cache_bytes:
                raise ArchiveUnavailable("Archive exceeds the configured cache limit")
            os.replace(working, target)
    total = 0
    for cached in sorted(cache_dir.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True):
        total += cached.stat().st_size
        if total > max_cache_bytes and cached != target:
            cached.unlink(missing_ok=True)
    return target


class ArchiveServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 8

    def __init__(self, address, db_path, cache_dir):
        self.db_path, self.cache_dir = db_path, cache_dir
        self.transfers = threading.BoundedSemaphore(2)
        self.clients = threading.BoundedSemaphore(8)
        self.build_lock = threading.Lock()
        super().__init__(address, ArchiveHandler)

    def process_request(self, request, client_address):
        if not self.clients.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.clients.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.clients.release()


class ArchiveHandler(BaseHTTPRequestHandler):
    server_version = "TimeLineStampArchive/1"
    sys_version = ""

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def send_common_headers(self, code, content_type, size):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")

    def json(self, value, code=200):
        body = canonical(value)
        self.send_common_headers(code, "application/json", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path == "/health":
                return self.json({"format": "timelinestamp-archive-health-v1", "status": "ok"})
            if path == "/v1/catalog":
                return self.json({"format": "timelinestamp-archive-catalog-v1", "days": available_days(self.server.db_path)})
            match = DAY.fullmatch(path)
            if not match:
                return self.json({"error": "not_found"}, 404)
            if not self.server.transfers.acquire(blocking=False):
                return self.json({"error": "busy", "retry_after_seconds": 30}, 429)
            try:
                with self.server.build_lock:
                    archive = build_archive(self.server.db_path, match[1], self.server.cache_dir)
                    stream = archive.open("rb")
                # Keep a descriptor open while streaming; cache cleanup may unlink old files.
                with stream:
                    self.send_common_headers(200, "application/gzip", os.fstat(stream.fileno()).st_size)
                    self.send_header("Content-Disposition", f'attachment; filename="timelinestamp-{match[1]}-{archive.stem[11:23]}.tar.gz"')
                    self.end_headers()
                    shutil.copyfileobj(stream, self.wfile, length=64 * 1024)
            finally:
                self.server.transfers.release()
        except (ArchiveUnavailable, ValueError) as exc:
            self.json({"error": "archive_unavailable", "message": str(exc)}, 404)
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except (sqlite3.Error, OSError):
            self.json({"error": "temporarily_unavailable"}, 503)

    def log_message(self, *_):
        pass  # Do not persist visitor IP addresses.
