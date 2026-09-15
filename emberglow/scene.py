"""Scene graph + painter's-algorithm renderer for a fixed-isometric room.

The renderer owns drawing order (back-to-front by gx+gy), tile elevation (2.5D),
soft ground shadows, warm/cool lighting, and firefly animation. It is pure of any
input/quest logic: given a Room and a time t it produces a surface.
"""

from dataclasses import dataclass, field

import pygame

from . import animation as anim
from .geometry import (TILE_W, TILE_H, HW, HH, ELEV, iso, iso_f, depth_key,
                       prop_anchor, LAYER_TILE, LAYER_SHADOW, LAYER_PROP, LAYER_GLOW)
from .palette import PALETTE, darken, mix
from .sprites import (tile_top, draw_tile, radial_glow, halo, soft_shadow, sky,
                      vignette, get_sprite)


@dataclass
class Prop:
    kind: str
    gx: int
    gy: int
    h: int = 0                  # tile elevation under the prop
    interactable: bool = False  # draw a Firefly-Glow halo (no outline)
    anim: str = ""              # "" | "bob" | "sway"
    glow: str = ""              # glow color name (additive) at the prop anchor


@dataclass
class Glow:
    fx: float
    fy: float
    color: str
    radius: int
    peak: int


@dataclass
class Room:
    grid: int
    title: str
    subtitle: str
    heights: dict = field(default_factory=dict)
    path: set = field(default_factory=set)
    props: list = field(default_factory=list)
    glows: list = field(default_factory=list)
    fireflies: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Representative scene: the Hollow Gate room (home room, re-themed from world.json)
# --------------------------------------------------------------------------- #
def build_room_gate():
    grid = 9
    # cobbled common + paths to the crown (top) and market (right) portals
    common = {(3, 3), (3, 4), (3, 5), (4, 3), (4, 4), (4, 5), (4, 6),
              (5, 3), (5, 4), (5, 5), (6, 4)}
    path_to_crown = {(4, 1), (4, 2), (5, 1), (5, 2)}
    path_to_market = {(6, 4), (7, 4), (8, 4)}
    path = common | path_to_crown | path_to_market

    heights = {(4, 0): 1, (5, 0): 1, (6, 0): 1, (3, 0): 1, (7, 0): 1}

    props = [
        Prop("cottage", 1, 2), Prop("cottage", 2, 1), Prop("cottage", 7, 1),
        Prop("cottage", 1, 5),
        Prop("stair", 5, 1, interactable=True),
        Prop("bell", 6, 3, interactable=True, anim="sway"),
        Prop("lantern_post", 4, 4, glow="hearth_amber"),
        Prop("lantern_post", 7, 5, glow="hearth_amber"),
        Prop("mushroom", 0, 7), Prop("mushroom", 3, 7), Prop("mushroom", 7, 6),
        Prop("rock", 1, 7), Prop("rock", 8, 3),
        Prop("grass_tuft", 2, 4), Prop("grass_tuft", 6, 6), Prop("grass_tuft", 7, 7),
        Prop("grass_tuft", 3, 1), Prop("grass_tuft", 0, 4),
        Prop("flower", 3, 2), Prop("flower", 6, 6), Prop("flower", 2, 6),
        Prop("flower", 7, 7), Prop("flower", 1, 3),
        Prop("fence", 0, 2), Prop("fence", 0, 3),
        # characters (part of the art, not quest logic here)
        Prop("mallow", 2, 3, interactable=True, glow="hearth_amber"),
        Prop("player", 4, 6, anim="bob"),
    ]

    glows = [
        Glow(4.0, 4.0, "hearth_amber", 74, 60),
        Glow(7.0, 5.0, "hearth_amber", 60, 55),
        Glow(2.0, 3.0, "hearth_amber", 52, 62),   # Mallow's lantern
        Glow(1.0, 2.0, "honey_gold", 40, 46),     # cottage windows
        Glow(2.0, 1.0, "honey_gold", 40, 46),
        Glow(7.0, 1.0, "honey_gold", 40, 46),
    ]

    fireflies = [(2.3, 2.4), (3.8, 5.1), (1.6, 6.2), (5.2, 1.8), (8.4, 2.2),
                 (7.7, 4.6), (6.3, 6.9), (4.4, 7.3), (2.9, 5.6), (7.1, 6.4),
                 (3.6, 8.4), (0.9, 4.1), (8.8, 1.2), (5.8, 3.4), (6.2, 1.1)]

    return Room(grid, "Hollow Gate", "the long dusk", heights, path, props,
                glows, fireflies)




