import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from period_codes import ALPHABETS, ensure_period_codes, public_period_codes, short_code
from timelinestamp import Store


class PeriodCodesTests(unittest.TestCase):
    def make_store(self):
        folder = tempfile.TemporaryDirectory()
        store = Store(Path(folder.name) / "test.sqlite3")
        with store.connect() as db:
            db.execute("UPDATE meta SET value='2026-09-30T00:00:00Z' WHERE key='started_at'")
        return folder, store

    def seal(self, store, day):
        start = datetime.combine(day, datetime.min.time(), timezone.utc)
        for hour in (0, 4, 8, 12, 16, 20):
            slot = (start + timedelta(hours=hour)).isoformat().replace("+00:00", "Z")
            store.add_observation("nist", slot, slot, {"value": str(day) + str(hour)},
                                  {"private_raw": "not public"}, "f" * 64, "https://private.invalid")
        return store.finalize_day(day.isoformat())

    def test_day_segments_and_backfill_are_immutable(self):
        folder, store = self.make_store()
        try:
            day = date(2026, 10, 23)
            daily = self.seal(store, day)
            first = public_period_codes(store, date(2026, 10, 24))
            self.assertEqual(len(first["day"]["positions"]), 6)
            self.assertTrue(all(item["state"] == "sealed" for item in first["day"]["positions"]))
            self.assertEqual(first["week"]["positions"][4]["state"], "sealed")
            self.assertEqual(first["week"]["positions"][0]["state"], "unavailable")
            self.assertEqual(first["month"]["positions"][3]["state"], "pending")
            self.assertEqual(first["year"]["positions"][9]["state"], "pending")
            self.assertEqual(store.get_day(day.isoformat()), daily)
            with store.connect() as db:
                before = db.execute("SELECT * FROM period_codes ORDER BY scope,start_utc").fetchall()
            ensure_period_codes(store)
            with store.connect() as db:
                after = db.execute("SELECT * FROM period_codes ORDER BY scope,start_utc").fetchall()
            self.assertEqual([tuple(x) for x in before], [tuple(x) for x in after])
            self.assertNotIn("private_raw", json.dumps(first))
            self.assertNotIn("private.invalid", json.dumps(first))
        finally:
            folder.cleanup()

    def test_first_day_stays_pending_until_sealed(self):
        folder, store = self.make_store()
        try:
            view = public_period_codes(store, date(2026, 10, 1))
            self.assertEqual(view["day"]["label"], "2026-10-01")
            self.assertEqual([item["state"] for item in view["day"]["positions"]], ["pending"] * 6)
            self.assertTrue(all(item["sha256"] is None for item in view["day"]["positions"]))
        finally:
            folder.cleanup()

    def test_completed_month_block_and_month_are_released_progressively(self):
        folder, store = self.make_store()
        try:
            for number in range(1, 32):
                self.seal(store, date(2026, 10, number))
            before = public_period_codes(store, date(2026, 11, 1))
            self.assertEqual(before["month"]["label"], "2026-10")
            self.assertEqual([item["state"] for item in before["month"]["positions"]], ["sealed"] * 4)
            self.assertEqual(before["year"]["positions"][9]["state"], "sealed")
            self.assertEqual(before["year"]["positions"][8]["state"], "unavailable")
            self.assertEqual(len(before["month"]["positions"][3]["codes"]["hex"]), 2)
        finally:
            folder.cleanup()

    def test_one_changed_four_hour_interval_keeps_other_marks(self):
        first_folder, first = self.make_store()
        second_folder, second = self.make_store()
        try:
            day = "2026-10-23"
            for store in (first, second):
                for hour in (0, 4, 8, 12, 16, 20):
                    slot = f"{day}T{hour:02d}:00:00Z"
                    value = "changed" if store is second and hour == 12 else "same"
                    store.add_observation("nist", slot, slot, {"value": value}, {}, "f" * 64, "test")
                store.finalize_day(day)
            a = public_period_codes(first, date(2026, 10, 24))["day"]["positions"]
            b = public_period_codes(second, date(2026, 10, 24))["day"]["positions"]
            self.assertEqual([x["sha256"] == y["sha256"] for x, y in zip(a, b)],
                             [True, True, True, False, True, True])
        finally:
            first_folder.cleanup()
            second_folder.cleanup()

    def test_leap_february_and_iso_week_boundary(self):
        folder, store = self.make_store()
        try:
            for number in range(1, 30):
                self.seal(store, date(2028, 2, number))
            result = public_period_codes(store, date(2028, 2, 29))
            self.assertTrue(all(item["state"] == "sealed" for item in result["month"]["positions"]))
            self.assertEqual(result["month"]["positions"][3]["end_utc"], "2028-03-01T00:00:00Z")
            empty_folder, empty = self.make_store()
            try:
                week = public_period_codes(empty, date(2028, 1, 1))["week"]
                self.assertEqual(week["label"], "2027-W52")
            finally:
                empty_folder.cleanup()
        finally:
            folder.cleanup()

    def test_sunday_seal_keeps_completed_week_visible_on_monday(self):
        folder, store = self.make_store()
        try:
            self.seal(store, date(2026, 10, 25))
            view = public_period_codes(store, date(2026, 10, 26))
            self.assertEqual(view["week"]["label"], "2026-W43")
            self.assertEqual(view["week"]["positions"][6]["state"], "sealed")
        finally:
            folder.cleanup()

    def test_format_lengths_and_collision_space(self):
        digest = "f" * 64
        for name, alphabet in ALPHABETS.items():
            for width in (1, 2):
                code = short_code(digest, name, width)
                self.assertEqual(len(code), width)
                self.assertTrue(set(code) <= set(alphabet))


if __name__ == "__main__":
    unittest.main()
