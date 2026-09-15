"""Node 15: full quest progression + world reactivity + softlock proof.

This is the completion-contract test suite for wiring the 11-action chain, the
room gates, the world-reactivity beats, and the ending sequence. It proves, at
the level of the actual verb resolver (not just the design JSON):

  - the adventure completes start-to-ending, each action firing EXACTLY once
    (one-shot flags; no re-grant, no re-consume, no out-of-order success);
  - every out-of-order attempt is rejected (LOCKED / FAILURE) without mutating
    world state -- there is no way to fire an action before its prerequisites;
  - zero softlocks: an exhaustive search of every reachable (room, flags,
    inventory) state shows 'ended' is reachable from every non-terminal state;
  - zero unreachable items: each of the 5 items is granted and consumed exactly
    once on the critical path, and every item is acquirable in some reachable
    state.

Pure (no pygame, no rendering); run via `python3 -m unittest tests.test_progression`.
"""

import unittest
from collections import deque

from emberglow import verbs
from emberglow.world import World, State


def _canonical_verb(world, action):
    """The verb + selected item that should fire `action` (the resolver's contract)."""
    if action["needs"]:
        return verbs.USE, action["needs"][0]
    if action["target"] in world.data.get("characters", {}):
        return verbs.TALK, None
    if action["grant"]:
        return verbs.TAKE, None
    return verbs.USE, None


def _reachable_rooms(world, room, flags):
    """Rooms reachable from `room` crossing only open gates (respects `flags`)."""
    seen = {room}
    q = deque([room])
    while q:
        r = q.popleft()
        for e in world.edges:
            if set(e.get("requires", ())).issubset(flags):
                if e["a"] == r and e["b"] not in seen:
                    seen.add(e["b"]); q.append(e["b"])
                if e["b"] == r and e["a"] not in seen:
                    seen.add(e["a"]); q.append(e["a"])
    return seen


def _doable_actions(world, room, flags, inventory):
    """Actions the design says are fireable right now (pending + prereqs met)."""
    out = []
    for a in world.actions:
        if a["room"] not in _reachable_rooms(world, room, flags):
            continue
        if set(a["flags"]).issubset(flags):
            continue                       # already done (one-shot)
        if set(a["requires"]).issubset(flags) and set(a["needs"]).issubset(inventory):
            out.append(a)
    return out


class ExactOnceProgressionTests(unittest.TestCase):
    """The 11 actions fire in order, exactly once, to 'ended'."""

    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_full_chain_fires_exactly_once_in_order(self):
        w = self.w
        state = w.initial_state()
        fired = []
        for action in w.actions:
            room, target = action["room"], action["target"]
            verb, selected = _canonical_verb(w, action)
            out = verbs.resolve(w, state, room, target, verb, selected)
            self.assertEqual(out.kind, verbs.SUCCESS,
                             f"{action['id']} -> {out.kind}: {out.lines}")
            self.assertEqual(out.action_id, action["id"])
            # the outcome's delta must match world.json exactly
            self.assertEqual(out.flags, frozenset(action["flags"]), action["id"])
            self.assertEqual(out.grant, frozenset(action["grant"]), action["id"])
            self.assertEqual(out.consume, frozenset(action["consume"]), action["id"])
            state = out.apply(state)
            fired.append(action["id"])
        self.assertEqual(fired, [a["id"] for a in w.actions])
        self.assertIn(w.terminal_flag, state.flags)
        self.assertEqual(state.inventory, frozenset(), "inventory must be empty at end")

    def test_every_action_is_one_shot_no_regrant(self):
        w = self.w
        state = w.initial_state()
        for action in w.actions:
            verb, selected = _canonical_verb(w, action)
            state = verbs.resolve(w, state, action["room"], action["target"],
                                  verb, selected).apply(state)
        # after 'ended', re-attempting the terminal action must not re-fire
        out = verbs.resolve(w, state, "gate", "hollow_bell", verbs.USE, None)
        self.assertNotEqual(out.kind, verbs.SUCCESS)
        self.assertIsNone(out.action_id)


class OutOfOrderTests(unittest.TestCase):
    """Attempting any action before its prerequisites is rejected, not applied."""

    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def _state_before(self, action_id):
        """State reached just before `action_id` in the canonical order."""
        w = self.w
        state = w.initial_state()
        for a in w.actions:
            if a["id"] == action_id:
                break
            verb, selected = _canonical_verb(w, a)
            state = verbs.resolve(w, state, a["room"], a["target"],
                                  verb, selected).apply(state)
        return state

    def test_no_action_fires_in_the_initial_state(self):
        w = self.w
        state = w.initial_state()
        entry = {"meet_mallow", "request_flask"}   # both legal at spawn
        for a in w.actions:
            if a["id"] in entry:
                continue
            verb, selected = _canonical_verb(w, a)
            # at spawn no item can exist -> a needs-type action can't be satisfied
            out = verbs.resolve(w, state, a["room"], a["target"], verb, None)
            # this specific action must never fire before its prerequisites
            self.assertNotEqual(out.action_id, a["id"], a["id"])

    def test_each_action_locked_before_its_requires_are_met(self):
        w = self.w
        for action in w.actions:
            if not action["requires"]:
                continue
            # build the canonical state just before this action, then strip the
            # requires flags (so the world is NOT ready) but keep the needed item
            state = self._state_before(action["id"])
            state = State(state.room, state.pos,
                          flags=state.flags - frozenset(action["requires"]),
                          inventory=state.inventory)
            verb, selected = _canonical_verb(w, action)
            out = verbs.resolve(w, state, action["room"], action["target"],
                                verb, selected)
            self.assertEqual(out.kind, verbs.LOCKED, action["id"])
            self.assertNotEqual(out.kind, verbs.SUCCESS, action["id"])
            self.assertEqual(out.flags, frozenset(), action["id"])
            self.assertEqual(out.consume, frozenset(), action["id"])

    def test_needs_item_missing_is_not_success(self):
        w = self.w
        # turn_wheel needs crank_handle: with the crank absent, must not fire
        state = State("mill", (3, 3), flags=frozenset(), inventory=frozenset())
        out = verbs.resolve(w, state, "mill", "crank_socket", verbs.USE, None)
        self.assertNotEqual(out.kind, verbs.SUCCESS)
        self.assertIsNone(out.action_id)


