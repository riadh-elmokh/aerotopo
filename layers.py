"""Build QGIS layers from classified OSM records and write them to disk."""
import re

from qgis.core import (
    QgsFeature, QgsField, QgsGeometry, QgsPointXY, QgsProject,
    QgsVectorFileWriter, QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

WKB = {"point": "Point", "line": "MultiLineString", "polygon": "MultiPolygon"}


def _field_map(records, shapefile):
    tags = sorted({k for r in records for k in r["tags"]})
    used = {"osm_id", "osm_type"}
    mapping = {}
    for k in tags:
        base = re.sub(r"[^A-Za-z0-9_]", "_", k).strip("_") or "tag"
        if base[0].isdigit():
            base = "t_" + base
        if shapefile:
            base = base[:10]
        name, n = base, 1
        while name.lower() in used:
            suffix = str(n)
            n += 1
            name = (base[:10 - len(suffix)] + suffix) if shapefile else f"{base}_{suffix}"
        used.add(name.lower())
        mapping[k] = name
    return mapping


def _pts(coords):
    return [QgsPointXY(x, y) for x, y in coords]


def _polygonize(pieces):
    lines = [QgsGeometry.fromPolylineXY(_pts(p)) for p in pieces if len(p) >= 2]
    if not lines:
        return None
    res = QgsGeometry.polygonize(lines)
    if res is None or res.isNull() or res.isEmpty():
        return None
    polys = res.asGeometryCollection()
    return QgsGeometry.unaryUnion(polys) if polys else None


def _polygon_geom(rec):
    outer, inner = rec["outer"], rec["inner"]
    if len(outer) == 1 and not inner and len(outer[0]) >= 4 and outer[0][0] == outer[0][-1]:
        geom = QgsGeometry.fromPolygonXY([_pts(outer[0])])
    else:
        geom = _polygonize(outer)
        if geom is None:
            return None
        if inner:
            holes = _polygonize(inner)
            if holes is not None:
                geom = geom.difference(holes)
    if geom is None or geom.isNull() or geom.isEmpty():
        return None
    if not geom.isGeosValid():
        geom = geom.makeValid()
    geom.convertToMultiType()
    return geom


def _geometry(rec, kind):
    if kind == "point":
        return QgsGeometry.fromPointXY(QgsPointXY(*rec["xy"]))
    if kind == "line":
        return QgsGeometry.fromMultiPolylineXY([_pts(c) for c in rec["lines"]])
    return _polygon_geom(rec)


def build_layer(name, records, kind, shapefile=False):
    """Return (memory_layer, skipped_count)."""
    fmap = _field_map(records, shapefile)
    layer = QgsVectorLayer(f"{WKB[kind]}?crs=EPSG:4326", name, "memory")
    pr = layer.dataProvider()
    fields = [QgsField("osm_id", QVariant.LongLong), QgsField("osm_type", QVariant.String)]
    fields += [QgsField(fn, QVariant.String) for fn in fmap.values()]
    pr.addAttributes(fields)
    layer.updateFields()

    feats, skipped = [], 0
    for rec in records:
        geom = _geometry(rec, kind)
        if geom is None:
            skipped += 1
            continue
        f = QgsFeature(layer.fields())
        f.setGeometry(geom)
        f.setAttribute(0, rec["id"])
        f.setAttribute(1, rec["type"])
        for i, tag in enumerate(fmap, start=2):
            f.setAttribute(i, rec["tags"].get(tag, ""))
        feats.append(f)
    pr.addFeatures(feats)
    layer.updateExtents()
    return layer, skipped


def save_layer(layer, path, layer_name, fmt, first_write):
    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.fileEncoding = "UTF-8"
    if fmt == "gpkg":
        opts.driverName = "GPKG"
        opts.layerName = layer_name
        opts.actionOnExistingFile = (
            QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile if first_write
            else QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteLayer
        )
    else:
        opts.driverName = "ESRI Shapefile"
    res = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, path, QgsProject.instance().transformContext(), opts
    )
    if res[0] != QgsVectorFileWriter.WriterError.NoError:
        raise RuntimeError(res[1])
