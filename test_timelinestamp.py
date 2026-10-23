import hashlib
import fcntl
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from timelinestamp import Collector, Store, beacon_payload, canonical, iso, noaa_payload, parse_utc
from v2_sources import SOURCE_BY_ID, _hour_samples, daily_samples, live_sample
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
            store.add_observation("ge_acrg", event_time, event_time, {"data_b64": "example"}, {}, "f" * 64, "test")
            first = store.finalize_day(day)
            self.assertEqual(first["quality"], "partial")
            self.assertEqual(first["counts"]["nist"]["received"], 1)
            self.assertEqual(first["counts"]["nqsn"]["received"], 0)
            self.assertEqual(len(first["digest"]), 64)
            self.assertRegex(first["coefficient"], r"^1\.\d{6}$")
            self.assertEqual(hashlib.sha256(canonical(store.get_manifest(day))).hexdigest(), first["digest"])
            self.assertEqual(set(store.get_manifest(day)["sources"]), {"nist", "nqsn", "noaa_mag", "noaa_wind"})
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

    def test_v2_manifest_freezes_enabled_source_set(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "v2.json"
            config.write_text(json.dumps({"start_day_utc": "2026-10-20",
                                          "disabled_groups": ["opensky"],
                                          "disabled_sources": ["ge_ape"]}), encoding="utf-8")
            store = Store(Path(folder) / "v2.sqlite3", config)
            with store.connect() as db:
                db.execute("UPDATE meta SET value='2026-10-19T00:00:00Z' WHERE key='started_at'")
            event = "2026-10-20T00:00:00Z"
            store.add_observation("nist", event, event,
                                  {"value": "a" * 128, "chain": 1, "index": 1}, {}, "f" * 64, "test")
            store.add_observation("ge_acrg", event, event, {"data_b64": "sample"}, {}, "f" * 64, "test")
            sealed = store.finalize_day("2026-10-20")
            manifest = store.get_manifest("2026-10-20")
            self.assertEqual(manifest["format"], "timelinestamp-v2")
            self.assertIn("ge_acrg", manifest["sources"])
            self.assertNotIn("ge_ape", manifest["sources"])
            self.assertNotIn("air_alps", manifest["sources"])
            self.assertEqual(sealed["counts"]["ge_acrg"], {"received": 1, "expected": 24})
            self.assertEqual(sealed["quality"], "partial")
            self.assertEqual(hashlib.sha256(canonical(manifest)).hexdigest(), sealed["digest"])
            config.write_text(json.dumps({"start_day_utc": "2026-10-20", "disabled_groups": [],
                                          "disabled_sources": []}), encoding="utf-8")
            self.assertEqual(store.finalize_day("2026-10-20"), sealed)

    def test_hour_selection_uses_first_valid_reading_in_first_half_hour(self):
        day = "2026-10-20"
        base = datetime(2026, 10, 20, tzinfo=timezone.utc)
        rows = [(base + timedelta(minutes=12), {"v": 2}),
                (base + timedelta(minutes=3), {"v": 1}),
                (base + timedelta(minutes=31), {"v": 3})]
        selected = _hour_samples(rows, day)
        self.assertEqual(selected[iso(base)]["data"], {"v": 1})
        self.assertEqual(len(selected), 1)

    def test_ndbc_response_reused_across_backfill_days(self):
        body = (b"#YY MM DD hh mm WDIR WSPD\n#yr mo dy hr mn deg m/s\n"
                b"2026 10 20 00 10 090 5.0\n2026 10 21 00 10 100 6.0\n")
        with patch("v2_sources.get", return_value=(body, "a" * 64, 200, 0.1)) as fetch:
            cache = {}
            first, first_receipt = daily_samples(SOURCE_BY_ID["buoy_41040"], "2026-10-20", response_cache=cache)
            second, second_receipt = daily_samples(SOURCE_BY_ID["buoy_41040"], "2026-10-21", response_cache=cache)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(first["2026-10-20T00:00:00Z"]["data"]["fields"]["WSPD"], "5.0")
        self.assertEqual(second["2026-10-21T00:00:00Z"]["data"]["fields"]["WSPD"], "6.0")
        self.assertFalse(first_receipt["reused_in_cycle"])
        self.assertTrue(second_receipt["reused_in_cycle"])

    def test_intermagnet_accepts_missing_scalar_with_valid_vector(self):
        slot = datetime(2026, 10, 23, 8, 0, tzinfo=timezone.utc)
        body = b"2026-10-23T08:00Z,21004.7000,1316.1300,43853.3600,99999.0000\n"
        with patch("v2_sources.get", return_value=(body, "a" * 64, 200, 0.1)):
            value, _ = live_sample(SOURCE_BY_ID["im_bfo"], slot)
        self.assertEqual(value["components_nT"], ["21004.7000", "1316.1300", "43853.3600", None])

    def test_v2_seals_only_after_delayed_sources_have_window(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "v2.json"
            config.write_text(json.dumps({"start_day_utc": "2026-10-20",
                                          "disabled_groups": [], "disabled_sources": []}), encoding="utf-8")
            store = Store(Path(folder) / "v2.sqlite3", config)
            with store.connect() as db:
                db.execute("UPDATE meta SET value='2026-10-19T00:00:00Z' WHERE key='started_at'")
            collector = Collector(store)
            collector.finalize_due_days(datetime(2026, 10, 23, 0, 14, tzinfo=timezone.utc))
            self.assertFalse(store.day_exists("2026-10-20"))
            collector.finalize_due_days(datetime(2026, 10, 23, 0, 15, tzinfo=timezone.utc))
            self.assertEqual(store.get_manifest("2026-10-20")["format"], "timelinestamp-v2")


if __name__ == "__main__":
    unittest.main()
