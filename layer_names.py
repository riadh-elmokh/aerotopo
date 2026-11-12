"""Verbatim ICAO layer names for exports - GENERATED from the source documents.

Source: ICAO Annex 4, Eleventh Edition (July 2009), Appendix 2 - ICAO Chart
Symbols, CATEGORY INDEX (APP 2-1..2-6), parsed programmatically from
an04_cons_en_2021.pdf. Doc 8697 (Third Edition, 2016) has no layer names of
its own; it references Annex 4 content, so the Appendix 2 names are
authoritative for exports.

None = no documented name could be matched confidently -> FLAGGED, never
invented. Do NOT hand-edit names: regenerate from the documents.
"""

# id -> verbatim Appendix 2 name. None = not confidently matched (FLAGGED).
LAYER_NAMES = {
    'contours': 'Contours',
    'cliff': 'Bluff, cliff or escarpment',
    'lava': 'Lava flow',
    'dunes': 'Sand dunes',
    'sand': 'Sand area',
    'gravel': 'Gravel',
    'levee': 'Levee or esker',
    'mtn_col': 'Mountain pass',
    'peaks': 'Highest elevation on chart',
    'survey': 'Spot elevation',
    'wood': 'Coniferous trees',
    'conifer': 'Coniferous trees (Coniferous trees)',
    'broadleaf': 'Other trees',
    'shore': 'Shore line (reliable)',
    'tidal': 'Tidal flats',
    'reef': 'Coral reefs and ledges',
    'river': 'Large river (perennial)',
    'river_a': 'Large river (perennial) (Large rivers areas)',
    'stream': 'Small river (perennial)',
    'nonper': 'Rivers and streams (non-perennial)',
    'rapids': 'Rapids',
    'falls': 'Falls',
    'canal': 'Canal',
    'canal_ab': 'Abandoned canal',
    'lakes': 'Lakes (perennial)',
    'water_all': 'Lakes (perennial) (All water bodies natural water)',
    'lakes_np': 'Lakes (non-perennial)',
    'salt_lake': 'Salt lake',
    'salt_pan': 'Salt pans (evaporator)',
    'swamp': 'Swamp',
    'rice': 'Rice field',
    'spring': 'Spring, well or water hole',
    'reservoir': 'Reservoir',
    'wash': 'Wash',
    'shoal': 'Shoals',
    'glacier': 'Glaciers and ice caps',
    'rock': 'Charted isolated rock',
    'rock_sea': 'Charted isolated rock (Charted rocks rock awash seamark)',
    'ocean': None,  # no Appendix 2 ocean symbol: sea surface defined by the shore line (syms 19-20); OSM supplies place=ocean / water=sea|ocean
    'dry_bed': 'Dry lake bed',
    'places': 'City or large town',
    'builtup': 'City or large town (Built up area outlines)',
    'buildings': 'Buildings',
    'rail': 'Railroad (single track)',
    'rail_con': 'Railroad (under construction)',
    'rail_br': 'Railroad bridge',
    'rail_tun': 'Railroad tunnel',
    'rail_stn': 'Railroad station',
    'dual': 'Dual highway',
    'primary': 'Primary road',
    'secondary': 'Secondary road',
    'trail': 'Trail',
    'road_br': 'Road bridge',
    'road_tun': 'Road tunnel',
    'road_con': None,
    'border': 'Boundaries (international)',
    'border_other': None,
    'mil_land': 'Restricted airspace (prohibited, restricted or danger area)',
    'mil_danger': 'Restricted airspace (prohibited, restricted or danger area) (Military danger areas and ranges)',
    'fence': 'Fence',
    'phone': 'Telegraph or telephone line (when a landmark)',
    'dam': 'Dam',
    'ferry': 'Ferry',
    'pipeline': 'Pipeline',
    'oil': 'Oil or gas field',
    'tank': 'Tank farms',
    'nuclear': 'Nuclear power station',
    'coastguard': 'Coast guard station',
    'lookout': 'Lookout tower',
    'mine': 'Mine',
    'ranger': 'Forest ranger station',
    'stadium': 'Race track or stadium',
    'ruins': 'Ruins',
    'fort': 'Fort',
    'church': 'Church',
    'mosque': 'Mosque',
    'pagoda': 'Pagoda',
    'temple': 'Temple',
    'ad': 'Civil — Land',
    'ad_mil': 'Military — Land',
    'airstrip': 'Civil — Land (Airstrips)',
    'heliport': 'Heliport',
    'ad_closed': 'Abandoned or closed aerodrome',
    'rn_all': 'Basic radio navigation aid symbol',
    'rn_vor': None,
    'rn_ndb': 'Non-directional radio beacon — NDB',
    'rn_dme': 'Distance measuring equipment — DME',
    'rn_tacan': 'UHF tactical air navigation aid — TACAN',
    'rn_ils': 'Instrument landing system — ILS',
    'rn_marker': 'Radio marker beacon',
    'towers': 'Obstacle',
    'pylons': 'Obstacle (Power pylons)',
    'powerline': 'Prominent transmission line',
    'wind': 'Wind turbine — unlighted and lighted',
    'cableway': None,
    'lighthouse': 'Marine light',
    'marine_light': 'Marine light (Marine lights)',
    'lightship': 'Lightship',
    'tallbldg': 'Obstacle (Tall buildings height 40)',
    'runway': 'Hard surface runway',
    'taxiway': 'Taxiways and parking areas',
    'apron': 'Taxiways and parking areas (Aprons)',
    'parking': 'Taxiways and parking areas (Parking positions and gates)',
    'helipad': 'Helicopter alighting area on an aerodrome',
    'holding': 'Runway-holding position',
    'adbldg': 'Building or large structure',
    'adarea': 'Hard surface runway (Aerodrome surfaces area mapping)',
    'windsock': 'Landing direction indicator (lighted)',
    'vasi': None,
    'stopway': 'Stopway',
    'tower': None,
    'servicing': None,
    'trees': 'Tree or shrub',
    'poles': 'Pole, tower, spire, antenna, etc.',
    'ohcable': 'Transmission line or overhead cable',
}