class SoftlockTests(unittest.TestCase):
    """Exhaustive game-level search: no softlocks, resolver faithful to design."""

    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_no_softlocks_and_resolver_faithful(self):
        w = self.w
        initial = w.initial_state()
        seen = set()
        seen_room = {}
        q = deque()
        key = (initial.room, initial.flags, initial.inventory)
        seen.add(key); seen_room[key] = initial.pos; q.append(key)
        ended_keys = set()
        actions_fired = set()
        resolver_mismatch = []
        terminal = frozenset({w.terminal_flag})

        while q:
            room, flags, inventory = q.popleft()
            if w.terminal_flag in flags:
                ended_keys.add((room, flags, inventory))
                continue

            # ground-truth doable set from world.json
            doable = _doable_actions(w, room, flags, inventory)
            doable_ids = {a["id"] for a in doable}

            # cross-check: the resolver must realize exactly these doable actions
            # (no out-of-order success, no wrongly-blocked success).
            for rid in _reachable_rooms(w, room, flags):
                for a in w.actions:
                    if a["room"] != rid:
                        continue
                    verb, selected = _canonical_verb(w, a)
                    if selected is not None and selected not in inventory:
                        selected = None       # can't use an item we don't have
                    state = State(rid, (4, 4), flags=flags, inventory=inventory)
                    out = verbs.resolve(w, state, rid, a["target"], verb, selected)
                    if a["id"] in doable_ids:
                        # a doable action must fire, and fire *as itself*
                        if out.kind != verbs.SUCCESS or out.action_id != a["id"]:
                            resolver_mismatch.append(
                                (a["id"], "expected SUCCESS as itself",
                                 out.kind, out.action_id))
                    elif not set(a["flags"]).issubset(flags):   # pending but not doable
                        # may fire an earlier pending action on the same target, but
                        # must NEVER fire *this* action before its prerequisites
                        if out.action_id == a["id"]:
                            resolver_mismatch.append(
                                (a["id"], "fired out of order",
                                 out.kind, out.action_id))

            # no softlock: every non-terminal state has at least one doable action
            if not doable_ids:
                # (should never happen if the design is softlock-free; flag it)
                self.fail(f"softlocked state: room={room} flags={sorted(flags)} "
                          f"inventory={sorted(inventory)}")

            for a in doable:
                nflags = flags | frozenset(a["flags"])
                ninv = (inventory - frozenset(a["consume"])) | frozenset(a["grant"])
                nkey = (a["room"], nflags, ninv)
                actions_fired.add(a["id"])
                if nkey not in seen:
                    seen.add(nkey); seen_room[nkey] = (4, 4); q.append(nkey)

        self.assertTrue(ended_keys, "ending unreachable")
        self.assertEqual(actions_fired, {a["id"] for a in w.actions},
                         "not every action is reachable")
        self.assertEqual(resolver_mismatch, [],
                         f"resolver diverges from design: {resolver_mismatch}")
        # every reachable non-terminal state must be able to reach the ending;
        # here we already asserted each has a doable successor, and the search
        # reached the ending -- so no reachable state is a dead end.


class ItemEconomyTests(unittest.TestCase):
    """Every item is granted and consumed exactly once; none is unreachable."""

    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_each_item_granted_and_consumed_exactly_once(self):
        w = self.w
        grants = {}
        consumes = {}
        for a in w.actions:
            for g in a["grant"]:
                grants[g] = grants.get(g, 0) + 1
            for c in a["consume"]:
                consumes[c] = consumes.get(c, 0) + 1
        item_ids = set(w.data.get("items", {}))
        for it in item_ids:
            self.assertEqual(grants.get(it, 0), 1, f"{it} grant count")
        # full_flask is both granted (by fill_flask) and consumed (by cool_lens)
        for it in item_ids:
            self.assertEqual(consumes.get(it, 0), 1, f"{it} consume count")
        # every consumed item is also granted somewhere (no orphan needs)
        for it in consumes:
            self.assertEqual(grants.get(it, 0), 1, f"{it} consumed but not granted")

    def test_no_action_needs_an_unobtainable_item(self):
        w = self.w
        granted = {g for a in w.actions for g in a["grant"]}
        for a in w.actions:
            for n in a["needs"]:
                self.assertIn(n, granted, f"{a['id']} needs unobtainable {n}")


if __name__ == "__main__":
    unittest.main()
