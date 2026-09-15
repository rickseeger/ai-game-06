"""Deterministic input-mapping + press/release controller tests (headless).

Covers: every key/escape alias maps to its action; WASD and arrows both drive all
four grid directions; press/release semantics (holding moves, releasing stops, no
stuck movement); blocked moves turn to face without moving; context-sensitive
target selection is unambiguous; interaction performs the target's action through
the application input path; dialogue opens and dismisses; movement never triggers
an unintended action. SDL dummy driver, no display, no vision.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import unittest

import pygame

from emberglow import inputmap, verbs
from emberglow.game import Game, MOVE_INTERVAL
from emberglow.world import State

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


def process(game):
    """Drain the real SDL event queue into the controller (no ticking)."""
    for e in pygame.event.get():
        game.handle_event(e)


def pump(game, n, dt=MOVE_INTERVAL):
    for _ in range(n):
        process(game)
        game.tick(dt)


class KeyMappingTests(unittest.TestCase):
    def test_every_binding_maps_to_its_action(self):
        self.assertEqual(len(inputmap.KEY_TO_ACTION), 19)
        for key, action in inputmap.KEY_TO_ACTION.items():
            self.assertEqual(inputmap.action_for_key(key), action)

    def test_verb_bindings(self):
        self.assertEqual(inputmap.action_for_key(pygame.K_x), inputmap.EXAMINE)
        self.assertEqual(inputmap.action_for_key(pygame.K_t), inputmap.TALK)
        self.assertEqual(inputmap.action_for_key(pygame.K_g), inputmap.TAKE)
        self.assertEqual(inputmap.action_for_key(pygame.K_u), inputmap.USE)
        self.assertEqual(inputmap.action_for_key(pygame.K_TAB), inputmap.NEXT_ITEM)
        self.assertEqual(inputmap.action_for_key(pygame.K_LEFTBRACKET), inputmap.PREV_ITEM)

    def test_arrows_and_wasd_cover_all_four_directions(self):
        arrows = {pygame.K_UP: inputmap.MOVE_NORTH, pygame.K_DOWN: inputmap.MOVE_SOUTH,
                  pygame.K_RIGHT: inputmap.MOVE_EAST, pygame.K_LEFT: inputmap.MOVE_WEST}
        wasd = {pygame.K_w: inputmap.MOVE_NORTH, pygame.K_s: inputmap.MOVE_SOUTH,
                pygame.K_d: inputmap.MOVE_EAST, pygame.K_a: inputmap.MOVE_WEST}
        for table in (arrows, wasd):
            for key, action in table.items():
                self.assertEqual(inputmap.action_for_key(key), action)
            self.assertEqual(set(table.values()), set(inputmap.MOVE_ACTIONS))

    def test_interact_aliases(self):
        for key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
            self.assertEqual(inputmap.action_for_key(key), inputmap.INTERACT)

    def test_escape_dismiss_and_q_quit(self):
        self.assertEqual(inputmap.action_for_key(pygame.K_ESCAPE), inputmap.DISMISS)
        self.assertEqual(inputmap.action_for_key(pygame.K_q), inputmap.QUIT)

    def test_unmapped_key_is_none(self):
        self.assertIsNone(inputmap.action_for_key(pygame.K_9))
        self.assertIsNone(inputmap.action_for_key(pygame.K_F1))

    def test_direction_vectors_are_correct_and_distinct(self):
        self.assertEqual(inputmap.direction_for(inputmap.MOVE_NORTH), (0, -1))
        self.assertEqual(inputmap.direction_for(inputmap.MOVE_SOUTH), (0, 1))
        self.assertEqual(inputmap.direction_for(inputmap.MOVE_EAST), (1, 0))
        self.assertEqual(inputmap.direction_for(inputmap.MOVE_WEST), (-1, 0))
        self.assertEqual(len(set(inputmap.ACTION_DIRECTION.values())), 4)
        self.assertIsNone(inputmap.direction_for(inputmap.INTERACT))

    def test_is_move(self):
        for a in inputmap.MOVE_ACTIONS:
            self.assertTrue(inputmap.is_move(a))
        self.assertFalse(inputmap.is_move(inputmap.INTERACT))
        self.assertFalse(inputmap.is_move(inputmap.DISMISS))


class InputControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.event.clear()

    def setUp(self):
        pygame.event.clear()
        self.game = Game()

    def _hold(self, action, ticks, dt=MOVE_INTERVAL):
        post(KEY[action], True)
        pump(self.game, ticks, dt)
        post(KEY[action], False)
        pump(self.game, 1, dt)

    def test_hold_move_then_release_stops(self):
        g = self.game
        self._hold(inputmap.MOVE_WEST, 1)          # (4,6) -> (3,6)
        self.assertEqual(g.state.pos, (3, 6))
        pos = g.state.pos
        pump(g, 8)                                  # nothing held -> must not move
        self.assertEqual(g.state.pos, pos)
        self.assertNotIn(inputmap.MOVE_WEST, g._held)

    def test_hold_produces_continuous_movement(self):
        g = self.game
        self._hold(inputmap.MOVE_NORTH, 3)          # (4,6) -> (4,3)
        self.assertEqual(g.state.pos, (4, 3))

    def test_wasd_alias_moves(self):
        g = self.game
        post(pygame.K_d, True); pump(g, 1)
        post(pygame.K_d, False); pump(g, 1)
        self.assertEqual(g.state.pos, (5, 6))

    def test_release_clears_held_keys(self):
        g = self.game
        post(KEY[inputmap.MOVE_EAST], True)
        process(g)
        self.assertIn(inputmap.MOVE_EAST, g._held)
        post(KEY[inputmap.MOVE_EAST], False)
        process(g)
        self.assertNotIn(inputmap.MOVE_EAST, g._held)

    def test_blocked_move_sets_facing_without_moving(self):
        g = self.game
        self._hold(inputmap.MOVE_WEST, 1)           # -> (3,6)
        self._hold(inputmap.MOVE_NORTH, 3)          # -> (3,3)
        self._hold(inputmap.MOVE_WEST, 1)           # blocked by Mallow (2,3)
        self.assertEqual(g.state.pos, (3, 3))
        self.assertEqual(g.facing, (-1, 0))
        self.assertEqual(g.target, "mallow")

    def test_target_selection_is_unambiguous(self):
        g = self.game
        self._hold(inputmap.MOVE_WEST, 1)           # face west into empty (2,6)
        self.assertIsNone(g.target)
        # now face into a real object and confirm exactly one target
        self._hold(inputmap.MOVE_NORTH, 3)          # -> (3,3)
        self._hold(inputmap.MOVE_WEST, 1)           # face Mallow
        self.assertEqual(g.target, "mallow")

    def test_interact_performs_action_and_opens_dialogue(self):
        g = self.game
        self._hold(inputmap.MOVE_WEST, 1)
        self._hold(inputmap.MOVE_NORTH, 3)
        self._hold(inputmap.MOVE_WEST, 1)           # face Mallow
        post(KEY[inputmap.INTERACT], True); pump(g, 1)
        post(KEY[inputmap.INTERACT], False); pump(g, 1)
        self.assertEqual(g.dialogue["speaker"], "Mallow")
        self.assertIn("crank_handle", g.state.inventory)
        self.assertIn("met_mallow", g.state.flags)

    def test_escape_dismisses_dialogue(self):
        g = self.game
        g._open_dialogue([("Mallow", "test line")])
        self.assertIsNotNone(g.dialogue)
        post(KEY[inputmap.DISMISS], True); pump(g, 1)
        post(KEY[inputmap.DISMISS], False); pump(g, 1)
        self.assertIsNone(g.dialogue)

    def test_movement_never_triggers_interaction(self):
        g = self.game
        self._hold(inputmap.MOVE_WEST, 1)
        self._hold(inputmap.MOVE_NORTH, 3)
        self.assertIsNone(g.dialogue)
        self.assertEqual(g.state.flags, frozenset())
        self.assertEqual(g.state.inventory, frozenset())

    def test_interact_with_no_target_does_nothing(self):
        g = self.game                      # spawn faces south -> (4,7) empty
        post(KEY[inputmap.INTERACT], True); pump(g, 1)
        post(KEY[inputmap.INTERACT], False); pump(g, 1)
        self.assertIsNone(g.dialogue)
        self.assertEqual(g.state.flags, frozenset())
        self.assertEqual(g.state.inventory, frozenset())


class VerbInputTests(unittest.TestCase):
    """Explicit verbs + inventory selection, driven through the real input path."""

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.event.clear()

    def setUp(self):
        pygame.event.clear()
        self.game = Game()

    def test_tab_cycles_inventory_selection(self):
        g = self.game
        g.state = State("gate", (4, 6), inventory=frozenset({"crank_handle", "glass_flask", "lens"}))
        g.selected_index = 0
        self.assertEqual(g.selected_item(), "crank_handle")
        post(pygame.K_TAB, True); pump(g, 1)
        post(pygame.K_TAB, False); pump(g, 1)
        self.assertEqual(g.selected_item(), "glass_flask")
        post(pygame.K_TAB, True); pump(g, 1)
        post(pygame.K_TAB, False); pump(g, 1)
        self.assertEqual(g.selected_item(), "lens")
        post(pygame.K_TAB, True); pump(g, 1)
        post(pygame.K_TAB, False); pump(g, 1)
        self.assertEqual(g.selected_item(), "crank_handle")   # wraps around

    def test_prev_item_cycles_backwards(self):
        g = self.game
        g.state = State("gate", (4, 6), inventory=frozenset({"crank_handle", "glass_flask"}))
        g.selected_index = 0
        post(pygame.K_LEFTBRACKET, True); pump(g, 1)
        post(pygame.K_LEFTBRACKET, False); pump(g, 1)
        self.assertEqual(g.selected_item(), "glass_flask")

    def test_use_key_consumes_item_on_correct_target(self):
        g = self.game
        g.state = State("mill", (3, 3), inventory=frozenset({"crank_handle"}))
        g._set_facing((-1, 0))                    # face crank socket (2,3)
        self.assertEqual(g.target, "crank_socket")
        post(pygame.K_u, True); pump(g, 1)
        post(pygame.K_u, False); pump(g, 1)
        self.assertIn("water_flowing", g.state.flags)
        self.assertNotIn("crank_handle", g.state.inventory)
        self.assertEqual(g.dialogue.tone, verbs.SUCCESS)

    def test_use_key_wrong_item_fails_without_consume(self):
        g = self.game
        g.state = State("mill", (3, 3), inventory=frozenset({"glass_flask"}))
        g._set_facing((-1, 0))                    # face crank socket (2,3)
        post(pygame.K_u, True); pump(g, 1)
        post(pygame.K_u, False); pump(g, 1)
        self.assertNotIn("water_flowing", g.state.flags)
        self.assertIn("glass_flask", g.state.inventory)
        self.assertEqual(g.dialogue.tone, verbs.FAILURE)

    def test_examine_key_opens_info_dialogue(self):
        g = self.game
        g._set_facing((-1, 0))                    # from (4,6) faces (3,6) empty
        g.state = State("gate", (3, 3))
        g._set_facing((-1, 0))                    # face Mallow (2,3)
        post(pygame.K_x, True); pump(g, 1)
        post(pygame.K_x, False); pump(g, 1)
        self.assertEqual(g.dialogue.tone, verbs.INFO)
        self.assertIn("Mallow", g.dialogue.text)
        self.assertEqual(g.state.flags, frozenset())

    def test_take_key_grants_seed(self):
        g = self.game
        g.state = State("greenhouse", (4, 4), flags=frozenset({"water_flowing"}))
        g._set_facing((0, -1))                    # face ember_seed (4,3)
        self.assertEqual(g.target, "ember_seed")
        post(pygame.K_g, True); pump(g, 1)
        post(pygame.K_g, False); pump(g, 1)
        self.assertIn("ember_seed", g.state.inventory)
        self.assertIn("seed_taken", g.state.flags)


if __name__ == "__main__":
    unittest.main()
