"""ICAO Annex 4 (Aeronautical Charts) topographic layers mapped to OSM tags.

Symbol numbers refer to Annex 4, Appendix 2 (ICAO chart symbols).
Pure Python (no QGIS imports).
"""
import re

# Each item: id, group, sym, name, rows [(key, value)], note
_G_TOPO = "Topography (symbols 1-18)"
_G_HYDRO = "Hydrography (symbols 19-46)"
_G_CULT = "Culture: built-up areas, railroads, roads (47-62)"
_G_MISC = "Culture: miscellaneous (63-83)"
_G_AD = "Aerodromes (84-98)"
_G_NAV = "Radio navigation aids (99-110)"
_G_OBS = "Obstacles, landmarks, visual aids (130-144)"
_G_ADC = "Aerodrome / Heliport / Ground movement charts (145-161)"
_G_OBC = "Aerodrome Obstacle charts A, B, C (162-170)"

_WOOD = '[~"^(natural|landuse)$"~"^(wood|forest)$"]'

ITEMS = [
    # ---------------- Topography
    ("contours", _G_TOPO, "1-2", "Contours (rare in OSM - use a DEM)", [("contour", "elevation")], "OSM has very few contour lines; derive them from a DEM (SRTM/Copernicus) in QGIS."),
    ("cliff", _G_TOPO, "4", "Bluff, cliff, escarpment", [("natural", "cliff")], ""),
    ("lava", _G_TOPO, "5", "Lava flow", [("geological", "volcanic_lava_field")], "Sparse."),
    ("dunes", _G_TOPO, "6", "Sand dunes", [("natural", "dune")], ""),
    ("sand", _G_TOPO, "7", "Sand area / beach", [("natural", "sand|beach")], ""),
    ("gravel", _G_TOPO, "8", "Gravel, shingle, scree", [("natural", "shingle|scree")], ""),
    ("levee", _G_TOPO, "9", "Levee / dyke", [("man_made", "dyke")], ""),
    ("pass", _G_TOPO, "11", "Mountain pass", [("mountain_pass", "yes")], ""),
    ("peaks", _G_TOPO, "12-14", "Spot elevations: peaks, volcanoes, saddles", [("natural", "peak|volcano|saddle")], "Elevation is in the 'ele' attribute."),
    ("survey", _G_TOPO, "13", "Spot elevations: survey / trig points", [("man_made", "survey_point")], "Elevation is in the 'ele' attribute."),
    ("wood", _G_TOPO, "15-17", "Wooded areas (forest, wood)", [(_WOOD, "")], "Heavy in forested regions."),
    ("conifer", _G_TOPO, "15", "Coniferous trees", [(_WOOD + '["leaf_type"="needleleaved"]', "")], ""),
    ("broadleaf", _G_TOPO, "16", "Other trees: broadleaved / mixed", [(_WOOD + '["leaf_type"~"^(broadleaved|mixed)$"]', "")], ""),
    # ---------------- Hydrography
    ("shore", _G_HYDRO, "19-20", "Shore line (coastline)", [("natural", "coastline")], ""),
    ("tidal", _G_HYDRO, "21", "Tidal flats", [("natural", "mud"), ('["natural"="wetland"]["wetland"="tidalflat"]', "")], ""),
    ("reef", _G_HYDRO, "22", "Coral reefs and ledges", [("natural", "reef")], ""),
    ("river", _G_HYDRO, "23", "Large rivers (lines)", [("waterway", "river")], ""),
    ("river_a", _G_HYDRO, "23", "Large rivers (areas)", [("water", "river")], ""),
    ("stream", _G_HYDRO, "24-26", "Small rivers and streams", [("waterway", "stream")], ""),
    ("nonper", _G_HYDRO, "25", "Non-perennial rivers and streams", [('["waterway"~"^(river|stream)$"]["intermittent"="yes"]', "")], ""),
    ("rapids", _G_HYDRO, "27", "Rapids", [("waterway", "rapids")], ""),
    ("falls", _G_HYDRO, "28", "Falls", [("waterway", "waterfall")], ""),
    ("canal", _G_HYDRO, "29", "Canals", [("waterway", "canal")], ""),
    ("canal_ab", _G_HYDRO, "30", "Abandoned canals", [("abandoned:waterway", "canal")], ""),
    ("lakes", _G_HYDRO, "31", "Lakes (perennial)", [("water", "lake")], ""),
    ("water_all", _G_HYDRO, "31", "All water bodies (natural=water)", [("natural", "water")], "Includes ponds and river areas: can be heavy."),
    ("lakes_np", _G_HYDRO, "32", "Lakes (non-perennial)", [('["natural"="water"]["intermittent"="yes"]', "")], ""),
    ("salt_lake", _G_HYDRO, "33", "Salt lakes", [('["natural"="water"]["salt"="yes"]', "")], ""),
    ("salt_pan", _G_HYDRO, "34", "Salt pans (evaporators)", [("landuse", "salt_pond")], ""),
    ("swamp", _G_HYDRO, "35", "Swamp / wetland", [("natural", "wetland")], ""),
    ("rice", _G_HYDRO, "36", "Rice fields", [("crop", "rice")], ""),
    ("spring", _G_HYDRO, "37", "Springs, wells, water holes", [("natural", "spring|hot_spring"), ("man_made", "water_well")], ""),
    ("reservoir", _G_HYDRO, "38", "Reservoirs", [('[~"^(water|landuse)$"~"^reservoir$"]', "")], ""),
    ("wash", _G_HYDRO, "40", "Wash / wadi", [("waterway", "wadi")], ""),
    ("shoal", _G_HYDRO, "41", "Shoals", [("natural", "shoal")], ""),
    ("glacier", _G_HYDRO, "42", "Glaciers and ice caps", [("natural", "glacier")], ""),
    ("rock", _G_HYDRO, "44", "Isolated rocks, stone, bare rock", [("natural", "rock|stone|bare_rock")], "Annex 4 16.7.6.3 / 17.7.6.3: rocky ledges, isolated rocks, stone and similar areas."),
    ("rock_sea", _G_HYDRO, "44-45", "Charted rocks / rock awash (seamark)", [("seamark:type", "rock")], ""),
    ("ocean", _G_HYDRO, "txt", "Ocean (polygons)",
     [("place", "ocean"), ('["natural"="water"]["water"~"^(sea|ocean)$"]', "")],
     "Couche polygone ocean demandee par l'utilisateur. Ocean n'a pas de symbole "
     "Appendix 2 (l'eau est definie par la shore line, syms 19-20); OSM mappe les "
     "oceans via place=ocean et water=sea/ocean."),
    ("dry_bed", _G_HYDRO, "39", "Dry lake bed", [("natural", "water"), ('["seasonal"="yes"]', "")],
     "Approximated by seasonal water bodies; verify locally."),
    # ---------------- Culture
    ("places", _G_CULT, "47-49", "Cities, towns, villages (points)", [("place", "city|town|village")], "Size class is in the 'place' attribute."),
    ("builtup", _G_CULT, "47-49", "Built-up area outlines", [("landuse", "residential|commercial|industrial|retail")], "Annex 4 asks for built-up outlines, not city limits."),
    ("buildings", _G_CULT, "50", "Buildings (HEAVY)", [("building", "")], "Very large in cities: use a small extent."),
    ("rail", _G_CULT, "51-52", "Railroads", [("railway", "rail")], ""),
    ("rail_con", _G_CULT, "53", "Railroads under construction", [("railway", "construction")], ""),
    ("rail_br", _G_CULT, "54", "Railroad bridges", [('["railway"="rail"]["bridge"]["bridge"!="no"]', "")], ""),
    ("rail_tun", _G_CULT, "55", "Railroad tunnels", [('["railway"="rail"]["tunnel"]["tunnel"!="no"]', "")], ""),
    ("rail_stn", _G_CULT, "56", "Railroad stations", [("railway", "station")], ""),
    ("dual", _G_CULT, "57", "Dual highways (motorway, trunk)", [("highway", "motorway|trunk")], ""),
    ("primary", _G_CULT, "58", "Primary roads", [("highway", "primary")], ""),
    ("secondary", _G_CULT, "59", "Secondary roads", [("highway", "secondary|tertiary")], ""),
    ("trail", _G_CULT, "60", "Trails (tracks)", [("highway", "track")], ""),
    ("road_br", _G_CULT, "61", "Road bridges", [('["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]["bridge"]["bridge"!="no"]', "")], ""),
    ("road_tun", _G_CULT, "62", "Road tunnels", [('["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]["tunnel"]["tunnel"!="no"]', "")], ""),
    ("road_con", _G_CULT, "txt", "Roads under construction", [("highway", "construction")], "Annex 4 17.7.3.1 note."),
    # ---------------- Miscellaneous culture
    ("border", _G_MISC, "63", "International boundaries", [('way["boundary"="administrative"]["admin_level"="2"]', "")], "Land and maritime borders as lines."),
    ("border_other", _G_MISC, "txt", "Other administrative boundaries (levels 3-4)", [('way["boundary"="administrative"]["admin_level"~"^(3|4)$"]', "")], "Annex 4 17.7.5: other boundaries may be shown."),
    ("mil_land", _G_MISC, "128", "Military land (possible restricted areas)", [("landuse", "military")], "Official prohibited / restricted / danger areas come from the AIP."),
    ("mil_danger", _G_MISC, "128", "Military danger areas and ranges", [("military", "danger_area|range")], ""),
    ("fence", _G_MISC, "65", "Fences (HEAVY)", [("barrier", "fence")], ""),
    ("phone", _G_MISC, "66", "Telegraph / telephone lines", [("communication", "line")], "Sparse in OSM."),
    ("dam", _G_MISC, "67", "Dams", [('[~"^(waterway|man_made)$"~"^dam$"]', "")], ""),
    ("ferry", _G_MISC, "68", "Ferry routes", [("route", "ferry")], ""),
    ("pipeline", _G_MISC, "69", "Pipelines", [("man_made", "pipeline")], ""),
    ("oil", _G_MISC, "70", "Oil or gas wells", [("man_made", "petroleum_well")], ""),
    ("tank", _G_MISC, "71", "Tank farms", [("man_made", "storage_tank")], ""),
    ("nuclear", _G_MISC, "72", "Nuclear power stations", [('["power"="plant"]["plant:source"="nuclear"]', "")], ""),
    ("coastguard", _G_MISC, "73", "Coast guard stations", [('[~"^(amenity|emergency|office)$"~"^coast_guard$"]', "")], ""),
    ("lookout", _G_MISC, "74", "Lookout towers", [("tower:type", "observation")], ""),
    ("mine", _G_MISC, "75", "Mines and quarries", [('[~"^(landuse|man_made|industrial)$"~"^(quarry|mineshaft|adit|mine)$"]', "")], ""),
    ("ranger", _G_MISC, "76", "Forest ranger stations", [("amenity", "ranger_station")], ""),
    ("stadium", _G_MISC, "77", "Race tracks and stadiums", [("leisure", "stadium|track")], ""),
    ("ruins", _G_MISC, "78", "Ruins", [("historic", "ruins")], ""),
    ("fort", _G_MISC, "79", "Forts", [("historic", "fort|castle")], ""),
    ("church", _G_MISC, "80", "Churches", [('["amenity"="place_of_worship"]["religion"="christian"]', "")], ""),
    ("mosque", _G_MISC, "81", "Mosques", [('["amenity"="place_of_worship"]["religion"="muslim"]', "")], ""),
    ("pagoda", _G_MISC, "82", "Pagodas", [("building", "pagoda")], ""),
    ("temple", _G_MISC, "83", "Temples", [("building", "temple")], ""),
    # ---------------- Aerodromes
    ("ad", _G_AD, "84-90", "Aerodromes (civil / military)", [("aeroway", "aerodrome")], "Type is in 'aerodrome:type' / 'military' attributes."),
    ("ad_mil", _G_AD, "86-87", "Military airfields", [("military", "airfield")], ""),
    ("airstrip", _G_AD, "84-93", "Airstrips", [("aeroway", "airstrip")], ""),
    ("heliport", _G_AD, "94", "Heliports", [("aeroway", "heliport")], ""),
    ("ad_closed", _G_AD, "91", "Abandoned / closed aerodromes", [('[~"^(abandoned|disused):aeroway$"~"^aerodrome$"]', "")], ""),
    # ---------------- Radio nav
    ("rn_all", _G_NAV, "99", "All radio navigation beacons (airmark=beacon)", [("airmark", "beacon")], "Radio navaids are inconsistently tagged in OSM: check against the AIP."),
    ("rn_vor", _G_NAV, "101,103,107", "VOR, DVOR, VOR/DME, VORTAC", [('["airmark"="beacon"]["beacon:type"~"VOR",i]', "")], ""),
    ("rn_ndb", _G_NAV, "100", "NDB", [('["airmark"="beacon"]["beacon:type"~"^NDB$",i]', "")], ""),
    ("rn_dme", _G_NAV, "102-103", "DME", [('["airmark"="beacon"]["beacon:type"~"DME",i]', "")], ""),
    ("rn_tacan", _G_NAV, "106-107", "TACAN / VORTAC", [('["airmark"="beacon"]["beacon:type"~"TACAN|VORTAC",i]', "")], ""),
    ("rn_ils", _G_NAV, "108", "ILS (localizer / glideslope)", [('["airmark"="beacon"]["beacon:type"~"^ILS$",i]', "")], ""),
    ("rn_marker", _G_NAV, "109", "Radio marker beacons", [('["airmark"="beacon"]["beacon:type"~"^(OM|MM|IM|marker)$",i]', "")], ""),
    # ---------------- Obstacles / landmarks
    ("towers", _G_OBS, "130-136", "Towers, masts, chimneys, cranes", [("man_made", "tower|mast|communications_tower|chimney|water_tower|crane|flare|silo")], "Height is in the 'height' attribute when mapped."),
    ("pylons", _G_OBS, "130", "Power pylons", [("power", "tower")], ""),
    ("powerline", _G_OBS, "137", "Prominent transmission lines", [("power", "line")], ""),
    ("wind", _G_OBS, "140-141", "Wind turbines", [('["power"="generator"]["generator:source"="wind"]', "")], ""),
    ("cableway", _G_OBS, "txt", "Cable cars / aerialways", [("aerialway", "")], "Annex 4 17.7.4: permanent cable car installations."),
    ("lighthouse", _G_OBS, "142-144", "Isolated lighthouses", [("man_made", "lighthouse")], ""),
    ("marine_light", _G_OBS, "142", "Marine lights", [('["seamark:type"~"^light_(major|minor|float)$"]', "")], ""),
    ("lightship", _G_OBS, "144", "Lightships (light vessels)", [("seamark:type", "light_vessel")], ""),
    ("tallbldg", _G_OBS, "130", "Tall buildings (height >= 40)", [('["building"]["height"~"^([4-9][0-9]|[1-9][0-9]{2,})"]', "")], "Only buildings with a 'height' tag."),
    # ---------------- Aerodrome chart
    ("runway", _G_ADC, "145-148", "Runways", [("aeroway", "runway")], "Surface type is in the 'surface' attribute."),
    ("taxiway", _G_ADC, "149", "Taxiways and taxilanes", [("aeroway", "taxiway|taxilane")], ""),
    ("apron", _G_ADC, "149", "Aprons", [("aeroway", "apron")], ""),
    ("parking", _G_ADC, "149", "Parking positions and gates", [("aeroway", "parking_position|gate")], ""),
    ("helipad", _G_ADC, "150", "Helicopter alighting areas", [("aeroway", "helipad")], ""),
    ("holding", _G_ADC, "159-160", "Holding positions", [("aeroway", "holding_position")], ""),
    ("adbldg", _G_ADC, "164", "Terminals and hangars", [("aeroway", "terminal|hangar")], ""),
    ("adarea", _G_ADC, "145-149", "Aerodrome surfaces (area mapping)", [("area:aeroway", "")], ""),
    ("windsock", _G_ADC, "156-157", "Landing direction indicators / windsocks", [("aeroway", "windsock")], ""),
    ("vasi", _G_ADC, "13.6", "Visual approach slope indicators / visual aids (PAPI, VASI)", [("aeroway", "navigationaid")], "aeroway=navigationaid is for VISUAL aids (Annex 4 13.6.1 n)."),
    ("stopway", _G_ADC, "148-169", "Stopways", [("aeroway", "stopway")], ""),
    ("tower", _G_ADC, "13.6", "Control towers", [('[~"^aeroway$"~"^(tower|control_tower|control_center)$"]', "")], ""),
    ("servicing", _G_ADC, "13.6", "Aircraft servicing: fuel, jet bridges", [("aeroway", "fuel|jet_bridge")], "Annex 4 13.6.1 q."),
    # ---------------- Obstacle chart
    ("trees", _G_OBC, "162", "Trees and shrubs (HEAVY)", [("natural", "tree|tree_row|scrub")], ""),
    ("poles", _G_OBC, "163", "Poles (power poles)", [("power", "pole")], ""),
    ("ohcable", _G_OBC, "166", "Overhead lines and cables", [("power", "line|minor_line|cable")], ""),
]

