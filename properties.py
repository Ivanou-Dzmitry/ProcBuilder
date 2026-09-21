import bpy


def get_style_items(self, context):
    from . import library

    props = context.scene.pb_props
    if not props.library_path:
        return [('NONE', 'No library set', '')]
    styles = library.scan_library(bpy.path.abspath(props.library_path))
    if not styles:
        return [('NONE', 'No PB_ collections found', '')]
    return [(name, name, '') for name in sorted(styles.keys())]


def get_swap_style_items(self, context):
    from . import library

    props = context.scene.pb_props
    obj = context.active_object
    if not obj or 'pb_band' not in obj or not props.library_path:
        return [('NONE', '-', '')]
    band = obj['pb_band']
    styles = library.scan_library(bpy.path.abspath(props.library_path))
    items = [(name, name, '') for name, bands in sorted(styles.items()) if bands.get(band)]
    return items or [('NONE', 'No modules for this band', '')]


def get_balcony_style_items(self, context):
    from . import library

    props = context.scene.pb_props
    if not props.library_path:
        return [('NONE', '-', '')]
    styles = library.scan_library(bpy.path.abspath(props.library_path))
    items = [(name, name, '') for name, bands in sorted(styles.items()) if bands.get('balcony')]
    return items or [('NONE', 'No balcony modules', '')]


class PB_SceneProperties(bpy.types.PropertyGroup):
    library_path: bpy.props.StringProperty(
        name="Library",
        description="Blend file containing PB_<band>_<Style> module collections",
        subtype='FILE_PATH',
    )
    style: bpy.props.EnumProperty(name="Style", items=get_style_items)
    size_x: bpy.props.IntProperty(name="Length (modules)", default=3, min=1)
    size_y: bpy.props.IntProperty(name="Width (modules)", default=3, min=1)
    floors: bpy.props.IntProperty(name="Floors (modules)", default=1, min=1)
    module_size: bpy.props.FloatProperty(
        name="Module Size (m)",
        description="Grid spacing along X/Y for one module",
        default=3.0,
        min=0.01,
        subtype='DISTANCE',
    )
    module_height: bpy.props.FloatProperty(
        name="Module Height (m)",
        description="Grid spacing along Z for one floor",
        default=3.0,
        min=0.01,
        subtype='DISTANCE',
    )
    include_roof: bpy.props.BoolProperty(
        name="Add Roof",
        description="Cap the building with a flat grid of PB_roof_<Style> tiles",
        default=False,
    )
    roof_grain: bpy.props.EnumProperty(
        name="Roof Grain",
        description="Which grid axis the roof tiles are oriented along",
        items=[
            ('X', "Along Length (X)", ""),
            ('Y', "Along Width (Y)", ""),
        ],
    )
    include_underground: bpy.props.BoolProperty(
        name="Add Underground Row",
        description="Add one extra wall ring below floor 0, from PB_underground_<Style>, "
                    "for burying the base into uneven ground",
        default=False,
    )
    underground_height: bpy.props.FloatProperty(
        name="Underground Height (m)",
        description="Depth of the underground row below floor 0 (independent of Module "
                    "Height) - the module is stretched/squashed on Z to match",
        default=0.5,
        min=0.05,
        soft_min=0.5,
        soft_max=1.0,
        subtype='DISTANCE',
    )
    swap_style: bpy.props.EnumProperty(name="Replace with", items=get_swap_style_items)
    balcony_style: bpy.props.EnumProperty(name="Balcony", items=get_balcony_style_items)
    export_name: bpy.props.StringProperty(
        name="Name",
        description="Filename (without extension) for the exported FBX",
        default="building_export",
    )
    export_dir: bpy.props.StringProperty(
        name="Folder",
        description="Where Export FBX writes files. Leave empty to use the .blend file's "
                    "own folder (or your home folder if the file isn't saved yet)",
        subtype='DIR_PATH',
        default="",
    )
    module_role: bpy.props.EnumProperty(
        name="Role",
        items=[
            ('bottom', "Bottom", ""),
            ('middle', "Middle", ""),
            ('top', "Top", ""),
            ('balcony', "Balcony", ""),
            ('roof', "Roof", ""),
            ('underground', "Underground", ""),
        ],
    )
    module_style: bpy.props.StringProperty(
        name="Style",
        description="Style name shared by this module's bottom/middle/top/balcony set",
    )
    element_type: bpy.props.EnumProperty(
        name="Part",
        description="What this object represents inside its module - used to build a "
                    "readable object name with Set Element Name",
        items=[
            ('wall', "Wall", ""),
            ('door', "Door", ""),
            ('window', "Window", ""),
            ('balcony', "Balcony", ""),
            ('flatwall', "FlatWall", ""),
            ('frame', "Frame", ""),
            ('sill', "Sill", ""),
            ('trim', "Trim", ""),
        ],
    )
    parapet_depth: bpy.props.FloatProperty(
        name="Depth",
        description="Bevel depth for the parapet profile built from the selected edges",
        default=0.2,
        min=0.001,
        subtype='DISTANCE',
    )
    parapet_resolution: bpy.props.IntProperty(
        name="Resolution",
        description="Bevel resolution for the parapet profile - 0 for a square profile, "
                    "higher for a rounded one",
        default=0,
        min=0,
        max=32,
    )


classes = (PB_SceneProperties,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pb_props = bpy.props.PointerProperty(type=PB_SceneProperties)


def unregister():
    del bpy.types.Scene.pb_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
