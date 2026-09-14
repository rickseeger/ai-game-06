"""World geometry + traversal contract (rendering-independent, headless).

Covers: legal movement, blocked movement, boundary cases, room transitions,
spawn validity, and reachability of every progression-critical location. No
pygame import and no display required; runs under SDL_VIDEODRIVER=dummy just like
the rest of the suite.
"""

import unittest

from emberglow.world import (
    World, State, BlockedError, NORTH, SOUTH, EAST, WEST, DIRECTIONS,
)
from emberglow import worldmap


def all_flags(world):
    return world.all_flags


class WorldLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_five_rooms_on_9x9(self):
        self.assertEqual(set(self.w.rooms), {"gate", "market", "mill", "greenhouse", "crown"})
        for room in self.w.rooms.values():
            self.assertEqual(room.size, 9)

    def test_obstacles_are_interior_and_disjoint_from_objects(self):
        for rid, room in self.w.rooms.items():
            for cell in room.obstacles:
                self.assertTrue(self.w._interior(cell), (rid, cell))
            for name, cell in room.objects.items():
                self.assertTrue(self.w._interior(cell), (rid, name, cell))
                self.assertNotIn(cell, room.obstacles, (rid, name))

    def test_obstacle_map_covers_every_room(self):
        self.assertEqual(set(worldmap.OBSTACLES), set(self.w.rooms))


class SpawnAndBlockedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_initial_spawn_is_valid(self):
        w = self.w
        self.assertEqual(w.initial_room, "gate")
        self.assertEqual(w.initial_pos, (4, 6))
        self.assertTrue(w.walkable("gate", (4, 6)))
        self.assertFalse(w.is_solid("gate", (4, 6)))
        self.assertTrue(w.in_bounds("gate", w.initial_pos))

    def test_every_object_and_obstacle_is_impassable(self):
        w = self.w
        for rid, room in w.rooms.items():
            for cell in room.blocked:
                self.assertTrue(w.is_solid(rid, cell), (rid, cell))
                self.assertFalse(w.walkable(rid, cell), (rid, cell))
                self.assertFalse(w.walkable(rid, cell, all_flags(w)), (rid, cell))

    def test_blocked_move_raises_and_leaves_state_unchanged(self):
        w = self.w
        state = w.initial_state()
        # The SE cottage (6,6) blocks the cell east of a known walkable cell (5,6).
        cottage_cell = (6, 6)
        self.assertTrue(w.is_solid("gate", cottage_cell))
        # stand at (5,6), one step west of the cottage
        s = State("gate", (5, 6))
        self.assertFalse(w.can_move(s, EAST))
        with self.assertRaises(BlockedError):
            w.move(s, EAST)
        # state unchanged (State is immutable; just confirm no exception alters it)
        self.assertEqual((s.room, s.pos), ("gate", (5, 6)))

    def test_out_of_bounds_is_blocked(self):
        w = self.w
        s = State("gate", (1, 1))
        self.assertFalse(w.can_move(s, NORTH))   # (1,0) is ring, not a portal
        self.assertFalse(w.can_move(s, WEST))    # (0,1) is ring
        with self.assertRaises(BlockedError):
            w.move(s, WEST)

    def test_non_portal_ring_is_impassable(self):
        w = self.w
        # every non-portal ring cell must be impassable in every room
        for rid, room in w.rooms.items():
            for x in range(9):
                for y in range(9):
                    on_ring = x in (0, 8) or y in (0, 8)
                    if on_ring and (x, y) not in room.portal_cells:
                        self.assertFalse(w.walkable(rid, (x, y), all_flags(w)),
                                         (rid, (x, y)))


class MovementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_legal_move_updates_position(self):
        w = self.w
        s = w.initial_state()
        s2 = w.move(s, WEST)       # (4,6)->(3,6) walkable
        self.assertEqual(s2.pos, (3, 6))
        self.assertEqual(s2.room, "gate")

    def test_all_cardinal_directions_from_spawn(self):
        w = self.w
        s = w.initial_state()
        reachable = []
        for d in DIRECTIONS:
            if w.can_move(s, d):
                reachable.append(w.move(s, d).pos)
        # spawn neighbours: (5,6) E, (3,6) W, (4,5) N, (4,7) S -- all open
        self.assertEqual(sorted(reachable), [(3, 6), (4, 5), (4, 7), (5, 6)])

    def test_neighbors_match_manual_checks(self):
        w = self.w
        s = w.initial_state()
        ns = w.neighbors("gate", s.pos)
        self.assertIn((5, 6), ns)
        self.assertNotIn((4, 6), ns)   # self not a neighbour


class TransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_gate_to_market_round_trip(self):
        w = self.w
        # approach gate's east portal from (7,4), step east -> land market (1,4)
        s = State("gate", (7, 4))
        s2 = w.move(s, EAST)
        self.assertEqual((s2.room, s2.pos), ("market", (1, 4)))
        # walk back west onto market's west portal -> land gate (7,4)
        s3 = w.move(s2, WEST)
        self.assertEqual((s3.room, s3.pos), ("gate", (7, 4)))

    def test_market_to_mill_round_trip(self):
        w = self.w
        s = State("market", (4, 1))
        s2 = w.move(s, NORTH)              # market north portal -> mill (4,7)
        self.assertEqual((s2.room, s2.pos), ("mill", (4, 7)))
        s3 = w.move(s2, SOUTH)             # mill south portal -> market (4,1)
        self.assertEqual((s3.room, s3.pos), ("market", (4, 1)))

    def test_closed_portal_blocks_then_opens(self):
        w = self.w
        # mill east portal (8,4) -> greenhouse, requires water_flowing
        s = State("mill", (7, 4))
        self.assertFalse(w.walkable("mill", (8, 4), frozenset()))
        self.assertFalse(w.can_move(s, EAST))
        with self.assertRaises(BlockedError):
            w.move(s, EAST)
        # with the flag, it opens and transitions
        s2 = State("mill", (7, 4), flags=frozenset({"water_flowing"}))
        self.assertTrue(w.walkable("mill", (8, 4), s2.flags))
        s3 = w.move(s2, EAST)
        self.assertEqual((s3.room, s3.pos), ("greenhouse", (1, 4)))

    def test_crown_portal_requires_stair_open(self):
        w = self.w
        s = State("gate", (4, 1))
        self.assertFalse(w.can_move(s, NORTH))          # closed
        s2 = State("gate", (4, 1), flags=frozenset({"stair_open"}))
        self.assertTrue(w.can_move(s2, NORTH))
        s3 = w.move(s2, NORTH)
        self.assertEqual((s3.room, s3.pos), ("crown", (4, 7)))

    def test_every_portal_landing_cell_is_walkable(self):
        w = self.w
        for (room, cell), portal in w._portal_at.items():
            from emberglow.world import _inward
            landing = _inward(portal.dest_cell, w.size)
            self.assertTrue(w.walkable(portal.dest_room, landing, all_flags(w)),
                            (room, cell, portal.dest_room, landing))


class ReachabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_validate_reports_ok(self):
        report = self.w.validate()
        self.assertTrue(report["ok"], report["problems"])

    def test_no_cell_traps_the_player(self):
        w = self.w
        reached = w.reachable_state_space(w.initial_room, w.initial_pos, all_flags(w))
        interior_floor = {(rid, c) for rid in w.rooms for c in w._cells()
                          if w._interior(c) and w.walkable(rid, c, all_flags(w))}
        self.assertEqual(interior_floor, reached)

    def test_gated_rooms_locked_without_flags(self):
        w = self.w
        no_flags = {r for r, _ in w.reachable_state_space(w.initial_room, w.initial_pos, frozenset())}
        self.assertIn("gate", no_flags)
        self.assertIn("market", no_flags)
        self.assertIn("mill", no_flags)
        self.assertNotIn("greenhouse", no_flags)
        self.assertNotIn("crown", no_flags)

    def test_all_rooms_reachable_with_flags(self):
        w = self.w
        reached = {r for r, _ in w.reachable_state_space(w.initial_room, w.initial_pos, all_flags(w))}
        self.assertEqual(reached, set(w.rooms))

    def test_every_object_has_reachable_standing_tile(self):
        w = self.w
        for rid, room in w.rooms.items():
            for name in room.objects:
                tiles = w.interaction_tiles(rid, name, all_flags(w))
                self.assertTrue(tiles, (rid, name))
                self.assertIsNotNone(
                    w.find_path(w.initial_room, w.initial_pos, rid, tiles[0], all_flags(w)),
                    (rid, name))

    def test_every_portal_is_usable(self):
        w = self.w
        for rid, room in w.rooms.items():
            for portal in room.portals:
                self.assertTrue(w.walkable(rid, portal.cell, all_flags(w)))
                # you can step onto it from inside the room
                from emberglow.world import _inward
                inside = _inward(portal.cell, w.size)
                self.assertIsNotNone(
                    w.find_path(w.initial_room, w.initial_pos, rid, inside, all_flags(w)),
                    (rid, portal.cell))


class ProgressionWalkthroughTests(unittest.TestCase):
    """The traversal layer must support the full 11-action progression on foot."""

    @classmethod
    def setUpClass(cls):
        cls.w = World()

    def test_full_progression_walkthrough(self):
        w = self.w
        state = w.initial_state()
        for action in w.actions:
            room, target = action["room"], action["target"]
            self.assertLessEqual(set(action["requires"]), set(state.flags), action["id"])
            self.assertLessEqual(set(action["needs"]), set(state.inventory), action["id"])
            tile = w.interaction_tiles(room, target, state.flags)[0]
            path = w.find_path(state.room, state.pos, room, tile, state.flags)
            self.assertIsNotNone(path, f"cannot reach {action['id']} ({room}.{target})")
            for d in path:
                state = w.move(state, d)
            self.assertEqual((state.room, state.pos), (room, tile), action["id"])
            # perform the action: flags and inventory change, position stays
            state = State(
                state.room, state.pos,
                flags=state.flags | frozenset(action["flags"]),
                inventory=(state.inventory - frozenset(action["consume"])) | frozenset(action["grant"]),
            )
        self.assertIn(w.terminal_flag, state.flags)

    def test_every_action_target_is_reachable_from_spawn_at_its_stage(self):
        w = self.w
        # Progressive flags: at each action, the room must be reachable with the
        # flags produced by all prior actions.
        flags = frozenset()
        inventory = frozenset()
        for action in w.actions:
            target_cell = w.object_position(action["room"], action["target"])
            tiles = w.interaction_tiles(action["room"], action["target"], flags)
            self.assertTrue(tiles, action["id"])
            self.assertIsNotNone(
                w.find_path(w.initial_room, w.initial_pos, action["room"], tiles[0], flags),
                action["id"])
            flags = flags | frozenset(action["flags"])
            inventory = (inventory - frozenset(action["consume"])) | frozenset(action["grant"])


if __name__ == "__main__":
    unittest.main()
