# G13 -- Implementation Approach Decision

Status: DECIDED (this node). Art direction was already locked as "Emberglow Hollow"
(option B) per the G13 design doc (docs/ART_DIRECTIONS.md) and the node's task brief.
This document chooses HOW to implement it and proves the choice runs headless here.

## Decision (one line)

Language/engine: Python 3.14 + pygame-ce 2.5.x (the community-maintained pygame, SDL2
backend). Rendering: a fixed 2:1 isometric software compositor with painter's-algorithm
depth sort, tile elevation ("2.5D"), procedural painterly tiles, and a warm/cool
two-light model (warm lit surfaces vs a single Twilight-Violet ambient).

## Why this stack

The choice is driven by five hard constraints, none of which I assumed -- all were
re-verified on this server this session:

1. Headless server. This host is a headless VM with no GPU (software Mesa llvmpipe only,
   per CAPABILITY.md). The chosen stack must render and frame-dump without a display.
   pygame-ce renders to an offscreen SDL2 surface and saves a PNG in one call under
   SDL_VIDEODRIVER=dummy -- proven here (evidence/emberglow_spike.png).

2. Single-command deploy. Rick playtests on Pop!_OS and wants trivial install/run.
   pygame-ce ships Linux x86_64 wheels for Python 3.14, so install is one command:
   `pip install -r spike/requirements.txt` (or `uv run`), then `python
   spike/isometric_spike.py`. No engine binary, no project-import step, no compile.

3. Art is code-driven. The locked art direction forbids image-gen and hand-drawn assets:
   everything is procedural. Python is the best fit for the painterly noise, palette
   math (HSV jitter), and deterministic generation the spec requires.

4. No vision tool. Workers must verify rendering by code-level pixel sampling. Software
   compositing is byte-reproducible given a seed, so pixel-sampling assertions are exact
   and stable -- ideal for an automated verification loop that has no eyes.

5. Scope is small. G13 is a modest adventure (5 rooms, 11 actions, one item chain from
   node 1's world.json). A hand-rolled scene graph, input, audio, and UI in pygame is
   tractable; a full engine is heavier than the problem needs.

## Alternatives considered (and rejected)

- Godot 4: the strongest alternative. Excellent built-in 2D lighting/particles (would
  make fireflies and glow easier), IsometricTileMap, one-download runtime. Rejected for
  THIS project because (a) Ubuntu 26.04 packages only Godot 3.x -- Godot 4 is a ~50 MB
  manual binary download, (b) headless frame capture needs Xvfb plus a viewport
  readback or `--write-movie` pass (more moving parts to verify on a worker box),
  (c) a heavier import/project scaffold. Still the fallback if G13 later needs real
  particle/lighting authoring that pygame's procedural glow can't match.

- LOVE (Lua): capable and light, but a thinner stdlib for procedural art and less
  ergonomic headless capture. More manual code for the same result.

- C + SDL2/OpenGL: the most self-contained final artifact, but the slowest to iterate
  and the highest bug risk for painterly procedural art. Not worth it art-first.

- Web/Canvas (Node): not a natural desktop game; would need a browser/Electron wrapper.

## Rendering pipeline (fixed-isometric 2.5D)

1. Projection: fixed 2:1 iso, world unit 64 px (64x32 diamond tiles), no rotation/zoom:
   sx = (gx - gy) * 32 + OX, sy = (gx + gy) * 16 + OY.
2. Depth: painter's algorithm -- sort tiles and props by (gx + gy) back-to-front. Tile
   elevation ELEV = 16 px/unit extrudes two shaded side faces under the top face, which
   is what produces the "2.5D" read (a fixed camera over a 2D scene, not full 3D).
3. Terrain: procedural painterly top faces -- per-pixel value (+/-8%) and saturation
   (+/-6%) jitter from ONE shared, world-space, deterministic value-noise seed (so the
   brush is continuous across the whole map, no per-object noise soup), with a soft 1px
   feathered diamond edge (soft edges only, per the art direction).
4. Props: billboarded painterly "cards" (soft-edged discs/rects with a warm rim light
   toward the north-west). Interactables get a Firefly-Glow halo instead of an outline
   (the art direction forbids hard outlines).
5. Light: warm lit surfaces (the locked Emberglow Hollow hex palette) against a single
   cool Twilight-Violet ambient (backdrop + multiply vignette), plus an additive
   Honey-Gold lantern glow and Firefly-Glow accents. Shadows/ambient are violet, never
   black -- matching the palette's cohesion rule.

The locked Emberglow Hollow palette (from docs/ART_DIRECTIONS.md) is hardcoded in
spike/isometric_spike.py: Hearth Amber, Honey Gold, Pumpkin, Russet, Moss Green, Fern
Deep, Cream Parchment, Bark Brown, Firefly Glow, Twilight Violet.

## Spike (proof, committed)

spike/isometric_spike.py renders a 12x12 Emberglow Hollow scene (a winding
Cream-Parchment path, a raised hill with a lantern-crown tree, a cottage with a warm
window, mushrooms, fireflies) and is deterministic given SEED.

Modes:
  python3 spike/isometric_spike.py            # live window (Rick playtest)
  python3 spike/isometric_spike.py --headless # frame-dump to evidence/
  python3 spike/isometric_spike.py --check    # render + 7 pixel-sampling assertions

Verified THIS session on this server (headless, SDL dummy driver), all 7 checks green
(see evidence/spike_check.json): correct 1280x720 size, non-blank (4,885 unique colors),
warm light present, cool violet ambient present, firefly glow present, a sampled grass
tile top-face is green, and a raised tile's side face is darker than its top face (the
2.5D extrusion). The ASCII structure map in evidence/emberglow_spike.ascii.txt shows a
diamond-shaped warm/green hollow on a cool violet backdrop -- the isometric grid is
structurally correct. Palette coverage of sampled pixels is 100% at dE <= 50 (painterly
jitter stays on-palette).

Note: the spike's ~5 s startup is one-time procedural tile generation (no asset
pipeline yet). Production would pre-render and cache tiles once at boot; steady-state
rendering is just blits.

## Trade-off accepted (recorded, not hidden)

pygame is a framework, not an engine. We hand-roll the scene graph, input, audio, UI,
and emulate glow/fireflies with additive radial sprites instead of Godot's built-in 2D
light nodes. For a five-room fixed-isometric adventure this is comfortably in scope and
keeps the whole game a small, auditable, single-language codebase. If Rick prefers
Godot 4 for its lighting/particle tooling, the palette, projection, and scene data all
port directly -- the art direction and layout are engine-agnostic.

## Go / no-go

Go: pygame-ce is proven installable and runnable here and deployable on Pop!_OS in one
command. Recommend building G13 on this stack. (Rick's sign-off recorded at node 12+.)
