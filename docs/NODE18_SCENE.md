# G13 node 18 -- Representative scene: Firefly Greenhouse

## What this scene is

The fourth art-complete room of Emberglow Hollow, built to the exact palette and
visual language node 2 established with the Hollow Gate scene (and nodes 16/17
with the Forge Market and Mill Court). The Firefly Greenhouse is the glass house
glowing with drifting fireflies: a translucent glass structure over a stone floor,
raised plant beds around the walls, the pulsing Ember-Seed on a raised planter,
and the painted founding-story Mural -- rendered through the existing
fixed-isometric renderer and wired into the live game (walk in from the Mill
Court's east portal, once water_flowing, and the room draws as this scene).

## Composition (9x9 grid, fixed 2:1 isometric, 64 px world unit)

- Terrain: a Cream-Parchment stone floor inside the glass house, opening to the
  west (Mill Court) portal through a vine-draped door; Moss-Green grass banks
  around the enclosing treeline. The Ember-Seed bed sits on a raised (h=1) stone
  planter (the 2.5D extrusion, echoing node 2's hilltop, node 16's forge plinth,
  and node 17's mill footing). One shared world-space painterly noise seed
  throughout.
- Props: the glass house (a pitched translucent glass roof + glass-wall band with
  bark mullions) on the north edge, glass-wall panels on the north and east
  flanks, eight raised Plant Beds around the walls (moss/fern), the painted Mural
  (light, water, and a growing seed -- the founding story), the pulsing
  Ember-Seed on its raised planter, vines over the west door, terracotta pots,
  a wooden bench, one warm lantern post, plus mushrooms, rocks, grass tufts and
  flowers for the same cozy ground-dressing as the gate.
- Lighting: warm Hearth-Amber lantern glow + Honey-Gold mural glow (additive), a
  single cool Twilight-Violet dusk sky + multiply vignette (never black), and --
  this room's signature -- bright Firefly-Glow clusters and ambient fireflies
  throughout (roughly 8x the firefly density of the other rooms).
- Interface: top-left room chip ("Firefly Greenhouse -- a glass greenhouse
  glowing with fireflies"), a hint line, the bottom inventory strip and a short
  dialogue panel -- all Cream-Parchment panels, Bark-Brown text, in-palette.
- Animation (restrained, deterministic in t): firefly drift + twinkle, glow
  flicker.
- World beat (seed_taken): the Ember-Seed dims on its planter (the live spark is
  gone) and a cool Twilight-Violet pool settles over the bed, so taking the seed
  visibly changes the room.

## Automated verification (no vision tool)

evidence/greenhouse_check.json records all green checks; evidence/
greenhouse_scene.png (UI frame), evidence/greenhouse_scene_room.png (bare room),
and evidence/greenhouse_live_frame.png (the live game in the greenhouse) are
fresh runtime frames at 1280x720. The greenhouse checks cover: fixed 2:1
projection, diamond 2:1 bounds, painter's-algorithm draw order (tiles monotonic,
props after their own tile, far-before-near), 2.5D extrusion (raised seed planter
side face darker than top face), on-palette flat fills (floor tile Cream-
Parchment, grass tile Moss-Green), warm lit surfaces + cool violet ambient + no
pure black, prop presence (glass house / glass wall bark frame, plant bed moss,
mural honey-gold, seed hearth-amber, vine fern-deep), interface presence, frame
determinism + animation, and the seed_taken beat (warm pixels vanish from the
seed bed). tests/test_greenhouse.py adds 9 scene-composition + render smoke tests
(interactables on their object cells, plant beds aligned with the worldmap
obstacle cells, every prop kind resolves to a sprite, no ghost static player,
worldreact routing + seed_taken flip).

Run it with:

    python3 -m emberglow.main --greenhouse-check

## Unverified visual concerns (deferred to Rick's playtest)

- Subjective aesthetic judgment (painterly feel, glow subtlety, whether the glass
  house reads as a glass greenhouse and the fireflies as warm, composition) is
  NOT verifiable here without vision; this node verifies palette/geometry/depth/
  lighting by code only.
- The glass panes are translucent cream-parchment fills (alpha ~150) over the
  backdrop; whether they read as convincing glass versus simply pale panels is a
  taste call best confirmed by Rick on Pop!_OS.
- The ember-seed's pulsing read is a warm sprite (no additive pulse); a slow
  brightness-pulse animation on the seed is a possible later polish pass, not a
  correctness issue.
- Character faces remain minimal (cream disc + eye dot); richer expression is a
  later polish pass.
