"""Sea-polygon generation from OSM coastlines (pure Python, no QGIS imports).

Method ("extent minus land", no extra download):
  1. Coastline ways are clipped to the download extent. OSM convention
     (OSM wiki "Coastline processing"): LAND is always on the LEFT side of
     the way direction, the water/sea on the right side.
  2. The extent border is split at the coastline endpoints; boundary arcs
     and coast segments form a planar graph.
  3. All faces of the graph are traced (half-edge walk, face on the left
     of each directed edge). A face bounded by a coast segment traversed
     AGAINST its OSM direction has the land on its left -> LAND face.
  4. land = union of land faces; sea = extent polygon - land.

The caller (dialog) does the final difference with QgsGeometry and exports
the result as the "Ocean (polygons)" layer.
"""
import math

_EPS = 1e-9


def _key(p):
    return (round(p[0], 9), round(p[1], 9))


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _on_border(p, bbox):
    s, w, n, e = bbox
    return (_abs_close(p[1], s) or _abs_close(p[1], n) or
            _abs_close(p[0], w) or _abs_close(p[0], e))


def _abs_close(v, ref):
    return abs(v - ref) < 1e-7


def _border_param(p, bbox):
    """Position t in [0,4) of a border point, counterclockwise from (W,S)."""
    s, w, n, e = bbox
    x, y = p
    if _abs_close(x, w):
        if _abs_close(y, s):
            return 0.0
        if _abs_close(y, n):
            return 3.0
        return 3.0 + (n - y) / (n - s)          # west edge, N->S (CCW)
    if _abs_close(x, e):
        if _abs_close(y, s):
            return 1.0
        if _abs_close(y, n):
            return 2.0
        return 1.0 + (y - s) / (n - s)          # east edge S->N
    if _abs_close(y, s):
        return (x - w) / (e - w)                # south edge W->E
    if _abs_close(y, n):
        return 2.0 + (e - x) / (e - w)          # north edge E->W
    return None


def _border_point(t, bbox):
    s, w, n, e = bbox
    t %= 4.0
    if t < 1.0:
        return (w + (e - w) * t, s)
    if t < 2.0:
        return (e, s + (n - s) * (t - 1.0))
    if t < 3.0:
        return (e - (e - w) * (t - 2.0), n)
    return (w, n - (n - s) * (t - 3.0))


def _clip_line_to_bbox(coords, bbox):
    """Clip one polyline to the bbox; return list of polylines inside."""
    s, w, n, e = bbox

    def inside(p):
        return s - 1e-12 <= p[1] <= n + 1e-12 and w - 1e-12 <= p[0] <= e + 1e-12

    def seg_clip(a, b):
        # Liang-Barsky; returns clipped segment or None
        x1, y1 = a
        x2, y2 = b
        dx, dy = x2 - x1, y2 - y1
        t0, t1 = 0.0, 1.0
        for p, q in ((-dx, x1 - w), (dx, e - x1), (-dy, y1 - s), (dy, n - y1)):
            if p == 0:
                if q < 0:
                    return None
            else:
                r = q / p
                if p < 0:
                    if r > t1:
                        return None
                    if r > t0:
                        t0 = r
                else:
                    if r < t0:
                        return None
                    if r < t1:
                        t1 = r
        return [(x1 + t0 * dx, y1 + t0 * dy), (x1 + t1 * dx, y1 + t1 * dy)]

    out, cur = [], []
    for i in range(len(coords) - 1):
        a, b = coords[i], coords[i + 1]
        c = seg_clip(a, b)
        if c is None:
            if len(cur) >= 2:
                out.append(cur)
            cur = []
            continue
        if not cur or _dist(cur[-1], c[0]) > _EPS:
            if len(cur) >= 2:
                out.append(cur)
            cur = [c[0]]
        if not cur:
            cur = [c[0]]
        cur.append(c[1])
    if len(cur) >= 2:
        out.append(cur)
    return [p for p in out if len(p) >= 2]


def _snap_to_border(p, bbox):
    if _on_border(p, bbox):
        return p
    s, w, n, e = bbox
    cands = [((p[0], s), abs(p[1] - s)), ((p[0], n), abs(p[1] - n)),
             ((w, p[1]), abs(p[0] - w)), ((e, p[1]), abs(p[0] - e))]
    return min(cands, key=lambda c: c[1])[0]


