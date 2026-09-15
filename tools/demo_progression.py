"""Node 15: recorded headless full-playthrough trace + fresh climax/ending captures.

Drives the Game controller end-to-end through pygame.event.post -> pygame.event.get
-> Game.handle_event (the exact application input path a real keyboard feeds) to
walk, talk, take, and use items across all five rooms, ending at 'ended'. Along the
way it proves each of the 11 actions fires exactly once, attempts several
out-of-order actions and asserts each is rejected (LOCKED, no state mutation), then
captures fresh runtime frames of the climax (lantern_lit) and the ending (ended,
with the firefly return + Mallow's companion + the end title).

Run:  python3 tools/demo_progression.py   (SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy)
Exits 0 iff every assertion and check passes.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from emberglow import inputmap, verbs, checks  # noqa: E402
from emberglow.game import Game, MOVE_INTERVAL  # noqa: E402
from emberglow.world import NORTH, SOUTH, EAST, WEST  # noqa: E402

DIR_KEY = {NORTH: pygame.K_UP, SOUTH: pygame.K_DOWN, EAST: pygame.K_RIGHT, WEST: pygame.K_LEFT}
KEY = {
    inputmap.INTERACT: pygame.K_e, inputmap.EXAMINE: pygame.K_x,
    inputmap.TALK: pygame.K_t, inputmap.TAKE: pygame.K_g, inputmap.USE: pygame.K_u,
    inputmap.DISMISS: pygame.K_ESCAPE,
}
DT = MOVE_INTERVAL


def post(code, down):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN if down else pygame.KEYUP, key=code))


def pump(game, n=1, dt=DT):
    for _ in range(n):
        for e in pygame.event.get():
            game.handle_event(e)
        game.tick(dt)


def step(game, d):
    post(DIR_KEY[d], True); pump(game)
    post(DIR_KEY[d], False); pump(game)


def face(game, d):
    post(DIR_KEY[d], True); post(DIR_KEY[d], False); pump(game)


def press(game, key):
    post(key, True); pump(game)
    post(key, False); pump(game)


def advance_all(game):
    guard = 0
    while game.dialogue is not None and guard < 40:
        press(game, KEY[inputmap.INTERACT])
        guard += 1
    assert game.dialogue is None, "dialogue did not dismiss"


def select_item(game, item_id):
    guard = 0
    while game.selected_item() != item_id and guard < 10:
        post(pygame.K_TAB, True); pump(game)
        post(pygame.K_TAB, False); pump(game)
        guard += 1
    assert game.selected_item() == item_id, (game.selected_item(), item_id, sorted(game.state.inventory))


def goto_and_face(game, room, target):
    tile = game.world.interaction_tiles(room, target, game.state.flags)[0]
    path = game.world.find_path(game.state.room, game.state.pos, room, tile, game.state.flags)
    assert path is not None, (game.state.room, game.state.pos, "->", room, target)
    for d in path:
        step(game, d)
    assert (game.state.room, game.state.pos) == (room, tile)
    ox, oy = game.world.object_position(room, target)
    face(game, (ox - tile[0], oy - tile[1]))
    assert game.target == target, (game.target, target)


def snap(game):
    return {
        "frame": game.frame, "room": game.state.room, "pos": list(game.state.pos),
        "facing": list(game.facing), "target": game.target,
        "dialogue": game.dialogue.speaker if game.dialogue else None,
        "selected": game.selected_item(), "flags": sorted(game.state.flags),
        "inventory": sorted(game.state.inventory),
    }


def main():
    pygame.init()
    pygame.event.clear()
    game = Game()
    trace = []
    assertions = {}

    def mark(label):
        trace.append({"label": label, **snap(game)})

    def do_action(action_id, room, target, verb_key, expect_flag=None, expect_item=None,
                  use_item=None, consume_item=None):
        goto_and_face(game, room, target)
        if use_item is not None:
            select_item(game, use_item)
        flags_before = frozenset(game.state.flags)
        press(game, verb_key)
        mark(action_id)
        s = snap(game)
        if expect_flag is not None:
            assertions[f"{action_id}_sets_{expect_flag}"] = expect_flag in s["flags"]
            assert assertions[f"{action_id}_sets_{expect_flag}"], s
        if expect_item is not None:
            assertions[f"{action_id}_grants_{expect_item}"] = expect_item in s["inventory"]
            assert assertions[f"{action_id}_grants_{expect_item}"], s
        if consume_item is not None:
            assertions[f"{action_id}_consumes_{consume_item}"] = consume_item not in s["inventory"]
            assert assertions[f"{action_id}_consumes_{consume_item}"], s
        # one-shot: the action's flag was not already present before firing
        if expect_flag is not None:
            assertions[f"{action_id}_fires_exactly_once"] = expect_flag not in flags_before
            assert assertions[f"{action_id}_fires_exactly_once"], s

    mark("spawn")

    # --- out-of-order attempt #1: ring the bell before the lantern is lit ---
    goto_and_face(game, "gate", "hollow_bell")
    press(game, KEY[inputmap.USE])
    mark("out_of_order_ring_bell_early")
    s = snap(game)
    assertions["out_of_order_ring_bell_locked"] = "ended" not in s["flags"]
    assert assertions["out_of_order_ring_bell_locked"], s
    advance_all(game)

    # --- the 11-action chain (each exactly once) -----------------------------
    do_action("meet_mallow", "gate", "mallow", KEY[inputmap.TALK],
              expect_flag="met_mallow", expect_item="crank_handle")
    advance_all(game)

    do_action("request_flask", "market", "bramble", KEY[inputmap.TALK],
              expect_flag="flask_received", expect_item="glass_flask")
    advance_all(game)

    # --- out-of-order attempt #2: fill the flask before the water flows ---
    goto_and_face(game, "mill", "water_spout")
    select_item(game, "glass_flask")
    press(game, KEY[inputmap.USE])
    mark("out_of_order_fill_before_water")
    s = snap(game)
    assertions["out_of_order_fill_locked"] = ("flask_filled" not in s["flags"]
                                              and "glass_flask" in s["inventory"])
    assert assertions["out_of_order_fill_locked"], s
    advance_all(game)

    do_action("turn_wheel", "mill", "crank_socket", KEY[inputmap.USE],
              expect_flag="water_flowing", use_item="crank_handle", consume_item="crank_handle")
    advance_all(game)

    do_action("fill_flask", "mill", "water_spout", KEY[inputmap.USE],
              expect_flag="flask_filled", expect_item="full_flask",
              use_item="glass_flask", consume_item="glass_flask")
    advance_all(game)

    do_action("take_seed", "greenhouse", "ember_seed", KEY[inputmap.TAKE],
              expect_flag="seed_taken", expect_item="ember_seed")
    advance_all(game)

    do_action("cool_lens", "market", "bramble", KEY[inputmap.USE],
              expect_flag="lens_ready", expect_item="lens",
              use_item="full_flask", consume_item="full_flask")
    advance_all(game)

    do_action("open_stair", "gate", "mallow", KEY[inputmap.TALK], expect_flag="stair_open")
    advance_all(game)

    # --- out-of-order attempt #3: kindle before the lens + seed are set ---
    goto_and_face(game, "crown", "focus_wheel")
    press(game, KEY[inputmap.USE])
    mark("out_of_order_kindle_before_lens_seed")
    s = snap(game)
    assertions["out_of_order_kindle_locked"] = ("lantern_lit" not in s["flags"]
                                                and "lens_mounted" not in s["flags"]
                                                and "seed_planted" not in s["flags"])
    assert assertions["out_of_order_kindle_locked"], s
    advance_all(game)

    do_action("mount_lens", "crown", "lens_mount", KEY[inputmap.USE],
              expect_flag="lens_mounted", use_item="lens", consume_item="lens")
    advance_all(game)

    do_action("plant_seed", "crown", "seed_cradle", KEY[inputmap.USE],
              expect_flag="seed_planted", use_item="ember_seed", consume_item="ember_seed")
    advance_all(game)

    do_action("kindle_lantern", "crown", "focus_wheel", KEY[inputmap.USE],
              expect_flag="lantern_lit")
    advance_all(game)

    # --- fresh climax capture (lantern_lit) ----------------------------------
    lantern_surface, _, _ = game.render(1280, 720, 0.0)
    pygame.image.save(lantern_surface, "evidence/lantern_lit.png")
    mark("capture_lantern_lit")

    do_action("ring_bell", "gate", "hollow_bell", KEY[inputmap.USE], expect_flag="ended")
    advance_all(game)

    # --- fresh ending capture (ended: fireflies + companion + title) ----------
    ended_surface, _, _ = game.render(1280, 720, 0.0)
    pygame.image.save(ended_surface, "evidence/ended.png")
    mark("capture_ended")

    final = snap(game)
    assertions["full_playthrough_reached_ended"] = "ended" in final["flags"]
    assertions["inventory_empty_at_end"] = final["inventory"] == []
    assertions["each_action_flag_set_exactly_once"] = (
        len(final["flags"]) == len(game.world.actions))
    assert assertions["full_playthrough_reached_ended"], final

    # pixel-sampling proofs (beats + feedback + ending companion/title)
    beats = checks.world_beat_checks()
    feedback = checks.feedback_tone_check()
    ending = checks.ending_checks()

    out = {
        "driver": "SDL dummy (headless)",
        "input_path": "pygame.event.post -> pygame.event.get -> Game.handle_event "
                      "(the real SDL keyboard event queue; no direct game-state calls)",
        "move_interval_s": MOVE_INTERVAL, "dt_s": DT,
        "trace": trace,
        "game_event_log": game.trace,
        "assertions": assertions,
        "final_state": final,
        "final_flag_count": len(final["flags"]),
        "action_count": len(game.world.actions),
        "world_beat_checks": {k: v["changed"] for k, v in beats.items()
                              if isinstance(v, dict) and "changed" in v},
        "all_beats_distinct": beats["all_beats_distinct"],
        "feedback_tone_check_ok": feedback["ok"],
        "ending_checks": ending,
        "frames": ["evidence/lantern_lit.png", "evidence/ended.png"],
    }

    all_ok = (all(assertions.values()) and beats["all_beats_distinct"]
              and feedback["ok"] and ending["ok"]
              and len(final["flags"]) == len(game.world.actions))
    out["all_checks_pass"] = all_ok

    os.makedirs("evidence", exist_ok=True)
    with open("evidence/progression_playthrough.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({
        "all_checks_pass": all_ok,
        "final_state": final,
        "world_beats": out["world_beat_checks"],
        "feedback_tone_ok": feedback["ok"],
        "ending_checks": ending,
    }, indent=2))
    pygame.quit()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
