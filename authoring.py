import re

import bpy

# Shorter tokens used only when building an OBJECT name from its collection's name - the
# collection itself keeps the full word (library.py's scan still needs PB_<band>_<style>).
BAND_ABBREVIATIONS = {
    'bottom': 'bot',
    'middle': 'mid',
    'top': 'top',
    'underground': 'uground',
}


def _abbreviated_collection_name(coll_name):
    """coll_name with its PB_<band>_ prefix shortened (PB_bottom_t01.002 -> PB_bot_t01.002),
    leaving everything else - including any .001-style suffix Blender added - untouched."""
    parts = coll_name.split('_', 2)
    if len(parts) == 3 and parts[0] == 'PB' and parts[1] in BAND_ABBREVIATIONS:
        return f"PB_{BAND_ABBREVIATIONS[parts[1]]}_{parts[2]}"
    return coll_name


class PB_OT_set_module_name(bpy.types.Operator):
    bl_idname = "pb.set_module_name"
    bl_label = "Set Module Name"
    bl_description = (
        "Name the selected objects' collection PB_<role>_<style> so the addon "
        "recognizes it as a module (creates the collection if needed)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.pb_props
        objs = context.selected_objects
        if not objs:
            self.report({'ERROR'}, "Select at least one object first")
            return {'CANCELLED'}

        style = props.module_style.strip()
        if not style:
            self.report({'ERROR'}, "Enter a style name first")
            return {'CANCELLED'}
        if props.module_variant != 'None':
            style = f"{style}_{props.module_variant}"

        target_name = f"PB_{props.module_role}_{style}"
        selected_set = set(objs)

        # Each call makes its OWN module collection - wall/window/door variants for the same
        # band are meant to stay independently selectable (separate styles you pick between
        # with Swap), not merged into one collection that would place all of them at once.
        exact_match = next(
            (c for c in bpy.data.collections if set(c.objects) == selected_set),
            None,
        )
        if exact_match is not None:
            target_collection = exact_match
            target_collection.name = target_name
        else:
            target_collection = bpy.data.collections.new(target_name)
            context.scene.collection.children.link(target_collection)
            for obj in objs:
                for coll in list(obj.users_collection):
                    coll.objects.unlink(obj)
                target_collection.objects.link(obj)

        self.report({'INFO'}, f"Module collection: {target_collection.name}")
        return {'FINISHED'}


class PB_OT_set_element_name(bpy.types.Operator):
    bl_idname = "pb.set_element_name"
    bl_label = "Set Element Name"
    bl_description = (
        "Rename the selected object(s) to <collection name (band abbreviated)>.<part> - "
        "the object's own module collection's name plus what it is inside that module "
        "(wall, door, window...), so its name always shows which module it belongs to"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.pb_props
        objs = context.selected_objects
        if not objs:
            self.report({'ERROR'}, "Select at least one object first")
            return {'CANCELLED'}

        part = props.element_type
        renamed = 0
        skipped = 0
        for obj in objs:
            coll = obj.users_collection[0] if obj.users_collection else None
            if coll is None:
                skipped += 1
                continue
            obj.name = f"{_abbreviated_collection_name(coll.name)}.{part}"
            renamed += 1

        if skipped:
            self.report(
                {'WARNING'},
                f"Renamed {renamed} object(s); {skipped} skipped (not in any collection)",
            )
        else:
            self.report({'INFO'}, f"Renamed {renamed} object(s)")
        return {'FINISHED'}


class PB_OT_rename_collection_elements(bpy.types.Operator):
    bl_idname = "pb.rename_collection_elements"
    bl_label = "Rename All In Collection"
    bl_description = (
        "Rename every object in the active object's collection to <collection name>.<its "
        "current name> - keeps whichever descriptive names you already gave each mesh "
        "(wall, door, window...) but stamps the module's collection name onto all of them "
        "in one go, instead of doing Set Element Name one object at a time"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None or not obj.users_collection:
            self.report({'ERROR'}, "Select an object inside a collection first")
            return {'CANCELLED'}

        coll = obj.users_collection[0]
        short_name = _abbreviated_collection_name(coll.name)
        prefix = f"{short_name}."
        renamed = 0
        for member in list(coll.objects):
            base_name = member.name
            if base_name.startswith(prefix):
                base_name = base_name[len(prefix):]  # re-running: don't double the prefix
            part = re.sub(r'\.\d{3}$', '', base_name)  # drop Blender's own .001-style suffix
            member.name = f"{short_name}.{part}"
            renamed += 1

        self.report({'INFO'}, f"Renamed {renamed} object(s) in '{coll.name}'")
        return {'FINISHED'}


classes = (PB_OT_set_module_name, PB_OT_set_element_name, PB_OT_rename_collection_elements)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
