# ProcBuilder

Blender extension that assembles a simple rectangular ("box") building from a
library of 3×3m modules, then lets you select individual placed blocks and
swap them for a different module, or attach a balcony.

## Terminology

- **Module**: one building block - a 3D object (or several meshes together,
  if they're always meant to stay as one piece) that the addon instances
  many times as a **Collection Instance** (not a copy of the mesh - a
  reference to a shared collection; swapping a module just points the same
  object at a different collection). One module fills one grid cell:
  `module_size` × `module_size` meters in plan, `module_height` tall (or its
  own measured height for `bottom` and the roof - see **Generate** below).
- **Band**: which role a module plays - `bottom` (ground floor), `middle`
  (every floor in between), `top` (last floor), `roof`, `underground` (an
  extra ring below the ground floor), `balcony` (see below), or
  `bottomcorner`/`middlecorner` (a dedicated corner piece - see **Corner
  modules** below). The same band can apply to several floors at once
  (e.g. `middle` covers every floor in between bottom and top).
- **Style**: a set of modules sharing one visual look (brick, concrete...),
  grouped by a common name, `PB_<band>_<Style>`. One library file can hold
  several styles, picked from the **Style** dropdown.
- **Balcony**: a module of a different kind from bottom/middle/top/roof/
  underground - balconies are **never placed automatically** by Generate.
  They're added by hand, one at a time, onto an already-generated wall
  block (**Add Balcony to Selected**, see below) - not part of the main
  wall perimeter, just an extra object attached on top of whichever wall
  block you pick, wherever you want one, not on every cell.
- **Library**: a separate `.blend` file holding every module, grouped into
  collections named `PB_<band>_<Style>` (see below). The working file
  (where the building gets assembled) is a different file - the addon
  **links** (`bpy.data.libraries.load`) collections from the library on
  demand, rather than copying everything upfront.

## Module library convention

Modules live in a **separate `.blend` file**. Group each module into its own
Collection, named:

```
PB_bottom_<StyleName>
PB_middle_<StyleName>
PB_top_<StyleName>
PB_balcony_<StyleName>
PB_roof_<StyleName>
PB_underground_<StyleName>
PB_bottomcorner_<StyleName>
PB_middlecorner_<StyleName>
```

`<StyleName>` is any name (e.g. `Brick01`) — it groups the bands that belong
to one visual style, and is what shows up in the addon's Style dropdown.
Every style must at least have a `bottom` collection; the rest
(`middle`/`top`/`balcony`/`roof`/`underground`/`bottomcorner`/`middlecorner`)
are optional (missing `middle`/`top` falls back to `bottom` with a warning;
missing `roof`/`underground` just skips that optional step with a warning;
missing `bottomcorner`/`middlecorner` just falls back to two overlapping
wall modules at the corner, same as if the feature didn't exist - see
**Corner modules** below).

`roof` modules are authored exactly like wall modules (front face toward
local +Y) — the addon tips them flat itself, no separate flat-plane
convention needed.

Each collection's contents should fit a *module_size* × *module_size* m
footprint (default 3×3m, configurable in the panel), with the module's
**front face pointing toward local +Y** — the addon rotates modules in 90°
steps to face outward on each side of the building. The object's origin must
sit on the wall's own plane, bottom-center (local `(0,0,0)`): the addon
measures the bounding box to re-center an off-center origin along X, but
trusts local Y=0 as the wall plane as-is - a protruding detail (a
windowsill, a trim board) can stick out into +Y as far as it needs to
without throwing off alignment, since it's the origin's Y position, not the
bounding box's, that anchors the wall to the grid.

## Using the addon

The panel's sections (**Generate**, **Edit Block**, **Export**, **Tools**,
**Prepare Module**) are collapsible - click the arrow left of a section's
title. **Generate**/**Edit Block** start expanded, **Export**/**Tools**/
**Prepare Module** start collapsed; each remembers its own state.

1. In the **ProcBuilder** tab of the 3D viewport sidebar, set *Library*
   to your module `.blend` file and pick a *Style*.
