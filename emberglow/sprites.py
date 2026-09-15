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



# --------------------------------------------------------------------------- #
# Forge Market props + the forge-smith (node 16)
# --------------------------------------------------------------------------- #
def build_forge(gx, gy):
    s = new_surf(150, 140)
    # chimney (russet brick) with a dark cap
    rect(s, PALETTE["russet"], (82, 10, 28, 42))
    rect(s, darken(PALETTE["russet"], 0.78), (79, 4, 34, 8))
    # main brick kiln body
    rect(s, PALETTE["russet"], (18, 42, 96, 82))
    for y in (56, 72, 88, 104):
        rect(s, darken(PALETTE["russet"], 0.82), (18, y, 96, 3))
    rect(s, mix(PALETTE["russet"], PALETTE["twilight_violet"], 0.22), (18, 110, 96, 14))
    # hearth mouth (dark opening + layered warm glow)
    polygon(s, PALETTE["bark_brown"], [(28, 72), (74, 72), (68, 112), (34, 112)])
    polygon(s, PALETTE["hearth_amber"], [(36, 80), (66, 80), (62, 106), (40, 106)])
    polygon(s, PALETTE["honey_gold"], [(42, 88), (60, 88), (58, 102), (44, 102)])
    circle(s, PALETTE["firefly_glow"], 51, 95, 6)
    # anvil (bark-brown) beside the body
    polygon(s, PALETTE["bark_brown"], [(108, 62), (140, 62), (144, 92), (124, 102), (104, 92)])
    rect(s, darken(PALETTE["bark_brown"], 0.8), (108, 62, 34, 6))
    # warm rim light NW
    polygon(s, lighten(PALETTE["russet"], 0.16), [(18, 42), (30, 42), (18, 124), (18, 42)])
    painterly_repaint(s, (18, 42, 96, 82), PALETTE["russet"], gx, gy)
    return finish(s)


def build_forge_kiln(gx, gy):
    s = new_surf(96, 70)
    rect(s, PALETTE["russet"], (8, 14, 80, 48))
    for y in (26, 38, 50):
        rect(s, darken(PALETTE["russet"], 0.82), (8, y, 80, 3))
    rect(s, mix(PALETTE["russet"], PALETTE["twilight_violet"], 0.22), (8, 50, 80, 12))
    # stacked firewood on top
    polygon(s, PALETTE["bark_brown"], [(50, 14), (84, 14), (84, 26), (50, 26)])
    polygon(s, lighten(PALETTE["russet"], 0.16), [(8, 14), (20, 14), (8, 62), (8, 14)])
    painterly_repaint(s, (8, 14, 80, 48), PALETTE["russet"], gx, gy)
    return finish(s)


def build_stall(gx, gy):
    s = new_surf(92, 78)
    # pumpkin canvas awning with a scalloped bottom edge
    ellipse(s, PALETTE["pumpkin"], (6, 4, 80, 34))
    for x in (14, 26, 38, 50, 62):
        circle(s, darken(PALETTE["pumpkin"], 0.8), x, 38, 6)
    for x in (22, 40, 58):
        rect(s, PALETTE["honey_gold"], (x, 6, 7, 32))
    # stall front (cream) + counter (russet) + side posts
    rect(s, PALETTE["cream_parch"], (16, 38, 60, 32))
    rect(s, PALETTE["russet"], (12, 42, 68, 8))
    rect(s, PALETTE["bark_brown"], (18, 30, 6, 40))
    rect(s, PALETTE["bark_brown"], (68, 30, 6, 40))
    # goods on the counter
    circle(s, PALETTE["pumpkin"], 30, 40, 5)
    circle(s, PALETTE["honey_gold"], 44, 38, 4)
    circle(s, PALETTE["moss_green"], 58, 40, 5)
    painterly_repaint(s, (6, 4, 80, 34), PALETTE["pumpkin"], gx, gy)
    painterly_repaint(s, (16, 38, 60, 32), PALETTE["cream_parch"], gx, gy)
    return finish(s)


