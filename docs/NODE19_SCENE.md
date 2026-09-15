# G13 node 19 -- Representative scene: Lantern Crown

## What this scene is

The fifth art-complete room of Emberglow Hollow, built to the exact palette and
visual language node 2 established with the Hollow Gate scene (and nodes 16/17/18
with the Forge Market, Mill Court and Firefly Greenhouse). The Lantern Crown is
the hilltop where the Heart-Lantern waits: a rocky north ridge, the great
lantern-crown tree hung with warm lanterns, the Seed Cradle, the Lens Mount and
the Focus Wheel -- rendered through the existing fixed-isometric renderer and
wired into the live game (climb up from the Hollow Gate's north portal once
stair_open, and the room draws as this scene).

## Composition (9x9 grid, fixed 2:1 isometric, 64 px world unit)

- Terrain: a Cream-Parchment hilltop clearing with a path down the south stair
  (to the Hollow Gate); Moss-Green grass banks around the enclosing treeline. A
  raised (h=1) rocky north ridge and a raised (h=1) mound under the tree give the
  2.5D extrusion (echoing node 2's hilltop, node 16's forge plinth, node 17's
  mill footing and node 18's seed planter). One shared world-space painterly
  noise seed throughout.
- Props: the great lantern-crown tree (bark trunk, layered moss canopy, a crown
  of hanging warm lanterns and the central Heart-Lantern) on its raised mound;
  the rocky ridge crest along the north; the three interactables (Seed Cradle,
  Lens Mount, Focus Wheel); three warm lantern posts around the clearing; the
  south stair crest descending to the gate; plus mushrooms, rocks, grass tufts,
  flowers and fencing for the same cozy ground-dressing as the gate.
- Lighting: warm Hearth-Amber / Honey-Gold lantern glows (additive) from the
  crown of lanterns and the clearing posts, a single cool Twilight-Violet dusk
  sky + multiply vignette (never black), Firefly-Glow halos on the three
  interactables, ambient fireflies.
- Interface: top-left room chip ("Lantern Crown -- a hilltop lit with
  lanterns"), a hint line, the bottom inventory strip and a short dialogue
  panel -- all Cream-Parchment panels, Bark-Brown text, in-palette.
- Animation (restrained, deterministic in t): firefly drift + twinkle, glow flicker.
- World beats: seed_planted (the ember-seed glows in the cradle), lens_mounted
  (the dew-cooled lens glints in its mount), lantern_lit (the Heart-Lantern
  floods the whole crown in warm light).

## Automated verification (no vision tool)

evidence/crown_check.json records all green checks; evidence/crown_scene.png (UI
frame) and evidence/crown_scene_room.png (bare room) are fresh runtime frames at
1280x720. The crown checks cover: fixed 2:1 projection, diamond 2:1 bounds,
painter's-algorithm draw order (tiles monotonic, props after their own tile,
far-before-near), 2.5D extrusion (raised ridge side face darker than top face),
on-palette flat fills (clearing tile Cream-Parchment, grass tile Moss-Green,
raised ridge top Moss-Green), warm lit surfaces + cool violet ambient + no pure
black, prop presence (tree canopy moss-green / ridge russet / cradle
cream-parch / mount bark-brown / focus wheel bark-brown / lantern hearth-amber),
interface presence, frame determinism + animation, and the three world beats
(seed_planted warm pixels, lens_mounted brook-glint pixels, lantern_lit warm
flood). tests/test_crown.py adds 10 scene-composition + render smoke tests
(interactables on their object cells, obstacle props aligned with the worldmap
cells, every prop kind resolves to a sprite, no ghost static player, worldreact
routing + seed_planted/lens_mounted/lantern_lit flips).

Run it with:

    python3 -m emberglow.main --crown-check

## Unverified visual concerns (deferred to Rick's playtest)

- Subjective aesthetic judgment (painterly feel, glow subtlety, whether the tree
  reads as a lantern-crown and the ridge as a hill crest, composition) is NOT
  verifiable here without vision; this node verifies palette/geometry/depth/
  lighting by code only.
- The tree is a static bark-and-canopy silhouette with drawn lanterns; a slow
  sway or lantern-swing animation is a possible later polish pass, not a
  correctness issue.
- The south stair is the reused gate "stair" sprite placed at the portal edge;
  whether it reads as the top of the Hill Stair (versus a second climb) is a
  taste/eyeball call best confirmed by Rick on Pop!_OS.
- Character faces remain minimal (cream disc + eye dot); richer expression is a
  later polish pass.
