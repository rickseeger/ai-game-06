#!/usr/bin/env python3
"""Emberglow Hollow -- node 2 representative scene (fixed-isometric foundation).

Usage:
  python3 -m emberglow.main                 # live game (real input: WASD/arrows)
  python3 -m emberglow.main --input-check   # input-mapping + press/release tests
  python3 -m emberglow.main --headless      # one frame -> evidence/scene_gate.png
  python3 -m emberglow.main --capture 6     # animation frames -> evidence/
  python3 -m emberglow.main --check         # render + full automated verification
"""

import argparse
import json
import os
import sys

if any(f in sys.argv for f in ("--headless", "--capture", "--check", "--input-check")):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from .scene import build_room_gate, render_room, layout  # noqa: E402
from . import ui  # noqa: E402

W, H = 1280, 720
ITEMS = ["crank_handle", "", "", "", ""]
SELECTED = 0
SPEAKER = "Mallow"
TEXT = ("The Heart-Lantern has gone out, and the hollow grows cold. "
        "Here -- this crank will free the mill-wheel.")


def render_frame(room, t, w=W, h=H, items=ITEMS, selected=SELECTED,
                 speaker=SPEAKER, text=TEXT):
    ox, oy = layout(room, w, h)
    surface = pygame.Surface((w, h))
    render_room(surface, room, t, ox, oy)
    ui.draw_ui(surface, room, items, selected, speaker, text)
    return surface, ox, oy