def build_crate(gx, gy):
    s = new_surf(48, 44)
    rect(s, PALETTE["russet"], (6, 12, 36, 26))
    rect(s, darken(PALETTE["russet"], 0.75), (6, 20, 36, 2))
    rect(s, darken(PALETTE["russet"], 0.75), (6, 28, 36, 2))
    polygon(s, PALETTE["bark_brown"], [(6, 12), (18, 12), (6, 38), (6, 12)])
    polygon(s, PALETTE["bark_brown"], [(42, 12), (30, 12), (42, 38), (42, 12)])
    circle(s, PALETTE["pumpkin"], 24, 8, 6)
    circle(s, PALETTE["honey_gold"], 36, 6, 4)
    painterly_repaint(s, (6, 12, 36, 26), PALETTE["russet"], gx, gy)
    return finish(s)


def build_bramble(gx, gy):
    s = new_surf(82, 98)
    # stocky smith: fern shirt + russet apron
    ellipse(s, PALETTE["fern_deep"], (20, 28, 42, 62))
    polygon(s, PALETTE["russet"], [(24, 46), (58, 46), (54, 92), (28, 92)])
    # head + beard + eye + pumpkin bandana
    circle(s, PALETTE["cream_parch"], 41, 22, 10)
    polygon(s, PALETTE["bark_brown"], [(31, 28), (51, 28), (47, 44), (35, 44)])
    circle(s, darken(PALETTE["cream_parch"], 0.85), 37, 24, 2)
    rect(s, PALETTE["pumpkin"], (30, 12, 22, 6))
    # hammer (bark handle + russet head)
    rect(s, PALETTE["bark_brown"], (58, 40, 5, 32))
    rect(s, PALETTE["russet"], (50, 36, 20, 9))
    # warm rim light NW
    polygon(s, lighten(PALETTE["russet"], 0.16), [(24, 46), (32, 46), (24, 92), (24, 46)])
    painterly_repaint(s, (24, 46, 34, 46), PALETTE["russet"], gx, gy)
    painterly_repaint(s, (20, 28, 42, 62), PALETTE["fern_deep"], gx, gy)
    return finish(s)


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
            "forge": build_forge, "forge_kiln": build_forge_kiln,
            "stall": build_stall, "crate": build_crate, "bramble": build_bramble,
            "marker": build_marker,
            "waterwheel": build_waterwheel, "mill_house": build_mill_house,
            "timber_stack": build_timber_stack, "mill_race": build_mill_race,
            "crank_socket": build_crank_socket, "water_spout": build_water_spout,
            "spout_flow": build_spout_flow,
            "seed": build_seed, "seed_bed": build_seed_bed, "water": build_water,
            "forge_flash": build_forge_flash, "stair_light": build_stair_light,
            "glass_house": build_glass_house, "glass_wall": build_glass_wall,
            "plant_bed": build_plant_bed, "mural": build_mural,
            "vine": build_vine, "pot": build_pot, "bench": build_bench,
        }
        _sprite_cache[key] = builders[kind](gx, gy)
    return _sprite_cache[key]



