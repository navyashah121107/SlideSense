"""Live search visualisation and the BFS-vs-A* comparison overlay.

Role: (1) while a solver runs in the background, show the explored-state count
climbing together with a sparkline of nodes over time; (2) render the side-by-side
comparison cards (nodes, time, length, optimality) with bars scaled to the
costliest solver, which makes A*'s pruning visible at a glance.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import pygame

from ui.theme import FontCache, Theme, draw_text, wrap_text
from utils.config import (
    COMPARISON_BAR_HEIGHT,
    COMPARISON_GAP,
    COMPARISON_MARGIN,
    COMPARISON_OVERLAY_ALPHA,
    COMPARISON_ROW_GAP,
    FONT_SIZE_BIG_NUMBER,
    FONT_SIZE_CARD_TITLE,
    FONT_SIZE_LABEL,
    FONT_SIZE_SMALL,
    GRID_CORNER_RADIUS,
    PANEL_CORNER_RADIUS,
    PANEL_INNER_PADDING,
    SPARKLINE_MAX_POINTS,
    SPARKLINE_WIDTH,
    SPINNER_DOTS,
    SPINNER_PERIOD_MS,
)


def downsample(points: Sequence[tuple[float, int]], limit: int = SPARKLINE_MAX_POINTS) -> list[tuple[float, int]]:
    """Reduce ``points`` to at most ``limit`` evenly spaced samples (keeps the last)."""
    if len(points) <= limit:
        return list(points)
    step = len(points) / limit
    sampled = [points[int(i * step)] for i in range(limit - 1)]
    sampled.append(points[-1])
    return sampled


class SearchVisualizer:
    """Bottom-left panel: live counter while searching, status text otherwise."""

    def __init__(self, fonts: FontCache) -> None:
        self.fonts = fonts

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        theme: Theme,
        *,
        active: bool,
        label: str,
        nodes: int,
        history: Sequence[tuple[float, int]],
        status: str,
        now_ms: int,
    ) -> None:
        """Draw the panel.

        Args:
            surface: Target surface.
            rect: Panel rectangle.
            theme: Colour theme.
            active: True while a search is running.
            label: Name of the running solver.
            nodes: States explored so far.
            history: ``(seconds, nodes)`` samples for the sparkline.
            status: Message shown when idle.
            now_ms: Current time in ms (drives the spinner).
        """
        pygame.draw.rect(surface, theme["panel"], rect, border_radius=PANEL_CORNER_RADIUS)
        pygame.draw.rect(surface, theme["panel_border"], rect, width=1, border_radius=PANEL_CORNER_RADIUS)
        pad = PANEL_INNER_PADDING
        if not active:
            draw_text(surface, self.fonts, status, FONT_SIZE_LABEL, theme["text"],
                      midleft=(rect.x + pad, rect.centery))
            return

        draw_text(surface, self.fonts, f"Searching with {label}", FONT_SIZE_SMALL, theme["text_muted"],
                  topleft=(rect.x + pad, rect.y + pad))
        draw_text(surface, self.fonts, f"{nodes:,} states explored", FONT_SIZE_BIG_NUMBER, theme["accent"],
                  topleft=(rect.x + pad, rect.y + pad + FONT_SIZE_SMALL + 6))
        self._draw_spinner(surface, theme, (rect.x + pad, rect.bottom - pad), now_ms)
        spark = pygame.Rect(rect.centerx + pad * 2, rect.y + pad, rect.width // 2 - pad * 3, rect.height - 2 * pad)
        self._draw_sparkline(surface, spark, theme, history)

    def _draw_spinner(self, surface: pygame.Surface, theme: Theme, origin: tuple[int, int], now_ms: int) -> None:
        active_dot = int((now_ms % SPINNER_PERIOD_MS) / SPINNER_PERIOD_MS * SPINNER_DOTS)
        for i in range(SPINNER_DOTS):
            color = theme["accent"] if i == active_dot else theme["bar_track"]
            pygame.draw.circle(surface, color, (origin[0] + 6 + i * 16, origin[1] - 6), 5)

    def _draw_sparkline(self, surface: pygame.Surface, rect: pygame.Rect, theme: Theme,
                        history: Sequence[tuple[float, int]]) -> None:
        pygame.draw.rect(surface, theme["background"], rect, border_radius=PANEL_CORNER_RADIUS // 2)
        samples = downsample(history)
        if len(samples) < 2:
            return
        max_t = max(samples[-1][0], 1e-6)
        max_n = max(samples[-1][1], 1)
        points = [
            (rect.x + s[0] / max_t * (rect.width - 1), rect.bottom - 1 - s[1] / max_n * (rect.height - 1))
            for s in samples
        ]
        pygame.draw.lines(surface, theme["accent"], False, points, SPARKLINE_WIDTH)


def _speedup_text(metrics: Mapping[str, Mapping[str, Any]]) -> str | None:
    """Sentence comparing BFS with the best A* variant, if both solved the board."""
    bfs = metrics.get("BFS")
    astar = [(n, m) for n, m in metrics.items() if n.startswith("A*") and m["solved"]]
    if not bfs or not bfs["solved"] or not astar:
        return None
    name, best = min(astar, key=lambda item: item[1]["nodes_explored"])
    if best["nodes_explored"] <= 0:
        return None
    ratio = bfs["nodes_explored"] / best["nodes_explored"]
    return f"{name} explored {ratio:,.1f}x fewer states than BFS"


def draw_comparison_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    metrics: Mapping[str, Mapping[str, Any]],
    theme: Theme,
    fonts: FontCache,
) -> None:
    """Draw the comparison overlay on top of the puzzle grid.

    Args:
        surface: Target surface.
        rect: Area to cover (the grid rectangle).
        metrics: Output of ``ai.comparator.compare_solvers``.
        theme: Colour theme.
        fonts: Shared font cache.
    """
    overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(overlay, (*theme["panel"], COMPARISON_OVERLAY_ALPHA), overlay.get_rect(),
                     border_radius=GRID_CORNER_RADIUS)
    surface.blit(overlay, rect.topleft)
    pygame.draw.rect(surface, theme["panel_border"], rect, width=1, border_radius=GRID_CORNER_RADIUS)

    draw_text(surface, fonts, "BFS vs A* on this board", FONT_SIZE_BIG_NUMBER, theme["text"],
              midtop=(rect.centerx, rect.y + COMPARISON_MARGIN))

    names = list(metrics)
    top = rect.y + COMPARISON_MARGIN * 3
    card_h = rect.height - (top - rect.y) - COMPARISON_MARGIN * 3
    card_w = (rect.width - 2 * COMPARISON_MARGIN - (len(names) - 1) * COMPARISON_GAP) // max(len(names), 1)
    max_nodes = max([m["nodes_explored"] for m in metrics.values() if m["solved"]] or [1])
    pad = PANEL_INNER_PADDING

    for i, name in enumerate(names):
        m = metrics[name]
        card = pygame.Rect(rect.x + COMPARISON_MARGIN + i * (card_w + COMPARISON_GAP), top, card_w, card_h)
        pygame.draw.rect(surface, theme["background"], card, border_radius=PANEL_CORNER_RADIUS)
        pygame.draw.rect(surface, theme["panel_border"], card, width=1, border_radius=PANEL_CORNER_RADIUS)
        x, y = card.x + pad, card.y + pad
        for line in wrap_text(name, fonts, FONT_SIZE_CARD_TITLE, card_w - 2 * pad)[:2]:
            draw_text(surface, fonts, line, FONT_SIZE_CARD_TITLE, theme["accent"], topleft=(x, y))
            y += FONT_SIZE_CARD_TITLE + 2
        y = card.y + pad + 2 * (FONT_SIZE_CARD_TITLE + 2) + COMPARISON_ROW_GAP

        if not m["solved"]:
            draw_text(surface, fonts, "Skipped", FONT_SIZE_LABEL, theme["danger"], topleft=(x, y))
            y += FONT_SIZE_LABEL + 6
            for line in wrap_text(str(m["error"]), fonts, FONT_SIZE_SMALL, card_w - 2 * pad):
                draw_text(surface, fonts, line, FONT_SIZE_SMALL, theme["text_muted"], topleft=(x, y))
                y += FONT_SIZE_SMALL + 2
            continue

        draw_text(surface, fonts, "States explored", FONT_SIZE_SMALL, theme["text_muted"], topleft=(x, y))
        y += FONT_SIZE_SMALL + 2
        draw_text(surface, fonts, f"{m['nodes_explored']:,}", FONT_SIZE_BIG_NUMBER, theme["text"], topleft=(x, y))
        y += FONT_SIZE_BIG_NUMBER + 4
        track = pygame.Rect(x, y, card_w - 2 * pad, COMPARISON_BAR_HEIGHT)
        pygame.draw.rect(surface, theme["bar_track"], track, border_radius=COMPARISON_BAR_HEIGHT // 2)
        fill = track.copy()
        fill.width = max(COMPARISON_BAR_HEIGHT, int(track.width * m["nodes_explored"] / max_nodes))
        pygame.draw.rect(surface, theme["accent"], fill, border_radius=COMPARISON_BAR_HEIGHT // 2)
        y += COMPARISON_BAR_HEIGHT + COMPARISON_ROW_GAP

        for label, value in (
            ("Time", f"{m['time_ms']:,.1f} ms"),
            ("Solution length", f"{m['solution_length']} moves"),
            ("Optimal", "Yes" if m["optimal"] else "No"),
        ):
            draw_text(surface, fonts, label, FONT_SIZE_SMALL, theme["text_muted"], topleft=(x, y))
            y += FONT_SIZE_SMALL + 2
            color = theme["success"] if (label == "Optimal" and m["optimal"]) else theme["text"]
            draw_text(surface, fonts, value, FONT_SIZE_LABEL, color, topleft=(x, y))
            y += FONT_SIZE_LABEL + COMPARISON_ROW_GAP

    summary = _speedup_text(metrics)
    footer_y = rect.bottom - COMPARISON_MARGIN - FONT_SIZE_LABEL
    if summary:
        draw_text(surface, fonts, summary, FONT_SIZE_LABEL, theme["success"],
                  midbottom=(rect.centerx, footer_y - 6))
    draw_text(surface, fonts, "Press C, Esc or click to close", FONT_SIZE_SMALL, theme["text_muted"],
              midbottom=(rect.centerx, rect.bottom - COMPARISON_MARGIN // 2))


if __name__ == "__main__":
    sample = [(i * 0.01, i * 100) for i in range(1000)]
    print("downsampled points:", len(downsample(sample)), "| last:", downsample(sample)[-1])
