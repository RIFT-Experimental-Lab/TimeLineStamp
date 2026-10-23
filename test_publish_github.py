import base64
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from publish_github import COMMIT_IDENTITY, GitHubPublisher, public_status
from timelinestamp import Store, canonical


class PublishingTests(unittest.TestCase):
    def test_public_status_contains_no_raw_measurements(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "test.sqlite3")
            day = "2026-10-20"
            event = day + "T00:00:00Z"
            store.add_observation("nist", event, event, {"value": "a" * 128, "chain": 1, "index": 1},
                                  {"secret_raw_response": "must stay on phone"}, "f" * 64, "https://example.test")
            store.finalize_day(day)
            status = public_status(store, datetime(2026, 10, 22, tzinfo=timezone.utc))
            encoded = canonical(status)
            self.assertEqual(status["current"]["day"], day)
            self.assertEqual(len(status["history"]), 1)
            self.assertNotIn(b"must stay on phone", encoded)
            self.assertNotIn(b"manifest", encoded)
            self.assertNotIn(b"example.test", encoded)
            self.assertNotIn(b"progress", encoded)

    def test_shadow_source_count_is_public_without_raw_observations(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "v2.json"
            config.write_text(json.dumps({"shadow_start_day_utc": "2026-10-23",
                                          "start_day_utc": None,
                                          "disabled_groups": ["ndbc", "usgs", "ea", "osm"],
                                          "disabled_sources": []}), encoding="utf-8")
            store = Store(Path(folder) / "test.sqlite3", config)
            status = public_status(store, datetime(2026, 10, 23, tzinfo=timezone.utc))
            self.assertEqual(status["v2_shadow_start_day_utc"], "2026-10-23")
            self.assertIsNone(status["v2_start_day_utc"])
            self.assertEqual(status["v2_enabled_source_count"], 23)
            self.assertNotIn("progress", status)

    def test_github_update_uses_existing_sha_and_private_token_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = Store(root / "test.sqlite3")
            store.finalize_day("2026-10-20")
            token_file = root / "token"
            token_file.write_text("test-token\n", encoding="utf-8")
            token_file.chmod(0o600)
            requests = []

            def fake_urlopen(request, timeout):
                requests.append(request)
                if request.get_method() == "GET":
                    return io.BytesIO(b'{"sha":"old-file-sha"}')
                return io.BytesIO(b'{"commit":{"sha":"new-commit-sha"}}')

            publisher = GitHubPublisher(store, "owner/repo", token_file)
            with patch.object(publisher.opener, "open", side_effect=fake_urlopen):
                publisher.publish_once()
            self.assertEqual([req.get_method() for req in requests], ["GET", "PUT"])
            self.assertTrue(requests[1].full_url.endswith("/repos/owner/repo/contents/docs/data/status.json"))
            self.assertEqual(requests[1].get_header("Authorization"), "Bearer test-token")
            body = json.loads(requests[1].data)
            self.assertEqual(body["sha"], "old-file-sha")
            self.assertEqual({key: body["author"][key] for key in COMMIT_IDENTITY}, COMMIT_IDENTITY)
            self.assertEqual(body["author"], body["committer"])
            self.assertRegex(body["author"]["date"], r"Z$")
            snapshot = json.loads(base64.b64decode(body["content"]))
            self.assertEqual(snapshot["format"], "timelinestamp-status-v1")
            self.assertEqual(snapshot["current"]["day"], "2026-10-20")
            self.assertNotIn("progress", snapshot)
            self.assertNotIn("test-token", json.dumps(snapshot))

            token_file.chmod(0o644)
            with self.assertRaises(PermissionError):
                publisher.publish_once()

    def test_only_newly_sealed_days_are_published(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = Store(root / "test.sqlite3")
            token_file = root / "token"
            token_file.write_text("test-token\n", encoding="utf-8")
            token_file.chmod(0o600)
            publisher = GitHubPublisher(store, "owner/repo", token_file)
            requests = []

            def fake_urlopen(request, timeout):
                requests.append(request.get_method())
                if request.get_method() == "GET":
                    old = {"format": "timelinestamp-status-v1", "current": {"day": "2026-10-20"}}
                    encoded = base64.b64encode(canonical(old)).decode()
                    return io.BytesIO(canonical({"sha": "old-file-sha", "content": encoded}))
                return io.BytesIO(b'{"commit":{"sha":"new-commit-sha"}}')

            with patch.object(publisher.opener, "open", side_effect=fake_urlopen):
                self.assertIsNone(publisher.publish_new_day())
                self.assertEqual(requests, [])
                store.finalize_day("2026-10-20")
                self.assertEqual(publisher.publish_new_day(), "2026-10-20")
                self.assertEqual(requests, ["GET"])
                store.finalize_day("2026-10-21")
                self.assertEqual(publisher.publish_new_day(), "2026-10-21")
                self.assertEqual(requests, ["GET", "GET", "GET", "PUT"])

    def test_publisher_does_not_repeat_a_day_during_normal_operation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = Store(root / "test.sqlite3")
            store.finalize_day("2026-10-20")
            publisher = GitHubPublisher(store, "owner/repo", root / "token")
            with patch.object(publisher.stop, "is_set", side_effect=[False, False, False, True]), \
                 patch.object(publisher.stop, "wait"), \
                 patch.object(publisher, "publish_new_day", return_value="2026-10-20") as publish:
                publisher.run()
            publish.assert_called_once()


if __name__ == "__main__":
    unittest.main()