2. Set *Length*, *Width* and *Floors* (module counts), *Extend X*/*Extend Y*
   (X = Length, Y = Width - shown as a hint under the row. Center by default
   on both axes - each axis independently picks which way the building grows
   in world space when Length/Width change: `X+`/`X-` pins the west/east
   edge in place while the other edge moves, `Y+`/`Y-` does the same for
   south/north, and `Center` grows symmetrically. The two axes are
   independent, so e.g. Extend X = Center with Extend Y = `Y-` grows Length
   symmetrically while Width only extends south. As long as you only change
   Length/Width/Floors, existing blocks - including swaps and balconies -
   never move; new modules are only appended at the growing edge. Changing
   the Extend X/Y setting itself between generates is different: it flips
   which edge is the growing one, so the whole wall visibly reflects to the
   other side, carrying existing blocks with it - that's expected, not a
   bug. `Center` is inherently different too: since it splits growth evenly
   onto both edges, every existing block shifts a little on every resize by
   design, whether or not you touch the Extend setting) and *Module Size*/
   *Module Height* (the
   real-world size of one module in meters — 3m by default; change this if
   your modules aren't 3×3m). The ground floor's own height is auto-measured
   from the `bottom` module's actual bounding box (real buildings often have
   a taller ground floor) - there's no separate field for it, just model
   `bottom` at whatever height it needs, and floor 1 stacks on top of its
   real height, undistorted. Changing *Floors* recomputes each floor's band
   from scratch (e.g. floor 2 can be `middle` in a 5-floor building but
   become `top` once you drop to 3) - a swap is only restored on Regenerate
   if the slot's band didn't change; otherwise it gets that band's fresh
   default module instead of a stale one, so the roof always lines up with
   whatever is actually the top floor now.
3. Optionally enable **Add Underground Row** (one extra wall ring below
   floor 0, from `PB_underground_<Style>`, for burying the base into uneven
   terrain — set its own *height* field, default 0.5m; the module is
   stretched/squashed on Z to match, independent of *Module Height*)
   and/or **Add Roof** (a full flat cap of `PB_roof_<Style>` tiles over the
   whole footprint, with a grain-direction dropdown to rotate all tiles 90°
   together). The roof's height is auto-measured from the actual topmost
   wall band's bounding box, not assumed to equal *Module Height* — handy
   since a parapet/attic top band is often shorter than a normal floor.
   **Use Corner Modules** (off by default) is separate from whether the
   library even has corner modules: off, corners always overlap two
   straight modules exactly like before, even if `PB_bottomcorner_<Style>`/
   `PB_middlecorner_<Style>` exist - sometimes you just don't want a
   corner module for a given build, without having to remove it from the
   library. On with the style missing a corner module for a band, it
   silently falls back to the overlap behavior too, plus the same kind of
   warning `roof`/`underground` already give when missing
   (`Style '<style>' is missing module(s) for: bottomcorner (skipped)`).
   Above the Generate button, an **"Estimate: N modules, ~X tris"** label
   updates live as you change any of the above - a prediction from the
   library's actual module geometry, so you can gauge scene complexity
   before committing to a (Re)generate.
5. Click **Generate**. This builds all 4 walls per floor, each running the
   building's full length/width (floor 0 = bottom band, last floor = top
   band, floors in between = middle band). Corner cells get a module from
   *each* of the two walls meeting there, so with flat/thin modules the two
   simply meet at the corner edge with no gap - unless a dedicated corner
   module exists for that band (see **Corner modules** below), in which
   case one L-shaped piece takes the whole corner instead. Clicking
   **Regenerate**
   rebuilds the grid but **preserves swaps and balconies** wherever the same
   slot (floor + side + position-along-that-side for walls/underground, grid
   cell for roof tiles) still exists after the resize - only slots that
   genuinely disappear lose their customization. The slot key is the wall's
   *side* (N/E/S/W) plus its position along that specific side, not a
   sequential index around the whole perimeter - the sequential index used
   to depend on both Length and Width at once, so growing/shrinking either
   one could reshuffle which physical wall a given index pointed to (a swap
   or an attached balcony could visibly jump from, say, the south wall to
   the east wall). Side+position stays tied to the same physical wall
   regardless of how Length/Width change. Below the button, a **"Last
   build: ~X tris"** label shows the actual (not estimated) count for what
   just got built. The full numbers - triangles AND vertices, broken down
   by wall/balcony/roof instance counts and the change from the previous
   build (`was N → +/-M`) - are printed to Blender's **system console** on
   every Generate/Regenerate (`Window → Toggle System Console` on Windows),
   e.g.:
   ```
   [ProcBuilder] Generated 'Brick01' 5x3x3: 48 walls, 2 balconies, 15 roof
   tiles (65 instances) - ~12,400 triangles (was 9,800 → +2,600),
   ~6,800 vertices (exact export count may differ slightly after vertex
   welding)
   ```
