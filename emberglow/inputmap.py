"""Deterministic keyboard -> game-action mapping for Emberglow Hollow.

Pure mapping layer: no game state, no event queue, just the single source of truth
the controller consults. Maps pygame key constants to logical actions and grid
directions, with WASD and arrow aliases pinned so the mapping is unit-testable
headless (SDL dummy driver). This is the one place a key binding is defined.
"""

from typing import Dict, FrozenSet, Optional, Tuple

import pygame

# -- logical actions ----------------------------------------------------------
MOVE_NORTH = "move_north"
MOVE_SOUTH = "move_south"
MOVE_EAST = "move_east"
MOVE_WEST = "move_west"
INTERACT = "interact"
DISMISS = "dismiss"
QUIT = "quit"

ALL_ACTIONS: FrozenSet[str] = frozenset({
    MOVE_NORTH, MOVE_SOUTH, MOVE_EAST, MOVE_WEST, INTERACT, DISMISS, QUIT,
})

MOVE_ACTIONS: FrozenSet[str] = frozenset({
    MOVE_NORTH, MOVE_SOUTH, MOVE_EAST, MOVE_WEST,
})

# -- key -> action ------------------------------------------------------------
# Arrows and WASD both move (aliases); E / Space / Return interact; Escape
# dismisses the dialogue/interface; Q quits.
KEY_TO_ACTION: Dict[int, str] = {
    pygame.K_UP: MOVE_NORTH,      pygame.K_w: MOVE_NORTH,
    pygame.K_DOWN: MOVE_SOUTH,    pygame.K_s: MOVE_SOUTH,
    pygame.K_RIGHT: MOVE_EAST,    pygame.K_d: MOVE_EAST,
    pygame.K_LEFT: MOVE_WEST,     pygame.K_a: MOVE_WEST,
    pygame.K_e: INTERACT,
    pygame.K_SPACE: INTERACT,
    pygame.K_RETURN: INTERACT,
    pygame.K_ESCAPE: DISMISS,
    pygame.K_q: QUIT,
}

# -- action -> grid direction (dx, dy); y grows southward ---------------------
ACTION_DIRECTION: Dict[str, Tuple[int, int]] = {
    MOVE_NORTH: (0, -1),
    MOVE_SOUTH: (0, 1),
    MOVE_EAST: (1, 0),
    MOVE_WEST: (-1, 0),
}

# Human-readable on-screen controls hint (single line).
CONTROLS_HINT = "move: WASD / arrows   interact: E / space   dismiss: esc   quit: q"


def action_for_key(key: int) -> Optional[str]:
    """The action a key press maps to, or None for unmapped keys."""
    return KEY_TO_ACTION.get(key)


def is_move(action: str) -> bool:
    return action in MOVE_ACTIONS


def direction_for(action: str) -> Optional[Tuple[int, int]]:
    return ACTION_DIRECTION.get(action)


def is_keydown(event) -> bool:
    return getattr(event, "type", None) == pygame.KEYDOWN


def is_keyup(event) -> bool:
    return getattr(event, "type", None) == pygame.KEYUP
