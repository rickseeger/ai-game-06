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


# --------------------------------------------------------------------------- #
# Node 5: success-vs-failure feedback + world-reactivity beat pixel checks
# --------------------------------------------------------------------------- #
def _is_water(c):
    """Brook (cool accent) water: cyan/blue, clearly distinct from violet ambient."""
    r, g, b = c
    return b > r + 20 and g > 100 and b > 120


def _is_gold(c):
    """Bright warm gold / amber (honey_gold / hearth_amber flash)."""
    r, g, b = c
    return r > 200 and 120 < g < 220 and b < 110


def _is_russet(c):
    return dE(c, PALETTE["russet"]) <= 45


def _is_warm_amber(c):
    return dE(c, PALETTE["hearth_amber"]) <= 50


def _is_firefly(c):
    r, g, b = c
    return g > 200 and g > r and 80 < b < 210


def _surface_count(surface, fn):
    w, h = surface.get_size()
    n = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if fn(surface.get_at((x, y))[:3]):
                n += 1
    return n


def _region_count(surface, cx, cy, r, fn):
    n = 0
    for y in range(max(0, cy - r), min(surface.get_height(), cy + r), 2):
        for x in range(max(0, cx - r), min(surface.get_width(), cx + r), 2):
            if fn(surface.get_at((x, y))[:3]):
                n += 1
    return n


def _scene_surface(rid, flags):
    """Render one room under `flags`, headlessly; return (surface, ox, oy)."""
    from . import worldreact
    from .world import World
    from .scene import layout, render_room
    w = World()
    room = worldreact.build_scene_room(w, rid, frozenset(flags))
    ox, oy = layout(room, 1280, 720)
    surf = pygame.Surface((1280, 720))
    render_room(surf, room, 0.0, ox, oy)
    return surf, ox, oy


def world_beat_checks():
    """Pixel-sampling proof that each world-reactivity beat changes the render."""
    from .ui import tile_top_center
    beats = {}

    # 1. water_flowing -> Brook water appears in the mill (was dry)
    before, _, _ = _scene_surface("mill", [])
    after, ox, oy = _scene_surface("mill", ["water_flowing"])
    beats["water_flowing"] = {
        "water_px_before": _surface_count(before, _is_water),
        "water_px_after": _surface_count(after, _is_water),
        "changed": _surface_count(after, _is_water) > _surface_count(before, _is_water) + 10,
    }

    # 2. lens_ready -> the forge flashes bright warm gold
    before, _, _ = _scene_surface("market", [])
    after, ox2, oy2 = _scene_surface("market", ["lens_ready"])
    beats["lens_ready"] = {
        "gold_px_before": _surface_count(before, _is_gold),
        "gold_px_after": _surface_count(after, _is_gold),
        "changed": _surface_count(after, _is_gold) > _surface_count(before, _is_gold) + 30,
    }

    # 3. seed_taken -> the greenhouse seed-bed dims (warm spark -> cool/dim)
    before, ox3, oy3 = _scene_surface("greenhouse", ["water_flowing"])
    after, _, _ = _scene_surface("greenhouse", ["water_flowing", "seed_taken"])
    cx, cy = tile_top_center(4, 3, ox3, oy3)
    beats["seed_taken"] = {
        "warm_px_before": _region_count(before, cx, cy, 30, _is_warm_amber),
        "warm_px_after": _region_count(after, cx, cy, 30, _is_warm_amber),
        "changed": _region_count(after, cx, cy, 30, _is_warm_amber)
                   < _region_count(before, cx, cy, 30, _is_warm_amber),
    }

    # 4. stair_open -> a ribbon of warm light on the cleared Hill Stair
    before, ox4, oy4 = _scene_surface("gate", [])
    after, _, _ = _scene_surface("gate", ["stair_open"])
    cx, cy = tile_top_center(5, 1, ox4, oy4)
    beats["stair_open"] = {
        "gold_px_before": _region_count(before, cx, cy, 34, _is_gold),
        "gold_px_after": _region_count(after, cx, cy, 34, _is_gold),
        "changed": _region_count(after, cx, cy, 34, _is_gold)
                   > _region_count(before, cx, cy, 34, _is_gold) + 6,
    }

    # 5. lantern_lit -> the Heart-Lantern floods the crown in warm light
    before, _, _ = _scene_surface("crown", ["stair_open"])
    after, _, _ = _scene_surface("crown", ["stair_open", "lantern_lit"])
    beats["lantern_lit"] = {
        "gold_px_before": _surface_count(before, _is_gold),
        "gold_px_after": _surface_count(after, _is_gold),
        "changed": _surface_count(after, _is_gold) > _surface_count(before, _is_gold) + 100,
    }

    # 6. ended -> fireflies pour back in a golden river
    before, _, _ = _scene_surface("gate", ["lantern_lit"])
    after, _, _ = _scene_surface("gate", ["lantern_lit", "ended"])
    beats["ended"] = {
        "firefly_px_before": _surface_count(before, _is_firefly),
        "firefly_px_after": _surface_count(after, _is_firefly),
        "changed": _surface_count(after, _is_firefly) > _surface_count(before, _is_firefly) + 8,
    }

    beats["all_beats_distinct"] = all(b["changed"] for b in beats.values())
    return beats