# id -> reason the name is flagged.
FLAGGED = {
    'conifer': "verbatim name 'Coniferous trees' also covers 'wood'; working name appended in parentheses to keep both exported layers unique",
    'river_a': "verbatim name 'Large river (perennial)' also covers 'river'; working name appended in parentheses to keep both exported layers unique",
    'water_all': "verbatim name 'Lakes (perennial)' also covers 'lakes'; working name appended in parentheses to keep both exported layers unique",
    'rock_sea': "verbatim name 'Charted isolated rock' also covers 'rock'; working name appended in parentheses to keep both exported layers unique",
    'ocean': "sym field 'txt' is a section reference, not an Appendix 2 symbol number; no documented layer name - needs verification",
    'builtup': "verbatim name 'City or large town' also covers 'places'; working name appended in parentheses to keep both exported layers unique",
    'road_con': "sym field 'txt' is a section reference, not an Appendix 2 symbol number; no documented layer name - needs verification",
    'border_other': "sym field 'txt' is a section reference, not an Appendix 2 symbol number; no documented layer name - needs verification",
    'mil_danger': "verbatim name 'Restricted airspace (prohibited, restricted or danger area)' also covers 'mil_land'; working name appended in parentheses to keep both exported layers unique",
    'airstrip': "verbatim name 'Civil — Land' also covers 'ad'; working name appended in parentheses to keep both exported layers unique",
    'rn_vor': "sym field '101,103,107' is a section reference, not an Appendix 2 symbol number; no documented layer name - needs verification",
    'pylons': "verbatim name 'Obstacle' also covers 'towers'; working name appended in parentheses to keep both exported layers unique",
    'cableway': "sym field 'txt' is a section reference, not an Appendix 2 symbol number; no documented layer name - needs verification",
    'marine_light': "verbatim name 'Marine light' also covers 'lighthouse'; working name appended in parentheses to keep both exported layers unique",
    'tallbldg': "verbatim name 'Obstacle' also covers 'towers'; working name appended in parentheses to keep both exported layers unique",
    'apron': "verbatim name 'Taxiways and parking areas' also covers 'taxiway'; working name appended in parentheses to keep both exported layers unique",
    'parking': "verbatim name 'Taxiways and parking areas' also covers 'taxiway'; working name appended in parentheses to keep both exported layers unique",
    'adarea': "verbatim name 'Hard surface runway' also covers 'runway'; working name appended in parentheses to keep both exported layers unique",
    'vasi': "sym field '13.6' is a section reference, not an Appendix 2 symbol number; no documented layer name - needs verification",
    'tower': "sym field '13.6' is a section reference, not an Appendix 2 symbol number; no documented layer name - needs verification",
    'servicing': "sym field '13.6' is a section reference, not an Appendix 2 symbol number; no documented layer name - needs verification",
}

