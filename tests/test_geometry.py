"""Isometric projection + painter's-algorithm draw-order (unit tests)."""

import unittest

import pygame

from emberglow.geometry import (iso, depth_key, prop_anchor, grid_bounds,
                                LAYER_TILE, LAYER_PROP, TILE_W, TILE_H, HW, HH, ELEV)
from emberglow.scene import build_drawables, depth_sorted, build_room_gate
from emberglow.checks import geometry_checks, draw_order_checks


class ProjectionTests(unittest.TestCase):
    def test_iso_slope_is_2_to_1(self):
        ox, oy = 600, 200
        x0, y0 = iso(0, 0, ox, oy)
        x1, y1 = iso(1, 0, ox, oy)
        x2, y2 = iso(0, 1, ox, oy)
        self.assertEqual((x1 - x0, y1 - y0), (HW, HH))      # +x -> (+32,+16)
        self.assertEqual((x2 - x0, y2 - y0), (-HW, HH))     # +y -> (-32,+16)

    def test_diamond_is_2_to_1(self):
        room = build_room_gate()
        x0, y0, x1, y1 = grid_bounds(room.grid, 600, 200)
        self.assertLessEqual(abs((x1 - x0) - 2 * (y1 - y0)), 1)

    def test_prop_anchor_raises_with_elevation(self):
        ax, ay = prop_anchor(2, 3, 0, 600, 200)
        bx, by = prop_anchor(2, 3, 2, 600, 200)
        self.assertEqual(ax, bx)
        self.assertEqual(ay - by, 2 * ELEV)


class DepthOrderTests(unittest.TestCase):
    def test_tiles_monotonic_back_to_front(self):
        room = build_room_gate()
        ox, oy = 600, 200
        res = draw_order_checks(room, 0.0, ox, oy)
        self.assertTrue(res["tile_order_monotonic"])
        self.assertTrue(res["props_after_own_tile"])
        self.assertTrue(res["far_before_near"])
        self.assertTrue(res["player_over_background_tiles"])

    def test_painter_occlusion_pixel(self):
        """A nearer solid card must cover a farther solid card where they overlap."""
        pygame.init()
        ox, oy = 0, 120
        RED = (255, 0, 0)
        BLUE = (0, 0, 255)
        far = pygame.Surface((60, 100), pygame.SRCALPHA)
        far.fill((*RED, 255))
        near = pygame.Surface((60, 100), pygame.SRCALPHA)
        near.fill((*BLUE, 255))

        # far card on tile (0,0), near card on tile (1,0) -> anchors 32px apart
        ax, ay = prop_anchor(0, 0, 0, ox, oy)
        bx, by = prop_anchor(1, 0, 0, ox, oy)
        draw = [
            (depth_key(0, 0, LAYER_PROP), "card", (far, ax, ay)),
            (depth_key(1, 0, LAYER_PROP), "card", (near, bx, by)),
        ]
        ordered = depth_sorted(draw)
        surf = pygame.Surface((200, 200))
        for _, kind, (spr, cx, cy) in ordered:
            surf.blit(spr, (cx - 30, cy - spr.get_height()))
        # overlap region: between the two anchors (both cards cover it)
        px, py = 50, 100
        self.assertEqual(surf.get_at((px, py))[:3], BLUE, "near card must occlude far card")
        pygame.quit()


if __name__ == "__main__":
    unittest.main()
