"""Fixed 2:1 isometric projection + painter's-algorithm depth keys.

Locked by the art direction: 64x32 diamond tiles (world unit 64 px), no rotation,
no zoom, one camera. Depth is the painter's algorithm -- sort by (gx+gy, layer)
back-to-front so nearer world cells draw later (on top).
"""

TILE_W, TILE_H = 64, 32
HW, HH = TILE_W // 2, TILE_H // 2   # 32, 16
ELEV = 16                            # screen px per unit of tile height (2.5D extrusion)

# Depth layers (floats) -- higher draws later (on top).
LAYER_TILE = 0.0
LAYER_SHADOW = 0.5
LAYER_PROP = 1.0
LAYER_GLOW = 1.5


def iso(gx, gy, ox, oy):
    """World grid (gx, gy) -> screen top-left of the tile diamond."""
    return int((gx - gy) * HW + ox), int((gx + gy) * HH + oy)


def iso_f(fx, fy, ox, oy):
    """Float version, for sub-tile animation positions."""
    return (fx - fy) * HW + ox, (fx + fy) * HH + oy


def depth_key(gx, gy, layer=LAYER_TILE, sub=0.0):
    """Painter's sort key: nearer cells have larger gx+gy, drawn later."""
    return (gx + gy, layer, sub)


def diamond_edge(px, py):
    """Distance to the diamond boundary (1.0 == edge, 0.0 == center)."""
    return abs(px - TILE_W / 2.0) / (TILE_W / 2.0) + abs(py - TILE_H / 2.0) / (TILE_H / 2.0)


def prop_anchor(gx, gy, h, ox, oy):
    """Screen point where a prop's base sits (top-face center, raised by h units)."""
    tx, ty = iso(gx, gy, ox, oy)
    return tx + HW, ty + HH - h * ELEV


def grid_bounds(grid_size, ox, oy):
    """Screen rectangle enclosing a grid_size x grid_size diamond field."""
    xs, ys = [], []
    for gx in (0, grid_size - 1):
        for gy in (0, grid_size - 1):
            x, y = iso(gx, gy, ox, oy)
            xs += [x, x + TILE_W]
            ys += [y, y + TILE_H]
    return min(xs), min(ys), max(xs), max(ys)
