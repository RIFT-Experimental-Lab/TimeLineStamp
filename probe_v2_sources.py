"""Run on the Android host to test every pinned v2 source from that network."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from v2_sources import SOURCES, _daily_url, daily_samples, live_sample, live_url, stamp


def probe_one(source, now: datetime) -> dict:
    started = time.monotonic()
    result = {"id": source.id, "group": source.group, "kind": source.kind}
    try:
        if source.kind in {"geofon", "geonet", "intermagnet", "opensky", "osm"}:
            slot = now.replace(minute=0, second=0, microsecond=0)
            if source.kind in {"geofon", "geonet", "intermagnet"}:
                slot -= timedelta(hours=1)
            if source.kind == "osm" and now.minute < 5:
                slot -= timedelta(hours=1)
            payload, receipt = live_sample(source, slot)
            observed = payload.get("observed_at", stamp(slot))
            result.update(status="ok", observed_at=observed, items=(len(payload.get("states", []))
                         if source.kind == "opensky" else 1), receipt=receipt)
        else:
            day = (now.date() - timedelta(days=1)).isoformat() if source.kind == "wikimedia" else now.date().isoformat()
            samples, receipt = daily_samples(source, day)
            if not samples:
                raise ValueError(f"No valid hourly sample for {day}")
            latest = samples[max(samples)]["observed_at"]
            result.update(status="ok", day=day, observed_at=latest, items=len(samples), receipt=receipt)
            if source.kind == "wikimedia":
                if len(samples) < 24:
                    result["status"] = "delayed"
            elif (now - datetime.fromisoformat(latest.replace("Z", "+00:00"))).total_seconds() > 8 * 3600:
                result["status"] = "stale"
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Check all v2 source endpoints from this device")
    parser.add_argument("--output", type=Path, help="Write detailed JSON report here")
    parser.add_argument("--group", help="Only check one provider group")
    parser.add_argument("--enabled-only", action="store_true", help="Check only sources enabled in local v2 config")
    parser.add_argument("--config", type=Path,
                        default=Path.home() / ".config/timelinestamp/v2-sources.json")
    parser.add_argument("--require-termux", action="store_true", help="Reject a Mac/Linux run")
    parser.add_argument("--list-requests", action="store_true", help="Print the exact primary URLs without fetching")
    args = parser.parse_args()
    runtime = "termux" if Path(sys.executable).as_posix().startswith("/data/data/com.termux/") else "other"
    if args.require_termux and runtime != "termux":
        parser.error("This check must run inside Termux on the phone")
    now = datetime.now(timezone.utc)
    disabled_groups: set[str] = set()
    disabled_sources: set[str] = set()
    if args.enabled_only:
        if not args.config.exists():
            parser.error(f"Missing config: {args.config}")
        settings = json.loads(args.config.read_text(encoding="utf-8"))
        disabled_groups = set(settings.get("disabled_groups", []))
        disabled_sources = set(settings.get("disabled_sources", []))
    selected = [source for source in SOURCES if (not args.group or source.group == args.group)
                and source.group not in disabled_groups and source.id not in disabled_sources]
    if args.list_requests:
        for source in selected:
            if source.kind in {"geofon", "geonet", "intermagnet", "opensky", "osm"}:
                slot = now.replace(minute=0, second=0, microsecond=0)
                if source.kind in {"geofon", "geonet", "intermagnet"} or (source.kind == "osm" and now.minute < 5):
                    slot -= timedelta(hours=1)
                url = live_url(source, slot)
            else:
                day = (now.date() - timedelta(days=1)).isoformat() if source.kind == "wikimedia" else now.date().isoformat()
                url = _daily_url(source, day)
            print(f"{source.id:16} {url}")
        return
    results = []
    for source in selected:
        result = probe_one(source, now)
        results.append(result)
        detail = result.get("observed_at") or result.get("error")
        print(f"{result['status']:6} {source.id:16} {detail}", flush=True)
    report = {"format": "timelinestamp-v2-probe-1", "tested_at": stamp(now),
              "runtime": runtime, "results": results,
              "ok": sum(item["status"] == "ok" for item in results), "total": len(results)}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Report: {args.output}")
    print(f"Available: {report['ok']}/{report['total']}")
    if report["ok"] != report["total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
