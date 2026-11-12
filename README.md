# AeroTopo

QGIS plugin that downloads **OpenStreetMap topographic data for aeronautical charts**,
organised by the symbols of **ICAO Annex 4 – Aeronautical Charts, Appendix 2**.

## Features
- Catalogue of 113 layers: topography, hydrography, culture, aerodromes, radio navigation aids,
  obstacles, aerodrome-chart and obstacle-chart features. Each layer shows its Annex 4 symbol number.
- One-click selection of what Annex 4 requires/recommends for each chart type
  (Chapters 3–4, 7–19, 21).
- Any custom OSM key/value, value lists (`a|b|c`), regular expressions (`~regex`) and raw Overpass filters.
- Extent from the map canvas, a layer, or a drawn rectangle,
  optionally clipped to the real border.
- Large areas are downloaded in tiles; tiles the server cannot answer are split automatically.
- Output to GeoPackage (one file per run) or Shapefile; runs in the background.



## Usage
1. **Annex 4 layers…** → tick layers (or choose a chart type) → *Add to table*.
2. Set the extent.
3. Choose the output folder and press *Download*.

Annex 4 layer list: see `annex4.py` (also exported as CSV in the release notes).

## Limits
- OSM is **not** an authoritative aeronautical source. Airspace, ATS routes, instrument procedures,
  navaid data and certified obstacle data must come from the AIP / official eTOD data.
- OSM has almost no contour lines: derive contours and spot elevations from a DEM.
- Very dense layers (buildings, all roads, trees) over large extents are better done from a
  Geofabrik extract than from the public Overpass servers.
- Be considerate with the public Overpass API (see its usage policy).

## Data and licence
Map data © OpenStreetMap contributors, available under the Open Database Licence (ODbL).
Plugin code: GPL-2.0-or-later (see `LICENSE`).
AeroTopo is not affiliated with or endorsed by ICAO or the OpenStreetMap Foundation.