def run_check():
    from . import checks
    room = build_room_gate()
    t0 = 0.0
    surface, ox, oy = render_frame(room, t0)
    w, h = surface.get_size()

    stats = checks._count_pixels(surface)
    geom = checks.geometry_checks(room, ox, oy)
    order = checks.draw_order_checks(room, t0, ox, oy)
    fills = {
        "path_tile": checks.flat_fill_check(surface, 4, 3, ox, oy, "cream_parch"),
        "grass_tile": checks.flat_fill_check(surface, 7, 2, ox, oy, "moss_green"),
        "raised_top": checks.flat_fill_check(surface, 3, 0, ox, oy, "moss_green", h=1),
    }
    # raised tile side face must be darker than its top face (2.5D extrusion)
    tx, ty = checks.tile_center(3, 0, ox, oy, h=1)
    top = surface.get_at((tx, ty))[:3]
    side = surface.get_at((tx + 16, ty + 22))[:3]
    side_darker = sum(top) > sum(side)

    # determinism + animation actually changes the frame
    s0b, _, _ = render_frame(room, t0)
    ident = pygame.image.tobytes(surface, "RGB") == pygame.image.tobytes(s0b, "RGB")
    s1, _, _ = render_frame(room, 0.4)
    animated = pygame.image.tobytes(surface, "RGB") != pygame.image.tobytes(s1, "RGB")

    # sky corner is cool violet ambient (B >= R), never black
    corner = surface.get_at((5, 5))[:3]
    corner_violet = corner[2] >= corner[0] and corner[2] > 40

    feats = checks.feature_presence(surface, room, ox, oy)
    ui = checks.ui_presence(surface)

    results = {
        "size": [w, h],
        "features": feats,
        "ui": ui,
        "unique_colors": stats["unique_colors"],
        "counts": {k: v for k, v in stats.items() if k != "unique_colors"},
        "geometry": geom,
        "draw_order": order,
        "flat_fills": fills,
        "side_darker_than_top": side_darker,
        "top_rgb": list(top), "side_rgb": list(side),
        "sky_corner_rgb": list(corner), "sky_corner_violet": corner_violet,
        "deterministic": ident,
        "animation_changes_frame": animated,
        "palette": {k: list(v) for k, v in __import__("emberglow.palette",
                                                       fromlist=["PALETTE"]).PALETTE.items()},
    }

    checks_dict = {
        "size_is_1280x720": (w, h) == (W, H),
        "not_blank": stats["unique_colors"] > 800,
        "warm_surfaces_present": stats["warm"] > 800,
        "cool_violet_ambient_present": stats["cool"] > 300,
        "foliage_present": stats["foliage"] > 300,
        "firefly_glow_present": stats["glow"] > 30,
        "warm_lantern_glow_present": stats["warm_glow"] > 40,
        "no_pure_black": stats["black"] == 0,
        "path_tile_on_palette": fills["path_tile"]["within_tolerance"],
        "grass_tile_on_palette": fills["grass_tile"]["within_tolerance"],
        "raised_top_on_palette": fills["raised_top"]["within_tolerance"],
        "side_darker_than_top": side_darker,
        "sky_corner_violet": corner_violet,
        "iso_slope_2_to_1": geom["iso_slope_2_to_1"],
        "diamond_2_to_1": geom["diamond_2_to_1"],
        "tile_order_monotonic": order["tile_order_monotonic"],
        "characters_and_props_present": all(f["present"] for f in feats.values()),
        "interface_present": ui["interface_present"],
        "props_after_own_tile": order["props_after_own_tile"],
        "far_before_near": order["far_before_near"],
        "deterministic": ident,
        "animation_changes_frame": animated,
    }
    results["checks"] = checks_dict
    results["ok"] = all(checks_dict.values())

    # unit tests (projection, palette, draw-order) -- stdlib unittest
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    ut = runner.run(suite)
    results["unit_tests_run"] = ut.testsRun
    results["unit_tests_failed"] = len(ut.failures) + len(ut.errors)
    results["unit_tests_ok"] = ut.wasSuccessful()

    os.makedirs("evidence", exist_ok=True)
    pygame.image.save(surface, "evidence/scene_gate.png")
    with open("evidence/scene_gate.ascii.txt", "w") as f:
        f.write(checks.ascii_map(surface) + "\n")
    with open("evidence/check_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(json.dumps({k: v for k, v in results.items() if k != "palette"}, indent=2))
    print("----- structure map (W=warm g=green C=cool F=firefly) -----")
    print(checks.ascii_map(surface))
    return 0 if (results["ok"] and ut.wasSuccessful()) else 1


def run_capture(n):
    room = build_room_gate()
    dt = 0.16
    os.makedirs("evidence", exist_ok=True)
    frames = []
    prev = None
    all_changed = True
    for i in range(n):
        t = i * dt
        surface, _, _ = render_frame(room, t)
        fn = f"evidence/scene_gate_t{i:02d}.png"
        pygame.image.save(surface, fn)
        cur = pygame.image.tobytes(surface, "RGB")
        if prev is not None and cur == prev:
            all_changed = False
        prev = cur
        frames.append({"file": fn, "t": round(t, 2)})
    manifest = {"frames": frames, "animates": all_changed,
                "note": "firefly drift + glow flicker + player idle bob (restrained)"}
    with open("evidence/capture_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))
    return 0


def run_play(w, h):
    """Live interactive game: real keyboard -> Game controller (the node-4 input path)."""
    from .game import Game
    game = Game()
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption("Emberglow Hollow -- the Long Dusk")
    clock = pygame.time.Clock()
    t = 0.0
    while not game.quit:
        for e in pygame.event.get():
            game.handle_event(e)
        dt = clock.tick(60) / 1000.0
        t += dt
        game.tick(dt)
        surface, _, _ = game.render(w, h, t)
        screen.blit(surface, (0, 0))
        pygame.display.flip()
    pygame.quit()
    return 0


def run_input_check():
    """Run the input-mapping + press/release unit tests (headless)."""
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_input.py")
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    ut = runner.run(suite)
    return 0 if ut.wasSuccessful() else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--capture", type=int, default=0, metavar="N")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--input-check", action="store_true")
    ap.add_argument("--play", action="store_true")
    ap.add_argument("--size", default=f"{W}x{H}")
    ap.add_argument("--out", default="evidence/scene_gate.png")
    args = ap.parse_args()

    pygame.init()
    w, h = (int(v) for v in args.size.split("x"))

    if args.check:
        code = run_check()
        pygame.quit()
        return code

    if args.input_check:
        code = run_input_check()
        pygame.quit()
        return code

    if args.capture:
        code = run_capture(args.capture)
        pygame.quit()
        return code

    room = build_room_gate()
    if args.headless:
        surface, _, _ = render_frame(room, 0.0, w, h)
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        pygame.image.save(surface, args.out)
        print("frame written:", os.path.abspath(args.out))
        pygame.quit()
        return 0

    return run_play(w, h)


if __name__ == "__main__":
    sys.exit(main())
