"""Runtime traversal demonstration for the Emberglow Hollow world geometry.

Rendering-independent and headless (no pygame, no display). Loads the world,
prints the validate() report, then walks a real route with World.move() to show
legal movement, a blocked move, room transitions, gate enforcement, and the full
11-action progression on foot. Exits 0 iff every assertion holds.

Run:  python3 tools/demo_traversal.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from emberglow.world import World, State, BlockedError, NORTH, SOUTH, EAST, WEST, DIRECTIONS

DIR_SYM = {NORTH: "N", SOUTH: "S", EAST: "E", WEST: "W"}


def main() -> int:
    w = World()

    print("== validate() ==")
    report = w.validate()
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        print("FAIL: geometry contract problems")
        return 1

    print("\n== legal / blocked movement (Hollow Gate) ==")
    state = w.initial_state()
    print(f"spawn: {state.room} {state.pos}")
    for d, name in ((EAST, "east"), (NORTH, "north"), (WEST, "west"), (SOUTH, "south")):
        if w.can_move(state, d):
            print(f"  move {name}: ok -> {w.move(state, d).pos}")
        else:
            print(f"  move {name}: blocked")
    cottage = (6, 6)
    s = State("gate", (5, 6))
    try:
        w.move(s, EAST)
        print("  BUG: walked into the SE cottage")
        return 1
    except BlockedError:
        print(f"  blocked: cannot walk east from (5,6) into cottage {cottage}")

    print("\n== room transitions ==")
    s = State("gate", (7, 4))
    s2 = w.move(s, EAST)
    print(f"  gate (7,4) --E--> {s2.room} {s2.pos}")
    assert (s2.room, s2.pos) == ("market", (1, 4))
    s3 = w.move(s2, WEST)
    print(f"  {s2.room} {s2.pos} --W--> {s3.room} {s3.pos}")
    assert (s3.room, s3.pos) == ("gate", (7, 4))

    print("\n== gate enforcement ==")
    s = State("mill", (7, 4))
    closed = not w.can_move(s, EAST)
    print(f"  mill->greenhouse without water_flowing: {'closed (correct)' if closed else 'OPEN (BUG)'}")
    assert closed
    s = State("mill", (7, 4), flags=frozenset({"water_flowing"}))
    s2 = w.move(s, EAST)
    print(f"  mill->greenhouse with water_flowing: {s2.room} {s2.pos}")
    assert (s2.room, s2.pos) == ("greenhouse", (1, 4))

    print("\n== full 11-action progression on foot ==")
    state = w.initial_state()
    for action in w.actions:
        room, target = action["room"], action["target"]
        tile = w.interaction_tiles(room, target, state.flags)[0]
        path = w.find_path(state.room, state.pos, room, tile, state.flags)
        assert path is not None, f"unreachable: {action['id']}"
        for d in path:
            state = w.move(state, d)
        assert (state.room, state.pos) == (room, tile)
        state = State(
            state.room, state.pos,
            flags=state.flags | frozenset(action["flags"]),
            inventory=(state.inventory - frozenset(action["consume"])) | frozenset(action["grant"]),
        )
        route = "".join(DIR_SYM[d] for d in path)
        print(f"  {action['id']:>16} -> {room}.{target} stand {tile}  ({len(path)} steps: {route})")
    assert w.terminal_flag in state.flags
    print(f"terminal flag '{w.terminal_flag}' reached: the hollow is lit.")

    print("\nALL TRAVERSAL DEMONSTRATIONS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