6. Select one or more generated blocks (multi-select works) to see an
   **Edit Block** section: pick a different style in *Replace with* and
   click **Swap Selected** (every currently-selected block, each resolved
   to its own band), **Swap All Matching** (every block anywhere sharing a
   module with any selected block), or **Fill Selected Side** (every block
   on the active block's N/E/S/W side, across all floors — handy for
   keeping one detailed facade and filling the other 3 sides with a plain
   filler style, e.g. `PB_bottom_WallFiller`). Any of these changes which
   module occupies a slot, so they update the **"Last build"** triangle
   count too, without needing a full Regenerate. Works on corner blocks
   too - *Replace with* is filtered by the *corner* band there
   (`bottomcorner`/`middlecorner`), not the straight one, so it only ever
   offers styles that actually have a corner module; a style without one
   simply won't appear, rather than swapping in a straight wall panel that
   wouldn't fit the corner's position/rotation.
7. With one or more wall blocks selected, pick a *Balcony* style and click
   **Add Balcony to Selected** to attach one to each - this also updates
   the **"Last build"** count (it adds new instances).
8. In **Export**, name the export and click **Export FBX** — bakes the whole
   building into one mesh, welds coincident vertices at module seams (Merge
   by Distance, 1mm), recenters the mesh on X/Y while keeping its base at
   Z=0 (so the object's origin sits at world (0,0,0), on the ground, under
   the footprint center — not floating at half the building's height), and
   writes `<name>_v001.fbx` (auto-incrementing). Destination: the **Folder**
   field if set, else next to your `.blend` file, else your home folder if
   the file isn't saved yet - the panel always shows the resolved path
   ("Saves to: ...") so it's never a guess. **Open Export Folder** opens
   that folder in the OS file browser (Explorer/Finder/etc., cross-platform
   via Blender's own `wm.path_open`). The editable building is never touched.

## Preparing modules from the panel

The **Prepare Module (for library)** section automates the naming
convention: select the object(s) making up one module, pick a *Role*
(bottom/middle/top/balcony/roof/underground/bottomcorner/middlecorner - see
**Corner modules** below for the last two), an optional *Variant* right
next to it (Plain/Window/Door/Corner), and type a *Style*, then click
**Set Module Name** — it renames (or creates) the collection as
`PB_<role>_<style>` (or `PB_<role>_<style>_<variant>` when Variant isn't
Plain) for you. *Variant* exists so alternative swappable modules for the
same Role+Style - a plain wall vs. one with a window vs. one with a door,
picked between via Swap at the same spot - get a readable collection name
(`PB_bottom_t01_Win`, `PB_bottom_t01_Door`) instead of Blender's meaningless
`.001`/`.002` auto-suffix. **Each call creates its own collection**, even
with the same Role/Style/Variant (Blender auto-suffixes with `.001`,
`.002`... on a name clash) - this matters because if wall/window/door for
the same band are meant to be *alternative* swappable variants (you pick
which one sits at a given spot via Swap), they must live in separate
collections. Merging them into one would place all of them at once at every
spot, and Swap would
only ever offer that one merged option.

Object names inside a module follow `<collection name, band abbreviated>.
<part>` - e.g. collection `PB_middle_Type01` → object `PB_mid_Type01.wall`
(`bottom→bot`, `middle→mid`, `top→top`, `underground→uground`; style and
any suffix Blender added to the collection, like `.002`, pass through
unchanged). This only makes sense for meshes that are *permanently* part of
one fixed module (e.g. a wall panel welded to its trim) - not for
alternative variants, which need their own collections as above. Two ways
to apply it:
- **Set Element Name**: select object(s) already inside a module
  collection, pick a *Part* (Wall/Door/Window/Balcony/FlatWall/Frame/Sill/
  Trim), click - renames them to `<collection>.<part>`.
- **Rename All In Collection**: renames *every* object in the active
  object's collection at once, reusing each object's own current name as
  the part (so if you already named your meshes `Wall`/`Door`/`Window`
  while modeling, one click prefixes all of them). Safe to run twice - it
  won't double the prefix on objects that already have it.

Both only rename the object, never its collection.

## Corner modules (optional, `bottom`/`middle` only)

By default, each corner is just two straight wall modules meeting at a 90°
edge (see the Generate step above and the limitations list below). For
`bottom` and `middle` you can instead author a **dedicated L-shaped corner
piece** that occupies the whole corner as one object, with no overlap.
`top` isn't supported (not requested, corners there still overlap as
before) - and if a style has no `PB_bottomcorner_<Style>`/
`PB_middlecorner_<Style>` at all, everything works exactly as it did before
this feature existed. It's also gated by the **Use Corner Modules**
checkbox in the Generate section (off by default) - a style can have a
perfectly good corner module and Generate will still use the overlap
behavior unless that checkbox is on.

Author it for the **North-West** corner at zero rotation - the same
reference SIDE_ROTATION uses for plain walls (N=0°, W=90°) - so each of its
two arms can reuse the exact same "front face at local Y=0, facing local
+Y" convention as a normal wall panel:
1. **North arm**: build it exactly like a normal wall panel (front at local
   Y=0, facing +Y). Position it so its corner-side edge - not its center -
   sits at the object's origin `(0,0,0)`, extending away along local **+X**
   for one *Module Size*.
2. **West arm**: build another normal-convention panel and **rotate it
   +90°** around the origin in your modeling software (its front ends up
   facing local **-X** - this is what a plain W-side wall panel looks like
   after the addon's own placement rotation, pre-baked into the mesh instead
   of relying on the addon to rotate it separately, since the whole corner
   object only gets ONE rotation). Position it extending along local **-Y**
   for one *Module Size* from the origin.
3. Join both arms into one object/collection. The point where both arms
   meet - their shared corner point, in the library file's world
   coordinates - must sit exactly on the outer grid corner point, at the
   base (Z=0): unlike straight wall cells, no bounding-box centering is
   applied to corner modules, that point is trusted as-is.
4. **Set Module Name** with Role = `Bottom Corner` (or `Middle Corner`),
   Variant = `Plain`, same Style as the rest of that style's modules -
   produces `PB_bottomcorner_<Style>` (or `PB_middlecorner_<Style>`).

The addon rotates this one authored piece by 0°/90°/180°/270° to cover all
4 corners (North-West/South-West/South-East/North-East) - model it once per
band, not four times. Don't confuse this with the *Variant* dropdown's
`Corner` option (see above) - that's just a naming tag for an alternative
*swappable* module and produces a completely different, unrelated style
name; the real corner module goes through *Role*, not *Variant*. **Variant
is automatically ignored (and greyed out) whenever Role is Bottom Corner/
Middle Corner** - it's a persistent field that doesn't reset itself, so
without this a leftover `Corner` value from a previous module could
silently split the corner module off into its own unmatched style
(`PB_bottomcorner_t01_Corner` instead of `PB_bottomcorner_t01`); now it
can't happen regardless of what Variant is set to.

**If the corner ends up in the wrong place** (floating off to one side,
near the middle of a wall, etc.) two separate things have to line up:
1. **The geometry itself** - where the two arms actually meet, in the
   library file's own world coordinates - must be exactly at `(0,0,0)`.
   Joining objects or moving them by hand can shift this even if an
   object's origin marker looks fine in the viewport.
2. **The collection's own Instance Offset** - a separate property from
   any object's origin, under Object Properties → Collection → Instance
   Offset when the collection is active in the Outliner. Creating a
   collection via the viewport's *Move to Collection → New Collection*
   sets it to wherever the 3D cursor happened to be at that moment - if
   that wasn't the corner point (e.g. left over from an earlier modeling
   step), it'll be some arbitrary value.

