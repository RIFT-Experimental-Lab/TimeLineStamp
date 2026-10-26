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
tar --uid 0 --gid 0 --uname rift --gname rift -czf "$temporary" -C "$project_dir" -T "$project_dir/android/package-files.txt"
tar -tzf "$temporary" >/dev/null
mv -f "$temporary" "$archive"
shasum -a 256 "$archive" > "$archive.sha256"
printf 'Готово: %s\n' "$archive"
printf 'SHA-256: '
shasum -a 256 "$archive" | cut -d ' ' -f 1
