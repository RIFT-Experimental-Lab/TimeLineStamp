"""One-shot macOS probe. Does not write to the daily Timelinestamp database."""

from __future__ import annotations

import hashlib
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from timelinestamp import (
    BEACON_SOURCES,
    NOAA_SOURCES,
    NOAA_URLS,
    beacon_payload,
    beacon_url,
    canonical,
    display_coefficient,
    fetch_json,
    noaa_payload,
    parse_utc,
    utc_now,
)


def latest_noaa(source: str, data: object, now: datetime) -> tuple[str, dict]:
    if not isinstance(data, list):
        raise ValueError(f"{source}: ответ NOAA имеет неверный формат")
    valid = []
    for row in data:
        parsed = noaa_payload(source, row)
        if parsed and now - timedelta(minutes=30) <= parse_utc(parsed[0]) <= now:
            valid.append(parsed)
    if not valid:
        raise ValueError(f"{source}: нет подходящих измерений за последние 30 минут")
    return max(valid, key=lambda item: item[0])


def take_snapshot(now: datetime | None = None) -> tuple[str, str, dict]:
    now = now or utc_now()
    # Use a common, already-published five-minute pulse for both beacons.
    base = int((now.timestamp() - 120) // 300) * 300
    last_error = None
    beacon_results = None
    with ThreadPoolExecutor(max_workers=4) as pool:
        noaa_futures = {source: pool.submit(fetch_json, NOAA_URLS[source]) for source in NOAA_SOURCES}
        for age in range(3):
            slot = datetime.fromtimestamp(base - age * 300, timezone.utc)
            futures = {source: pool.submit(fetch_json, beacon_url(source, slot)) for source in BEACON_SOURCES}
            try:
                beacon_results = {
                    source: beacon_payload(source, futures[source].result()[0], slot)
                    for source in BEACON_SOURCES
                }
                break
            except (OSError, ValueError, KeyError, TypeError) as exc:
                last_error = exc
        if beacon_results is None:
            raise RuntimeError(f"Не удалось получить общий пульс NIST и NQSN: {last_error}")
        noaa_results = {
            source: latest_noaa(source, noaa_futures[source].result()[0], now)
            for source in NOAA_SOURCES
        }

    measurements = {**beacon_results, **noaa_results}
    snapshot = {
        "format": "timelinestamp-test-snapshot-v1",
        "sources": {
            source: {"event_time": event_time, "measurement": payload}
            for source, (event_time, payload) in measurements.items()
        },
    }
    digest = hashlib.sha256(canonical(snapshot)).hexdigest()
    return display_coefficient(digest), digest, snapshot


def main() -> int:
    try:
        coefficient, digest, snapshot = take_snapshot()
    except Exception as exc:
        print(f"Ошибка тестового измерения: {exc}", file=sys.stderr)
        return 1
    print(coefficient)
    print("Тестовый снимок, не суточный коэффициент")
    for source, item in snapshot["sources"].items():
        print(f"{source}: {item['event_time']}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
