import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dialog import AeroTopoDialog

MENU = "&AeroTopo"


class AeroTopoPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        icon = QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))
        self.action = QAction(icon, "AeroTopo: topographic data for aeronautical charts",
                              self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToWebMenu(MENU, self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginWebMenu(MENU, self.action)
        self.iface.removeToolBarIcon(self.action)
        if self.dialog:
            if hasattr(self.dialog, "reset_state"):
                self.dialog.reset_state()   # cancel task, disconnect signals
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None

    def run(self):
        if self.dialog is None:
            self.dialog = AeroTopoDialog(self.iface, self.iface.mainWindow())
        else:
            self.dialog.refresh_extent()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
