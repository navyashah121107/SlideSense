"""Translate raw pygame events into game ``Action`` objects.

Role: the only module that knows which key or click means what. The main loop
asks ``InputHandler.translate(event, board_size)`` and receives an ``Action``
(or None), keeping pygame details out of the game logic. Keyboard map:
arrows slide a tile into the blank, H hint, S auto-solve,
R rescramble, T theme, Z/Y undo/redo, 3/4/5 board size, Esc cancel.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

import pygame

from utils.config import (
    BOARD_SIZES,
    DIRECTION_DOWN,
    DIRECTION_LEFT,
    DIRECTION_RIGHT,
    DIRECTION_UP,
)


class ActionType(Enum):
    """Everything the player can ask the game to do."""

    QUIT = auto()
    NEW_GAME = auto()
    HINT = auto()
    AUTO_SOLVE = auto()
    TOGGLE_THEME = auto()
    SLIDE_INDEX = auto()      # value: flat tile index (mouse click)
    SLIDE_DIRECTION = auto()  # value: (d_row, d_col) the tile travels (arrow key)
    SET_SIZE = auto()         # value: board size
    SET_SOLVER = auto()       # value: index into SOLVER_OPTIONS
    UNDO = auto()
    REDO = auto()
    CANCEL = auto()


@dataclass(frozen=True)
class Action:
    """A user intent, optionally carrying a value."""

    type: ActionType
    value: int | tuple[int, int] | None = None


_KEY_ACTIONS: dict[int, Action] = {
    pygame.K_UP: Action(ActionType.SLIDE_DIRECTION, DIRECTION_UP),
    pygame.K_DOWN: Action(ActionType.SLIDE_DIRECTION, DIRECTION_DOWN),
    pygame.K_LEFT: Action(ActionType.SLIDE_DIRECTION, DIRECTION_LEFT),
    pygame.K_RIGHT: Action(ActionType.SLIDE_DIRECTION, DIRECTION_RIGHT),
    pygame.K_h: Action(ActionType.HINT),
    pygame.K_s: Action(ActionType.AUTO_SOLVE),
    pygame.K_r: Action(ActionType.NEW_GAME),
    pygame.K_t: Action(ActionType.TOGGLE_THEME),
    pygame.K_z: Action(ActionType.UNDO),
    pygame.K_y: Action(ActionType.REDO),
    pygame.K_ESCAPE: Action(ActionType.CANCEL),
    pygame.K_3: Action(ActionType.SET_SIZE, 3),
    pygame.K_4: Action(ActionType.SET_SIZE, 4),
    pygame.K_5: Action(ActionType.SET_SIZE, 5),
}
assert {a.value for a in _KEY_ACTIONS.values() if a.type is ActionType.SET_SIZE} == set(BOARD_SIZES)

LEFT_MOUSE_BUTTON = 1


class InputHandler:
    """Maps pygame events to ``Action`` objects.

    Args:
        hud: The HUD; it owns buttons, size selector and solver dropdown.
        grid_rect: Screen rectangle of the puzzle grid (for tile clicks).
    """

    def __init__(self, hud: Any, grid_rect: pygame.Rect) -> None:
        self._hud = hud
        self._grid_rect = grid_rect

    def translate(self, event: pygame.event.Event, board_size: int) -> Action | None:
        """Convert one pygame event into an action, or None if it means nothing."""
        if event.type == pygame.QUIT:
            return Action(ActionType.QUIT)
        if event.type == pygame.KEYDOWN:
            return _KEY_ACTIONS.get(event.key)
        if event.type == pygame.MOUSEMOTION:
            self._hud.handle_motion(event.pos)
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == LEFT_MOUSE_BUTTON:
            hud_action = self._hud.handle_click(event.pos)
            if hud_action is not None:
                return hud_action
            index = pixel_to_index(event.pos, self._grid_rect, board_size)
            if index is not None:
                return Action(ActionType.SLIDE_INDEX, index)
        return None


def pixel_to_index(pos: tuple[int, int], grid_rect: pygame.Rect, size: int) -> int | None:
    """Convert a screen position to a flat tile index, or None if outside the grid."""
    if not grid_rect.collidepoint(pos):
        return None
    cell = grid_rect.width / size
    col = min(int((pos[0] - grid_rect.x) / cell), size - 1)
    row = min(int((pos[1] - grid_rect.y) / cell), size - 1)
    return row * size + col


if __name__ == "__main__":
    rect = pygame.Rect(20, 20, 560, 560)
    print("click (30, 30)   ->", pixel_to_index((30, 30), rect, 3))
    print("click (570, 570) ->", pixel_to_index((570, 570), rect, 3))
    print("click (700, 10)  ->", pixel_to_index((700, 10), rect, 3))
