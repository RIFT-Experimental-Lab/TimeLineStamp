#!/data/data/com.termux/files/usr/bin/sh
set -eu
umask 077
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
config_file="$HOME/.config/timelinestamp/config"
if [ ! -f "$config_file" ]; then
    printf 'Run android/install-termux.sh first.\n' >&2
    exit 1
fi
. "$config_file"
repo="${TIMELINESTAMP_REPO:-}"
token_file="${TIMELINESTAMP_TOKEN_FILE:-$HOME/.config/timelinestamp/github-token}"
if [ -z "$repo" ] || [ ! -s "$token_file" ]; then
    printf 'Configure the project repository and a private GitHub token first.\n' >&2
    exit 1
fi
pkg install -y cloudflared
python - "$config_file" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
lines=[line for line in p.read_text().splitlines() if not line.startswith('TIMELINESTAMP_DOWNLOADS_ENABLED=')]
p.write_text('\n'.join(lines)+'\nTIMELINESTAMP_DOWNLOADS_ENABLED="1"\n')
p.chmod(0o600)
PY
cp "$project_dir/android/termux-boot.sh" "$HOME/.termux/boot/90-timelinestamp"
chmod 700 "$HOME/.termux/boot/90-timelinestamp"
nohup python "$project_dir/public_downloads.py" --db "$project_dir/data/timelinestamp.sqlite3" \
    --repo "$repo" --token-file "$token_file" >/dev/null 2>&1 &
printf 'Archive service requested. See ~/.local/state/timelinestamp/downloads.log\n'
