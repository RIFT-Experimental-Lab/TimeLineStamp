#!/data/data/com.termux/files/usr/bin/sh
set -u

config_file="$HOME/.config/timelinestamp/config"
state_dir="$HOME/.local/state/timelinestamp"
mkdir -p "$state_dir"
if [ ! -f "$config_file" ]; then
    printf 'Missing config: %s\n' "$config_file" >&2
    exit 1
fi
. "$config_file"
project_dir="${TIMELINESTAMP_PROJECT_DIR:-$HOME/TimeLineStamp}"
token_file="${TIMELINESTAMP_TOKEN_FILE:-$HOME/.config/timelinestamp/github-token}"
backup_dir="${TIMELINESTAMP_BACKUP_DIR:-$HOME/storage/shared/TimeLineStamp-backups}"
repo="${TIMELINESTAMP_REPO:-}"
if [ ! -f "$project_dir/timelinestamp.py" ]; then
    printf 'Missing project: %s\n' "$project_dir" >&2
    exit 1
fi

termux-wake-lock
if [ -f "$HOME/.config/timelinestamp/ssh.env" ]; then
    python "$project_dir/android/ssh-watchdog.py" >/dev/null 2>&1 &
fi
while :; do
    # Pick up repository and token changes after a collector restart.
    . "$config_file"
    token_file="${TIMELINESTAMP_TOKEN_FILE:-$HOME/.config/timelinestamp/github-token}"
    backup_dir="${TIMELINESTAMP_BACKUP_DIR:-$HOME/storage/shared/TimeLineStamp-backups}"
    repo="${TIMELINESTAMP_REPO:-}"
    if [ -f "$state_dir/launcher.log" ] && [ "$(wc -c < "$state_dir/launcher.log")" -gt 1000000 ]; then
        mv "$state_dir/launcher.log" "$state_dir/launcher.log.old"
    fi
    set -- --headless --db "$project_dir/data/timelinestamp.sqlite3" --log-file "$state_dir/collector.log"
    if [ -n "$backup_dir" ]; then
        set -- "$@" --backup-dir "$backup_dir"
    fi
    if [ -n "$repo" ]; then
        set -- "$@" --publish-repo "$repo" --token-file "$token_file"
    fi
    python "$project_dir/timelinestamp.py" "$@" >> "$state_dir/launcher.log" 2>&1
    printf '%s Collector stopped; restarting in 60 seconds\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "$state_dir/launcher.log"
    sleep 60
done
