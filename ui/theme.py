"""Colour themes and small drawing helpers.

Role: DARK and LIGHT colour dictionaries, the blue -> green -> yellow -> red
tile gradient, a lazily-initialised ``FontCache`` and a ``draw_text`` helper.
Importing this module does not touch pygame; pygame is imported only when a
font is actually requested.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from utils.config import COLORS, FONTS_DIR, TILE_GRADIENT_STOPS, Color

Theme = dict[str, Color]

DARK: Theme = {
    "background": (24, 26, 32),
    "grid_bg": (38, 41, 52),
    "slot": (30, 32, 41),
    "panel": (33, 36, 46),
    "panel_border": (58, 62, 78),
    "text": (236, 239, 245),
    "text_muted": (150, 157, 175),
    "tile_text": (255, 255, 255),
    "tile_shadow": (0, 0, 0),
    "accent": (92, 156, 255),
    "hint": (255, 214, 10),
    "success": (80, 220, 140),
    "danger": (255, 99, 99),
    "button": (52, 58, 78),
    "button_hover": (70, 78, 104),
    "button_disabled": (40, 43, 55),
    "button_text": (236, 239, 245),
    "button_text_disabled": (110, 116, 132),
    "bar_track": (50, 54, 70),
}

LIGHT: Theme = {
    "background": (240, 242, 247),
    "grid_bg": (210, 215, 226),
    "slot": (196, 202, 216),
    "panel": (255, 255, 255),
    "panel_border": (205, 210, 222),
    "text": (30, 34, 44),
    "text_muted": (110, 116, 132),
    "tile_text": (255, 255, 255),
    "tile_shadow": (0, 0, 0),
    "accent": (37, 99, 235),
    "hint": (245, 158, 11),
    "success": (22, 163, 74),
    "danger": (220, 38, 38),
    "button": (226, 231, 242),
    "button_hover": (208, 215, 232),
    "button_disabled": (236, 238, 244),
    "button_text": (30, 34, 44),
    "button_text_disabled": (160, 166, 180),
    "bar_track": (222, 226, 236),
}

THEMES: dict[str, Theme] = {"dark": DARK, "light": LIGHT}


def get_theme(name: str) -> Theme:
    """Return the colour dictionary for ``name`` ("dark" or "light")."""
    return THEMES[name]


def next_theme_name(current: str) -> str:
    """Return the theme that follows ``current`` when toggling."""
    names = list(THEMES)
    return names[(names.index(current) + 1) % len(names)]


def lerp_color(a: Color, b: Color, t: float) -> Color:
    """Linearly interpolate between two colours (``t`` clamped to 0..1)."""
    t = max(0.0, min(1.0, t))
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


def shade(color: Color, amount: float) -> Color:
    """Lighten (amount > 0) toward white or darken (amount < 0) toward black."""
    target = COLORS["white"] if amount > 0 else COLORS["black"]
    return lerp_color(color, target, abs(amount))


def gradient_color(t: float, stops: Sequence[Color] = TILE_GRADIENT_STOPS) -> Color:
    """Sample a multi-stop gradient at ``t`` in 0..1."""
    t = max(0.0, min(1.0, t))
    scaled = t * (len(stops) - 1)
    index = min(int(scaled), len(stops) - 2)
    return lerp_color(stops[index], stops[index + 1], scaled - index)


def tile_gradient_color(value: int, total_cells: int) -> Color:
    """Colour of tile ``value`` (1..total_cells-1): blue for 1 up to red for the last."""
    last = total_cells - 1
    return gradient_color((value - 1) / (last - 1)) if last > 1 else gradient_color(0.0)


def _find_font_file() -> Path | None:
    """First .ttf/.otf in ``assets/fonts`` if the user dropped one in."""
    if FONTS_DIR.is_dir():
        for pattern in ("*.ttf", "*.otf"):
            for candidate in sorted(FONTS_DIR.glob(pattern)):
                return candidate
    return None


class FontCache:
    """Lazily creates and caches ``pygame.font.Font`` objects by pixel size."""

    def __init__(self, font_path: Path | None = None) -> None:
        self._path = font_path if font_path is not None else _find_font_file()
        self._fonts: dict[int, Any] = {}

    def get(self, size: int) -> Any:
        """Return a font of ``size`` pixels (pygame default font if no file)."""
        if size not in self._fonts:
            import pygame

            self._fonts[size] = pygame.font.Font(str(self._path) if self._path else None, size)
        return self._fonts[size]


def draw_text(
    surface: Any,
    fonts: FontCache,
    text: str,
    size: int,
    color: Color,
    **anchor: tuple[float, float],
) -> Any:
    """Render ``text`` and blit it; ``anchor`` is a pygame rect kwarg like ``topleft=(x, y)``.

    Returns:
        The rect the text occupies.
    """
    image = fonts.get(size).render(text, True, color)
    rect = image.get_rect(**anchor)
    surface.blit(image, rect)
    return rect


def wrap_text(text: str, fonts: FontCache, size: int, max_width: int) -> list[str]:
    """Greedy word-wrap ``text`` so each line fits ``max_width`` pixels."""
    font = fonts.get(size)
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if current and font.size(candidate)[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


if __name__ == "__main__":
    print("themes:", list(THEMES))
    for tile in (1, 4, 8):
        print(f"tile {tile} colour (3x3):", tile_gradient_color(tile, 9))
