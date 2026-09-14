# ai-game-06 -- G13 "Emberglow Hollow" (The Long Dusk)

A cozy, warm, fixed-isometric (2.5D) adventure game. Linux-first, art-direction-first,
all art code-driven and deterministic (no image assets, no image-gen).

Art direction: **Emberglow Hollow** (direction B) -- a storybook-autumnal hollow at
dusk, lit as if by lanterns (warm honeyed surfaces vs a single cool Twilight-Violet
ambient). Full palette + cohesion rules: docs/ART_DIRECTIONS.md. Bounded adventure
design (5 rooms, 11 actions): docs/ADVENTURE_DESIGN.md + docs/world.json.

## What is here (node 2 deliverable)

The **fixed-isometric visual foundation** plus **one representative art-complete
scene** (the Hollow Gate room): painterly environment tiles, the player and Mallow
(character) appearance, mushroom-roof cottages / Hollow Bell / Hill Stair / lantern
posts / mushrooms / rocks / flowers, the in-palette interface (inventory strip +
dialogue panel + room chip), and restrained animation (firefly drift, glow flicker,
player idle bob, bell sway).

- `emberglow/palette.py`  -- locked named palette + cohesion predicates
- `emberglow/noise.py`    -- one shared deterministic value-noise seed (continuous brush)
- `emberglow/geometry.py` -- fixed 2:1 isometric projection + painter's depth keys
- `emberglow/sprites.py`  -- procedural tiles / props / characters / lighting
- `emberglow/scene.py`    -- scene graph + back-to-front renderer + the gate room
- `emberglow/ui.py`       -- interface treatment (in-palette)
- `emberglow/animation.py`-- restrained, deterministic motion
- `emberglow/main.py`     -- CLI entry point
- `emberglow/checks.py`   -- automated code-level verification (no vision tool)
- `tests/`                -- unit tests (projection, palette, draw-order occlusion)

## Node 3 deliverable: world geometry + traversal (rendering-independent)

The walkable-space layer for the whole 5-room hollow, decoupled from all drawing
code so it is tested headless (no pygame, no display, SDL dummy driver):

- `emberglow/worldmap.py` -- hand-authored solid (impassable) obstacle cells per
  room (cottages, the forge block, the waterwheel + mill-race, plant beds, the
  hilltop ridge + lantern-crown tree).
- `emberglow/world.py`   -- grid geometry + traversal contract: walkable vs solid
  cells, 4-directional movement with collision, room portals (including gated
  portals closed by flags), spawn validity, reachability, pathfinding, and a
  `validate()` self-check of the whole contract.
- `tests/test_world.py`  -- 24 tests: legal movement, blocked movement, boundary
  cases, transitions (incl. round trips), closed-portal gating, spawn validity,
  no-trap reachability, and a full 11-action on-foot walkthrough.
- `tools/demo_traversal.py` -- a runtime traversal demonstration that walks a real
  route (legal + blocked moves, transitions, gate enforcement, the full 11-action
  progression) and exits 0 on success.

Grid model: 9x9 per room; coordinates are (x, y) with x west->east and y
north->south. The non-portal outer ring is the hollow's enclosing treeline
(impassable); interactable objects/characters and the authored obstacles are
solid; stepping onto a portal cell teleports you one step into the paired room,
and a portal whose edge declares `requires` flags is closed until those flags are
present (which is what prevents progression bypasses). The fixed 2:1 isometric
mapping of these grid steps onto the on-screen diagonals is rendering's concern;
this layer is agnostic to it.

## Install (one command)

    pip install -r requirements.txt

(Requires Python 3.10+ and pygame-ce 2.5.x. No other dependencies, no build step.)

## Run

    python3 -m emberglow.main                 # live window (Rick playtest)
    python3 -m emberglow.main --headless      # one frame -> evidence/scene_gate.png
    python3 -m emberglow.main --capture 6     # animation frames -> evidence/
    python3 -m emberglow.main --check         # render + full automated verification

## Verify (automated, no vision)

    python3 -m unittest discover tests        # projection / palette / occlusion units
    python3 -m emberglow.main --check         # pixel sampling + geometry + draw order
    python3 tools/demo_traversal.py            # node 3: traversal demo (exits 0)
    python3 -m unittest tests.test_world -v    # node 3: world geometry/traversal tests

`--check` renders the 1280x720 scene headlessly (SDL dummy driver) and asserts:
fixed 2:1 projection, diamond 2:1 bounds, painter's-algorithm draw order (tiles
monotonic back-to-front, props after their own tile, far-before-near, player over
background tiles), 2.5D extrusion (raised-tile side face darker than top face),
on-palette flat fills (path / grass / raised grass), warm lit surfaces (R>=G>=B,
R-B>=15), cool violet ambient (B>=R, never black), firefly + lantern glow presence,
character/prop presence (player, Mallow, bell, cottage, stair), interface presence,
and frame determinism + animation actually changing the frame. Results land in
evidence/check_results.json; captured frames in evidence/.

## Status

Node 2 (visual foundation + representative scene) is complete and self-verifying.
See docs/NODE2_SCENE.md for the scene's composition and the unverified visual notes.

Node 3 (rendering-independent world geometry + traversal) is complete and
self-verifying: 177 walkable cells across 5 rooms, all progression-critical
locations reachable, gated rooms (greenhouse, crown) locked until their flags,
and a full 11-action on-foot walkthrough passing headless. Traversal owns the
walkable space and room graph; art, rendering, input handling, quest logic, and
audio remain separate later nodes. Final human aesthetic judgment is Rick's.