def feedback_tone_check():
    """Prove success vs failure feedback renders differently (dialogue + marker).

    Drives two real Game outcomes -- a valid item use (success) and a wrong-item
    use (failure) -- and pixel-samples the dialogue panel accent + the target
    marker glow to confirm success reads warm-gold and failure reads russet, and
    that the two frames differ in the interface bands.
    """
    from .game import Game
    from .world import State
    from . import verbs

    def frame(kind):
        g = Game()
        if kind == "success":
            g.state = State("mill", (3, 3), inventory=frozenset({"crank_handle"}))
        else:
            g.state = State("mill", (3, 3), inventory=frozenset({"glass_flask"}))
        g._set_facing((-1, 0))                # face crank socket (2,3)
        g._verb(verbs.USE)
        return g

    gs = frame("success")
    gf = frame("failure")
    surf_s, ox, oy = gs.render(1280, 720, 0.0)
    surf_f, _, _ = gf.render(1280, 720, 0.0)

    w, h = surf_s.get_size()
    # dialogue panel band (drawn at y = h-250 .. h-150)
    def band_count(surface, fn):
        n = 0
        for y in range(h - 250, h - 150, 2):
            for x in range(0, w, 2):
                if fn(surface.get_at((x, y))[:3]):
                    n += 1
        return n

    gold_s = band_count(surf_s, _is_gold)
    russet_s = band_count(surf_s, _is_russet)
    gold_f = band_count(surf_f, _is_gold)
    russet_f = band_count(surf_f, _is_russet)

    # target-marker stamp: the solid tone dot at the faced cell's center
    from .ui import tile_top_center
    tx, ty = tile_top_center(2, 3, ox, oy)
    def marker_gold(surface):
        return _region_count(surface, tx, ty, 9, _is_gold)
    def marker_russet(surface):
        return _region_count(surface, tx, ty, 9, _is_russet)

    bands_differ = pygame.image.tobytes(surf_s, "RGB") != pygame.image.tobytes(surf_f, "RGB")

    return {
        "success_dialogue_gold_px": gold_s,
        "success_dialogue_russet_px": russet_s,
        "failure_dialogue_gold_px": gold_f,
        "failure_dialogue_russet_px": russet_f,
        "success_marker_gold_px": marker_gold(surf_s),
        "success_marker_russet_px": marker_russet(surf_s),
        "failure_marker_gold_px": marker_gold(surf_f),
        "failure_marker_russet_px": marker_russet(surf_f),
        "dialogue_success_reads_gold": gold_s > 3 and gold_s > russet_s,
        "dialogue_failure_reads_russet": russet_f > 3 and russet_f > gold_f,
        "marker_success_reads_gold": marker_gold(surf_s) > marker_russet(surf_s),
        "marker_failure_reads_russet": marker_russet(surf_f) > marker_gold(surf_f),
        "frames_differ": bands_differ,
        "ok": (gold_s > 3 and gold_s > russet_s
               and russet_f > 3 and russet_f > gold_f
               and marker_gold(surf_s) > marker_russet(surf_s)
               and marker_russet(surf_f) > marker_gold(surf_f)
               and bands_differ),
    }
