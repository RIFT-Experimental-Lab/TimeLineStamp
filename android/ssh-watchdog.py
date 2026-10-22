"""Keep phone SSH available on the configured Wi-Fi address only."""

import fcntl
import logging
from logging.handlers import RotatingFileHandler
import re
import subprocess
import time
from pathlib import Path


HOME = Path.home()
CONFIG = HOME / ".config/timelinestamp/ssh.env"
SSHD_CONFIG = HOME / ".config/timelinestamp/sshd_config"
STATE = HOME / ".local/state/timelinestamp"


def main():
    match = re.fullmatch(r"TIMELINESTAMP_SSH_BIND=((?:10|172|192)\.[0-9.]+)\n?", CONFIG.read_text())
    if match is None:
        raise SystemExit("Invalid SSH address configuration")
    address = match.group(1)
    STATE.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[RotatingFileHandler(STATE / "ssh-supervisor.log", maxBytes=1_000_000,
                                                      backupCount=2)])
    with (STATE / "ssh-supervisor.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        command = ["sshd", "-D", "-e", "-f", str(SSHD_CONFIG)]
        while True:
            logging.info("Starting SSH on %s:8022", address)
            try:
                with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, errors="replace") as process:
                    for line in process.stdout:
                        logging.info("sshd: %s", line.rstrip())
                    logging.warning("SSH exited with code %s; retrying in 30 seconds", process.wait())
            except OSError:
                logging.exception("Could not start SSH; retrying in 30 seconds")
            time.sleep(30)


if __name__ == "__main__":
    main()
