"""Right-hand side panel: timer, moves, buttons, solver dropdown and metrics.

Role: lays out and draws the 300x700 HUD and turns mouse clicks on it into
``Action`` objects. The game loop feeds it a ``HudView`` snapshot every frame,
so the HUD holds only widget state (hover, dropdown open, selected size/solver).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import pygame

from ui.input_handler import Action, ActionType
from ui.theme import FontCache, Theme, draw_text
from utils.config import (
    BOARD_SIZES,
    DEFAULT_BOARD_SIZE,
    FONT_SIZE_LABEL,
    FONT_SIZE_SMALL,
    FONT_SIZE_TIMER,
    FONT_SIZE_TITLE,
    GRID_PANEL_SIZE,
    HUD_BUTTON_GAP,
    HUD_BUTTON_HEIGHT,
    HUD_CORNER_RADIUS,
    HUD_DROPDOWN_HEIGHT,
    HUD_METRICS_HEIGHT,
    HUD_METRICS_LINE_HEIGHT,
    HUD_PADDING,
    HUD_SECTION_GAP,
    HUD_SHORTCUT_LINE_HEIGHT,
    HUD_SHORTCUT_LINES,
    HUD_SIZE_BUTTON_GAP,
    HUD_SIZE_BUTTON_HEIGHT,
    HUD_TOP,
    PANEL_INNER_PADDING,
    SIDE_PANEL_WIDTH,
)


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS."""
    total = int(seconds)
    return f"{total // 60:02d}:{total % 60:02d}"


@dataclass
class Button:
    """A clickable rounded rectangle."""

    label: str
    rect: pygame.Rect
    action: Action
    enabled: bool = True
    selected: bool = False


@dataclass
class HudView:
    """Per-frame data the HUD displays.

    Attributes:
        elapsed_s: Timer value in seconds.
        moves: Move counter.
        metrics: Last solver metrics (solver, nodes_explored, time_ms, solution_length).
        live_nodes: Running node count while a search is in progress, else None.
        best_text: Leaderboard line for the current board size.
        board_size: Current board width.
        busy: A background search is running.
        autoplaying: The AI is currently playing its solution.
        won: The puzzle is solved.
    """

    elapsed_s: float = 0.0
    moves: int = 0
    metrics: dict[str, Any] | None = None
    live_nodes: int | None = None
    best_text: str = ""
    board_size: int = DEFAULT_BOARD_SIZE
    busy: bool = False
    autoplaying: bool = False
    won: bool = False


class Dropdown:
    """A simple solver selector that expands downward."""

    def __init__(self, rect: pygame.Rect, options: Sequence[str], selected: int) -> None:
        self.rect = rect
        self.options = list(options)
        self.selected = selected
        self.is_open = False

    def option_rect(self, index: int) -> pygame.Rect:
        """Rectangle of option ``index`` in the expanded list."""
        return pygame.Rect(self.rect.x, self.rect.bottom + index * self.rect.height,
                           self.rect.width, self.rect.height)


