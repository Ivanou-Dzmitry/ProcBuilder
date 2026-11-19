import bpy

from . import export as pb_export
from . import generator as pb_generator
from . import presets as pb_presets

ADDON_VERSION = "0.20.0"


class PB_PT_main(bpy.types.Panel):
    bl_label = f"ProcBuilder v{ADDON_VERSION}"
    bl_idname = "PB_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ProcBuilder"

    def draw(self, context):
        layout = self.layout
        props = context.scene.pb_props

        header, box = layout.panel("PB_PT_generate", default_closed=False)
        header.label(text="Generate", icon='HOME')
        if box:
            box.prop(props, "library_path")
            box.prop(props, "style")
            box.label(text="Modules count", icon='MESH_CUBE')
            row = box.row(align=True)
            row.prop(props, "size_x")
            row.prop(props, "size_y")
            row.prop(props, "floors")
            row = box.row(align=True)
            row.prop(props, "extend_x")
            row.prop(props, "extend_y")
            box.label(text="X = Length, Y = Width", icon='INFO')
            row = box.row(align=True)
            row.prop(props, "module_size")
            row.prop(props, "module_height")
            row = box.row(align=True)
            row.prop(props, "include_underground", toggle=True)
            if props.include_underground:
                row.prop(props, "underground_height", text="")
            row = box.row(align=True)
            row.prop(props, "include_roof", toggle=True)
            if props.include_roof:
                row.prop(props, "roof_grain", text="")
            box.prop(props, "use_corner_modules", toggle=True)

            estimate = pb_generator.estimate_stats(props)
            if estimate is not None:
                count, tris, _verts = estimate
                box.label(text=f"Estimate: {count} modules, ~{tris:,} tris")

            exists = bpy.data.collections.get("Building") is not None
            box.operator(
                "pb.generate_building",
                text="Regenerate" if exists else "Generate",
                icon='FILE_REFRESH' if exists else 'HOME',
            )

            root = bpy.data.objects.get("Building")
            if root is not None and 'pb_last_tris' in root:
                box.label(text=f"Last build: ~{root['pb_last_tris']:,} tris")

        obj = context.active_object
        if obj is not None and obj.get('pb_role'):
            header, box = layout.panel("PB_PT_edit_block", default_closed=False)
            header.label(text="Edit Block", icon='MODIFIER')
            if box:
                col = box.column(align=True)
                if 'pb_floor' in obj:
                    col.label(text=f"Floor: {obj.get('pb_floor')}")
                col.label(text=f"Band: {obj.get('pb_band')}")
                col.label(text=f"Role: {obj.get('pb_role')}")
                if 'pb_side' in obj:
                    col.label(text=f"Side: {obj.get('pb_side')}")

                box.prop(props, "swap_style")
                row = box.row(align=True)
                op = row.operator("pb.swap_module", text="Swap Selected", icon='FILE_REFRESH')
                op.also_matching = False
                op = row.operator(
                    "pb.swap_module", text="Swap All Matching", icon='FILE_REFRESH',
                )
                op.also_matching = True

                if obj.get('pb_role') == 'wall':
                    box.operator("pb.fill_side", text="Fill Selected Side", icon='SNAP_FACE')
                    box.prop(props, "balcony_style")
                    box.operator("pb.add_balcony", text="Add Balcony to Selected", icon='ADD')

        header, box = layout.panel("PB_PT_export", default_closed=True)
        header.label(text="Export", icon='EXPORT')
        if box:
            box.prop(props, "export_name")
            box.prop(props, "export_dir")
            box.label(text=f"Saves to: {pb_export.resolve_export_dir(props)}")
            box.operator("pb.export_fbx", text="Export FBX", icon='EXPORT')
            box.operator("pb.open_export_folder", text="Open Export Folder", icon='FILE_FOLDER')

        header, box = layout.panel("PB_PT_tools", default_closed=True)
        header.label(text="Tools", icon='TOOL_SETTINGS')
        if box:
            row = box.row(align=True)
            row.prop(props, "parapet_depth")
            row.prop(props, "parapet_resolution")
            box.operator(
                "pb.make_parapet", text="Make Parapet From Selection", icon='CURVE_DATA',
            )

        header, box = layout.panel("PB_PT_prepare_module", default_closed=True)
        header.label(text="Prepare Module (for library)", icon='OUTLINER_COLLECTION')
        if box:
            row = box.row(align=True)
            row.prop(props, "module_role")
            is_corner_role = props.module_role in ('bottomcorner', 'middlecorner')
            sub = row.row(align=True)
            sub.enabled = not is_corner_role
            sub.prop(props, "module_variant", text="")
            box.prop(props, "module_style")
            box.operator("pb.set_module_name", text="Set Module Name", icon='CHECKMARK')

            box.separator()
            box.label(text="Name an object inside the module")
            box.prop(props, "element_type")
            box.operator("pb.set_element_name", text="Set Element Name", icon='SORTALPHA')
            box.operator(
                "pb.rename_collection_elements", text="Rename All In Collection", icon='GROUP',
            )

        header, box = layout.panel("PB_PT_presets", default_closed=True)
        header.label(text="Presets", icon='PRESET')
        if box:
            box.prop(props, "preset_dir")
            box.label(text=f"Saves as: {pb_presets.next_preset_filename(props)}")
            box.operator("pb.save_preset", text="Save Preset", icon='FILE_TICK')
            row = box.row(align=True)
            row.prop(props, "preset_file", text="")
            row.operator("pb.load_preset", text="Load Preset", icon='IMPORT')
            box.operator("pb.open_preset_folder", text="Open Preset Folder", icon='FILE_FOLDER')


classes = (PB_PT_main,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
