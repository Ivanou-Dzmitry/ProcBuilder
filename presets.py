import json
import os
import re

import bpy

from . import generator as pb_generator
from .export import _sanitize_filename

PRESET_FORMAT = 1

# Every Generate-section setting a preset captures. library_path must come before style when
# applying: style is a dynamic enum whose valid values depend on the library.
SETTING_KEYS = (
    'library_path', 'style', 'size_x', 'size_y', 'floors', 'extend_x', 'extend_y',
    'module_size', 'module_height', 'include_underground', 'underground_height',
    'include_roof', 'roof_grain', 'use_corner_modules',
)


def resolve_preset_dir(props, create=False):
    """The Folder field if set, else a ProcBuilder/presets folder inside Blender's own config
    directory (survives add-on updates/reinstalls, unlike a folder inside the add-on)."""
    if props.preset_dir:
        path = bpy.path.abspath(props.preset_dir)
    else:
        path = bpy.utils.user_resource(
            'CONFIG', path=os.path.join("ProcBuilder", "presets"), create=create,
        )
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def preset_base_name(props):
    """<style>_<length>x<width>x<floors>, so a preset is recognizable at a glance."""
    return _sanitize_filename(f"{props.style}_{props.size_x}x{props.size_y}x{props.floors}")


def next_preset_filename(props):
    """<base>_v001.json, _v002.json, ... so saving never overwrites an earlier preset."""
    base = preset_base_name(props)
    pattern = re.compile(rf"^{re.escape(base)}_v(\d+)\.json$", re.IGNORECASE)
    folder = resolve_preset_dir(props)
    highest = 0
    if os.path.isdir(folder):
        for fname in os.listdir(folder):
            match = pattern.match(fname)
            if match:
                highest = max(highest, int(match.group(1)))
    return f"{base}_v{highest + 1:03d}.json"


def list_presets(context):
    """Enum items for the Load dropdown: newest file first."""
    props = context.scene.pb_props
    folder = resolve_preset_dir(props)
    files = []
    if os.path.isdir(folder):
        files = [f for f in os.listdir(folder) if f.lower().endswith('.json')]
        files.sort(key=lambda f: os.path.getmtime(os.path.join(folder, f)), reverse=True)
    if not files:
        return [('NONE', 'No presets found', '')]
    return [(f, f[:-5], '') for f in files]


def _default_name_for(band_map, band, side):
    if side in pb_generator.CORNERS:
        return band_map.get(pb_generator.CORNER_BAND_KEY.get(band, ''))
    return band_map.get(band)


def _collect_customizations(band_map):
    """Manual edits on the current building (swapped modules, balconies), as JSON-friendly
    lists. Slots still holding their style's default module are left out - on load they come
    back as the default anyway, so storing them would only bloat the file."""
    wall_swaps, roof_swaps, balconies = pb_generator._snapshot_building_state()

    walls = []
    for (floor, side, local_pos), (name, band) in sorted(
        wall_swaps.items(), key=lambda kv: tuple(str(x) for x in kv[0]),
    ):
        if None in (floor, side, local_pos) or name == _default_name_for(band_map, band, side):
            continue
        walls.append([floor, side, local_pos, name, band])

    roofs = [
        [i, j, name] for (i, j), name in sorted(
            roof_swaps.items(), key=lambda kv: tuple(str(x) for x in kv[0]),
        )
        if None not in (i, j) and name != band_map.get('roof')
    ]

    balcony_list = [
        {
            'floor': b['floor'], 'side': b['side'],
            'local_pos': b['local_pos'], 'collection_name': b['collection_name'],
        }
        for b in balconies if None not in (b['floor'], b['side'], b['local_pos'])
    ]
    return walls, roofs, balcony_list


