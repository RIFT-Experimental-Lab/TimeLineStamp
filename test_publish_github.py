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

    def test_github_update_uses_existing_sha_and_private_token_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            store = Store(root / "test.sqlite3")
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
            self.assertEqual(body["author"], COMMIT_IDENTITY)
            self.assertEqual(body["committer"], COMMIT_IDENTITY)
            snapshot = json.loads(base64.b64decode(body["content"]))
            self.assertEqual(snapshot["format"], "timelinestamp-status-v1")
            self.assertNotIn("test-token", json.dumps(snapshot))

            token_file.chmod(0o644)
            with self.assertRaises(PermissionError):
                publisher.publish_once()


if __name__ == "__main__":
    unittest.main()
