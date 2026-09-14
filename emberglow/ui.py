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


def draw_dialogue(surface, speaker, text, y):
    """Short modal text panel (1-2 cozy sentences)."""
    font = _font(24)
    font_s = _font(26)
    max_w = surface.get_width() - 320
    lines = _wrap(text, font, max_w - 80)
    w = surface.get_width() - 320
    h = 40 + len(lines) * 30
    x = (surface.get_width() - w) // 2
    _blit_panel(surface, x, y, w, h, PALETTE["cream_parch"], 246)
    name = font_s.render(speaker, True, PALETTE["russet"])
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
