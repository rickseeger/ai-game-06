"""Flag-aware scene building + world-reactivity overlays for Emberglow Hollow.

Owns the mapping from the player's world state (room + flags) to the concrete
SceneRoom the renderer draws. The base scenes come from node 2/3 (the art-complete
Hollow Gate, and marker/rock stand-ins for the other four rooms); this module then
applies the world-reactivity beats declared in docs/ADVENTURE_DESIGN.md section 9:

  - water_flowing : Brook (cool accent) water pours at the mill-race / spout
  - lens_ready    : the forge flashes a bright warm light
  - seed_taken    : the greenhouse seed-bed dims (the live spark is gone)
  - stair_open    : a ribbon of warm light marks the cleared Hill Stair
  - lantern_lit   : the Heart-Lantern floods the crown in warm light
  - ended         : fireflies pour back over the ridge (a golden river)

These overlays are pure additions to the scene graph (glows, props, fireflies), so
the beat changes are deterministic and pixel-samplable (see emberglow/checks.py).
"""

from __future__ import annotations

from typing import Dict, FrozenSet

from .scene import (Room as SceneRoom, Prop, Glow, build_room_gate,
                   build_room_market, build_room_mill, build_room_greenhouse,
                   build_room_crown)

# Object id (docs/world.json ``objects`` / ``characters``) -> scene prop kind.
#
# This is the single catalog-agreement table for node 14's population contract:
# every entity authored in docs/world.json must be placed in its room's finished
# scene as exactly this prop kind, at the exact world.json grid cell. It backs the
# generic (marker/rock) fallback scene AND the catalog-agreement test in
# tests/test_population.py, so a divergence between the art and the data is caught
# mechanically rather than by eye.
OBJECT_PROP_KIND: Dict[str, str] = {
    # Hollow Gate
    "mallow": "mallow", "hollow_bell": "bell", "hill_stair": "stair",
    # Forge Market
    "bramble": "bramble", "forge": "forge",
    # Mill Court
    "crank_socket": "crank_socket", "water_spout": "water_spout",
    # Firefly Greenhouse
    "ember_seed": "seed", "mural": "mural",
    # Lantern Crown
    "seed_cradle": "seed_cradle", "lens_mount": "lens_mount",
    "focus_wheel": "focus_wheel",
}

# The four non-gate rooms' ambient fireflies (they return home on 'ended').
_BASE_FIREFLIES: Dict[str, list] = {
    "market": [(1.8, 2.1), (6.4, 2.6), (3.1, 4.2), (5.7, 5.1), (2.6, 6.4)],
    "mill": [(2.2, 4.1), (5.6, 1.9), (4.3, 6.2), (7.2, 3.4)],
    "greenhouse": [(1.9, 1.7), (4.1, 1.4), (6.3, 1.8), (2.2, 4.6), (5.8, 4.4),
                   (4.0, 6.3), (6.6, 6.1), (1.7, 6.2)],
    "crown": [(2.4, 6.6), (5.7, 6.8), (3.6, 5.9)],
}


def generic_scene(world, rid: str) -> SceneRoom:
    """Stand-in scene for the four rooms without dedicated art yet."""
    data = world.data["rooms"][rid]
    room = SceneRoom(9, data["title"], data.get("mood", ""))
    for cell in sorted(world.rooms[rid].obstacles):
        room.props.append(Prop("rock", cell[0], cell[1]))
    for name, cell in sorted(world.rooms[rid].objects.items()):
        kind = OBJECT_PROP_KIND.get(name, "marker")
        room.props.append(Prop(kind, cell[0], cell[1], interactable=True))
    return room


def apply_beats(world, room: SceneRoom, rid: str, flags: FrozenSet[str]) -> SceneRoom:
    """Apply the world-reactivity overlays for the given flags. Mutates + returns room."""
    F = set(flags)

    # --- water_flowing: Brook water at the mill-race + spout -----------------
    if rid == "mill" and "water_flowing" in F:
        for cell in ((1, 5), (1, 6)):
            room.props = [p for p in room.props if not (p.gx == cell[0] and p.gy == cell[1])]
            room.props.append(Prop("water", cell[0], cell[1]))
        room.props.append(Prop("spout_flow", 6, 3))
        room.glows.append(Glow(6.0, 3.0, "brook", 42, 150))

    # --- lens_ready: the forge flashes a bright warm light --------------------
    if rid == "market" and "lens_ready" in F:
        room.props.append(Prop("forge_flash", 6, 3, h=1))

    # --- seed_taken: the greenhouse seed-bed dims -----------------------------
    if rid == "greenhouse":
        for p in room.props:
            if p.gx == 4 and p.gy == 3 and p.kind in ("seed", "seed_bed", "marker"):
                p.kind = "seed_bed" if "seed_taken" in F else "seed"
                p.interactable = "seed_taken" not in F
        if "seed_taken" in F:
            room.glows.append(Glow(4.0, 3.0, "twilight_violet", 36, 70))

    # --- stair_open: a ribbon of warm light up the cleared Hill Stair ---------
    if rid == "gate" and "stair_open" in F:
        room.props.append(Prop("stair_light", 5, 1))

    # --- seed_planted: the ember-seed glows in the crown cradle ---------------
    if rid == "crown":
        for p in room.props:
            if p.gx == 3 and p.gy == 3 and p.kind == "seed_cradle":
                p.kind = "seed_cradle_planted" if "seed_planted" in F else "seed_cradle"
                p.interactable = "seed_planted" not in F
            if p.gx == 5 and p.gy == 3 and p.kind == "lens_mount":
                p.kind = "lens_mount_lit" if "lens_mounted" in F else "lens_mount"
                p.interactable = "lens_mounted" not in F
        if "seed_planted" in F:
            room.glows.append(Glow(3.0, 3.0, "hearth_amber", 40, 72))
        if "lens_mounted" in F:
            room.glows.append(Glow(5.0, 3.0, "honey_gold", 36, 62))

    # --- lantern_lit: the Heart-Lantern floods the crown in warm light --------
    if rid == "crown" and "lantern_lit" in F:
        room.glows.append(Glow(4.0, 3.0, "hearth_amber", 130, 230))
        room.glows.append(Glow(4.0, 4.0, "honey_gold", 110, 210))

    # --- ended: fireflies pour back in a golden river --------------------------
    if "ended" in F:
        extra = [(3.2, 7.4), (4.8, 7.2), (5.6, 6.8), (2.6, 6.9), (6.4, 6.6),
                 (3.9, 6.2), (5.1, 6.0), (4.2, 5.4), (6.0, 5.2), (3.5, 5.0),
                 (5.4, 4.6), (4.0, 4.2), (6.2, 3.8), (4.8, 3.4), (3.6, 3.0)]
        room.fireflies.extend(extra)

    return room


def build_scene_room(world, rid: str, flags: FrozenSet[str]) -> SceneRoom:
    """The concrete scene for `rid` under `flags` (base + world-reactivity beats)."""
    if rid == "gate":
        room = build_room_gate()
        room.props = [p for p in room.props if p.kind != "player"]
    elif rid == "market":
        room = build_room_market()
    elif rid == "mill":
        room = build_room_mill()
    elif rid == "greenhouse":
        room = build_room_greenhouse()
    elif rid == "crown":
        room = build_room_crown()
    else:
        room = generic_scene(world, rid)
    # baseline ambient glows + fireflies for the non-gate rooms
    if rid != "gate":
        for anchor in _BASE_FIREFLIES.get(rid, []):
            room.fireflies.append(anchor)
    return apply_beats(world, room, rid, flags)
