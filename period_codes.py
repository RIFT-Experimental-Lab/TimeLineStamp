"""Immutable short codes for completed UTC intervals of sealed daily records."""

from __future__ import annotations

import calendar
import hashlib
import json
from datetime import date, datetime, timedelta, timezone


ALPHABETS = {
    "hex": "0123456789ABCDEF",
    "base32": "0123456789ABCDEFGHJKMNPQRSTVWXYZ",
    "base58": "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz",
}
FORMAT = "timelinestamp-period-v1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def short_code(digest: str, alphabet: str, width: int) -> str:
    chars = ALPHABETS[alphabet]
    modulus = len(chars) ** width
    limit = (1 << 256) - (1 << 256) % modulus
    candidate = bytes.fromhex(digest)
    retry = 0
    while int.from_bytes(candidate, "big") >= limit:
        retry += 1
        candidate = hashlib.sha256(bytes.fromhex(digest) + b"period-code-retry-v1" + retry.to_bytes(4, "big")).digest()
    number = int.from_bytes(candidate, "big") % modulus
    result = ""
    for _ in range(width):
        number, remainder = divmod(number, len(chars))
        result = chars[remainder] + result
    return result


def _digest(payload: dict) -> str:
    return hashlib.sha256(canonical(payload)).hexdigest()


def _row(scope: str, start: datetime, end: datetime, digest: str, quality: str) -> tuple:
    return scope, stamp(start), stamp(end), digest, quality, stamp(datetime.now(timezone.utc))


def _day_start(day: str) -> datetime:
    return datetime.fromisoformat(day).replace(tzinfo=timezone.utc)


def _month_end(first: date) -> date:
    return date(first.year, first.month, calendar.monthrange(first.year, first.month)[1])


def _month_blocks(year: int, month: int) -> list[tuple[date, date]]:
    last = calendar.monthrange(year, month)[1]
    return [(date(year, month, a), date(year, month, min(b, last)))
            for a, b in ((1, 7), (8, 14), (15, 21), (22, 31))]


def ensure_period_codes(store) -> None:
    """Backfill from immutable daily manifests; reruns never alter a sealed code."""
    with store.connect() as db:
        days = db.execute("SELECT day,digest,quality,counts,manifest FROM days ORDER BY day").fetchall()
        existing = {(row["scope"], row["start_utc"]) for row in db.execute(
            "SELECT scope,start_utc FROM period_codes")}
    by_day = {row["day"]: row for row in days}
    pending = []

    for row in days:
        start = _day_start(row["day"])
        manifest = json.loads(row["manifest"])
        for part in range(6):
            segment_start = start + timedelta(hours=part * 4)
            segment_end = segment_start + timedelta(hours=4)
            key = ("day4h", stamp(segment_start))
            if key in existing:
                continue
            begin, finish = stamp(segment_start), stamp(segment_end)
            sources = {name: [entry for entry in values if begin <= entry[0] < finish]
                       for name, values in manifest["sources"].items()}
            quantum = sum(sum(value is not None for _, value in sources.get(source, []))
                          for source in ("nist", "nqsn"))
            expected = 96  # two beacons, 48 five-minute slots each
            quality = "unavailable" if quantum == 0 else "partial" if quantum < expected or row["quality"] != "good" else "good"
            digest = _digest({"format": FORMAT, "scope": "day4h", "start_utc": begin,
                              "end_utc": finish, "manifest_format": manifest["format"],
                              "source_set": manifest.get("source_set"), "sources": sources})
            pending.append(_row("day4h", segment_start, segment_end, digest, quality))
            existing.add(key)

        key = ("week_day", stamp(start))
        if key not in existing:
            digest = _digest({"format": FORMAT, "scope": "week_day", "day_utc": row["day"],
                              "daily_sha256": row["digest"]})
            pending.append(_row("week_day", start, start + timedelta(days=1), digest, row["quality"]))
            existing.add(key)

    for year, month in sorted({(date.fromisoformat(day).year, date.fromisoformat(day).month) for day in by_day}):
        for first, last in _month_blocks(year, month):
            start = datetime.combine(first, datetime.min.time(), timezone.utc)
            end = datetime.combine(last + timedelta(days=1), datetime.min.time(), timezone.utc)
            key = ("month_block", stamp(start))
            if key in existing:
                continue
            dates = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
            if not all(day.isoformat() in by_day for day in dates):
                continue
            records = [by_day[day.isoformat()] for day in dates]
            digest = _digest({"format": FORMAT, "scope": "month_block", "start_utc": stamp(start),
                              "end_utc": stamp(end), "daily_sha256": [[row["day"], row["digest"]] for row in records]})
            quality = "unavailable" if all(row["quality"] == "unavailable" for row in records) else (
                "good" if all(row["quality"] == "good" for row in records) else "partial")
            pending.append(_row("month_block", start, end, digest, quality))
            existing.add(key)

        first = date(year, month, 1)
        last = _month_end(first)
        start = datetime.combine(first, datetime.min.time(), timezone.utc)
        end = datetime.combine(last + timedelta(days=1), datetime.min.time(), timezone.utc)
        key = ("year_month", stamp(start))
        if key in existing:
            continue
        dates = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
        if not all(day.isoformat() in by_day for day in dates):
            continue
        records = [by_day[day.isoformat()] for day in dates]
        digest = _digest({"format": FORMAT, "scope": "year_month", "start_utc": stamp(start),
                          "end_utc": stamp(end), "daily_sha256": [[row["day"], row["digest"]] for row in records]})
        quality = "unavailable" if all(row["quality"] == "unavailable" for row in records) else (
            "good" if all(row["quality"] == "good" for row in records) else "partial")
        pending.append(_row("year_month", start, end, digest, quality))

    if pending:
        with store.connect() as db:
            db.executemany("""INSERT OR IGNORE INTO period_codes
                (scope,start_utc,end_utc,digest,quality,created_at) VALUES(?,?,?,?,?,?)""", pending)


