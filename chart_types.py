"""Chart-type layer registry, source traceability and document comparison.

Pure Python (no QGIS imports) so it can be tested outside QGIS.

Authoritative sources for every layer name and status:
  * ICAO Annex 4 — Aeronautical Charts, Eleventh Edition (July 2009),
    consolidated 2021, incorporating amendments up to No. 61 (4/11/21).
    Symbol names are quoted VERBATIM from Appendix 2 (pages APP 2-1..APP 2-6).
  * ICAO Doc 8697 — Aeronautical Chart Manual, Third Edition, 2016.
    Feature lists are quoted from Chapter 7 preparation sections.

This plugin maps ICAO chart content onto OpenStreetMap tags. It does NOT make
the resulting data ICAO-compliant: official aeronautical data (airspace,
procedures, obstacles, navaids) must come from the AIP.
"""
import csv
import os

DOCUMENTS = {
    "annex4": {
        "title": "ICAO Annex 4 — Aeronautical Charts",
        "edition": "Eleventh Edition, July 2009",
        "file_edition": "consolidated edition 2021 (an04_cons_en_2021.pdf)",
        "amendment": "incorporates amendments adopted prior to 9 March 2009; "
                     "pages also carry Amendment 61, dated 4/11/21",
        "status": "in force (verify the amendment applicable to your chart)",
    },
    "doc8697": {
        "title": "ICAO Doc 8697 — Aeronautical Chart Manual",
        "edition": "Third Edition, 2016",
        "file_edition": "8697_cons_en_2020_Carto Manual.pdf",
        "amendment": "original text 2016 (no amendment markers found in file)",
        "status": "guidance material (no Standards; supports Annex 4)",
    },
}

# Status vocabulary (never invent anything stronger than the documents say):
REQUIRED, CONDITIONAL, OPTIONAL, VERIFY, NOT_APPLICABLE = (
    "required", "conditional", "optional", "needs verification", "not applicable")

_AOC_OBSTACLES = {"towers": CONDITIONAL, "pylons": CONDITIONAL, "poles": CONDITIONAL,
                  "ohcable": CONDITIONAL, "trees": CONDITIONAL, "wind": CONDITIONAL,
                  "tallbldg": CONDITIONAL}
_VFR_RELIEF = {"contours": CONDITIONAL, "peaks": CONDITIONAL, "survey": CONDITIONAL,
               "cliff": CONDITIONAL}
_VFR_HYDRO = {"shore": REQUIRED, "ocean": REQUIRED, "lakes": REQUIRED,
              "river": REQUIRED, "river_a": CONDITIONAL, "stream": CONDITIONAL,
              "reservoir": CONDITIONAL}
_VFR_CULT = {"places": REQUIRED, "builtup": REQUIRED, "rail": REQUIRED,
             "dual": REQUIRED, "primary": REQUIRED, "secondary": REQUIRED,
             "rail_stn": CONDITIONAL, "road_con": CONDITIONAL, "trail": OPTIONAL}
_VFR_MISC = {"border": REQUIRED, "border_other": CONDITIONAL, "lookout": CONDITIONAL,
             "lighthouse": CONDITIONAL}
_AD_BASE = {"ad": REQUIRED, "heliport": CONDITIONAL, "airstrip": CONDITIONAL,
            "ad_closed": CONDITIONAL, "ad_mil": CONDITIONAL}
_RADIO_BASE = {"rn_vor": CONDITIONAL, "rn_ndb": CONDITIONAL, "rn_dme": CONDITIONAL,
               "rn_tacan": CONDITIONAL, "rn_ils": CONDITIONAL, "rn_marker": CONDITIONAL,
               "rn_all": CONDITIONAL}
_RESTRICTED = {"mil_land": CONDITIONAL, "mil_danger": CONDITIONAL}

