import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from public_downloads import publish_endpoint
from publish_github import COMMIT_IDENTITY
from timelinestamp import canonical


class PublicDownloadsTests(unittest.TestCase):
    def test_announces_only_endpoint_and_uses_laboratory_identity(self):
        requests = []
        def request(_self, token, method, body=None):
            requests.append((method, body))
            return {"sha": "old"} if method == "GET" else {}
        with patch("public_downloads.GitHubPublisher._token", return_value="never-publish-this-token"), \
             patch("public_downloads.GitHubPublisher._request", new=request):
            publish_endpoint("RIFT-Experimental-Lab/TimeLineStamp", Path("/private/token"), "https://sample-test.trycloudflare.com")
        body = requests[-1][1]
        self.assertEqual([method for method, _ in requests], ["GET", "PUT"])
        self.assertEqual(body["author"]["name"], COMMIT_IDENTITY["name"])
        self.assertEqual(body["author"]["email"], COMMIT_IDENTITY["email"])
        content = base64.b64decode(body["content"])
        self.assertNotIn(b"never-publish-this-token", content)
        self.assertNotIn(b"/private", content)

    def test_same_endpoint_does_not_create_repeated_commits(self):
        current = {"sha": "old", "content": base64.b64encode(canonical({
            "format": "timelinestamp-downloads-v1", "base_url": "https://sample-test.trycloudflare.com"})).decode()}
        with patch("public_downloads.GitHubPublisher._token", return_value="test"), \
             patch("public_downloads.GitHubPublisher._request", return_value=current) as request:
            publish_endpoint("RIFT-Experimental-Lab/TimeLineStamp", Path("token"), "https://sample-test.trycloudflare.com")
        request.assert_called_once()

    def test_rejects_other_origins(self):
        for url in ("http://sample.trycloudflare.com", "https://evil.test", "https://sample.trycloudflare.com/secret"):
            with self.assertRaises(ValueError):
                publish_endpoint("RIFT-Experimental-Lab/TimeLineStamp", Path("token"), url)


if __name__ == "__main__":
    unittest.main()
