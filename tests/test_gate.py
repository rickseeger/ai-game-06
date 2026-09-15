"""G13 node 14 -- Hollow Gate room: scene composition + render smoke tests.

Headless (offscreen surfaces only, no display). Completes the per-room scene
contract for the home room (parity with market/mill/greenhouse/crown): Mallow,
the Hollow Bell and the Hill Stair sit at their world.json object cells, the
cottages sit at their worldmap obstacle cells, every prop kind resolves to a
sprite, and the room renders deterministically without errors. The stair_open
beat (ribbon of light) and the static-player strip are also asserted here.
"""

import os
import unittest

# headless: no display / no sound card (offscreen surfaces only)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from emberglow.scene import build_room_gate, render_room, layout
from emberglow.sprites import get_sprite
from emberglow.world import World
from emberglow import worldreact


class GateSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.room = build_room_gate()
        self.world = World()

    def tearDown(self):
        pygame.quit()

    def _prop_at(self, kind, gx, gy):
        return next(p for p in self.room.props if p.kind == kind
                    and p.gx == gx and p.gy == gy)

    def test_room_identity(self):
        self.assertEqual(self.room.grid, 9)
        self.assertEqual(self.room.title, "Hollow Gate")
        self.assertIn("dusk", self.room.subtitle)

    def test_interactables_on_object_cells(self):
        # Mallow (character), the Hollow Bell (terminal), the Hill Stair
        self.assertTrue(self._prop_at("mallow", 2, 3).interactable)
        self.assertTrue(self._prop_at("bell", 6, 3).interactable)
        self.assertTrue(self._prop_at("stair", 5, 1).interactable)

    def test_interactables_align_with_world_objects(self):
        objects = self.world.rooms["gate"].objects
        self.assertEqual((2, 3), objects["mallow"])
        self.assertEqual((6, 3), objects["hollow_bell"])
        self.assertEqual((5, 1), objects["hill_stair"])
        self._prop_at("mallow", 2, 3)
        self._prop_at("bell", 6, 3)
        self._prop_at("stair", 5, 1)

    def test_every_prop_kind_has_a_sprite(self):
        kinds = {p.kind for p in self.room.props}
        for kind in kinds:
            spr = get_sprite(kind, 0, 0)
            self.assertGreater(spr.get_width(), 0, kind)
            self.assertGreater(spr.get_height(), 0, kind)

    def test_renders_without_errors_and_is_not_blank(self):
        ox, oy = layout(self.room, 1280, 720)
        surf = pygame.Surface((1280, 720))
        render_room(surf, self.room, 0.0, ox, oy)
        uniq = set()
        for y in range(0, 720, 4):
            for x in range(0, 1280, 4):
                uniq.add(surf.get_at((x, y))[:3])
        self.assertGreater(len(uniq), 500)

    def test_worldreact_routes_gate_and_strips_static_player(self):
        # the live game draws the player at its true world position; build_scene_room
        # must remove the scene's static player prop so no ghost is left behind
        room = worldreact.build_scene_room(self.world, "gate", frozenset())
        self.assertEqual(room.title, "Hollow Gate")
        self.assertNotIn("player", {p.kind for p in room.props})
        self.assertTrue(any(p.kind == "mallow" for p in room.props))

    def test_stair_open_beat_adds_light_ribbon(self):
        room = worldreact.build_scene_room(self.world, "gate", frozenset())
        opened = worldreact.build_scene_room(self.world, "gate",
                                             frozenset({"stair_open"}))
        self.assertTrue(any(p.kind == "stair_light" and (p.gx, p.gy) == (5, 1)
                            for p in opened.props))
        self.assertFalse(any(p.kind == "stair_light" for p in room.props))


if __name__ == "__main__":
    unittest.main()