# --------------------------------------------------------------------------- #
# Mill Court props (node 17): waterwheel, mill house, timber, mill-race,
# crank socket, water spout -- the third art-complete room, to node 2's standard.
# --------------------------------------------------------------------------- #
def build_waterwheel(gx, gy):
    s = new_surf(150, 150)
    cx, cy, r = 75, 75, 56
    # outer rim (russet) + inner rim (bark) as rings (SRCALPHA: grass shows through)
    pygame.draw.circle(s, (*PALETTE["russet"], 255),
                       (cx * SCALE, cy * SCALE), r * SCALE, width=11 * SCALE)
    pygame.draw.circle(s, (*PALETTE["bark_brown"], 255),
                       (cx * SCALE, cy * SCALE), (r - 9) * SCALE, width=5 * SCALE)
    # spokes
    for i in range(8):
        ang = i * math.pi / 4.0
        x2 = cx + int(round(math.cos(ang) * (r - 8)))
        y2 = cy + int(round(math.sin(ang) * (r - 8)))
        pygame.draw.line(s, (*PALETTE["bark_brown"], 255),
                         (cx * SCALE, cy * SCALE), (x2 * SCALE, y2 * SCALE), 4 * SCALE)
    # rim paddles (russet nubs)
    for i in range(12):
        ang = i * math.pi / 6.0
        px = cx + int(round(math.cos(ang) * r))
        py = cy + int(round(math.sin(ang) * r))
        circle(s, PALETTE["russet"], px, py, 5)
    # hub + axle
    circle(s, PALETTE["bark_brown"], cx, cy, 13)
    circle(s, PALETTE["russet"], cx, cy, 7)
    circle(s, PALETTE["honey_gold"], cx, cy, 3)
    return finish(s)


def build_mill_house(gx, gy):
    s = new_surf(110, 110)
    # pitched russet roof
    polygon(s, PALETTE["russet"], [(14, 40), (55, 8), (96, 40)])
    polygon(s, darken(PALETTE["russet"], 0.8), [(14, 40), (55, 8), (55, 40)])
    rect(s, darken(PALETTE["russet"], 0.82), (52, 4, 8, 5))   # ridge cap
    # bark-brown plank facade
    rect(s, PALETTE["bark_brown"], (22, 40, 66, 62))
    for y in (52, 64, 76, 88):
        rect(s, darken(PALETTE["bark_brown"], 0.8), (22, y, 66, 2))
    # door + warm windows
    rect(s, PALETTE["cream_parch"], (44, 72, 18, 30))
    rect(s, darken(PALETTE["bark_brown"], 0.85), (47, 76, 6, 6))
    rect(s, PALETTE["hearth_amber"], (66, 48, 14, 12))
    rect(s, PALETTE["honey_gold"], (68, 50, 10, 8))
    rect(s, PALETTE["hearth_amber"], (28, 48, 14, 12))
    rect(s, PALETTE["honey_gold"], (30, 50, 10, 8))
    # mill chute (russet) on the east side
    rect(s, PALETTE["russet"], (84, 34, 10, 36))
    rect(s, darken(PALETTE["russet"], 0.8), (87, 34, 3, 36))
    # warm rim light NW
    polygon(s, lighten(PALETTE["bark_brown"], 0.14),
            [(22, 40), (30, 40), (22, 102), (22, 40)])
    painterly_repaint(s, (22, 40, 66, 62), PALETTE["bark_brown"], gx, gy)
    painterly_repaint(s, (14, 8, 82, 34), PALETTE["russet"], gx, gy)
    return finish(s)


def build_timber_stack(gx, gy):
    s = new_surf(60, 54)
    for i in range(3):
        y = 12 + i * 14
        rect(s, PALETTE["bark_brown"], (8, y, 44, 10))
        ellipse(s, PALETTE["russet"], (46, y, 12, 10))
        rect(s, darken(PALETTE["bark_brown"], 0.78), (8, y + 7, 44, 3))
    painterly_repaint(s, (8, 12, 44, 40), PALETTE["bark_brown"], gx, gy)
    return finish(s)


def build_mill_race(gx, gy):
    s = new_surf(64, 32)
    # stone-lined channel (russet) with a dry mossy bed (Brook water fills it later)
    ellipse(s, PALETTE["russet"], (4, 4, 56, 24))
    ellipse(s, mix(PALETTE["cream_parch"], PALETTE["twilight_violet"], 0.12), (11, 8, 42, 16))
    ellipse(s, mix(PALETTE["moss_green"], PALETTE["bark_brown"], 0.35), (18, 12, 28, 8))
    painterly_repaint(s, (4, 4, 56, 24), PALETTE["russet"], gx, gy)
    return finish(s)


