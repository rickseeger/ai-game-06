"""Hand-authored solid (impassable) obstacle cells per room.

Rendering-independent world geometry, authored once and tested headless. This file
owns the NON-interactable blocking props -- cottages, the forge block, the
waterwheel body and mill-race water, plant beds, the hilltop ridge and the
lantern-crown tree trunk. It is deliberately free of any pygame import so the whole
geometry/traversal contract can be exercised with no display (SDL dummy driver).

Coordinates are (x, y) grid cells: x in 0..8 runs west -> east, y in 0..8 runs
north -> south. The outer ring of each 9x9 room (x in {0, 8} or y in {0, 8}) is the
hollow's enclosing treeline and is impassable EXCEPT the portal cells declared by
the room edges in docs/world.json. Interactable objects and characters (the
`objects` map in docs/world.json) are also solid -- you stand on an adjacent tile
to interact. The cells listed here are only the props that are NOT interactable.

Each list is authored to read as its room's description while keeping every room's
floor fully connected (asserted by emberglow/world.py validate() and tests/test_world.py).
"""

OBSTACLES = {
    # Hollow Gate: the village common, cottages around a cobbled square.
    "gate": frozenset({
        (1, 1), (2, 1), (1, 2),             # NW mushroom-roof cottage
        (6, 1), (7, 1), (7, 2),             # NE cottage (by the Hill Stair)
        (1, 6), (1, 7),                     # SW cottage
        (6, 6), (7, 6), (6, 7), (7, 7),     # SE cottage
    }),

    # Forge Market: canvas awnings, the forge block, stalls and crates.
    "market": frozenset({
        (1, 1), (2, 1), (5, 1), (6, 1), (7, 1),   # awning stalls (N)
        (6, 2), (7, 2), (7, 3),                   # forge block (E)
        (2, 5), (5, 5),                           # crates / barrels
        (1, 7), (2, 7), (5, 7), (6, 7),           # market stalls (S)
    }),

    # Mill Court: the waterwheel, its mill-race, the mill house, stacked timber.
    "mill": frozenset({
        (1, 2), (2, 2), (1, 3),             # waterwheel body (crank socket at 2,3)
        (1, 5), (1, 6),                     # mill-race Brook (water), west edge
        (6, 1), (7, 1),                     # stacked timber (NE)
        (6, 6), (7, 6), (6, 7), (7, 7),     # mill house (SE)
    }),

    # Firefly Greenhouse: glassy and open; raised plant beds around the walls.
    "greenhouse": frozenset({
        (1, 1), (2, 1), (6, 1), (7, 1),     # plant beds (N)
        (1, 6), (1, 7), (7, 6), (7, 7),     # plant beds (S)
    }),

    # Lantern Crown: the hilltop; a rocky north ridge and the lantern-crown tree.
    "crown": frozenset({
        (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1),  # rocky ridge (N)
        (3, 2), (4, 2),                                            # lantern-crown tree
        (1, 7), (7, 7),                                            # ridge (S corners)
    }),
}
