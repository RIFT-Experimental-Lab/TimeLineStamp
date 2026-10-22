# TimeLineStamp

**A daily fingerprint of physical events.** TimeLineStamp records public measurements from two quantum randomness beacons and two solar wind streams. At the end of each UTC day, it turns that record into a SHA-256 fingerprint and a short number that a person can remember.

**[Open the live TimeLineStamp page](https://rift-experimental-lab.github.io/TimeLineStamp/)** · [Public status data](https://rift-experimental-lab.github.io/TimeLineStamp/data/status.json)

## The experiment

Imagine that an intervention in the past changes the course of a day. Some physical measurements made during that day might then have different outcomes. TimeLineStamp gives each completed day one number to compare with memory.

If you remember a different number **for the same UTC date** than the one shown now, write to [rift.research@outlook.com](mailto:rift.research@outlook.com). Include the date, the number you remember, and the number currently on the page. The report can rest on memory alone; the experiment looks for precisely that kind of discrepancy. A daily difference cannot reveal when a possible change occurred.

The [public page](https://rift-experimental-lab.github.io/TimeLineStamp/) explains the timeline model, the choice of measurements, the calculation, and each source in English, Russian, and Chinese. English is the default language.

## How a daily record is made

1. Every five minutes, the collector selects one pulse from each of the [NIST Randomness Beacon](https://csrc.nist.gov/Projects/interoperable-randomness-beacons/beacon-20) and the [NQSN Beacon](https://quantum-entropy.sg/api/beacon/). It also collects one-minute magnetic field and plasma measurements from [NOAA SWPC](https://www.swpc.noaa.gov/products/real-time-solar-wind).
2. The server stores accepted measurements, raw source entries, and HTTP response hashes in SQLite. Missing beacon slots remain explicit gaps; old periods are not silently filled later.
3. At **00:15 UTC** on the following day, it seals the previous UTC day's record. The first seal follows the first *full* day of collection. A sealed day is not recalculated during normal operation.
4. The canonical daily manifest is hashed with SHA-256. A deterministic, unbiased mapping turns the digest into a coefficient of the form `1.xxxxxx`. The coefficient is a short memory aid; the full SHA-256 digest identifies the record more precisely.

Version 1 expects 288 pulses per beacon and up to 1,440 one-minute entries per NOAA stream per day. It marks substantial gaps as incomplete. If both quantum streams are entirely absent, it keeps the hash but does not issue a coefficient. The calculation is implemented in `Store.finalize_day` in [timelinestamp.py](timelinestamp.py).

## What the public page shows

The site in [`docs/`](docs/) is static. When publication is enabled, the server sends a small JSON snapshot to GitHub: the latest sealed record, up to 30 recent days, current collection counts, and the publication time. The page shows a waiting state until a daily record exists and marks delayed updates.

Raw source entries, the SQLite database, and the canonical manifests stay on the server. A complete manifest can be read from the local API for recalculation; it is not part of the public JSON snapshot. The browser never connects directly to the server.

The design source and fictional demonstration data live in [`demo/`](demo/). To rebuild both the offline demo and the public HTML after a design change, run:

```sh
python3 demo/build_public.py
```

Deployment details are in [GITHUB_PAGES.md](GITHUB_PAGES.md). The unattended Android setup is in [ANDROID.md](ANDROID.md).

## Run the collector locally

Python 3.9 or newer is required. The collector uses the Python standard library and needs internet access to reach the sources. Run these commands from the repository root.

```sh
# Collect without a local web interface.
python3 timelinestamp.py --headless

# Inspect the current database and collection progress.
python3 timelinestamp.py --status
```

To enable the local web interface and API, run `python3 timelinestamp.py` and open `http://127.0.0.1:8765` **on the same device**. It binds to the loopback address by default. The database path can be changed with `--db`; the default is `../local/data/timelinestamp.sqlite3` when a sibling `local/` directory exists, or `data/timelinestamp.sqlite3` otherwise.

For a one-off source check, run `python3 test_now.py` or `./test_now.command` on macOS. It prints a **test snapshot**, not a sealed daily coefficient.

Optional `--backup-dir` and `--log-file` arguments enable two rotating compressed database backups and a size-limited log. To publish the status snapshot, supply `--publish-repo RIFT-Experimental-Lab/TimeLineStamp` and `--token-file /path/to/github-token`. Keep the token outside the repository with file mode `0600`.

### Local API

- `/api/status` — latest record, recent history, and current collection progress.
- `/api/day/YYYY-MM-DD` — digest, coefficient, quality, and source counts for one day.
- `/api/day/YYYY-MM-DD/manifest` — the canonical inputs used to calculate that day's digest.

## Source handling

Beacon pulses are checked for their expected timestamp, the presence of indices, and normal status. NOAA rows are accepted only when active, with overall quality flag `0` and numeric values. Version 1 does not cryptographically verify beacon signatures. If a source format changes, the calculation rules need a new version; previously sealed records remain as they were.

The measurements belong to their respective operators. TimeLineStamp records their published outputs and does not control the sources.
