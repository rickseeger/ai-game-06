"""Restrained, deterministic animation -- every value is a pure function of time t.

The design calls for gentle, atmospheric motion: drifting fireflies, a soft
lantern/glow flicker, the player's idle bob, a barely-there bell sway. Nothing is
driven by a clock beyond t (seconds), so a frame at time t is byte-reproducible.
"""

import math

TAU = 2.0 * math.pi


def firefly_drift(fx, fy, phase, t, amp=0.34, speed=0.14):
    """Slow lissajous drift (world units) around a firefly's anchor."""
    x = fx + amp * math.sin(TAU * speed * t + phase)
    y = fy + amp * math.cos(TAU * speed * 0.72 * t + phase * 1.7)
    return x, y


def firefly_brightness(phase, t):
    """Gentle twinkle in [0.45, 1.0]."""
    return 0.45 + 0.55 * (0.5 + 0.5 * math.sin(TAU * 0.55 * t + phase * 3.1))


def idle_bob(t, amp=2.0, speed=1.1):
    """Player idle bob (vertical px), subtle breathing."""
    return amp * math.sin(TAU * speed * t)


def flicker(t, phase=0.0, depth=0.11):
    """Subtle warm-light flicker in [1-depth, 1+depth]."""
    s = math.sin(TAU * 2.7 * t + phase) * 0.6 + math.sin(TAU * 6.9 * t + phase * 2.3) * 0.4
    return 1.0 + depth * s


def sway(t, phase=0.0, amp=1.2, speed=0.6):
    """Barely-there lateral sway (px) for a hanging bell."""
    return amp * math.sin(TAU * speed * t + phase)
