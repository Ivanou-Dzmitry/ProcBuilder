# ProcBuilder

Blender extension that assembles a simple rectangular ("box") building from a
library of 3×3m modules, then lets you select individual placed blocks and
swap them for a different module, or attach a balcony.

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
```

`<StyleName>` is any name (e.g. `Brick01`) — it groups the bands that belong
to one visual style, and is what shows up in the addon's Style dropdown.
Every style must at least have a `bottom` collection; the rest
(`middle`/`top`/`balcony`/`roof`/`underground`) are optional (missing
`middle`/`top` falls back to `bottom` with a warning; missing `roof`/
`underground` just skips that optional step with a warning).

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
   Above the Generate button, an **"Estimate: N modules, ~X tris, ~Y verts"**
   label updates live as you change any of the above - a prediction from the
   library's actual module geometry, so you can gauge scene complexity
   before committing to a (Re)generate.
5. Click **Generate**. This builds all 4 walls per floor, each running the
   building's full length/width (floor 0 = bottom band, last floor = top
   band, floors in between = middle band). Corner cells get a module from
   *each* of the two walls meeting there, so with flat/thin modules the two
   simply meet at the corner edge with no gap. Clicking **Regenerate**
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
   build: ~X tris, ~Y verts"** label shows the actual (not estimated) count
   for what just got built. The same numbers, broken down by wall/balcony/
   roof instance counts and the change from the previous build (`was N →
   +/-M`), are also printed to Blender's **system console** on every
   Generate/Regenerate (`Window → Toggle System Console` on Windows), e.g.:
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
   filler style, e.g. `PB_bottom_WallFiller`).
7. With one or more wall blocks selected, pick a *Balcony* style and click
   **Add Balcony to Selected** to attach one to each.
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
(bottom/middle/top/balcony/roof/underground), an optional *Variant* right
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

## Known v1 limitations

- No floor slabs between stories — only walls, an optional roof cap, and an
  optional underground ring.
- No dedicated corner module — corners are two wall modules (one per side)
  meeting at the edge, rotated 90° to each other. Works cleanly for flat/thin
  modules; a module with real depth will visibly overlap at the corner.
- Regenerating preserves swaps/balconies only for slots that still exist
  after the resize (see the Generate step above); Tools objects like
  `Parapet` aren't part of the `Building` collection at all, so they're
  simply left alone (not deleted, not recalculated) across a regenerate.
- Module discovery is name-based (no Blender Asset Browser integration).