def _ring_area(ring):
    a = 0.0
    for i in range(len(ring) - 1):
        a += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1]
    return a / 2.0


def trace_land_faces(bbox, coast_lines):
    """Trace the planar faces and return (land_rings, warnings).

    coast_lines: iterable of polylines [(x, y), ...] in OSM direction
    (land on the right). Rings are returned as coordinate lists.
    """
    warnings = []
    s, w, n, e = bbox
    if n - s < 1e-9 or e - w < 1e-9:
        return [], ["extent is empty"]

    # ---- collect directed segments ------------------------------------
    # edge types: coast-original (land right), coast-reversed, border
    segs = {}          # (u, v) -> ("coast", original: bool) | ("border", None)
    nodes_out = {}     # u -> {v: (kind, original)}

    def add_edge(u, v, kind, original=True):
        u, v = _key(u), _key(v)
        if u == v:
            return
        segs.setdefault((u, v), (kind, original))
        nodes_out.setdefault(u, {})[v] = (kind, original)

    # coast segments (clipped, snapped, deduplicated)
    coast_nodes = set()
    for line in coast_lines:
        for piece in _clip_line_to_bbox(line, bbox):
            prev = None
            for pt in piece:
                pt = _key(pt)
                if prev is not None:
                    if _dist(prev, pt) > 1e-12:
                        add_edge(prev, pt, "coast", True)
                        add_edge(pt, prev, "coast", False)
                prev = pt
            # BOTH piece endpoints must split the extent border, otherwise
            # border arcs run through them and the graph is not planar
            for endpt in (piece[0], piece[-1]):
                if _on_border(endpt, bbox):
                    coast_nodes.add(_key(endpt))
                else:
                    warnings.append("coastline does not reach the extent "
                                    "border (dangling); sea may be incomplete")

    # ---- border arcs between consecutive nodes ------------------------
    ts = sorted({0.0, 1.0, 2.0, 3.0} |
                {t for t in (_border_param(p, bbox) for p in coast_nodes)
                 if t is not None})
    for i in range(len(ts)):
        t0, t1 = ts[i], ts[(i + 1) % len(ts)]
        a = _key(_border_point(t0, bbox))
        b = _key(_border_point(t1, bbox))
        if a == b:
            continue
        add_edge(a, b, "border")
        add_edge(b, a, "border")

    # ---- half-edge face walk (face on the left) -----------------------
    def angle(u, v):
        return math.atan2(v[1] - u[1], v[0] - u[0])

    outgoing = {u: sorted(((angle(u, v), v) for v in nodes_out[u])) for u in nodes_out}

    def next_edge(u, v):
        """Face-on-left walk: from directed edge u->v, at v pick the first
        outgoing edge clockwise after the reverse edge (v->u)."""
        back = angle(v, u)
        cands = outgoing.get(v, [])
        if not cands:
            return None
        # first edge with angle < back (strictly), wrapping: clockwise scan
        best = None
        for ang, w_ in cands:
            if _key(w_) == _key(u):
                continue                      # never bounce straight back
            # clockwise after back: angle < back, take the LARGEST such
            if ang < back - 1e-12:
                if best is None or ang > best[0]:
                    best = (ang, w_)
        if best is None:
            # wrap around: take the largest angle overall
            for ang, w_ in cands:
                if _key(w_) == _key(u):
                    continue
                if best is None or ang > best[0]:
                    best = (ang, w_)
        return (v, best[1]) if best else None

    visited = set()
    land_rings = []
    for start in list(segs.keys()):
        if start in visited:
            continue
        cycle = []
        u, v = start
        has_original_coast = False
        ok = True
        while (u, v) not in visited:
            visited.add((u, v))
            cycle.append((u, v))
            kind, original = segs[(u, v)]
            if kind == "coast" and original:
                # the face lies on the LEFT of every edge in its cycle; for
                # an ORIGINAL coast edge (OSM direction) the left side is
                # LAND per the OSM coastline convention -> land face
                has_original_coast = True
            nxt = next_edge(u, v)
            if nxt is None:
                ok = False
                break
            u, v = nxt
            if (u, v) == start:
                break
        if not ok or len(cycle) < 3:
            continue
        if has_original_coast:
            ring = [p for p, _q in cycle]
            if _ring_area(ring) > 1e-12:
                land_rings.append(ring)
    return land_rings, warnings
