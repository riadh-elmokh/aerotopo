"""Overpass helpers: query building, download, and OSM JSON -> plain records.

No QGIS imports here, so this module can be tested outside QGIS.
"""
import json
import math
import re
import socket
import time
from collections import deque
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "QGIS-AeroTopo/1.0"


class OverpassError(Exception):
    def __init__(self, msg="", too_big=False):
        super().__init__(msg)
        self.too_big = too_big


class Cancelled(OverpassError):
    pass


# ---------------------------------------------------------------- queries
def _q(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


_TYPE_RE = re.compile(r"^(nwr|nw|nr|wr|node|way|relation|rel|n|w|r)(?=\[)")


def is_raw(key):
    return key.startswith("[") or bool(_TYPE_RE.match(key))


def build_filter(key, value):
    """Return an Overpass tag filter.

    key only            -> ["key"]
    key + value         -> ["key"="value"]
    value "a|b|c"       -> ["key"~"^(a|b|c)$"]
    value "~regex"      -> ["key"~"regex"]
    value "*"           -> ["key"]
    key starting with [ -> used as a raw filter, e.g. ["amenity"="cafe"]["wheelchair"="yes"]
    """
    key = key.strip()
    value = (value or "").strip()
    if is_raw(key):
        return key
    k = _q(key)
    if value in ("", "*"):
        return f'["{k}"]'
    if value.startswith("~"):
        return f'["{k}"~"{_q(value[1:])}"]'
    if "|" in value:
        parts = "|".join(re.escape(p.strip()) for p in value.split("|") if p.strip())
        return f'["{k}"~"^({_q(parts)})$"]'
    return f'["{k}"="{_q(value)}"]'


def build_query(key, value, bbox, timeout=180):
    """bbox = (south, west, north, east) in EPSG:4326."""
    s, w, n, e = bbox
    flt = build_filter(key, value)
    head = "" if _TYPE_RE.match(flt) else "nwr"
    return (
        f"[out:json][timeout:{int(timeout)}];\n"
        f"{head}{flt}({s:.7f},{w:.7f},{n:.7f},{e:.7f});\n"
        "out tags geom;"
    )


def _too_big_remark(remark):
    r = remark.lower()
    return "timed out" in r or "memory" in r or "too large" in r


def fetch(endpoint, query, timeout=180, retries=2, is_canceled=None):
    payload = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last, too_big = None, False
    for attempt in range(retries + 1):
        if is_canceled and is_canceled():
            raise Cancelled("Cancelled")
        req = urllib.request.Request(
            endpoint, data=payload, headers={"User-Agent": USER_AGENT}
        )
        if urllib.parse.urlparse(endpoint).scheme != "https":
            raise OverpassError("only https endpoints are allowed")
        try:
            with urllib.request.urlopen(req, timeout=timeout + 30) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last, too_big = f"HTTP {exc.code} {exc.reason}", exc.code == 504
            if exc.code not in (429, 502, 503, 504):
                break
        except (socket.timeout, TimeoutError):
            raise OverpassError("request timed out", too_big=True)
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (socket.timeout, TimeoutError)):
                raise OverpassError("request timed out", too_big=True)
            last, too_big = str(exc.reason), False
        except ValueError as exc:
            last, too_big = f"invalid or truncated response ({exc})", True
        else:
            remark = data.get("remark", "")
            if remark and ("runtime error" in remark.lower() or not data.get("elements")):
                raise OverpassError(remark, too_big=_too_big_remark(remark))
            return data
        if attempt < retries:
            for _ in range(10 * (attempt + 1)):
                if is_canceled and is_canceled():
                    raise Cancelled("Cancelled")
                time.sleep(1)
    raise OverpassError(last or "Unknown error", too_big=too_big)

# ---------------------------------------------------------------- parsing
AREA_KEYS = {
    "building", "building:part", "landuse", "leisure", "amenity", "shop",
    "tourism", "office", "craft", "historic", "man_made", "military", "place",
    "aeroway", "healthcare", "club", "natural", "boundary", "landcover",
    "geological", "public_transport", "area:aeroway",
}
# aeroway=runway/taxiway/taxilane are deliberately NOT listed here: a closed
# way with these tags is a surface polygon (ICAO Annex 4 App. 2 syms 145-149).
# The line representation is produced separately in classify() so the runway
# surface polygon and the runway centreline line are separate layers.
LINEAR_VALUES = {
    "aeroway": {"navigationaid", "windsock"},
    "boundary": {"administrative", "maritime", "political", "disputed"},
    "leisure": {"track"},
    "natural": {"coastline", "cliff", "ridge", "tree_row", "valley", "arete"},
    "man_made": {"pier", "breakwater", "embankment", "dyke", "cutline",
                 "pipeline", "goods_conveyor", "groyne"},
}


def is_area(tags):
    if tags.get("area") == "yes":
        return True
    if tags.get("area") == "no":
        return False
    if tags.get("waterway") in ("riverbank", "dock", "boatyard"):
        return True
    if tags.get("highway") in ("services", "rest_area"):
        return True
    for k, v in tags.items():
        if k in AREA_KEYS and v not in LINEAR_VALUES.get(k, ()):
            return True
    return False


