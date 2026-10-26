# TimeLineStamp Android widget

A native home screen widget for the latest sealed daily fingerprint from
[TimeLineStamp](https://rift-experimental-lab.github.io/TimeLineStamp/).
Android 8.0 or newer. No account, Termux, root, or collector access is required.

## Install

1. [Download the signed APK](https://rift-experimental-lab.github.io/TimeLineStamp/downloads/TimeLineStamp-widget-android-0.2.1.apk) on the phone and open it.
   Allow installation from that file manager or browser when Android asks.
2. Open **TimeLineStamp** and tap **Add to home screen**. Alternatively, hold an
   empty area of the launcher, select **Widgets**, and choose **TimeLineStamp**.
3. Resize the widget as desired. Tap the reading to open the experiment, or **↻**
   to request an update.

The interface is always in English, regardless of the phone's system language. The widget
shows the record's UTC date and completeness, so yesterday's sealed reading is
distinguishable from today's date. It never substitutes a live or initial snapshot.

Background checks are requested every 30 minutes using Android's JobScheduler.
Android and manufacturer battery policies can delay them. Manual requests have a
30 second cooldown. Cached readings survive restarts and connection failures;
the status line identifies offline or failed updates when rendered. A launcher
can retain the last rendered status until the next widget update.

## Data and privacy

Only `https://rift-experimental-lab.github.io/TimeLineStamp/data/status.json` is
requested, over HTTPS. The app checks the record format, UTC closure time,
quality, and decimal coefficient against the published SHA-256 using the
collector's rejection sampling rule. This consistency check is not a digital
signature or proof of the experiment's physical claims.

The last record and request timestamps are stored in private app preferences.
There is no analytics SDK, advertising, login, or device registration. Network
requests expose normal connection metadata to the hosting provider. The APK
signing certificate identifies **RIFT Experimental Lab**.

## Build

No Gradle or third party runtime libraries are used. Install JDK 17 and the
official Android SDK platform 35 and build tools 35.0.0, then run:

```sh
python3 widgets/android/build.py --sdk /path/to/android-sdk --jdk /path/to/jdk17
```

In this workspace, output goes to `local/packages/`, build intermediates to
`local/build/`, and the private release key and password to `local/keys/`.
Paths can be overridden with `--output`, `--build-dir`, and `--private-dir`.
Preserve both signing files privately: future APK updates must use the same key.
Never add them to a repository or distributable bundle.

The SDK's `aapt2`, `javac`, D8, `zipalign`, and `apksigner` build and verify the APK.
The minimum API level is 26 and the target API level is 35.

Run `python3 widgets/android/test.py --jdk /path/to/jdk17` for JVM contract tests
against the collector's published record and coefficient function. The runner
downloads a pinned, SHA-256 checked `org.json` test JAR (20250517) from Maven
Central. This test dependency is not packaged in the app.

## Validation

Version 0.2.1 was exercised on an AOSP Android 15 ARM64 emulator: installation,
real HTTPS status retrieval, launcher pinning, opening the site from the widget,
background job execution, English on non-English system settings, and cached reading retention
after disconnecting the network and restarting the app. The record parser passed
20 JVM contract checks. Background scheduling on a physical phone, including
manufacturer battery restrictions, still needs a device trial.