BY_ID = {}
for _id, _grp, _sym, _name, _rows, _note in ITEMS:
    BY_ID[_id] = {"id": _id, "group": _grp, "sym": _sym, "name": _name,
                  "rows": _rows, "note": _note}


def groups():
    """[(group_name, [item, ...])] in declaration order."""
    out = {}
    for it in BY_ID.values():
        out.setdefault(it["group"], []).append(it)
    return list(out.items())


def summary(item):
    return "  +  ".join(f"{k}={v}" if v else k for k, v in item["rows"])


def rows_with_labels(item):
    """[(key, value, layer_label)] for one item (unique label per row)."""
    base = re.sub(r"[^A-Za-z0-9]+", "_", f"A4_{item['sym']}_{item['name']}").strip("_")[:48]
    n = len(item["rows"])
    return [(k, v, base if n == 1 else f"{base}_{i + 1}")
            for i, (k, v) in enumerate(item["rows"])]


# ---------------------------------------------------------------------------
# Source traceability overlay (requirement 6).
# "official"  : layer name(s) VERBATIM from ICAO Annex 4, Appendix 2, or from
#               the cited Annex 4 / Doc 8697 section. Never renamed.
# "src_annex4": Annex 4 section (+ Appendix 2 symbol numbers, APP 2-1..2-6).
# "src_doc8697": Doc 8697 Third Edition (2016) section.
# "geom"      : representations this feature can take (point/line/polygon).
#               A surface polygon and a centreline line are SEPARATE
#               representations and both are offered where documented.
# "warning"   : uncertainty that the user must verify (never auto-resolved).
# ---------------------------------------------------------------------------
_G_A2 = "Appendix 2 (APP 2-1)"
_META = {
    # Topography (Appendix 2 symbols 1-18, verbatim names)
    "contours": {"official": ["Contours", "Approximate contours"], "src_annex4": "Appendix 2 syms 1, 2 (APP 2-1)", "geom": ("line",), "warning": "OSM has almost no contours; derive from a DEM and state the source."},
    "cliff": {"official": ["Bluff, cliff or escarpment"], "src_annex4": "Appendix 2 sym 4 (APP 2-1)", "geom": ("line", "polygon")},
    "dunes": {"official": ["Sand dunes"], "src_annex4": "Appendix 2 sym 6 (APP 2-1)", "geom": ("point", "line", "polygon")},
    "sand": {"official": ["Sand area"], "src_annex4": "Appendix 2 sym 7 (APP 2-1)", "geom": ("polygon",)},
    "gravel": {"official": ["Gravel"], "src_annex4": "Appendix 2 sym 8 (APP 2-1)", "geom": ("polygon",)},
    "peaks": {"official": ["Spot elevation", "Spot elevation (of doubtful accuracy)", "Highest elevation on chart"], "src_annex4": "Appendix 2 syms 12-14 (APP 2-1)", "geom": ("point",), "warning": "3D: elevation is the 'ele' attribute, not geometry (OSM has no Z)."},
    "survey": {"official": ["Spot elevation"], "src_annex4": "Appendix 2 sym 13 (APP 2-1)", "geom": ("point",), "warning": "3D: elevation is the 'ele' attribute, not geometry."},
    "wood": {"official": ["Coniferous trees", "Other trees", "Palms"], "src_annex4": "Appendix 2 syms 15-17 (APP 2-1)", "geom": ("point", "polygon")},
    # Hydrography (19-46, verbatim)
    "shore": {"official": ["Shore line (reliable)", "Shore line (unreliable)"], "src_annex4": "Appendix 2 syms 19-20 (APP 2-1/2-2)", "geom": ("line",)},
    "river": {"official": ["Large river (perennial)"], "src_annex4": "Appendix 2 sym 23 (APP 2-2)", "geom": ("line", "polygon")},
    "river_a": {"official": ["Large river (perennial)"], "src_annex4": "Appendix 2 sym 23 (APP 2-2)", "geom": ("polygon",)},
    "stream": {"official": ["Small river (perennial)"], "src_annex4": "Appendix 2 sym 24 (APP 2-2)", "geom": ("line",)},
    "lakes": {"official": ["Lakes (perennial)"], "src_annex4": "Appendix 2 sym 31 (APP 2-2)", "geom": ("polygon",)},
    "lakes_np": {"official": ["Lakes (non-perennial)"], "src_annex4": "Appendix 2 sym 32 (APP 2-2)", "geom": ("polygon",)},
    "reservoir": {"official": ["Reservoir"], "src_annex4": "Appendix 2 sym 38 (APP 2-2)", "geom": ("polygon",)},
    "swamp": {"official": ["Swamp"], "src_annex4": "Appendix 2 sym 35 (APP 2-2)", "geom": ("polygon",)},
    # Culture (47-62, verbatim)
    "places": {"official": ["City or large town", "Town", "Village"], "src_annex4": "Appendix 2 syms 47-49 (APP 2-2)", "geom": ("point", "polygon")},
    "builtup": {"official": ["City or large town", "Town", "Village"], "src_annex4": "Appendix 2 syms 47-49 (APP 2-2)", "geom": ("polygon",), "warning": "OSM landuse=residential approximates the built-up outline; verify against imagery."},
    "buildings": {"official": ["Buildings"], "src_annex4": "Appendix 2 sym 50 (APP 2-2)", "geom": ("point", "polygon")},
    "rail": {"official": ["Railroad (single track)", "Railroad (two or more tracks)"], "src_annex4": "Appendix 2 syms 51-52 (APP 2-2)", "geom": ("line",)},
    "rail_stn": {"official": ["Railroad station"], "src_annex4": "Appendix 2 sym 56 (APP 2-2)", "geom": ("point", "polygon")},
    "dual": {"official": ["Dual highway"], "src_annex4": "Appendix 2 sym 57 (APP 2-2)", "geom": ("line", "polygon")},
    "primary": {"official": ["Primary road"], "src_annex4": "Appendix 2 sym 58 (APP 2-2)", "geom": ("line",)},
    "secondary": {"official": ["Secondary road"], "src_annex4": "Appendix 2 sym 59 (APP 2-2)", "geom": ("line",)},
    "trail": {"official": ["Trail"], "src_annex4": "Appendix 2 sym 60 (APP 2-2)", "geom": ("line",)},
    # Aerodromes (84-95, verbatim)
    "ad": {"official": ["Civil — Land", "Military — Land", "Joint civil and military — Land", "Aerodrome for use on charts on which aerodrome classification is not required"], "src_annex4": "Appendix 2 syms 84, 86, 88, 93 (APP 2-3)", "geom": ("point", "polygon")},
    "ad_mil": {"official": ["Military — Land"], "src_annex4": "Appendix 2 sym 86 (APP 2-3)", "geom": ("point", "polygon")},
    "airstrip": {"official": ["Runway pattern in lieu of the aerodrome symbol"], "src_annex4": "Appendix 2 sym 95 (APP 2-3)", "geom": ("line", "polygon")},
    "heliport": {"official": ["Heliport"], "src_annex4": "Appendix 2 sym 94 (APP 2-3)", "geom": ("point", "polygon")},
    "ad_closed": {"official": ["Abandoned or closed aerodrome"], "src_annex4": "Appendix 2 sym 91 (APP 2-3)", "geom": ("point", "polygon")},
    # Radio navigation aids (99-110, verbatim)
    "rn_vor": {"official": ["VHF omnidirectional radio range — VOR", "Collocated VOR and DME radio navigation aids — VOR/DME", "Collocated VOR and TACAN radio navigation aids — VORTAC"], "src_annex4": "Appendix 2 syms 101, 103, 107 (APP 2-3)", "geom": ("point",)},
    "rn_ndb": {"official": ["Non-directional radio beacon — NDB"], "src_annex4": "Appendix 2 sym 100 (APP 2-3)", "geom": ("point",)},
    "rn_dme": {"official": ["Distance measuring equipment — DME"], "src_annex4": "Appendix 2 sym 102 (APP 2-3)", "geom": ("point",)},
    "rn_tacan": {"official": ["UHF tactical air navigation aid — TACAN"], "src_annex4": "Appendix 2 sym 106 (APP 2-3)", "geom": ("point",)},
    "rn_ils": {"official": ["Instrument landing system — ILS"], "src_annex4": "Appendix 2 sym 108 (APP 2-3)", "geom": ("point",)},
    "rn_marker": {"official": ["Radio marker beacon"], "src_annex4": "Appendix 2 sym 109 (APP 2-3)", "geom": ("point",)},
    "rn_all": {"official": ["Basic radio navigation aid symbol"], "src_annex4": "Appendix 2 sym 99 (APP 2-3)", "geom": ("point",)},
    # ATS (111-129): airspace/procedures come from the AIP, not OSM
    "mil_land": {"official": ["Restricted airspace (prohibited, restricted or danger area)"], "src_annex4": "Appendix 2 sym 128 (APP 2-4)", "geom": ("line", "polygon"), "warning": "Official vertical limits and designation come from the AIP."},
    "mil_danger": {"official": ["Restricted airspace (prohibited, restricted or danger area)"], "src_annex4": "Appendix 2 sym 128 (APP 2-4)", "geom": ("line", "polygon"), "warning": "Official vertical limits and designation come from the AIP."},
    # Obstacles (130-141, verbatim)
    "towers": {"official": ["Obstacle", "Lighted obstacle", "Group obstacles", "Pole, tower, spire, antenna, etc."], "src_annex4": "Appendix 2 syms 130-132, 163 (APP 2-4/2-6)", "geom": ("point", "line", "polygon"), "warning": "3D: height is the 'height' attribute; obstacle data authority is the AIP."},
    "pylons": {"official": ["Obstacle"], "src_annex4": "Appendix 2 sym 130 (APP 2-4)", "geom": ("point", "line")},
    "powerline": {"official": ["Prominent transmission line", "Transmission line or overhead cable"], "src_annex4": "Appendix 2 syms 137, 166 (APP 2-4/2-6)", "geom": ("line",)},
    "wind": {"official": ["Wind turbine — unlighted and lighted", "Wind turbines — minor group and group in major area, lighted"], "src_annex4": "Appendix 2 syms 140-141 (APP 2-4)", "geom": ("point", "polygon")},
    "tallbldg": {"official": ["Obstacle", "Exceptionally high obstacle (optional symbol)"], "src_annex4": "Appendix 2 syms 130, 134 (APP 2-4)", "geom": ("polygon",), "warning": "Only buildings tagged with 'height'; verify heights before charting."},
    "lighthouse": {"official": ["Marine light", "Aeronautical ground light"], "src_annex4": "Appendix 2 syms 142-144 (APP 2-4)", "geom": ("point",)},
    # Aerodrome chart symbols (145-161, verbatim) — line AND polygon both kept
    "runway": {"official": ["Hard surface runway", "Pierced steel plank or steel mesh runway", "Unpaved runway", "Runway"], "src_annex4": "Appendix 2 syms 145-148 (APP 2-5), 175 (APP 2-6); 13.6.1 d)", "src_doc8697": "7.13 (Aerodrome/Heliport Chart data)", "geom": ("line", "polygon"), "warning": "Runway surface polygon AND runway centreline/strip line are separate representations — both layers are produced."},
    "taxiway": {"official": ["Taxiways and parking areas"], "src_annex4": "Appendix 2 sym 149 (APP 2-5); 13.6.1 g)", "src_doc8697": "7.13 / 7.14 / 7.15", "geom": ("line", "polygon"), "warning": "Taxiway surface polygon AND taxiway centreline line are separate representations — both layers are produced."},
    "apron": {"official": ["Taxiways and parking areas"], "src_annex4": "Appendix 2 sym 149 (APP 2-5); 13.6.1 e)", "geom": ("polygon",)},
    "parking": {"official": ["Taxiways and parking areas"], "src_annex4": "Appendix 2 sym 149 (APP 2-5); 13.6.1 e), i)", "geom": ("point", "polygon")},
    "helipad": {"official": ["Helicopter alighting area on an aerodrome"], "src_annex4": "Appendix 2 sym 150 (APP 2-5); 13.6.3 b)", "geom": ("point", "polygon")},
    "holding": {"official": ["Runway-holding position", "Intermediate holding position", "Stop bar"], "src_annex4": "Appendix 2 syms 158-160 (APP 2-5)", "geom": ("point", "line")},
    "windsock": {"official": ["Landing direction indicator (lighted)", "Landing direction indicator (unlighted)"], "src_annex4": "Appendix 2 syms 156-157 (APP 2-5)", "geom": ("point",)},
    "vasi": {"official": ["Point light", "Aeronautical ground light"], "src_annex4": "Appendix 2 syms 143, 154 (APP 2-5); 13.6.1 n)", "geom": ("point",)},
    "stopway": {"official": ["Stopway"], "src_annex4": "Appendix 2 syms 148, 169 (APP 2-5/2-6); 3.8.4.1", "geom": ("line", "polygon")},
    "adbldg": {"official": ["Building or large structure"], "src_annex4": "Appendix 2 sym 164 (APP 2-6); 13.6.1 q)", "geom": ("point", "polygon")},
    "adarea": {"official": ["Hard surface runway", "Taxiways and parking areas"], "src_annex4": "Appendix 2 syms 145-149 (APP 2-5)", "geom": ("polygon",)},
    "tower": {"official": [], "src_annex4": "13.6.1 (operational information); not symbol-numbered", "geom": ("point",), "warning": "No Appendix 2 symbol: name needs manual verification."},
    "servicing": {"official": [], "src_annex4": "13.6.1 q) 'aircraft servicing areas and buildings of operational significance'", "geom": ("point", "polygon"), "warning": "No Appendix 2 symbol: name needs manual verification."},
    # Obstacle chart symbols (162-170, verbatim)
    "trees": {"official": ["Tree or shrub"], "src_annex4": "Appendix 2 sym 162 (APP 2-6)", "geom": ("point", "line", "polygon")},
    "poles": {"official": ["Pole, tower, spire, antenna, etc."], "src_annex4": "Appendix 2 sym 163 (APP 2-6)", "geom": ("point",)},
    "ohcable": {"official": ["Transmission line or overhead cable"], "src_annex4": "Appendix 2 sym 166 (APP 2-6)", "geom": ("line",)},
}
for _id, _m in _META.items():
    if _id in BY_ID:
        BY_ID[_id].update(_m)
for _it in BY_ID.values():
    _it.setdefault("official", [])
    _it.setdefault("src_annex4", "")
    _it.setdefault("src_doc8697", "")
    _it.setdefault("geom", ("point", "line", "polygon"))
    _it.setdefault("warning", "")


def official_names(item):
    """Comma-joined official names, or the working name when unverified."""
    return ", ".join(item["official"]) if item["official"] else f"[unverified] {item['name']}"


# ---------------------------------------------------------------------------
# Export naming: verbatim ICAO names for exported files live in layer_names.py
# (generated from the source documents). This reverse map lets the download
# pipeline recover the catalog id of a layer row from its stored label.
# ---------------------------------------------------------------------------
def _label_to_id():
    out = {}
    for it in BY_ID.values():
        for _k, _v, label in rows_with_labels(it):
            out[label] = it["id"]
    return out


LABEL_TO_ID = _label_to_id()
