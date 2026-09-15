# ai-game-06 -- G13 "Emberglow Hollow" (The Long Dusk)

A cozy, warm, fixed-isometric (2.5D) adventure game. Linux-first, art-direction-first,
all art code-driven and deterministic (no image assets, no image-gen).

Art direction: **Emberglow Hollow** (direction B) -- a storybook-autumnal hollow at
dusk, lit as if by lanterns (warm honeyed surfaces vs a single cool Twilight-Violet
ambient). Full palette + cohesion rules: docs/ART_DIRECTIONS.md. Bounded adventure
design (5 rooms, 11 actions): docs/ADVENTURE_DESIGN.md + docs/world.json.

## Quick start (Linux)

One command to install and launch the game (from a fresh clone):

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m emberglow.main

Controls: WASD / arrows to move; E / Space / Enter to interact or talk; X examine,
T talk, G take, U use the selected item; Tab / [ cycle the selected inventory
item; Escape dismiss dialogue; Q quit. Goal: relight the Heart-Lantern (the exact
11-step route is in docs/WALKTHROUGH.md).

No display? Verify headlessly instead:

    .venv/bin/python -m emberglow.main --check        # render + full automated verification
    .venv/bin/python -m unittest discover -s tests    # 144 unit tests

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

## Node 5 deliverable: explicit verbs + inventory + dialogue + feedback

The full classic-adventure interaction system now sits on top of the node-4 stub.
The partial auto-apply stub is replaced by an explicit verb model:

- `emberglow/verbs.py` -- the pure verb model and resolver. Four distinct verbs
  (Examine / Talk / Take / Use-item-on-target, plus walk), the contextual E key,
  inspectable objects (every prop + both characters have an examine line), cozy
  multi-line conversations for Mallow and Bramble that progress through the story
  beats, success/failure/locked lines, and a resolver that maps (verb, faced
  target, selected item) onto an Outcome carrying the dialogue lines + the exact
  flag/inventory change (which is the ONLY progression state -- never hardcoded
  outside docs/world.json's actions).
- `emberglow/game.py` -- the live controller: the four verb keys (X/T/G/U), a real
  inventory with Tab/[ selection and item-use (use the selected item on the faced
  target; consumed only on the correct target, otherwise a distinct failure line),
  multi-line conversations advanced with the interact key, and visible success vs
  failure feedback (dialogue-panel accent + target-marker stamp + prompt color).
- `emberglow/worldreact.py` -- flag-aware scene building + the world-reactivity
  beats (water_flowing, lens_ready, seed_taken, stair_open, lantern_lit, ended).
- `emberglow/ui.py` / `emberglow/checks.py` -- tone-colored interface treatment and
  pixel-sampling checks that prove success vs failure renders differently and each
  world beat produces distinct pixels (vision-free).
- `tests/test_verbs.py` -- verb model, acquisition + duplicate prevention, valid and
  invalid item use, locked gating, bare "operate" actions, conversation progression,
  and a full 11-action playthrough driven end-to-end by verbs.resolve.
- `tools/demo_adventure.py` -- a full 11-action playthrough through the real event
  queue (pygame.event.post -> get -> Game.handle_event) ending at 'ended', with a
  JSON runtime trace + success/failure/lantern-lit/ended frame dumps.

Controls: WASD/arrows walk, X examine, T talk, G take, U use (selected item),
Tab/[ cycle the selected item, E is a contextual "do the obvious thing", Escape
dismisses dialogue, Q quits.

## Install (one command)

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

Requires Python 3.10+ (pygame-ce 2.5.8 ships manylinux wheels for CPython 3.10
through 3.15). No other dependencies, no build step. All art is generated in
code at runtime, so there are no image/audio assets to download. If your distro
lacks `python3 -m venv`, install its python3-venv package first.

## Run

    .venv/bin/python -m emberglow.main                # live game (real input: WASD/arrows)
    .venv/bin/python -m emberglow.main --headless     # one frame -> evidence/scene_gate.png
    .venv/bin/python -m emberglow.main --capture 6    # animation frames -> evidence/
    .venv/bin/python -m emberglow.main --check        # render + full automated verification
    .venv/bin/python -m emberglow.main --market-check      # node 16: Forge Market scene verification
    .venv/bin/python -m emberglow.main --mill-check        # node 17: Mill Court scene verification
    .venv/bin/python -m emberglow.main --greenhouse-check  # node 18: Firefly Greenhouse scene verification
    .venv/bin/python -m emberglow.main --crown-check       # node 19: Lantern Crown scene verification
    .venv/bin/python -m emberglow.main --population-check  # node 14: world.json catalog agreement
    .venv/bin/python -m emberglow.main --input-check       # input-mapping + press/release tests

## Verify (automated, no vision)

    .venv/bin/python -m unittest discover -s tests   # 144 tests: geometry/palette/world/input/verbs/scenes/progression
    .venv/bin/python -m emberglow.main --check       # pixel sampling + geometry + draw order + beats + ending
    .venv/bin/python -m emberglow.main --market-check      # node 16: Forge Market room render + geometry + props
    .venv/bin/python -m emberglow.main --mill-check        # node 17: Mill Court room render + geometry + props
    .venv/bin/python -m emberglow.main --greenhouse-check  # node 18: Firefly Greenhouse room render + geometry + props
    .venv/bin/python -m emberglow.main --crown-check       # node 19: Lantern Crown room render + geometry + props
    .venv/bin/python -m emberglow.main --population-check  # node 14: world.json catalog agreement
    .venv/bin/python -m emberglow.main --input-check       # node 4: key mapping + press/release
    .venv/bin/python tools/demo_input.py             # node 4: actual-input runtime trace + frame dumps
    .venv/bin/python tools/demo_traversal.py         # node 3: traversal demo (exits 0)
    .venv/bin/python tools/demo_adventure.py         # node 5: full 11-action playthrough + beats/feedback
    .venv/bin/python -m unittest tests.test_progression  # node 15: chain / out-of-order / softlock proof
    .venv/bin/python tools/demo_progression.py       # node 15: headless playthrough + lantern_lit/ended captures

## Distribution & reproducibility (node 7)

The game is distributed as this repository itself -- an explicitly documented
installation bundle -- because every asset is generated in code, so `git clone`
plus the one-command install above is the complete distribution (no missing
assets, no undeclared dependencies). A clean-room install has been verified
end-to-end in a fresh disposable clone on CPython 3.14 and 3.12: the one-command
install succeeds, `--headless` writes a frame, the full 144-test suite passes,
and `--check` regenerates fresh evidence frames + JSON. The dependency and
asset-license inventory is in docs/DEPENDENCIES.md.

For an offline/air-gapped copy, a source tarball is made with:

    git archive --format=tar.gz -o emberglow-hollow-<rev>.tar.gz HEAD

Unpacking that tarball yields the identical one-command install and run recipe.

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
confirmation of feel.

Node 5 (explicit verbs + inventory + dialogue + feedback) is complete and
self-verifying: 83 unit tests pass headless, tools/demo_adventure.py drives the
full 11-action playthrough through the real event queue to 'ended', and the
pixel-sampling checks prove success-vs-failure feedback is distinct and all six
world-reactivity beats (water_flowing, lens_ready, seed_taken, stair_open,
lantern_lit, ended) produce distinct pixels. Remaining: per-room art polish, soft
audio, and final human aesthetic judgment (Rick's, on Pop!_OS).

Node 16 (Forge Market art) is complete and self-verifying: the market room
is now an art-complete scene (raised brick forge hearth + anvil, canvas-
awning stalls, crates, lantern posts, and Bramble the forge-smith) built to
node 2's palette + visual language and wired into the live game. See
docs/NODE16_SCENE.md; verify with `python3 -m emberglow.main --market-check`.

Node 17 (Mill Court art) is complete and self-verifying: the mill room is now
an art-complete scene (russet waterwheel, stone-lined mill-race Brook channel,
Crank Socket + Water Spout, bark-brown plank mill house on a raised footing,
stacked timber, lantern posts) built to node 2's palette + visual language and
wired into the live game, including the water_flowing beat (Brook water fills
the race + pours from the spout). See docs/NODE17_SCENE.md; verify with
`python3 -m emberglow.main --mill-check`.

Node 18 (Firefly Greenhouse art) is complete and self-verifying: the
greenhouse room is now an art-complete scene (glass house + glass walls,
raised plant beds, the pulsing Ember-Seed on a raised planter, the painted
founding-story Mural, vines over the west door, terracotta pots, a bench,
and dense ambient fireflies) built to node 2's palette + visual language and
wired into the live game, including the seed_taken beat (the seed dims and a
cool pool settles over the bed). See docs/NODE18_SCENE.md; verify with
`python3 -m emberglow.main --greenhouse-check`.

Node 15 (full quest progression + world reactivity) is complete and
self-verifying: the 11-action flag/item chain (meet_mallow -> request_flask ->
turn_wheel -> fill_flask -> take_seed -> cool_lens -> open_stair -> mount_lens ->
plant_seed -> kindle_lantern -> ring_bell), the room gates (water_flowing,
stair_open), the four big world-change beats (water flows, lens cooled, seed
taken, lantern lit), and the full ending sequence are wired end-to-end. The
ending now returns Mallow's long-lost companion (a little firefly-moth that
drifts home to the gatekeeper) and renders the one-line title "the fireflies
came home." on top of the firefly river. See docs/WALKTHROUGH.md for the
explicit step-by-step route. Verify with
`python3 -m unittest tests.test_progression` (chain / out-of-order / softlock
proof) and `python3 tools/demo_progression.py` (recorded headless playthrough +
fresh lantern_lit and ended captures).


Node 7 (reproducible Linux-only distribution) is complete and self-verifying:
a fresh disposable clone installs with the one-command recipe, launches
headless, passes the full 144-test suite, and `--check` regenerates fresh
evidence frames + check JSON. The dependency/asset-license inventory is in
docs/DEPENDENCIES.md; the single-command launch path is the "Quick start"
above. No Windows deliverable is required.
