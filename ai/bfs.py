"""Breadth-first search.

Role: the optimal-but-slow baseline. BFS expands states level by level, so the
first time it pops the goal the path is guaranteed shortest. Memory grows
roughly b^d, therefore the solver refuses 5x5 boards and caps the number of
explored nodes (``BFS_NODE_CAP``).
"""

from __future__ import annotations

import time
from collections import deque

from ai.base_solver import SolveResult, Solver, UnsupportedBoardError
from game.board import Board
from utils.config import BFS_MAX_SIZE, BFS_NODE_CAP
from utils.logger import get_logger

logger = get_logger(__name__)


class BFSSolver(Solver):
    """Optimal breadth-first search with a node cap."""

    name = "BFS"

    def __init__(self, *args, max_nodes: int | None = BFS_NODE_CAP, **kwargs) -> None:
        super().__init__(*args, max_nodes=max_nodes, **kwargs)

    def solve(self, start: Board) -> SolveResult:
        """Find a shortest path from ``start`` to the goal.

        Raises:
            UnsupportedBoardError: If the board is 5x5 or larger.
            UnsolvableBoardError: If the board fails the parity test.
        """
        if start.size >= BFS_MAX_SIZE:
            raise UnsupportedBoardError(
                f"BFS does not support {start.size}x{start.size} boards (memory). Use A*."
            )
        self._check_solvable(start)

        started = time.perf_counter()
        parents: dict[Board, Board | None] = {start: None}
        frontier: deque[Board] = deque([start])
        explored = 0

        while frontier:
            current = frontier.popleft()
            explored += 1
            if current.is_goal():
                path = self._reconstruct(parents, current)
                return self._finish(path, explored, started, optimal=True)
            if self._tick(explored) or self._over_budget(explored):
                logger.info("BFS stopped after %d nodes (cap or cancel)", explored)
                break
            for neighbor in current.neighbors():
                if neighbor not in parents:
                    parents[neighbor] = current
                    frontier.append(neighbor)

        return self._finish(None, explored, started, optimal=False)


if __name__ == "__main__":
    demo = Board.from_tiles((1, 2, 3, 4, 5, 6, 0, 7, 8))
    result = BFSSolver().solve(demo)
    print("moves:", result.solution_length, "| nodes:", result.nodes_explored)