# ---------------------------------------------------------------------------
# Chart types.  "layers" maps catalog item id -> status.  "ref" cites the
# exact Annex 4 section and Doc 8697 section that lists the elements.
# ---------------------------------------------------------------------------
CHART_TYPES = [
    {"code": "ADC", "name": "Aerodrome/Heliport Chart — ICAO",
     "ref": "Annex 4 Ch. 13, 13.6.1 a)-s) (pp. 13-2/13-3); Doc 8697 7.13 (7-13-1 ff.)",
     "layers": {
         "runway": REQUIRED,        # 13.6.1 d) "all runways including those under construction"
         "taxiway": REQUIRED,       # 13.6.1 g) "all taxiways, helicopter air and ground taxiways"
         "apron": REQUIRED,         # 13.6.1 e) "all aprons"
         "parking": REQUIRED,       # 13.6.1 e) "aircraft/helicopter stands"
         "holding": REQUIRED,       # 13.6.1 g) "runway-holding positions ... intermediate holding positions, stop bars"
         "helipad": CONDITIONAL,    # 13.6.3 b) touchdown and lift-off area (heliports)
         "windsock": CONDITIONAL,   # 13.6.1 n) visual aids; Appendix 2 syms 156/157
         "vasi": CONDITIONAL,       # 13.6.1 n) visual approach slope indicator systems
         "stopway": CONDITIONAL,    # 13.6.1 d) stopways
         "adbldg": CONDITIONAL,     # 13.6.1 q) "buildings of operational significance"
         "servicing": CONDITIONAL,  # 13.6.1 q) "aircraft servicing areas"
         "tower": CONDITIONAL,      # operational facility (not symbol-numbered)
         "adarea": CONDITIONAL,     # movement-area surfaces (Appendix 2 syms 145-149)
         "ad": REQUIRED, "airstrip": NOT_APPLICABLE, "heliport": CONDITIONAL,
         "ad_closed": CONDITIONAL,
         "rn_vor": CONDITIONAL,     # 13.6.1 r) "VOR checkpoint"
         "rn_all": CONDITIONAL,
         "buildings": CONDITIONAL,  # surrounding area only
         "shore": OPTIONAL, "lakes": OPTIONAL, "river": OPTIONAL,  # not required by 13.6
         "mil_danger": VERIFY, "mil_land": VERIFY,
     }},
    {"code": "GMC", "name": "Aerodrome Ground Movement Chart — ICAO",
     "ref": "Annex 4 Ch. 14, 14.6.1 a)-m) (pp. 14-1/14-2); Doc 8697 7.14",
     "layers": {
         "apron": REQUIRED,         # 14.6.1 b)
         "parking": REQUIRED,       # 14.6.1 c) "aircraft stands"
         "taxiway": REQUIRED,       # 14.6.1 d) "taxiways with designations, width"
         "holding": REQUIRED,       # 14.6.1 d) runway-holding positions, stop bars
         "runway": CONDITIONAL,     # shown "in a similar manner" as ADC, relevant to area
         "servicing": CONDITIONAL,  # 14.6.1 k) "aircraft servicing areas and buildings"
         "adbldg": CONDITIONAL,     # 14.6.1 k) "buildings of operational significance"
         "tower": CONDITIONAL, "adarea": CONDITIONAL, "ad": REQUIRED,
         "rn_vor": CONDITIONAL,     # 14.6.1 l) VOR checkpoint
         "ad_closed": CONDITIONAL, "heliport": CONDITIONAL,
         "buildings": CONDITIONAL, "shore": OPTIONAL, "lakes": OPTIONAL,
         "mil_danger": VERIFY, "mil_land": VERIFY,
     }},
    {"code": "PDC", "name": "Aircraft Parking/Docking Chart — ICAO",
     "ref": "Annex 4 Ch. 15, 15.6 a)-l) (pp. 15-1/15-2); Doc 8697 7.15",
     "note": "Terminology verified: the official title is “Aircraft Parking/Docking "
             "Chart — ICAO” (Annex 4 Ch. 15; Doc 8697 7.15). “APDC” is not an ICAO "
             "term; “PDC” commonly means pre-departure clearance. Both user names "
             "kept for reference only.",
     "layers": {
         "apron": REQUIRED,         # 15.6 b)
         "parking": REQUIRED,       # 15.6 c) "aircraft stands"
         "taxiway": REQUIRED,       # 15.6 d) "taxiway entries with designations"
         "holding": REQUIRED,       # 15.6 d) runway-holding positions, stop bars
         "servicing": CONDITIONAL,  # 15.6 j)
         "adbldg": CONDITIONAL,     # 15.6 j) buildings of operational significance
         "runway": CONDITIONAL, "adarea": CONDITIONAL, "ad": REQUIRED,
         "rn_vor": CONDITIONAL,     # 15.6 k) VOR checkpoint
         "tower": CONDITIONAL, "helipad": CONDITIONAL,
         "buildings": CONDITIONAL, "shore": OPTIONAL, "lakes": OPTIONAL,
     }},
    {"code": "AOC-A", "name": "Aerodrome Obstacle Chart — ICAO Type A (Operating Limitations)",
     "ref": "Annex 4 Ch. 3, 3.8.1/3.8.2/3.8.4 (pp. 3-2..3-4); Doc 8697 7.3",
     "layers": {
         "runway": REQUIRED,        # 3.8.4.1 a) "outline of the runways by a solid line"
         "stopway": REQUIRED,       # 3.8.4.1 / Appendix 2 sym 169
         "buildings": CONDITIONAL,  # Doc 8697 7.3 drafting: aerodrome buildings
         "adbldg": CONDITIONAL,
         "towers": REQUIRED,        # 3.8.1.1 obstacles above the 1.2 % plane
         "pylons": REQUIRED, "poles": REQUIRED, "ohcable": REQUIRED,
         "trees": REQUIRED, "wind": REQUIRED, "tallbldg": REQUIRED,
         "rail": CONDITIONAL,       # 4.7.4-style culture near the strip (Type A: plan view culture)
         "dual": CONDITIONAL, "primary": CONDITIONAL, "secondary": CONDITIONAL,
         "cliff": CONDITIONAL, "lighthouse": OPTIONAL,
         "contours": VERIFY, "peaks": VERIFY,   # Type A uses a profile; survey data from AIP
     }},
    {"code": "AOC-B", "name": "Aerodrome Obstacle Chart — ICAO Type B",
     "ref": "Annex 4 Ch. 4, 4.7.1-4.7.4 (p. 4-2); Doc 8697 7.4",
     "layers": {
         "runway": REQUIRED, "stopway": REQUIRED,   # plan view; Appendix 2 syms 167-170
         "adbldg": REQUIRED,        # 4.7.2 "Buildings and other salient features ... shown"
         "buildings": CONDITIONAL,  # 4.7.2, shown to scale where possible
         "towers": REQUIRED,        # 4.7.3 objects projecting above the surfaces
         "pylons": REQUIRED, "poles": REQUIRED, "ohcable": REQUIRED,
         "trees": REQUIRED, "wind": REQUIRED, "tallbldg": REQUIRED,
         "rail": REQUIRED,          # 4.7.4 "Roads and railroads ... less than 600 m"
         "dual": REQUIRED, "primary": REQUIRED, "secondary": REQUIRED,
         "cliff": REQUIRED,         # Appendix 2 sym 168 "Escarpment"
         "shore": CONDITIONAL,      # 4.7.1 hydrography "kept to a minimum"
         "lakes": CONDITIONAL, "river": CONDITIONAL,
         "lighthouse": OPTIONAL, "contours": VERIFY, "peaks": VERIFY,
     }},
    {"code": "ATEC", "name": "Aerodrome Terrain and Obstacle Chart — ICAO (Electronic)",
     "ref": "Annex 4 Ch. 5 (5.1-5.7); Doc 8697 7.5",
     "layers": {
         "runway": CONDITIONAL, "taxiway": CONDITIONAL, "apron": CONDITIONAL,
         "towers": CONDITIONAL, "buildings": CONDITIONAL, "contours": VERIFY,
         "peaks": VERIFY, "shore": VERIFY, "lakes": VERIFY,
     },
     "note": "Electronic chart: terrain and obstacle data sets (Annex 4 Ch. 5, "
             "aligned with Annex 15 data collections) are NOT obtainable from OSM; "
             "use a DEM and the AIP obstacle data. All statuses need verification."},
    {"code": "PATC", "name": "Precision Approach Terrain Chart — ICAO",
     "ref": "Annex 4 Ch. 6, 6.5.1 a)-c) (p. 6-1); Doc 8697 7.6",
     "layers": {
         "contours": VERIFY,        # 6.5.1 a) 1 m contours — DEM required, not OSM
         "runway": CONDITIONAL, "peaks": VERIFY, "buildings": CONDITIONAL,
         "towers": CONDITIONAL, "trees": CONDITIONAL,
     },
     "note": "Content is a terrain profile within 60 m either side of the extended "
             "centre line (6.5.1 a)); derive contours from a DEM. OSM contributes "
             "only incidental plan features."},
    {"code": "ENR", "name": "Enroute Chart — ICAO",
     "ref": "Annex 4 Ch. 7, 7.6-7.7 (7.6.1 culture; 7.7 aeronautical data); Doc 8697 7.7",
     "layers": {
         "shore": REQUIRED, "lakes": REQUIRED, "river": REQUIRED,
         "places": CONDITIONAL, "builtup": CONDITIONAL,
         "ad": REQUIRED,            # 7.7.1 aerodromes
         "rn_vor": CONDITIONAL, "rn_ndb": CONDITIONAL, "rn_dme": CONDITIONAL,
         "rn_all": CONDITIONAL,     # 7.7.2 radio navigation aids
         "mil_land": CONDITIONAL, "mil_danger": CONDITIONAL,  # 7.7.4 restricted airspace (AIP)
         "border": CONDITIONAL,     # 7.6.2 area limits where appropriate
         "contours": OPTIONAL, "peaks": OPTIONAL, "airstrip": CONDITIONAL,
     },
     "note": "ATS routes, reporting points and airspace classifications "
             "(Appendix 2 syms 111-129) come from the AIP, not OSM."},
    {"code": "AREA", "name": "Area Chart — ICAO",
     "ref": "Annex 4 Ch. 8, 8.6.1/8.6.2 (8-3); Doc 8697 7.8",
     "layers": {
         "shore": REQUIRED, "lakes": REQUIRED, "river": REQUIRED,
         "ad": REQUIRED, "rn_vor": CONDITIONAL, "rn_ndb": CONDITIONAL,
         "rn_dme": CONDITIONAL, "rn_all": CONDITIONAL,
         "mil_land": CONDITIONAL, "mil_danger": CONDITIONAL,
         "places": CONDITIONAL, "builtup": CONDITIONAL, "rail": CONDITIONAL,
         "dual": CONDITIONAL, "primary": CONDITIONAL, "secondary": CONDITIONAL,
         "peaks": OPTIONAL, "contours": OPTIONAL,
     },
     "note": "Contains mainly ATS route/procedure data from the AIP; OSM covers "
             "only the underlying culture and topography."},
    {"code": "SID", "name": "Standard Departure Chart — Instrument (SID) — ICAO",
     "ref": "Annex 4 Ch. 9, 9.6.1/9.6.2 (9-3); Doc 8697 7.9",
     "layers": {
         "shore": REQUIRED, "lakes": REQUIRED, "river": REQUIRED,
         "ad": REQUIRED, "rn_vor": CONDITIONAL, "rn_ndb": CONDITIONAL,
         "rn_dme": CONDITIONAL, "rn_all": CONDITIONAL,
         "mil_land": CONDITIONAL, "mil_danger": CONDITIONAL,
         "places": CONDITIONAL, "peaks": OPTIONAL, "contours": OPTIONAL,
     },
     "note": "Departure procedures from the AIP; OSM provides base topography only."},
    {"code": "STAR", "name": "Standard Arrival Chart — Instrument (STAR) — ICAO",
     "ref": "Annex 4 Ch. 10, 10.6.1/10.6.2 (10-3); Doc 8697 7.10",
     "layers": {
         "shore": REQUIRED, "lakes": REQUIRED, "river": REQUIRED,
         "ad": REQUIRED, "rn_vor": CONDITIONAL, "rn_ndb": CONDITIONAL,
         "rn_dme": CONDITIONAL, "rn_all": CONDITIONAL,
         "mil_land": CONDITIONAL, "mil_danger": CONDITIONAL,
         "places": CONDITIONAL, "peaks": OPTIONAL, "contours": OPTIONAL,
     },
     "note": "Arrival procedures from the AIP; OSM provides base topography only."},
    {"code": "IAC", "name": "Instrument Approach Chart — ICAO",
     "ref": "Annex 4 Ch. 11, 11.10 (11-4 ff.); Doc 8697 7.11",
     "layers": {
         "ad": REQUIRED,            # 11.10.1 aerodromes
         "towers": REQUIRED,        # 11.10.2 obstacles (with AIP obstacle data)
         "buildings": CONDITIONAL, "pylons": CONDITIONAL, "wind": CONDITIONAL,
         "rn_vor": CONDITIONAL, "rn_ndb": CONDITIONAL, "rn_dme": CONDITIONAL,
         "rn_ils": CONDITIONAL, "rn_all": CONDITIONAL,
         "mil_land": CONDITIONAL, "mil_danger": CONDITIONAL,  # 11.10.3 restricted areas
         "runway": CONDITIONAL,     # landing aerodrome runway pattern
         "shore": CONDITIONAL, "lakes": CONDITIONAL, "river": CONDITIONAL,
         "places": CONDITIONAL, "contours": CONDITIONAL, "peaks": CONDITIONAL,
         "cliff": OPTIONAL,
     },
     "note": "Minimum sector altitude and procedure data (Appendix 2 syms 171-174) "
             "come from the AIP."},
    {"code": "VAC", "name": "Visual Approach Chart — ICAO",
     "ref": "Annex 4 Ch. 12, 12.7.1-12.7.4 and 12.10 (12-2/12-3); Doc 8697 7.12",
     "layers": {
         "cliff": REQUIRED,         # 12.7.1 "bluffs, cliffs"
         "dunes": REQUIRED,         # 12.7.1 "sand dunes"
         "places": REQUIRED,        # 12.7.1 "cities, towns"
         "dual": REQUIRED, "primary": REQUIRED, "secondary": REQUIRED,  # "roads"
         "rail": REQUIRED,          # 12.7.1 "railroads"
         "lighthouse": REQUIRED,    # 12.7.1 "isolated lighthouses"
         "shore": REQUIRED,         # 12.7.2 "Shore lines, lakes, rivers and streams"
         "lakes": REQUIRED, "river": REQUIRED, "stream": REQUIRED,
         "contours": CONDITIONAL,   # 12.7.3 relief "best suited"
         "peaks": CONDITIONAL,      # 12.7.4 spot elevations when shown
         "ad": REQUIRED,            # 12.10.1 "all aerodromes ... runway pattern"
         "towers": REQUIRED,        # 12.10.2 obstacles
         "pylons": CONDITIONAL, "wind": CONDITIONAL, "buildings": CONDITIONAL,
         "mil_land": REQUIRED, "mil_danger": REQUIRED,  # 12.10.3 prohibited/restricted/danger
         "rn_vor": CONDITIONAL, "rn_all": CONDITIONAL,  # 12.10.6 radio aids
         "airstrip": CONDITIONAL, "heliport": CONDITIONAL, "ad_closed": CONDITIONAL,
     }},
    {"code": "WAC", "name": "World Aeronautical Chart — ICAO 1:1 000 000",
     "ref": "Annex 4 Ch. 16, 16.7 (16-4 ff.); Doc 8697 7.16",
     "layers": {**_VFR_HYDRO, **_VFR_CULT, **_VFR_MISC, **_VFR_RELIEF,
                **_AD_BASE, **_RADIO_BASE, **_RESTRICTED,
                "rock": CONDITIONAL,       # 16.7.6.3 reefs, shoals, rocky ledges
                "dry_bed": CONDITIONAL,    # Appendix 2 sym 39 "Dry lake bed"
                "glacier": CONDITIONAL, "swamp": CONDITIONAL, "dam": CONDITIONAL,
                "ferry": CONDITIONAL, "pipeline": CONDITIONAL,
                "coastguard": CONDITIONAL, "mine": CONDITIONAL, "ranger": CONDITIONAL,
                "stadium": CONDITIONAL, "ruins": CONDITIONAL, "fort": CONDITIONAL,
                "church": CONDITIONAL, "mosque": CONDITIONAL, "pagoda": CONDITIONAL,
                "temple": CONDITIONAL, "fence": OPTIONAL, "tank": CONDITIONAL,
                "nuclear": CONDITIONAL, "oil": CONDITIONAL, "powerline": CONDITIONAL,
                "cableway": CONDITIONAL,   # 17.7.4-style permanent cable installations
                "marine_light": CONDITIONAL, "lightship": CONDITIONAL,
                "runway": CONDITIONAL, "helipad": CONDITIONAL,
     }},
    {"code": "A500K", "name": "Aeronautical Chart — ICAO 1:500 000",
     "ref": "Annex 4 Ch. 17, 17.7 (17-3 ff.); Doc 8697 7.17",
     "layers": {**_VFR_HYDRO, **_VFR_CULT, **_VFR_MISC, **_VFR_RELIEF,
                **_AD_BASE, **_RADIO_BASE, **_RESTRICTED,
                "rail_stn": REQUIRED,      # 17.7 rail stations (16.7-level plus)
                "lookout": REQUIRED,       # 17.7 lookout towers
                "rock": CONDITIONAL, "glacier": CONDITIONAL, "swamp": CONDITIONAL,
                "dam": CONDITIONAL, "ferry": CONDITIONAL, "pipeline": CONDITIONAL,
                "coastguard": CONDITIONAL, "mine": CONDITIONAL, "ranger": CONDITIONAL,
                "stadium": CONDITIONAL, "ruins": CONDITIONAL, "fort": CONDITIONAL,
                "church": CONDITIONAL, "mosque": CONDITIONAL, "pagoda": CONDITIONAL,
                "temple": CONDITIONAL, "fence": OPTIONAL, "tank": CONDITIONAL,
                "nuclear": CONDITIONAL, "oil": CONDITIONAL, "powerline": CONDITIONAL,
                "cableway": CONDITIONAL, "marine_light": CONDITIONAL,
                "lightship": CONDITIONAL, "runway": CONDITIONAL, "helipad": CONDITIONAL,
     }},
    {"code": "ANCS", "name": "Aeronautical Navigation Chart — ICAO Small Scale",
     "ref": "Annex 4 Ch. 18, 18.6 (18-3 ff.); Doc 8697 7.18",
     "layers": {
         "builtup": REQUIRED, "places": REQUIRED, "rail": REQUIRED,
         "dual": REQUIRED, "primary": REQUIRED, "secondary": REQUIRED,
         "lighthouse": CONDITIONAL, "lookout": CONDITIONAL, "towers": CONDITIONAL,
         "border": REQUIRED, "shore": REQUIRED, "lakes": REQUIRED,
         "river": REQUIRED, "contours": REQUIRED, "peaks": CONDITIONAL,
         "ad": REQUIRED, "rn_vor": CONDITIONAL, "rn_all": CONDITIONAL,
         "mil_land": CONDITIONAL, "mil_danger": CONDITIONAL,
     }},
    {"code": "PLOT", "name": "Plotting Chart — ICAO",
     "ref": "Annex 4 Ch. 19, 19.7 (19-3 ff.); Doc 8697 7.19",
     "layers": {
         "shore": REQUIRED, "lakes": REQUIRED, "river": REQUIRED,
         "peaks": CONDITIONAL, "survey": CONDITIONAL,  # spot elevations of hazards
         "places": REQUIRED,        # large cities and towns
         "ad": REQUIRED,            # 19.9 aerodromes
         "rn_vor": CONDITIONAL, "rn_all": CONDITIONAL,  # selected radio aids
         "border": CONDITIONAL,
     }},
    {"code": "ATCSMA", "name": "ATC Surveillance Minimum Altitude Chart — ICAO",
     "ref": "Annex 4 Ch. 21, 21.6 (21-2 ff.); Doc 8697 7.21",
     "layers": {
         "contours": VERIFY, "peaks": VERIFY,       # relief as needed for altitude assignment
         "ad": REQUIRED, "towers": CONDITIONAL, "buildings": CONDITIONAL,
         "shore": CONDITIONAL, "lakes": CONDITIONAL, "river": CONDITIONAL,
         "places": CONDITIONAL, "mil_land": CONDITIONAL, "mil_danger": CONDITIONAL,
     },
     "note": "Primary content (sector altitudes, radar coverage) comes from the "
             "AIP. OSM contributes base topography only; statuses need verification."},
]

