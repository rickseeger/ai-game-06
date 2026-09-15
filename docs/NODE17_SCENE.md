# G13 node 17 -- Representative scene: Mill Court

## What this scene is

The third art-complete room of Emberglow Hollow, built to the exact palette and
visual language node 2 established with the Hollow Gate scene (and node 16 with
the Forge Market). The Mill Court is the wooden waterwheel at the hollow's edge:
a paved courtyard with a big russet waterwheel on the west, the stone-lined
mill-race Brook channel (dry until the water flows), the Crank Socket and Water
Spout, a bark-brown plank mill house on a raised stone footing (SE), and stacked
timber (NE) -- rendered through the existing fixed-isometric renderer and wired
into the live game (walk in from the Forge Market's north portal and the room
draws as this scene).

## Composition (9x9 grid, fixed 2:1 isometric, 64 px world unit)

- Terrain: a Cream-Parchment paved court with paths to the south (Forge Market)
  and east (Firefly Greenhouse) portals; Moss-Green grass banks around the
  enclosing treeline. A raised (h=1) stone footing under the mill house (the 2.5D
  extrusion, echoing node 2's hilltop and node 16's forge plinth). One shared
  world-space painterly noise seed throughout.
- Props: the Waterwheel (russet rim + bark spokes, on the west edge), the
  stone-lined Mill-Race channel (west edge, dry bed), the Crank Socket and the
  Water Spout (the room's two interactables), the Mill House (pitched russet roof,
  bark-brown plank facade, warm windows, a mill chute), two Stacked Timber piles
  (NE), two warm lantern posts, plus mushrooms, rocks, grass tufts, flowers and
  fencing for the same cozy ground-dressing as the gate.
- Lighting: warm Hearth-Amber lantern glows + Honey-Gold mill-house window glows
  (additive), a single cool Twilight-Violet dusk sky + multiply vignette (never
  black), Firefly-Glow halos on the two interactables (Crank Socket, Water Spout),
  ambient fireflies.
- Interface: top-left room chip ("Mill Court -- a wooden waterwheel at the
  hollow's edge"), a hint line, the bottom inventory strip and a short dialogue
  panel -- all Cream-Parchment panels, Bark-Brown text, in-palette.
- Animation (restrained, deterministic in t): firefly drift + twinkle, glow flicker.
- World beat (water_flowing): the mill-race fills with Brook (cool accent) water
  and the spout pours (a Brook "spout_flow" overlay + cool Brook glow), so the
  wheel-fixing step visibly changes the room.

## Automated verification (no vision tool)

evidence/mill_check.json records all green checks; evidence/mill_scene.png (UI
frame) and evidence/mill_scene_room.png (bare room) are fresh runtime frames at
1280x720. The mill checks cover: fixed 2:1 projection, diamond 2:1 bounds,
painter's-algorithm draw order (tiles monotonic, props after their own tile,
far-before-near), 2.5D extrusion (raised footing side face darker than top face),
on-palette flat fills (court tile Cream-Parchment, grass tile Moss-Green), warm
lit surfaces + cool violet ambient + no pure black, prop presence (waterwheel
russet / mill house bark / timber bark / crank socket russet / water spout
russet), interface presence, frame determinism + animation, and the water_flowing
beat (Brook cool pixels appear at the mill-race + spout). tests/test_mill.py adds
9 scene-composition + render smoke tests (interactables on their object cells,
obstacle props aligned with the worldmap cells, every prop kind resolves to a
sprite, no ghost static player, worldreact routing + water_flowing overlay).

Run it with:

    python3 -m emberglow.main --mill-check

## Unverified visual concerns (deferred to Rick's playtest)

- Subjective aesthetic judgment (painterly feel, glow subtlety, whether the wheel
  reads as a wooden waterwheel and the mill house as a mill, composition) is NOT
  verifiable here without vision; this node verifies palette/geometry/depth/
  lighting by code only.
- The waterwheel is a flat russet/bark ring-and-spoke silhouette (no motion);
  a slow wheel-turn animation when water_flowing is a possible later polish pass,
  not a correctness issue.
- The spout_flow overlay is positioned at the spout cell's anchor; its exact
  alignment with the spout mouth (so the water appears to pour, not float) is a
  taste/eyeball call best confirmed by Rick on Pop!_OS.
- Character faces remain minimal (cream disc + eye dot); richer expression is a
  later polish pass.
