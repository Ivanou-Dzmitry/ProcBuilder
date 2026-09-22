import math

import bpy
from mathutils import Matrix, Vector

BUILDING_COLLECTION_NAME = "Building"
BUILDING_ROOT_NAME = "Building"

# Rotation (degrees) so the module's local +Y front face points outward on that edge.
SIDE_ROTATION = {
    'S': 180.0,
    'E': -90.0,
    'N': 0.0,
    'W': 90.0,
}

# Roof tiles are authored like wall modules (front face pointing local +Y) and tipped flat
# by the addon; this Z-rotation just picks which grid axis the tile's "grain" runs along.
ROOF_GRAIN_ROTATION = {'X': 0.0, 'Y': 90.0}

# (triangle_count, vertex_count) per module collection, keyed by collection name - modules
# don't change shape at runtime, so this avoids re-walking every mesh on every UI redraw.
_MESH_STATS_CACHE = {}


def _mesh_stats(collection):
    """(triangle_count, vertex_count) for one module collection's mesh geometry, cached by
    collection name."""
    cached = _MESH_STATS_CACHE.get(collection.name)
    if cached is not None:
        return cached
    tris = 0
    verts = 0
    for obj in collection.all_objects:
        if obj.type != 'MESH' or obj.data is None:
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        tris += len(mesh.loop_triangles)
        verts += len(mesh.vertices)
    stats = (tris, verts)
    _MESH_STATS_CACHE[collection.name] = stats
    return stats


def _collection_bounds(collection):
    """Bounding box (min, max) of a module collection's mesh geometry, relative to its
    instance_offset (the point Blender treats as the collection's own origin when instancing)."""
    offset = collection.instance_offset
    min_v = None
    max_v = None
    for obj in collection.all_objects:
        if obj.type != 'MESH' or obj.data is None or not obj.data.vertices:
            continue
        for corner in obj.bound_box:
            point = obj.matrix_world @ Vector(corner) - offset
            if min_v is None:
                min_v, max_v = point.copy(), point.copy()
            else:
                min_v.x, min_v.y, min_v.z = min(min_v.x, point.x), min(min_v.y, point.y), min(min_v.z, point.z)
                max_v.x, max_v.y, max_v.z = max(max_v.x, point.x), max(max_v.y, point.y), max(max_v.z, point.z)
    return None if min_v is None else (min_v, max_v)


def _module_anchor(collection):
    """(width_center_x, front_face_y) in the module's own local space, used to line the
    module up with a grid cell.

    front_face_y is fixed at 0.0 - by convention the object's own origin sits on the wall's
    front plane (bottom-center-front), and we trust that rather than deriving it from the
    bounding box, because a protruding detail (a windowsill, a trim board) would otherwise
    push the measured "front" out to the tip of the protrusion instead of the wall itself.
    width_center_x still comes from the bounding box, to correct an off-center origin."""
    bounds = _collection_bounds(collection)
    if bounds is None:
        return (0.0, 0.0)
    min_v, max_v = bounds
    return ((min_v.x + max_v.x) / 2.0, 0.0)


def _module_height(collection):
    """Actual authored Z-height of a module (its own bounding box), or None if unmeasurable -
    top/bottom/underground bands don't have to share module_height's nominal grid value."""
    bounds = _collection_bounds(collection)
    if bounds is None:
        return None
    min_v, max_v = bounds
    return max_v.z - min_v.z


def _roof_anchor(collection):
    """(center_x, front_face_y, center_z) in the module's own local space - the same
    front-face convention as walls (front point sits at local Y=0, see _module_anchor),
    used before tipping it flat."""
    bounds = _collection_bounds(collection)
    if bounds is None:
        return Vector((0.0, 0.0, 0.0))
    min_v, max_v = bounds
    return Vector(((min_v.x + max_v.x) / 2.0, 0.0, (min_v.z + max_v.z) / 2.0))


def _roof_cell_transform(i, j, anchor, roof_z, module_size, grain_deg, size_x, size_y, extend_x, extend_y):
    """Tip a wall-authored module flat (its front face ends up pointing +Z, visible from
    above) and place it to fill roof grid cell (i, j), with a Z-rotation for grain direction."""
    tip = Matrix.Rotation(math.radians(90.0), 3, 'X')
    grain = Matrix.Rotation(math.radians(grain_deg), 3, 'Z')
    rot3 = grain @ tip
    total_x = size_x * module_size
    total_y = size_y * module_size
    target = Vector((
        _axis_along(i, module_size, extend_x, total_x),
        _axis_along(j, module_size, extend_y, total_y),
        roof_z,
    ))
    location = target - (rot3 @ anchor)
    return tuple(location), tuple(rot3.to_euler('XYZ'))


