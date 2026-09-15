"""Actual-input runtime trace for Emberglow Hollow (G13 node 4).

Posts real SDL keyboard events through the game's event queue (pygame.event.post
-> pygame.event.get) and drives the Game controller's own tick loop -- the exact
application input path a real keyboard feeds -- then asserts the documented
controls behave: movement, stopping, target selection, interaction, and
dialogue/interface dismissal, with no stuck movement, no unintended actions, and
no ambiguous targeting. Emits a JSON trace plus frame dumps showing the player in
world with controls and target feedback visible.

Run:  python3 tools/demo_input.py
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from emberglow import inputmap  # noqa: E402
from emberglow.game import Game, MOVE_INTERVAL, OBJECT_NAMES  # noqa: E402
from emberglow.palette import PALETTE, dE  # noqa: E402

KEY = {
    inputmap.MOVE_NORTH: pygame.K_UP,
    inputmap.MOVE_SOUTH: pygame.K_DOWN,
    inputmap.MOVE_EAST: pygame.K_RIGHT,
    inputmap.MOVE_WEST: pygame.K_LEFT,
    inputmap.INTERACT: pygame.K_e,
    inputmap.DISMISS: pygame.K_ESCAPE,
}


def post(code, down):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=code))


def pump(game, n, dt):
    for _ in range(n):
        for e in pygame.event.get():
            game.handle_event(e)
        game.tick(dt)


def snap(game):
    return {
        "frame": game.frame,
        "room": game.state.room,
        "pos": list(game.state.pos),
        "facing": list(game.facing),
        "target": game.target,
        "dialogue": game.dialogue["speaker"] if game.dialogue else None,
        "flags": sorted(game.state.flags),
        "inventory": sorted(game.state.inventory),
    }


def _firefly_hits(surface, cx, cy, r=42):
    hits = 0
    for y in range(max(0, cy - r), min(surface.get_height(), cy + r), 2):
        for x in range(max(0, cx - r), min(surface.get_width(), cx + r), 2):
            r_, g_, b_, *_ = surface.get_at((x, y))
            if g_ > 200 and g_ > r_ and 80 < b_ < 210:
                hits += 1
    return hits


def _dark_text_hits(surface, x0, y0, x1, y1):
    hits = 0
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            r, g, b, *_ = surface.get_at((x, y))
            if r < 140 and g < 110 and b < 90:
                hits += 1
    return hits


def _gold_hits_near(surface, cx, cy, r=26):
    hits = 0
    for y in range(max(0, cy - r), min(surface.get_height(), cy + r), 2):
        for x in range(max(0, cx - r), min(surface.get_width(), cx + r), 2):
            if dE(surface.get_at((x, y))[:3], PALETTE["honey_gold"]) <= 60:
                hits += 1
    return hits


def verify_frame(surface, game, ox, oy):
    """Code-level checks (no vision) that controls + target feedback rendered."""
    from emberglow.ui import tile_top_center
    dx, dy = game.facing
    cell = (game.state.pos[0] + dx, game.state.pos[1] + dy)
    tx, ty = tile_top_center(cell[0], cell[1], ox, oy)
    px, py = tile_top_center(game.state.pos[0], game.state.pos[1], ox, oy)
    w, h = surface.get_size()
    uniq = len({surface.get_at((x, y))[:3]
                for x in range(0, w, 4) for y in range(0, h, 4)})
    res = {
        "not_blank": uniq > 400,
        "controls_hint_text_present": _dark_text_hits(surface, w // 2, 0, w, 80) > 4,
        "player_gold_present": _gold_hits_near(surface, px, py) > 8,
    }
    if game.target is not None:
        res["target_glow_present"] = _firefly_hits(surface, tx, ty) > 8
        # the name label chip sits just above the tile top-center
        res["target_label_text_present"] = _dark_text_hits(
            surface, tx - 48, ty - 42, tx + 48, ty - 8) > 3
    else:
        # facing empty space -> no glow expected; the facing dot is drawn instead
        res["target_glow_present"] = None
        res["target_label_text_present"] = None
    return res


def main():
    pygame.init()
    pygame.event.clear()
    dt = MOVE_INTERVAL
    game = Game()
    trace = []

    def mark(label):
        trace.append({"label": label, **snap(game)})

    checks = {}
    mark("spawn")

    # 1. hold WEST one step, then release -> must stop (no stuck movement)
    post(KEY[inputmap.MOVE_WEST], True); pump(game, 1, dt)
    post(KEY[inputmap.MOVE_WEST], False); pump(game, 1, dt)
    mark("after_west_one_step")
    p_after_west = snap(game)["pos"]
    pump(game, 4, dt)
    mark("after_release_settle")
    checks["stopping_no_stuck"] = snap(game)["pos"] == p_after_west == [3, 6]
    assert checks["stopping_no_stuck"], "stuck movement: player kept moving after release"

    # 2. hold NORTH three steps (continuous hold-to-move), then release
    post(KEY[inputmap.MOVE_NORTH], True); pump(game, 3, dt)
    post(KEY[inputmap.MOVE_NORTH], False); pump(game, 1, dt)
    mark("after_north_three_steps")
    assert snap(game)["pos"] == [3, 3], snap(game)["pos"]

    # 3. face west toward Mallow: blocked move turns facing, selects target
    post(KEY[inputmap.MOVE_WEST], True); pump(game, 1, dt)
    post(KEY[inputmap.MOVE_WEST], False); pump(game, 1, dt)
    mark("facing_mallow")
    checks["target_selection"] = snap(game)["target"] == "mallow"
    checks["blocked_move_no_displacement"] = snap(game)["pos"] == [3, 3]
    assert checks["target_selection"], snap(game)["target"]
    assert checks["blocked_move_no_displacement"], snap(game)["pos"]

    # frame dump: player in world + controls hint + target feedback visible
    surface, ox, oy = game.render(1280, 720, 0.0)
    checks["target_frame"] = verify_frame(surface, game, ox, oy)
    pygame.image.save(surface, "evidence/input_target_frame.png")

    # 4. interact -> performs meet_mallow (dialogue opens, crank granted)
    post(KEY[inputmap.INTERACT], True); pump(game, 1, dt)
    post(KEY[inputmap.INTERACT], False); pump(game, 1, dt)
    mark("after_interact")
    checks["interaction_performed"] = (
        snap(game)["dialogue"] == "Mallow"
        and "crank_handle" in snap(game)["inventory"]
        and "met_mallow" in snap(game)["flags"])
    assert checks["interaction_performed"], snap(game)

    surface, _, _ = game.render(1280, 720, 0.0)
    pygame.image.save(surface, "evidence/input_dialogue_frame.png")

    # 5. dismiss dialogue with escape
    post(KEY[inputmap.DISMISS], True); pump(game, 1, dt)
    post(KEY[inputmap.DISMISS], False); pump(game, 1, dt)
    mark("after_dismiss")
    checks["dialogue_dismissed"] = snap(game)["dialogue"] is None
    assert checks["dialogue_dismissed"], snap(game)

    # 6. no unintended actions: movement changes position only, never flags/inventory
    post(KEY[inputmap.MOVE_SOUTH], True); pump(game, 1, dt)
    post(KEY[inputmap.MOVE_SOUTH], False); pump(game, 1, dt)
    mark("after_south_step")
    checks["no_unintended_actions"] = (
        snap(game)["flags"] == ["met_mallow"]
        and snap(game)["inventory"] == ["crank_handle"])
    checks["no_ambiguous_targeting"] = snap(game)["target"] is None  # faces empty cell
    assert checks["no_unintended_actions"], snap(game)
    assert checks["no_ambiguous_targeting"], snap(game)

    # final frame dump: player standing in world with controls visible
    surface, _, _ = game.render(1280, 720, 0.0)
    checks["controls_frame"] = verify_frame(surface, game, ox, oy)
    pygame.image.save(surface, "evidence/input_controls_frame.png")

    def _all_true(d):
        for v in d.values():
            if isinstance(v, dict):
                if not _all_true(v):
                    return False
            elif v is False:
                return False
        return True

    out = {
        "driver": "SDL dummy (headless)",
        "input_path": "pygame.event.post -> pygame.event.get -> Game.handle_event "
                      "(the real SDL keyboard event queue; no direct game-state calls)",
        "move_interval_s": MOVE_INTERVAL,
        "dt_s": dt,
        "trace": trace,
        "game_event_log": game.trace,
        "checks": checks,
        "all_checks_pass": _all_true(checks),
    }

    os.makedirs("evidence", exist_ok=True)
    with open("evidence/input_trace.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    pygame.quit()
    return 0 if out["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