BY_CODE = {c["code"]: c for c in CHART_TYPES}

STATUS_ORDER = (REQUIRED, CONDITIONAL, OPTIONAL, VERIFY, NOT_APPLICABLE)


def chart_status(chart_code, item_id):
    """Status of one catalog item for one chart type ('' if not listed)."""
    c = BY_CODE.get(chart_code)
    if not c:
        return ""
    return c["layers"].get(item_id, NOT_APPLICABLE)


def chart_layers(chart_code, statuses=(REQUIRED, CONDITIONAL, OPTIONAL, VERIFY)):
    """[item_id, ...] for a chart type, filtered by status."""
    c = BY_CODE[chart_code]
    return [i for i, st in c["layers"].items() if st in statuses]


def bundle_for(chart_code):
    """Back-compatible bundle dict as the old annex4.BUNDLES produced."""
    c = BY_CODE[chart_code]
    return {"ref": c["ref"],
            "items": sorted(set(chart_layers(chart_code,
                                             (REQUIRED, CONDITIONAL, OPTIONAL, VERIFY))))}


# ---------------------------------------------------------------------------
# Document comparison (requirement 4): keep both original names + sources.
# ---------------------------------------------------------------------------
def compare_documents():
    """Compare layer names across Annex 4 and Doc 8697.

    Returns a dict with categories:
      both / annex4_only / doc8697_only / needs_verification / duplicates
    Each entry: {id, annex4_name, doc8697_name, note}.
    """
    from . import annex4
    out = {"both": [], "annex4_only": [], "doc8697_only": [],
           "needs_verification": [], "duplicates": []}
    seen_names = {}
    for it in annex4.BY_ID.values():
        a4 = it.get("src_annex4")
        d86 = it.get("src_doc8697")
        entry = {"id": it["id"], "name": it["name"],
                 "annex4_name": a4 or "", "doc8697_name": d86 or ""}
        if not annex4.BY_ID[it["id"]]["official"]:
            # No verbatim ICAO name established: needs manual verification
            # even when a section reference exists (e.g. tower, servicing).
            out["needs_verification"].append(entry)
        elif a4 and d86:
            out["both"].append(entry)
        elif a4:
            out["annex4_only"].append(entry)
        elif d86:
            out["doc8697_only"].append(entry)
        else:
            out["needs_verification"].append(entry)
        key = it["name"].lower().strip()
        seen_names.setdefault(("working", key), []).append(it["id"])
        for off in it.get("official", []):
            seen_names.setdefault(("official", off.strip().lower()),
                                  []).append(it["id"])
    for (kind, name), ids in seen_names.items():
        if len(ids) > 1:
            out["duplicates"].append({"name": name, "ids": ids,
                                      "kind": kind})
    # Equivalent-but-differently-named pairs: NEVER merged automatically.
    # They stay listed under both sources; the UI shows each original name.
    return out