def _rotate_xy(x, y, degrees):
    rad = math.radians(degrees)
    c, s = math.cos(rad), math.sin(rad)
    return (x * c - y * s, x * s + y * c)


def _axis_along(k, module_size, extend, total):
    """World coordinate of cell index k, measured along one axis (i for S/N walls and roof
    tiles' X; j for E/W walls and roof tiles' Y), honoring that axis's extend direction.

    POS and NEG are mirror images of each other and, on purpose, do NOT depend on `total`
    (the current size along this axis) - cell k always sits the same distance from its own
    anchor edge no matter how much the building has grown, so growing only ever appends cells
    past the far end instead of shifting the ones that already exist. CENTER is the one mode
    that's supposed to be total-dependent: growing means splitting the new length equally onto
    both ends, which necessarily shifts every existing cell inward/outward a bit - that's the
    intended behavior of Center, not a bug."""
    if extend == 'NEG':
        return -(k + 0.5) * module_size
    natural = (k + 0.5) * module_size
    if extend == 'CENTER':
        return natural - total / 2.0
    return natural  # 'POS'


def _axis_near(extend, total):
    """World coordinate of this axis's 'near' boundary - where the W wall's X (or S wall's Y)
    sits. See _axis_along for why POS/NEG are total-independent and CENTER isn't."""
    if extend == 'NEG':
        return -total
    if extend == 'CENTER':
        return -total / 2.0
    return 0.0


def _axis_far(extend, total):
    """World coordinate of this axis's 'far' boundary - where the E wall's X (or N wall's Y)
    sits. See _axis_along for why POS/NEG are total-independent and CENTER isn't."""
    if extend == 'NEG':
        return 0.0
    if extend == 'CENTER':
        return total / 2.0
    return total


def _cell_location(i, j, side, size_x, size_y, anchor, z, module_size, extend_x, extend_y):
    """World location for a perimeter-cell instance so its front face and width-center
    land exactly on the grid, no matter where the module's own origin is."""
    total_x = size_x * module_size
    total_y = size_y * module_size
    if side == 'S':
        target = (_axis_along(i, module_size, extend_x, total_x), _axis_near(extend_y, total_y))
    elif side == 'N':
        target = (_axis_along(i, module_size, extend_x, total_x), _axis_far(extend_y, total_y))
    elif side == 'E':
        target = (_axis_far(extend_x, total_x), _axis_along(j, module_size, extend_y, total_y))
    else:  # 'W'
        target = (_axis_near(extend_x, total_x), _axis_along(j, module_size, extend_y, total_y))

    anchor_x, anchor_y = _rotate_xy(anchor[0], anchor[1], SIDE_ROTATION[side])
    return (target[0] - anchor_x, target[1] - anchor_y, z)


def _floor_z_positions(floors, module_height, bottom_height):
    """Starting Z for each floor 0..floors-1. Floor 0 is bottom_height tall (normally equal
    to module_height, but the ground floor is often taller in real buildings); every floor
    above it is spaced by the plain module_height."""
    z_positions = []
    z = 0.0
    for floor_index in range(floors):
        z_positions.append(z)
        z += bottom_height if floor_index == 0 else module_height
    return z_positions


def _perimeter_walk(size_x, size_y):
    """Four independent wall runs (S/E/N/W), each spanning its FULL length including the
    corner cells. Corner cells get two modules (one per side meeting there) so both exterior
    faces of the corner are covered - with flat/thin modules the two just meet at an edge,
    unlike a single-module-per-corner walk which leaves one face of every corner open."""
    for i in range(size_x):
        yield (i, 0, 'S')
    for j in range(size_y):
        yield (size_x - 1, j, 'E')
    for i in range(size_x - 1, -1, -1):
        yield (i, size_y - 1, 'N')
    for j in range(size_y - 1, -1, -1):
        yield (0, j, 'W')


def _local_pos(i, j, side):
    """A cell's position ALONG its own side (S/N run along X -> i; E/W run along Y -> j).
    Stable across Length/Width changes, unlike the sequential perimeter-walk index, which
    depends on the total size and so shifts which physical cell a given index refers to
    whenever size_x/size_y change - e.g. index 12 might be the south wall at one size and
    the east wall at another. (side, local_pos) is what swap-preservation keys off instead."""
    return i if side in ('S', 'N') else j


