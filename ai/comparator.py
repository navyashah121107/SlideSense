"""Run several solvers on the same board and collect comparable metrics.

Role: powers the "Compare BFS vs A*" feature and the README benchmark table.
Also hosts ``create_solver``, the factory that turns a UI label such as
"A* (Linear Conflict)" into a configured solver.
"""

from __future__ import annotations

from typing import Any, Sequence

from ai.astar import AStarSolver
from ai.base_solver import SolveResult, Solver, SolverError
from ai.bfs import BFSSolver
from ai.dfs import DFSSolver
from ai.heuristics import linear_conflict, manhattan, misplaced_tiles
from game.board import Board
from utils.config import COMPARE_SOLVER_OPTIONS
from utils.logger import get_logger

logger = get_logger(__name__)

Metrics = dict[str, dict[str, Any]]


def create_solver(option: str, **kwargs: Any) -> Solver:
    """Build a solver from its display label.

    Args:
        option: One of "BFS", "DFS", "A* (Manhattan)", "A* (Linear Conflict)",
            "A* (Misplaced Tiles)".
        **kwargs: Forwarded to the solver (progress_callback, cancel_event, ...).

    Raises:
        ValueError: For an unknown label.
    """
    factories = {
        "BFS": lambda: BFSSolver(**kwargs),
        "DFS": lambda: DFSSolver(**kwargs),
        "A* (Manhattan)": lambda: AStarSolver(manhattan, **kwargs),
        "A* (Linear Conflict)": lambda: AStarSolver(linear_conflict, **kwargs),
        "A* (Misplaced Tiles)": lambda: AStarSolver(misplaced_tiles, **kwargs),
    }
    try:
        return factories[option]()
    except KeyError:
        raise ValueError(f"unknown solver option: {option!r}") from None


def _metrics_from_result(result: SolveResult) -> dict[str, Any]:
    return {
        "solved": result.solved,
        "nodes_explored": result.nodes_explored,
        "time_ms": result.time_ms,
        "solution_length": result.solution_length,
        "optimal": result.optimal,
        "error": None if result.solved else "No solution within search limits",
    }


def compare_solvers(
    start: Board,
    solvers: Sequence[Solver] | None = None,
    include_dfs: bool = False,
) -> Metrics:
    """Run each solver on ``start`` and gather metrics.

    Args:
        start: Board to solve.
        solvers: Solvers to run. Defaults to BFS, A* (Manhattan) and
            A* (Linear Conflict).
        include_dfs: Also run depth-limited DFS (only for the default set).

    Returns:
        ``{solver name: {solved, nodes_explored, time_ms, solution_length,
        optimal, error}}``. A solver that refuses the board (e.g. BFS on 5x5)
        gets ``solved=False`` and an ``error`` message instead of raising.
    """
    if solvers is None:
        labels = list(COMPARE_SOLVER_OPTIONS) + (["DFS"] if include_dfs else [])
        solvers = [create_solver(label) for label in labels]

    metrics: Metrics = {}
    for solver in solvers:
        try:
            metrics[solver.name] = _metrics_from_result(solver.solve(start))
        except SolverError as exc:
            logger.info("%s skipped: %s", solver.name, exc)
            metrics[solver.name] = {
                "solved": False,
                "nodes_explored": 0,
                "time_ms": 0.0,
                "solution_length": None,
                "optimal": False,
                "error": str(exc),
            }
    return metrics


if __name__ == "__main__":
    board = Board.from_tiles((8, 1, 3, 4, 0, 2, 7, 6, 5))
    for solver_name, row in compare_solvers(board).items():
        print(f"{solver_name:22s} {row['nodes_explored']:>7} nodes  {row['time_ms']:8.1f} ms")
