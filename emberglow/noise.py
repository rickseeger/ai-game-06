"""Deterministic value noise with ONE shared seed.

The whole hollow samples this same noise field so the painterly brush is
continuous across the map (no per-object noise soup) -- cohesion rule 2.
"""

import math
from functools import lru_cache

SEED = 20260914
_MASK = 4294967296  # 2**32


@lru_cache(maxsize=None)
def _hash(x, y):
    n = (x * 374761393 + y * 668265263 + SEED * 1440662683) % _MASK
    n = (n * 2654435761 + 1013904223) % _MASK
    return n / float(_MASK)


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def value_noise(x, y):
    xi, yi = int(math.floor(x)), int(math.floor(y))
    xf, yf = x - xi, y - yi
    u, v = _smooth(xf), _smooth(yf)
    a = _hash(xi, yi)
    b = _hash(xi + 1, yi)
    c = _hash(xi, yi + 1)
    d = _hash(xi + 1, yi + 1)
    return (a * (1 - u) * (1 - v) + b * u * (1 - v) + c * (1 - u) * v + d * u * v) * 2.0 - 1.0


def fbm(x, y, octaves=2):
    total, amp, freq, norm = 0.0, 1.0, 1.0, 0.0
    for _ in range(octaves):
        total += amp * value_noise(x * freq, y * freq)
        norm += amp
        amp *= 0.5
        freq *= 2.0
    return total / norm   # in [-1, 1]