The addon compensates for whatever Instance Offset a corner collection has
(same as it already did for straight walls), so (2) usually doesn't need a
manual fix. (1) does, if it's actually off: select both arm meshes,
`Object → Set Origin → Origin to 3D Cursor` (cursor first snapped to the
corner vertex via `Shift+S` → Cursor to Selected), then move the object so
its origin sits exactly at the library file's world `(0,0,0)`.

Corner slots participate in swap-preservation and the "Last build"/
"Estimate" triangle counts exactly like straight wall slots, and were
verified against a synthetic test asset to connect to the adjacent straight
runs with no gap or overlap on all 4 corners.

## Tools: post-processing, independent of the generator

Works on any mesh in Edit Mode - not tied to `Building` at all.

- **Make Parapet From Selection**: select the edges to trim (e.g. a wall's
  top edge loop), set **Depth** and **Resolution** (0 = square profile,
  higher = rounded), click the button. Automates: Separate Selection →
  Convert to Curve → Bevel → Tilt every point 45° (diamond orientation) →
  Convert to Mesh, producing a new `Parapet` object. Sharp corners on a
  POLY curve normally pinch (the bevel profile is oriented to the turn's
  bisector, so its apparent width along either wall shrinks to
  `cos(turn/2)`, for any profile shape) - the tool detects points where the
  curve direction actually changes and scales their `radius` by
  `1/cos(turn/2)` to compensate; points on a straight run are left untouched.
  Since walls are usually zero-thickness planes, the profile straddles that
  plane symmetrically - the same band appears on both the outside and the
  inside of the building, at the same offset. That's expected, not a bug.

