#!/usr/bin/env python3
"""
G13 -- "Emberglow Hollow" isometric renderer spike.

A minimal, dependency-light proof of the chosen implementation approach for G13:

  * Language/framework : Python 3.14 + pygame-ce 2.5.x (SDL2), software compositing
  * Projection         : fixed 2:1 isometric (diamond tiles), no rotation / no zoom
  * Depth              : painter's-algorithm back-to-front sort with tile ELEVATION
                         (vertical extrusion) -> the "2.5D" read
  * Art                : procedural painterly tiles (per-pixel value/saturation jitter
                         driven by one shared, world-space, deterministic value noise)
  * Light              : warm lit surfaces vs a single cool Twilight-Violet ambient
                         (backdrop + vignette); additive Honey-Gold lantern glow and
                         Firefly-Glow accents -- never black

Everything is code-driven (no image assets) and deterministic given SEED, so the same
frame is reproducible and verifiable by code-level pixel sampling (no vision tool).

Usage:
  python3 isometric_spike.py                 # open a live window (Rick playtest)
  python3 isometric_spike.py --headless      # frame-dump PNG to evidence/
  python3 isometric_spike.py --check         # render + run pixel-sampling assertions
  python3 isometric_spike.py --size 1280x720
"""

import argparse
import json
import math
import os
import sys
from functools import lru_cache

# Force headless SDL before pygame import when requested.
if "--headless" in sys.argv or "--check" in sys.argv:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

# --------------------------------------------------------------------------- #
# Locked art direction: "Emberglow Hollow" (option B) named hex palette.
# --------------------------------------------------------------------------- #
PALETTE = {
    "hearth_amber":    (0xF5, 0xA6, 0x23),
    "honey_gold":      (0xF7, 0xC9, 0x48),
    "pumpkin":         (0xE8, 0x7A, 0x3E),
    "russet":          (0xC9, 0x6F, 0x4A),
    "moss_green":      (0x6B, 0x9E, 0x4A),
    "fern_deep":       (0x3F, 0x6F, 0x3A),
    "cream_parch":     (0xFB, 0xEF, 0xD8),
    "bark_brown":      (0x6B, 0x4A, 0x32),
    "firefly_glow":    (0xD9, 0xF2, 0x6A),
    "twilight_violet": (0x5B, 0x4A, 0x78),
}

# Fixed 2:1 isometric tile (world unit 64 px) and elevation step.
TILE_W, TILE_H = 64, 32
HW, HH = TILE_W // 2, TILE_H // 2
ELEV = 16          # screen px per unit of tile height ("2.5D" extrusion)
SEED = 20260914    # one shared seed -> consistent brush across the whole scene

# --------------------------------------------------------------------------- #
# Scene layout (world grid).
# --------------------------------------------------------------------------- #
GRID = 12                       # 0..GRID-1 in both axes
HEIGHTS = {(6, 4): 1, (3, 6): 1}          # raised tiles (the hilltop + a mound)
PATH = {(0, 11), (1, 11), (2, 10), (3, 10), (4, 9), (5, 9), (6, 9),
        (7, 8), (8, 8), (9, 7), (10, 7), (11, 6)}   # Cream-Parchment winding path
TREE_TILE = (6, 4)               # lantern-crown tree (interactable -> halo)
COTTAGE_TILE = (8, 8)
MUSHROOMS = [(2, 8), (10, 8)]

# Fireflies: deterministic world positions (scatter across the hollow).
FIREFLIES = [(2.3, 2.4), (3.8, 5.1), (1.6, 7.2), (5.2, 1.8), (8.4, 2.2),
             (9.7, 4.6), (10.3, 7.9), (4.4, 8.3), (2.9, 9.6), (7.1, 6.4),
             (6.6, 10.2), (0.9, 4.1), (10.8, 1.2), (5.8, 11.4), (11.2, 3.1)]


# --------------------------------------------------------------------------- #
# Small deterministic helpers.
# --------------------------------------------------------------------------- #
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


