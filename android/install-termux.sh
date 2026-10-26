#!/data/data/com.termux/files/usr/bin/sh
set -eu
umask 077

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if ! command -v python >/dev/null 2>&1 || ! command -v termux-wake-lock >/dev/null 2>&1; then
    printf 'Install Python in Termux first: pkg install python\n' >&2
    exit 1
fi
if [ ! -d "$HOME/storage/shared" ]; then
    printf 'Grant file access first: termux-setup-storage\n' >&2
    exit 1
fi
python - "$project_dir" <<'PY'
import ast
import sys
from pathlib import Path

if sys.version_info < (3, 9):
    raise SystemExit("Python 3.9 or newer is required")
root = Path(sys.argv[1])
for name in ("timelinestamp.py", "test_now.py", "backup_store.py", "publish_github.py", "period_codes.py", "recovery.py", "raw_archive.py", "public_downloads.py", "v2_sources.py", "probe_v2_sources.py", "v2_toggle.py", "android/ssh-watchdog.py"):
    ast.parse((root / name).read_text(encoding="utf-8"), filename=name)
PY
config_dir="$HOME/.config/timelinestamp"
boot_dir="$HOME/.termux/boot"
mkdir -p "$config_dir" "$boot_dir" "$HOME/.local/state/timelinestamp"
if [ ! -e "$config_dir/config" ]; then
    cp "$project_dir/android/config.example" "$config_dir/config"
    chmod 600 "$config_dir/config"
fi
if [ ! -e "$config_dir/v2-sources.json" ]; then
    cp "$project_dir/v2_sources.json" "$config_dir/v2-sources.json"
    chmod 600 "$config_dir/v2-sources.json"
fi
cp "$project_dir/android/termux-boot.sh" "$boot_dir/90-timelinestamp"
chmod 700 "$boot_dir/90-timelinestamp"
printf 'Installed boot script: %s\n' "$boot_dir/90-timelinestamp"
printf 'Configuration: %s\n' "$config_dir/config"
printf 'Start Termux:Boot once from the launcher, then run the boot script manually for a first test.\n'
