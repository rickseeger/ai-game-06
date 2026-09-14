"""Automated code-level verification (no vision tool).

Pixel-sampling invariants + isometric-geometry + painter's-algorithm draw-order,
all computed from the deterministic render. Every check is a plain boolean, so a
controller can rerun and diff the JSON.
"""

import math

import pygame

from .geometry import iso, HW, HH, ELEV, TILE_W, TILE_H, depth_key, \
    LAYER_TILE, LAYER_SHADOW, LAYER_PROP, LAYER_GLOW, grid_bounds
from .palette import PALETTE, darken, dE, is_warm, is_violet, is_foliage, nearest_swatch
from .scene import build_drawables, depth_sorted


def tile_center(gx, gy, ox, oy, h=0):
    tx, ty = iso(gx, gy, ox, oy)
    return tx + HW, ty + HH - h * ELEV


def _count_pixels(surface):
    w, h = surface.get_size()
    stats = {"warm": 0, "cool": 0, "foliage": 0, "glow": 0, "warm_glow": 0,
             "black": 0, "total": 0}
    uniq = set()
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b, *_ = surface.get_at((x, y))
            uniq.add((r, g, b))
            stats["total"] += 1
            if r >= g >= b and r - b >= 15:
                stats["warm"] += 1
            if b >= r + 5 and b > 50:
                stats["cool"] += 1
            if g > r and g > b and g > 55:
                stats["foliage"] += 1
            if g > 200 and g > r and 80 < b < 210:
                stats["glow"] += 1
            if r > 210 and 130 < g < 215 and b < 90:
                stats["warm_glow"] += 1
            if r < 8 and g < 8 and b < 8:
                stats["black"] += 1
    stats["unique_colors"] = len(uniq)
    return stats


def flat_fill_check(surface, gx, gy, ox, oy, name, h=0, tolerance=50):
    cx, cy = tile_center(gx, gy, ox, oy, h)
    c = surface.get_at((cx, cy))[:3]
    d = dE(c, PALETTE[name])
    return {"sample": name, "rgb": list(c), "dE": round(d, 1),
            "within_tolerance": d <= tolerance}


def geometry_checks(room, ox, oy):
    res = {}
    res["iso_slope_2_to_1"] = bool(iso(1, 0, ox, oy) == (iso(0, 0, ox, oy)[0] + 32,
                                                          iso(0, 0, ox, oy)[1] + 16))
    res["iso_diag_symmetric"] = bool(iso(0, 1, ox, oy) == (iso(0, 0, ox, oy)[0] - 32,
                                                          iso(0, 0, ox, oy)[1] + 16))
    x0, y0, x1, y1 = grid_bounds(room.grid, ox, oy)
    w = x1 - x0
    h = y1 - y0
    res["diamond_2_to_1"] = bool(abs(w - 2 * h) <= 1)
    res["diamond_bounds"] = [x0, y0, x1, y1]
    return res


def draw_order_checks(room, t, ox, oy):
    draw = build_drawables(room, t, ox, oy)
    ordered = depth_sorted(draw)

    # 1. monotonic in gx+gy for tiles (back-to-front)
    tiles = [(d[0], d[2]) for d in ordered if d[1] == "tile"]
    sums = [gx + gy for _, (gx, gy, _, _) in tiles]
    mono = all(a <= b for a, b in zip(sums, sums[1:]))

    # 2. every prop sorts strictly after the tile it stands on
    props_after_own_tile = True
    for key, kind, payload in ordered:
        if kind == "prop":
            gx, gy = payload.gx, payload.gy
            own_tile_key = depth_key(gx, gy, LAYER_TILE)
            if not (key > own_tile_key):
                props_after_own_tile = False

    # 3. a far prop (small gx+gy) draws before a near prop (large gx+gy)
    far = min((d for d in ordered if d[1] == "prop"),
              key=lambda d: (d[2].gx + d[2].gy))
    near = max((d for d in ordered if d[1] == "prop"),
               key=lambda d: (d[2].gx + d[2].gy))
    far_before_near = far[0] < near[0]

    # 4. player (near, foreground) draws after every background tile it overlaps
    player = next(d for d in ordered if d[1] == "prop" and d[2].kind == "player")
    bg_tiles_behind = all(d[0] < player[0] for d in ordered
                          if d[1] == "tile" and (d[2][0] + d[2][1]) < player[2].gx + player[2].gy)

    return {
        "tile_order_monotonic": mono,
        "props_after_own_tile": props_after_own_tile,
        "far_before_near": far_before_near,
        "player_over_background_tiles": bg_tiles_behind,
        "far_prop": far[2].kind, "near_prop": near[2].kind,
        "drawable_count": len(ordered),
    }


