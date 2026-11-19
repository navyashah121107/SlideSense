"""Tests for BFS, DFS, A* and the comparator."""

import random
from functools import lru_cache

import pytest

from ai.astar import AStarSolver
from ai.base_solver import UnsolvableBoardError, UnsupportedBoardError
from ai.bfs import BFSSolver
from ai.comparator import compare_solvers, create_solver
from ai.dfs import DFSSolver
from ai.heuristics import linear_conflict, manhattan, misplaced_tiles
from game.board import Board
from game.scramble import generate_scramble

SEED = 20240607
WALK_3X3 = 20  # random-walk scramble keeps BFS fast enough for 100 boards
WALK_4X4 = 22


def assert_valid_path(start: Board, path: list[Board] | None) -> None:
    """Path starts at ``start``, ends at the goal and every step is one legal move."""
    assert path is not None
    assert path[0] == start
    assert path[-1].is_goal()
    for before, after in zip(path, path[1:]):
        assert after in before.neighbors()


@lru_cache(maxsize=1)
def _benchmark_3x3() -> list[tuple[Board, object, object]]:
    rng = random.Random(SEED)
    bfs, astar = BFSSolver(), AStarSolver(manhattan)
    rows = []
    for _ in range(100):
        board = generate_scramble(3, rng, moves=WALK_3X3)
        rows.append((board, bfs.solve(board), astar.solve(board)))
    return rows


def test_bfs_and_astar_return_same_optimal_length_on_100_boards() -> None:
    for board, bfs_result, astar_result in _benchmark_3x3():
        assert_valid_path(board, bfs_result.path)
        assert_valid_path(board, astar_result.path)
        assert len(bfs_result.path) == len(astar_result.path)
        assert bfs_result.optimal and astar_result.optimal


def test_astar_explores_fewer_nodes_than_bfs_on_90_percent_of_boards() -> None:
    rows = _benchmark_3x3()
    wins = sum(1 for _, bfs_r, astar_r in rows if astar_r.nodes_explored < bfs_r.nodes_explored)
    assert wins / len(rows) >= 0.9


def test_all_astar_heuristics_agree_on_uniform_random_boards() -> None:
    rng = random.Random(SEED + 1)
    solvers = [AStarSolver(h) for h in (misplaced_tiles, manhattan, linear_conflict)]
    for _ in range(15):
        board = generate_scramble(3, rng)  # uniform: deep, hard boards
        lengths = {s.solve(board).solution_length for s in solvers}
        assert len(lengths) == 1


def test_astar_returns_valid_path_on_10_random_4x4_boards() -> None:
    rng = random.Random(SEED + 2)
    solver = AStarSolver(linear_conflict)
    for _ in range(10):
        board = generate_scramble(4, rng, moves=WALK_4X4)
        result = solver.solve(board)
        assert_valid_path(board, result.path)
        assert result.optimal


def test_linear_conflict_explores_no_more_than_manhattan_on_average() -> None:
    rng = random.Random(SEED + 3)
    boards = [generate_scramble(3, rng) for _ in range(20)]
    total_m = sum(AStarSolver(manhattan).solve(b).nodes_explored for b in boards)
    total_lc = sum(AStarSolver(linear_conflict).solve(b).nodes_explored for b in boards)
    assert total_lc <= total_m


def test_already_solved_board() -> None:
    goal = Board.goal(3)
    for solver in (BFSSolver(), AStarSolver(), DFSSolver()):
        result = solver.solve(goal)
        assert result.path == [goal]
        assert result.solution_length == 0


def test_dfs_finds_valid_but_not_necessarily_optimal_path() -> None:
    board = generate_scramble(3, random.Random(SEED + 4), moves=10)
    optimal = AStarSolver(manhattan).solve(board).solution_length
    result = DFSSolver(depth_limit=25).solve(board)
    assert_valid_path(board, result.path)
    assert result.optimal is False
    assert result.solution_length >= optimal


def test_dfs_respects_depth_limit() -> None:
    board = Board.from_tiles((8, 6, 7, 2, 5, 4, 3, 0, 1))  # needs 31 moves
    result = DFSSolver(depth_limit=5, max_nodes=50_000).solve(board)
    assert result.path is None


def test_bfs_refuses_5x5() -> None:
    with pytest.raises(UnsupportedBoardError):
        BFSSolver().solve(Board.goal(5).slide(23))


def test_bfs_node_cap_returns_no_path() -> None:
    board = Board.from_tiles((8, 6, 7, 2, 5, 4, 3, 0, 1))
    result = BFSSolver(max_nodes=100).solve(board)
    assert result.path is None and result.nodes_explored == 100


def test_unsolvable_board_raises() -> None:
    bad = Board.from_tiles((1, 2, 3, 4, 5, 6, 8, 7, 0))
    for solver in (BFSSolver(), AStarSolver(), DFSSolver()):
        with pytest.raises(UnsolvableBoardError):
            solver.solve(bad)


def test_progress_callback_reports_final_node_count() -> None:
    seen: list[int] = []
    board = generate_scramble(3, random.Random(SEED + 5), moves=20)
    result = AStarSolver(manhattan, progress_callback=seen.append).solve(board)
    assert seen and seen[-1] == result.nodes_explored


def test_comparator_returns_metrics_for_each_solver() -> None:
    board = generate_scramble(3, random.Random(SEED + 6), moves=18)
    metrics = compare_solvers(board)
    assert set(metrics) == {"BFS", "A* (Manhattan)", "A* (Linear Conflict)"}
    lengths = {m["solution_length"] for m in metrics.values()}
    assert len(lengths) == 1 and None not in lengths
    assert metrics["A* (Manhattan)"]["nodes_explored"] < metrics["BFS"]["nodes_explored"]


def test_comparator_reports_bfs_skipped_on_5x5() -> None:
    board = generate_scramble(5, random.Random(SEED + 7), moves=8)
    metrics = compare_solvers(board)
    assert metrics["BFS"]["solved"] is False and metrics["BFS"]["error"]
    assert metrics["A* (Linear Conflict)"]["solved"] is True


def test_create_solver_labels() -> None:
    for label in ("BFS", "DFS", "A* (Manhattan)", "A* (Linear Conflict)", "A* (Misplaced Tiles)"):
        assert create_solver(label).name == label
    with pytest.raises(ValueError):
        create_solver("nonsense")