class PB_OT_save_preset(bpy.types.Operator):
    bl_idname = "pb.save_preset"
    bl_label = "Save Preset"
    bl_description = (
        "Save the current Generate settings - and any swapped modules/balconies on the "
        "existing building - to a preset file named after the building's parameters, so "
        "the same building can be rebuilt later"
    )
    bl_options = {'REGISTER'}

    def execute(self, context):
        from . import library

        props = context.scene.pb_props
        if props.style in ('NONE', ''):
            self.report({'ERROR'}, "Pick a style first")
            return {'CANCELLED'}

        data = {
            'format': PRESET_FORMAT,
            'settings': {key: getattr(props, key) for key in SETTING_KEYS},
            'wall_swaps': [],
            'roof_swaps': [],
            'balconies': [],
        }

        if bpy.data.collections.get(pb_generator.BUILDING_COLLECTION_NAME) is not None:
            filepath = bpy.path.abspath(props.library_path) if props.library_path else ""
            band_map = library.scan_library(filepath).get(props.style, {})
            walls, roofs, balconies = _collect_customizations(band_map)
            data['wall_swaps'], data['roof_swaps'], data['balconies'] = walls, roofs, balconies

        folder = resolve_preset_dir(props, create=True)
        fname = next_preset_filename(props)
        with open(os.path.join(folder, fname), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        props.preset_file = fname
        edits = len(data['wall_swaps']) + len(data['roof_swaps']) + len(data['balconies'])
        self.report({'INFO'}, f"Saved preset {fname} ({edits} manual edit(s)) to {folder}")
        return {'FINISHED'}


class PB_OT_load_preset(bpy.types.Operator):
    bl_idname = "pb.load_preset"
    bl_label = "Load Preset"
    bl_description = (
        "Apply the chosen preset's settings and rebuild the building, restoring its "
        "swapped modules and balconies"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from . import library

        props = context.scene.pb_props
        if props.preset_file in ('NONE', ''):
            self.report({'ERROR'}, "No preset selected")
            return {'CANCELLED'}

        path = os.path.join(resolve_preset_dir(props), props.preset_file)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            settings = data['settings']
        except (OSError, ValueError, KeyError) as exc:
            self.report({'ERROR'}, f"Could not read preset '{props.preset_file}': {exc}")
            return {'CANCELLED'}

        # Check the library/style up front so a bad preset never leaves the settings
        # half-applied.
        lib_path = settings.get('library_path', '')
        lib_file = bpy.path.abspath(lib_path) if lib_path else ""
        if not lib_file or not os.path.isfile(lib_file):
            self.report({'ERROR'}, f"Preset's library not found: {lib_path or '(none)'}")
            return {'CANCELLED'}
        if settings.get('style') not in library.scan_library(lib_file):
            self.report(
                {'ERROR'}, f"Style '{settings.get('style')}' not found in {lib_path}",
            )
            return {'CANCELLED'}

        skipped = []
        for key in SETTING_KEYS:
            if key not in settings:
                continue
            try:
                setattr(props, key, settings[key])
            except (TypeError, ValueError):
                skipped.append(key)

        wall_swaps = {
            (floor, side, local_pos): (name, band)
            for floor, side, local_pos, name, band in data.get('wall_swaps', [])
        }
        roof_swaps = {(i, j): name for i, j, name in data.get('roof_swaps', [])}
        balconies = list(data.get('balconies', []))

        pb_generator.set_pending_state(wall_swaps, roof_swaps, balconies)
        try:
            result = bpy.ops.pb.generate_building()
        finally:
            pb_generator.clear_pending_state()
        if result != {'FINISHED'}:
            return {'CANCELLED'}

        if skipped:
            self.report({'WARNING'}, f"Preset values not applied: {', '.join(skipped)}")
        else:
            self.report({'INFO'}, f"Loaded preset {props.preset_file}")
        return {'FINISHED'}


class PB_OT_open_preset_folder(bpy.types.Operator):
    bl_idname = "pb.open_preset_folder"
    bl_label = "Open Preset Folder"
    bl_description = "Open the folder presets are saved to, in the OS file browser"
    bl_options = {'REGISTER'}

    def execute(self, context):
        folder = resolve_preset_dir(context.scene.pb_props, create=True)
        bpy.ops.wm.path_open(filepath=folder)
        return {'FINISHED'}


classes = (PB_OT_save_preset, PB_OT_load_preset, PB_OT_open_preset_folder)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
