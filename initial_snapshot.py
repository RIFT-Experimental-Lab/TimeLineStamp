"""Make one immutable public summary from the collector's incomplete first day."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from timelinestamp import LOCAL_DATA, SOURCE_NAMES, Store, canonical, display_coefficient, iso, parse_utc, utc_now


def create_initial_snapshot(store: Store, cutoff: datetime) -> dict:
    cutoff = cutoff.astimezone(timezone.utc)
    day = cutoff.date().isoformat()
    start = day + "T00:00:00Z"
    end = iso(cutoff)
    with store.connect() as db:
        rows = db.execute("""SELECT source,event_time,slot_time,payload FROM observations
            WHERE event_time>=? AND event_time<? AND received_at<?
            ORDER BY source,event_time""", (start, end, end)).fetchall()
    sources = {source: [] for source in SOURCE_NAMES}
    for row in rows:
        sources[row["source"]].append([row["slot_time"] or row["event_time"], json.loads(row["payload"])])
    counts = {source: {"received": len(values), "expected": 288 if source in ("nist", "nqsn") else 1440}
              for source, values in sources.items()}
    if not all(counts[source]["received"] for source in SOURCE_NAMES):
        raise ValueError("An initial snapshot requires measurements from all four sources")
    manifest = {"format": "timelinestamp-initial-v1", "day_utc": day,
                "captured_at": end, "sources": sources}
    digest = hashlib.sha256(canonical(manifest)).hexdigest()
    return {"format": "timelinestamp-initial-v1", "day": day,
            "created_at": end, "period_start": min(row["event_time"] for row in rows),
            "digest": digest, "coefficient": display_coefficient(digest),
            "quality": "partial", "counts": counts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=LOCAL_DATA / "timelinestamp.sqlite3")
    parser.add_argument("--cutoff", type=parse_utc, default=None,
                        help="Fixed UTC cutoff; omit to capture the current measurements")
    args = parser.parse_args()
    print(canonical(create_initial_snapshot(Store(args.db), args.cutoff or utc_now())).decode())


if __name__ == "__main__":
    main()
