import os
import re

import bmesh
import bpy
from mathutils import Matrix, Vector

from .generator import BUILDING_COLLECTION_NAME

MERGE_DISTANCE = 0.001  # weld seams between modules (Merge by Distance, in meters)


def _sanitize_filename(name):
    keep = "-_.() "
    cleaned = "".join(c for c in name if c.isalnum() or c in keep).strip()
    return cleaned or "building_export"


def resolve_export_dir(props):
    """The folder Export FBX will actually write to: the explicit override if set, else the
    .blend file's own folder, else the user's home folder (e.g. when the file isn't saved
    yet - a common source of "where did it save?" confusion)."""
    if props.export_dir:
        return bpy.path.abspath(props.export_dir)
    return os.path.dirname(bpy.data.filepath) or os.path.expanduser("~")


def _next_versioned_path(export_dir, export_name):
    """<export_name>_v001.fbx, _v002.fbx, ... so repeat exports never overwrite each other."""
    pattern = re.compile(rf"^{re.escape(export_name)}_v(\d+)\.fbx$", re.IGNORECASE)
    max_version = 0
    if os.path.isdir(export_dir):
        for fname in os.listdir(export_dir):
            match = pattern.match(fname)
            if match:
                max_version = max(max_version, int(match.group(1)))
    version = max_version + 1
    return os.path.join(export_dir, f"{export_name}_v{version:03d}.fbx")


def _build_export_mesh(source_objs, mesh_name):
    """Bake every wall/balcony instance's geometry into one combined mesh, in world space.

    Works directly off bpy.data (no duplicate/make_real/join operators) so it doesn't depend
    on operator/context selection quirks, and never touches the original instance objects.
    """
    bm = bmesh.new()
    combined_materials = []
    material_index_map = {}

    for inst_obj in source_objs:
        collection = inst_obj.instance_collection
        if collection is None:
            continue
        base_matrix = inst_obj.matrix_world @ Matrix.Translation(-collection.instance_offset)
        for child in collection.all_objects:
            if child.type != 'MESH' or child.data is None:
                continue
            mesh_copy = child.data.copy()
            mesh_copy.transform(base_matrix @ child.matrix_world)

            remap = []
            for mat in mesh_copy.materials:
                key = mat.name if mat else None
                if key not in material_index_map:
                    material_index_map[key] = len(combined_materials)
                    combined_materials.append(mat)
                remap.append(material_index_map[key])
            if remap:
                for poly in mesh_copy.polygons:
                    poly.material_index = remap[poly.material_index]

            bm.from_mesh(mesh_copy)
            bpy.data.meshes.remove(mesh_copy)

    if len(bm.verts) == 0:
        bm.free()
        return None

    # Weld coincident vertices at module seams (equivalent to Mesh > Clean Up > Merge by Distance).
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=MERGE_DISTANCE)

    # Recenter on X/Y (footprint center) but keep Z based at the building's own floor (min Z),
    # so the exported object's origin (world 0,0,0) sits at ground level under the footprint
    # center, not floating at half the building's height.
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    center = Vector(((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0, min(zs)))
    bmesh.ops.translate(bm, verts=bm.verts, vec=-center)

    combined_mesh = bpy.data.meshes.new(mesh_name)
    bm.to_mesh(combined_mesh)
    bm.free()
    for mat in combined_materials:
        combined_mesh.materials.append(mat)
    return combined_mesh


class PB_OT_export_fbx(bpy.types.Operator):
    bl_idname = "pb.export_fbx"
    bl_label = "Export FBX"
    bl_description = (
        "Merge a copy of the building into one mesh and export it as FBX "
        "(the editable modular building is left untouched)"
    )
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.pb_props
        building = bpy.data.collections.get(BUILDING_COLLECTION_NAME)
        if building is None:
            self.report({'ERROR'}, "Generate a building first")
            return {'CANCELLED'}

        source_objs = [o for o in building.objects if o.get('pb_role') in ('wall', 'balcony', 'roof')]
        if not source_objs:
            self.report({'ERROR'}, "No wall/balcony blocks found to export")
            return {'CANCELLED'}

        export_name = _sanitize_filename(props.export_name)
        combined_mesh = _build_export_mesh(source_objs, export_name)
        if combined_mesh is None:
            self.report({'ERROR'}, "No real geometry produced from the building's modules")
            return {'CANCELLED'}

        export_dir = resolve_export_dir(props)
        os.makedirs(export_dir, exist_ok=True)
        filepath = _next_versioned_path(export_dir, export_name)

        joined = bpy.data.objects.new(export_name, combined_mesh)
        context.scene.collection.objects.link(joined)

        view_layer = context.view_layer
        bpy.ops.object.select_all(action='DESELECT')
        joined.select_set(True)
        view_layer.objects.active = joined

        bpy.ops.export_scene.fbx(filepath=filepath, use_selection=True)

        bpy.data.objects.remove(joined, do_unlink=True)
        if combined_mesh.users == 0:
            bpy.data.meshes.remove(combined_mesh)
        bpy.ops.object.select_all(action='DESELECT')

        self.report({'INFO'}, f"Exported {filepath}")
        return {'FINISHED'}


class PB_OT_open_export_folder(bpy.types.Operator):
    bl_idname = "pb.open_export_folder"
    bl_label = "Open Export Folder"
    bl_description = "Open the folder Export FBX writes to, in the OS file browser"
    bl_options = {'REGISTER'}

    def execute(self, context):
        export_dir = resolve_export_dir(context.scene.pb_props)
        os.makedirs(export_dir, exist_ok=True)
        bpy.ops.wm.path_open(filepath=export_dir)
        return {'FINISHED'}


classes = (PB_OT_export_fbx, PB_OT_open_export_folder)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
