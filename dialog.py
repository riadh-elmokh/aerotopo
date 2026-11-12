import contextlib
import math
import os
import time

from qgis.core import (
    QgsApplication, QgsCoordinateReferenceSystem, QgsProject, QgsRectangle,
    QgsSettings, QgsVectorLayer,
)
from qgis.gui import QgsExtentGroupBox, QgsFileWidget
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog,
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QSizeGrip, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from . import annex4, chart_types, layer_names, layers, overpass, sea
from .picker import Annex4Picker
from .task import DownloadTask

SETTINGS = "aerotopo/"
_ROLE_LABEL = Qt.ItemDataRole.UserRole          # display label for the layer
_ROLE_LABEL_KEY = Qt.ItemDataRole.UserRole + 1  # key the label was built from
_ROLE_PRESET = Qt.ItemDataRole.UserRole + 2     # chart code that added this row (preset)


class AeroTopoDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.task = None
        self._suspend_edit = False   # guards programmatic table updates
        self.setWindowTitle("AeroTopo: topographic data for aeronautical charts")
        # normal app window: minimize, maximize AND close buttons
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint)
        self.resize(700, 900)
        self.setSizeGripEnabled(True)
        s = QgsSettings()
        # Every section lives inside a scroll area: the dialog's minimum size
        # stays small, so it can be resized freely (taller AND shorter).
        content = QWidget()
        content.setObjectName("aerotopo_content")
        root = QVBoxLayout(content)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # --- chart type (standalone section, sibling of Annex 4) ----------
        root.addWidget(self._build_chart_type_group())

        # --- Annex 4 layers ----------------------------------------------
        root.addWidget(self._build_annex4_group(s))

        # --- extent ------------------------------------------------------
        canvas = iface.mapCanvas()
        self.extent_box = QgsExtentGroupBox()
        self.extent_box.setTitle("3. Extent")
        self.extent_box.setMapCanvas(canvas)
        self.extent_box.setOutputCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        self.refresh_extent(set_output=True)
        root.addWidget(self.extent_box)

        # --- tiling ------------------------------------------------------
        box = QGroupBox("4. Tiling (large extents)")
        f = QFormLayout(box)
        self.tile = QDoubleSpinBox()
        self.tile.setRange(0, 30)
        self.tile.setDecimals(2)
        self.tile.setSingleStep(0.25)
        self.tile.setValue(float(s.value(SETTINGS + "tile", 1.0)))
        self.tile.setSuffix(" °")
        self.tile.setToolTip("The extent is downloaded in tiles of this size. 0 = one single request.\n"
                             "A tile the server cannot answer is split automatically.")
        f.addRow("Tile size", self.tile)
        root.addWidget(box)

        # --- output ------------------------------------------------------
        box = QGroupBox("5. Output")
        f = QFormLayout(box)
        self.folder = QgsFileWidget()
        self.folder.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        self.folder.setFilePath(s.value(SETTINGS + "folder", ""))
        self.fmt = QComboBox()
        self.fmt.addItems(["GeoPackage (one file per run)", "Shapefile (one file per layer)"])
        self.add_to_project = QCheckBox("Add results to the project")
        self.add_to_project.setChecked(True)
        self.sea_poly = QCheckBox(
            "Generate sea polygon (Ocean) from the downloaded coastlines")
        self.sea_poly.setChecked(True)
        self.sea_poly.setToolTip(
            "Needs the 'Shore line (reliable)' layer in the table. The sea "
            "polygon is computed as (extent - land) using the OSM rule that "
            "land lies on the LEFT side of coastline ways (sea on the right). "
            "No extra download.")
        f.addRow("Folder", self.folder)
        f.addRow("Format", self.fmt)
        f.addRow("", self.add_to_project)
        f.addRow("", self.sea_poly)
        root.addWidget(box)

        # --- advanced ----------------------------------------------------
        box = QGroupBox("Advanced (tick to edit)")
        box.setCheckable(True)
        box.setChecked(False)
        f = QFormLayout(box)
        self.endpoint = QComboBox()
        self.endpoint.setEditable(True)
        self.endpoint.addItems(overpass.DEFAULT_ENDPOINTS)
        self.timeout = QSpinBox()
        self.timeout.setRange(10, 900)
        self.timeout.setValue(180)
        self.timeout.setSuffix(" s")
        self.pause = QDoubleSpinBox()
        self.pause.setRange(0, 60)
        self.pause.setValue(0.5)
        self.pause.setSuffix(" s")
        f.addRow("Overpass server", self.endpoint)
        f.addRow("Query timeout", self.timeout)
        f.addRow("Pause between requests", self.pause)
        root.addWidget(box)

        # --- run ---------------------------------------------------------
        self.bar = QProgressBar()
        root.addWidget(self.bar)
        self.eta = QLabel("")
        self.eta.setStyleSheet("color:#444;")
        root.addWidget(self.eta)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(80)
        root.addWidget(self.log_view, 1)
        row = QHBoxLayout()
        self.run_btn = QPushButton("Download")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        close = QPushButton("Close")
        self.run_btn.clicked.connect(self.start)
        self.cancel_btn.clicked.connect(self.cancel)
        close.clicked.connect(self.close)
        row.addStretch()
        for w in (self.run_btn, self.cancel_btn, close):
            row.addWidget(w)
        root.addLayout(row)
        root.addStretch(0)
        outer.addWidget(QSizeGrip(self), 0, Qt.AlignmentFlag.AlignRight)
        self.footer = QLabel("Data © OpenStreetMap contributors (ODbL)")
        self.footer.setContentsMargins(8, 0, 8, 2)
        outer.addWidget(self.footer)

    # ------------------------------------------------------ chart type
    def _build_chart_type_group(self):
        """Standalone Chart Type Selection section — independent of Annex 4."""
        box = QGroupBox("1. Chart Type Selection")
        v = QVBoxLayout(box)
        row = QHBoxLayout()
        row.addWidget(QLabel("Chart type"))
        self.chart_type = QComboBox()
        for c in chart_types.CHART_TYPES:
            self.chart_type.addItem(f"{c['code']} — {c['name']}", c["code"])
        self.chart_type.setCurrentIndex(-1)
        self.chart_type.setPlaceholderText("Choose a chart type…")
        b_apply = QPushButton("Apply layers")
        b_apply.setToolTip("Add the previewed topographic layers to the table below. "
                           "Rows you added or edited manually are kept.")
        b_apply.clicked.connect(self.apply_chart_type)
        # selecting only PREVIEWS; nothing is added until "Apply layers"
        self.chart_type.activated.connect(self._on_chart_type)
        row.addWidget(self.chart_type, 1)
        row.addWidget(b_apply)
        v.addLayout(row)
        self.chart_ref = QLabel("")
        self.chart_ref.setWordWrap(True)
        self.chart_ref.setStyleSheet("color:#444;")
        v.addWidget(self.chart_ref)
        self.chart_note = QLabel("")
        self.chart_note.setWordWrap(True)
        self.chart_note.setStyleSheet("color:#a16207;")
        v.addWidget(self.chart_note)
        self.chart_summary = QLabel("")
        self.chart_summary.setWordWrap(True)
        # cap the preview height: the label lists every layer name of a chart
        # (WAC has 40+); uncapped, the dialog grew on every preview/apply.
        self.chart_summary.setMaximumHeight(140)
        v.addWidget(self.chart_summary)
        return box

    def _on_chart_type(self, _index):
        self.preview_chart_type()

    def preview_chart_type(self):
        """Show (only) what the selected chart type would add."""
        code = self.chart_type.currentData()
        if not code:
            return
        c = chart_types.BY_CODE[code]
        self.chart_ref.setText(f"Sources: {c['ref']}")
        self.chart_note.setText(c.get("note", ""))
        n_topo, n_aero = chart_types.chart_topo_summary(code)
        names = []
        from . import layer_names as _ln
        for _iid in sorted(chart_types.chart_layers_topo(code)):
            _n = _ln.LAYER_NAMES.get(_iid)
            names.append(_n if _n else f"[flagged] {annex4.BY_ID[_iid]['name']}")
        self.chart_summary.setText(
            f"{code}: preview of the {n_topo} TOPOGRAPHIC layer(s) this chart needs "
            f"({n_aero} aeronautical layers of its list are skipped - airspace, "
            "navaids, aerodrome surfaces and official obstacles come from the AIP, "
            "not from OSM; use the Annex 4 catalogue if you still want them):\n"
            + "; ".join(names))
        self.chart_preview_code = code

    def apply_chart_type(self):
        """Add the chart type's preset layers to the Annex 4 table.

        Presets never remove rows and never overwrite rows the user added or
        edited: an existing key/value pair is left exactly as it is.
        """
        code = getattr(self, "chart_preview_code", None) or self.chart_type.currentData()
        if not code:
            return
        self._suspend_edit = True          # programmatic updates: no edit flag
        try:
            self._apply_preset(code)
        finally:
            self._suspend_edit = False

    def _apply_preset(self, code):
        c = chart_types.BY_CODE[code]

        existing = {}
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            if item:
                existing.setdefault(
                    (item.text().strip(),
                     (self.table.item(r, 1).text().strip()
                      if self.table.item(r, 1) else "")), []).append(r)

        added = 0
        for iid in sorted(chart_types.chart_layers_topo(code)):
            st = chart_types.chart_status(code, iid)
            if st == chart_types.NOT_APPLICABLE or st == chart_types.VERIFY:
                continue
            it = annex4.BY_ID[iid]
            for key, value, label in annex4.rows_with_labels(it):
                matches = existing.get((key, value), [])
                if matches:
                    # already present: just tag it with this preset, keep values
                    r = matches[0]
                    item = self.table.item(r, 0)
                    if item and not item.data(_ROLE_PRESET):
                        item.setData(_ROLE_PRESET, code)
                    continue
                if existing.get((key, "")) and not value:
                    continue
                self.add_row(key, value, label, preset=code)
                existing.setdefault((key, value), []).append(self.table.rowCount() - 1)
                added += 1
        self.log(f"Chart type {code}: preset applied — {added} layer row(s) added, "
                 "existing rows kept unchanged.")

    # ------------------------------------------------------- Annex 4
    def _build_annex4_group(self, s):
        box = QGroupBox("2. Annex 4 Layers (layer table and ICAO catalogue)")
        v = QVBoxLayout(box)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Key", "Value (empty = any)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setToolTip(
            "Value tips:  a|b|c = several values,  ~regex = regular expression.\n"
            "Advanced: type a raw filter in the Key cell, e.g.\n"
            '["amenity"="cafe"]["wheelchair"="yes"]  or  way["boundary"="administrative"]')
        v.addWidget(self.table)
        row = QHBoxLayout()
        b_an4 = QPushButton("Annex 4 layer catalogue…")
        b_add = QPushButton("Add row")
        b_del = QPushButton("Remove selected")
        b_an4.clicked.connect(self.open_picker)
        b_add.clicked.connect(lambda: self.add_row())
        b_del.clicked.connect(self.remove_rows)
        for w in (b_an4, b_add, b_del):
            row.addWidget(w)
        v.addLayout(row)
        return box

    def closeEvent(self, event):
        # Closing the plugin RESETS everything: no layer selection, chart
        # type, log or progress survives to the next opening. (Only the
        # output folder and tile size stay saved as user preferences.)
        self.reset_state()
        super().closeEvent(event)

    def reject(self):
        # Esc / dialog-cancel path: QDialog.reject() does NOT go through
        # closeEvent, so reset here too.
        self.reset_state()
        super().reject()

    def reset_state(self):
        """Full teardown of runtime state. Safe to call repeatedly and
        from any close path (closeEvent, reject, unload)."""
        if getattr(self, "_resetting", False):
            return                     # already resetting: do not re-enter
        self._resetting = True
        try:
            # 1) stop and detach any running download task + its signals
            task = getattr(self, "task", None)
            if task is not None:
                with contextlib.suppress(Exception):
                    task.cancel()
                for sig in ("progressChanged", "message", "query_done"):
                    with contextlib.suppress(Exception):
                        getattr(task, sig).disconnect()
                self.task = None
            # 2) clear the layer table (programmatic, not a manual edit)
            self._suspend_edit = True
            try:
                self.table.setRowCount(0)
            finally:
                self._suspend_edit = False
            # 3) clear chart-type selection, preview and notes
            self.chart_type.setCurrentIndex(-1)
            self.chart_preview_code = None
            self.chart_ref.setText("")
            self.chart_note.setText("")
            self.chart_summary.setText("")
            # 4) clear progress, ETA and log
            self.bar.setValue(0)
            self.eta.setText("")
            self.log_view.clear()
            # 5) clear run-state variables
            self._total = 0
            self._run_failed = False
            self._used_names = set()
            self._coast_lines = []
            self._bbox = None
            self._t0 = None
            # 6) restore buttons to their fresh-open state
            self.run_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
        except Exception as exc:  # reset must never raise on close
            self._reset_error = str(exc)
        finally:
            self._resetting = False

    # backwards-compatible alias
    def _reset_all(self):
        self.reset_state()

    # ------------------------------------------------------------ helpers
    def log(self, msg):
        self.log_view.appendPlainText(msg)

    def refresh_extent(self, set_output=False):
        canvas = self.iface.mapCanvas()
        crs = canvas.mapSettings().destinationCrs()
        self.extent_box.setOriginalExtent(canvas.extent(), crs)
        self.extent_box.setCurrentExtent(canvas.extent(), crs)
        if set_output:
            self.extent_box.setOutputExtentFromCurrent()

    def add_row(self, key="", value="", label=None, preset=None):
        self._suspend_edit = True      # programmatic fill: not a manual edit
        try:
            r = self.table.rowCount()
            self.table.insertRow(r)
            k = QTableWidgetItem(key)
            if label:
                k.setData(_ROLE_LABEL, label)
                k.setData(_ROLE_LABEL_KEY, key)
            if preset:
                k.setData(_ROLE_PRESET, preset)
            self.table.setItem(r, 0, k)
            self.table.setItem(r, 1, QTableWidgetItem(value))
        finally:
            self._suspend_edit = False

    def _on_item_changed(self, item):
        # a MANUAL edit detaches the row from its preset; programmatic
        # updates are skipped via the suspend flag
        if self._suspend_edit:
            return
        item.setData(_ROLE_PRESET, None)

    def remove_rows(self):
        for r in sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True):
            self.table.removeRow(r)

    def open_picker(self):
        picker = Annex4Picker(self)
        if not picker.exec():
            return
        existing = {
            (self.table.item(r, 0).text().strip() if self.table.item(r, 0) else "",
             self.table.item(r, 1).text().strip() if self.table.item(r, 1) else "")
            for r in range(self.table.rowCount())
        }
        for item in picker.selected():
            for key, value, label in annex4.rows_with_labels(item):
                if (key, value) not in existing:
                    self.add_row(key, value, label)

    @staticmethod
    def _label(k, val):
        return f"{k}={val}" if val and not k.startswith("[") else k

    def queries(self):
        out = []
        for r in range(self.table.rowCount()):
            item = self.table.item(r, 0)
            k = (item.text() if item else "").strip()
            val = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip()
            if k:
                stored = item.data(_ROLE_LABEL)
                if stored and item.data(_ROLE_LABEL_KEY) == item.text():
                    label = stored
                else:
                    label = self._label(k, val)
                out.append((label, k, val))
        return out

    # ------------------------------------------------------------ run
    def start(self):
        queries = self.queries()
        if not queries:
            QMessageBox.warning(self, "AeroTopo", "Add at least one key.")
            return
        folder = self.folder.filePath().strip()
        if not folder:
            QMessageBox.warning(self, "AeroTopo", "Choose an output folder.")
            return
        ext = self.extent_box.outputExtent()
        if ext.isNull() or ext.isEmpty():
            QMessageBox.warning(self, "AeroTopo", "Set a valid extent.")
            return
        size = self.tile.value()
        tiles = 1 if size <= 0 else (
            math.ceil(ext.height() / size) * math.ceil(ext.width() / size))
        requests = tiles * len(queries)
        if requests > 150:
            ans = QMessageBox.question(
                self, "AeroTopo",
                f"This will need about {requests} requests ({tiles} tiles x {len(queries)} layers), "
                "possibly more if tiles are split.\n"
                "It can take a long time and put load on the public Overpass server.\n\n"
                "Continue?")
            if ans != QMessageBox.StandardButton.Yes:
                return
        os.makedirs(folder, exist_ok=True)
        QgsSettings().setValue(SETTINGS + "folder", folder)
        QgsSettings().setValue(SETTINGS + "tile", size)

        # bbox FIRST: everything below depends on it
        bbox = None
        if not ext.isNull() and not ext.isEmpty():
            bbox = (ext.yMinimum(), ext.xMinimum(), ext.yMaximum(), ext.xMaximum())
        if bbox is None:
            QMessageBox.warning(self, "AeroTopo",
                                "Could not determine a valid download extent.")
            return
        self._fmt = "gpkg" if self.fmt.currentIndex() == 0 else "shp"
        self._folder = folder
        self._gpkg = os.path.join(folder, f"osm_{time.strftime('%Y%m%d_%H%M%S')}.gpkg")
        self._total = 0
        self._run_failed = False
        self._used_names = set()   # exported layer names used in THIS run
        self._coast_lines = []     # coastline coords for sea-polygon generation
        self._bbox = bbox
        self._t0 = time.time()
        self.eta.setText(
            f"≈ {self._hms(tiles * 20)} estimated for {tiles} tile(s) "
            "(rough guess — a live estimate appears with the first tiles)")
        # Fresh execution message for EVERY run: discard the previous
        # download's log so old results can never be mistaken for new ones.
        self.log_view.clear()
        self.log(f"=== New download — {time.strftime('%Y-%m-%d %H:%M:%S')} — "
                 f"{len(queries)} layer(s), {tiles} tile(s) each ===")
        self.bar.setValue(0)
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.task = DownloadTask(
            queries, bbox, self.endpoint.currentText().strip(), self.timeout.value(),
            self.pause.value(), size, self._done)
        # bound methods only: signals are delivered in the GUI thread
        self.task.progressChanged.connect(self._on_progress)
        self.task.message.connect(self.log)
        self.task.query_done.connect(self._handle_result)
        QgsApplication.taskManager().addTask(self.task)

    def cancel(self):
        if self.task:
            self.task.cancel()
            self.log("Cancelling…")

    @staticmethod
    def _hms(seconds):
        seconds = max(0, int(seconds))
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

    def _on_progress(self, p):
        self.bar.setValue(int(p))
        if p > 0 and hasattr(self, "_t0"):
            elapsed = time.time() - self._t0
            done = p / 100.0
            remaining = elapsed / done - elapsed
            self.eta.setText(
                f"Elapsed {self._hms(elapsed)} — remaining ≈ {self._hms(remaining)}")

    def _handle_result(self, label, data, err):
        if err:
            self._run_failed = True
            self.log(f"❌ {label}: {err}")
            return
        shp = self._fmt == "shp"
        found = False
        # Exact exported layer names come from the source documents
        # (layer_names.py, generated from ICAO Annex 4 Appendix 2).
        kinds = [k for k in ("point", "line", "polygon") if data[k]]
        iid = annex4.LABEL_TO_ID.get(label)
        doc_names = layer_names.export_names(iid, kinds) if iid else None
        if iid is None:
            self._run_failed = True
            self.log(f"⚠️ FLAGGED: '{label}' is not in the ICAO catalogue; "
                     "exported with its working name - needs verification")
        elif doc_names is None:
            self._run_failed = True
            self.log(f"⚠️ FLAGGED: '{label}' has no confidently matched documented "
                     f"name ({layer_names.FLAGGED.get(iid, 'unmatched')}); exported "
                     "with its working name - needs verification")
        for kind in kinds:
            if not data[kind]:
                continue
            found = True
            if doc_names:
                name = doc_names[kind]          # verbatim documented name
            else:
                name = label                     # flagged fallback (working name)
            if name in self._used_names:
                # GPKG layer names / SHP filenames are unique per run; the same
                # documented name exporting twice (e.g. two representations in
                # separate queries) is disambiguated with the geometry kind -
                # flagged, not renamed silently.
                name = f"{name} ({kind})"
                self._run_failed = True
                self.log(f"⚠️ FLAGGED: documented name was already exported in "
                         f"this run; geometry kind appended: '{name}'")
            self._used_names.add(name)
            try:
                layer, skipped = layers.build_layer(name, data[kind], kind, shp)
                if layer.featureCount() == 0:
                    self.log(f"⚠️ {label}: no valid {kind} geometry")
                    continue
                if shp:
                    path = os.path.join(self._folder, name + ".shp")
                else:
                    path = self._gpkg
                layers.save_layer(layer, path, name, self._fmt,
                                  first_write=(shp or not os.path.exists(self._gpkg)))
            except Exception as exc:  # noqa: BLE001
                self._run_failed = True
                self.log(f"❌ {label} ({kind}): {exc}")
                continue
            self._total += layer.featureCount()
            msg = f"✅ {name}: {layer.featureCount()} {kind} feature(s)"
            if skipped:
                msg += f"  ({skipped} incomplete geometries skipped)"
            self.log(msg)
            if self.add_to_project.isChecked():
                uri = path if shp else f"{path}|layername={name}"
                vl = QgsVectorLayer(uri, name, "ogr")
                if vl.isValid():
                    QgsProject.instance().addMapLayer(vl)
        if not found:
            self.log(f"⚠️ {label}: nothing found in this area")
        # collect coastline geometry for the sea-polygon generation
        if iid == "shore":
            for rec in data["line"]:
                self._coast_lines.extend(rec["lines"])
        data.clear()

    def _generate_sea(self):
        """Sea polygon = download extent minus land (from coastlines)."""
        if not self._coast_lines:
            self.log("⚠️ sea: no coastlines were downloaded - add the "
                     "'Shore line (reliable)' layer to generate the sea polygon")
            return
        rings, warns = sea.trace_land_faces(self._bbox, self._coast_lines)
        for w_ in sorted(set(warns)):
            self.log(f"⚠️ sea: {w_}")
        if not rings:
            self.log("⚠️ sea: no land rings could be traced - no sea polygon generated")
            return
        land = QgsGeometry.fromMultiPolygonXY(
            [[QgsPointXY(x, y) for x, y in ring] for ring in rings])
        if not land.isGeosValid():
            land = land.makeValid()
        s, w, n, e = self._bbox
        ext_geom = QgsGeometry.fromRect(QgsRectangle(w, s, e, n))
        sea_geom = ext_geom.difference(land)
        if sea_geom is None or sea_geom.isNull() or sea_geom.isEmpty():
            self.log("⚠️ sea: the extent is entirely land - no sea polygon")
            return
        sea_geom.convertToMultiType()
        recs = []
        for part in sea_geom.constParts():
            outer = [(v.x(), v.y()) for v in part.exterior_ring()]
            inner = [[(v.x(), v.y()) for v in ring]
                     for ring in part.interior_rings()]
            recs.append({"id": 0, "type": "generated", "tags": {},
                         "outer": [outer], "inner": inner})
        name = "Ocean (polygons)"
        if name in self._used_names:
            self.log("⚠️ FLAGGED: 'Ocean (polygons)' was already exported in "
                     "this run; the generated sea polygon is skipped")
            return
        self._used_names.add(name)
        shp = self._fmt == "shp"
        try:
            layer, skipped = layers.build_layer(name, recs, "polygon", shp)
            path = os.path.join(self._folder, name + ".shp") if shp else self._gpkg
            layers.save_layer(layer, path, name, self._fmt,
                              first_write=(shp or not os.path.exists(self._gpkg)))
        except Exception as exc:  # noqa: BLE001
            self._run_failed = True
            self.log(f"❌ {name} (generated): {exc}")
            return
        self._total += layer.featureCount()
        self.log(f"✅ {name}: {layer.featureCount()} feature(s) generated "
                 "from coastlines (extent minus land)")
        if self.add_to_project.isChecked():
            uri = path if shp else f"{path}|layername={name}"
            vl = QgsVectorLayer(uri, name, "ogr")
            if vl.isValid():
                QgsProject.instance().addMapLayer(vl)

    def _done(self, task, ok):
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        if not ok:
            self._run_failed = True
            self.log("⏹ Download cancelled — results from this run are incomplete.")
            return
        self.bar.setValue(100)
        if self.sea_poly.isChecked():
            self._generate_sea()
        where = self._folder if self._fmt == "shp" else self._gpkg
        if self._run_failed:
            self.log(f"❌ Finished with errors. Partial results: {self._total} "
                     f"feature(s) saved to {where}. Check the ❌ lines above.")
        else:
            self.log(f"✅ Done. {self._total} feature(s) saved to {where}")
