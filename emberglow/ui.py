"""Interface treatment: inventory strip + dialogue panel + room chip + hint.

All in-palette (Cream Parchment panels, Bark Brown text, Firefly Glow / Hearth
Amber accents, Twilight Violet for a soft drop shadow -- never a hard outline).
"""

import pygame

from .palette import PALETTE, darken, mix
from .sprites import build_item_icon

_FONT_CACHE = {}


def _font(size):
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = pygame.font.Font(None, size)
    return _FONT_CACHE[size]


def _panel(w, h, fill, alpha=255, radius=12):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (*fill, alpha), s.get_rect(), border_radius=radius)
    return s


def _blit_panel(surface, x, y, w, h, fill, alpha=255, radius=12):
    # soft Twilight-Violet drop shadow first (offset), then the cream panel
    shadow = _panel(w, h, PALETTE["twilight_violet"], 70, radius)
    surface.blit(shadow, (x + 3, y + 4))
    surface.blit(_panel(w, h, fill, alpha, radius), (x, y))


def _wrap(text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_room_chip(surface, title, subtitle):
    font_t = _font(34)
    font_s = _font(20)
    tw = font_t.size(title)[0]
    w = max(tw, font_s.size(subtitle)[0]) + 44
    _blit_panel(surface, 20, 20, w, 62, PALETTE["cream_parch"], 242)
    t = font_t.render(title, True, PALETTE["bark_brown"])
    s = font_s.render(subtitle, True, mix(PALETTE["bark_brown"], PALETTE["twilight_violet"], 0.35))
    surface.blit(t, (42, 30))
    surface.blit(s, (42, 56))


def draw_inventory(surface, items, selected, y):
    """Horizontal inventory strip with item slots (in-palette)."""
    font = _font(18)
    n = max(1, len(items))
    slot, gap = 52, 12
    w = n * slot + (n + 1) * gap
    x = (surface.get_width() - w) // 2
    h = 66
    _blit_panel(surface, x, y, w, h, PALETTE["cream_parch"], 244)
    label = font.render("pockets", True, mix(PALETTE["bark_brown"], PALETTE["twilight_violet"], 0.3))
    surface.blit(label, (x + gap, y + h + 2))
    for i in range(n):
        sx = x + gap + i * (slot + gap)
        # slot well
        pygame.draw.rect(surface, mix(PALETTE["cream_parch"], PALETTE["twilight_violet"], 0.18),
                         (sx, y + gap, slot, slot), border_radius=8)
        if i == selected:
            pygame.draw.rect(surface, PALETTE["firefly_glow"], (sx, y + gap, slot, slot), width=3, border_radius=8)
        item = items[i]
        if item:
            icon = build_item_icon(item)
            surface.blit(icon, (sx + (slot - icon.get_width()) // 2,
                                y + gap + (slot - icon.get_height()) // 2))


def _tone_accent(tone):
    """Dialogue accent bar color per outcome tone (success / failure / info)."""
    return {"success": PALETTE["honey_gold"],
            "failure": PALETTE["russet"],
            "info": PALETTE["twilight_violet"],
            "locked": PALETTE["russet"]}.get(tone, PALETTE["twilight_violet"])


def draw_dialogue(surface, speaker, text, y, tone="info"):
    """Short modal text panel (1-2 cozy sentences), tone-colored for success/failure."""
    font = _font(24)
    font_s = _font(26)
    max_w = surface.get_width() - 320
    lines = _wrap(text, font, max_w - 80)
    w = surface.get_width() - 320
    h = 40 + len(lines) * 30
    x = (surface.get_width() - w) // 2
    _blit_panel(surface, x, y, w, h, PALETTE["cream_parch"], 246)
    accent = _tone_accent(tone)
    # a small tone accent chip at the panel's top-left (success gold / failure
    # russet / info violet) -- the pixel-sampled success-vs-failure signal
    pygame.draw.rect(surface, accent, (x + 18, y + 18, 12, 12), border_radius=3)
    name_color = accent if speaker else PALETTE["bark_brown"]
    if speaker:
        name = font_s.render(speaker, True, name_color)
        surface.blit(name, (x + 40, y + 18))
    ty = y + 52
    for ln in lines:
        surface.blit(font.render(ln, True, PALETTE["bark_brown"]), (x + 40, ty))
        ty += 30


def draw_hint(surface, text):
    font = _font(18)
    w = font.size(text)[0] + 28
    x = surface.get_width() - w - 24
    _blit_panel(surface, x, 24, w, 30, PALETTE["cream_parch"], 210, radius=8)
    surface.blit(font.render(text, True, PALETTE["bark_brown"]), (x + 14, 32))


def draw_ui(surface, room, items, selected, speaker, text):
    draw_room_chip(surface, room.title, room.subtitle)
    draw_hint(surface, "walk to a person or object to interact")
    draw_inventory(surface, items, selected, surface.get_height() - 100)
    draw_dialogue(surface, speaker, text, surface.get_height() - 250)


# --------------------------------------------------------------------------- #
# Node 4: controls hint + target feedback
# --------------------------------------------------------------------------- #
def tile_top_center(gx, gy, ox, oy):
    """Screen-space top-center of a grid tile (where a marker/label anchors)."""
    from .geometry import iso, HW, HH
    tx, ty = iso(gx, gy, ox, oy)
    return tx + HW, ty + HH


def draw_label_chip(surface, cx, cy, text, accent=False):
    """A small in-palette name chip above a target (readable, soft-edged)."""
    font = _font(18)
    tw = font.size(text)[0]
    w = tw + 24
    x = int(cx - w / 2)
    y = cy - 34
    _blit_panel(surface, x, y, w, 24, PALETTE["cream_parch"], 244, radius=8)
    color = PALETTE["russet"] if accent else PALETTE["bark_brown"]
    surface.blit(font.render(text, True, color), (x + 12, y + 5))


def draw_target_marker(surface, cx, cy, has_target, tone=None):
    """Readable target feedback on the cell the player currently faces.

    A neutral target glows firefly-green. On a result, a solid tone stamp is
    stamped at the marker center so success (warm gold) vs failure (russet) is
    unmistakable and pixel-samplable (solid, not additive).
    """
    from .sprites import radial_glow
    if has_target:
        glow = radial_glow(26, PALETTE["firefly_glow"], 150)
        surface.blit(glow, (int(cx - 26), int(cy - 26)),
                     special_flags=pygame.BLEND_RGB_ADD)
        if tone == "success":
            pygame.draw.circle(surface, PALETTE["honey_gold"], (int(cx), int(cy)), 7)
        elif tone == "failure":
            pygame.draw.circle(surface, PALETTE["russet"], (int(cx), int(cy)), 7)
    else:
        # faint cool facing dot on an empty cell (never black)
        pygame.draw.circle(surface, PALETTE["twilight_violet"],
                           (int(cx), int(cy)), 3)


def draw_controls_hint(surface):
    """Top-right, always-visible controls line (from inputmap.CONTROLS_HINT)."""
    from . import inputmap
    draw_hint(surface, inputmap.CONTROLS_HINT)


def draw_prompt(surface, text, tone=None):
    """Centered one-line interaction prompt / result feedback (tone-colored)."""
    font = _font(20)
    w = font.size(text)[0] + 32
    x = (surface.get_width() - w) // 2
    y = surface.get_height() - 134
    _blit_panel(surface, x, y, w, 30, PALETTE["cream_parch"], 236, radius=8)
    color = _tone_accent(tone) if tone else PALETTE["bark_brown"]
    surface.blit(font.render(text, True, color), (x + 16, y + 6))
