import gzip
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backup_store import create_backup
from timelinestamp import Store


class BackupTests(unittest.TestCase):
    def test_backups_keep_all_measurements_and_rotate_two_copies(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = Store(root / "data" / "timelinestamp.sqlite3")
            backup_dir = root / "backups"
            for day in ("2026-10-20", "2026-10-21", "2026-10-22"):
                event = day + "T00:00:00Z"
                store.add_observation("nist", event, event, {"value": "a" * 128, "chain": 1, "index": 1},
                                      {"raw": day}, "f" * 64, "https://example.test")
                store.finalize_day(day)
                create_backup(store, backup_dir, day)
            names = sorted(path.name for path in backup_dir.glob("*.sqlite3.gz"))
            self.assertEqual(names, ["timelinestamp-2026-10-21.sqlite3.gz", "timelinestamp-2026-10-22.sqlite3.gz"])
            restored = root / "restored.sqlite3"
            with gzip.open(backup_dir / names[-1], "rb") as source, restored.open("wb") as target:
                shutil.copyfileobj(source, target)
            with sqlite3.connect(restored) as db:
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 3)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM days").fetchone()[0], 3)
                self.assertEqual(db.execute("SELECT raw FROM observations WHERE event_time LIKE '2026-10-20%'").fetchone()[0],
                                 '{"raw":"2026-10-20"}')


if __name__ == "__main__":
    unittest.main()
