"""Portable published state, with no observations, credentials, or invented history."""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path
from urllib.request import urlopen, Request


FORMAT = "timelinestamp-recovery-v1"
SCOPES = {"day4h", "week_day", "month_block", "year_month"}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def checkpoint(store):
    from timelinestamp import iso, utc_now
    settings = store.v2_settings()
    with store.connect() as db:
        periods = [dict(row) for row in db.execute("SELECT * FROM period_codes ORDER BY scope,start_utc")]
    return pack({"format": FORMAT, "saved_at": iso(utc_now()), "first_full_day": store.first_full_day(),
                 "days": store.sealed_records(), "periods": periods,
                 "v2": {key: settings[key] for key in ("start_day_utc", "shadow_start_day_utc", "disabled_groups", "disabled_sources")}})


def pack(body):
    return {**body, "sha256": hashlib.sha256(canonical(body)).hexdigest()}


def validate(state):
    from timelinestamp import display_coefficient, iso, parse_utc
    body = {key: value for key, value in state.items() if key != "sha256"}
    if state.get("format") != FORMAT or state.get("sha256") != hashlib.sha256(canonical(body)).hexdigest():
        raise ValueError("Recovery state format/checksum mismatch")
    date.fromisoformat(state["first_full_day"])
    keys = set()
    for row in state["days"]:
        day = date.fromisoformat(row["day"]).isoformat()
        if day in keys or day < state["first_full_day"] or not re.fullmatch("[a-f0-9]{64}", row["digest"]):
            raise ValueError("Invalid or duplicate recovery day")
        keys.add(day)
        parse_utc(row["created_at"])
        if row["quality"] not in {"good", "partial", "unavailable"}:
            raise ValueError("Unknown daily quality")
        expected = None if row["quality"] == "unavailable" else display_coefficient(row["digest"])
        if row["coefficient"] != expected:
            raise ValueError("Daily coefficient does not match its digest")
        if not isinstance(row["counts"], dict):
            raise ValueError("Invalid daily counts")
    keys = set()
    for row in state["periods"]:
        key = row["scope"], row["start_utc"]
        if key in keys or row["scope"] not in SCOPES or not re.fullmatch("[a-f0-9]{64}", row["digest"]):
            raise ValueError("Invalid or duplicate recovery period")
        keys.add(key)
        start, end = parse_utc(row["start_utc"]), parse_utc(row["end_utc"])
        if iso(start) != row["start_utc"] or end <= start or row["quality"] not in {"good", "partial", "unavailable"}:
            raise ValueError("Invalid period boundaries/quality")
        duration = end - start
        if row["scope"] == "day4h" and (duration != timedelta(hours=4) or start.hour % 4 or start.minute or start.second):
            raise ValueError("Invalid four-hour period")
        if row["scope"] == "week_day" and (duration != timedelta(days=1) or start.hour or start.minute or start.second):
            raise ValueError("Invalid daily period")
    return state


def from_git(repo: Path):
    """Read every status revision, including records older than the current 30-day view."""
    revisions = subprocess.check_output(["git", "-C", str(repo), "log", "--reverse", "--format=%H", "--", "docs/data/status.json"], text=True).splitlines()
    days, periods, first, saved, settings = {}, {}, None, None, None
    for revision in revisions:
        snapshot = json.loads(subprocess.check_output(["git", "-C", str(repo), "show", f"{revision}:docs/data/status.json"]))
        if snapshot.get("format") != "timelinestamp-status-v1":
            continue
        first = first or snapshot.get("first_full_day")
        saved = snapshot.get("published_at") or saved
        embedded = snapshot.get("recovery")
        if embedded:
            validate(embedded)
            records = embedded["days"]
            positions = embedded["periods"]
            settings = embedded.get("v2")
        else:
            records = snapshot.get("history", []) + ([snapshot["current"]] if snapshot.get("current") else [])
            positions = []
            for scope, group in (("day4h", "day"), ("week_day", "week"), ("month_block", "month"), ("year_month", "year")):
                for position in (snapshot.get("period_codes", {}).get(group) or {}).get("positions", []):
                    if position.get("sha256"):
                        positions.append({"scope": scope, "start_utc": position["start_utc"], "end_utc": position["end_utc"],
                                          "digest": position["sha256"], "quality": position["quality"], "created_at": saved})
        for row in records:
            if row["day"] in days and days[row["day"]] != row:
                raise ValueError("Conflicting published daily records")
            days[row["day"]] = row
        for row in positions:
            key = row["scope"], row["start_utc"]
            if key in periods and any(periods[key][field] != row[field] for field in ("digest", "end_utc", "quality")):
                raise ValueError("Conflicting published period records")
            periods.setdefault(key, row)
    if not first or not saved:
        raise ValueError("No published history in this Git checkout")
    return validate(pack({"format": FORMAT, "saved_at": saved, "first_full_day": first,
                          "days": sorted(days.values(), key=lambda row: row["day"]),
                          "periods": sorted(periods.values(), key=lambda row: (row["scope"], row["start_utc"])), "v2": settings}))