# --------------------------------------------------------------------------- #
# Forge Market (node 16): a warm, busy market square -- canvas-awning stalls,
# crates, a raised brick forge hearth with an anvil, and Bramble the forge-smith.
# Matches node 2's Hollow Gate scene in palette + visual language (painterly tiles,
# warm/cool two-light model, Firefly-Glow halos on interactables, fireflies).
# --------------------------------------------------------------------------- #
def build_room_market():
    grid = 9
    # paved market square + paths to the west (gate) and north (mill) portals
    square = {
        (1, 2), (2, 2), (3, 2), (4, 2), (5, 2),
        (1, 3), (3, 3), (4, 3), (5, 3),
        (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4),
        (1, 5), (3, 5), (4, 5), (6, 5), (7, 5),
        (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6),
        (3, 7), (4, 7), (7, 7),
    }
    path_to_mill = {(3, 1), (4, 1)}
    forge_plinth = {(6, 2), (7, 2), (6, 3), (7, 3)}   # raised stone plinth
    path = square | path_to_mill | forge_plinth

    # the forge block sits on a raised (h=1) stone platform -> 2.5D extrusion
    heights = {cell: 1 for cell in forge_plinth}

    props = [
        # the forge (NE): raised brick hearth + anvil -- the market's warm heart
        Prop("forge", 6, 3, h=1, interactable=True, glow="hearth_amber"),
        Prop("forge_kiln", 6, 2, h=1),
        Prop("forge_kiln", 7, 2, h=1),
        Prop("forge_kiln", 7, 3, h=1),
        # canvas-awning stalls along the north and south edges
        Prop("stall", 1, 1), Prop("stall", 2, 1), Prop("stall", 5, 1),
        Prop("stall", 6, 1), Prop("stall", 7, 1),
        Prop("stall", 1, 7), Prop("stall", 2, 7), Prop("stall", 5, 7),
        Prop("stall", 6, 7),
        # crates / barrels
        Prop("crate", 2, 5), Prop("crate", 5, 5),
        # warm lantern posts
        Prop("lantern_post", 4, 4, glow="hearth_amber"),
        Prop("lantern_post", 3, 6, glow="hearth_amber"),
        # ambient greenery + ground props
        Prop("mushroom", 1, 6), Prop("mushroom", 7, 6), Prop("mushroom", 0, 7),
        Prop("rock", 6, 6), Prop("rock", 0, 3),
        Prop("grass_tuft", 2, 6), Prop("grass_tuft", 5, 4), Prop("grass_tuft", 6, 5),
        Prop("grass_tuft", 1, 2), Prop("grass_tuft", 3, 7), Prop("grass_tuft", 8, 2),
        Prop("flower", 1, 5), Prop("flower", 7, 5), Prop("flower", 4, 6),
        Prop("flower", 3, 3), Prop("flower", 8, 6),
        # Bramble, the forge-smith (character, part of the art)
        Prop("bramble", 2, 3, interactable=True, glow="hearth_amber"),
    ]

    glows = [
        Glow(6.0, 3.0, "hearth_amber", 74, 120),   # forge hearth (warm, not blinding)
        Glow(6.0, 3.0, "honey_gold", 46, 80),       # forge inner glow
        Glow(4.0, 4.0, "hearth_amber", 60, 60),    # lantern post
        Glow(3.0, 6.0, "hearth_amber", 52, 52),    # lantern post
        Glow(2.0, 3.0, "hearth_amber", 42, 50),    # Bramble's forge-light
    ]

    fireflies = [(1.6, 2.4), (5.3, 1.8), (3.2, 3.1), (4.8, 4.6), (6.8, 4.2),
                 (2.4, 5.8), (7.2, 5.4), (3.6, 6.6)]

    return Room(grid, "Forge Market", "a warm forge under canvas", heights, path,
                props, glows, fireflies)





