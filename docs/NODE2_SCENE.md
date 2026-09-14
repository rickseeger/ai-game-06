# G13 node 2 -- Representative scene: Hollow Gate

## What this scene is

The fixed-isometric visual foundation plus the **Hollow Gate** room (the home room
from docs/world.json), rendered as a connected part of the bounded 5-room world --
not a throwaway. The player has just arrived; Mallow has greeted you and handed over
the Crank Handle (the opening beat, action `meet_mallow`).

## Composition (9x9 grid, fixed 2:1 isometric, 64 px world unit)

- Terrain: a Cream-Parchment cobbled common + paths to the crown (top) and market
  (right) portals; Moss-Green grass banks; a raised (h=1) hilltop along the top edge
  (the "2.5D" extrusion). Painterly brush from ONE shared world-space noise seed.
- Props: four mushroom-roof cottages framing the common (Pumpkin caps, Cream walls,
  warm windows), the Hollow Bell on a wooden frame, the moss-choked Hill Stair,
  two lantern posts, mushrooms, rocks, grass tufts, flowers, a fence.
- Characters: **Mallow** (russet robe + fern hood, holding a small lantern) and the
  **player** (bright honey-gold cloak + pumpkin cap + hearth-amber scarf, idle bob).
- Lighting: warm Hearth-Amber / Honey-Gold lantern glows (additive), a single cool
  Twilight-Violet dusk sky + multiply vignette (never black), Firefly-Glow halos on
  the three interactables (Mallow, Bell, Stair) instead of outlines.
- Interface: top-left room chip ("Hollow Gate -- the long dusk"), a hint line, a
  bottom inventory strip (Crank Handle selected, Firefly-Glow highlight) and a short
  Mallow dialogue panel -- all Cream-Parchment panels, Bark-Brown text, in-palette.
- Animation (restrained, deterministic in t): firefly drift + twinkle, lantern-glow
  flicker, player idle bob, a barely-there bell sway.

## Automated verification (no vision tool)

evidence/check_results.json records all green checks; evidence/scene_gate*.png are
fresh runtime frames at 1280x720 (t00..t05 show the animation). The unit tests cover
projection, palette discipline, and a pixel-level painter's-algorithm occlusion test.

## Unverified visual concerns (deferred to Rick's playtest at node 8)

- Subjective aesthetic judgment (painterly feel, glow subtlety, composition, whether
  the silhouettes are charming) is NOT verifiable here without vision; this node
  verifies palette/geometry/depth/lighting by code only.
- Prop edges are soft-scaled but not antialiased per-primitive; fine at 1280x720 but
  a possible polish item if Rick finds silhouettes too crisp.
- Character faces are minimal (a cream disc + eye dot); richer expression is a later
  polish pass, not a correctness issue.
