"""Mutable game session state.

Role: tracks the current board, move counter, timer and an undo/redo history.
The clock is injectable so the class is deterministic under test. Pure module:
no pygame, no side effects on import.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from game.board import Board


@dataclass
class GameState:
    """State of one play session.

    Attributes:
        board: The current position.
        clock: Monotonic time source in seconds (override in tests).
        undo_stack: Previous boards, oldest first. ``moves == len(undo_stack)``.
        redo_stack: Boards undone and available to redo.
        undos_used: How many times the player pressed undo.
        auto_solved: True once the AI made a move for the player.
        won: True when the goal was reached.
    """

    board: Board
    clock: Callable[[], float] = time.perf_counter
    undo_stack: list[Board] = field(default_factory=list)
    redo_stack: list[Board] = field(default_factory=list)
    undos_used: int = 0
    auto_solved: bool = False
    won: bool = False
    started_at: float | None = field(default=None, init=False)
    finished_at: float | None = field(default=None, init=False)

    @property
    def moves(self) -> int:
        """Number of moves currently applied (undo lowers it, redo restores it)."""
        return len(self.undo_stack)

    @property
    def is_clean_solve(self) -> bool:
        """True for a win with no AI help and no undo - eligible for the leaderboard."""
        return self.won and not self.auto_solved and self.undos_used == 0

    def elapsed(self) -> float:
        """Seconds since the first move (frozen once the puzzle is won)."""
        if self.started_at is None:
            return 0.0
        end = self.finished_at if self.finished_at is not None else self.clock()
        return end - self.started_at

    def slide(self, index: int, auto: bool = False) -> bool:
        """Slide the tile at ``index`` into the blank.

        Args:
            index: Flat index of the tile to move.
            auto: True when the AI is playing the move.

        Returns:
            True if the move was legal and applied.
        """
        if self.won or not self.board.can_move(index):
            return False
        if self.started_at is None:
            self.started_at = self.clock()
        self.undo_stack.append(self.board)
        self.redo_stack.clear()
        self.board = self.board.slide(index)
        self.auto_solved = self.auto_solved or auto
        self._check_win()
        return True

    def undo(self) -> bool:
        """Revert the last move. Returns False if there is nothing to undo."""
        if self.won or not self.undo_stack:
            return False
        self.redo_stack.append(self.board)
        self.board = self.undo_stack.pop()
        self.undos_used += 1
        return True

    def redo(self) -> bool:
        """Re-apply an undone move. Returns False if there is nothing to redo."""
        if self.won or not self.redo_stack:
            return False
        self.undo_stack.append(self.board)
        self.board = self.redo_stack.pop()
        self._check_win()
        return True

    def _check_win(self) -> None:
        if self.board.is_goal():
            self.won = True
            self.finished_at = self.clock()


if __name__ == "__main__":
    state = GameState(Board.from_tiles((1, 2, 3, 4, 5, 6, 7, 0, 8)))
    state.slide(8)
    print("won:", state.won, "| moves:", state.moves, "| clean:", state.is_clean_solve)
