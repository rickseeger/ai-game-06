"""Explicit verb model + interaction resolution (pure, headless, no pygame).

Covers the node-5 interaction contract: the four distinct verbs, inspectable
objects (every prop has an examine line), acquisition + duplicate prevention,
valid and invalid item use (consume only on the correct target, distinct failure
otherwise), locked-vs-ready gating, bare "operate" actions, multi-line cozy
conversation progression, and a full 11-action playthrough driven end-to-end by
verbs.resolve (never by manually applying world.json actions).
"""

import unittest

from emberglow import verbs
from emberglow.world import World, State, BlockedError, NORTH, SOUTH, EAST, WEST


def _walk_to(state, world, room, target):
    """Move (via World.move) to a standpoint adjacent to `target`; return state."""
    tile = world.interaction_tiles(room, target, state.flags)[0]
    path = world.find_path(state.room, state.pos, room, tile, state.flags)
    assert path is not None, (room, target)
    for d in path:
        state = world.move(state, d)
    assert (state.room, state.pos) == (room, tile), (state.room, state.pos, room, tile)
    return state


def _verb_for(world, action):
    """The verb + selected item that should trigger `action` (generic rule)."""
    if action["needs"]:
        return verbs.USE, action["needs"][0]
    if action["target"] in world.data.get("characters", {}):
        return verbs.TALK, None
    if action["grant"]:
        return verbs.TAKE, None
    return verbs.USE, None


class VerbModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_four_verbs_are_distinct(self):
        self.assertEqual(len(set(verbs.VERBS)), 4)
        self.assertIn(verbs.EXAMINE, verbs.VERBS)
        self.assertIn(verbs.TALK, verbs.VERBS)
        self.assertIn(verbs.TAKE, verbs.VERBS)
        self.assertIn(verbs.USE, verbs.VERBS)

    def test_every_object_and_character_has_an_examine_line(self):
        w = self.w
        objects = {name for room in w.rooms.values() for name in room.objects}
        chars = set(w.data.get("characters", {}))
        for name in sorted(objects | chars):
            self.assertIn(name, verbs.EXAMINE_LINES, f"missing examine line for {name}")
            self.assertTrue(verbs.EXAMINE_LINES[name].strip(), name)

    def test_examine_returns_info_without_state_change(self):
        w = self.w
        state = w.initial_state()
        for target in ("hill_stair", "mural", "mallow", "crank_socket"):
            room = next(r for r, room in w.rooms.items() if target in room.objects)
            out = verbs.resolve(w, state, room, target, verbs.EXAMINE, None)
            self.assertEqual(out.kind, verbs.INFO, target)
            self.assertTrue(out.lines and out.lines[0][1], target)
            self.assertEqual(out.flags, frozenset())
            self.assertEqual(out.grant, frozenset())
            self.assertEqual(out.consume, frozenset())
            self.assertIsNone(out.action_id)

    def test_talk_to_non_character_fails(self):
        w = self.w
        state = w.initial_state()
        out = verbs.resolve(w, state, "gate", "hollow_bell", verbs.TALK, None)
        self.assertEqual(out.kind, verbs.FAILURE)
        self.assertIsNone(out.action_id)


class AcquisitionAndDuplicatePreventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_meet_mallow_grants_crank_once(self):
        w = self.w
        state = _walk_to(w.initial_state(), w, "gate", "mallow")
        out = verbs.resolve(w, state, "gate", "mallow", verbs.TALK, None)
        self.assertEqual(out.kind, verbs.SUCCESS)
        self.assertEqual(out.action_id, "meet_mallow")
        self.assertEqual(out.grant, frozenset({"crank_handle"}))
        self.assertIn("met_mallow", out.flags)
        state = out.apply(state)
        self.assertIn("crank_handle", state.inventory)
        # duplicate prevention: talking again does not re-grant
        again = verbs.resolve(w, state, "gate", "mallow", verbs.TALK, None)
        self.assertNotEqual(again.kind, verbs.SUCCESS)
        self.assertNotEqual(again.action_id, "meet_mallow")
        self.assertEqual(state.inventory, frozenset({"crank_handle"}))

    def test_request_flask_grants_flask_once(self):
        w = self.w
        state = _walk_to(w.initial_state(), w, "market", "bramble")
        out = verbs.resolve(w, state, "market", "bramble", verbs.TALK, None)
        self.assertEqual(out.action_id, "request_flask")
        self.assertEqual(out.grant, frozenset({"glass_flask"}))
        state = out.apply(state)
        again = verbs.resolve(w, state, "market", "bramble", verbs.TALK, None)
        self.assertNotEqual(again.action_id, "request_flask")

    def test_take_seed_grants_once_and_second_take_fails(self):
        w = self.w
        state = State("greenhouse", (4, 4), flags=frozenset({"water_flowing"}))
        out = verbs.resolve(w, state, "greenhouse", "ember_seed", verbs.TAKE, None)
        self.assertEqual(out.action_id, "take_seed")
        self.assertEqual(out.grant, frozenset({"ember_seed"}))
        state = out.apply(state)
        again = verbs.resolve(w, state, "greenhouse", "ember_seed", verbs.TAKE, None)
        self.assertEqual(again.kind, verbs.FAILURE)
        self.assertNotIn("ember_seed", again.grant)


class ItemUseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_use_crank_on_socket_succeeds_and_consumes(self):
        w = self.w
        state = State("mill", (3, 3), inventory=frozenset({"crank_handle"}))
        out = verbs.resolve(w, state, "mill", "crank_socket", verbs.USE, "crank_handle")
        self.assertEqual(out.kind, verbs.SUCCESS)
        self.assertEqual(out.action_id, "turn_wheel")
        self.assertEqual(out.consume, frozenset({"crank_handle"}))
        self.assertIn("water_flowing", out.flags)
        state = out.apply(state)
        self.assertNotIn("crank_handle", state.inventory)
        self.assertIn("water_flowing", state.flags)

    def test_use_wrong_item_on_socket_fails_without_consume(self):
        w = self.w
        state = State("mill", (3, 3), inventory=frozenset({"glass_flask"}))
        out = verbs.resolve(w, state, "mill", "crank_socket", verbs.USE, "glass_flask")
        self.assertEqual(out.kind, verbs.FAILURE)
        self.assertIsNone(out.action_id)
        self.assertEqual(out.consume, frozenset())
        self.assertNotIn("water_flowing", out.flags)

    def test_use_valid_item_before_world_ready_is_locked(self):
        w = self.w
        state = State("mill", (5, 3), inventory=frozenset({"glass_flask"}))
        out = verbs.resolve(w, state, "mill", "water_spout", verbs.USE, "glass_flask")
        self.assertEqual(out.kind, verbs.LOCKED)
        self.assertEqual(out.consume, frozenset())
        self.assertNotIn("flask_filled", out.flags)

    def test_use_on_socket_with_no_item_fails(self):
        w = self.w
        state = State("mill", (3, 3), inventory=frozenset())
        out = verbs.resolve(w, state, "mill", "crank_socket", verbs.USE, None)
        self.assertEqual(out.kind, verbs.FAILURE)
        self.assertIn("Crank Handle", out.lines[0][1])

    def test_fill_flask_after_water_flowing_succeeds(self):
        w = self.w
        state = State("mill", (5, 3), flags=frozenset({"water_flowing"}),
                      inventory=frozenset({"glass_flask"}))
        out = verbs.resolve(w, state, "mill", "water_spout", verbs.USE, "glass_flask")
        self.assertEqual(out.action_id, "fill_flask")
        self.assertEqual(out.grant, frozenset({"full_flask"}))
        self.assertEqual(out.consume, frozenset({"glass_flask"}))

    def test_cool_lens_uses_full_flask_on_bramble(self):
        w = self.w
        state = State("market", (3, 3), inventory=frozenset({"full_flask"}),
                      flags=frozenset({"flask_received"}))
        out = verbs.resolve(w, state, "market", "bramble", verbs.USE, "full_flask")
        self.assertEqual(out.action_id, "cool_lens")
        self.assertEqual(out.grant, frozenset({"lens"}))
        self.assertEqual(out.consume, frozenset({"full_flask"}))

    def test_bare_operate_kindles_when_ready(self):
        w = self.w
        state = State("crown", (4, 7), flags=frozenset({"stair_open", "lens_mounted", "seed_planted"}),
                      inventory=frozenset())
        out = verbs.resolve(w, state, "crown", "focus_wheel", verbs.USE, None)
        self.assertEqual(out.action_id, "kindle_lantern")
        self.assertIn("lantern_lit", out.flags)

    def test_bare_operate_locked_before_lens_and_seed(self):
        w = self.w
        state = State("crown", (4, 7), flags=frozenset({"stair_open"}), inventory=frozenset())
        out = verbs.resolve(w, state, "crown", "focus_wheel", verbs.USE, None)
        self.assertEqual(out.kind, verbs.LOCKED)

    def test_bare_operate_rings_bell(self):
        w = self.w
        state = State("gate", (5, 3), flags=frozenset({"lantern_lit"}), inventory=frozenset())
        out = verbs.resolve(w, state, "gate", "hollow_bell", verbs.USE, None)
        self.assertEqual(out.action_id, "ring_bell")
        self.assertIn("ended", out.flags)


class ContextualInteractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_interact_on_character_talks(self):
        w = self.w
        state = _walk_to(w.initial_state(), w, "gate", "mallow")
        out = verbs.resolve(w, state, "gate", "mallow", verbs.INTERACT, None)
        self.assertEqual(out.action_id, "meet_mallow")

    def test_interact_on_takeable_takes(self):
        w = self.w
        state = State("greenhouse", (4, 4), flags=frozenset({"water_flowing"}))
        out = verbs.resolve(w, state, "greenhouse", "ember_seed", verbs.INTERACT, None)
        self.assertEqual(out.action_id, "take_seed")

    def test_interact_on_socket_uses_selected_item(self):
        w = self.w
        state = State("mill", (3, 3), inventory=frozenset({"crank_handle"}))
        out = verbs.resolve(w, state, "mill", "crank_socket", verbs.INTERACT, "crank_handle")
        self.assertEqual(out.action_id, "turn_wheel")


class ConversationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_conversation_is_multiline_and_advances(self):
        lines = verbs.ACTION_LINES["meet_mallow"]
        self.assertGreater(len(lines), 1)
        for speaker, text in lines:
            self.assertTrue(speaker and text)
        conv = verbs.Conversation(list(lines))
        seen = []
        while not conv.done:
            seen.append((conv.speaker, conv.text))
            conv.advance()
        self.assertEqual(seen, lines)

    def test_mallow_conversation_progresses(self):
        w = self.w
        state = _walk_to(w.initial_state(), w, "gate", "mallow")
        out = verbs.resolve(w, state, "gate", "mallow", verbs.TALK, None)
        self.assertEqual(out.action_id, "meet_mallow")
        self.assertEqual(out.lines[0][0], "Mallow")
        state = out.apply(state)
        # after meeting, talk again -> open_stair is pending but not ready: locked
        # (a distinct "not yet" line, no second crank grant)
        locked = verbs.resolve(w, state, "gate", "mallow", verbs.TALK, None)
        self.assertEqual(locked.kind, verbs.LOCKED)
        self.assertIsNone(locked.action_id)
        self.assertIn("lens", locked.lines[0][1])
        # with lens_ready + seed_taken, talk -> open_stair (success)
        state2 = State(state.room, state.pos, flags=state.flags | frozenset({"lens_ready", "seed_taken"}),
                       inventory=state.inventory)
        opened = verbs.resolve(w, state2, "gate", "mallow", verbs.TALK, None)
        self.assertEqual(opened.action_id, "open_stair")
        state3 = opened.apply(state2)
        # after the stair is open, talk again -> hint (info, no pending action)
        hint = verbs.resolve(w, state3, "gate", "mallow", verbs.TALK, None)
        self.assertEqual(hint.kind, verbs.INFO)
        self.assertNotEqual(hint.lines, out.lines)

    def test_bramble_conversation_progresses(self):
        w = self.w
        state = _walk_to(w.initial_state(), w, "market", "bramble")
        out = verbs.resolve(w, state, "market", "bramble", verbs.TALK, None)
        self.assertEqual(out.action_id, "request_flask")
        self.assertEqual(out.lines[0][0], "Bramble")
        state = out.apply(state)
        hint = verbs.resolve(w, state, "market", "bramble", verbs.TALK, None)
        self.assertEqual(hint.kind, verbs.INFO)
        # with full_flask in hand, the hint directs the player to use it here
        state2 = State(state.room, state.pos, flags=state.flags, inventory=frozenset({"full_flask"}))
        hint2 = verbs.resolve(w, state2, "market", "bramble", verbs.TALK, None)
        self.assertIn("Use it here", hint2.lines[0][1])


class FullPlaythroughViaVerbsTests(unittest.TestCase):
    """The verb model alone must drive the whole 11-action progression to 'ended'."""

    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_full_11_action_playthrough_via_verbs(self):
        w = self.w
        state = w.initial_state()
        performed = []
        for action in w.actions:
            room, target = action["room"], action["target"]
            verb, selected = _verb_for(w, action)
            state = _walk_to(state, w, room, target)
            out = verbs.resolve(w, state, room, target, verb, selected)
            self.assertEqual(out.kind, verbs.SUCCESS,
                             f"{action['id']} -> {out.kind}: {out.lines}")
            self.assertEqual(out.action_id, action["id"])
            # the outcome's flag/inventory delta must match world.json exactly
            self.assertEqual(out.flags, frozenset(action["flags"]), action["id"])
            self.assertEqual(out.grant, frozenset(action["grant"]), action["id"])
            self.assertEqual(out.consume, frozenset(action["consume"]), action["id"])
            state = out.apply(state)
            performed.append(action["id"])
        self.assertEqual(performed, [a["id"] for a in w.actions])
        self.assertIn(w.terminal_flag, state.flags)
        self.assertEqual(state.inventory, frozenset())

    def test_wrong_order_is_prevented_by_requires(self):
        w = self.w
        # try to kindle before mounting/planting -> locked, not success
        state = State("crown", (4, 7), flags=frozenset({"stair_open"}), inventory=frozenset())
        out = verbs.resolve(w, state, "crown", "focus_wheel", verbs.USE, None)
        self.assertEqual(out.kind, verbs.LOCKED)
        self.assertNotIn("lantern_lit", out.flags)


if __name__ == "__main__":
    unittest.main()
