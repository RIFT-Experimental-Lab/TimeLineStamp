import copy
import base64
import io
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from backup_store import create_backup
from period_codes import public_period_codes
from recovery import checkpoint, restore, restore_backup, merge_published_history, fetch_state, canonical
from raw_archive import available_days
from timelinestamp import Collector, Store
from urllib.error import URLError


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.original = Store(self.root / "original.sqlite3")
        with self.original.connect() as db:
            db.execute("UPDATE meta SET value='2026-09-30T00:00:00Z' WHERE key='started_at'")

    def tearDown(self):
        self.folder.cleanup()

    def seal(self, day):
        event = day + "T00:00:00Z"
        self.original.add_observation("nist", event, event, {"value": "a" * 128}, {"raw_secret": "not transferred"}, "f" * 64, "private")
        self.original.finalize_day(day)

    def test_published_state_restores_exact_marks_without_creating_raw_data(self):
        for number in range(1, 8):
            self.seal(f"2026-10-{number:02d}")
        state = checkpoint(self.original)
        with patch("timelinestamp.utc_now", return_value=datetime(2026, 10, 26, 14, tzinfo=timezone.utc)):
            restored = restore(state, self.root / "new.sqlite3")
        self.assertEqual(restored.history(), self.original.history())
        self.assertEqual(public_period_codes(restored), public_period_codes(self.original))
        self.assertEqual(restored.first_full_day(), "2026-10-01")
        self.assertEqual(restored.collection_first_full_day(), "2026-10-27")
        self.assertIsNone(restored.get_manifest("2026-10-01"))
        self.assertEqual(available_days(restored.path), [])
        Collector(restored).finalize_due_days(datetime(2026, 10, 27, 0, 14, tzinfo=timezone.utc))
        self.assertEqual(restored.history(), self.original.history())
        # Rebuilding a day after recovery must return the preserved record.
        self.assertEqual(restored.finalize_day("2026-10-01"), self.original.get_day("2026-10-01"))

    def test_bad_checkpoint_and_existing_database_are_rejected(self):
        self.seal("2026-10-01")
        state = checkpoint(self.original)
        changed = copy.deepcopy(state); changed["days"][0]["digest"] = "0" * 64
        with self.assertRaises(ValueError):
            restore(changed, self.root / "invalid.sqlite3")
        self.assertFalse((self.root / "invalid.sqlite3").exists())
        with self.assertRaises(ValueError):
            restore(state, self.original.path)

    def test_full_backup_keeps_raw_and_merges_newer_published_records(self):
        self.seal("2026-10-01")
        backup = create_backup(self.original, self.root / "backups", "2026-10-01")
        self.seal("2026-10-02")
        restored = restore_backup(backup, self.root / "restored.sqlite3")
        merge_published_history(restored, checkpoint(self.original))
        self.assertEqual(restored.history(), self.original.history())
        self.assertIsNotNone(restored.get_manifest("2026-10-01"))
        self.assertIsNone(restored.get_manifest("2026-10-02"))
        self.assertEqual([r["day"] for r in available_days(restored.path)], ["2026-10-01"])

    def test_recovery_can_use_api_when_raw_host_is_unreachable(self):
        self.seal("2026-10-01")
        state = checkpoint(self.original)
        response = io.BytesIO(canonical({"content": base64.b64encode(canonical({"recovery": state})).decode()}))
        with patch("recovery.urlopen", side_effect=[URLError("unreachable"), response]):
            self.assertEqual(fetch_state(), state)


if __name__ == "__main__":
    unittest.main()
