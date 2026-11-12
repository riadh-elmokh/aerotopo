from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
)

from . import annex4, chart_types

_STATUS_COLORS = {
    chart_types.REQUIRED: QColor(21, 128, 61),        # green
    chart_types.CONDITIONAL: QColor(161, 98, 7),      # amber
    chart_types.OPTIONAL: QColor(37, 99, 235),        # blue
    chart_types.VERIFY: QColor(190, 18, 60),          # red: needs verification
}


class Annex4Picker(QDialog):
    """Annex 4 layer catalogue: verbatim official names, geometry and sources.

    Chart-type selection lives ONLY in the main window. This dialog reuses the
    chart type chosen there (read-only) to colour the status column; it never
    offers its own selector and never changes the main selection.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annex 4 layer catalogue (ICAO Annex 4 / Doc 8697)")
        self.resize(1000, 720)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Tick the layers to add. Official ICAO layer names are shown verbatim "
            "from Annex 4, Appendix 2, with the source section. The status column "
            "reflects the chart type selected in the main window."))

        self.ref = QLabel("")
        self.ref.setWordWrap(True)
        self.ref.setStyleSheet("color:#444;")
        lay.addWidget(self.ref)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ["Layer (working name)", "Official ICAO name (verbatim)", "Status",
             "Geometry", "Source"])
        self.items = {}
        self._build_tree()
        self.tree.setColumnWidth(0, 220)
        self.tree.setColumnWidth(1, 300)
        self.tree.setColumnWidth(2, 120)
        self.tree.setColumnWidth(3, 110)
        lay.addWidget(self.tree, 1)

        row2 = QHBoxLayout()
        b_report = QPushButton("Export validation report (CSV)…")
        b_report.clicked.connect(self.export_report)
        self.status_summary = QLabel("")
        row2.addWidget(b_report)
        row2.addStretch()
        row2.addWidget(self.status_summary)
        lay.addLayout(row2)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Add to table")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        # Read-only reuse of the main window's chart type (no selector here).
        self.chart_code = self._parent_chart_code()
        self._apply_status()

    def _parent_chart_code(self):
        p = self.parent()
        combo = getattr(p, "chart_type", None)
        return combo.currentData() if combo else None

    # ------------------------------------------------------------- tree
    def _build_tree(self):
        self.tree.clear()
        self.items = {}
        for group, items in annex4.groups():
            g = QTreeWidgetItem(self.tree, [group])
            g.setFlags(g.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsTristate)
            g.setCheckState(0, Qt.Unchecked)
            for it in items:
                c = QTreeWidgetItem(g, [
                    it["name"], annex4.official_names(it), "", "",
                    "/".join(it["geom"])])
                c.setFlags(c.flags() | Qt.ItemIsUserCheckable)
                c.setCheckState(0, Qt.Unchecked)
                c.setData(0, Qt.UserRole, it["id"])
                tip = "\n".join(x for x in (
                    f"Annex 4: {it['src_annex4']}" if it["src_annex4"] else "",
                    f"Doc 8697: {it['src_doc8697']}" if it["src_doc8697"] else "",
                    f"OSM: {annex4.summary(it)}",
                    it["note"], it["warning"]) if x)
                for col in range(5):
                    c.setToolTip(col, tip)
                self.items[it["id"]] = c
            g.setExpanded(True)

    def _apply_status(self):
        """Colour the status column from the main window's chart type."""
        code = self.chart_code
        if not code:
            self.ref.setText(
                "No chart type selected in the main window — showing the full catalogue.")
            return
        c = chart_types.BY_CODE[code]
        n_topo, n_aero = chart_types.chart_topo_summary(code)
        self.ref.setText(
            f"Status shown for chart type {code} — sources: {c['ref']}\n"
            f"The chart-type preset in the main window adds the {n_topo} "
            f"TOPOGRAPHIC layer(s) only; the {n_aero} aeronautical entries "
            "(airspace, navaids, aerodrome surfaces, obstacles) are skipped "
            "there but shown here for completeness.")
        for iid, item in self.items.items():
            it = annex4.BY_ID[iid]
            st = chart_types.chart_status(code, iid)
            if st == chart_types.NOT_APPLICABLE or not st:
                item.setText(2, "not applicable")
                item.setForeground(2, QColor(120, 120, 120))
            elif iid in chart_types.AERONAUTICAL_IDS:
                item.setText(2, f"{st} (aeronautical - not in preset)")
                item.setForeground(2, QColor(120, 120, 120))
            else:
                item.setText(2, st)
                item.setForeground(2, _STATUS_COLORS.get(st, QColor(0, 0, 0)))

    def set_all(self, state):
        for c in self.items.values():
            c.setCheckState(0, Qt.Checked if state else Qt.Unchecked)

    def selected(self):
        return [annex4.BY_ID[i] for i, c in self.items.items()
                if c.checkState(0) == Qt.Checked]

    def export_report(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Validation report",
            f"aerotopo_validation_{self.chart_code or 'all'}.csv", "CSV (*.csv)")
        if not path:
            return
        ids = sorted(self.items)
        try:
            chart_types.export_report_csv(path, ids, self.chart_code)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "AeroTopo", f"Could not write report:\n{exc}")
            return
        self.status_summary.setText(f"Report written: {path}")