def build_crank_socket(gx, gy):
    s = new_surf(56, 60)
    # wooden housing post
    rect(s, PALETTE["bark_brown"], (12, 32, 32, 24))
    rect(s, darken(PALETTE["bark_brown"], 0.82), (12, 50, 32, 6))
    # russet metal collar + side bracket
    rect(s, PALETTE["russet"], (16, 22, 24, 12))
    polygon(s, PALETTE["russet"], [(40, 30), (52, 30), (52, 40), (40, 40)])
    # honey-gold socket mouth (where the crank handle inserts)
    circle(s, PALETTE["honey_gold"], 28, 22, 7)
    circle(s, darken(PALETTE["honey_gold"], 0.7), 28, 22, 3)
    painterly_repaint(s, (12, 32, 32, 24), PALETTE["bark_brown"], gx, gy)
    return finish(s)


def build_water_spout(gx, gy):
    s = new_surf(56, 64)
    # wooden trough
    rect(s, PALETTE["bark_brown"], (6, 36, 44, 16))
    rect(s, darken(PALETTE["bark_brown"], 0.82), (6, 36, 44, 3))
    # russet spout pipe
    polygon(s, PALETTE["russet"], [(14, 16), (42, 16), (46, 36), (10, 36)])
    rect(s, PALETTE["bark_brown"], (10, 32, 36, 5))   # spout mouth
    # mount post
    rect(s, PALETTE["bark_brown"], (22, 6, 12, 14))
    painterly_repaint(s, (6, 36, 44, 16), PALETTE["bark_brown"], gx, gy)
    painterly_repaint(s, (14, 16, 32, 20), PALETTE["russet"], gx, gy)
    return finish(s)


def build_spout_flow(gx, gy):
    s = new_surf(40, 44)
    # Brook water pouring from the spout into a small pool
    ellipse(s, PALETTE["brook"], (14, 2, 12, 26))
    ellipse(s, PALETTE["brook"], (4, 24, 32, 16))
    ellipse(s, lighten(PALETTE["brook"], 0.3), (16, 6, 8, 16))
    painterly_repaint(s, (4, 2, 32, 38), PALETTE["brook"], gx, gy)
    return finish(s)


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
    """A solid warm flash over the forge (lens_ready): opaque, pixel-samplable.

    Large and gold-dominant so the burst spills warm light past the forge's own
    always-on hearth glow and is unambiguously brighter (the lens_ready beat).
    """
    s = new_surf(96, 96)
    circle(s, PALETTE["hearth_amber"], 48, 48, 46)
    circle(s, PALETTE["honey_gold"], 48, 48, 34)
    circle(s, PALETTE["firefly_glow"], 48, 48, 12)
    return finish(s)


def build_stair_light(gx, gy):
    """A solid ribbon of warm light on the cleared Hill Stair (stair_open)."""
    s = new_surf(64, 40)
    ellipse(s, PALETTE["honey_gold"], (8, 8, 48, 24))
    ellipse(s, PALETTE["hearth_amber"], (16, 12, 32, 16))
    painterly_repaint(s, (8, 8, 48, 24), PALETTE["honey_gold"], gx, gy)
    return finish(s)


# --------------------------------------------------------------------------- #
# Firefly Greenhouse props (node 18): glass walls + glass house, plant beds,
# the painted mural, vines over the door, terracotta pots, a bench.
# --------------------------------------------------------------------------- #
def build_glass_wall(gx, gy):
    s = new_surf(84, 96)
    # opaque frame (painterly) first so the brush touches only the wood
    rect(s, PALETTE["bark_brown"], (4, 4, 76, 88))       # outer border
    rect(s, PALETTE["bark_brown"], (40, 4, 6, 88))       # vertical mullion
    rect(s, PALETTE["bark_brown"], (4, 46, 76, 6))       # horizontal rail
    painterly_repaint(s, (4, 4, 76, 88), PALETTE["bark_brown"], gx, gy)
    # translucent cream-parchment glass panes (the scene shows through)
    for px, py in ((9, 9), (49, 9), (9, 55), (49, 55)):
        pygame.draw.rect(s, (*PALETTE["cream_parch"], 150),
                         (px * SCALE, py * SCALE, 26 * SCALE, 28 * SCALE))
    # cool violet sheen streak (glass reflection) + fireflies drifting inside
    pygame.draw.polygon(s, (*PALETTE["twilight_violet"], 90),
                        [(10 * SCALE, 10 * SCALE), (30 * SCALE, 10 * SCALE),
                         (10 * SCALE, 44 * SCALE)])
    circle(s, PALETTE["firefly_glow"], 60, 70, 5)
    circle(s, PALETTE["firefly_glow"], 20, 60, 4)
    return finish(s)


