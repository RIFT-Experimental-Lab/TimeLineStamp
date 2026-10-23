"""Switch v2 inputs off or on without modifying the collector code."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

from v2_sources import SOURCES, SOURCE_BY_ID


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the local TimeLineStamp v2 source set")
    parser.add_argument("action", choices=("list", "disable", "enable", "disable-group", "enable-group", "shadow", "activate"))
    parser.add_argument("value", nargs="?")
    parser.add_argument("--config", type=Path,
                        default=Path.home() / ".config/timelinestamp/v2-sources.json")
    args = parser.parse_args()
    config = args.config.expanduser()
    if not config.exists():
        parser.error(f"Missing config: {config}")
    data = json.loads(config.read_text(encoding="utf-8"))
    if args.action == "list":
        print(f"Shadow start UTC: {data.get('shadow_start_day_utc') or 'inactive'}")
        print(f"Start day UTC: {data.get('start_day_utc') or 'inactive'}")
        for source in SOURCES:
            disabled = source.id in data.get("disabled_sources", []) or source.group in data.get("disabled_groups", [])
            print(f"{'off' if disabled else 'on ':3} {source.id:16} {source.group}")
        return
    if not args.value:
        parser.error("This action needs a source ID, group, or UTC date")
    if args.action in {"disable", "enable"}:
        if args.value not in SOURCE_BY_ID:
            parser.error(f"Unknown source ID: {args.value}")
        key = "disabled_sources"
    elif args.action in {"disable-group", "enable-group"}:
        if args.value not in {source.group for source in SOURCES}:
            parser.error(f"Unknown group: {args.value}")
        key = "disabled_groups"
    else:
        try:
            requested = date.fromisoformat(args.value)
        except ValueError:
            parser.error("Use YYYY-MM-DD for shadow or activation")
        if requested.isoformat() != args.value:
            parser.error("Use YYYY-MM-DD")
        if args.action == "activate":
            if requested <= datetime.now(timezone.utc).date():
                parser.error("Activation must start on a future complete UTC day")
            data["start_day_utc"] = requested.isoformat()
        else:
            if requested < datetime.now(timezone.utc).date():
                parser.error("Shadow collection cannot start in the past")
            data["shadow_start_day_utc"] = requested.isoformat()
        key = None
    if key:
        values = set(data.get(key, []))
        if args.action.startswith("disable"):
            values.add(args.value)
        else:
            values.discard(args.value)
        data[key] = sorted(values)
    temporary = config.with_name(config.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, config)
    print(f"Updated {config}; change applies to the next unsealed v2 day")


if __name__ == "__main__":
    main()