@lru_cache(maxsize=None)
def _hash(x, y):
    n = (x * 374761393 + y * 668265263 + SEED * 1440662683) % 4294967296
    n = (n * 2654435761 + 1013904223) % 4294967296
    return n / 4294967296.0


def _smooth(t):
    return t * t * (3 - 2 * t)


def value_noise(x, y):
    xi, yi = int(math.floor(x)), int(math.floor(y))
    xf, yf = x - xi, y - yi
    u, v = _smooth(xf), _smooth(yf)
    a = _hash(xi, yi)
    b = _hash(xi + 1, yi)
    c = _hash(xi, yi + 1)
    d = _hash(xi + 1, yi + 1)
    return (a * (1 - u) * (1 - v) + b * u * (1 - v) + c * (1 - u) * v + d * u * v) * 2 - 1


def fbm(x, y, octaves=2):
    total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        total += amp * value_noise(x * freq, y * freq)
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm   # in [-1, 1]


def rgb_to_hsv(r, g, b):
    r, g, b = r / 255, g / 255, b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d == 0:
        h = 0.0
    elif mx == r:
        h = 60 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60 * ((b - r) / d + 2)
    else:
        h = 60 * ((r - g) / d + 4)
    s = 0.0 if mx == 0 else d / mx
    return h, s, mx


def hsv_to_rgb(h, s, v):
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)


def painterly(base, n):
    """Apply +/-8% value, +/-6% saturation jitter (the painterly brush)."""
    h, s, v = rgb_to_hsv(*base)
    s = clamp(s * (1 + n * 0.06), 0.0, 1.0)
    v = clamp(v * (1 + n * 0.08), 0.0, 1.0)
    return hsv_to_rgb(h, s, v)


def darken(base, f):
    """Darken by value-multiply (the fixed light rule for side faces)."""
    h, s, v = rgb_to_hsv(*base)
    return hsv_to_rgb(h, s, clamp(v * f, 0.0, 1.0))


def iso(gx, gy, ox, oy):
    return int((gx - gy) * HW + ox), int((gx + gy) * HH + oy)


def diamond_edge(px, py):
    return abs(px - TILE_W / 2) / (TILE_W / 2) + abs(py - TILE_H / 2) / (TILE_H / 2)


# --------------------------------------------------------------------------- #
# Painterly tile top faces (world-space noise => seamless across the map).
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
            sx, sy = tx + px, ty + py
            a = (sx - ox) / HW            # = gx - gy (continuous)
            b = (sy - oy) / HH            # = gx + gy (continuous)
            wx = (a + b) / 2.0
            wy = (b - a) / 2.0
            n = fbm(wx * 0.55, wy * 0.55)
            r, g, b = painterly(base, n)
            alpha = 255
            if d > 0.93:   # soft 1px feather on the diamond edge
                alpha = int(255 * clamp((1.0 - d) / 0.07, 0.0, 1.0))
            surf.set_at((px, py), (r, g, b, alpha))
    _tile_cache[key] = surf
    return surf


def draw_tile(scene, gx, gy, base, h, ox, oy):
    tx, ty = iso(gx, gy, ox, oy)
    rise = h * ELEV
    # two visible side faces (front-right darker, front-left mid) for 2.5D
    if h > 0:
        pygame.draw.polygon(scene, darken(base, 0.68),
                            [(tx + 63, ty + 16), (tx + 32, ty + 31),
                             (tx + 32, ty + 31 - rise), (tx + 63, ty + 16 - rise)])
        pygame.draw.polygon(scene, darken(base, 0.82),
                            [(tx, ty + 16), (tx + 32, ty + 31),
                             (tx + 32, ty + 31 - rise), (tx, ty + 16 - rise)])
    scene.blit(tile_top(gx, gy, base, ox, oy), (tx, ty - rise))