def build_glass_house(gx, gy):
    s = new_surf(160, 150)
    # pitched translucent glass roof (cream-parchment, scene shows through)
    pygame.draw.polygon(s, (*PALETTE["cream_parch"], 150),
                        [(8 * SCALE, 44 * SCALE), (80 * SCALE, 6 * SCALE),
                         (152 * SCALE, 44 * SCALE)])
    # roof ridge + eave frame (bark)
    pygame.draw.polygon(s, (*PALETTE["bark_brown"], 255),
                        [(80 * SCALE, 6 * SCALE), (86 * SCALE, 8 * SCALE),
                         (80 * SCALE, 12 * SCALE)])
    rect(s, PALETTE["bark_brown"], (6, 40, 148, 6))     # eave line
    # translucent glass wall band below the roof
    for cx in (14, 46, 78, 110):
        for cy in (52, 84):
            pygame.draw.rect(s, (*PALETTE["cream_parch"], 150),
                             (cx * SCALE, cy * SCALE, 26 * SCALE, 28 * SCALE))
    # wall frame (bark) mullions + rails (opaque, over the panes)
    for x in (14, 46, 78, 110):
        rect(s, PALETTE["bark_brown"], (x - 4, 52, 5, 60))
    rect(s, PALETTE["bark_brown"], (8, 48, 144, 6))     # top wall rail
    rect(s, PALETTE["bark_brown"], (8, 112, 144, 6))    # bottom wall rail
    # stone foundation sill (painterly)
    rect(s, PALETTE["bark_brown"], (6, 118, 148, 16))
    painterly_repaint(s, (6, 118, 148, 16), PALETTE["bark_brown"], gx, gy)
    # cool sheen on the roof + firefly glow inside the glass
    pygame.draw.polygon(s, (*PALETTE["twilight_violet"], 85),
                        [(20 * SCALE, 42 * SCALE), (60 * SCALE, 20 * SCALE),
                         (20 * SCALE, 20 * SCALE)])
    circle(s, PALETTE["firefly_glow"], 40, 90, 5)
    circle(s, PALETTE["firefly_glow"], 96, 76, 5)
    circle(s, PALETTE["firefly_glow"], 120, 92, 4)
    return finish(s)


def build_plant_bed(gx, gy):
    s = new_surf(72, 40)
    # raised wooden planter box (bark) with a soft violet shade
    rect(s, PALETTE["bark_brown"], (6, 14, 60, 22))
    rect(s, darken(PALETTE["bark_brown"], 0.8), (6, 14, 60, 4))
    rect(s, mix(PALETTE["bark_brown"], PALETTE["twilight_violet"], 0.25), (10, 20, 52, 12))
    painterly_repaint(s, (6, 14, 60, 22), PALETTE["bark_brown"], gx, gy)
    # dark warm soil mound + moss/fern sprouts
    ellipse(s, mix(PALETTE["bark_brown"], PALETTE["russet"], 0.5), (14, 8, 44, 12))
    ellipse(s, PALETTE["moss_green"], (10, 2, 26, 14))
    ellipse(s, PALETTE["fern_deep"], (34, 0, 26, 14))
    ellipse(s, PALETTE["moss_green"], (52, 4, 14, 10))
    circle(s, PALETTE["firefly_glow"], 26, 8, 3)
    return finish(s)