def _band_for_floor(floor_index, floors):
    if floor_index == 0:
        return 'bottom'
    if floor_index == floors - 1:
        return 'top'
    return 'middle'


def estimate_stats(props):
    """Predict (instance_count, triangle_count, vertex_count) for the CURRENT Generate
    settings without building anything - lets the panel show a live estimate as Length/
    Width/Floors/etc change, before the user commits to a (Re)generate. Returns None if the
    library/style isn't resolvable yet (no library set, style has no bottom module, ...)."""
    from . import library

    filepath = bpy.path.abspath(props.library_path) if props.library_path else ""
    if not filepath:
        return None
    styles = library.scan_library(filepath)
    band_map = styles.get(props.style)
    if not band_map or 'bottom' not in band_map:
        return None

    wall_cells_per_floor = 2 * (props.size_x + props.size_y)
    band_counts = {}
    if props.include_underground and 'underground' in band_map:
        band_counts['underground'] = band_counts.get('underground', 0) + wall_cells_per_floor
    for floor_index in range(props.floors):
        band = _band_for_floor(floor_index, props.floors)
        if band not in band_map:
            band = 'bottom'
        band_counts[band] = band_counts.get(band, 0) + wall_cells_per_floor
    if props.include_roof and 'roof' in band_map:
        band_counts['roof'] = band_counts.get('roof', 0) + props.size_x * props.size_y

    total_tris = 0
    total_verts = 0
    for band, count in band_counts.items():
        coll_name = band_map.get(band)
        if coll_name is None:
            continue
        collection = library.ensure_collection_linked(filepath, coll_name)
        if collection is None:
            continue
        tris, verts = _mesh_stats(collection)
        total_tris += tris * count
        total_verts += verts * count

    return sum(band_counts.values()), total_tris, total_verts


def _clear_existing_building():
    col = bpy.data.collections.get(BUILDING_COLLECTION_NAME)
    if col is None:
        return
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col)


def _snapshot_building_state():
    """Capture which module each slot currently uses before clearing, so Regenerate can
    restore manual swaps (and reattach balconies) afterward instead of discarding them.

    Wall swaps are stored WITH the band they were recorded under. A slot's default band can
    change across a regenerate (e.g. floor 2 is 'middle' in a 5-floor building but becomes
    'top' once you drop it to 3 floors) - blindly restoring the old collection in that case
    would silently keep a middle-band module (and its height) sitting where a top band should
    now be, throwing off the roof. Only restore when the band still matches."""
    col = bpy.data.collections.get(BUILDING_COLLECTION_NAME)
    wall_swaps, roof_swaps, balcony_snapshots = {}, {}, []
    if col is None:
        return wall_swaps, roof_swaps, balcony_snapshots

    for obj in col.objects:
        if obj.instance_collection is None:
            continue
        role = obj.get('pb_role')
        if role == 'wall':
            slot_key = (obj.get('pb_floor'), obj.get('pb_side'), obj.get('pb_local_pos'))
            wall_swaps[slot_key] = (obj.instance_collection.name, obj.get('pb_band'))
        elif role == 'roof':
            roof_swaps[(obj.get('pb_grid_i'), obj.get('pb_grid_j'))] = obj.instance_collection.name
        elif role == 'balcony':
            balcony_snapshots.append({
                'floor': obj.get('pb_floor'),
                'side': obj.get('pb_side'),
                'local_pos': obj.get('pb_local_pos'),
                'collection_name': obj.instance_collection.name,
            })
    return wall_swaps, roof_swaps, balcony_snapshots


def _resolve_collection(library_module, filepath, default_collection, saved_name):
    """Re-use a previously-swapped module for this slot if it can still be found, else fall
    back to the style's default module for that band."""
    if not saved_name or saved_name == default_collection.name:
        return default_collection
    swapped = library_module.ensure_collection_linked(filepath, saved_name)
    return swapped if swapped is not None else default_collection


def _make_instance(name, collection, location, rotation_euler, parent, target_collection, custom_props):
    obj = bpy.data.objects.new(name, None)
    obj.instance_type = 'COLLECTION'
    obj.instance_collection = collection
    obj.location = location
    obj.rotation_euler = rotation_euler
    obj.parent = parent
    for key, value in custom_props.items():
        obj[key] = value
    target_collection.objects.link(obj)
    return obj


