"""G13 node 14 -- population + handoff runtime evidence (headless, no vision).

Two things, both code-level (no vision tool):

  1. population_checks() renders each finished room, then for every docs/world.json
     object re-renders with that prop dropped and diffs its footprint -- proving
     each entity draws in place at its catalog cell. Dumps frames + ASCII maps.

  2. A live Game controller run through the real SDL input path
     (pygame.event.post -> pygame.event.get -> Game.handle_event) that talks to
     Mallow (yields the Crank Handle) and Bramble (yields the Glass Flask) and
     asserts both handoffs, then records a JSON runtime trace.

Run:  python3 tools/demo_population.py   (SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy)
Exits 0 iff every entity is present in-place AND both handoffs land.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from emberglow import inputmap, checks  # noqa: E402
from emberglow.game import Game, MOVE_INTERVAL  # noqa: E402
from emberglow.world import NORTH, SOUTH, EAST, WEST  # noqa: E402

DIR_KEY = {NORTH: pygame.K_UP, SOUTH: pygame.K_DOWN,
           EAST: pygame.K_RIGHT, WEST: pygame.K_LEFT}
DT = MOVE_INTERVAL


def post(code, down):
    pygame.event.post(pygame.event.Event(
        pygame.KEYDOWN if down else pygame.KEYUP, key=code))


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
        press(game, pygame.K_e)
        guard += 1
    assert game.dialogue is None, "dialogue did not dismiss"


def goto_and_face(game, room, target):
    tile = game.world.interaction_tiles(room, target, game.state.flags)[0]
    path = game.world.find_path(game.state.room, game.state.pos, room, tile,
                                game.state.flags)
    assert path is not None, (game.state.room, game.state.pos, "->", room, target)
    for d in path:
        step(game, d)
    assert (game.state.room, game.state.pos) == (room, tile)
    ox, oy = game.world.object_position(room, target)
    face(game, (ox - tile[0], oy - tile[1]))
    assert game.target == target, (game.target, target)


def snap(game):
    return {
        "room": game.state.room, "pos": list(game.state.pos),
        "target": game.target,
        "dialogue": game.dialogue.speaker if game.dialogue else None,
        "selected": game.selected_item(),
        "flags": sorted(game.state.flags),
        "inventory": sorted(game.state.inventory),
    }


def main():
    pygame.init()
    pygame.event.clear()

    # --- 1. population (render-in-place) check -------------------------------
    pop = checks.population_checks()
    present = {k: v["present"] for k, v in pop["entities"].items()}
    print(json.dumps({"population_entities": present,
                      "population_ok": pop["ok"]}, indent=2))

    # --- 2. live handoffs through the real input path -------------------------
    game = Game()
    trace = []

    def mark(label):
        trace.append({"label": label, **snap(game)})

    mark("spawn")

    # Mallow -> Crank Handle
    goto_and_face(game, "gate", "mallow")
    press(game, pygame.K_t)          # TALK
    mark("meet_mallow")
    assert "crank_handle" in snap(game)["inventory"], "Mallow did not grant the crank"
    assert "met_mallow" in snap(game)["flags"], "meet_mallow flag not set"
    mallow_lines = [l[1] for l in game.dialogue.lines]
    advance_all(game)

    # Bramble -> Glass Flask (cross the open gate->market portal)
    goto_and_face(game, "market", "bramble")
    press(game, pygame.K_t)          # TALK
    mark("request_flask")
    assert "glass_flask" in snap(game)["inventory"], "Bramble did not grant the flask"
    assert "flask_received" in snap(game)["flags"], "flask_received flag not set"
    bramble_lines = [l[1] for l in game.dialogue.lines]
    advance_all(game)

    final = snap(game)
    handoff_ok = ("crank_handle" in final["inventory"]
                  and "glass_flask" in final["inventory"])
    assert handoff_ok, final

    handoffs = {
        "mallow": {"item": "crank_handle", "flag": "met_mallow",
                   "lines": mallow_lines},
        "bramble": {"item": "glass_flask", "flag": "flask_received",
                    "lines": bramble_lines},
        "handoffs_land": handoff_ok,
    }

    out = {
        "driver": "SDL dummy (headless)",
        "input_path": "pygame.event.post -> pygame.event.get -> Game.handle_event "
                      "(the real SDL keyboard event queue; no direct game-state calls)",
        "population": pop,
        "handoffs": handoffs,
        "trace": trace,
        "final_state": final,
    }

    os.makedirs("evidence", exist_ok=True)
    with open("evidence/node14_handoff_trace.json", "w") as f:
        json.dump(out, f, indent=2)

    all_ok = pop["ok"] and handoff_ok
    print(json.dumps({
        "population_ok": pop["ok"],
        "handoffs_land": handoff_ok,
        "all_ok": all_ok,
    }, indent=2))
    pygame.quit()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
