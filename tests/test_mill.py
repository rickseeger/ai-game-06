"""G13 node 17 -- Mill Court room: scene composition + render smoke tests.

Headless (offscreen surfaces only, no display). Verifies the mill room is
authored to match node 2/16's scene contract: the waterwheel and mill house sit
at their worldmap obstacle cells, the crank socket and water spout at their
object cells, every prop kind resolves to a sprite, and the room renders
deterministically without errors. The water_flowing beat is also asserted here.
"""

import os
import unittest

# headless: no display / no sound card (offscreen surfaces only)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from emberglow.scene import build_room_mill, render_room, layout
from emberglow.sprites import get_sprite
from emberglow.world import World
from emberglow import worldreact


class MillSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.room = build_room_mill()
        self.world = World()

    def tearDown(self):
        pygame.quit()

    def _prop_at(self, kind, gx, gy):
        return next(p for p in self.room.props if p.kind == kind
                    and p.gx == gx and p.gy == gy)

    def test_room_identity(self):
        self.assertEqual(self.room.grid, 9)
        self.assertEqual(self.room.title, "Mill Court")
        self.assertIn("waterwheel", self.room.subtitle)

    def test_interactables_on_object_cells(self):
        self.assertTrue(self._prop_at("crank_socket", 2, 3).interactable)
        self.assertTrue(self._prop_at("water_spout", 6, 3).interactable)

    def test_mill_footing_heights(self):
        self.assertEqual(set(self.room.heights), {(6, 6), (7, 6), (6, 7), (7, 7)})
        self.assertTrue(all(h == 1 for h in self.room.heights.values()))

    def test_interactables_align_with_world_objects(self):
        objects = self.world.rooms["mill"].objects
        self.assertEqual((2, 3), objects["crank_socket"])
        self.assertEqual((6, 3), objects["water_spout"])
        self._prop_at("crank_socket", 2, 3)
        self._prop_at("water_spout", 6, 3)

    def test_props_align_with_obstacles(self):
        obstacles = set(self.world.rooms["mill"].obstacles)
        wheel = {(p.gx, p.gy) for p in self.room.props if p.kind == "waterwheel"}
        house = {(p.gx, p.gy) for p in self.room.props if p.kind == "mill_house"}
        timber = {(p.gx, p.gy) for p in self.room.props if p.kind == "timber_stack"}
        race = {(p.gx, p.gy) for p in self.room.props if p.kind == "mill_race"}
        self.assertLessEqual(wheel | house | timber | race, obstacles)
        self.assertEqual(len(house), 1)
        self.assertEqual(len(timber), 2)
        self.assertEqual(len(race), 2)

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

    def test_worldreact_routes_mill_to_the_mill_scene(self):
        room = worldreact.build_scene_room(self.world, "mill", frozenset())
        self.assertEqual(room.title, "Mill Court")
        self.assertTrue(any(p.kind == "waterwheel" for p in room.props))
        # water_flowing adds Brook water at the mill-race and spout_flow at the spout
        flow = worldreact.build_scene_room(self.world, "mill",
                                           frozenset({"water_flowing"}))
        water_cells = {(p.gx, p.gy) for p in flow.props if p.kind == "water"}
        self.assertEqual(water_cells, {(1, 5), (1, 6)})
        self.assertTrue(any(p.kind == "spout_flow" and (p.gx, p.gy) == (6, 3)
                            for p in flow.props))
        # the spout stays the single interactable at (6,3) (no double halo)
        interactables_63 = [p for p in flow.props if (p.gx, p.gy) == (6, 3)
                            and p.interactable]
        self.assertEqual(len(interactables_63), 1)


if __name__ == "__main__":
    unittest.main()
