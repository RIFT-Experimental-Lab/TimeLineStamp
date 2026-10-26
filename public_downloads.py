"""Supervise a read-only archive endpoint and an account-free outbound Quick Tunnel."""
from __future__ import annotations

import argparse
import base64
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import queue
import re
import signal
import subprocess
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from publish_github import GitHubPublisher, COMMIT_IDENTITY
from raw_archive import ArchiveServer
from timelinestamp import canonical, iso, utc_now


LOG = logging.getLogger("timelinestamp.downloads")
TUNNEL_URL = re.compile(r"https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com\b")


def publish_endpoint(repo, token_file, endpoint):
    if not TUNNEL_URL.fullmatch(endpoint):
        raise ValueError("Expected a Quick Tunnel HTTPS endpoint")
    publisher = GitHubPublisher(None, repo, token_file)
    publisher.url = f"https://api.github.com/repos/{repo}/contents/docs/data/downloads.json"
    token = publisher._token()
    for attempt in range(2):
        try:
            current = publisher._request(token, "GET")
        except HTTPError as exc:
            if exc.code != 404:
                raise
            current = {}
        if current.get("content"):
            previous = json.loads(base64.b64decode(current["content"]))
            if previous.get("base_url") == endpoint and previous.get("format") == "timelinestamp-downloads-v1":
                return
        now = iso(utc_now())
        body = {"message": "Update archive endpoint " + now,
                "content": base64.b64encode(canonical({"format": "timelinestamp-downloads-v1", "base_url": endpoint,
                                                       "updated_at": now}) + b"\n").decode(),
                "branch": "main", "author": {**COMMIT_IDENTITY, "date": now},
                "committer": {**COMMIT_IDENTITY, "date": now}}
        if current.get("sha"):
            body["sha"] = current["sha"]
        try:
            publisher._request(token, "PUT", body)
            return
        except HTTPError as exc:
            if exc.code != 409 or attempt:
                raise


def relay_output(process, messages):
    for line in process.stdout:
        line = line.strip()[:2000]
        LOG.info("tunnel: %s", line)
        match = TUNNEL_URL.search(line)
        if match:
            try:
                messages.put_nowait(match[0])
            except queue.Full:
                pass


def healthy(endpoint):
    with urlopen(endpoint + "/health", timeout=12) as response:
        return json.loads(response.read(1000)).get("format") == "timelinestamp-archive-health-v1"


def run(args, stop):
    args.state_dir.mkdir(parents=True, exist_ok=True)
    server = ArchiveServer(("127.0.0.1", args.port), args.db, args.state_dir / "archive-cache")
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    LOG.info("Read-only archive server listening on loopback port %d", args.port)
    child = None
    try:
        while not stop.is_set():
            if args.local_only:
                stop.wait(1)
                continue
            messages = queue.Queue(maxsize=4)
            try:
                child = subprocess.Popen([args.cloudflared, "tunnel", "--no-autoupdate", "--protocol", "http2",
                                          "--url", f"http://127.0.0.1:{args.port}"],
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                reader = threading.Thread(target=relay_output, args=(child, messages), daemon=True)
                reader.start()
                endpoint, published, retry, check_at, failures = None, False, 0, 0, 0
                while not stop.is_set() and child.poll() is None:
                    try:
                        value = messages.get(timeout=2)
                        if value != endpoint:
                            endpoint, published, retry = value, False, 0
                    except queue.Empty:
                        pass
                    if endpoint and not published and time.monotonic() >= retry:
                        retry = time.monotonic() + 30
                        try:
                            if healthy(endpoint):
                                publish_endpoint(args.repo, args.token_file, endpoint)
                                published = True
                                check_at = time.monotonic() + 300
                                LOG.info("Public archive endpoint verified and announced")
                        except Exception as exc:
                            LOG.warning("Archive endpoint is not announced yet: %s", type(exc).__name__)
                    if endpoint and published and time.monotonic() >= check_at:
                        check_at = time.monotonic() + 300
                        try:
                            failures = 0 if healthy(endpoint) else failures + 1
                        except Exception:
                            failures += 1
                        if failures >= 3:
                            LOG.warning("Tunnel health checks failed; creating a new tunnel")
                            break
                LOG.warning("Tunnel stopped; retrying shortly")
            except OSError as exc:
                LOG.warning("Cannot run tunnel: %s", exc)
            finally:
                if child is not None and child.poll() is None:
                    child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)
                child = None
            stop.wait(30)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".local/state/timelinestamp")
    parser.add_argument("--token-file", type=Path, default=Path.home() / ".config/timelinestamp/github-token")
    parser.add_argument("--repo", default="RIFT-Experimental-Lab/TimeLineStamp")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--cloudflared", default="cloudflared")
    parser.add_argument("--local-only", action="store_true")
    args = parser.parse_args()
    args.state_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=[
        RotatingFileHandler(args.state_dir / "downloads.log", maxBytes=1_000_000, backupCount=2)])
    with (args.state_dir / "downloads.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.exit(message="Downloads supervisor already runs\n")
        stop = threading.Event()
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: stop.set())
        while not stop.is_set():
            try:
                run(args, stop)
            except Exception:
                LOG.exception("Downloads supervisor failed; restarting")
                stop.wait(60)


if __name__ == "__main__":
    main()
