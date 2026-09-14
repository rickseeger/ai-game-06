"""Rendering-independent world geometry and player traversal for Emberglow Hollow.

This module owns the WALKABLE SPACE, not the drawing. It has no pygame dependency
and never touches the isometric projection in emberglow/geometry.py; it reasons
purely in integer grid coordinates, so the entire geometry/traversal contract can
be exercised headless (SDL dummy driver, no display, no vision).

Coordinate system
    Each room is a GRID_SIZE x GRID_SIZE (9x9) grid of cells addressed by integer
    (x, y): x in 0..8 runs west -> east, y in 0..8 runs north -> south. The fixed
    2:1 isometric presentation maps these grid-cardinal steps onto the four on-screen
    diagonals; that mapping is rendering's concern and this layer is agnostic to it.

Solid cells
    A cell is solid (impassable) if it is an interior cell (1..7) occupied by either
    an interactable object/character (docs/world.json ``objects``) or a hand-authored
    non-interactable obstacle (emberglow/worldmap.py). The non-portal outer ring is
    the hollow's enclosing treeline and is also impassable.

Portals (room exits)
    Declared by the ``edges`` array in docs/world.json. A portal is a single edge
    cell. Stepping onto an open portal cell teleports the player one step INTO the
    adjacent room (the interior neighbour of the paired portal cell), so a portal is
    a trigger, never a resting position, and every crossing is reversible (no traps).
    An edge that declares ``requires`` flags is CLOSED -- its portal cell is
    impassable until every required flag is present, which is what prevents
    unintended progression bypasses.

Contract (asserted by tests/test_world.py and by World.validate())
    - blocked cells (obstacles and objects) are impassable;
    - a move onto a blocked / out-of-bounds / closed cell leaves the state unchanged;
    - every room's floor is connected (every walkable cell reachable from the entry);
    - every progression-critical location (object tile) has a reachable standing tile;
    - every portal is reachable and the room graph is connected;
    - the initial spawn is valid;
    - gated rooms are unreachable without their flags and reachable with them.
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Iterator, List, Optional, Set, Tuple

from . import worldmap

GRID_SIZE = 9
INNER_LO, INNER_HI = 1, GRID_SIZE - 2   # interior cells: x, y in 1..7 (0 and 8 are the ring)

# Cardinal directions in grid space (dx, dy). y grows "southward" (toward the
# player, in grid-row terms).
NORTH = (0, -1)
SOUTH = (0, 1)
EAST = (1, 0)
WEST = (-1, 0)
DIRECTIONS: Tuple[Tuple[int, int], ...] = (NORTH, SOUTH, EAST, WEST)
DIRECTION_NAMES = {NORTH: "north", SOUTH: "south", EAST: "east", WEST: "west"}

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORLD_PATH = REPO_ROOT / "docs" / "world.json"


class BlockedError(Exception):
    """Raised when a move would enter a solid, out-of-bounds, or closed cell."""

    def __init__(self, state: "State", direction: Tuple[int, int]):
        self.state = state
        self.direction = direction
        super().__init__(
            f"blocked moving {DIRECTION_NAMES[direction]} from {state.pos} in {state.room}"
        )


def _inward(cell: Tuple[int, int], size: int) -> Tuple[int, int]:
    """The interior neighbour of an edge cell (the landing tile just inside it)."""
    x, y = cell
    if x == 0:
        return (1, y)
    if x == size - 1:
        return (size - 2, y)
    if y == 0:
        return (x, 1)
    if y == size - 1:
        return (x, size - 2)
    raise ValueError(f"{cell} is not an edge cell")


@dataclass(frozen=True)
class State:
    """The player's traversal state: room, standing cell, flags, inventory."""

    room: str
    pos: Tuple[int, int]
    flags: FrozenSet[str] = frozenset()
    inventory: FrozenSet[str] = frozenset()


@dataclass(frozen=True)
class Portal:
    """One directed room exit: the trigger cell, the paired cell, and its gate."""

    cell: Tuple[int, int]        # portal (edge) cell in the source room
    dest_room: str
    dest_cell: Tuple[int, int]   # paired portal (edge) cell in the destination room
    requires: FrozenSet[str]     # flags needed for the portal to be open


