def classFactory(iface):
    from .plugin import AeroTopoPlugin
    return AeroTopoPlugin(iface)
