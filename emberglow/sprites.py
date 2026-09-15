"""Procedural sprite builders for Emberglow Hollow.

All art is code-driven and deterministic. Floor tiles are painted per-pixel at 1x
with a continuous world-space brush (soft feathered diamond edges). Prop/character
"cards" are built at 2x and soft-scaled back to 1x so silhouettes have soft edges
(no 1px outlines, per the art direction). Lighting helpers (glow, halo, shadow,
sky, vignette) live here too.
"""

import math

import pygame

from .geometry import TILE_W, TILE_H, HW, HH, ELEV, diamond_edge, iso
from .noise import fbm
from .palette import PALETTE, darken, lighten, mix, painterly, clamp

SCALE = 2  # props are authored at 2x then soft-scaled
PROP_SCALE = 0.62  # world props authored large, then shrunk to fit 64px tiles


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def brush(base, wx, wy, scale=0.55):
    """Painterly color from the shared world-space noise field (continuous)."""
    return painterly(base, fbm(wx * scale, wy * scale))


def new_surf(w, h):
    """Create a 2x SRCALPHA surface (w,h given in 1x units)."""
    return pygame.Surface((w * SCALE, h * SCALE), pygame.SRCALPHA)


def finish(surf):
    """Soft-scale a 2x surface down (soft edges, no aliasing)."""
    w, h = surf.get_size()
    tw = max(1, int(round(w * PROP_SCALE / SCALE)))
    th = max(1, int(round(h * PROP_SCALE / SCALE)))
    return pygame.transform.smoothscale(surf, (tw, th))


