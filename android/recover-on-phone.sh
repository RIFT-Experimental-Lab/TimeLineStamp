#!/data/data/com.termux/files/usr/bin/sh
set -eu
umask 077
bundle_project=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
bundle_root=$(dirname "$bundle_project")
target="$HOME/TimeLineStamp"
if [ -e "$target/data/timelinestamp.sqlite3" ]; then
    printf 'A database already exists. This recovery command will not overwrite it.\n' >&2
    exit 1
fi
if [ ! -f "$bundle_root/recovery-state.json" ]; then
    printf 'Recovery state is missing. Extract the complete recovery bundle first.\n' >&2
    exit 1
fi
pkg install -y python openssh git
python - "$bundle_root" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1])
manifest=json.loads((root/'bundle-manifest.json').read_text())
for name,expected in manifest['sha256'].items():
    path=Path(name)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Invalid bundle path')
    digest=hashlib.sha256()
    with (root/path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            digest.update(chunk)
    if digest.hexdigest()!=expected:
        raise ValueError('Bundle checksum mismatch: '+name)
print('Bundle integrity verified')
PY
mkdir -p "$target" "$HOME/.config/timelinestamp"
cp -R "$bundle_project/." "$target/"
cp "$bundle_root/v2-sources.json" "$HOME/.config/timelinestamp/v2-sources.json"
state_file="$bundle_root/recovery-state.json"
if python "$target/recovery.py" fetch-state --output "$HOME/.config/timelinestamp/recovery-latest.json"; then
    state_file="$HOME/.config/timelinestamp/recovery-latest.json"
else
    printf 'Could not fetch current history. Fix network access and rerun before starting collection.\n' >&2
    exit 1
fi
python - "$state_file" "$HOME/.config/timelinestamp/v2-sources.json" <<'PY'
import json,sys
from pathlib import Path
state=json.loads(Path(sys.argv[1]).read_text())
if state.get('v2') is not None:
    Path(sys.argv[2]).write_text(json.dumps(state['v2'])+'\n')
PY
if [ "$#" -gt 0 ]; then
    python "$target/recovery.py" restore --backup "$1" --db "$target/data/timelinestamp.sqlite3" \
        --v2-config "$HOME/.config/timelinestamp/v2-sources.json" --history "$state_file"
else
    python "$target/recovery.py" restore --state "$state_file" \
        --db "$target/data/timelinestamp.sqlite3" --v2-config "$HOME/.config/timelinestamp/v2-sources.json"
fi
sh "$target/android/install-termux.sh"
printf '\nRecovery complete. Publishing and downloads are disabled until a new token is installed.\n'
printf 'Use android/configure-publishing.sh, then start Termux:Boot and the boot script.\n'
