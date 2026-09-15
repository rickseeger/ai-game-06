# G13 node 16 -- Representative scene: Forge Market

## What this scene is

The second art-complete room of Emberglow Hollow, built to the exact palette and
visual language node 2 established with the Hollow Gate scene. The Forge Market is
the warm, busy heart of the hollow: a paved market square under canvas awnings, a
raised brick forge hearth with an anvil, and Bramble the forge-smith -- rendered
through the existing fixed-isometric renderer and wired into the live game (walk in
from the Hollow Gate's east portal and the room draws as this scene).

## Composition (9x9 grid, fixed 2:1 isometric, 64 px world unit)

- Terrain: a large Cream-Parchment paved market square with paths to the west (Hollow
  Gate) and north (Mill Court) portals; Moss-Green grass banks around the enclosing
  treeline. A raised (h=1) stone plinth under the forge block (the 2.5D extrusion,
  echoing node 2's hilltop). One shared world-space painterly noise seed throughout.
- Props: the Forge (russet brick kiln + glowing hearth mouth + bark-brown anvil, on
  the raised plinth, with a chimney), nine Pumpkin canvas-awning market stalls
  (goods on the counters), two wooden crates, two warm lantern posts, plus mushrooms,
  rocks, grass tufts and flowers for the same cozy ground-dressing as the gate.
- Characters: **Bramble** (stocky forge-smith: fern shirt, russet apron, pumpkin
  bandana, hammer in hand) -- the market's interactable character.
- Lighting: warm Hearth-Amber + Honey-Gold forge/lantern glows (additive), a single
  cool Twilight-Violet dusk sky + multiply vignette (never black), Firefly-Glow
  halos on the two interactables (Forge, Bramble), ambient fireflies.
- Interface: top-left room chip ("Forge Market -- a warm forge under canvas"), a
  hint line, the bottom inventory strip and a short Bramble dialogue panel -- all
  Cream-Parchment panels, Bark-Brown text, in-palette.
- Animation (restrained, deterministic in t): firefly drift + twinkle, glow flicker.

## Automated verification (no vision tool)

evidence/market_check.json records all green checks; evidence/market_scene.png (UI
frame) and evidence/market_scene_room.png (bare room) are fresh runtime frames at
1280x720. The market checks cover: fixed 2:1 projection, diamond 2:1 bounds,
painter's-algorithm draw order (tiles monotonic, props after their own tile,
far-before-near), 2.5D extrusion (raised plinth side face darker than top face),
on-palette flat fills (square tile Cream-Parchment, grass tile Moss-Green), warm
lit surfaces + cool violet ambient + no pure black, prop presence (forge russet /
stall pumpkin / crate russet / Bramble fern-deep), interface presence, frame
determinism + animation, and the lens_ready beat (the forge flashes clearly warmer
when the lens is ready). tests/test_market.py adds 9 scene-composition + render
smoke tests (forge interactable on the raised plinth, props aligned with the
worldmap obstacle/object cells, every prop kind resolves to a sprite, no ghost
static player, worldreact routing).

Run it with:

    python3 -m emberglow.main --market-check

## Unverified visual concerns (deferred to Rick's playtest)

- Subjective aesthetic judgment (painterly feel, glow subtlety, whether the forge
  reads warm-but-not-blinding, stall charm) is NOT verifiable here without vision;
  this node verifies palette/geometry/depth/lighting by code only.
- The additive forge glow washes nearby warm props toward orange at close range
  (a deliberate warm pool, but its subtlety is a taste call).
- Character faces remain minimal (cream disc + eye dot); richer expression is a
  later polish pass, not a correctness issue.
