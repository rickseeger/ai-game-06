"""Emberglow Hollow -- locked named palette (direction B) and color math.

The palette is the single source of truth for every flat surface fill. Cohesion
rules (from docs/ART_DIRECTIONS.md) are encoded as predicates so both the renderer
and the automated checks share one definition of "on-palette", "warm", "cool".
"""

import math

# Named hex swatches (locked by Rick's art-direction choice).
PALETTE = {
    "hearth_amber":    (0xF5, 0xA6, 0x23),   # primary warm light
    "honey_gold":      (0xF7, 0xC9, 0x48),   # highlights, glow, lantern light
    "pumpkin":         (0xE8, 0x7A, 0x3E),   # roofs, harvest accents
    "russet":          (0xC9, 0x6F, 0x4A),   # wood, soil, brick
    "moss_green":      (0x6B, 0x9E, 0x4A),   # foliage mid
    "fern_deep":       (0x3F, 0x6F, 0x3A),   # foliage shadow
    "cream_parch":     (0xFB, 0xEF, 0xD8),   # paper, walls, paths
    "bark_brown":      (0x6B, 0x4A, 0x32),   # trunks, dark wood
    "firefly_glow":    (0xD9, 0xF2, 0x6A),   # accent glow, fireflies
    "twilight_violet": (0x5B, 0x4A, 0x78),   # the single cool shadow / ambient
    "brook":           (0x6F, 0xA8, 0xB8),   # cool accent: mill-water only
}

# Palette roles (for cohesion checks).
WARM = {"hearth_amber", "honey_gold", "pumpkin", "russet", "cream_parch", "bark_brown"}
FOLIAGE = {"moss_green", "fern_deep"}
GLOW = {"firefly_glow"}
COOL = {"twilight_violet"}      # shadows / ambient only
COOL_ACCENT = {"brook"}         # water only

# Painterly brush tolerance (locked: +/-8% value, +/-6% saturation).
VALUE_JITTER = 0.08
SAT_JITTER = 0.06


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def rgb_to_hsv(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d == 0:
        h = 0.0
    elif mx == r:
        h = 60.0 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60.0 * ((b - r) / d + 2)
    else:
        h = 60.0 * ((r - g) / d + 4)
    s = 0.0 if mx == 0 else d / mx
    return h, s, mx


def hsv_to_rgb(h, s, v):
    c = v * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = v - c
    if h < 60:
        r, g, b = c, x, 0.0
    elif h < 120:
        r, g, b = x, c, 0.0
    elif h < 180:
        r, g, b = 0.0, c, x
    elif h < 240:
        r, g, b = 0.0, x, c
    elif h < 300:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x
    return int(round((r + m) * 255)), int(round((g + m) * 255)), int(round((b + m) * 255))


def darken(c, f):
    """Value-multiply (the fixed light rule for shaded side faces)."""
    h, s, v = rgb_to_hsv(*c[:3])
    return hsv_to_rgb(h, s, clamp(v * f))


def lighten(c, f):
    """Blend toward white (value lift)."""
    h, s, v = rgb_to_hsv(*c[:3])
    return hsv_to_rgb(h, s, clamp(v + (1 - v) * f))


def mix(a, b, t):
    t = clamp(t)
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a[:3], b[:3]))


def lerp(a, b, t):
    return a + (b - a) * t


def painterly(base, n):
    """Apply the locked painterly brush: +/-8% value, +/-6% saturation jitter.

    n is a single noise value in [-1, 1]; jitter is applied in HSV so palette
    identity survives the brush stroke.
    """
    h, s, v = rgb_to_hsv(*base[:3])
    s = clamp(s * (1 + n * SAT_JITTER))
    v = clamp(v * (1 + n * VALUE_JITTER))
    return hsv_to_rgb(h, s, v)


def dE(c1, c2):
    """Perceptual-ish color distance (Euclidean RGB) -- matches the design's dE<=50 rule."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1[:3], c2[:3])))


def is_warm(c):
    """Cohesion rule: lit warm surfaces satisfy R >= G >= B and R-B >= 15."""
    r, g, b = c[:3]
    return r >= g >= b and (r - b) >= 15


def is_violet(c):
    """Cohesion rule: shadows/ambient are violet-ish (B >= R), never black."""
    r, _, b = c[:3]
    return b >= r and b > 0


def is_foliage(c):
    r, g, b = c[:3]
    return g > r and g > b


def nearest_swatch(c):
    """Return (name, dE) of the closest named swatch -- for palette-adherence checks."""
    best, bestd = None, 1e9
    for name, sw in PALETTE.items():
        d = dE(c, sw)
        if d < bestd:
            best, bestd = name, d
    return best, bestd
