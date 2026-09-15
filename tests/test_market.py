"""G13 node 16 -- Forge Market room: scene composition + render smoke tests.

Headless (offscreen surfaces only, no display). Verifies the market room is
authored to match node 2's scene contract: the forge sits on a raised (h=1)
plinth at the world's forge object cell, Bramble at his object cell, stalls and
crates at the worldmap obstacle cells, every prop kind resolves to a sprite,
and the room renders deterministically without errors.
"""

import os
import unittest

# headless: no display / no sound card (offscreen surfaces only)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from emberglow.scene import build_room_market, render_room, layout
from emberglow.sprites import get_sprite
from emberglow.world import World
from emberglow import worldreact


class MarketSceneTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.room = build_room_market()
        self.world = World()

    def tearDown(self):
        pygame.quit()

    def _prop_at(self, kind, gx, gy):
        return next(p for p in self.room.props if p.kind == kind
                    and p.gx == gx and p.gy == gy)

    def test_room_identity(self):
        self.assertEqual(self.room.grid, 9)
        self.assertEqual(self.room.title, "Forge Market")
        self.assertIn("forge", self.room.subtitle)

    def test_forge_interactable_on_raised_plinth(self):
        forge = self._prop_at("forge", 6, 3)
        self.assertTrue(forge.interactable)
        self.assertEqual(forge.h, 1)

    def test_forge_plinth_heights(self):
        self.assertEqual(set(self.room.heights), {(6, 2), (7, 2), (6, 3), (7, 3)})
        self.assertTrue(all(h == 1 for h in self.room.heights.values()))

    def test_forge_and_bramble_align_with_world_objects(self):
        # the interactable art must sit exactly on the world object cells so the
        # Firefly-Glow halo + interaction target line up with the traversal layer
        objects = self.world.rooms["market"].objects
        self.assertEqual((6, 3), objects["forge"])
        self.assertEqual((2, 3), objects["bramble"])
        self._prop_at("forge", 6, 3)
        self._prop_at("bramble", 2, 3)

    def test_stalls_and_crates_align_with_obstacles(self):
        obstacles = set(self.world.rooms["market"].obstacles)
        stall_cells = {(p.gx, p.gy) for p in self.room.props if p.kind == "stall"}
        crate_cells = {(p.gx, p.gy) for p in self.room.props if p.kind == "crate"}
        self.assertLessEqual(stall_cells | crate_cells, obstacles)
        self.assertEqual(len(stall_cells), 9)
        self.assertEqual(len(crate_cells), 2)

    def test_every_prop_kind_has_a_sprite(self):
        kinds = {p.kind for p in self.room.props}
        for kind in kinds:
            spr = get_sprite(kind, 0, 0)
            self.assertGreater(spr.get_width(), 0, kind)
            self.assertGreater(spr.get_height(), 0, kind)

    def test_no_static_player_prop(self):
        # the live game draws the player at its true world position; the static
        # scene must not plant a ghost player in the room
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

    def test_worldreact_routes_market_to_the_market_scene(self):
        room = worldreact.build_scene_room(self.world, "market", frozenset())
        self.assertEqual(room.title, "Forge Market")
        self.assertTrue(any(p.kind == "forge" for p in room.props))
        # lens_ready adds the forge flash on the same raised cell as the forge
        flash = worldreact.build_scene_room(self.world, "market",
                                            frozenset({"lens_ready"}))
        f = next(p for p in flash.props if p.kind == "forge_flash")
        self.assertEqual((f.gx, f.gy, f.h), (6, 3, 1))


if __name__ == "__main__":
    unittest.main()