# --------------------------------------------------------------------------- #
# Mill Court (node 17): a wooden waterwheel at the hollow's edge -- the mill
# house, the mill-race Brook, the Crank Socket and the Water Spout. Matches node
# 2's Hollow Gate and node 16's Forge Market in palette + visual language.
# --------------------------------------------------------------------------- #
def build_room_mill():
    grid = 9
    # paved court + paths to the south (market) and east (greenhouse) portals
    court = {
        (3, 3), (4, 3), (5, 3), (6, 3),
        (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4),
        (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5),
        (3, 6), (4, 6), (5, 6),
        (4, 7), (5, 7),
    }
    mill_footing = {(6, 6), (7, 6), (6, 7), (7, 7)}   # raised stone footing
    path = court | mill_footing

    heights = {cell: 1 for cell in mill_footing}

    props = [
        # the waterwheel (NW) + its crank socket
        Prop("waterwheel", 2, 2),
        Prop("crank_socket", 2, 3, interactable=True),
        # mill-race channel (west edge; dry until water_flowing fills it)
        Prop("mill_race", 1, 5), Prop("mill_race", 1, 6),
        # the water spout (court)
        Prop("water_spout", 6, 3, interactable=True),
        # the mill house (SE, on a raised stone footing)
        Prop("mill_house", 7, 7, h=1),
        # stacked timber (NE)
        Prop("timber_stack", 6, 1), Prop("timber_stack", 7, 1),
        # warm lantern posts (west court, clear of the mill house)
        Prop("lantern_post", 3, 6, glow="hearth_amber"),
        Prop("lantern_post", 4, 7, glow="hearth_amber"),
        # ambient greenery + ground props (cozy ground-dressing, as gate/market)
        Prop("mushroom", 0, 7), Prop("mushroom", 8, 2), Prop("mushroom", 3, 7),
        Prop("rock", 8, 3), Prop("rock", 0, 3), Prop("rock", 5, 2),
        Prop("grass_tuft", 1, 4), Prop("grass_tuft", 3, 2), Prop("grass_tuft", 8, 5),
        Prop("grass_tuft", 0, 6), Prop("grass_tuft", 2, 7), Prop("grass_tuft", 8, 7),
        Prop("flower", 4, 2), Prop("flower", 5, 5), Prop("flower", 2, 6),
        Prop("flower", 3, 5), Prop("flower", 8, 1), Prop("flower", 7, 5),
        Prop("fence", 0, 2), Prop("fence", 0, 4),
    ]

    glows = [
        Glow(3.0, 6.0, "hearth_amber", 62, 82),   # lantern post
        Glow(4.0, 7.0, "hearth_amber", 54, 74),   # lantern post
        Glow(7.0, 6.0, "honey_gold", 44, 66),     # mill house windows (warm)
        Glow(6.0, 6.0, "honey_gold", 40, 60),     # mill house windows (warm)
    ]

    fireflies = [(3.1, 4.2), (5.3, 2.1), (4.6, 5.8), (7.4, 3.2), (2.4, 6.4),
                 (6.2, 4.6), (5.1, 7.2), (3.8, 2.6), (1.7, 7.1), (8.3, 2.6)]

    return Room(grid, "Mill Court", "a wooden waterwheel at the hollow's edge",
                heights, path, props, glows, fireflies)


