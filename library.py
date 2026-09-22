import bpy

BANDS = (
    'bottom', 'middle', 'top', 'balcony', 'roof', 'underground',
    'bottomcorner', 'middlecorner',
)


def scan_library(filepath):
    """Return {style: {band: collection_name, ...}} parsed from PB_<band>_<Style> collection names."""
    styles = {}
    if not filepath:
        return styles

    try:
        with bpy.data.libraries.load(filepath, link=True) as (data_from, _data_to):
            names = list(data_from.collections)
    except (OSError, RuntimeError):
        return styles

    for name in names:
        parts = name.split('_', 2)
        if len(parts) != 3 or parts[0] != 'PB':
            continue
        _, band, style = parts
        if band not in BANDS:
            continue
        styles.setdefault(style, {}).setdefault(band, name)

    return styles


def ensure_collection_linked(filepath, collection_name):
    """Return the named collection, linking it from filepath if it isn't already linked."""
    existing = bpy.data.collections.get(collection_name)
    if existing is not None and existing.library is not None:
        return existing

    with bpy.data.libraries.load(filepath, link=True) as (data_from, data_to):
        if collection_name not in data_from.collections:
            return None
        data_to.collections = [collection_name]

    return bpy.data.collections.get(collection_name)


def register():
    pass


def unregister():
    pass
