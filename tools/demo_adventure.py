"""Full 11-action adventure playthrough via the real input path (G13 node 5).

Drives the Game controller end-to-end through pygame.event.post -> pygame.event.get
-> Game.handle_event (the exact application input path a real keyboard feeds) to
walk, examine, talk, take, and use items across all five rooms, ending at the
'ended' terminal flag. It also demonstrates a distinct item-use failure, proves the
success-vs-failure and world-reactivity feedback with code-level pixel sampling,
and dumps frame PNGs + a JSON runtime trace.

Run:  python3 tools/demo_adventure.py   (SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy)
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

DIR_KEY = {
    NORTH: pygame.K_UP, SOUTH: pygame.K_DOWN, EAST: pygame.K_RIGHT, WEST: pygame.K_LEFT,
}
KEY = {
    inputmap.INTERACT: pygame.K_e,
    inputmap.EXAMINE: pygame.K_x,
    inputmap.TALK: pygame.K_t,
    inputmap.TAKE: pygame.K_g,
    inputmap.USE: pygame.K_u,
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
    while game.dialogue is not None and guard < 30:
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
    assert (game.state.room, game.state.pos) == (room, tile), (game.state.room, game.state.pos, room, tile)
    ox, oy = game.world.object_position(room, target)
    face(game, (ox - tile[0], oy - tile[1]))
    assert game.target == target, (game.target, target)


def snap(game):
    return {
        "frame": game.frame,
        "room": game.state.room,
        "pos": list(game.state.pos),
        "facing": list(game.facing),
        "target": game.target,
        "dialogue": game.dialogue.speaker if game.dialogue else None,
        "dialogue_tone": game.dialogue.tone if game.dialogue else None,
        "selected": game.selected_item(),
        "flags": sorted(game.state.flags),
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

    def do_action(action_id, room, target, verb_key, expect_flag=None, expect_item=None, use_item=None):
        goto_and_face(game, room, target)
        if use_item is not None:
            select_item(game, use_item)
        press(game, verb_key)
        mark(action_id)
        s = snap(game)
        if expect_flag is not None:
            assertions[f"{action_id}_sets_{expect_flag}"] = expect_flag in s["flags"]
            assert assertions[f"{action_id}_sets_{expect_flag}"], s
        if expect_item is not None:
            assertions[f"{action_id}_grants_{expect_item}"] = expect_item in s["inventory"]
            assert assertions[f"{action_id}_grants_{expect_item}"], s

    mark("spawn")

    # 1. meet Mallow -> crank handle
    do_action("meet_mallow", "gate", "mallow", KEY[inputmap.TALK],
              expect_flag="met_mallow", expect_item="crank_handle")
    assertions["meet_mallow_conversation_multiline"] = len(game.dialogue.lines) > 1
    advance_all(game)

    # 2. request the flask from Bramble
    do_action("request_flask", "market", "bramble", KEY[inputmap.TALK],
              expect_flag="flask_received", expect_item="glass_flask")
    advance_all(game)

    # 3. FAILURE: use the glass flask on the crank socket (wrong item) -> distinct failure
    goto_and_face(game, "mill", "crank_socket")
    select_item(game, "glass_flask")
    press(game, KEY[inputmap.USE])
    mark("use_wrong_item_on_socket")
    s = snap(game)
    assertions["wrong_item_fails"] = ("water_flowing" not in s["flags"]
                                      and "glass_flask" in s["inventory"]
                                      and game.dialogue is not None
                                      and game.dialogue.tone == verbs.FAILURE)
    assert assertions["wrong_item_fails"], s
    failure_surface, _, _ = game.render(1280, 720, 0.0)
    pygame.image.save(failure_surface, "evidence/node5_failure.png")
    advance_all(game)

    # 4. turn the wheel with the crank
    do_action("turn_wheel", "mill", "crank_socket", KEY[inputmap.USE],
              expect_flag="water_flowing", use_item="crank_handle")
    assertions["turn_wheel_consumed_crank"] = "crank_handle" not in snap(game)["inventory"]
    assert assertions["turn_wheel_consumed_crank"]
    success_surface, _, _ = game.render(1280, 720, 0.0)
    pygame.image.save(success_surface, "evidence/node5_success.png")
    advance_all(game)

    # 5. fill the flask at the spout
    do_action("fill_flask", "mill", "water_spout", KEY[inputmap.USE],
              expect_flag="flask_filled", expect_item="full_flask", use_item="glass_flask")
    advance_all(game)

    # 6. take the ember-seed from the greenhouse
    do_action("take_seed", "greenhouse", "ember_seed", KEY[inputmap.TAKE],
              expect_flag="seed_taken", expect_item="ember_seed")
    advance_all(game)

    # 7. cool the lens at Bramble (use full flask)
    do_action("cool_lens", "market", "bramble", KEY[inputmap.USE],
              expect_flag="lens_ready", expect_item="lens", use_item="full_flask")
    advance_all(game)

    # 8. Mallow clears the stair
    do_action("open_stair", "gate", "mallow", KEY[inputmap.TALK],
              expect_flag="stair_open")
    advance_all(game)

    # 9. mount the lens
    do_action("mount_lens", "crown", "lens_mount", KEY[inputmap.USE],
              expect_flag="lens_mounted", use_item="lens")
    advance_all(game)

    # 10. plant the seed
    do_action("plant_seed", "crown", "seed_cradle", KEY[inputmap.USE],
              expect_flag="seed_planted", use_item="ember_seed")
    advance_all(game)

    # 11. kindle the lantern (bare operate)
    do_action("kindle_lantern", "crown", "focus_wheel", KEY[inputmap.USE],
              expect_flag="lantern_lit")
    advance_all(game)
    lantern_surface, _, _ = game.render(1280, 720, 0.0)
    pygame.image.save(lantern_surface, "evidence/node5_lantern_lit.png")

    # 12. ring the bell -> ended
    do_action("ring_bell", "gate", "hollow_bell", KEY[inputmap.USE],
              expect_flag="ended")
    advance_all(game)
    ended_surface, _, _ = game.render(1280, 720, 0.0)
    pygame.image.save(ended_surface, "evidence/node5_ended.png")

    final = snap(game)
    assertions["full_playthrough_reached_ended"] = "ended" in final["flags"]
    assertions["inventory_empty_at_end"] = final["inventory"] == []
    assertions["all_11_actions_in_order"] = (
        [a["id"] for a in game.world.actions]
        == ["meet_mallow", "request_flask", "turn_wheel", "fill_flask", "take_seed",
            "cool_lens", "open_stair", "mount_lens", "plant_seed", "kindle_lantern",
            "ring_bell"])
    assert assertions["full_playthrough_reached_ended"], final

    # pixel-sampling checks (success vs failure feedback + world beats)
    beats = checks.world_beat_checks()
    feedback = checks.feedback_tone_check()

    out = {
        "driver": "SDL dummy (headless)",
        "input_path": "pygame.event.post -> pygame.event.get -> Game.handle_event "
                      "(the real SDL keyboard event queue; no direct game-state calls)",
        "move_interval_s": MOVE_INTERVAL,
        "dt_s": DT,
        "trace": trace,
        "game_event_log": game.trace,
        "assertions": assertions,
        "final_state": final,
        "world_beat_checks": beats,
        "feedback_tone_check": feedback,
        "frames": [
            "evidence/node5_success.png",
            "evidence/node5_failure.png",
            "evidence/node5_lantern_lit.png",
            "evidence/node5_ended.png",
        ],
    }

    all_ok = (all(assertions.values())
              and beats["all_beats_distinct"]
              and feedback["ok"])
    out["all_checks_pass"] = all_ok

    os.makedirs("evidence", exist_ok=True)
    with open("evidence/adventure_playthrough.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({
        "all_checks_pass": all_ok,
        "assertions": assertions,
        "final_state": final,
        "world_beats": {k: v["changed"] for k, v in beats.items() if isinstance(v, dict) and "changed" in v},
        "feedback_tone": {k: v for k, v in feedback.items() if isinstance(v, bool)},
    }, indent=2))
    pygame.quit()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