def build_mural(gx, gy):
    s = new_surf(96, 88)
    # stone wall backing (cream) + soft violet shade
    rect(s, PALETTE["cream_parch"], (6, 4, 84, 80))
    rect(s, mix(PALETTE["cream_parch"], PALETTE["twilight_violet"], 0.18), (6, 68, 84, 16))
    painterly_repaint(s, (6, 4, 84, 80), PALETTE["cream_parch"], gx, gy)
    # the painted founding story: light, water, and a growing seed
    circle(s, PALETTE["hearth_amber"], 28, 22, 12)       # the heart-lantern light
    circle(s, PALETTE["honey_gold"], 28, 22, 7)
    pygame.draw.polygon(s, (*PALETTE["brook"], 255),      # a stream of water
                        [(52 * SCALE, 12 * SCALE), (72 * SCALE, 12 * SCALE),
                         (64 * SCALE, 40 * SCALE), (58 * SCALE, 40 * SCALE)])
    ellipse(s, PALETTE["fern_deep"], (58, 44, 14, 22))     # a growing seed
    ellipse(s, PALETTE["moss_green"], (62, 46, 8, 14))
    # two painted keepers (bark + cream)
    rect(s, PALETTE["bark_brown"], (20, 56, 6, 14))
    circle(s, PALETTE["cream_parch"], 23, 52, 5)
    rect(s, PALETTE["bark_brown"], (74, 56, 6, 14))
    circle(s, PALETTE["cream_parch"], 77, 52, 5)
    # firefly-glow sparkles in the painting
    circle(s, PALETTE["firefly_glow"], 34, 40, 3)
    circle(s, PALETTE["firefly_glow"], 60, 62, 3)
    return finish(s)


def build_vine(gx, gy):
    s = new_surf(60, 64)
    # trailing vine strands (fern) over the door
    for x, h, w in [(12, 56, 6), (24, 62, 6), (36, 52, 6), (46, 58, 6)]:
        rect(s, PALETTE["fern_deep"], (x, 4, w, h))
    # leaf clusters
    ellipse(s, PALETTE["moss_green"], (6, 6, 20, 14))
    ellipse(s, PALETTE["moss_green"], (32, 2, 20, 14))
    ellipse(s, PALETTE["fern_deep"], (18, 28, 22, 14))
    ellipse(s, PALETTE["moss_green"], (40, 30, 16, 12))
    # a firefly perched in the vines
    circle(s, PALETTE["firefly_glow"], 30, 40, 4)
    return finish(s)


def build_pot(gx, gy):
    s = new_surf(40, 44)
    # terracotta pot (russet) + rim
    polygon(s, PALETTE["russet"], [(8, 16), (32, 16), (28, 42), (12, 42)])
    rect(s, darken(PALETTE["russet"], 0.8), (6, 12, 28, 6))
    # a mossy plant sprouting
    ellipse(s, PALETTE["moss_green"], (12, 2, 16, 12))
    ellipse(s, PALETTE["fern_deep"], (20, 0, 12, 10))
    circle(s, PALETTE["firefly_glow"], 20, 6, 2)
    painterly_repaint(s, (8, 12, 24, 30), PALETTE["russet"], gx, gy)
    return finish(s)


def build_bench(gx, gy):
    s = new_surf(64, 44)
    # seat + back + legs (bark) with russet slat accents
    rect(s, PALETTE["bark_brown"], (6, 18, 52, 8))
    rect(s, PALETTE["bark_brown"], (6, 6, 8, 28))
    rect(s, PALETTE["bark_brown"], (50, 6, 8, 28))
    rect(s, darken(PALETTE["bark_brown"], 0.82), (6, 24, 52, 2))
    rect(s, PALETTE["russet"], (8, 8, 4, 22))
    rect(s, PALETTE["russet"], (52, 8, 4, 22))
    painterly_repaint(s, (6, 6, 52, 24), PALETTE["bark_brown"], gx, gy)
    return finish(s)
