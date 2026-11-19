"""Draws the puzzle grid, gradient tiles, hint pulse, win glow and particles.

Role: all drawing of the left-hand puzzle area. Tiles are pre-rendered once
(vertical gradient, rounded corners, number) and cached, so a frame is just a
handful of blits. The renderer is stateless about the game: ``main`` passes in
the board and any animation overrides.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import pygame

from ui.animator import Particle, Point
from ui.theme import FontCache, Theme, draw_text, get_theme, lerp_color, shade, tile_gradient_color
from game.board import Board
from utils.config import (
    BLANK,
    GRID_CORNER_RADIUS,
    GRID_MARGIN,
    GRID_PIXELS,
    HINT_ALPHA_MAX,
    HINT_ALPHA_MIN,
    HINT_BORDER_MAX,
    HINT_BORDER_MIN,
    TILE_CORNER_RADIUS,
    TILE_FONT_RATIO,
    TILE_PADDING,
    TILE_SHADE,
    TILE_SHADOW_OFFSET,
    GLOW_MIN_STRENGTH,
    WIN_GLOW_ALPHA_MAX,
    WIN_GLOW_BORDER,
    WIN_GLOW_LAYERS,
    WIN_GLOW_SPREAD,
)


class Renderer:
    """Renders the board onto a pygame surface.

    Args:
        screen: The window surface.
        theme_name: "dark" or "light".
        fonts: Shared font cache.
    """

    def __init__(self, screen: pygame.Surface, theme_name: str, fonts: FontCache) -> None:
        self.screen = screen
        self.fonts = fonts
        self.theme_name = theme_name
        self.theme: Theme = get_theme(theme_name)
        self.grid_rect = pygame.Rect(GRID_MARGIN, GRID_MARGIN, GRID_PIXELS, GRID_PIXELS)
        self._tile_cache: dict[tuple[int, int, int, str], pygame.Surface] = {}

    # ------------------------------------------------------------------ geometry
    def set_theme(self, theme_name: str) -> None:
        """Switch colour theme (cached tiles are rebuilt lazily)."""
        self.theme_name = theme_name
        self.theme = get_theme(theme_name)

    def index_to_pos(self, index: int, size: int) -> Point:
        """Pixel top-left of the *cell* at flat ``index``."""
        cell = self.grid_rect.width / size
        row, col = divmod(index, size)
        return (self.grid_rect.x + col * cell, self.grid_rect.y + row * cell)

    def tile_pixels(self, size: int) -> int:
        """Side length in pixels of a drawn tile."""
        return max(1, int(self.grid_rect.width / size - 2 * TILE_PADDING))

    def _tile_rect(self, cell_pos: Point, px: int) -> pygame.Rect:
        return pygame.Rect(round(cell_pos[0] + TILE_PADDING), round(cell_pos[1] + TILE_PADDING), px, px)

    # ------------------------------------------------------------------ drawing
    def clear(self) -> None:
        """Fill the whole window with the background colour."""
        self.screen.fill(self.theme["background"])

    def draw_board(
        self,
        board: Board,
        slide_positions: Mapping[int, Point],
        hint_index: int | None = None,
        hint_phase: float = 0.0,
        glow_phase: float | None = None,
    ) -> None:
        """Draw the grid and tiles.

        Args:
            board: Current position (already updated for any running slide).
            slide_positions: Tile value -> animated cell position override.
            hint_index: Flat index of the tile to highlight with a pulsing border.
            hint_phase: 0..1 pulse value for the hint border.
            glow_phase: 0..1 pulse for the win glow, or None when not won.
        """
        size = board.size
        px = self.tile_pixels(size)
        pygame.draw.rect(self.screen, self.theme["grid_bg"], self.grid_rect, border_radius=GRID_CORNER_RADIUS)
        for index in range(size * size):
            slot = self._tile_rect(self.index_to_pos(index, size), px)
            pygame.draw.rect(self.screen, self.theme["slot"], slot, border_radius=TILE_CORNER_RADIUS)

        moving: list[tuple[int, Point]] = []
        glow_rects: list[pygame.Rect] = []
        total = size * size
        for index, value in enumerate(board.tiles):
            if value == BLANK:
                continue
            if value in slide_positions:
                moving.append((value, slide_positions[value]))
                continue
            rect = self._tile_rect(self.index_to_pos(index, size), px)
            self.screen.blit(self._tile_surface(value, px, total), rect)
            glow_rects.append(rect)
        for value, cell_pos in moving:
            rect = self._tile_rect(cell_pos, px)
            self.screen.blit(self._tile_surface(value, px, total), rect)

        if glow_phase is not None:
            for rect in glow_rects:
                self._draw_glow(rect, glow_phase)
        if hint_index is not None and glow_phase is None:
            rect = self._tile_rect(self.index_to_pos(hint_index, size), px)
            width = round(HINT_BORDER_MIN + (HINT_BORDER_MAX - HINT_BORDER_MIN) * hint_phase)
            alpha = round(HINT_ALPHA_MIN + (HINT_ALPHA_MAX - HINT_ALPHA_MIN) * hint_phase)
            self._draw_alpha_border(rect.inflate(width, width), self.theme["hint"], width, alpha)

    def draw_particles(self, particles: Sequence[Particle]) -> None:
        """Draw confetti, shrinking each particle as it fades."""
        for p in particles:
            radius = max(1, round(p.radius * p.fade))
            pygame.draw.circle(self.screen, p.color, (round(p.x), round(p.y)), radius)

    # ------------------------------------------------------------------ helpers
    def _draw_alpha_border(self, rect: pygame.Rect, color: tuple[int, int, int], width: int, alpha: int) -> None:
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            overlay, (*color, alpha), overlay.get_rect(), width=max(1, width), border_radius=TILE_CORNER_RADIUS
        )
        self.screen.blit(overlay, rect.topleft)

    def _draw_glow(self, rect: pygame.Rect, phase: float) -> None:
        strength = GLOW_MIN_STRENGTH + (1 - GLOW_MIN_STRENGTH) * phase
        for layer in range(WIN_GLOW_LAYERS):
            spread = WIN_GLOW_SPREAD * (layer + 1)
            alpha = round(WIN_GLOW_ALPHA_MAX * strength * (1 - layer / WIN_GLOW_LAYERS))
            self._draw_alpha_border(rect.inflate(spread, spread), self.theme["success"], WIN_GLOW_BORDER, alpha)

    def _tile_surface(self, value: int, px: int, total: int) -> pygame.Surface:
        """Build (or fetch) the cached surface for one numbered tile."""
        key = (value, px, total, self.theme_name)
        cached = self._tile_cache.get(key)
        if cached is not None:
            return cached

        base = tile_gradient_color(value, total)
        top, bottom = shade(base, TILE_SHADE), shade(base, -TILE_SHADE)
        surface = pygame.Surface((px, px), pygame.SRCALPHA)
        for y in range(px):
            line_color = lerp_color(top, bottom, y / max(px - 1, 1))
            pygame.draw.line(surface, line_color, (0, y), (px - 1, y))

        mask = pygame.Surface((px, px), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=TILE_CORNER_RADIUS)
        surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        font_size = max(8, int(px * TILE_FONT_RATIO))
        center = (px // 2, px // 2)
        draw_text(surface, self.fonts, str(value), font_size, self.theme["tile_shadow"],
                  center=(center[0] + TILE_SHADOW_OFFSET, center[1] + TILE_SHADOW_OFFSET))
        draw_text(surface, self.fonts, str(value), font_size, self.theme["tile_text"], center=center)

        self._tile_cache[key] = surface
        return surface


if __name__ == "__main__":
    pygame.init()
    demo_screen = pygame.display.set_mode((600, 600))
    demo_renderer = Renderer(demo_screen, "dark", FontCache())
    demo_renderer.clear()
    demo_renderer.draw_board(Board.goal(4).slide(14), {}, hint_index=10, hint_phase=0.5)
    pygame.display.flip()
    pygame.time.wait(1500)
    pygame.quit()
