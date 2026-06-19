# Agent Glitch — Level Editor

A browser-based visual editor for `.agl`/`.agd` level files. Loads your real
`Assets` and `Levels` folders directly (via Chrome's File System Access API),
lets you paint entities onto a grid, edit their data, and saves back to the
exact same file formats your game already reads.

## Recent fixes (this round)

- **Scrollbars**: the canvas now sizes itself to the actual level dimensions
  rather than always matching the visible viewport, so `#canvas-area`'s
  scrollbars genuinely activate for levels larger than your window. This
  also fixed clicking not registering correctly in some cases — the old
  canvas-sizing approach could make click coordinates and visible content
  drift out of sync.
- **Cell Layers panel**: was silently failing to populate due to the same
  underlying canvas-sizing issue above; fixed as part of the same change.
- **Terrain tile size**: now defaults to 48 (matching your real
  `Terrain.png`), and both this and Block size now persist across sessions
  via the browser's local storage — set them once, they stay set.
- **Canvas background**: changed from dark to off-white (`#F6F6F4`, matching
  the game's own background color) so block sprites are easier to make out.
  The surrounding tool chrome (toolbar, palette, status bar) stays dark.
- **Randomized Actor-sprite variants**: the editor now mirrors
  `EntityFactory`'s sprite resolution — if a `sprite` value doesn't match an
  exact folder, it looks for folders sharing that base name with a numeric
  suffix (e.g. `UnarmedAgent` → one of `UnarmedAgent0`..`UnarmedAgent7`) and
  picks one. Since the real game re-randomizes this choice every time the
  entity is built, there's no "correct" variant to show — the editor picks
  one and keeps it stable for the rest of your session (no flickering
  between redraws), and marks any tile using a randomized variant with a
  small purple "?" corner badge so it's never mistaken for guaranteed
  in-game appearance. The **🎲 Reshuffle previews** toolbar button re-rolls
  all of these picks if you want to see a different variant — it only
  changes what the editor shows you, never anything in the saved level data.

## Running it

1. Open `index.html` in **Chrome or Edge** (File System Access API isn't
   supported in Firefox or Safari — this was a deliberate tradeoff to keep
   the tool simple, per your call).
2. Easiest way to open it correctly: serve it from a local folder rather than
   double-clicking the file, so relative script paths resolve cleanly:
   ```
   cd agent-glitch-editor
   python3 -m http.server 8000
   ```
   then visit `http://localhost:8000/index.html`. (Double-clicking the HTML
   file directly may also work in Chrome, but a local server avoids any
   `file://` quirks with module loading.)
3. Click **Open Project Folder…** and pick your project root (the folder
   that contains `Assets/`). The tool looks for level grids in
   `Assets/Levels/*.agl` and their matching entity dicts in
   `Assets/ReferenceDicts/GameObjects/*.agd` — these are two separate
   folders sharing the same base filename per level (e.g. `level1a.agl` /
   `level1a.agd`), not one folder holding both.
   After the first time you pick your folder, the picker will remember it
   and re-open there automatically on future launches (see "Remembering
   your folder" below for the one caveat on this).
4. Pick a level from the dropdown to load it, or click **+ New Level** to
   start a fresh empty grid (you'll be asked for a name and starting size).
5. Edit. Click **Save** to write both files back to their correct folders.
   The Save button is disabled until something's loaded, and shows an
   orange dot when there are unsaved changes.

## Remembering your folder

The File System Access API can't be pointed at an arbitrary path like
`/home/brent/Documents/AgentGlitch/` on a cold start — browsers deliberately
don't let a webpage know your filesystem layout ahead of time. What the
editor does instead: the **first** time you pick your project folder, it's
remembered (via the browser's local storage), and every **subsequent**
launch's picker opens already inside that folder, so it really is just
"click Open, click Select" after the first time.

## How to use it

- **+ New Level**: creates a fresh, empty grid at a size you choose. It
  isn't written to disk until you click Save — so if you change your mind,
  just load a different level instead and nothing's been touched.
- **Place tool** (default): select an entity in the left palette, then
  click or click-drag on the grid to stamp it. Multiple entities can occupy
  the same cell — this matches how `EntityFactory` reads space-separated
  tokens in a single CSV cell.
- **Erase tool**: click/drag to clear a cell's top entity.
- **Select tool**: click a cell to inspect it in the right-hand **Cell
  Layers** panel without painting.
- **Cell Layers panel** (right side): shows every entity stacked in the
  selected cell, topmost first. Drag rows to reorder (this changes draw/
  z-order in the saved CSV), or use the ✎/🗑 buttons to edit/remove just
  that one entity.
- **New entity**: click **+ New** next to any type in the palette. Fill in
  the form, give it a name, save — it's added to the dict but not yet placed
  anywhere; select it in the palette and click the grid to place it.
- **Edit entity**: click the ✎ next to any palette or layer row to open its
  data form (sprite folder, HP, door lock state, trigger target, etc.).
- **Trigger size**: select a cell containing a trigger (anything ending in
  a `*Trigger` type) and you'll see a dashed teal rectangle showing its
  `width`/`height` footprint. Drag the bottom-right handle to resize.
- **Patrol paths**: in the Cell Layers panel, click **⟶ path** next to any
  entity that has a `path` field. The grid will show its route as connected
  yellow waypoints. **Shift+click** anywhere on the grid to append a new
  waypoint (stored as a relative `[dx, dy]` step, matching the format
  already in your `.agd` files). Press **Esc** or click the path button
  again to stop.

## Tooltips

Every toolbar button and setting has a hover tooltip (including the ones
whose icons are easy to read once you know them, like − / + for zoom, but
not obvious on first glance). Hover over anything you're unsure about.

## Settings

- **Block size** (default 96): the on-disk pixel size everything gets scaled
  to. Sprites natively smaller than this (your 48px sheets) are automatically
  upscaled.
- **Terrain tile size** (default 96): the native cell size of `Terrain.png`
  itself, used to slice `coord_x`/`coord_y` lookups. **I could not verify
  this against your real `Terrain.png`** since it wasn't part of what you
  shared — if terrain tiles look cropped or misaligned once you load your
  real Assets folder, this is almost certainly the number to adjust.

## What I verified myself vs. what needs your eyes

I don't have a real browser-with-filesystem-access in my environment, and I
only had your real `level1a`/`level1b` CSVs, the full `.agd` dicts, and one
sample `animate.png` to test against — not your actual `Assets` folder. So
here's an honest split of what's been exercised vs. what's untested:

**Verified, with real data, in an actual Chromium browser:**
- `.agl` round-trip is byte-identical against both `level1a.agl` and
  `level1b.agl`, including the CRLF line endings and the no-trailing-newline
  quirk in your source files.
- `.agd` round-trip is semantically identical (key/value content matches;
  whitespace style is pretty-printed at 2-space indent).
- Multi-entity cell stacking parses correctly against the real
  `bus_l t_next_level` / `bus_m obj_e t_next_level` example from `level1b`.
- Palette grouping, layer panel, entity edit forms (Door, Enemy schemas)
  all render correctly and round-trip existing entity data without mutation
  when no edits are made.
- Trigger rectangle drag-resize works via real synthetic mouse events.
- Patrol path waypoint math (relative offset from current path end)
  computes correctly against the real `el_24d` moving-block path.
- The 48→96 sprite upscale math (`frame_height = image_height`,
  `frame_count = width/height`) is correct against your real 240×48
  5-frame `animate.png` sample.
- **The corrected Levels vs. ReferenceDicts/GameObjects split**: tested
  against a simulated filesystem matching your real folder layout —
  confirmed `.agl` loads/saves from `Assets/Levels` and `.agd` loads/saves
  from `Assets/ReferenceDicts/GameObjects` as two genuinely separate
  folders, not the same one.
- **Blank level creation** (`Model.LevelModel.blank`): produces a grid of
  the exact requested dimensions with valid (empty) CSV and an empty
  entity dict — confirmed it'll load back in cleanly.

**Not verified — needs you to confirm on your machine:**
- The File System Access API folder-picker flow itself (`fsio.js`) — this
  requires a real OS-level folder dialog that I have no way to automate or
  even simulate. This is the single biggest unknown in the whole tool.
- The "remember last folder" persistence specifically — I tested the
  underlying logic, but the real browser-storage round trip across an
  actual browser restart is something only you can confirm.
- Loading your actual `Assets/Sprites/*` and `Assets/Terrain/Terrain.png` —
  I only had folder *names* (from your `find` output) and one sample image,
  not the real files. If any sprite folder's `animate.png`/`picker.png`
  doesn't match the horizontal-strip assumption, that sprite will fail to
  load (it'll fall back to the colored-placeholder rendering rather than
  crash, but it won't look right).
- `Terrain.png`'s native tile size — flagged above, defaulted to 96.
- Whatever your real Assets folder's exact casing/structure is for edge
  cases (e.g. if `Levels` ever ends up somewhere other than directly under
  `Assets/`).

If something doesn't load right, open Chrome's DevTools console (F12) —
I've tried to make failures degrade to visible placeholders + console
warnings rather than silent breakage, specifically so you can tell me what
broke instead of just "it didn't work."

## A few implementation notes worth knowing

- **Patrol path origin**: I'm treating an entity's *first grid placement* as
  the implicit start of its path, with each `[dx, dy]` pair as a relative
  step from there — this matches the pattern in `hov_2l`/`hov_2r`/`el_24d`
  in your dict. I haven't seen the Python code that actually consumes
  `path` at runtime, so if there's some wrinkle I'm not accounting for
  (e.g. the first point being absolute rather than relative), the visual
  path in the editor would be wrong even though the saved data itself is
  unchanged from what you started with — tell me and I'll fix the math.
- **Trigger width/height**: treated purely as metadata on a single anchor
  cell (not multi-cell placement), per your confirmation. Any pre-existing
  "duplicate trigger across cells" hack in your levels is preserved as-is,
  not auto-corrected.
- **Erase tool** removes only the topmost entity in a cell (matching "last
  placed, first removed" intuition for click-erase); to remove a specific
  entity from a stack, use the 🗑 in the Cell Layers panel instead.
- Unknown/future entity types (anything not in the hardcoded type schema
  list) still load and can still be placed — they just fall back to a raw
  JSON textarea for editing instead of a friendly form.

## Files

```
index.html       — app shell
style.css         — dark, dense UI styling
js/model.js       — .agl/.agd parsing, serialization, entity CRUD
js/fsio.js        — File System Access API wrapper
js/sprites.js     — Assets folder indexing, sprite/terrain loading, scaling
js/canvas.js      — grid rendering, placement, trigger drag, path editing
js/palette.js     — entity palette + create/edit form generation
js/layers.js       — per-cell stacked-entity side panel
js/app.js         — wires everything together
```