class Hud:
    """The side panel.

    Args:
        theme: Active colour theme.
        fonts: Shared font cache.
        board_size: Initially selected board size.
        solver_options: Labels shown in the solver dropdown.
        solver_index: Initially selected solver.
    """

    def __init__(
        self,
        theme: Theme,
        fonts: FontCache,
        board_size: int,
        solver_options: Sequence[str],
        solver_index: int,
    ) -> None:
        self.theme = theme
        self.fonts = fonts
        self._mouse: tuple[int, int] = (-1, -1)

        x = GRID_PANEL_SIZE + HUD_PADDING
        width = SIDE_PANEL_WIDTH - 2 * HUD_PADDING
        y = HUD_TOP

        self._title_pos = (x, y)
        y += FONT_SIZE_TITLE + 4
        self._timer_pos = (x, y)
        y += FONT_SIZE_TIMER + 2
        self._moves_pos = (x, y)
        y += FONT_SIZE_LABEL + 4 + HUD_SECTION_GAP

        # board-size selector row
        count = len(BOARD_SIZES)
        size_w = (width - (count - 1) * HUD_SIZE_BUTTON_GAP) // count
        self.size_buttons: list[Button] = []
        for i, size in enumerate(BOARD_SIZES):
            rect = pygame.Rect(x + i * (size_w + HUD_SIZE_BUTTON_GAP), y, size_w, HUD_SIZE_BUTTON_HEIGHT)
            self.size_buttons.append(Button(f"{size}x{size}", rect, Action(ActionType.SET_SIZE, size),
                                            selected=size == board_size))
        y += HUD_SIZE_BUTTON_HEIGHT + HUD_SECTION_GAP

        self.dropdown = Dropdown(pygame.Rect(x, y, width, HUD_DROPDOWN_HEIGHT), solver_options, solver_index)
        y += HUD_DROPDOWN_HEIGHT + HUD_SECTION_GAP

        def make_button(label: str, action_type: ActionType) -> Button:
            nonlocal y
            button = Button(label, pygame.Rect(x, y, width, HUD_BUTTON_HEIGHT), Action(action_type))
            y += HUD_BUTTON_HEIGHT + HUD_BUTTON_GAP
            return button

        self.btn_new = make_button("New Game (R)", ActionType.NEW_GAME)
        self.btn_hint = make_button("Hint (H)", ActionType.HINT)
        self.btn_auto = make_button("Auto-Solve (S)", ActionType.AUTO_SOLVE)
        self.buttons = [self.btn_new, self.btn_hint, self.btn_auto]
        y += HUD_SECTION_GAP - HUD_BUTTON_GAP

        self._metrics_rect = pygame.Rect(x, y, width, HUD_METRICS_HEIGHT)
        y += HUD_METRICS_HEIGHT + HUD_SECTION_GAP // 2
        self._best_pos = (x, y)
        y += FONT_SIZE_SMALL + 4 + HUD_SECTION_GAP // 2
        self._shortcuts_pos = (x, y)

    # ------------------------------------------------------------------ input
    @property
    def solver_index(self) -> int:
        """Index of the solver chosen in the dropdown."""
        return self.dropdown.selected

    def set_theme(self, theme: Theme) -> None:
        """Switch colour theme."""
        self.theme = theme

    def set_board_size(self, size: int) -> None:
        """Highlight the selected board size."""
        for button in self.size_buttons:
            button.selected = button.action.value == size

    def handle_motion(self, pos: tuple[int, int]) -> None:
        """Track the mouse for hover effects."""
        self._mouse = pos

    def handle_click(self, pos: tuple[int, int]) -> Action | None:
        """Return the action for a click on the HUD, or None if it hit nothing."""
        dd = self.dropdown
        if dd.is_open:
            for i in range(len(dd.options)):
                if dd.option_rect(i).collidepoint(pos):
                    dd.selected = i
                    dd.is_open = False
                    return Action(ActionType.SET_SOLVER, i)
            dd.is_open = False
            if dd.rect.collidepoint(pos):
                return None
        elif dd.rect.collidepoint(pos):
            dd.is_open = True
            return None
        for button in self.size_buttons + self.buttons:
            if button.enabled and button.rect.collidepoint(pos):
                return button.action
        return None

    # ------------------------------------------------------------------ drawing
    def draw(self, surface: pygame.Surface, view: HudView) -> None:
        """Draw the whole panel for the given frame snapshot."""
        self._sync_buttons(view)
        t = self.theme
        panel = pygame.Rect(GRID_PANEL_SIZE, 0, SIDE_PANEL_WIDTH, surface.get_height())
        pygame.draw.rect(surface, t["panel"], panel)
        pygame.draw.line(surface, t["panel_border"], panel.topleft, panel.bottomleft)

        draw_text(surface, self.fonts, "AI Puzzle Solver", FONT_SIZE_TITLE, t["accent"], topleft=self._title_pos)
        timer_color = t["success"] if view.won else t["text"]
        draw_text(surface, self.fonts, format_time(view.elapsed_s), FONT_SIZE_TIMER, timer_color,
                  topleft=self._timer_pos)
        draw_text(surface, self.fonts, f"Moves: {view.moves}", FONT_SIZE_LABEL, t["text_muted"],
                  topleft=self._moves_pos)

        for button in self.size_buttons:
            self._draw_button(surface, button)
        for button in self.buttons:
            self._draw_button(surface, button)
        self._draw_metrics(surface, view)
        draw_text(surface, self.fonts, view.best_text, FONT_SIZE_SMALL, t["text_muted"], topleft=self._best_pos)
        for i, line in enumerate(HUD_SHORTCUT_LINES):
            draw_text(surface, self.fonts, line, FONT_SIZE_SMALL, t["text_muted"],
                      topleft=(self._shortcuts_pos[0], self._shortcuts_pos[1] + i * HUD_SHORTCUT_LINE_HEIGHT))
        self._draw_dropdown(surface)  # last, so the open list overlays the buttons

    def _sync_buttons(self, view: HudView) -> None:
        searching = view.busy or view.autoplaying
        self.set_board_size(view.board_size)
        self.btn_hint.enabled = not searching and not view.won
        self.btn_auto.label = "Stop (S)" if searching else "Auto-Solve (S)"
        self.btn_auto.enabled = searching or not view.won

    def _draw_button(self, surface: pygame.Surface, button: Button) -> None:
        t = self.theme
        hovered = button.enabled and button.rect.collidepoint(self._mouse)
        if not button.enabled:
            fill, text_color = t["button_disabled"], t["button_text_disabled"]
        elif button.selected:
            fill, text_color = t["accent"], t["tile_text"]
        else:
            fill, text_color = (t["button_hover"] if hovered else t["button"]), t["button_text"]
        pygame.draw.rect(surface, fill, button.rect, border_radius=HUD_CORNER_RADIUS)
        draw_text(surface, self.fonts, button.label, FONT_SIZE_LABEL, text_color, center=button.rect.center)

    def _draw_dropdown(self, surface: pygame.Surface) -> None:
        t, dd = self.theme, self.dropdown
        pygame.draw.rect(surface, t["button"], dd.rect, border_radius=HUD_CORNER_RADIUS)
        pygame.draw.rect(surface, t["panel_border"], dd.rect, width=1, border_radius=HUD_CORNER_RADIUS)
        draw_text(surface, self.fonts, dd.options[dd.selected], FONT_SIZE_LABEL, t["button_text"],
                  midleft=(dd.rect.x + PANEL_INNER_PADDING, dd.rect.centery))
        cx, cy = dd.rect.right - PANEL_INNER_PADDING - 4, dd.rect.centery
        pygame.draw.polygon(surface, t["text_muted"], [(cx - 5, cy - 3), (cx + 5, cy - 3), (cx, cy + 4)])
        if not dd.is_open:
            return
        for i, label in enumerate(dd.options):
            rect = dd.option_rect(i)
            hovered = rect.collidepoint(self._mouse)
            fill = t["accent"] if i == dd.selected else (t["button_hover"] if hovered else t["button"])
            color = t["tile_text"] if i == dd.selected else t["button_text"]
            pygame.draw.rect(surface, fill, rect, border_radius=HUD_CORNER_RADIUS)
            pygame.draw.rect(surface, t["panel_border"], rect, width=1, border_radius=HUD_CORNER_RADIUS)
            draw_text(surface, self.fonts, label, FONT_SIZE_LABEL, color,
                      midleft=(rect.x + PANEL_INNER_PADDING, rect.centery))

    def _draw_metrics(self, surface: pygame.Surface, view: HudView) -> None:
        t, rect = self.theme, self._metrics_rect
        pygame.draw.rect(surface, t["background"], rect, border_radius=HUD_CORNER_RADIUS)
        pygame.draw.rect(surface, t["panel_border"], rect, width=1, border_radius=HUD_CORNER_RADIUS)

        metrics = view.metrics or {}
        searching = view.live_nodes is not None
        nodes = view.live_nodes if searching else metrics.get("nodes_explored")
        time_ms = metrics.get("time_ms")
        length = metrics.get("solution_length")
        rows = [
            ("Solver", str(metrics.get("solver", "--"))),
            ("Nodes explored", "--" if nodes is None else f"{nodes:,}"),
            ("Time", "..." if searching else ("--" if time_ms is None else f"{time_ms:,.1f} ms")),
            ("Solution length", "..." if searching else ("--" if length is None else str(length))),
        ]
        x, y = rect.x + PANEL_INNER_PADDING, rect.y + PANEL_INNER_PADDING // 2
        draw_text(surface, self.fonts, "Metrics", FONT_SIZE_LABEL, t["accent"], topleft=(x, y))
        y += HUD_METRICS_LINE_HEIGHT
        for label, value in rows:
            draw_text(surface, self.fonts, label, FONT_SIZE_SMALL, t["text_muted"], topleft=(x, y))
            draw_text(surface, self.fonts, value, FONT_SIZE_LABEL, t["text"],
                      topright=(rect.right - PANEL_INNER_PADDING, y - 2))
            y += HUD_METRICS_LINE_HEIGHT


if __name__ == "__main__":
    print(format_time(0), format_time(75), format_time(3599))