An earlier **Remove Interior Faces** tool (ray-cast point-in-solid test) was
removed in v0.9.1: it works for genuine solid volumes (e.g. two intersecting
cubes) but the building's walls are zero-thickness planes, not closed
volumes, so the point-in-mesh test was unreliable on real building geometry
(inconsistent results, sometimes deleting exterior faces). No reliable fix
was found in reasonable time, so the feature was dropped rather than kept
in a flaky state.

## Presets: rebuild a building you assembled

The **Presets** section (bottom of the panel, collapsed by default) saves
and restores a whole building:

- **Save Preset** writes `<style>_<L>x<W>x<F>_v001.json` (e.g.
  `t01_3x23x6_v001.json`; saving again never overwrites - `_v002`, ...)
  holding every Generate setting plus the building's manual edits (swapped
  wall/roof-tile modules and balconies, keyed by the same stable
  floor+side+position slots Regenerate uses; slots still on their style's
  default module are omitted). The *Saves as* label shows the next name.
- **Load Preset** applies the settings and runs Generate with those saved
  edits injected in place of the ones read off the current building (the
  current `Building` is replaced). The library/style are checked first, so a
  bad preset is refused before any setting changes. A module missing from the
  library falls back to the style's default.
- **Open Preset Folder** opens the folder; **Folder** overrides it. Empty
  means `ProcBuilder/presets` in Blender's config directory
  (`%APPDATA%\Blender Foundation\Blender\<version>\config\...` on Windows),
  which survives add-on updates. The library path is stored as set.

## Known v1 limitations

- No floor slabs between stories — only walls, an optional roof cap, and an
  optional underground ring.
- Dedicated corner modules are only supported for `bottom`/`middle` (see
  **Corner modules** above); without one, and always for `top`, corners are
  two wall modules (one per side) meeting at the edge, rotated 90° to each
  other. Works cleanly for flat/thin modules; a module with real depth will
  visibly overlap at the corner.
- Regenerating preserves swaps/balconies only for slots that still exist
  after the resize (see the Generate step above); Tools objects like
  `Parapet` aren't part of the `Building` collection at all, so they're
  simply left alone (not deleted, not recalculated) across a regenerate.
- Module discovery is name-based (no Blender Asset Browser integration).