def restore(state, destination: Path, config: Path | None = None):
    from timelinestamp import Store, canonical
    from period_codes import ensure_period_codes
    validate(state)
    if destination.exists():
        raise ValueError("Destination database already exists; stop the collector and choose a new path")
    store = Store(destination, config)
    with store.connect() as db:
        db.execute("INSERT INTO meta(key,value) VALUES('experiment_first_full_day',?)", (state["first_full_day"],))
        db.executemany("INSERT INTO recovered_days VALUES(?,?,?,?,?,?)", [
            (r["day"], r["created_at"], r["digest"], r["coefficient"], r["quality"], canonical(r["counts"]).decode()) for r in state["days"]])
        db.executemany("INSERT INTO period_codes VALUES(?,?,?,?,?,?)", [
            tuple(r[key] for key in ("scope", "start_utc", "end_utc", "digest", "quality", "created_at")) for r in state["periods"]])
    ensure_period_codes(store)
    return store


def merge_published_history(store, state):
    from period_codes import ensure_period_codes
    validate(state)
    if store.first_full_day() != state["first_full_day"]:
        raise ValueError("Backup belongs to a different collection history")
    for record in state["days"]:
        current = store.get_day(record["day"])
        if current is not None and current != record:
            raise ValueError("Backup conflicts with a published daily record")
    with store.connect() as db:
        for record in state["periods"]:
            current = db.execute("SELECT * FROM period_codes WHERE scope=? AND start_utc=?",
                                 (record["scope"], record["start_utc"])).fetchone()
            if current and any(current[key] != record[key] for key in ("end_utc", "digest", "quality")):
                raise ValueError("Backup conflicts with a published period")
        for record in state["days"]:
            if not store.day_exists(record["day"]):
                db.execute("INSERT INTO recovered_days VALUES(?,?,?,?,?,?)", (
                    record["day"], record["created_at"], record["digest"], record["coefficient"], record["quality"], canonical(record["counts"]).decode()))
        db.executemany("INSERT OR IGNORE INTO period_codes VALUES(?,?,?,?,?,?)", [
            tuple(r[key] for key in ("scope", "start_utc", "end_utc", "digest", "quality", "created_at")) for r in state["periods"]])
    ensure_period_codes(store)


def restore_backup(backup: Path, destination: Path, config: Path | None = None):
    from timelinestamp import Store, iso, utc_now
    if destination.exists():
        raise ValueError("Destination database already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as folder:
        working = Path(folder) / "restore.sqlite3"
        with gzip.open(backup, "rb") as source, working.open("wb") as target:
            shutil.copyfileobj(source, target)
        with sqlite3.connect(working) as db:
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Backup integrity check failed")
        store = Store(working, config)
        original = store.first_full_day()
        with store.connect() as db:
            db.execute("INSERT OR REPLACE INTO meta VALUES('experiment_first_full_day',?)", (original,))
            db.execute("UPDATE meta SET value=? WHERE key='started_at'", (iso(utc_now()),))
        with store.connect() as db:
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        with sqlite3.connect(working) as source, sqlite3.connect(destination) as target:
            source.backup(target)
    return Store(destination, config)


def fetch_state():
    for url in ("https://raw.githubusercontent.com/RIFT-Experimental-Lab/TimeLineStamp/main/docs/data/status.json",
                "https://api.github.com/repos/RIFT-Experimental-Lab/TimeLineStamp/contents/docs/data/status.json"):
        try:
            request = Request(url, headers={"User-Agent": "TimeLineStamp-Recovery/1"})
            with urlopen(request, timeout=30) as response:
                data = response.read(16_000_001)
            if len(data) > 16_000_000:
                raise ValueError("Published state exceeds 16 MB")
            snapshot = json.loads(data)
            if "content" in snapshot:
                snapshot = json.loads(base64.b64decode(snapshot["content"]))
            if snapshot.get("recovery"):
                return validate(snapshot["recovery"])
            break
        except (OSError, ValueError, KeyError):
            continue
    # Older publishers kept the complete history in Git revisions only.
    with tempfile.TemporaryDirectory() as folder:
        repo = Path(folder) / "history"
        subprocess.run(["git", "clone", "--quiet", "https://github.com/RIFT-Experimental-Lab/TimeLineStamp.git", str(repo)], check=True)
        return from_git(repo)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("from-git")
    build.add_argument("--repo", type=Path, default=Path(__file__).parent)
    build.add_argument("--output", type=Path, required=True)
    fetch = sub.add_parser("fetch-state")
    fetch.add_argument("--output", type=Path, required=True)
    load = sub.add_parser("restore")
    source = load.add_mutually_exclusive_group(required=True)
    source.add_argument("--state", type=Path)
    source.add_argument("--backup", type=Path)
    load.add_argument("--db", type=Path, required=True)
    load.add_argument("--v2-config", type=Path)
    load.add_argument("--history", type=Path, help="Merge newer published history after restoring a full backup")
    args = parser.parse_args()
    if args.command in {"from-git", "fetch-state"}:
        state = from_git(args.repo) if args.command == "from-git" else fetch_state()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical(state) + b"\n")
        print(f"Saved {len(state['days'])} daily records and {len(state['periods'])} period digests")
    else:
        store = restore(json.loads(args.state.read_text()), args.db, args.v2_config) if args.state else restore_backup(args.backup, args.db, args.v2_config)
        if args.history:
            merge_published_history(store, json.loads(args.history.read_text()))
        print(f"Restored {len(store.sealed_records())} days; new full-day collection starts {store.collection_first_full_day()} UTC")


if __name__ == "__main__":
    main()