# ---------------------------------------------------------------------------
# Validation report (requirements 6 and 7)
# ---------------------------------------------------------------------------
def report_rows(item_ids, chart_code=None):
    """Rows for the CSV/validation report, one per (item, representation)."""
    from . import annex4
    from . import layer_names
    rows = []
    for iid in item_ids:
        it = annex4.BY_ID.get(iid)
        if not it:
            continue
        if chart_code:
            st = chart_status(chart_code, iid)
            if st == NOT_APPLICABLE:
                continue
        else:
            st = "n/a (no chart type selected)"
        for kind, kdesc in (("point", "point"), ("line", "line"),
                            ("polygon", "polygon / multipolygon")):
            if kind not in it.get("geom", ("point", "line", "polygon")):
                continue
            doc_name = layer_names.LAYER_NAMES.get(iid)
            rows.append({
                "layer": it["name"],
                "export_name": doc_name if doc_name is not None
                else f"FLAGGED (no documented match): {it['name']}",
                "official_names": "; ".join(it.get("official", ())),
                "geometry": kdesc,
                "chart_type": chart_code or "",
                "status": st,
                "annex4_source": it.get("src_annex4", ""),
                "doc8697_source": it.get("src_doc8697", ""),
                "osm_filter": annex4.summary(it),
                "notes": it.get("note", ""),
                "warning": it.get("warning", ""),
            })
    return rows


