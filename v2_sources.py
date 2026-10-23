"""Pinned, removable v2 inputs. No third-party Python packages are required."""

from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


UTC = timezone.utc
USER_AGENT = "TimeLineStamp/2.0 (rift.research@outlook.com)"


@dataclass(frozen=True)
class Source:
    id: str
    group: str
    kind: str
    target: str
    cadence: str = "hour"


SOURCES = (
    Source("ge_acrg", "geofon", "geofon", "ACRG"),
    Source("ge_ape", "geofon", "geofon", "APE"),
    Source("ge_pmg", "geofon", "geofon", "PMG"),
    Source("ge_salta", "geofon", "geofon", "SALTA"),
    Source("nz_tdhs", "geonet", "geonet", "TDHS"),
    Source("im_bfo", "intermagnet", "intermagnet", "bfo"),
    Source("im_hon", "intermagnet", "intermagnet", "hon"),
    Source("im_sit", "intermagnet", "intermagnet", "sit"),
    Source("im_kak", "intermagnet", "intermagnet", "kak"),
    Source("sea_sf", "coops", "coops", "9414290"),
    Source("sea_ny", "coops", "coops", "8518750"),
    Source("sea_hon", "coops", "coops", "1612340"),
    Source("buoy_41040", "ndbc", "ndbc", "41040"),
    Source("buoy_51002", "ndbc", "ndbc", "51002"),
    Source("buoy_46042", "ndbc", "ndbc", "46042"),
    Source("us_potomac", "usgs", "usgs", "USGS-01646500"),
    Source("us_mississippi", "usgs", "usgs", "USGS-07010000"),
    Source("us_colorado", "usgs", "usgs", "USGS-08158000"),
    Source("ca_ottawa", "eccc", "eccc", "02KF005"),
    Source("uk_bourton", "ea", "ea", "1029TH:level-stage"),
    Source("uk_gaw", "ea", "ea", "52119:level-stage"),
    Source("uk_rain", "ea", "ea", "3680:rainfall"),
    Source("uk_temp", "ea", "ea", "3680:temperature"),
    Source("de_bonn", "pegel", "pegel", "593647aa-9fea-43ec-a7d6-6476a76ae868"),
    Source("de_dresden", "pegel", "pegel", "70272185-b2b3-4178-96b8-43bea330dcae"),
    Source("air_alps", "opensky", "opensky", "46,7,47,8", "twenty"),
    Source("air_nyc", "opensky", "opensky", "40,-74.5,41.5,-72.5", "twenty"),
    Source("air_tokyo", "opensky", "opensky", "35,139,36,141", "twenty"),
    Source("air_sao", "opensky", "opensky", "-24,-47.5,-23,-46", "twenty"),
    Source("wiki_en", "wikimedia", "wikimedia", "en"),
    Source("wiki_ru", "wikimedia", "wikimedia", "ru"),
    Source("wiki_zh", "wikimedia", "wikimedia", "zh"),
    Source("wiki_es", "wikimedia", "wikimedia", "es"),
    Source("osm_edits", "osm", "osm", "minute", "hour_live"),
)
SOURCE_BY_ID = {source.id: source for source in SOURCES}


def utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def stamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def get(url: str, *, limit: int = 5_000_000) -> tuple[bytes, str, int, float]:
    started = time.monotonic()
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/plain, */*"})
    with urlopen(request, timeout=18) as response:
        body = response.read(limit + 1)
        status = response.status
    if len(body) > limit:
        raise ValueError(f"Response exceeds {limit} bytes")
    return body, hashlib.sha256(body).hexdigest(), status, round(time.monotonic() - started, 3)


def _json(url: str) -> tuple[object, str, int, int, float]:
    body, digest, status, seconds = get(url)
    return json.loads(body), digest, status, len(body), seconds


def _hour_samples(rows: list[tuple[datetime, object]], day: str) -> dict[str, object]:
    """First valid reading in each UTC hour, with its actual observation time."""
    output: dict[str, object] = {}
    for when, data in sorted(rows, key=lambda item: item[0]):
        when = when.astimezone(UTC)
        if when.date().isoformat() != day:
            continue
        slot = when.replace(minute=0, second=0, microsecond=0)
        if (when - slot).total_seconds() >= 1800:
            continue
        output.setdefault(stamp(slot), {"observed_at": stamp(when), "data": data})
    return output


def _daily_url(source: Source, day: str) -> str:
    compact = day.replace("-", "")
    if source.kind == "coops":
        return "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + urlencode({
            "begin_date": compact, "end_date": compact, "station": source.target,
            "product": "water_level", "datum": "MLLW", "time_zone": "gmt",
            "units": "metric", "application": "TimeLineStamp", "format": "json"})
    if source.kind == "ndbc":
        return f"https://www.ndbc.noaa.gov/data/realtime2/{source.target}.txt"
    if source.kind == "usgs":
        start = day + "T00:00:00Z"
        end = stamp(utc(start) + timedelta(days=1) - timedelta(seconds=1))
        return "https://api.waterdata.usgs.gov/ogcapi/v1/collections/continuous/items?" + urlencode({
            "monitoring_location_id": source.target, "parameter_code": "00060",
            "datetime": f"{start}/{end}", "limit": 500})
    if source.kind == "eccc":
        start = day + "T00:00:00Z"
        end = stamp(utc(start) + timedelta(days=1))
        return "https://api.weather.gc.ca/collections/hydrometric-realtime/items?" + urlencode({
            "STATION_NUMBER": source.target, "datetime": f"{start}/{end}", "limit": 500})
    if source.kind == "ea":
        station = source.target.split(":", 1)[0]
        return f"https://environment.data.gov.uk/flood-monitoring/id/stations/{station}/readings?" + urlencode({
            "startdate": day, "enddate": day, "_limit": 1000})
    if source.kind == "pegel":
        start = day + "T00:00:00Z"
        end = stamp(utc(start) + timedelta(days=1))
        return (f"https://pegelonline.wsv.de/webservices/rest-api/v2/stations/{source.target}/W/measurements.json?"
                + urlencode({"start": start, "end": end}))
    if source.kind == "wikimedia":
        next_day = (datetime.fromisoformat(day) + timedelta(days=1)).strftime("%Y%m%d")
        return (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/aggregate/{source.target}.wikipedia.org/"
                f"all-access/user/hourly/{compact}00/{next_day}00")
    raise ValueError(f"No daily URL for {source.id}")


def daily_samples(source: Source, day: str, *, response_cache: dict | None = None) -> tuple[dict[str, object], dict]:
    """Return fixed hourly samples and a response receipt; no persistent writes."""
    if source.kind not in {"coops", "ndbc", "usgs", "eccc", "ea", "pegel", "wikimedia"}:
        raise ValueError(f"{source.id} is not a daily feed")
    url = _daily_url(source, day)
    reused = response_cache is not None and url in response_cache
    if reused:
        body, digest, status, seconds = response_cache[url]
    else:
        body, digest, status, seconds = get(url)
        if response_cache is not None:
            response_cache[url] = (body, digest, status, seconds)
    receipt = {"url": url, "sha256": digest, "http_status": status, "bytes": len(body),
               "seconds": seconds, "reused_in_cycle": reused}
    rows: list[tuple[datetime, object]] = []
    if source.kind == "ndbc":
        lines = body.decode("utf-8").splitlines()
        if not lines or not lines[0].startswith("#YY"):
            raise ValueError("NDBC header missing")
        fields = lines[0][1:].split()
        for line in lines[2:]:
            parts = line.split()
            if len(parts) != len(fields):
                continue
            when = datetime(*map(int, parts[:5]), tzinfo=UTC)
            values = dict(zip(fields[5:], parts[5:]))
            rows.append((when, {"fields": values, "raw_line": line}))
    else:
        data = json.loads(body)
        if source.kind == "coops":
            if not isinstance(data, dict) or "data" not in data:
                raise ValueError(f"CO-OPS response has no data: {str(data)[:160]}")
            for item in data["data"]:
                if item.get("v") not in (None, ""):
                    rows.append((utc(item["t"]), {"level_m": item["v"], "flags": item.get("f"),
                                                  "quality": item.get("q")}))
        elif source.kind in {"usgs", "eccc"}:
            if not isinstance(data, dict) or "features" not in data:
                raise ValueError("OGC features missing")
            if any(link.get("rel") == "next" for link in data.get("links", [])):
                raise ValueError("OGC result paginated; raise fixed limit or add paging")
            for item in data["features"]:
                p = item.get("properties", {})
                if source.kind == "usgs":
                    if p.get("parameter_code") == "00060" and p.get("value") not in (None, ""):
                        rows.append((utc(p["time"]), {"flow": p["value"], "unit": p.get("unit_of_measure"),
                                                       "series": p.get("time_series_id"), "approval": p.get("approval_status")}))
                elif p.get("STATION_NUMBER") == source.target and (p.get("LEVEL") is not None or p.get("DISCHARGE") is not None):
                    rows.append((utc(p["DATETIME"]), {"level_m": p.get("LEVEL"), "flow_m3_s": p.get("DISCHARGE"),
                                                        "level_flag": p.get("LEVEL_SYMBOL_EN"),
                                                        "flow_flag": p.get("DISCHARGE_SYMBOL_EN")}))
        elif source.kind == "ea":
            if not isinstance(data, dict) or "items" not in data:
                raise ValueError("Environment Agency readings missing")
            station, parameter = source.target.split(":", 1)
            for item in data["items"]:
                measure = item.get("measure", "").rsplit("/", 1)[-1]
                if measure.startswith(station + "-" + parameter + "-") and item.get("value") is not None:
                    rows.append((utc(item["dateTime"]), {"value": item["value"], "measure": measure}))
        elif source.kind == "pegel":
            if not isinstance(data, list):
                raise ValueError("PEGELONLINE measurements missing")
            rows = [(utc(item["timestamp"]), {"level_cm": item["value"]}) for item in data
                    if item.get("value") is not None]
        elif source.kind == "wikimedia":
            if not isinstance(data, dict) or "items" not in data:
                raise ValueError("Wikimedia hourly items missing")
            rows = [(datetime.strptime(item["timestamp"], "%Y%m%d%H").replace(tzinfo=UTC),
                     {"views": item["views"], "project": item.get("project")}) for item in data["items"]
                    if isinstance(item.get("views"), int)]
    return _hour_samples(rows, day), receipt


def live_url(source: Source, slot: datetime) -> str:
    """Build the primary URL of a fixed live or short-window request."""
    slot = slot.astimezone(UTC).replace(second=0, microsecond=0)
    if source.kind == "geofon":
        start = slot.strftime("%Y-%m-%dT%H:%M:%S")
        end = (slot + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")
        url = ("https://geofon.gfz.de/fdsnws/dataselect/1/query?" + urlencode({
            "net": "GE", "sta": source.target, "cha": "BHZ", "starttime": start, "endtime": end}))
    elif source.kind == "geonet":
        url = "https://service-nrt.geonet.org.nz/fdsnws/dataselect/1/query?" + urlencode({
            "network": "NZ", "station": source.target, "location": "20", "channel": "HNZ",
            "starttime": slot.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": (slot + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")})
    elif source.kind == "intermagnet":
        url = "https://imag-data.bgs.ac.uk/GIN_V1/hapi/data?" + urlencode({
            "id": f"{source.target}/adjusted/PT1M/xyzf",
            "time.min": stamp(slot), "time.max": stamp(slot + timedelta(minutes=1))})
    elif source.kind == "opensky":
        box = source.target.split(",")
        url = "https://opensky-network.org/api/states/all?" + urlencode(dict(zip(
            ("lamin", "lomin", "lamax", "lomax"), box)))
    elif source.kind == "osm":
        url = "https://planet.openstreetmap.org/replication/minute/state.txt"
    else:
        raise ValueError(f"No live adapter for {source.id}")
    return url


def live_sample(source: Source, slot: datetime) -> tuple[object, dict]:
    """Fetch a historical one-minute window or one live snapshot for a fixed slot."""
    slot = slot.astimezone(UTC).replace(second=0, microsecond=0)
    url = live_url(source, slot)
    body, digest, status, seconds = get(url)
    receipt = {"url": url, "sha256": digest, "http_status": status, "bytes": len(body), "seconds": seconds}
    if source.kind in {"geofon", "geonet"}:
        if len(body) < 48 or not body[:6].isdigit() or body[6:7] not in (b"D", b"R", b"Q", b"M"):
            raise ValueError("miniSEED header invalid")
        return {"format": "miniSEED", "data_b64": base64.b64encode(body).decode()}, receipt
    if source.kind == "intermagnet":
        lines = body.decode("utf-8").strip().splitlines()
        if not lines or not lines[0].startswith(slot.strftime("%Y-%m-%dT%H:%M")):
            raise ValueError("INTERMAGNET minute missing")
        cells = lines[0].split(",")
        if len(cells) != 5 or any(not re.fullmatch(r"-?\d+(?:\.\d+)?", value) for value in cells[1:]):
            raise ValueError("INTERMAGNET components invalid")
        # HAPI advertises 99999.0 as its fill value. F is measured separately
        # and can be missing while the three vector components remain useful.
        components = [None if float(value) == 99999.0 else value for value in cells[1:]]
        if any(value is None for value in components[:3]):
            raise ValueError("INTERMAGNET vector components missing")
        return {"observed_at": stamp(slot), "components_nT": components}, receipt
    if source.kind == "opensky":
        data = json.loads(body)
        if not isinstance(data, dict) or not isinstance(data.get("time"), int) or not isinstance(data.get("states"), (list, type(None))):
            raise ValueError("OpenSky states missing")
        observed = datetime.fromtimestamp(data["time"], UTC)
        if abs((observed - datetime.now(UTC)).total_seconds()) > 900:
            raise ValueError("OpenSky snapshot is stale")
        return {"observed_at": stamp(observed), "states": data["states"] or []}, receipt
    text = body.decode("utf-8")
    match = re.search(r"^sequenceNumber=(\d+)$", text, re.M)
    clock = re.search(r"^timestamp=(.+)$", text, re.M)
    if not match or not clock:
        raise ValueError("OSM state fields missing")
    sequence = int(match.group(1))
    observed = utc(clock.group(1).replace("\\:", ":"))
    if observed.replace(minute=0, second=0, microsecond=0) != slot:
        raise ValueError("OSM latest diff outside requested hour")
    path = f"{sequence:09d}"
    diff_url = f"https://planet.openstreetmap.org/replication/minute/{path[:3]}/{path[3:6]}/{path[6:]}.osc.gz"
    compressed, diff_digest, diff_status, diff_seconds = get(diff_url)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as archive:
        xml = archive.read(20_000_001)
    if len(xml) > 20_000_000:
        raise ValueError("OSM minute diff exceeds 20 MB uncompressed")
    if ET.fromstring(xml).tag != "osmChange":
        raise ValueError("OSM diff is not osmChange")
    receipt["diff"] = {"url": diff_url, "sha256": diff_digest, "http_status": diff_status,
                       "bytes": len(compressed), "seconds": diff_seconds}
    return {"observed_at": stamp(observed), "sequence": sequence,
            "state_text": text, "diff_sha256": diff_digest,
            "diff_gz_b64": base64.b64encode(compressed).decode()}, receipt
