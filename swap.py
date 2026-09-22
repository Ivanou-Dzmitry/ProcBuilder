import bpy


def _library_filepath(context):
    props = context.scene.pb_props
    return bpy.path.abspath(props.library_path) if props.library_path else ""


class PB_OT_swap_module(bpy.types.Operator):
    bl_idname = "pb.swap_module"
    bl_label = "Swap Module"
    bl_description = (
        "Replace every selected block's module with the chosen style (each resolved to its "
        "own band) - selecting several blocks swaps all of them, not just the active one"
    )
    bl_options = {'REGISTER', 'UNDO'}

    also_matching: bpy.props.BoolProperty(
        name="Replace All Matching",
        description="Also replace every other block currently using the same module as any "
                    "of the selected blocks",
        default=False,
    )

    def execute(self, context):
        from . import library
        from . import generator as pb_generator

        selected = [o for o in context.selected_objects if 'pb_band' in o]
        if not selected:
            self.report({'ERROR'}, "Select at least one generated building block first")
            return {'CANCELLED'}

        props = context.scene.pb_props
        filepath = _library_filepath(context)
        if not filepath or props.swap_style in ('NONE', ''):
            self.report({'ERROR'}, "Pick a replacement style first")
            return {'CANCELLED'}

        targets = set(selected)
        if self.also_matching:
            old_collections = {o.instance_collection for o in selected}
            targets = {
                o for o in bpy.data.objects
                if o.get('pb_role') and o.instance_collection in old_collections
            }

        missing_bands = set()
        for target in targets:
            band = pb_generator.lookup_band_for_object(target)
            if band is None:
                continue
            new_name = f"PB_{band}_{props.swap_style}"
            new_collection = library.ensure_collection_linked(filepath, new_name)
            if new_collection is None:
                missing_bands.add(band)
                continue
            target.instance_collection = new_collection

        if missing_bands:
            self.report(
                {'WARNING'},
                f"Style '{props.swap_style}' has no {', '.join(sorted(missing_bands))} "
                "module(s); those blocks were left unchanged",
            )

        pb_generator.refresh_building_stats()

        return {'FINISHED'}


class PB_OT_fill_side(bpy.types.Operator):
    bl_idname = "pb.fill_side"
    bl_label = "Fill Selected Side"
    bl_description = (
        "Replace every wall block on the same side (N/E/S/W) as the active block with the "
        "chosen style, across all floors - handy for filling 3 plain sides with a filler "
        "module while keeping one detailed front facade"
    )
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from . import library
        from . import generator as pb_generator

        obj = context.active_object
        if obj is None or obj.get('pb_role') != 'wall' or 'pb_side' not in obj:
            self.report({'ERROR'}, "Select a generated wall block first")
            return {'CANCELLED'}

        props = context.scene.pb_props
        filepath = _library_filepath(context)
        if not filepath or props.swap_style in ('NONE', ''):
            self.report({'ERROR'}, "Pick a replacement style first")
            return {'CANCELLED'}

        side = obj['pb_side']
        targets = [
            o for o in bpy.data.objects
            if o.get('pb_role') == 'wall' and o.get('pb_side') == side
        ]

        missing_bands = set()
        for target in targets:
            band = pb_generator.lookup_band_for_object(target)
            if band is None:
                continue
            new_name = f"PB_{band}_{props.swap_style}"
            new_collection = library.ensure_collection_linked(filepath, new_name)
            if new_collection is None:
                missing_bands.add(band)
                continue
            target.instance_collection = new_collection

        if missing_bands:
            self.report(
                {'WARNING'},
                f"Style '{props.swap_style}' has no {', '.join(sorted(missing_bands))} "
                "module(s); those blocks were left unchanged",
            )

        pb_generator.refresh_building_stats()

        return {'FINISHED'}


class PB_OT_add_balcony(bpy.types.Operator):
    bl_idname = "pb.add_balcony"
    bl_label = "Add Balcony"
    bl_description = "Attach a balcony module to every selected wall block"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from . import library

        wall_objs = [o for o in context.selected_objects if o.get('pb_role') == 'wall']
        if not wall_objs:
            self.report({'ERROR'}, "Select at least one wall block first")
            return {'CANCELLED'}

        props = context.scene.pb_props
        filepath = _library_filepath(context)
        if not filepath or props.balcony_style in ('NONE', ''):
            self.report({'ERROR'}, "Pick a balcony style first")
            return {'CANCELLED'}

        coll_name = f"PB_balcony_{props.balcony_style}"
        balcony_collection = library.ensure_collection_linked(filepath, coll_name)
        if balcony_collection is None:
            self.report({'ERROR'}, f"Could not find '{coll_name}' in the library")
            return {'CANCELLED'}

        for obj in wall_objs:
            target_collection = obj.users_collection[0] if obj.users_collection else context.scene.collection

            balcony = bpy.data.objects.new(f"{obj.name}_balcony", None)
            balcony.instance_type = 'COLLECTION'
            balcony.instance_collection = balcony_collection
            balcony.location = obj.location
            balcony.rotation_euler = obj.rotation_euler
            balcony.parent = obj.parent
            balcony['pb_role'] = 'balcony'
            balcony['pb_band'] = 'balcony'
            balcony['pb_floor'] = obj.get('pb_floor', 0)
            balcony['pb_perimeter_index'] = obj.get('pb_perimeter_index', 0)
            balcony['pb_side'] = obj.get('pb_side')
            balcony['pb_local_pos'] = obj.get('pb_local_pos')
            target_collection.objects.link(balcony)

        from . import generator
        generator.refresh_building_stats()

        return {'FINISHED'}


classes = (PB_OT_swap_module, PB_OT_fill_side, PB_OT_add_balcony)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