class PB_OT_generate_building(bpy.types.Operator):
    bl_idname = "pb.generate_building"
    bl_label = "Generate Building"
    bl_description = "(Re)generate the building from the current library/style/size settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from . import library

        props = context.scene.pb_props
        filepath = bpy.path.abspath(props.library_path) if props.library_path else ""
        if not filepath:
            self.report({'ERROR'}, "Set a module library .blend file first")
            return {'CANCELLED'}

        styles = library.scan_library(filepath)
        band_map = styles.get(props.style)
        if not band_map or 'bottom' not in band_map:
            self.report({'ERROR'}, f"Style '{props.style}' has no PB_bottom_ module in the library")
            return {'CANCELLED'}

        previous_root = bpy.data.objects.get(BUILDING_ROOT_NAME)
        previous_tris = previous_root.get('pb_last_tris') if previous_root else None
        previous_verts = previous_root.get('pb_last_verts') if previous_root else None

        wall_swaps, roof_swaps, balcony_snapshots = _snapshot_building_state()
        _clear_existing_building()

        building_collection = bpy.data.collections.new(BUILDING_COLLECTION_NAME)
        context.scene.collection.children.link(building_collection)

        root = bpy.data.objects.new(BUILDING_ROOT_NAME, None)
        root['pb_size_x'] = props.size_x
        root['pb_size_y'] = props.size_y
        root['pb_floors'] = props.floors
        root['pb_library_path'] = props.library_path
        root['pb_style'] = props.style
        building_collection.objects.link(root)

        perimeter_cells = list(_perimeter_walk(props.size_x, props.size_y))
        missing_bands = set()
        wall_by_slot = {}

        # The ground floor is often taller than the rest (real buildings do this a lot) - so
        # its stacking height is the module's own ACTUAL modeled height, measured from its
        # bounding box, not assumed to equal module_height. Model it at whatever height it
        # needs to be; nothing here scales or distorts it.
        bottom_coll_name = band_map['bottom']
        bottom_default_collection = library.ensure_collection_linked(filepath, bottom_coll_name)
        if bottom_default_collection is None:
            self.report({'ERROR'}, f"Could not link collection '{bottom_coll_name}'")
            return {'CANCELLED'}
        measured_bottom_height = _module_height(bottom_default_collection)
        bottom_effective_height = (
            measured_bottom_height if measured_bottom_height and measured_bottom_height > 1e-6
            else props.module_height
        )
        floor_z_positions = _floor_z_positions(props.floors, props.module_height, bottom_effective_height)

        floor_bands = []
        if props.include_underground:
            if 'underground' in band_map:
                floor_bands.append((-1, 'underground'))
            else:
                missing_bands.add('underground (skipped)')
        floor_bands.extend((i, _band_for_floor(i, props.floors)) for i in range(props.floors))

        for floor_index, band in floor_bands:
            coll_name = band_map.get(band)
            if coll_name is None:
                missing_bands.add(band)
                coll_name = band_map['bottom']

            default_collection = library.ensure_collection_linked(filepath, coll_name)
            if default_collection is None:
                self.report({'ERROR'}, f"Could not link collection '{coll_name}'")
                return {'CANCELLED'}

            for perimeter_index, (i, j, side) in enumerate(perimeter_cells):
                local_pos = _local_pos(i, j, side)
                slot_key = (floor_index, side, local_pos)
                saved = wall_swaps.get(slot_key)
                saved_name = saved[0] if saved is not None and saved[1] == band else None
                module_collection = _resolve_collection(
                    library, filepath, default_collection, saved_name,
                )
                anchor = _module_anchor(module_collection)

                z = floor_z_positions[floor_index] if floor_index >= 0 else 0.0
                location = _cell_location(
                    i, j, side, props.size_x, props.size_y, anchor, z, props.module_size,
                    props.extend_x, props.extend_y,
                )
                if band == 'underground':
                    # Independent, user-set depth (not module_height) so one underground
                    # module can flex to bury the base into uneven terrain.
                    location = (location[0], location[1], -props.underground_height)
                name = f"PB_wall_f{floor_index}_{perimeter_index}"
                obj = _make_instance(
                    name,
                    module_collection,
                    location,
                    (0.0, 0.0, math.radians(SIDE_ROTATION[side])),
                    root,
                    building_collection,
                    {
                        'pb_role': 'wall',
                        'pb_band': band,
                        'pb_floor': floor_index,
                        'pb_perimeter_index': perimeter_index,
                        'pb_side': side,
                        'pb_local_pos': local_pos,
                    },
                )
                wall_by_slot[slot_key] = obj

                if band == 'underground':
                    authored_height = _module_height(module_collection)
                    scale_z = 1.0
                    if authored_height and authored_height > 1e-6:
                        scale_z = props.underground_height / authored_height
                    obj.scale = (1.0, 1.0, scale_z)

        for info in balcony_snapshots:
            wall_obj = wall_by_slot.get((info['floor'], info['side'], info['local_pos']))
            if wall_obj is None:
                continue  # that slot no longer exists at the new size - can't reattach it
            balcony_collection = library.ensure_collection_linked(filepath, info['collection_name'])
            if balcony_collection is None:
                continue
            balcony = bpy.data.objects.new(f"{wall_obj.name}_balcony", None)
            balcony.instance_type = 'COLLECTION'
            balcony.instance_collection = balcony_collection
            balcony.location = wall_obj.location
            balcony.rotation_euler = wall_obj.rotation_euler
            balcony.parent = wall_obj.parent
            balcony['pb_role'] = 'balcony'
            balcony['pb_band'] = 'balcony'
            balcony['pb_floor'] = wall_obj.get('pb_floor', 0)
            balcony['pb_perimeter_index'] = wall_obj.get('pb_perimeter_index', 0)
            balcony['pb_side'] = wall_obj.get('pb_side')
            balcony['pb_local_pos'] = wall_obj.get('pb_local_pos')
            building_collection.objects.link(balcony)

        if props.include_roof:
            coll_name = band_map.get('roof')
            if coll_name is None:
                missing_bands.add('roof (skipped)')
            else:
                default_roof_collection = library.ensure_collection_linked(filepath, coll_name)
                if default_roof_collection is None:
                    self.report({'ERROR'}, f"Could not link collection '{coll_name}'")
                    return {'CANCELLED'}

                # Stack the roof on the ACTUAL measured height of the topmost wall band,
                # rather than assuming it equals module_height - a parapet/attic top band
                # is often shorter than a normal floor.
                top_band = _band_for_floor(props.floors - 1, props.floors)
                top_coll_name = band_map.get(top_band, band_map['bottom'])
                top_collection = library.ensure_collection_linked(filepath, top_coll_name)
                top_height = _module_height(top_collection) if top_collection else None
                if top_height is None:
                    top_height = props.module_height

                roof_z = floor_z_positions[props.floors - 1] + top_height
                grain_deg = ROOF_GRAIN_ROTATION[props.roof_grain]
                roof_index = 0
                for i in range(props.size_x):
                    for j in range(props.size_y):
                        roof_collection = _resolve_collection(
                            library, filepath, default_roof_collection, roof_swaps.get((i, j)),
                        )
                        anchor3d = _roof_anchor(roof_collection)
                        location, rotation_euler = _roof_cell_transform(
                            i, j, anchor3d, roof_z, props.module_size, grain_deg,
                            props.size_x, props.size_y, props.extend_x, props.extend_y,
                        )
                        _make_instance(
                            f"PB_roof_{roof_index}",
                            roof_collection,
                            location,
                            rotation_euler,
                            root,
                            building_collection,
                            {'pb_role': 'roof', 'pb_band': 'roof', 'pb_grid_i': i, 'pb_grid_j': j},
                        )
                        roof_index += 1

        if missing_bands:
            self.report(
                {'WARNING'},
                f"Style '{props.style}' is missing module(s) for: {', '.join(sorted(missing_bands))}",
            )

        role_counts = {'wall': 0, 'balcony': 0, 'roof': 0}
        collection_counts = {}
        for obj in building_collection.objects:
            role = obj.get('pb_role')
            if role in role_counts:
                role_counts[role] += 1
            if obj.instance_collection is not None:
                collection_counts[obj.instance_collection] = (
                    collection_counts.get(obj.instance_collection, 0) + 1
                )
        total_tris = 0
        total_verts = 0
        for collection, count in collection_counts.items():
            tris, verts = _mesh_stats(collection)
            total_tris += tris * count
            total_verts += verts * count

        root['pb_last_tris'] = total_tris
        root['pb_last_verts'] = total_verts

        total_instances = sum(role_counts.values())
        delta = ""
        if previous_tris is not None:
            diff = total_tris - previous_tris
            delta = f" (was {previous_tris:,} → {diff:+,})"
        print(
            f"[ProcBuilder] Generated '{props.style}' {props.size_x}x{props.size_y}x{props.floors}: "
            f"{role_counts['wall']} walls, {role_counts['balcony']} balconies, "
            f"{role_counts['roof']} roof tiles ({total_instances} instances) - "
            f"~{total_tris:,} triangles{delta}, ~{total_verts:,} vertices "
            "(exact export count may differ slightly after vertex welding)"
        )

        return {'FINISHED'}


classes = (PB_OT_generate_building,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