_AEROWAY_DUAL = {"runway", "taxiway", "taxilane", "airstrip", "helipad"}


def _coords(geometry):
    return [(p["lon"], p["lat"]) for p in (geometry or []) if p]


def classify(elements):
    """Split Overpass elements into point / line / polygon records."""
    out = {"point": [], "line": [], "polygon": []}
    for e in elements:
        t = e.get("type")
        tags = e.get("tags") or {}
        base = {"id": e.get("id"), "type": t, "tags": tags}

        if t == "node":
            if "lat" in e and "lon" in e:
                out["point"].append(dict(base, xy=(e["lon"], e["lat"])))

        elif t == "way":
            c = _coords(e.get("geometry"))
            if len(c) < 2:
                continue
            closed = len(c) >= 4 and c[0] == c[-1]
            if closed and is_area(tags):
                out["polygon"].append(dict(base, outer=[c], inner=[]))
                # Runway/taxiway surfaces keep a SEPARATE line representation
                # (Annex 4 App. 2 syms 145-149 appear as areas and as centre
                # lines/strip outlines on Aerodrome charts). Two layers.
                if tags.get("aeroway") in _AEROWAY_DUAL:
                    out["line"].append(dict(base, lines=[c]))
            else:
                out["line"].append(dict(base, lines=[c]))

        elif t == "relation":
            members = [m for m in e.get("members", [])
                       if m.get("type") == "way" and m.get("geometry")]
            linear_boundary = (tags.get("type") == "boundary"
                               and tags.get("boundary") in LINEAR_VALUES["boundary"])
            if tags.get("type") in ("multipolygon", "boundary") and not linear_boundary:
                outer, inner = [], []
                for m in members:
                    c = _coords(m["geometry"])
                    if len(c) < 2:
                        continue
                    (inner if m.get("role") == "inner" else outer).append(c)
                if outer:
                    out["polygon"].append(dict(base, outer=outer, inner=inner))
            else:
                lines = [c for c in (_coords(m["geometry"]) for m in members) if len(c) >= 2]
                if lines:
                    out["line"].append(dict(base, lines=lines))
    return out


# ---------------------------------------------------------------- big areas
def make_tiles(bbox, size):
    """Split (s, w, n, e) into tiles of at most `size` degrees (size <= 0: one tile)."""
    s, w, n, e = bbox
    if size <= 0 or ((n - s) <= size and (e - w) <= size):
        return [tuple(bbox)]
    rows = math.ceil((n - s) / size)
    cols = math.ceil((e - w) / size)
    tiles = []
    for i in range(rows):
        for j in range(cols):
            ts, tw = s + i * size, w + j * size
            tiles.append((ts, tw, min(n, ts + size), min(e, tw + size)))
    return tiles


def split_tile(t):
    s, w, n, e = t
    ms, mw = (s + n) / 2, (w + e) / 2
    return [(s, w, ms, mw), (s, mw, ms, e), (ms, w, n, mw), (ms, mw, n, e)]


def download(endpoint, key, value, bbox, tile_size=1.0, timeout=180, pause=0.5,
             min_tile=0.02, is_canceled=None, log=None, progress=None):
    """Download one key/value over a (possibly large) bbox.

    The bbox is cut into tiles; a tile that the server cannot answer (timeout / out of
    memory) is split in four and retried. Elements are de-duplicated across tiles.
    Returns (classified_dict, failed_tiles).
    """
    log = log or (lambda m: None)
    queue = deque(make_tiles(bbox, tile_size))
    if len(queue) > 1:
        log(f"  {len(queue)} tiles of {tile_size}\u00b0")
    out = {"point": [], "line": [], "polygon": []}
    seen, failed, done = set(), [], 0
    while queue:
        if is_canceled and is_canceled():
            raise Cancelled("Cancelled")
        tile = queue.popleft()
        query = build_query(key, value, tile, timeout)
        try:
            data = fetch(endpoint, query, timeout, is_canceled=is_canceled)
        except Cancelled:
            raise
        except OverpassError as exc:
            if exc.too_big and max(tile[2] - tile[0], tile[3] - tile[1]) / 2 >= min_tile:
                log(f"  tile too heavy ({exc}); splitting in 4")
                queue.extendleft(reversed(split_tile(tile)))
                continue
            failed.append((tile, str(exc)))
            log(f"  tile failed: {exc}")
        else:
            fresh = []
            for el in data.get("elements", []):
                k = (el.get("type"), el.get("id"))
                if k not in seen:
                    seen.add(k)
                    fresh.append(el)
            part = classify(fresh)
            for kind in out:
                out[kind].extend(part[kind])
        done += 1
        if progress:
            progress(done, len(queue))
        if pause and queue:
            for _ in range(int(pause * 10)):
                if is_canceled and is_canceled():
                    raise Cancelled("Cancelled")
                time.sleep(0.1)
    return out, failed
