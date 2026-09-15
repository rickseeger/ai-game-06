"""G13 node 19 -- Lantern Crown room: scene composition + render smoke tests.

Headless (offscreen surfaces only, no display). Verifies the crown room is
authored to match node 2/16/17/18's scene contract: the seed cradle, lens mount
and focus wheel sit at their world object cells, the lantern-crown tree and the
rocky ridge sit at their worldmap obstacle cells, every prop kind resolves to a
sprite, and the room renders deterministically without errors. The
seed_planted / lens_mounted / lantern_lit beats are also asserted here.
"""

import os
import unittest

# headless: no display / no sound card (offscreen surfaces only)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from emberglow.scene import build_room_crown, render_room, layout
from emberglow.sprites import get_sprite
from emberglow.world import World
from emberglow import worldreact


class CrownSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.room = build_room_crown()
        self.world = World()

    def tearDown(self):
        pygame.quit()

    def _prop_at(self, kind, gx, gy):
        return next(p for p in self.room.props if p.kind == kind
                    and p.gx == gx and p.gy == gy)

    def test_room_identity(self):
        self.assertEqual(self.room.grid, 9)
        self.assertEqual(self.room.title, "Lantern Crown")
        self.assertIn("lantern", self.room.subtitle)

    def test_interactables_on_object_cells(self):
        self.assertTrue(self._prop_at("seed_cradle", 3, 3).interactable)
        self.assertTrue(self._prop_at("lens_mount", 5, 3).interactable)
        self.assertTrue(self._prop_at("focus_wheel", 4, 6).interactable)

    def test_ridge_and_tree_raised_heights(self):
        for x in range(1, 8):
            self.assertIn((x, 1), self.room.heights)
        self.assertIn((3, 2), self.room.heights)
        self.assertIn((4, 2), self.room.heights)
        self.assertTrue(all(h == 1 for h in self.room.heights.values()))

    def test_interactables_align_with_world_objects(self):
        objects = self.world.rooms["crown"].objects
        self.assertEqual((3, 3), objects["seed_cradle"])
        self.assertEqual((5, 3), objects["lens_mount"])
        self.assertEqual((4, 6), objects["focus_wheel"])
        self._prop_at("seed_cradle", 3, 3)
        self._prop_at("lens_mount", 5, 3)
        self._prop_at("focus_wheel", 4, 6)

    def test_obstacle_props_align_with_obstacles(self):
        obstacles = set(self.world.rooms["crown"].obstacles)
        tree = {(p.gx, p.gy) for p in self.room.props if p.kind == "lantern_tree"}
        self.assertLessEqual(tree, obstacles)
        self.assertIn((4, 2), tree)
        ridge = {(p.gx, p.gy) for p in self.room.props if p.kind == "ridge"}
        self.assertLessEqual(ridge, obstacles)

    def test_every_prop_kind_has_a_sprite(self):
        kinds = {p.kind for p in self.room.props}
        for kind in kinds:
            spr = get_sprite(kind, 0, 0)
            self.assertGreater(spr.get_width(), 0, kind)
            self.assertGreater(spr.get_height(), 0, kind)

    def test_no_static_player_prop(self):
        self.assertNotIn("player", {p.kind for p in self.room.props})

    def test_renders_without_errors_and_is_not_blank(self):
        ox, oy = layout(self.room, 1280, 720)
        surf = pygame.Surface((1280, 720))
        render_room(surf, self.room, 0.0, ox, oy)
        uniq = set()
        for y in range(0, 720, 4):
            for x in range(0, 1280, 4):
                uniq.add(surf.get_at((x, y))[:3])
        self.assertGreater(len(uniq), 500)

    def test_worldreact_routes_crown_to_the_crown_scene(self):
        room = worldreact.build_scene_room(self.world, "crown", frozenset())
        self.assertEqual(room.title, "Lantern Crown")
        self.assertTrue(any(p.kind == "lantern_tree" for p in room.props))
        self.assertTrue(any(p.kind == "seed_cradle" for p in room.props))

        # seed_planted flips the cradle to the planted state and drops the halo
        planted = worldreact.build_scene_room(self.world, "crown",
                                              frozenset({"seed_planted"}))
        cradle = next(p for p in planted.props if (p.gx, p.gy) == (3, 3)
                      and p.kind == "seed_cradle_planted")
        self.assertFalse(cradle.interactable)
        self.assertFalse(any(p.kind == "seed_cradle" and (p.gx, p.gy) == (3, 3)
                             for p in planted.props))

        # lens_mounted flips the mount to the lit state and drops the halo
        mounted = worldreact.build_scene_room(self.world, "crown",
                                              frozenset({"lens_mounted"}))
        mount = next(p for p in mounted.props if (p.gx, p.gy) == (5, 3)
                     and p.kind == "lens_mount_lit")
        self.assertFalse(mount.interactable)

    def test_lantern_lit_beat_adds_warm_glow(self):
        room = worldreact.build_scene_room(self.world, "crown", frozenset())
        lit = worldreact.build_scene_room(self.world, "crown",
                                          frozenset({"lantern_lit"}))
        self.assertGreater(len(lit.glows), len(room.glows))


if __name__ == "__main__":
    unittest.main()
