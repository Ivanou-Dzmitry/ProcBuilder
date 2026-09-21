import math

import bpy
from mathutils import Vector

CORNER_ANGLE_THRESHOLD = math.radians(1.0)


def _compensate_corner_radii(curve_data):
    """Bevels on a POLY curve pinch at sharp corners (the profile is oriented to the
    bisector of the turn, so its width projects to width*cos(turn/2) along either wall).
    Scale radius up by 1/cos(turn/2) exactly at those corner points to compensate - points
    on a straight run (no turn) are left untouched."""
    for spline in curve_data.splines:
        points = spline.bezier_points if spline.type == 'BEZIER' else spline.points
        count = len(points)
        if count < 3:
            continue
        cyclic = spline.use_cyclic_u

        for i in range(count):
            if not cyclic and (i == 0 or i == count - 1):
                continue  # open-path endpoints have no incoming+outgoing pair to compare

            prev_co = points[(i - 1) % count].co
            co = points[i].co
            next_co = points[(i + 1) % count].co

            incoming = Vector(co[:3]) - Vector(prev_co[:3])
            outgoing = Vector(next_co[:3]) - Vector(co[:3])
            if incoming.length < 1e-9 or outgoing.length < 1e-9:
                continue
            incoming.normalize()
            outgoing.normalize()

            turn_angle = math.acos(max(-1.0, min(1.0, incoming.dot(outgoing))))
            if turn_angle < CORNER_ANGLE_THRESHOLD:
                continue

            points[i].radius *= 1.0 / math.cos(turn_angle / 2.0)


class PB_OT_make_parapet(bpy.types.Operator):
    bl_idname = "pb.make_parapet"
    bl_label = "Make Parapet From Selection"
    bl_description = (
        "Separate the selected edges into a new object, turn them into a beveled/tilted "
        "diamond-profile trim (parapet coping), and bake it back to a mesh. Works on any "
        "mesh - typically the exported/welded building geometry. Select edges in Edit Mode "
        "first"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.active_object is not None

    def execute(self, context):
        props = context.scene.pb_props
        depth = props.parapet_depth

        before = set(bpy.data.objects.keys())
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')
        new_names = set(bpy.data.objects.keys()) - before
        if not new_names:
            self.report({'ERROR'}, "Nothing was separated - select some edges in Edit Mode first")
            return {'CANCELLED'}

        new_obj = bpy.data.objects[next(iter(new_names))]

        view_layer = context.view_layer
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        view_layer.objects.active = new_obj

        bpy.ops.object.convert(target='CURVE')

        curve_data = new_obj.data
        curve_data.bevel_depth = depth
        curve_data.bevel_resolution = props.parapet_resolution  # 0 = square, higher = rounded

        tilt = math.radians(45.0)
        for spline in curve_data.splines:
            for point in spline.bezier_points if spline.type == 'BEZIER' else spline.points:
                point.tilt = tilt

        _compensate_corner_radii(curve_data)

        bpy.ops.object.convert(target='MESH')
        new_obj.name = "Parapet"

        self.report({'INFO'}, f"Created {new_obj.name}")
        return {'FINISHED'}


classes = (PB_OT_make_parapet,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
