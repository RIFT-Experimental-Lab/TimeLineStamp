"""Consistent rotating backups of the complete local measurements database."""

from __future__ import annotations

import gzip
import logging
import os
import shutil
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

from timelinestamp import Store


LOG = logging.getLogger("timelinestamp.backup")
BACKUP_PREFIX = "timelinestamp-"
BACKUP_SUFFIX = ".sqlite3.gz"


def create_backup(store: Store, backup_dir: Path, day: str) -> Path:
    """Copy the live WAL database, verify it, then atomically publish a gzip file."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    final = backup_dir / f"{BACKUP_PREFIX}{day}{BACKUP_SUFFIX}"
    if final.exists():
        return final
    working = store.path.parent / ".timelinestamp-backup-working.sqlite3"
    compressed = backup_dir / f".{BACKUP_PREFIX}{day}{BACKUP_SUFFIX}.tmp"
    for stale in backup_dir.glob(f".{BACKUP_PREFIX}*{BACKUP_SUFFIX}.tmp"):
        stale.unlink()
    for path in (working, Path(str(working) + "-wal"), Path(str(working) + "-shm"), compressed):
        path.unlink(missing_ok=True)
    try:
        with closing(store.connect()) as source, closing(sqlite3.connect(working)) as destination:
            source.backup(destination, pages=1000, sleep=0.05)
            check = destination.execute("PRAGMA quick_check").fetchone()[0]
            if check != "ok":
                raise RuntimeError(f"Backup integrity check failed: {check}")
        with working.open("rb") as source_file, gzip.open(compressed, "wb", compresslevel=6) as target_file:
            shutil.copyfileobj(source_file, target_file, length=1024 * 1024)
        with compressed.open("rb") as completed:
            os.fsync(completed.fileno())
        os.replace(compressed, final)
        backups = sorted(backup_dir.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}"))
        for old in backups[:-2]:
            old.unlink()
        LOG.info("Complete backup for %s: %s (%d bytes)", day, final, final.stat().st_size)
        return final
    finally:
        for path in (working, Path(str(working) + "-wal"), Path(str(working) + "-shm"), compressed):
            path.unlink(missing_ok=True)


class BackupWorker:
    def __init__(self, store: Store, backup_dir: Path):
        self.store = store
        self.backup_dir = backup_dir.expanduser()
        self.stop = threading.Event()

    def run(self) -> None:
        while not self.stop.is_set():
            try:
                current = self.store.latest_day()
                if current:
                    create_backup(self.store, self.backup_dir, current["day"])
                delay = 60
            except Exception as exc:
                LOG.warning("Database backup failed: %s", exc)
                delay = 300
            self.stop.wait(delay)
