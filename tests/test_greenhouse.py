"""G13 node 18 -- Firefly Greenhouse room: scene composition + render smoke tests.

Headless (offscreen surfaces only, no display). Verifies the greenhouse room is
authored to match node 2/16/17's scene contract: the ember-seed and the mural sit
at their world object cells, the plant beds sit at their worldmap obstacle cells,
every prop kind resolves to a sprite, and the room renders deterministically
without errors. The seed_taken beat is also asserted here.
"""

import os
import unittest

# headless: no display / no sound card (offscreen surfaces only)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from emberglow.scene import build_room_greenhouse, render_room, layout
from emberglow.sprites import get_sprite
from emberglow.world import World
from emberglow import worldreact


class GreenhouseSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.room = build_room_greenhouse()
        self.world = World()

    def tearDown(self):
        pygame.quit()

    def _prop_at(self, kind, gx, gy):
        return next(p for p in self.room.props if p.kind == kind
                    and p.gx == gx and p.gy == gy)

    def test_room_identity(self):
        self.assertEqual(self.room.grid, 9)
        self.assertEqual(self.room.title, "Firefly Greenhouse")
        self.assertIn("glass", self.room.subtitle)

    def test_interactables_on_object_cells(self):
        self.assertTrue(self._prop_at("seed", 4, 3).interactable)
        self.assertTrue(self._prop_at("mural", 2, 2).interactable)

    def test_seed_bed_raised_heights(self):
        self.assertEqual(set(self.room.heights), {(4, 3)})
        self.assertTrue(all(h == 1 for h in self.room.heights.values()))

    def test_interactables_align_with_world_objects(self):
        objects = self.world.rooms["greenhouse"].objects
        self.assertEqual((4, 3), objects["ember_seed"])
        self.assertEqual((2, 2), objects["mural"])
        self._prop_at("seed", 4, 3)
        self._prop_at("mural", 2, 2)

    def test_plant_beds_align_with_obstacles(self):
        obstacles = set(self.world.rooms["greenhouse"].obstacles)
        beds = {(p.gx, p.gy) for p in self.room.props if p.kind == "plant_bed"}
        self.assertLessEqual(beds, obstacles)
        self.assertEqual(len(beds), 8)

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

    def test_worldreact_routes_greenhouse_to_the_greenhouse_scene(self):
        room = worldreact.build_scene_room(self.world, "greenhouse", frozenset())
        self.assertEqual(room.title, "Firefly Greenhouse")
        self.assertTrue(any(p.kind == "glass_house" for p in room.props))
        self.assertTrue(any(p.kind == "seed" for p in room.props))
        # seed_taken flips the seed to the dimmed seed_bed and drops the halo
        taken = worldreact.build_scene_room(self.world, "greenhouse",
                                            frozenset({"seed_taken"}))
        seed_bed = next(p for p in taken.props if (p.gx, p.gy) == (4, 3)
                        and p.kind == "seed_bed")
        self.assertFalse(seed_bed.interactable)
        self.assertFalse(any(p.kind == "seed" and (p.gx, p.gy) == (4, 3)
                             for p in taken.props))


if __name__ == "__main__":
    unittest.main()