# --------------------------------------------------------------------------- #
# Drawable list (pure, testable) + painter's sort
# --------------------------------------------------------------------------- #
def build_drawables(room, t, ox, oy):
    """Produce an unsorted list of (depth_key, kind, payload) drawables."""
    draw = []
    for gx in range(room.grid):
        for gy in range(room.grid):
            h = room.heights.get((gx, gy), 0)
            base = PALETTE["cream_parch"] if (gx, gy) in room.path else PALETTE["moss_green"]
            draw.append((depth_key(gx, gy, LAYER_TILE), "tile", (gx, gy, base, h)))

    for p in room.props:
        k = depth_key(p.gx, p.gy, LAYER_SHADOW)
        draw.append((k, "shadow", p))
        draw.append((depth_key(p.gx, p.gy, LAYER_PROP), "prop", p))
        if p.interactable:
            draw.append((depth_key(p.gx, p.gy, LAYER_GLOW), "halo", p))

    for g in room.glows:
        draw.append((depth_key(int(g.fx), int(g.fy), LAYER_GLOW), "glow", g))

    for i, anchor in enumerate(room.fireflies):
        fx, fy = anchor[0], anchor[1]
        phase = anchor[2] if len(anchor) >= 3 else (fx * 1.7 + fy * 3.1 + i)
        x, y = anim.firefly_drift(fx, fy, phase, t)
        draw.append((depth_key(int(x), int(y), LAYER_GLOW + 1.0), "firefly",
                     (x, y, anim.firefly_brightness(phase, t))))

    return draw


def depth_sorted(drawables):
    """Painter's algorithm: back-to-front = ascending depth key."""
    return sorted(drawables, key=lambda d: d[0])


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
_sky_cache = {}


def _cached_sky(w, h):
    if (w, h) not in _sky_cache:
        _sky_cache[(w, h)] = sky(w, h)
    return _sky_cache[(w, h)]


