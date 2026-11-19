"""Solver interface shared by every search algorithm.

Role: defines ``SolveResult`` (what every solver returns), the abstract
``Solver`` base class, and the small amount of plumbing all solvers share:
timing, progress callbacks (for the live visualizer), cooperative cancellation
and path reconstruction. Pure module: no side effects on import.
"""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Mapping

from game.board import Board
from utils.config import PROGRESS_INTERVAL
from utils.parity import is_solvable

ProgressCallback = Callable[[int], None]


class SolverError(Exception):
    """Base class for solver failures that callers are expected to handle."""


class UnsupportedBoardError(SolverError, ValueError):
    """Raised when an algorithm refuses a board (e.g. BFS on 5x5)."""


class UnsolvableBoardError(SolverError, ValueError):
    """Raised when the start board fails the inversion-parity test."""


@dataclass
class SolveResult:
    """Outcome of one solver run.

    Attributes:
        path: Boards from start to goal inclusive, or None if no solution was
            found (search cap hit or cancelled).
        nodes_explored: States popped from the frontier / open set.
        time_ms: Wall-clock search time in milliseconds.
        optimal: True when ``path`` is guaranteed shortest (BFS and A*).
    """

    path: list[Board] | None
    nodes_explored: int
    time_ms: float
    optimal: bool

    @property
    def solved(self) -> bool:
        """True if a path was found."""
        return self.path is not None

    @property
    def solution_length(self) -> int | None:
        """Number of moves in the path, or None when unsolved."""
        return None if self.path is None else len(self.path) - 1


class Solver(ABC):
    """Abstract search algorithm for the sliding puzzle.

    Args:
        progress_callback: Called with the running node count every
            ``PROGRESS_INTERVAL`` nodes and once more at the end.
        cancel_event: When set (from another thread) the search stops early.
        max_nodes: Hard cap on explored nodes; the search gives up beyond it.
    """

    name: str = "Solver"

    def __init__(
        self,
        progress_callback: ProgressCallback | None = None,
        cancel_event: threading.Event | None = None,
        max_nodes: int | None = None,
    ) -> None:
        self.progress_callback = progress_callback
        self.cancel_event = cancel_event
        self.max_nodes = max_nodes

    @abstractmethod
    def solve(self, start: Board) -> SolveResult:
        """Search for a path from ``start`` to the goal of the same size.

        Args:
            start: The initial board.

        Returns:
            A ``SolveResult``. ``path`` is None if no solution was found
            within the node cap or the search was cancelled.

        Raises:
            UnsolvableBoardError: If ``start`` has the wrong parity.
            UnsupportedBoardError: If this solver cannot handle the board.
        """

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _check_solvable(start: Board) -> None:
        if not is_solvable(start.tiles, start.size):
            raise UnsolvableBoardError("This board is not solvable (inversion parity).")

    def _tick(self, nodes: int) -> bool:
        """Report progress; return True when the search must stop (cancelled)."""
        if nodes % PROGRESS_INTERVAL:
            return False
        if self.progress_callback is not None:
            self.progress_callback(nodes)
        return self.cancel_event is not None and self.cancel_event.is_set()

    def _over_budget(self, nodes: int) -> bool:
        return self.max_nodes is not None and nodes >= self.max_nodes

    def _finish(
        self,
        path: list[Board] | None,
        nodes: int,
        started: float,
        optimal: bool,
    ) -> SolveResult:
        if self.progress_callback is not None:
            self.progress_callback(nodes)
        return SolveResult(
            path=path,
            nodes_explored=nodes,
            time_ms=(time.perf_counter() - started) * 1000.0,
            optimal=optimal and path is not None,
        )

    @staticmethod
    def _reconstruct(parents: Mapping[Board, Board | None], goal: Board) -> list[Board]:
        """Walk parent pointers back from ``goal`` and return start -> goal."""
        path: list[Board] = []
        node: Board | None = goal
        while node is not None:
            path.append(node)
            node = parents[node]
        path.reverse()
        return path


if __name__ == "__main__":
    demo = SolveResult(path=[Board.goal(3)], nodes_explored=1, time_ms=0.1, optimal=True)
    print("solved:", demo.solved, "| length:", demo.solution_length)
