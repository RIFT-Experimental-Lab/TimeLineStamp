import hashlib
import fcntl
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from timelinestamp import Collector, Store, beacon_payload, canonical, iso, noaa_payload, parse_utc
from initial_snapshot import create_initial_snapshot


class TimelinestampTests(unittest.TestCase):
    def test_initial_snapshot_uses_fixed_received_cutoff(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.sqlite3")
            day = "2026-10-20"
            for source in ("nist", "nqsn", "noaa_mag", "noaa_wind"):
                event = day + "T12:00:00Z"
                store.add_observation(source, event, event, {"value": source}, {}, "f" * 64, "test")
            cutoff = datetime(2026, 10, 20, 12, 5, tzinfo=timezone.utc)
            with store.connect() as db:
                db.execute("UPDATE observations SET received_at=?", (day + "T12:01:00Z",))
            first = create_initial_snapshot(store, cutoff)
            self.assertEqual(first["day"], day)
            self.assertEqual(first["quality"], "partial")
            self.assertRegex(first["coefficient"], r"^1\.\d{6}$")
            with store.connect() as db:
                db.execute("""INSERT INTO observations(source,event_time,slot_time,received_at,payload,raw,response_sha256,url)
                    VALUES(?,?,?,?,?,?,?,?)""", ("nist", day + "T12:02:00Z", day + "T12:02:00Z",
                    day + "T12:06:00Z", '{"value":"late"}', '{}', "f" * 64, "test"))
            self.assertEqual(create_initial_snapshot(store, cutoff), first)

    def test_finalized_day_never_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.sqlite3")
            day = "2026-10-20"
            event_time = day + "T00:00:00Z"
            store.add_observation("nist", event_time, event_time,
                                  {"value": "a" * 128, "chain": 1, "index": 7}, {}, "f" * 64, "test")
            first = store.finalize_day(day)
            self.assertEqual(first["quality"], "partial")
            self.assertEqual(first["counts"]["nist"]["received"], 1)
            self.assertEqual(first["counts"]["nqsn"]["received"], 0)
            self.assertEqual(len(first["digest"]), 64)
            self.assertRegex(first["coefficient"], r"^1\.\d{6}$")
            self.assertEqual(hashlib.sha256(canonical(store.get_manifest(day))).hexdigest(), first["digest"])
            store.add_observation("nqsn", event_time, event_time,
                                  {"value": "b" * 128, "chain": 1, "index": 9}, {}, "f" * 64, "test")
            self.assertEqual(store.finalize_day(day), first)

    def test_beacon_rejects_wrong_minute(self):
        slot = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        data = {"pulse": {"timeStamp": iso(slot + timedelta(minutes=1)),
                          "localRandomValue": "a" * 128, "statusCode": 0,
                          "chainIndex": 1, "pulseIndex": 1}}
        with self.assertRaisesRegex(ValueError, "different minute"):
            beacon_payload("nist", data, slot)

    def test_noaa_requires_active_good_measurement(self):
        row = {"time_tag": "2026-10-20T12:00:01", "active": True,
               "overall_quality": 0, "source": "SOLAR1",
               "bt": 7.1, "bx_gsm": 1.2, "by_gsm": 3.4, "bz_gsm": -2.1}
        self.assertEqual(noaa_payload("noaa_mag", row)[1]["spacecraft"], "SOLAR1")
        row["overall_quality"] = 1
        self.assertIsNone(noaa_payload("noaa_mag", row))

    def test_noaa_timestamp_without_suffix_is_utc(self):
        self.assertEqual(iso(parse_utc("2026-10-20T12:00:01")), "2026-10-20T12:00:01Z")

    def test_restart_request_reaches_running_collector(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "test.sqlite3"
            store = Store(db)
            with db.with_suffix(".sqlite3.lock").open("w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = subprocess.run([sys.executable, str(Path(__file__).with_name("timelinestamp.py")),
                                         "--restart", "--db", str(db)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Restart requested", result.stdout)
                restart_request = db.with_suffix(".sqlite3.restart")
                self.assertTrue(restart_request.exists())
                Collector(store).run()
                self.assertFalse(restart_request.exists())


if __name__ == "__main__":
    unittest.main()
