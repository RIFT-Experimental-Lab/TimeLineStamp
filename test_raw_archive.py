import io
import json
import tempfile
import threading
import tarfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from raw_archive import ArchiveServer, ArchiveUnavailable, available_days, build_archive
from timelinestamp import Store


class RawArchiveTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.store = Store(self.root / "data.sqlite3")
        event = "2026-10-23T00:00:00Z"
        self.store.add_observation("nist", event, event, {"value": "a" * 128}, {"pulse": "raw-day-one"}, "f" * 64, "https://secret.invalid/?token=never-export")
        self.record = self.store.finalize_day("2026-10-23")
        self.store.add_observation("nist", "2026-10-24T00:00:00Z", None, {}, {"secret": "unsealed-next-day"}, "f" * 64, "private")

    def tearDown(self):
        self.folder.cleanup()

    def test_export_reproduces_sealed_input_and_omits_other_dates_and_urls(self):
        archive = build_archive(self.store.path, "2026-10-23", self.root / "cache")
        with tarfile.open(archive) as tar:
            self.assertEqual(set(tar.getnames()), {"manifest.json", "record.json", "archive.json", "observations.jsonl"})
            manifest = json.load(tar.extractfile("manifest.json"))
            observations = tar.extractfile("observations.jsonl").read()
            record = json.load(tar.extractfile("record.json"))
        self.assertEqual(manifest, self.store.get_manifest("2026-10-23"))
        self.assertEqual(record["digest"], self.record["digest"])
        self.assertIn(b"raw-day-one", observations)
        self.assertNotIn(b"unsealed-next-day", observations)
        self.assertNotIn(b"secret.invalid", observations)
        self.assertNotIn(b"never-export", observations)
        self.assertEqual(archive, build_archive(self.store.path, "2026-10-23", self.root / "cache"))
        self.assertEqual(self.store.get_day("2026-10-23"), self.record)

    def test_late_shadow_samples_get_new_revision_without_changing_daily_digest(self):
        first = build_archive(self.store.path, "2026-10-23", self.root / "cache")
        self.store.add_observation("ge_acrg", "2026-10-23T01:00:00Z", None, {"data_b64": "later"}, {}, "e" * 64, "private")
        second = build_archive(self.store.path, "2026-10-23", self.root / "cache")
        self.assertNotEqual(first.name, second.name)
        self.assertEqual(self.store.get_day("2026-10-23"), self.record)

    def test_public_http_is_read_only_and_only_closed_dates_are_exported(self):
        server = ArchiveServer(("127.0.0.1", 0), self.store.path, self.root / "cache")
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/v1/catalog") as response:
                self.assertEqual(response.headers["Access-Control-Allow-Origin"], "*")
                self.assertEqual([r["day"] for r in json.load(response)["days"]], ["2026-10-23"])
            with urlopen(base + "/v1/day/2026-10-23.tar.gz") as response:
                self.assertIn("attachment", response.headers["Content-Disposition"])
                with tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:gz") as tar:
                    self.assertIn("manifest.json", tar.getnames())
            for path in ("/api/status", "/../config", "/v1/day/2026-10-24.tar.gz", "/v1/day/2026-99-99.tar.gz"):
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + path)
                self.assertEqual(error.exception.code, 404)
            server.transfers.acquire(); server.transfers.acquire()
            try:
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + "/v1/day/2026-10-23.tar.gz")
                self.assertEqual(error.exception.code, 429)
            finally:
                server.transfers.release(); server.transfers.release()
        finally:
            server.shutdown(); server.server_close(); worker.join()

    def test_missing_raw_and_corrupt_manifest_are_not_served(self):
        with self.assertRaises(ArchiveUnavailable):
            build_archive(self.store.path, "2026-10-24", self.root / "cache")
        with self.store.connect() as db:
            db.execute("UPDATE days SET manifest='{}'")
        with self.assertRaisesRegex(ArchiveUnavailable, "digest"):
            build_archive(self.store.path, "2026-10-23", self.root / "cache")


if __name__ == "__main__":
    unittest.main()