def ascii_map(surface):
    w, h = surface.get_size()
    cols, rows = 96, 46
    cw, ch = max(1, w // cols), max(1, h // rows)
    lines = []
    for r in range(rows):
        line = []
        for c in range(cols):
            x = min(w - 1, c * cw + cw // 2)
            y = min(h - 1, r * ch + ch // 2)
            rr, gg, bb, *_ = surface.get_at((x, y))
            if rr >= gg >= bb and rr - bb >= 15:
                line.append("W")        # warm lit surface
            elif gg > rr and gg > bb:
                line.append("g")        # green foliage
            elif bb >= rr + 5 and bb > 50:
                line.append("C")        # cool twilight ambient
            elif gg > 200 and gg > rr and bb < 210:
                line.append("F")        # firefly / glow
            else:
                line.append(".")
        lines.append("".join(line))
    return "\n".join(lines)


def feature_presence(surface, room, ox, oy):
    """Confirm characters + key props are actually drawn (palette hit in their box)."""
    from .sprites import get_sprite
    from .geometry import prop_anchor
    feats = {}
    for kind, gx, gy, name in [
        ("player", 4, 6, "honey_gold"),   # bright cloak
        ("mallow", 2, 3, "russet"),        # robe
        ("bell", 6, 3, "honey_gold"),      # bell body
        ("cottage", 1, 2, "pumpkin"),      # mushroom roof
        ("stair", 5, 1, "fern_deep"),      # mossy bank
    ]:
        p = next(pp for pp in room.props if pp.kind == kind and pp.gx == gx and pp.gy == gy)
        fx, fy = prop_anchor(gx, gy, p.h, ox, oy)
        spr = get_sprite(kind, gx, gy)
        x0, y0 = fx - spr.get_width() // 2, fy - spr.get_height() + 2
        target = PALETTE[name]
        hit = total = 0
        for py in range(max(0, y0), min(surface.get_height(), y0 + spr.get_height()), 2):
            for px in range(max(0, x0), min(surface.get_width(), x0 + spr.get_width()), 2):
                total += 1
                if dE(surface.get_at((px, py))[:3], target) <= 60:
                    hit += 1
        feats[f"{kind}@{gx},{gy}:{name}"] = {
            "hits": hit, "total": total,
            "frac": round(hit / max(1, total), 3),
            "present": hit > 20,
        }
    return feats


def ui_presence(surface):
    """Confirm the interface treatment (dialogue panel + inventory strip) renders."""
    w, h = surface.get_size()
    cream = dark = glow = 0
    for y in range(h - 250, h - 150, 2):        # dialogue panel band
        for x in range(0, w, 4):
            r, g, b = surface.get_at((x, y))[:3]
            if dE((r, g, b), PALETTE["cream_parch"]) <= 40:
                cream += 1
            if r < 120 and g < 90 and b < 80:
                dark += 1
    for y in range(h - 100, h - 34, 2):         # inventory strip band
        for x in range(0, w, 4):
            r, g, b = surface.get_at((x, y))[:3]
            if dE((r, g, b), PALETTE["firefly_glow"]) <= 50:
                glow += 1
    return {"dialogue_cream_px": cream, "dialogue_text_px": dark,
            "inventory_selected_glow_px": glow,
            "interface_present": cream > 60 and dark > 12 and glow > 4}
