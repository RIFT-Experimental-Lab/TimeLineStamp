"""Build a local transfer kit from reviewed source and the complete published history."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from recovery import canonical, from_git, pack, validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--v2-config", type=Path, required=True, help="Reviewed configuration; never a token file")
    parser.add_argument("--termux-apk", type=Path)
    parser.add_argument("--boot-apk", type=Path)
    args = parser.parse_args()
    state = from_git(ROOT)
    config = json.loads(args.v2_config.read_text())
    if set(config) - {"start_day_utc", "shadow_start_day_utc", "disabled_groups", "disabled_sources"}:
        raise ValueError("Only public source configuration may enter the bundle")
    state["v2"] = config
    state = validate(pack({key: value for key, value in state.items() if key != "sha256"}))
    files = {"recovery-state.json": canonical(state) + b"\n", "v2-sources.json": canonical(config) + b"\n",
             "START_HERE_RU.txt": (ROOT / "android/RECOVERY-RU.txt").read_bytes()}
    for name in (ROOT / "android/package-files.txt").read_text().splitlines():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Invalid package file")
        files["project/" + name] = (ROOT / relative).read_bytes()
    for name, path in (("apps/Termux.apk", args.termux_apk), ("apps/TermuxBoot.apk", args.boot_apk)):
        if path:
            files[name] = path.read_bytes()
    manifest = {"format": "timelinestamp-recovery-bundle-v1", "built_at": datetime.now(timezone.utc).isoformat(),
                "last_published_day": state["days"][-1]["day"] if state["days"] else None,
                "days": len(state["days"]), "period_digests": len(state["periods"]),
                "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    files["bundle-manifest.json"] = canonical(manifest) + b"\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in files.items():
            archive.writestr("TimeLineStamp-recovery/" + name, data)
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            raise ValueError("Bundle ZIP verification failed")
        for name, digest in manifest["sha256"].items():
            if hashlib.sha256(archive.read("TimeLineStamp-recovery/" + name)).hexdigest() != digest:
                raise ValueError("Bundle checksum mismatch")
    args.output.with_suffix(args.output.suffix + ".sha256").write_text(
        hashlib.sha256(args.output.read_bytes()).hexdigest() + "  " + args.output.name + "\n")
    print(f"Ready: {args.output.name}; {len(state['days'])} days, {len(state['periods'])} period digests")


if __name__ == "__main__":
    main()