# --------------------------------------------------------------------------- #
# Painterly "card" props (billboarded sprites, soft edges, warm rim light).
# --------------------------------------------------------------------------- #
def paint_disc(radius, base, seed_off, soft=0.55):
    size = radius * 2 + 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = radius + 1
    r2 = radius * radius
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            d2 = dx * dx + dy * dy
            if d2 > r2:
                continue
            d = math.sqrt(d2)
            n = fbm((cx + dx) * 0.10, (cy + dy) * 0.10) + seed_off * 0.13
            r, g, b = painterly(base, n)
            lift = max(0.0, 1.0 - (dx + dy) / (radius * 1.6)) * 0.18
            r = clamp(int(r * (1 + lift)), 0, 255)
            g = clamp(int(g * (1 + lift)), 0, 255)
            b = clamp(int(b * (1 + lift)), 0, 255)
            alpha = 255
            if d / radius > soft:
                alpha = int(255 * clamp((1.0 - d / radius) / (1.0 - soft), 0.0, 1.0))
            surf.set_at((cx + dx, cy + dy), (r, g, b, alpha))
    return surf


def build_tree():
    s = pygame.Surface((180, 190), pygame.SRCALPHA)
    s.blit(paint_disc(50, PALETTE["fern_deep"], 1), (40, 0))
    s.blit(paint_disc(50, PALETTE["moss_green"], 2), (40, 36))
    s.blit(paint_disc(44, PALETTE["moss_green"], 3), (46, 42))
    for lx, ly in [(72, 46), (100, 40), (112, 60), (84, 76), (104, 86)]:
        pygame.draw.circle(s, PALETTE["firefly_glow"], (lx, ly), 3)
    pygame.draw.rect(s, PALETTE["bark_brown"], (82, 150, 16, 40))
    pygame.draw.rect(s, darken(PALETTE["bark_brown"], 0.8), (90, 150, 8, 40))
    return s


def build_cottage():
    s = pygame.Surface((120, 130), pygame.SRCALPHA)
    pygame.draw.rect(s, PALETTE["cream_parch"], (24, 40, 72, 60))
    pygame.draw.rect(s, darken(PALETTE["cream_parch"], 0.85), (24, 84, 72, 16))
    pygame.draw.rect(s, PALETTE["hearth_amber"], (48, 60, 24, 22))
    pygame.draw.rect(s, PALETTE["honey_gold"], (52, 64, 16, 14))
    pygame.draw.polygon(s, PALETTE["pumpkin"], [(16, 44), (60, 8), (104, 44)])
    pygame.draw.polygon(s, darken(PALETTE["pumpkin"], 0.82), [(60, 8), (104, 44), (88, 44)])
    pygame.draw.rect(s, PALETTE["russet"], (82, 16, 12, 30))
    return s


def build_mushroom():
    s = pygame.Surface((64, 72), pygame.SRCALPHA)
    s.blit(paint_disc(26, PALETTE["pumpkin"], 4), (4, 0))
    pygame.draw.rect(s, PALETTE["cream_parch"], (26, 30, 14, 40))
    pygame.draw.circle(s, PALETTE["firefly_glow"], (22, 16), 2)
    pygame.draw.circle(s, PALETTE["firefly_glow"], (40, 22), 2)
    return s


def radial_glow(radius, color, peak):
    """Opaque surface with the color PRE-MULTIPLIED by a soft falloff, so it is
    correct under pygame's BLEND_RGB_ADD (which ignores source alpha)."""
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


def vignette(w, h, color, strength):
    """Opaque multiplicative gradient: white at center -> violet at edges."""
    small_w, small_h = 160, 90
    s = pygame.Surface((small_w, small_h))
    cx, cy = (small_w - 1) / 2, (small_h - 1) / 2
    maxd = math.hypot(cx, cy)
    for y in range(small_h):
        for x in range(small_w):
            t = (math.hypot(x - cx, y - cy) / maxd) ** 2
            r = 255 - (255 - color[0]) * strength * t
            g = 255 - (255 - color[1]) * strength * t
            b = 255 - (255 - color[2]) * strength * t
            s.set_at((x, y), (int(r), int(g), int(b)))
    return pygame.transform.smoothscale(s, (w, h))


def _prop_anchor(gx, gy, h, ox, oy):
    tx, ty = iso(gx, gy, ox, oy)
    return tx + HW, ty + HH - h * ELEV   # top-face center (where the prop sits)


