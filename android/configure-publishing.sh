#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
umask 077
config_file="$HOME/.config/timelinestamp/config"
if [[ ! -f "$config_file" ]]; then
    printf 'Run install-termux.sh first.\n' >&2
    exit 1
fi
read -r -s -p 'Paste a new GitHub token for the laboratory repository (hidden): ' project_token
printf '\n'
if [[ -z "$project_token" ]]; then exit 1; fi
mkdir -p "$HOME/.config/timelinestamp"
printf '%s\n' "$project_token" > "$HOME/.config/timelinestamp/github-token"
chmod 600 "$HOME/.config/timelinestamp/github-token"
unset project_token
python - "$config_file" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
lines=[line for line in p.read_text().splitlines() if not line.startswith('TIMELINESTAMP_REPO=')]
p.write_text('\n'.join(lines)+'\nTIMELINESTAMP_REPO="RIFT-Experimental-Lab/TimeLineStamp"\n')
p.chmod(0o600)
PY
printf 'Publishing configured. Keep the previous collector stopped.\n'