def export_report_csv(path, item_ids, chart_code=None):
    """Write the validation report; returns the path. Raises on failure."""
    rows = report_rows(item_ids, chart_code)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else
                           ["layer", "export_name", "official_names", "geometry",
                            "chart_type", "status", "annex4_source",
                            "doc8697_source", "osm_filter", "notes", "warning"])
        w.writeheader()
        w.writerows(rows)
    return path


def export_comparison_csv(path):
    """Write the Annex 4 vs Doc 8697 layer-name comparison; returns path."""
    from . import annex4
    comp = compare_documents()
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["category", "id", "working_name", "annex4_name",
                    "doc8697_name", "note"])
        for cat, title in (("both", "in both documents"),
                           ("annex4_only", "only in Annex 4"),
                           ("doc8697_only", "only in Doc 8697"),
                           ("needs_verification", "needs manual verification")):
            for e in comp[cat]:
                it = annex4.BY_ID[e["id"]]
                w.writerow([title, e["id"], e["name"], e["annex4_name"],
                            e["doc8697_name"], it.get("warning", "")])
        for d in comp["duplicates"]:
            w.writerow(["duplicate working name", "; ".join(d["ids"]), d["name"],
                        "", "", "verify whether these are truly the same feature"])
    return path


# ---------------------------------------------------------------------------
# Topographic focus (chart-based selection shows TOPOGRAPHIC layers only).
# These catalog groups are aeronautical data (Appendix 2 symbol groups):
# aerodromes (84-95), radio navigation aids (99-110), obstacles/visual aids
# (130-144), aerodrome chart symbols (145-161) and obstacle-chart symbols
# (162-170). They are NOT topographic data: aerodrome surfaces, navaids and
# official obstacles come from surveys / the AIP, not from OSM, so chart
# presets no longer add them. They remain available in the full catalogue.
# ---------------------------------------------------------------------------
_AERONAUTICAL_GROUPS = (
    "Aerodromes (84-98)",
    "Radio navigation aids (99-110)",
    "Obstacles, landmarks, visual aids (130-144)",
    "Aerodrome / Heliport / Ground movement charts (145-161)",
    "Aerodrome Obstacle charts A, B, C (162-170)",
)