class Room:
    """Room geometry: blocked cells, objects, and portals."""

    __slots__ = ("id", "size", "blocked", "objects", "obstacles", "portals", "portal_cells")

    def __init__(self, rid: str, size: int, blocked: Set[Tuple[int, int]],
                 objects: Dict[str, Tuple[int, int]],
                 obstacles: Set[Tuple[int, int]]):
        self.id = rid
        self.size = size
        self.blocked = frozenset(blocked)            # objects | obstacles
        self.objects = dict(objects)                 # name -> cell
        self.obstacles = frozenset(obstacles)        # non-interactable solids only
        self.portals: List[Portal] = []
        self.portal_cells: Set[Tuple[int, int]] = set()


class World:
    """The loaded, validated world: rooms, portals, and the traversal contract."""

    def __init__(self, world_path: Optional[Path] = None,
                 obstacles: Optional[Dict[str, FrozenSet[Tuple[int, int]]]] = None):
        world_path = Path(world_path) if world_path else DEFAULT_WORLD_PATH
        data = json.loads(world_path.read_text())
        assert data["schemaVersion"] == 1
        assert data["gridSize"] == GRID_SIZE
        obstacles = worldmap.OBSTACLES if obstacles is None else obstacles

        self.data = data
        self.size = GRID_SIZE
        self.edges = data["edges"]
        self.actions = data["actions"]
        self.terminal_flag = data["terminalFlag"]
        self.initial_room = data["initial"]["room"]
        self.initial_pos = tuple(data["initial"]["position"])

        # All flag names that can ever gate a portal (used by validate()).
        self.all_flags: FrozenSet[str] = frozenset(
            {f for a in self.actions for f in a["flags"]}
            | {f for e in self.edges for f in e.get("requires", ())}
        )

        self.rooms: Dict[str, Room] = {}
        self._portal_at: Dict[Tuple[str, Tuple[int, int]], Portal] = {}

        for rid, rdata in data["rooms"].items():
            objects = {name: tuple(cell) for name, cell in rdata["objects"].items()}
            obs = set(obstacles.get(rid, ()))
            for name, cell in objects.items():
                assert self._interior(cell), (rid, name, "object outside interior", cell)
            for cell in obs:
                assert self._interior(cell), (rid, "obstacle outside interior", cell)
                assert cell not in objects.values(), (rid, "obstacle overlaps object", cell)
            self.rooms[rid] = Room(rid, self.size, set(objects.values()) | obs, objects, obs)

        for edge in data["edges"]:
            requires = frozenset(edge.get("requires", ()))
            for src_key, dst_key in (("a", "b"), ("b", "a")):
                src_room = edge[src_key]
                src_cell = tuple(edge[f"{src_key}_port"])
                dst_room = edge[dst_key]
                dst_cell = tuple(edge[f"{dst_key}_port"])
                portal = Portal(src_cell, dst_room, dst_cell, requires)
                self.rooms[src_room].portals.append(portal)
                self.rooms[src_room].portal_cells.add(src_cell)
                assert (src_room, src_cell) not in self._portal_at, (src_room, src_cell)
                self._portal_at[(src_room, src_cell)] = portal

    # -- basic predicates ---------------------------------------------------

    def _interior(self, pos: Tuple[int, int]) -> bool:
        x, y = pos
        return INNER_LO <= x <= INNER_HI and INNER_LO <= y <= INNER_HI

    def in_bounds(self, room_id: str, pos: Tuple[int, int]) -> bool:
        x, y = pos
        return 0 <= x < self.size and 0 <= y < self.size

    def is_solid(self, room_id: str, pos: Tuple[int, int]) -> bool:
        """True if `pos` is an interior solid cell (object or obstacle)."""
        return self.in_bounds(room_id, pos) and pos in self.rooms[room_id].blocked

    def portal_at(self, room_id: str, pos: Tuple[int, int]) -> Optional[Portal]:
        return self._portal_at.get((room_id, pos))

    def walkable(self, room_id: str, pos: Tuple[int, int],
                 flags: FrozenSet[str] = frozenset()) -> bool:
        """True if the player can step onto `pos` given `flags`.

        A portal cell is walkable only when its gate is open; the non-portal outer
        ring is always impassable; interior cells are walkable unless solid.
        """
        if not self.in_bounds(room_id, pos):
            return False
        portal = self.portal_at(room_id, pos)
        if portal is not None:
            return portal.requires <= flags
        if not self._interior(pos):
            return False
        return pos not in self.rooms[room_id].blocked

    def neighbors(self, room_id: str, pos: Tuple[int, int],
                  flags: FrozenSet[str] = frozenset()) -> List[Tuple[int, int]]:
        """Walkable 4-neighbour cells (portal cells included as step-on triggers)."""
        x, y = pos
        return [(x + dx, y + dy) for dx, dy in DIRECTIONS
                if self.walkable(room_id, (x + dx, y + dy), flags)]

    def object_position(self, room_id: str, obj_id: str) -> Tuple[int, int]:
        return self.rooms[room_id].objects[obj_id]

    def objects_at(self, room_id: str, pos: Tuple[int, int]) -> List[str]:
        return [n for n, c in self.rooms[room_id].objects.items() if c == pos]

    def interaction_tiles(self, room_id: str, obj_id: str,
                          flags: FrozenSet[str] = frozenset()) -> List[Tuple[int, int]]:
        """Walkable cells from which `obj_id` can be interacted with (adjacent)."""
        x, y = self.rooms[room_id].objects[obj_id]
        return [(x + dx, y + dy) for dx, dy in DIRECTIONS
                if self.walkable(room_id, (x + dx, y + dy), flags)]

    # -- traversal ----------------------------------------------------------

    def initial_state(self) -> State:
        return State(self.initial_room, self.initial_pos)

    def can_move(self, state: State, direction: Tuple[int, int]) -> bool:
        dx, dy = direction
        return self.walkable(state.room, (state.pos[0] + dx, state.pos[1] + dy), state.flags)

    def move(self, state: State, direction: Tuple[int, int]) -> State:
        """Move one cell in `direction`, crossing a portal if one is stepped onto.

        Raises BlockedError (leaving `state` unchanged) when the target cell is
        solid, out of bounds, or a closed portal.
        """
        dx, dy = direction
        target = (state.pos[0] + dx, state.pos[1] + dy)
        if not self.walkable(state.room, target, state.flags):
            raise BlockedError(state, direction)
        portal = self.portal_at(state.room, target)
        if portal is not None:
            landing = _inward(portal.dest_cell, self.size)
            return State(portal.dest_room, landing, state.flags, state.inventory)
        return State(state.room, target, state.flags, state.inventory)

    # -- reachability -------------------------------------------------------

    def reachable_cells(self, room_id: str, start: Tuple[int, int],
                        flags: FrozenSet[str] = frozenset()) -> Set[Tuple[int, int]]:
        """Walkable cells reachable from `start` without leaving the room."""
        seen: Set[Tuple[int, int]] = {start}
        q = deque([start])
        while q:
            pos = q.popleft()
            for n in self.neighbors(room_id, pos, flags):
                if n not in seen:
                    seen.add(n)
                    q.append(n)
        return seen

    def reachable_state_space(self, start_room: str, start_pos: Tuple[int, int],
                              flags: FrozenSet[str] = frozenset()
                              ) -> Set[Tuple[str, Tuple[int, int]]]:
        """All (room, cell) standpoints reachable, crossing open portals."""
        start = (start_room, start_pos)
        seen: Set[Tuple[str, Tuple[int, int]]] = {start}
        q = deque([start])
        while q:
            room, pos = q.popleft()
            for n in self.neighbors(room, pos, flags):
                portal = self.portal_at(room, n)
                nxt = (portal.dest_room, _inward(portal.dest_cell, self.size)) \
                    if portal is not None else (room, n)
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
        return seen

    def find_path(self, start_room: str, start_pos: Tuple[int, int],
                  dest_room: str, dest_pos: Tuple[int, int],
                  flags: FrozenSet[str] = frozenset()
                  ) -> Optional[List[Tuple[int, int]]]:
        """Shortest list of directions from (start_room, start_pos) to a standpoint.

        Returns None when unreachable. Crosses open portals; directions are
        grid-cardinal and can be replayed through World.move().
        """
        start = (start_room, start_pos)
        dest = (dest_room, dest_pos)
        if start == dest:
            return []
        prev: Dict[Tuple[str, Tuple[int, int]],
                   Optional[Tuple[Tuple[str, Tuple[int, int]], Tuple[int, int]]]] = {start: None}
        q = deque([start])
        while q:
            room, pos = q.popleft()
            for d in DIRECTIONS:
                dx, dy = d
                n = (pos[0] + dx, pos[1] + dy)
                if not self.walkable(room, n, flags):
                    continue
                portal = self.portal_at(room, n)
                nxt = (portal.dest_room, _inward(portal.dest_cell, self.size)) \
                    if portal is not None else (room, n)
                if nxt not in prev:
                    prev[nxt] = ((room, pos), d)
                    if nxt == dest:
                        steps: List[Tuple[int, int]] = []
                        node = dest
                        while prev[node] is not None:
                            (parent, d) = prev[node]
                            steps.append(d)
                            node = parent
                        steps.reverse()
                        return steps
                    q.append(nxt)
        return None

    # -- contract validation ------------------------------------------------

    def validate(self) -> dict:
        """Assert the whole geometry/traversal contract; return a report dict."""
        problems: List[str] = []
        all_flags = self.all_flags

        if not self.walkable(self.initial_room, self.initial_pos, frozenset()):
            problems.append("initial spawn is not walkable")

        room_stats: Dict[str, dict] = {}
        for rid, room in self.rooms.items():
            floor = {c for c in self._cells() if self.walkable(rid, c, all_flags)}
            seed = self.initial_pos if rid == self.initial_room else room.portals[0].cell
            reach = self.reachable_cells(rid, seed, all_flags)
            missing = floor - reach
            if missing:
                problems.append(f"{rid}: {len(missing)} walkable cells unreachable "
                                f"from {seed}: {sorted(missing)}")
            for name, cell in room.objects.items():
                tiles = self.interaction_tiles(rid, name, all_flags)
                if not tiles:
                    problems.append(f"{rid}.{name}: no walkable standing tile next to {cell}")
                elif not set(tiles).intersection(reach):
                    problems.append(f"{rid}.{name}: standing tiles {tiles} unreachable")
            for portal in room.portals:
                if not self.walkable(rid, portal.cell, all_flags):
                    problems.append(f"{rid}: portal {portal.cell} not walkable when open")
                if _inward(portal.cell, self.size) not in reach:
                    problems.append(f"{rid}: portal {portal.cell} has no reachable approach")
            room_stats[rid] = {
                "walkable": len(floor),
                "solid": len(room.blocked),
                "obstacles": len(room.obstacles),
                "objects": len(room.objects),
                "portals": len(room.portals),
                "reachable": len(reach),
                "connected": not missing,
            }

        # Resting positions only (interior walkable cells). Portal cells are
        # step-on triggers (verified approachable per-room above), not rest states.
        world_floor = {(rid, c) for rid in self.rooms for c in self._cells()
                       if self._interior(c) and self.walkable(rid, c, all_flags)}
        reached = self.reachable_state_space(self.initial_room, self.initial_pos, all_flags)
        unreached = world_floor - reached
        if unreached:
            problems.append(f"world graph disconnected: {len(unreached)} standpoints "
                            f"unreachable: {sorted(unreached)}")

        gated_dest_rooms = {edge["b"] for edge in self.edges if edge.get("requires")}
        no_flag_rooms = {r for r, _ in self.reachable_state_space(
            self.initial_room, self.initial_pos, frozenset())}
        all_flag_rooms = {r for r, _ in reached}
        for rid in gated_dest_rooms:
            if rid in no_flag_rooms:
                problems.append(f"gated room {rid} reachable without its flags (bypass)")
            if rid not in all_flag_rooms:
                problems.append(f"gated room {rid} unreachable even with its flags")

        return {
            "ok": not problems,
            "problems": problems,
            "rooms": room_stats,
            "worldWalkable": len(world_floor),
            "worldReachable": len(reached),
            "gatedRoomsLockedWithoutFlags": sorted(gated_dest_rooms - no_flag_rooms),
            "gatedRoomsOpenWithFlags": sorted(gated_dest_rooms.intersection(all_flag_rooms)),
            "terminalFlag": self.terminal_flag,
        }

    def _cells(self) -> Iterator[Tuple[int, int]]:
        for x in range(self.size):
            for y in range(self.size):
                yield (x, y)