def render_room(surface, room, t, ox, oy):
    surface.blit(_cached_sky(surface.get_width(), surface.get_height()), (0, 0))
    draw = depth_sorted(build_drawables(room, t, ox, oy))

    for _, kind, payload in draw:
        if kind == "tile":
            gx, gy, base, h = payload
            draw_tile(surface, gx, gy, base, h, ox, oy)
        elif kind == "shadow":
            p = payload
            fx, fy = prop_anchor(p.gx, p.gy, p.h, ox, oy)
            sh = soft_shadow(74, 34)
            surface.blit(sh, (fx - 37, fy - 22))
        elif kind == "prop":
            p = payload
            fx, fy = prop_anchor(p.gx, p.gy, p.h, ox, oy)
            spr = get_sprite(p.kind, p.gx, p.gy)
            dy = 0
            if p.anim == "bob":
                dy = int(round(anim.idle_bob(t)))
            elif p.anim == "sway":
                fx += int(round(anim.sway(t, phase=0.3)))
            surface.blit(spr, (fx - spr.get_width() // 2, fy - spr.get_height() + 2 + dy))
        elif kind == "halo":
            p = payload
            fx, fy = prop_anchor(p.gx, p.gy, p.h, ox, oy)
            h = halo(46, PALETTE["firefly_glow"], 110)
            surface.blit(h, (fx - 46, fy - 60))
        elif kind == "glow":
            g = payload
            px, py = iso_f(g.fx, g.fy, ox, oy)
            f = anim.flicker(t, phase=g.fx * 1.3)
            peak = int(g.peak * f)
            surface.blit(radial_glow(g.radius, PALETTE[g.color], peak),
                         (px - g.radius, py - g.radius), special_flags=pygame.BLEND_RGB_ADD)
        elif kind == "firefly":
            x, y, bright = payload
            px, py = iso_f(x, y, ox, oy)
            r = 3 if bright > 0.75 else 2
            glow = radial_glow(9, PALETTE["firefly_glow"], int(70 * bright))
            surface.blit(glow, (int(px) - 9, int(py) - 9), special_flags=pygame.BLEND_RGB_ADD)
            pygame.draw.circle(surface, PALETTE["firefly_glow"], (int(px), int(py)), r)

    # cool Twilight-Violet vignette (multiply) -- never black
    surface.blit(vignette(surface.get_width(), surface.get_height(), (120, 108, 150), 0.5),
                 (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    return surface


# --------------------------------------------------------------------------- #
# Camera layout (single fixed camera, no rotation/zoom)
# --------------------------------------------------------------------------- #
def layout(room, w, h):
    """Center the room diamond horizontally; leave the lower band for the UI."""
    span_w = (room.grid - 1) * 2 * HW + TILE_W
    ox = (w - span_w) // 2 + (room.grid - 1) * HW
    oy = 200
    return ox, oy


# --------------------------------------------------------------------------- #
# Firefly Greenhouse (node 18): a glass greenhouse glowing with drifting
# fireflies -- the fourth art-complete room. Matches node 2's Hollow Gate, node
# 16's Forge Market, and node 17's Mill Court in palette + visual language.
# --------------------------------------------------------------------------- #
def build_room_greenhouse():
    grid = 9
    # stone floor inside the glass house + the west door (from the Mill Court)
    floor = {
        (0, 4), (1, 4),                                   # west door + approach
        (2, 2), (3, 2), (4, 2), (5, 2), (6, 2),
        (2, 3), (3, 3), (4, 3), (5, 3), (6, 3),
        (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4),
        (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5),
        (2, 6), (3, 6), (4, 6), (5, 6), (6, 6),
    }
    path = floor

    # the ember-seed bed sits on a raised (h=1) stone planter -> 2.5D extrusion
    heights = {(4, 3): 1}

    props = [
        # the glass house: back wall + pitched glass roof (north), east glass wall
        Prop("glass_house", 4, 1),
        Prop("glass_wall", 3, 1), Prop("glass_wall", 5, 1),
        Prop("glass_wall", 7, 2), Prop("glass_wall", 7, 3),
        # the room's two interactables (from world.json objects)
        Prop("mural", 2, 2, interactable=True, glow="honey_gold"),
        Prop("seed", 4, 3, h=1, interactable=True, glow="hearth_amber"),
        # raised plant beds (worldmap obstacles) around the walls
        Prop("plant_bed", 1, 1), Prop("plant_bed", 2, 1),
        Prop("plant_bed", 6, 1), Prop("plant_bed", 7, 1),
        Prop("plant_bed", 1, 6), Prop("plant_bed", 1, 7),
        Prop("plant_bed", 7, 6), Prop("plant_bed", 7, 7),
        # vines over the west door
        Prop("vine", 1, 4), Prop("vine", 1, 3),
        # cozy interior: terracotta pots + a bench
        Prop("pot", 3, 4), Prop("pot", 6, 5), Prop("pot", 5, 2),
        Prop("bench", 2, 6),
        # one warm lantern post (clear of the glass, cozy warm light)
        Prop("lantern_post", 6, 4, glow="hearth_amber"),
        # ambient greenery + ground dressing (as gate/market/mill)
        Prop("mushroom", 3, 6), Prop("mushroom", 5, 6), Prop("mushroom", 8, 2),
        Prop("rock", 8, 5), Prop("rock", 0, 2),
        Prop("grass_tuft", 3, 7), Prop("grass_tuft", 5, 7), Prop("grass_tuft", 8, 3),
        Prop("grass_tuft", 0, 5), Prop("grass_tuft", 6, 2),
        Prop("flower", 4, 2), Prop("flower", 2, 5), Prop("flower", 6, 6),
        Prop("flower", 1, 2),
    ]

    glows = [
        Glow(2.0, 2.0, "honey_gold", 46, 70),       # the mural's painted light
        Glow(6.0, 4.0, "hearth_amber", 56, 78),     # lantern post
        Glow(4.0, 4.0, "firefly_glow", 52, 64),     # firefly cluster (green-gold)
        Glow(3.0, 5.0, "firefly_glow", 44, 56),     # firefly cluster
        Glow(6.5, 2.5, "firefly_glow", 40, 50),     # firefly cluster (east)
    ]

    fireflies = [
        (1.9, 3.1), (2.6, 4.2), (3.4, 2.4), (4.3, 4.8), (5.2, 3.2),
        (6.1, 4.4), (3.1, 5.6), (4.8, 6.1), (5.9, 5.4), (2.4, 5.9),
        (6.4, 2.8), (4.6, 2.6), (3.8, 3.8), (5.4, 4.0), (6.9, 5.6),
    ]

    return Room(grid, "Firefly Greenhouse",
                "a glass greenhouse glowing with fireflies", heights, path,
                props, glows, fireflies)
