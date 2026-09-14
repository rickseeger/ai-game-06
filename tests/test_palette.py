"""Palette discipline + cohesion rules (unit tests)."""

import math
import unittest

from emberglow.palette import (PALETTE, dE, painterly, darken, is_warm, is_violet,
                               is_foliage, nearest_swatch, WARM, FOLIAGE, COOL, GLOW)


class PaletteTests(unittest.TestCase):
    def test_locked_swatches_present(self):
        for k in ("hearth_amber", "honey_gold", "pumpkin", "russet", "moss_green",
                  "fern_deep", "cream_parch", "bark_brown", "firefly_glow",
                  "twilight_violet", "brook"):
            self.assertIn(k, PALETTE)

    def test_each_swatch_is_self_nearest(self):
        for name, sw in PALETTE.items():
            n, d = nearest_swatch(sw)
            self.assertEqual(n, name)
            self.assertEqual(d, 0.0)

    def test_painterly_stays_near_base(self):
        for name, sw in PALETTE.items():
            for n in (-1.0, -0.5, 0.0, 0.5, 1.0):
                c = painterly(sw, n)
                self.assertLessEqual(dE(c, sw), 50, f"{name} jitter {n}")

    def test_darken_reduces_brightness(self):
        for name in ("cream_parch", "moss_green", "pumpkin"):
            sw = PALETTE[name]
            self.assertLess(sum(darken(sw, 0.68)), sum(sw))

    def test_cohesion_classifiers(self):
        self.assertTrue(is_warm(PALETTE["cream_parch"]))
        self.assertTrue(is_warm(PALETTE["hearth_amber"]))
        self.assertFalse(is_warm(PALETTE["moss_green"]))
        self.assertTrue(is_violet(PALETTE["twilight_violet"]))
        self.assertFalse(is_violet(PALETTE["hearth_amber"]))
        self.assertTrue(is_foliage(PALETTE["moss_green"]))
        self.assertTrue(is_foliage(PALETTE["fern_deep"]))

    def test_role_sets_are_disjoint(self):
        self.assertTrue(WARM.isdisjoint(FOLIAGE))
        self.assertTrue(COOL.isdisjoint(WARM | FOLIAGE | GLOW))


if __name__ == "__main__":
    unittest.main()
