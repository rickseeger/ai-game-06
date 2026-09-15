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

## Node 4 deliverable: real input + interaction + target feedback

The game now responds to its documented controls through the real input path.
Movement is held-key driven and mapped onto the 9x9-grid traversal from node 3;
interaction is context-sensitive (the object you face is the target); the screen
always shows the controls and a readable target readout.

- `emberglow/inputmap.py` -- deterministic keyboard -> action mapping (the single
  source of truth for bindings): WASD + arrows move, E / Space / Return interact,
  Escape dismisses dialogue/interface, Q quits. Pure, headless-testable.
- `emberglow/game.py` -- the live session controller: held directional keys drive
  discrete grid movement (release stops, no stuck movement); facing follows the
  most recent press; the target is the object in the faced cell (unambiguous);
  interact performs that target's 11-action-chain step or opens a short dialogue;
  escape dismisses. Renders the player at its true world position plus a controls
  hint, a target marker + name label, and an "E: <verb> <name>" prompt.
- `tests/test_input.py` -- 17 tests: every binding maps to its action; press/release
  semantics; no stuck movement; blocked-move turns facing without moving; target
  selection is unambiguous; interaction performs through the input path; dialogue
  opens and dismisses; movement never triggers an unintended action.
- `tools/demo_input.py` -- an actual-input runtime trace: posts real SDL keyboard
  events through the application event queue (pygame.event.post -> get ->
  Game.handle_event -- the same path a real keyboard feeds) and asserts movement,
  stopping, target selection, interaction, and dialogue dismissal. Emits
  evidence/input_trace.json and frame dumps (input_target_frame.png, etc.).

Controls: WASD / arrows to walk (hold to move), E / Space / Enter to interact,
Escape to dismiss, Q to quit. The on-screen hint and target readout are always
visible; the firefly-glow marker + name label highlight the object you would
interact with.

## Install (one command)

    pip install -r requirements.txt

(Requires Python 3.10+ and pygame-ce 2.5.x. No other dependencies, no build step.)

## Run

    python3 -m emberglow.main                 # live game (real input: WASD/arrows)
    python3 -m emberglow.main --input-check   # input-mapping + press/release tests
    python3 -m emberglow.main --headless      # one frame -> evidence/scene_gate.png
    python3 -m emberglow.main --capture 6     # animation frames -> evidence/
    python3 -m emberglow.main --check         # render + full automated verification

## Verify (automated, no vision)

    python3 -m unittest discover tests        # projection / palette / occlusion / input units
    python3 -m emberglow.main --check         # pixel sampling + geometry + draw order
    python3 -m emberglow.main --input-check   # node 4: key mapping + press/release
    python3 tools/demo_input.py               # node 4: actual-input runtime trace + frame dumps
    python3 tools/demo_traversal.py           # node 3: traversal demo (exits 0)

`--check` renders the 1280x720 scene headlessly (SDL dummy driver) and asserts:
fixed 2:1 projection, diamond 2:1 bounds, painter's-algorithm draw order (tiles
monotonic back-to-front, props after their own tile, far-before-near, player over
background tiles), 2.5D extrusion (raised-tile side face darker than top face),
on-palette flat fills (path / grass / raised grass), warm lit surfaces (R>=G>=B,
R-B>=15), cool violet ambient (B>=R, never black), firefly + lantern glow presence,
character/prop presence (player, Mallow, bell, cottage, stair), interface presence,
and frame determinism + animation actually changing the frame. Results land in
evidence/check_results.json; captured frames in evidence/.

`tools/demo_input.py` posts real SDL key events through the event queue and drives
the controller's tick loop, asserting movement, stopping (no stuck movement),
target selection, interaction (meet_mallow grants the crank through the input
path), dialogue dismissal, no unintended actions, and no ambiguous targeting --
plus code-level frame checks that the controls hint, target glow, name label, and
player are actually rendered. Frame dumps land in evidence/input_*.png; the trace
in evidence/input_trace.json.

## Status

Node 2 (visual foundation + representative scene) is complete and self-verifying.
See docs/NODE2_SCENE.md for the scene's composition and the unverified visual notes.

Node 3 (rendering-independent world geometry + traversal) is complete and
self-verifying: 177 walkable cells across 5 rooms, all progression-critical
locations reachable, gated rooms (greenhouse, crown) locked until their flags,
and a full 11-action on-foot walkthrough passing headless.

Node 4 (real input + context-sensitive interaction + target feedback) is complete
and self-verifying: 17 input tests + an actual-input runtime trace pass headless,
movement maps onto the grid traversal, and the on-screen controls + target readout
render (verified by code-level pixel checks, not vision). The live `--play` loop
uses this controller; a real keyboard on Rick's Pop!_OS is the final human
confirmation of feel. Per-room art (market/mill/greenhouse/crown) and the full
progression/world-reactivity wiring remain later nodes. Final aesthetic judgment
is Rick's.

