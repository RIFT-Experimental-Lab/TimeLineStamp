# TimeLineStamp

**A daily fingerprint of physical events.** TimeLineStamp records public measurements from two quantum randomness beacons and two solar wind streams. At the end of each UTC day, it turns that record into a SHA-256 fingerprint and a short number that a person can remember.

**[Open the live TimeLineStamp page](https://rift-experimental-lab.github.io/TimeLineStamp/)** · [Public status data](https://rift-experimental-lab.github.io/TimeLineStamp/data/status.json)

An [Android home screen widget](https://rift-experimental-lab.github.io/TimeLineStamp/#android-widget)
displays the latest sealed daily number, its UTC date, and data completeness.
[Download the APK](https://rift-experimental-lab.github.io/TimeLineStamp/downloads/TimeLineStamp-widget-android-0.2.1.apk)
for Android 8 or newer. The interface is in English and the last reading stays
available offline. See the [widget guide](widgets/android/README.md) for installation and source code.

## The experiment

Imagine that an intervention in the past changes the course of a day. Some physical measurements made during that day might then have different outcomes. TimeLineStamp gives each completed day one number to compare with memory.

If you remember a different number **for the same UTC date** than the one shown now, write to [rift.research@outlook.com](mailto:rift.research@outlook.com). Include the date, the number you remember, and the number currently on the page. The report can rest on memory alone; the experiment looks for precisely that kind of discrepancy. A daily difference cannot reveal when a possible change occurred.

The page also shows secondary period codes below the daily coefficient. Six hexadecimal marks divide a sealed day into four-hour UTC intervals. A week has seven daily marks, a month has four two-character marks for days 1–7, 8–14, 15–21, and 22–end, and a year has twelve monthly marks. Week, month, and year fill as their component records are sealed. The day code appears all at once after the daily seal. A difference in a short mark can narrow the differing measurement interval; it does not establish when an intervention occurred.

The [public page](https://rift-experimental-lab.github.io/TimeLineStamp/) explains the timeline model, the choice of measurements, the calculation, and each source in English, Russian, and Chinese. English is the default language.

## How a daily record is made

1. Every five minutes, the collector selects one pulse from each of the [NIST Randomness Beacon](https://csrc.nist.gov/Projects/interoperable-randomness-beacons/beacon-20) and the [NQSN Beacon](https://quantum-entropy.sg/api/beacon/). It also collects one-minute magnetic field and plasma measurements from [NOAA SWPC](https://www.swpc.noaa.gov/products/real-time-solar-wind).
2. The server stores accepted measurements, raw source entries, and HTTP response hashes in SQLite. Missing beacon slots remain explicit gaps; old periods are not silently filled later.
3. At **00:15 UTC** on the following day, it seals the previous UTC day's record. The first seal follows the first *full* day of collection. A sealed day is not recalculated during normal operation.
4. The canonical daily manifest is hashed with SHA-256. A deterministic, unbiased mapping turns the digest into a coefficient of the form `1.xxxxxx`. The coefficient is a short memory aid; the full SHA-256 digest identifies the record more precisely.

Version 1 expects 288 pulses per beacon and up to 1,440 one-minute entries per NOAA stream per day. It marks substantial gaps as incomplete. If both quantum streams are entirely absent, it keeps the hash but does not issue a coefficient. The calculation is implemented in `Store.finalize_day` in [timelinestamp.py](timelinestamp.py).

## What the public page shows

The site in [`docs/`](docs/) is static. After each daily seal, the server sends a small JSON snapshot to GitHub: the latest sealed record, up to 30 recent days, and the publication time. It does not publish current collection progress. A separate, fixed [initial snapshot](docs/data/initial.json) was calculated from the measurements collected on 2026-10-22 before the first full UTC day. The page labels its number as incomplete and keeps it in the archive after daily records begin. It is not a daily coefficient. The page marks a daily publication as delayed if the next record does not arrive.

Raw source entries, the SQLite database, and the canonical manifests stay on the server. A complete manifest can be read from the local API for recalculation; it is not part of the public JSON snapshot. The regular page display reads GitHub snapshots; optional archive requests reach the read-only service through an HTTPS tunnel.

An optional read-only archive service lets visitors request a compressed snapshot for a sealed UTC day from the server through an outbound HTTPS tunnel. It includes the sealed manifest and stored observations, including shadow inputs available at export time. The website checks availability when the download is requested. Until that service is connected, the button reports that archives are unavailable. See [RECOVERY.md](RECOVERY.md) for deployment and limitations of the experimental tunnel.

Period codes are derived only from sealed daily records and stored immutably in `period_codes`. The public JSON includes their interval boundaries, full SHA-256 digests, quality, and short marks, but no raw measurements. The selectable HEX 16, BASE32, and BASE58 views derive from the same full digest; pending symbols on the page are visual placeholders and are never published as readings. Dates before the first full collection day remain unavailable.

The initial snapshot uses only observations with event times on its UTC date before `created_at` and with `received_at` strictly before that time. Its manifest format is `timelinestamp-initial-v1`; the SHA-256 digest and short number use the same canonical encoding and coefficient mapping as daily records. The calculation is in [initial_snapshot.py](initial_snapshot.py). Unlike a daily record, it covers only part of a day and is never updated.

The design source and fictional demonstration data live in [`demo/`](demo/). To rebuild both the offline demo and the public HTML after a design change, run:

```sh
python3 demo/build_public.py
```

Deployment details are in [GITHUB_PAGES.md](GITHUB_PAGES.md). The unattended Android setup is in [ANDROID.md](ANDROID.md).

The daily public status also retains a compact recovery checkpoint with all published daily records and closed period digests. A replacement collector can restore those marks without raw observations. [RECOVERY.md](RECOVERY.md) and the locally built transfer bundle cover complete SQLite backups, metadata-only recovery from Git, and restarting on a replacement Android device. Existing published records are preserved; interrupted days remain gaps.

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

- `/api/status` — latest record, recent history, period codes, and current collection progress.
- `/api/day/YYYY-MM-DD` — digest, coefficient, quality, and source counts for one day.
- `/api/day/YYYY-MM-DD/manifest` — the canonical inputs used to calculate that day's digest.

## Source handling

Beacon pulses are checked for their expected timestamp, the presence of indices, and normal status. NOAA rows are accepted only when active, with overall quality flag `0` and numeric values. Version 1 does not cryptographically verify beacon signatures. If a source format changes, the calculation rules need a new version; previously sealed records remain as they were.

The measurements belong to their respective operators. TimeLineStamp records their published outputs and does not control the sources.

## Optional v2 source set

The collector also contains a versioned v2 input set: 34 fixed observation series or areas from 12 public APIs, spanning seismometers, geomagnetic observatories, sea and river gauges, ocean buoys, observed aircraft, Wikimedia pageviews, and OpenStreetMap changes. It can collect in shadow mode without changing the daily number; v2 calculation starts only on a future UTC day set in the local `v2_sources.json` configuration. Existing v1 days keep their original manifest and digest.

Run `python3 probe_v2_sources.py --output /private/path/probe-v2.json` **on the collecting device** to test each endpoint, response structure, and observation freshness from that network. `v2_toggle.py` lists the source IDs and can disable one source or an entire provider without changing code. A v2 day uses fixed UTC slots and seals 48 hours 15 minutes after the end of the day to allow delayed feeds. See [ANDROID.md](ANDROID.md) for deployment commands. The public page still emphasizes the four original streams; v2 counts are retained in the daily record.
