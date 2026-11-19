"""Depth-limited depth-first search (educational, NOT optimal).

Role: shows why DFS is a poor fit here. It dives down one branch, so it often
returns a long, wandering solution; the depth limit keeps it from running
forever. Implemented with an explicit stack (no recursion). A state is
re-expanded only if reached at a smaller depth, which prevents cycles.
"""

from __future__ import annotations

import time

from ai.base_solver import SolveResult, Solver
from game.board import Board
from utils.config import DFS_DEFAULT_DEPTH_LIMIT, DFS_NODE_CAP


class DFSSolver(Solver):
    """Iterative depth-limited DFS.

    Args:
        depth_limit: Maximum number of moves along any explored path.
    """

    name = "DFS"

    def __init__(
        self,
        *args,
        depth_limit: int = DFS_DEFAULT_DEPTH_LIMIT,
        max_nodes: int | None = DFS_NODE_CAP,
        **kwargs,
    ) -> None:
        super().__init__(*args, max_nodes=max_nodes, **kwargs)
        self.depth_limit = depth_limit

    def solve(self, start: Board) -> SolveResult:
        """Search depth-first up to ``depth_limit`` moves (first hit, not shortest)."""
        self._check_solvable(start)
        started = time.perf_counter()
        parents: dict[Board, Board | None] = {start: None}
        best_depth: dict[Board, int] = {start: 0}
        stack: list[tuple[Board, int]] = [(start, 0)]
        explored = 0

        while stack:
            current, depth = stack.pop()
            if depth > best_depth[current]:
                continue  # stale entry: reached more cheaply since it was pushed
            explored += 1
            if current.is_goal():
                path = self._reconstruct(parents, current)
                return self._finish(path, explored, started, optimal=False)
            if self._tick(explored) or self._over_budget(explored):
                break
            if depth >= self.depth_limit:
                continue
            for neighbor in reversed(current.neighbors()):
                next_depth = depth + 1
                if next_depth < best_depth.get(neighbor, next_depth + 1):
                    best_depth[neighbor] = next_depth
                    parents[neighbor] = current
                    stack.append((neighbor, next_depth))

        return self._finish(None, explored, started, optimal=False)


if __name__ == "__main__":
    demo = Board.from_tiles((1, 2, 3, 4, 5, 6, 0, 7, 8))
    result = DFSSolver(depth_limit=12).solve(demo)
    print("moves:", result.solution_length, "| nodes:", result.nodes_explored)