def public_period_codes(store, today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    latest = store.latest_day()
    anchor = date.fromisoformat(latest["day"]) if latest else today
    with store.connect() as db:
        rows = db.execute("SELECT scope,start_utc,end_utc,digest,quality FROM period_codes").fetchall()
    by_key = {(row["scope"], row["start_utc"]): row for row in rows}
    first_full = date.fromisoformat(store.first_full_day())

    def entry(scope: str, start: datetime, end: datetime, width: int) -> dict:
        row = by_key.get((scope, stamp(start)))
        if row:
            quality = row["quality"]
            return {"start_utc": stamp(start), "end_utc": stamp(end), "state": "sealed" if quality != "unavailable" else "unavailable",
                    "quality": quality, "sha256": row["digest"],
                    "codes": {name: short_code(row["digest"], name, width) for name in ALPHABETS} if quality != "unavailable" else None}
        state = "unavailable" if start.date() < first_full or end.date() <= today else "pending"
        return {"start_utc": stamp(start), "end_utc": stamp(end), "state": state,
                "quality": None, "sha256": None, "codes": None}

    result = {"format": FORMAT, "alphabets": {name: len(chars) for name, chars in ALPHABETS.items()}}
    if latest:
        day = date.fromisoformat(latest["day"])
        start = _day_start(latest["day"])
        result["day"] = {"label": day.isoformat(), "positions": [
            entry("day4h", start + timedelta(hours=4 * i), start + timedelta(hours=4 * (i + 1)), 1)
            for i in range(6)]}
    else:
        start = _day_start(first_full.isoformat())
        result["day"] = {"label": first_full.isoformat(), "positions": [
            {"start_utc": stamp(start + timedelta(hours=4 * i)),
             "end_utc": stamp(start + timedelta(hours=4 * (i + 1))),
             "state": "pending", "quality": None, "sha256": None, "codes": None}
            for i in range(6)]}
    monday = anchor - timedelta(days=anchor.weekday())
    result["week"] = {"label": f"{monday.isocalendar().year}-W{monday.isocalendar().week:02d}", "positions": [
        entry("week_day", datetime.combine(monday + timedelta(days=i), datetime.min.time(), timezone.utc),
              datetime.combine(monday + timedelta(days=i + 1), datetime.min.time(), timezone.utc), 1)
        for i in range(7)]}
    result["month"] = {"label": anchor.strftime("%Y-%m"), "positions": [
        entry("month_block", datetime.combine(a, datetime.min.time(), timezone.utc),
              datetime.combine(b + timedelta(days=1), datetime.min.time(), timezone.utc), 2)
        for a, b in _month_blocks(anchor.year, anchor.month)]}
    result["year"] = {"label": str(anchor.year), "positions": [
        entry("year_month", datetime(year=anchor.year, month=i, day=1, tzinfo=timezone.utc),
              datetime(year=anchor.year + (1 if i == 12 else 0), month=i % 12 + 1, day=1, tzinfo=timezone.utc), 1)
        for i in range(1, 13)]}
    return result
