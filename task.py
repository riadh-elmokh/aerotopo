"""Background task: runs the Overpass downloads (tiled) without freezing QGIS."""
from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from . import overpass


class DownloadTask(QgsTask):
    query_done = pyqtSignal(str, object, object)   # label, classified | None, error | None
    message = pyqtSignal(str)

    def __init__(self, queries, bbox, endpoint, timeout, pause, tile_size, on_done):
        super().__init__("AeroTopo", QgsTask.CanCancel)
        self.queries = queries      # list of (label, key, value)
        self.bbox = bbox
        self.endpoint = endpoint
        self.timeout = timeout
        self.pause = pause
        self.tile_size = tile_size
        self.on_done = on_done

    def run(self):
        n = len(self.queries)
        for i, (label, key, value) in enumerate(self.queries):
            if self.isCanceled():
                return False
            self.message.emit(f"▶ {label}  ({i + 1}/{n})")

            def progress(done, left, i=i):
                self.setProgress(100.0 * (i + done / max(done + left, 1)) / n)

            try:
                data, failed = overpass.download(
                    self.endpoint, key, value, self.bbox, self.tile_size, self.timeout,
                    self.pause, is_canceled=self.isCanceled,
                    log=self.message.emit, progress=progress)
                if failed:
                    self.message.emit(f"⚠️ {label}: {len(failed)} tile(s) failed, data is incomplete")
                self.query_done.emit(label, data, None)
            except overpass.Cancelled:
                return False
            except Exception as exc:  # noqa: BLE001
                self.query_done.emit(label, None, str(exc))
        return True

    def finished(self, result):  # main thread
        self.on_done(self, result)
