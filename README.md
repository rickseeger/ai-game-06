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
Rendering and artistic coherence are owned here; navigation, quest logic, audio, and
final human aesthetic judgment (Rick at node 8) are out of scope for this node.
See docs/NODE2_SCENE.md for the scene's composition and the unverified visual notes.