def _aeronautical_ids():
    """Aeronautical symbol ids per Appendix 2: symbols 84 and above belong to
    the aerodrome (84-95), radio-aid (99-110), ATS/airspace (111-129),
    obstacle (130-144) and aerodrome/obstacle-chart (145-170) symbol groups.
    Topographic data is symbols 1-83 (topography, hydrography, culture).
    Items without a symbol number are classified by their catalog group."""
    import re as _re
    from . import annex4
    out = set()
    for i, it in annex4.BY_ID.items():
        m = _re.fullmatch(r"(\d{1,3})(?:-\d{1,3})?", it["sym"].strip())
        if m:
            if int(m.group(1)) >= 84:
                out.add(i)
        else:   # sym is a section reference ("13.6") or text: group decides
            if it["group"] in _AERONAUTICAL_GROUPS or it["sym"] == "13.6":
                out.add(i)
    return out


AERONAUTICAL_IDS = _aeronautical_ids()


def chart_layers_topo(chart_code, statuses=(REQUIRED, CONDITIONAL, OPTIONAL, VERIFY)):
    """Topographic layers of a chart type only (aeronautical ids excluded)."""
    return [i for i in chart_layers(chart_code, statuses)
            if i not in AERONAUTICAL_IDS]


def chart_topo_summary(chart_code):
    """(n_topo, n_aero) layer counts for the preset note."""
    c = BY_CODE[chart_code]
    listed = {i for i, st in c["layers"].items()
              if st in (REQUIRED, CONDITIONAL, OPTIONAL, VERIFY)}
    topo = listed - AERONAUTICAL_IDS
    return len(topo), len(listed & AERONAUTICAL_IDS)