def finish_icon(surf):
    """Soft-scale a 2x surface back to its authored 1x size (for item icons)."""
    w, h = surf.get_size()
    return pygame.transform.smoothscale(surf, (w // SCALE, h // SCALE))


def painterly_repaint(surf, rect, base, wx, wy, scale=0.55):
    """Repaint the opaque pixels of `rect` (1x units) with the painterly brush."""
    x0, y0, w, h = rect
    for py in range(y0 * SCALE, (y0 + h) * SCALE):
        for px in range(x0 * SCALE, (x0 + w) * SCALE):
            a = surf.get_at((px, py))[3]
            if a == 0:
                continue
            r, g, b = brush(base, wx + px / float(SCALE) / 64.0,
                            wy + py / float(SCALE) / 64.0, scale)
            surf.set_at((px, py), (r, g, b, a))


def rect(surf, color, r):
    """Filled rect at 2x (r in 1x units)."""
    x, y, w, h = r
    pygame.draw.rect(surf, (*color, 255), (x * SCALE, y * SCALE, w * SCALE, h * SCALE))


def ellipse(surf, color, r):
    x, y, w, h = r
    pygame.draw.ellipse(surf, (*color, 255), (x * SCALE, y * SCALE, w * SCALE, h * SCALE))


def circle(surf, color, cx, cy, rad):
    pygame.draw.circle(surf, (*color, 255), (cx * SCALE, cy * SCALE), rad * SCALE)


def polygon(surf, color, pts):
    pygame.draw.polygon(surf, (*color, 255), [(x * SCALE, y * SCALE) for x, y in pts])


# --------------------------------------------------------------------------- #
# Painterly floor tiles
# --------------------------------------------------------------------------- #
_tile_cache = {}


def tile_top(gx, gy, base, ox, oy):
    key = (gx, gy, base)
    if key in _tile_cache:
        return _tile_cache[key]
    tx, ty = iso(gx, gy, ox, oy)
    surf = pygame.Surface((TILE_W, TILE_H), pygame.SRCALPHA)
    for py in range(TILE_H):
        for px in range(TILE_W):
            d = diamond_edge(px, py)
            if d > 1.0:
                continue
            a = (tx + px - ox) / float(HW)      # = gx - gy (continuous)
            b = (ty + py - oy) / float(HH)      # = gx + gy (continuous)
            wx = (a + b) / 2.0
            wy = (b - a) / 2.0
            r, g, bl = brush(base, wx, wy)
            alpha = 255
            if d > 0.93:
                alpha = int(255 * clamp((1.0 - d) / 0.07))
            surf.set_at((px, py), (r, g, bl, alpha))
    _tile_cache[key] = surf
    return surf


def draw_tile(scene, gx, gy, base, h, ox, oy):
    tx, ty = iso(gx, gy, ox, oy)
    rise = h * ELEV
    if h > 0:  # two visible side faces -> the 2.5D extrusion (1x, on the scene)
        pygame.draw.polygon(scene, darken(base, 0.68),
                            [(tx + 63, ty + 16), (tx + 32, ty + 31),
                             (tx + 32, ty + 31 - rise), (tx + 63, ty + 16 - rise)])
        pygame.draw.polygon(scene, darken(base, 0.82),
                            [(tx, ty + 16), (tx + 32, ty + 31),
                             (tx + 32, ty + 31 - rise), (tx, ty + 16 - rise)])
    scene.blit(tile_top(gx, gy, base, ox, oy), (tx, ty - rise))


# --------------------------------------------------------------------------- #
# Lighting helpers
# --------------------------------------------------------------------------- #
def radial_glow(radius, color, peak):
    """Opaque surface, color PRE-MULTIPLIED by falloff -> correct under BLEND_RGB_ADD."""
    s = pygame.Surface((radius * 2, radius * 2))
    for dy in range(-radius, radius):
        for dx in range(-radius, radius):
            d = math.hypot(dx, dy)
            if d >= radius:
                continue
            f = peak * (1 - d / radius) ** 2 / 255.0
            s.set_at((radius + dx, radius + dy),
                     (int(color[0] * f), int(color[1] * f), int(color[2] * f)))
    return s


def halo(radius, color, alpha_peak=160):
    """Soft SRCALPHA annulus -- the Firefly-Glow halo on interactables."""
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for dy in range(-radius, radius):
        for dx in range(-radius, radius):
            d = math.hypot(dx, dy) / radius
            if d >= 1.0:
                continue
            a = alpha_peak * (1 - d) ** 2
            s.set_at((radius + dx, radius + dy),
                     (*color, int(clamp(a, 0, 255))))
    return s


def soft_shadow(w, h, color=(91, 74, 120), alpha_peak=70):
    """Soft violet ground shadow (SRCALPHA). Grounds props without black."""
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w / 2.0, h / 2.0
    for py in range(h):
        for px in range(w):
            d = math.hypot((px - cx) / (w / 2.0), (py - cy) / (h / 2.0))
            if d >= 1.0:
                continue
            a = alpha_peak * (1 - d) ** 2
            s.set_at((px, py), (*color, int(clamp(a, 0, 255))))
    return s


def sky(w, h):
    """Dusk backdrop: cool Twilight Violet above, warm Honey-Gold glow at the horizon."""
    s = pygame.Surface((w, h))
    top = darken(PALETTE["twilight_violet"], 0.5)
    mid = PALETTE["twilight_violet"]
    low = mix(PALETTE["twilight_violet"], PALETTE["honey_gold"], 0.4)
    horizon = int(h * 0.62)
    for y in range(h):
        if y < horizon:
            t = y / float(horizon)
            c = mix(top, mid, t)
        else:
            t = (y - horizon) / float(h - horizon)
            c = mix(mid, low, t)
        pygame.draw.line(s, c, (0, y), (w, y))
    # warm pool of lantern-light low in the hollow
    glow = radial_glow(int(h * 0.5), PALETTE["hearth_amber"], 46)
    s.blit(glow, (int(w * 0.5 - h * 0.5), int(h * 0.45)), special_flags=pygame.BLEND_RGB_ADD)
    return s


def vignette(w, h, color, strength):
    """Opaque multiplicative gradient: white center -> violet edges (never black)."""
    small_w, small_h = 160, 90
    s = pygame.Surface((small_w, small_h))
    cx, cy = (small_w - 1) / 2.0, (small_h - 1) / 2.0
    maxd = math.hypot(cx, cy)
    for y in range(small_h):
        for x in range(small_w):
            t = (math.hypot(x - cx, y - cy) / maxd) ** 2
            r = 255 - (255 - color[0]) * strength * t
            g = 255 - (255 - color[1]) * strength * t
            b = 255 - (255 - color[2]) * strength * t
            s.set_at((x, y), (int(r), int(g), int(b)))
    return pygame.transform.smoothscale(s, (w, h))


# --------------------------------------------------------------------------- #
# Props (gate room + reusable foundation pieces)
# --------------------------------------------------------------------------- #
def build_cottage(gx, gy):
    s = new_surf(150, 140)
    # mushroom-cap roof
    ellipse(s, PALETTE["pumpkin"], (16, 6, 118, 66))
    ellipse(s, darken(PALETTE["pumpkin"], 0.74), (6, 44, 138, 34))   # cap underside
    # roof spots (honey-gold)
    for cx, cy, r in [(46, 24, 6), (78, 16, 7), (106, 30, 6), (60, 42, 5), (92, 46, 5)]:
        circle(s, PALETTE["honey_gold"], cx, cy, r)
    # walls
    rect(s, PALETTE["cream_parch"], (40, 70, 70, 52))
    # soft violet shade at wall base (value contrast, no outline)
    rect(s, mix(PALETTE["cream_parch"], PALETTE["twilight_violet"], 0.22), (40, 110, 70, 12))
    # door + window + chimney
    rect(s, PALETTE["bark_brown"], (62, 88, 22, 34))
    rect(s, darken(PALETTE["bark_brown"], 0.85), (66, 92, 6, 6))
    rect(s, PALETTE["hearth_amber"], (90, 82, 16, 16))
    rect(s, PALETTE["honey_gold"], (93, 85, 10, 10))
    rect(s, PALETTE["russet"], (112, 12, 14, 34))
    rect(s, darken(PALETTE["russet"], 0.8), (109, 8, 20, 6))
    # warm rim light on the NW (top-left) edge
    polygon(s, lighten(PALETTE["cream_parch"], 0.18), [(40, 70), (52, 70), (40, 122), (40, 70)])
    painterly_repaint(s, (40, 70, 70, 52), PALETTE["cream_parch"], gx, gy)
    painterly_repaint(s, (16, 6, 118, 66), PALETTE["pumpkin"], gx, gy)
    return finish(s)


def build_bell(gx, gy):
    s = new_surf(110, 120)
    # wooden A-frame
    polygon(s, PALETTE["bark_brown"], [(14, 4), (96, 4), (78, 118), (66, 118)])
    polygon(s, darken(PALETTE["bark_brown"], 0.85), [(32, 4), (78, 4), (66, 118), (54, 118)])
    # bell (honey-gold, flared) + clapper
    polygon(s, PALETTE["honey_gold"], [(34, 10), (76, 10), (82, 52), (28, 52)])
    polygon(s, darken(PALETTE["honey_gold"], 0.8), [(28, 52), (82, 52), (74, 60), (36, 60)])
    circle(s, PALETTE["russet"], 55, 62, 5)
    # warm sheen
    polygon(s, lighten(PALETTE["honey_gold"], 0.2), [(34, 10), (46, 10), (40, 52), (28, 52)])
    painterly_repaint(s, (34, 10, 48, 42), PALETTE["honey_gold"], gx, gy)
    return finish(s)


def build_stair(gx, gy):
    s = new_surf(170, 100)
    # mossy raised bank
    ellipse(s, PALETTE["fern_deep"], (8, 20, 154, 76))
    # stone steps ascending (cream, receding)
    steps = [(30, 84, 110, 12), (26, 70, 110, 12), (22, 56, 110, 12), (18, 42, 110, 12)]
    for i, (x, y, w, h) in enumerate(steps):
        rect(s, PALETTE["cream_parch"], (x, y, w, h))
        rect(s, mix(PALETTE["cream_parch"], PALETTE["twilight_violet"], 0.28),
             (x, y + h - 3, w, 3))
    # moss clumps on the flanks
    for cx, cy, r in [(16, 60, 8), (14, 78, 9), (154, 62, 8), (152, 80, 9)]:
        circle(s, PALETTE["moss_green"], cx, cy, r)
    painterly_repaint(s, (8, 20, 154, 76), PALETTE["fern_deep"], gx, gy)
    painterly_repaint(s, (18, 42, 110, 54), PALETTE["cream_parch"], gx, gy)
    return finish(s)


def build_lantern_post(gx, gy):
    s = new_surf(56, 110)
    rect(s, PALETTE["bark_brown"], (24, 30, 8, 80))
    polygon(s, PALETTE["hearth_amber"], [(8, 22), (48, 22), (42, 42), (14, 42)])
    polygon(s, PALETTE["honey_gold"], [(16, 26), (40, 26), (36, 38), (20, 38)])
    rect(s, darken(PALETTE["bark_brown"], 0.85), (18, 6, 20, 4))
    return finish(s)


def build_mushroom(gx, gy):
    s = new_surf(52, 56)
    ellipse(s, PALETTE["pumpkin"], (4, 0, 44, 28))
    rect(s, PALETTE["cream_parch"], (20, 24, 12, 28))
    circle(s, PALETTE["firefly_glow"], 18, 12, 3)
    circle(s, PALETTE["firefly_glow"], 34, 16, 3)
    painterly_repaint(s, (4, 0, 44, 28), PALETTE["pumpkin"], gx, gy)
    return finish(s)


def build_rock(gx, gy):
    s = new_surf(56, 40)
    polygon(s, PALETTE["russet"], [(6, 32), (20, 8), (40, 10), (50, 32)])
    polygon(s, darken(PALETTE["russet"], 0.72), [(6, 32), (20, 8), (30, 18), (14, 32)])
    painterly_repaint(s, (6, 8, 44, 24), PALETTE["russet"], gx, gy)
    return finish(s)


def build_grass_tuft(gx, gy):
    s = new_surf(36, 28)
    for x, h in [(10, 18), (16, 24), (22, 16)]:
        polygon(s, PALETTE["moss_green"], [(x, 28), (x + 3, 28 - h), (x + 6, 28)])
    polygon(s, PALETTE["fern_deep"], [(16, 28), (19, 4), (22, 28)])
    return finish(s)


def build_flower(gx, gy):
    s = new_surf(24, 30)
    rect(s, PALETTE["moss_green"], (10, 14, 2, 16))
    circle(s, PALETTE["honey_gold"], 11, 8, 6)
    circle(s, PALETTE["hearth_amber"], 11, 8, 3)
    return finish(s)


def build_fence(gx, gy):
    s = new_surf(80, 48)
    for x in (6, 30, 54):
        rect(s, PALETTE["bark_brown"], (x, 8, 8, 38))
        rect(s, darken(PALETTE["bark_brown"], 0.8), (x + 4, 8, 4, 38))
    rect(s, PALETTE["russet"], (2, 16, 76, 6))
    rect(s, PALETTE["russet"], (2, 30, 76, 6))
    return finish(s)


# --------------------------------------------------------------------------- #
# Characters
# --------------------------------------------------------------------------- #
def build_mallow(gx, gy):
    s = new_surf(78, 96)
    # hooded robe (russet) + fern-deep hood
    polygon(s, PALETTE["fern_deep"], [(20, 6), (58, 6), (54, 44), (24, 44)])
    ellipse(s, PALETTE["russet"], (16, 34, 46, 58))
    # face
    circle(s, PALETTE["cream_parch"], 39, 30, 9)
    circle(s, darken(PALETTE["cream_parch"], 0.85), 36, 32, 2)   # eye
    # collar + held lantern
    polygon(s, PALETTE["cream_parch"], [(28, 46), (50, 46), (46, 56), (32, 56)])
    circle(s, PALETTE["hearth_amber"], 58, 62, 6)
    circle(s, PALETTE["honey_gold"], 58, 62, 3)
    # warm rim light NW
    polygon(s, lighten(PALETTE["russet"], 0.16), [(16, 34), (24, 34), (16, 92), (16, 34)])
    painterly_repaint(s, (16, 34, 46, 58), PALETTE["russet"], gx, gy)
    painterly_repaint(s, (20, 6, 38, 38), PALETTE["fern_deep"], gx, gy)
    return finish(s)


def build_player(gx, gy):
    s = new_surf(54, 74)
    # bright honey-gold cloak (young ember-keeper)
    ellipse(s, PALETTE["honey_gold"], (8, 28, 38, 44))
    # pumpkin cap + face + hearth-amber scarf
    ellipse(s, PALETTE["pumpkin"], (16, 4, 22, 18))
    circle(s, PALETTE["cream_parch"], 27, 28, 7)
    polygon(s, PALETTE["hearth_amber"], [(16, 40), (38, 40), (34, 48), (20, 48)])
    # warm rim light NW
    polygon(s, lighten(PALETTE["honey_gold"], 0.16), [(8, 28), (16, 28), (8, 72), (8, 28)])
    painterly_repaint(s, (8, 28, 38, 44), PALETTE["honey_gold"], gx, gy)
    return finish(s)


# --------------------------------------------------------------------------- #
# Item icons (inventory)
# --------------------------------------------------------------------------- #
def build_item_icon(item_id):
    s = new_surf(26, 26)
    if item_id == "crank_handle":
        rect(s, PALETTE["bark_brown"], (4, 14, 18, 5))
        rect(s, PALETTE["russet"], (14, 4, 6, 14))
        circle(s, PALETTE["honey_gold"], 6, 8, 4)
    elif item_id == "glass_flask":
        polygon(s, PALETTE["cream_parch"], [(9, 3), (17, 3), (20, 10), (17, 22), (9, 22), (6, 10)])
        rect(s, PALETTE["russet"], (11, 0, 4, 4))
    elif item_id == "full_flask":
        polygon(s, PALETTE["brook"], [(9, 3), (17, 3), (20, 10), (17, 22), (9, 22), (6, 10)])
        rect(s, PALETTE["russet"], (11, 0, 4, 4))
        polygon(s, lighten(PALETTE["brook"], 0.3), [(10, 6), (13, 6), (12, 14), (9, 14)])
    elif item_id == "ember_seed":
        ellipse(s, PALETTE["hearth_amber"], (8, 4, 10, 16))
        ellipse(s, PALETTE["honey_gold"], (10, 6, 6, 10))
        circle(s, PALETTE["firefly_glow"], 13, 22, 3)
    elif item_id == "lens":
        circle(s, PALETTE["honey_gold"], 13, 13, 9)
        circle(s, mix(PALETTE["honey_gold"], PALETTE["brook"], 0.4), 13, 13, 7)
        circle(s, PALETTE["cream_parch"], 10, 10, 2)
    else:
        circle(s, PALETTE["cream_parch"], 13, 13, 8)
    return finish_icon(s)


def build_marker(gx, gy):
    """Generic interactable marker (placeholder art for not-yet-art-complete rooms)."""
    s = new_surf(40, 52)
    # a glowing orb on a stone plinth, so any interactable object reads at a glance
    rect(s, PALETTE["bark_brown"], (14, 28, 12, 20))
    ellipse(s, PALETTE["firefly_glow"], (13, 6, 14, 20))
    circle(s, PALETTE["honey_gold"], 20, 14, 5)
    painterly_repaint(s, (14, 28, 12,20), PALETTE["bark_brown"], gx, gy)
    return finish(s)


# --------------------------------------------------------------------------- #
# Dispatch (cached by kind + world position so brush stays continuous)
# --------------------------------------------------------------------------- #
_sprite_cache = {}


def get_sprite(kind, gx=0, gy=0):
    key = (kind, gx, gy)
    if key not in _sprite_cache:
        builders = {
            "cottage": build_cottage, "bell": build_bell, "stair": build_stair,
            "lantern_post": build_lantern_post, "mushroom": build_mushroom,
            "rock": build_rock, "grass_tuft": build_grass_tuft,
            "flower": build_flower, "fence": build_fence,
            "mallow": build_mallow, "player": build_player,
            "marker": build_marker,
            "seed": build_seed, "seed_bed": build_seed_bed, "water": build_water,
            "forge_flash": build_forge_flash, "stair_light": build_stair_light,
        }
        _sprite_cache[key] = builders[kind](gx, gy)
    return _sprite_cache[key]


# --------------------------------------------------------------------------- #
# Node 5: world-beat props (ember seed alive/dim, flowing mill-water)
# --------------------------------------------------------------------------- #
def build_seed(gx, gy):
    """The ember-seed, alive and pulsing (before seed_taken)."""
    s = new_surf(34, 38)
    ellipse(s, PALETTE["hearth_amber"], (6, 10, 22, 24))
    ellipse(s, PALETTE["honey_gold"], (10, 14, 14, 16))
    ellipse(s, PALETTE["firefly_glow"], (12, 18, 10, 8))
    circle(s, PALETTE["firefly_glow"], 17, 32, 3)
    painterly_repaint(s, (6, 10, 22, 24), PALETTE["hearth_amber"], gx, gy)
    return finish(s)


def build_seed_bed(gx, gy):
    """The greenhouse seed-bed after the ember-seed is taken (dimmed)."""
    s = new_surf(44, 30)
    ellipse(s, darken(PALETTE["moss_green"], 0.7), (4, 6, 36, 20))
    ellipse(s, mix(PALETTE["bark_brown"], PALETTE["twilight_violet"], 0.4), (10, 12, 24, 12))
    painterly_repaint(s, (4, 6, 36, 20), darken(PALETTE["moss_green"], 0.7), gx, gy)
    return finish(s)


def build_water(gx, gy):
    """Flowing Brook water (cool accent) -- the mill-race / spout, once water_flowing."""
    s = new_surf(64, 32)
    ellipse(s, PALETTE["brook"], (6, 6, 52, 20))
    ellipse(s, lighten(PALETTE["brook"], 0.3), (14, 9, 36, 12))
    painterly_repaint(s, (6, 6, 52, 20), PALETTE["brook"], gx, gy)
    return finish(s)


def build_forge_flash(gx, gy):
    """A solid warm flash over the forge (lens_ready): opaque, pixel-samplable."""
    s = new_surf(56, 56)
    circle(s, PALETTE["hearth_amber"], 28, 28, 26)
    circle(s, PALETTE["honey_gold"], 28, 28, 17)
    circle(s, PALETTE["firefly_glow"], 28, 28, 9)
    return finish(s)


def build_stair_light(gx, gy):
    """A solid ribbon of warm light on the cleared Hill Stair (stair_open)."""
    s = new_surf(64, 40)
    ellipse(s, PALETTE["honey_gold"], (8, 8, 48, 24))
    ellipse(s, PALETTE["hearth_amber"], (16, 12, 32, 16))
    painterly_repaint(s, (8, 8, 48, 24), PALETTE["honey_gold"], gx, gy)
    return finish(s)
