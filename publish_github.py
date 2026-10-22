"""Publish a small, public snapshot without exposing the phone or its database."""

from __future__ import annotations

import base64
import json
import logging
import re
import stat
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from timelinestamp import SOURCE_NAMES, Store, canonical, iso, utc_now


LOG = logging.getLogger("timelinestamp.publisher")
PUBLIC_PATH = "docs/data/status.json"
COMMIT_IDENTITY = {
    "name": "AntonKreighoff",
    "email": "346522204+AntonKreighoff@users.noreply.github.com",
}


class _NoRedirect(HTTPRedirectHandler):
    # Never forward the repository token to a different URL.
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def public_status(store: Store, now: datetime) -> dict:
    return {
        "format": "timelinestamp-status-v1",
        "published_at": iso(now),
        "first_full_day": store.first_full_day(),
        "current": store.latest_day(),
        "history": store.history(30),
        "progress": store.progress(),
        "source_names": SOURCE_NAMES,
    }


class GitHubPublisher:
    def __init__(self, store: Store, repo: str, token_file: Path, *, api_base: str = "https://api.github.com"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("Expected GitHub repository as OWNER/REPO")
        self.store = store
        self.repo = repo
        self.token_file = token_file.expanduser()
        self.url = f"{api_base}/repos/{repo}/contents/{PUBLIC_PATH}"
        self.opener = build_opener(_NoRedirect())
        self.stop = threading.Event()

    def _token(self) -> str:
        mode = stat.S_IMODE(self.token_file.stat().st_mode)
        if mode & 0o077:
            raise PermissionError(f"Token file must be private (chmod 600): {self.token_file}")
        token = self.token_file.read_text(encoding="utf-8").strip()
        if not token:
            raise ValueError("GitHub token file is empty")
        return token

    def _request(self, token: str, method: str, body: dict | None = None) -> dict:
        data = canonical(body) if body is not None else None
        request = Request(self.url, data=data, method=method, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Timelinestamp/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with self.opener.open(request, timeout=20) as response:
            return json.loads(response.read(1_000_001))

    def _current_sha(self, token: str) -> str | None:
        try:
            return self._request(token, "GET")["sha"]
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    def publish_once(self) -> None:
        token = self._token()
        snapshot = public_status(self.store, utc_now())
        content = base64.b64encode(canonical(snapshot) + b"\n").decode("ascii")
        body = {
            "message": "Update Timelinestamp status " + snapshot["published_at"],
            "content": content,
            "branch": "main",
            "author": COMMIT_IDENTITY,
            "committer": COMMIT_IDENTITY,
        }
        for attempt in range(2):
            sha = self._current_sha(token)
            if sha is not None:
                body["sha"] = sha
            else:
                body.pop("sha", None)
            try:
                self._request(token, "PUT", body)
                LOG.info("Published status to %s (%s)", self.repo, snapshot["published_at"])
                return
            except HTTPError as exc:
                if exc.code != 409 or attempt:
                    raise

    def run(self) -> None:
        next_due = 0.0
        last_attempt_day: str | None = None
        has_attempted = False
        while not self.stop.is_set():
            current = self.store.latest_day()
            day = current["day"] if current else None
            if time.monotonic() >= next_due or (has_attempted and day != last_attempt_day):
                last_attempt_day = day
                has_attempted = True
                try:
                    self.publish_once()
                    next_due = time.monotonic() + 3600
                except Exception as exc:
                    LOG.warning("GitHub publication failed: %s", exc)
                    next_due = time.monotonic() + 300
            self.stop.wait(30)
