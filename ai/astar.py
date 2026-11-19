"""A* search with a pluggable heuristic.

Role: the star of the project. A* orders the open set by f(n) = g(n) + h(n),
where g is the cost so far and h an admissible estimate of the cost to go.
With an admissible (and consistent) heuristic the first time the goal is
popped its g is optimal, so A* matches BFS's solution length while exploring
far fewer states.

Stale entries: ``heapq`` cannot decrease a key, so a node may sit in the heap
several times with different g values. Each pop is checked and skipped when
the node is already closed (or a cheaper entry exists).
"""

from __future__ import annotations

import heapq
import itertools
import time

from ai.base_solver import SolveResult, Solver
from ai.heuristics import HEURISTIC_LABELS, Heuristic, manhattan
from game.board import Board
from utils.config import ASTAR_NODE_CAP
from utils.logger import get_logger

logger = get_logger(__name__)


class AStarSolver(Solver):
    """Optimal A* search.

    Args:
        heuristic: ``h(state, goal) -> int``; must be admissible and consistent
            for the optimality guarantee (all heuristics in ``ai.heuristics`` are).
        name: Display name; defaults to ``A* (<Heuristic>)``.
    """

    def __init__(
        self,
        heuristic: Heuristic = manhattan,
        *args,
        name: str | None = None,
        max_nodes: int | None = ASTAR_NODE_CAP,
        **kwargs,
    ) -> None:
        super().__init__(*args, max_nodes=max_nodes, **kwargs)
        self.heuristic = heuristic
        label = HEURISTIC_LABELS.get(heuristic.__name__, heuristic.__name__)
        self.name = name or f"A* ({label})"

    def solve(self, start: Board) -> SolveResult:
        """Find a shortest path from ``start`` to the goal.

        ``nodes_explored`` counts only states popped from the open set and not
        skipped as stale.
        """
        self._check_solvable(start)
        started = time.perf_counter()
        goal = Board.goal(start.size)
        h = self.heuristic

        tie_breaker = itertools.count()
        h_start = h(start, goal)
        # heap entry: (f, h, insertion order, g, board) - order never compares boards
        open_heap: list[tuple[int, int, int, int, Board]] = [
            (h_start, h_start, next(tie_breaker), 0, start)
        ]
        best_g: dict[Board, int] = {start: 0}
        parents: dict[Board, Board | None] = {start: None}
        closed: set[Board] = set()
        explored = 0

        while open_heap:
            _, _, _, g, current = heapq.heappop(open_heap)
            if current in closed or g > best_g[current]:
                continue  # stale entry
            closed.add(current)
            explored += 1

            if current.is_goal():
                path = self._reconstruct(parents, current)
                return self._finish(path, explored, started, optimal=True)
            if self._tick(explored) or self._over_budget(explored):
                logger.info("%s stopped after %d nodes (cap or cancel)", self.name, explored)
                break

            next_g = g + 1
            for neighbor in current.neighbors():
                if neighbor in closed:
                    continue
                if next_g < best_g.get(neighbor, next_g + 1):
                    best_g[neighbor] = next_g
                    parents[neighbor] = current
                    h_n = h(neighbor, goal)
                    heapq.heappush(
                        open_heap, (next_g + h_n, h_n, next(tie_breaker), next_g, neighbor)
                    )

        return self._finish(None, explored, started, optimal=False)


if __name__ == "__main__":
    demo = Board.from_tiles((8, 1, 3, 4, 0, 2, 7, 6, 5))
    result = AStarSolver().solve(demo)
    print(f"{result.solution_length} moves, {result.nodes_explored} nodes, {result.time_ms:.1f} ms")
