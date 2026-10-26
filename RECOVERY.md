# Recovery and public day archives

The collector can move to a replacement Android device with either a full compressed SQLite backup or only published state from GitHub. Published state retains daily hashes, coefficients, quality, counts, source settings, and all saved period digests. It contains no observations or secrets. Daily status commits now include this complete recovery state; older history is reconstructed from every Git revision of `docs/data/status.json`.

## Replacement procedure

Stop the old collector before starting a replacement. If the old device is lost, revoke its GitHub token and issue a new repository-scoped token under the laboratory account. The transfer ZIP deliberately excludes GitHub tokens, SSH keys and tunnel credentials. Two active publishers must not collect competing records for the same day.

Install Termux and Termux:Boot from the same signing source. Official installation information: [Termux](https://github.com/termux/termux-app#installation), [Termux:Boot](https://github.com/termux/termux-boot). Open both, grant Termux shared storage, and enable Android autostart and unrestricted battery operation. The included APKs, when present, are the pair previously downloaded for this installation; the bundle records their SHA-256. The bundle is not an offline Python/package mirror.

Extract the complete ZIP into Android Downloads and follow `START_HERE_RU.txt`. `android/recover-on-phone.sh` installs Python, Git and OpenSSH, obtains the latest published state over HTTPS (or reads complete Git history for older publishers), restores a new database and installs the boot script. It refuses to overwrite an existing database. A full backup can be passed as its first argument; newer published records missing from that backup are merged from Git. Source settings come from the latest checkpoint, or the reviewed bundle fallback for older publishers. Test enabled sources again on the replacement network.

Published hashes and already closed codes remain identical. Restored metadata lives in a separate `recovered_days` table; missing raw observations and manifests are never fabricated. New full-day collection begins on the next UTC day after recovery. An interrupted period remains a gap, so a month that spans lost days may be unavailable. Recovered daily hashes still contribute to future monthly/yearly aggregation when every required day exists.

For a manual metadata restore:

```sh
python recovery.py fetch-state --output /private/path/recovery.json
python recovery.py restore --state /private/path/recovery.json --db /private/path/new.sqlite3
```

Build a refreshed bundle on the Mac after fetching the repository history:

```sh
git fetch origin main
git merge --ff-only origin/main
python android/build-recovery-bundle.py --output /private/path/TimeLineStamp-recovery.zip --v2-config /private/path/v2-sources.json --termux-apk /private/path/Termux.apk --boot-apk /private/path/TermuxBoot.apk
```

The APK arguments are optional. `bundle-manifest.json` checksums every included file; a companion SHA-256 checks the ZIP. Keep a refreshed copy outside the server. A bundled checkpoint is only current as of its build; recovery fetches newer published state before starting.

## Public download service

`raw_archive.py` exposes only `/health`, `/v1/catalog`, and `/v1/day/YYYY-MM-DD.tar.gz`. It reads SQLite in read-only mode with a consistent transaction, verifies the sealed manifest, and streams a compressed archive. Unsealed days and metadata-only recovered dates have no raw download. Archives omit stored request URLs and all server configuration. They include stored raw source entries or normalized payloads; they do not claim to contain the original bytes of every HTTP response.

The fixed `manifest.json` reproduces the published daily SHA-256. `observations.jsonl` also includes stored shadow samples. Such samples may arrive after a daily seal; a subsequent export has a different revision when more observations arrive. A revision is a snapshot, not an assertion that every possible source sample is already present. The cache is limited to 256 MiB, a build to 512 MiB uncompressed, and simultaneous downloads/builds to two. Eight HTTP clients are admitted. Oversized days return an unavailable error rather than filling the device.

`public_downloads.py` binds that service to loopback and supervises an outbound Cloudflare Quick Tunnel. It verifies the public health response before publishing the HTTPS URL in `docs/data/downloads.json`, using the existing restricted GitHub token and laboratory commit identity. A new tunnel URL causes one small endpoint commit; no raw data is uploaded to GitHub. The website retrieves this address and checks the day catalog before requesting the download. Collector restarts do not stop an already running download service.

On the collecting phone, after deploying this code:

```sh
sh ~/TimeLineStamp/android/enable-downloads.sh
```

This installs the [Termux cloudflared package](https://github.com/termux/termux-packages/tree/master/packages/cloudflared), enables startup, and starts the service. [Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) require neither a domain nor an account, but are intended for testing, change hostname after restart, and provide no uptime guarantee. This is an experimental route, not a guaranteed worldwide service. Availability must be checked from the actual collecting network and a second independent network before declaring it operational. The website remains available if downloads are offline. A stable production route can later replace this transport.

Do not point the tunnel at the collector's local management API or SSH. Logs are under `~/.local/state/timelinestamp/downloads.log`; the archive service does not persist visitor IPs. Do not run a second copy of the boot shell to enable downloads: the enable script starts only the separate archive supervisor.
