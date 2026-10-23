#!/bin/zsh
set -euo pipefail
export LC_ALL=C LANG=C
export COPYFILE_DISABLE=1
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -d "$project_dir/../local" ]]; then
  archive_dir="$project_dir/../local/packages"
else
  archive_dir="$HOME/Downloads"
fi
mkdir -p "$archive_dir"
archive="$archive_dir/TimeLineStamp-android.tar.gz"
temporary="$(mktemp "$archive_dir/.TimeLineStamp-android.XXXXXX")"
trap 'rm -f "$temporary"' EXIT
tar -czf "$temporary" -C "$project_dir" \
  timelinestamp.py publish_github.py backup_store.py test_now.py test_now.command \
  v2_sources.py v2_sources.json probe_v2_sources.py v2_toggle.py period_codes.py \
  README.md ANDROID.md GITHUB_PAGES.md \
  docs/index.html docs/style.css docs/app.js docs/.nojekyll docs/data/status.json \
  android/config.example android/install-termux.sh android/termux-boot.sh \
  android/enable-ssh.sh android/ssh-watchdog.py android/package.command
tar -tzf "$temporary" >/dev/null
mv -f "$temporary" "$archive"
shasum -a 256 "$archive" > "$archive.sha256"
printf 'Готово: %s\n' "$archive"
printf 'SHA-256: '
shasum -a 256 "$archive" | cut -d ' ' -f 1