# items covering several official symbol names (primary used for export).
MULTI_NAME = {
    'contours': ['Approximate contours', 'Contours'],
    'peaks': ['Highest elevation on chart', 'Spot elevation', 'Spot elevation (of doubtful accuracy)'],
    'wood': ['Coniferous trees', 'Other trees', 'Palms'],
    'shore': ['Shore line (reliable)', 'Shore line (unreliable)'],
    'stream': ['Rivers and streams (non-perennial)', 'Rivers and streams (unsurveyed)', 'Small river (perennial)'],
    'rock_sea': ['Charted isolated rock', 'Rock awash'],
    'places': ['City or large town', 'Town', 'Village'],
    'builtup': ['City or large town', 'Town', 'Village'],
    'rail': ['Railroad (single track)', 'Railroad (two or more tracks)'],
    'ad': ['Civil — Land', 'Civil — Water', 'Emergency aerodrome or aerodrome with no facilities', 'Joint civil and military — Land', 'Joint civil and military — Water', 'Military — Land', 'Military — Water'],
    'ad_mil': ['Military — Land', 'Military — Water'],
    'airstrip': ['Abandoned or closed aerodrome', 'Aerodrome for use on charts on which aerodrome classification is not required', 'Civil — Land', 'Civil — Water', 'Emergency aerodrome or aerodrome with no facilities', 'Joint civil and military — Land', 'Joint civil and military — Water', 'Military — Land', 'Military — Water', 'Sheltered anchorage'],
    'rn_dme': ['Collocated VOR and DME radio navigation aids — VOR/DME', 'Distance measuring equipment — DME'],
    'rn_tacan': ['Collocated VOR and TACAN radio navigation aids — VORTAC', 'UHF tactical air navigation aid — TACAN'],
    'towers': ['Elevation of top/Height above specified datum', 'Exceptionally high obstacle (optional symbol)', 'Exceptionally high obstacle — lighted (optional symbol)', 'Group obstacles', 'Lighted group obstacles', 'Lighted obstacle', 'Obstacle'],
    'wind': ['Wind turbine — unlighted and lighted', 'Wind turbines — minor group and group in major area, lighted'],
    'lighthouse': ['Aeronautical ground light', 'Lightship', 'Marine light'],
    'runway': ['Hard surface runway', 'Pierced steel plank or steel mesh runway', 'Stopway', 'Unpaved runway'],
    'holding': ['Intermediate holding position', 'Runway-holding position'],
    'adarea': ['Hard surface runway', 'Pierced steel plank or steel mesh runway', 'Stopway', 'Taxiways and parking areas', 'Unpaved runway'],
    'windsock': ['Landing direction indicator (lighted)', 'Landing direction indicator (unlighted)'],
    'stopway': ['Aerodrome reference point', 'Building or large structure', 'Escarpment', 'Helicopter alighting area on an aerodrome', 'Hot spot', 'Intermediate holding position', 'Landing direction indicator (lighted)', 'Landing direction indicator (unlighted)', 'Obstacle light', 'Point light', 'Pole, tower, spire, antenna, etc.', 'Railroad', 'Runway visual range (RVR) observation site', 'Runway-holding position', 'Stop bar', 'Stopway', 'Taxiways and parking areas', 'Terrain penetrating obstacle plane', 'Transmission line or overhead cable', 'Tree or shrub', 'VOR check-point'],
}


def official_name(item_id):
    """Verbatim export name, or None when not confidently matched."""
    return LAYER_NAMES.get(item_id)



def export_names(item_id, kinds):
    """Map each produced geometry kind to its exported layer name.

    kinds: list of the representations actually produced ('point', 'line',
    'polygon'). When an item yields several representations, the verbatim
    name alone cannot identify both layers (two GPKG layers cannot share one
    name), so the representation is appended in parentheses - a flagged
    disambiguation, not a rename. Single-representation exports use the
    verbatim name unmodified.

    Returns {kind: name}, or None when the item has no confidently matched
    documented name (caller must flag instead of inventing one).
    """
    base = LAYER_NAMES.get(item_id)
    if base is None:
        return None
    if len(kinds) == 1:
        return {kinds[0]: base}
    return {k: f"{base} ({k})" for k in kinds}