# --------------------------------------------------------------------------- #
# Render.
# --------------------------------------------------------------------------- #
def render_scene(w, h, ox, oy):
    scene = pygame.Surface((w, h))
    # cool dusk ambient (Twilight Violet) behind the warm hollow
    scene.fill(PALETTE["twilight_violet"])

    drawables = []
    for gx in range(GRID):
        for gy in range(GRID):
            h = HEIGHTS.get((gx, gy), 0)
            base = PALETTE["cream_parch"] if (gx, gy) in PATH else PALETTE["moss_green"]
            drawables.append(((gx + gy), 0, "tile", (gx, gy, base, h)))
    drawables.append((TREE_TILE[0] + TREE_TILE[1], 1, "tree", HEIGHTS.get(TREE_TILE, 0)))
    drawables.append((COTTAGE_TILE[0] + COTTAGE_TILE[1], 1, "cottage", 0))
    for m in MUSHROOMS:
        drawables.append((m[0] + m[1], 1, "mushroom", m))
    drawables.sort(key=lambda d: (d[0], d[1]))

    for _, _, kind, payload in drawables:
        if kind == "tile":
            gx, gy, base, h = payload
            draw_tile(scene, gx, gy, base, h, ox, oy)
        elif kind == "tree":
            h = payload
            fx, fy = _prop_anchor(TREE_TILE[0], TREE_TILE[1], h, ox, oy)
            glow = radial_glow(46, PALETTE["firefly_glow"], 90)
            scene.blit(glow, (fx - 46, fy - 46), special_flags=pygame.BLEND_RGB_ADD)
            spr = build_tree()
            scene.blit(spr, (fx - spr.get_width() // 2, fy - spr.get_height() + 4))
        elif kind == "cottage":
            fx, fy = _prop_anchor(COTTAGE_TILE[0], COTTAGE_TILE[1], 0, ox, oy)
            spr = build_cottage()
            scene.blit(spr, (fx - spr.get_width() // 2, fy - spr.get_height() + 6))
            win = radial_glow(30, PALETTE["hearth_amber"], 120)
            scene.blit(win, (fx - 30, fy - 30), special_flags=pygame.BLEND_RGB_ADD)
        elif kind == "mushroom":
            gx, gy = payload
            fx, fy = _prop_anchor(gx, gy, 0, ox, oy)
            spr = build_mushroom()
            scene.blit(spr, (fx - spr.get_width() // 2, fy - spr.get_height() + 2))

    # warm Honey-Gold lantern glow over the hollow (additive)
    tx, ty = iso(TREE_TILE[0], TREE_TILE[1], ox, oy)
    lg = radial_glow(150, PALETTE["honey_gold"], 70)
    scene.blit(lg, (tx - 80, ty - 120), special_flags=pygame.BLEND_RGB_ADD)

    # fireflies (firefly-glow dots)
    for fx, fy in FIREFLIES:
        px, py = iso(fx, fy, ox, oy)
        pygame.draw.circle(scene, PALETTE["firefly_glow"], (px, py), 2)

    # cool Twilight-Violet vignette (multiply) -- never black
    scene.blit(vignette(w, h, (120, 108, 150), 0.55), (0, 0),
               special_flags=pygame.BLEND_RGB_MULT)
    return scene


# --------------------------------------------------------------------------- #
# Automated verification (code-level pixel sampling; no vision tool).
# --------------------------------------------------------------------------- #
def dE(c1, c2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))


def ascii_map(scene):
    w, h = scene.get_size()
    cols, rows = 80, 40
    cw, ch = max(1, w // cols), max(1, h // rows)
    lines = []
    for r in range(rows):
        line = []
        for c in range(cols):
            x = min(w - 1, c * cw + cw // 2)
            y = min(h - 1, r * ch + ch // 2)
            rr, gg, bb, *_ = scene.get_at((x, y))
            if rr >= gg >= bb and rr - bb >= 15:
                line.append("W")        # warm lit
            elif gg > rr and gg > bb:
                line.append("g")        # green foliage
            elif bb >= rr + 5 and bb > 50:
                line.append("C")        # cool twilight ambient
            else:
                line.append(".")
        lines.append("".join(line))
    return "\n".join(lines)


def check(scene, ox, oy):
    w, h = scene.get_size()
    results = {"size": [w, h]}

    pixels = []
    warm = cool = glow = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b, *_ = scene.get_at((x, y))
            if r >= g >= b and r - b >= 15:
                warm += 1
            if b >= r + 5 and b > 50:
                cool += 1
            if g > 200 and g > r and 80 < b < 200:
                glow += 1
            pixels.append((r, g, b))
    uniq = len(set(pixels))
    results["unique_colors"] = uniq
    results["warm_px"] = warm
    results["cool_shadow_px"] = cool
    results["glow_px"] = glow

    extended = list(PALETTE.values()) + [darken(c, 0.68) for c in PALETTE.values()] \
        + [darken(c, 0.82) for c in PALETTE.values()]
    near = sum(1 for p in pixels if min(dE(p, c) for c in extended) <= 50)
    results["palette_coverage_frac"] = round(near / len(pixels), 3)

    # deterministic geometry: a grass tile's top-face center is green
    gx, gy = 5, 2
    tx, ty = iso(gx, gy, ox, oy)
    r, g, b, *_ = scene.get_at((tx + HW, ty + HH))
    results["grass_top_rgb"] = [r, g, b]
    results["grass_is_green"] = bool(g > r and g > b)

    # deterministic geometry: raised tile shows a darker side face than top face
    gx, gy = 3, 6
    tx, ty = iso(gx, gy, ox, oy)
    top = scene.get_at((tx + HW, ty + HH - ELEV))[:3]
    side = scene.get_at((tx + 47, ty + 15))[:3]
    results["hill_top_rgb"] = list(top)
    results["hill_side_rgb"] = list(side)
    results["side_darker_than_top"] = bool(
        (top[0] + top[1] + top[2]) > (side[0] + side[1] + side[2]))

    checks = {
        "size_is_1280x720": (w, h) == (1280, 720),
        "not_blank": uniq > 40,
        "warm_light_present": warm > 400,
        "cool_shadow_present": cool > 500,
        "firefly_glow_present": glow > 15,
        "grass_is_green": results["grass_is_green"],
        "side_darker_than_top (2.5D)": results["side_darker_than_top"],
    }
    results["checks"] = checks
    results["ok"] = all(checks.values())
    return results


# --------------------------------------------------------------------------- #
# Main.
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true", help="frame-dump PNG, no window")
    ap.add_argument("--check", action="store_true", help="run pixel-sampling assertions")
    ap.add_argument("--size", default="1280x720", help="WxH")
    ap.add_argument("--out", default="evidence/emberglow_spike.png")
    args = ap.parse_args()

    w, h = (int(v) for v in args.size.split("x"))
    ox = (w - ((GRID - 1) * 2 * HW + TILE_W)) // 2 + (GRID - 1) * HW
    oy = 150

    pygame.init()
    scene = render_scene(w, h, ox, oy)

    if args.check:
        res = check(scene, ox, oy)
        os.makedirs("evidence", exist_ok=True)
        pygame.image.save(scene, args.out)
        with open("evidence/spike_check.json", "w") as f:
            json.dump(res, f, indent=2)
        amap = ascii_map(scene)
        with open("evidence/emberglow_spike.ascii.txt", "w") as f:
            f.write(amap + "\n")
        print(json.dumps(res, indent=2))
        print("----- structure map (W=warm g=green C=cool) -----")
        print(amap)
        pygame.quit()
        return 0 if res["ok"] else 1

    if args.headless:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        pygame.image.save(scene, args.out)
        print("frame written:", os.path.abspath(args.out))
        pygame.quit()
        return 0

    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption("Emberglow Hollow - isometric spike")
    screen.blit(scene, (0, 0))
    pygame.display.flip()
    clock = pygame.time.Clock()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False
        clock.tick(60)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
