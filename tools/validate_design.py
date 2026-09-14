"""Validate the Emberglow Hollow progression (docs/world.json).

Reuses node 1's proven algorithm: builds the producer graph, checks for circular
dependencies, exhaustively searches all reachable (room, flags, inventory) states,
asserts the ending is reachable, every action is reachable, zero softlocked states,
and that each room's floor is connected with every required interaction having a
reachable standing tile. Run:  python3 tools/validate_design.py
"""
from pathlib import Path
from collections import deque, defaultdict
import json

ROOT = Path(__file__).resolve().parents[1]
w = json.loads((ROOT / "docs/world.json").read_text())
rooms, edges, actions = w["rooms"], w["edges"], w["actions"]
assert w["schemaVersion"] == 1
assert len({a["id"] for a in actions}) == len(actions)

# Logical producer graph, including consumed-item dependencies.
producers = {}
for a in actions:
    assert a["flags"], "Every action must be one-shot via a persistent flag"
    for kind, names in (("flag", a["flags"]), ("item", a["grant"])):
        for name in names:
            assert (kind, name) not in producers, ("duplicate producer", name)
            producers[kind, name] = a["id"]

deps = {}
for a in actions:
    assert set(a["consume"]) <= set(a["needs"])
    deps[a["id"]] = {producers["flag", x] for x in a["requires"]} | {producers["item", x] for x in a["needs"]}

order = []
while len(order) < len(actions):
    ready = sorted(k for k, v in deps.items() if k not in order and v <= set(order))
    assert ready, "Circular progression dependency"
    order.extend(ready)

# Exact coarse tile geometry: connected floor, solid props, portals, and at least
# one cardinal interaction standing tile per required object.
geometry = {}
for rid, room in rooms.items():
    floor = {(x, y) for x in range(1, 8) for y in range(1, 8)}
    props = {tuple(p) for p in room["objects"].values()}
    assert len(props) == len(room["objects"])
    assert props <= floor
    portals = {tuple(e[f"{side}_port"]) for e in edges for side in ("a", "b") if e[side] == rid}
    floor = (floor - props) | portals
    start = tuple(w["initial"]["position"]) if rid == w["initial"]["room"] else min(portals)
    seen = {start}; q = deque([start])
    while q:
        x, y = q.popleft()
        for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if p in floor and p not in seen:
                seen.add(p); q.append(p)
    assert seen == floor, ("Disconnected floor", rid)
    for a in actions:
        if a["room"] == rid:
            x, y = room["objects"][a["target"]]
            assert any(p in seen for p in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))), a["id"]
    geometry[rid] = {"walkableTiles": len(floor), "solidProps": len(props),
                     "portals": len(portals), "allInteractionStandpointsReachable": True}

# Exhaustive state search includes room gates, inventory consumption, and all
# acquisition/installation orders.
initial = (w["initial"]["room"], frozenset(w["initial"]["flags"]), frozenset(w["initial"]["inventory"]))
seen = {initial}; q = deque([initial]); parents = {}; reverse = defaultdict(set)
ends = set(); reached_actions = set(); transition_count = 0
while q:
    state = q.popleft(); room, flags, items = state
    if w["terminalFlag"] in flags:
        ends.add(state); continue
    nexts = []
    for e in edges:
        if set(e["requires"]) <= flags:
            if e["a"] == room: nexts.append(((e["b"], flags, items), "walk:" + e["b"]))
            if e["b"] == room: nexts.append(((e["a"], flags, items), "walk:" + e["a"]))
    for a in actions:
        if a["room"] == room and not set(a["flags"]) <= flags and set(a["requires"]) <= flags and set(a["needs"]) <= items:
            nexts.append(((room, flags | frozenset(a["flags"]),
                           (items - frozenset(a["consume"])) | frozenset(a["grant"])), a["id"]))
            reached_actions.add(a["id"])
    for dst, label in nexts:
        transition_count += 1; reverse[dst].add(state)
        if dst not in seen:
            seen.add(dst); q.append(dst); parents[dst] = (state, label)
assert ends, "Ending unreachable"
assert reached_actions == {a["id"] for a in actions}, "Required action inaccessible"
can_finish = set(ends); q = deque(ends)
while q:
    for prev in reverse[q.popleft()]:
        if prev not in can_finish:
            can_finish.add(prev); q.append(prev)
assert can_finish == seen, ("Softlocked reachable states", len(seen - can_finish))
end = sorted(ends, key=repr)[0]; witness = []
while end != initial:
    end, label = parents[end]; witness.append(label)
witness.reverse()

report = {
    "result": "passed",
    "title": w.get("title"),
    "artDirection": w.get("artDirection"),
    "scope": "Authored symbolic progression and coarse grid; not implemented movement, visuals, save code, or a game playthrough",
    "rooms": len(rooms),
    "actions": len(actions),
    "topologicalOrder": order,
    "geometry": geometry,
    "reachableStates": len(seen),
    "transitions": transition_count,
    "endingStates": len(ends),
    "softlockedStates": len(seen - can_finish),
    "allRequiredActionsReachable": True,
    "completionWitness": witness,
}
(ROOT / "evidence/progression-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
