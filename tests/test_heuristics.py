"""Tests for ai.heuristics: correctness, admissibility and dominance."""

import random

from ai.astar import AStarSolver
from ai.bfs import BFSSolver
from ai.heuristics import linear_conflict, manhattan, misplaced_tiles
from game.board import Board
from game.scramble import generate_scramble

ALL_HEURISTICS = (misplaced_tiles, manhattan, linear_conflict)


def test_heuristics_are_zero_on_goal() -> None:
    for size in (3, 4, 5):
        goal = Board.goal(size)
        for h in ALL_HEURISTICS:
            assert h(goal, goal) == 0


def test_manhattan_known_value() -> None:
    board = Board.from_tiles((1, 2, 3, 4, 5, 6, 0, 7, 8))  # 7 and 8 each one square away
    assert manhattan(board, Board.goal(3)) == 2
    assert misplaced_tiles(board, Board.goal(3)) == 2


def test_linear_conflict_known_value() -> None:
    # Row 0 holds 3,2,1 reversed: manhattan 4, two tiles must leave the row -> +4
    board = Board.from_tiles((3, 2, 1, 4, 5, 6, 7, 8, 0))
    goal = Board.goal(3)
    assert manhattan(board, goal) == 4
    assert linear_conflict(board, goal) == 8


def test_linear_conflict_never_below_manhattan() -> None:
    rng = random.Random(1)
    for size in (3, 4, 5):
        goal = Board.goal(size)
        for _ in range(300):
            board = generate_scramble(size, rng)
            assert linear_conflict(board, goal) >= manhattan(board, goal)
            assert manhattan(board, goal) >= misplaced_tiles(board, goal)


def test_heuristics_are_admissible_on_sample_boards() -> None:
    """h(n) must never exceed the true distance (computed by optimal BFS)."""
    rng = random.Random(2)
    bfs = BFSSolver()
    goal = Board.goal(3)
    for _ in range(30):
        board = generate_scramble(3, rng, moves=14)
        true_distance = bfs.solve(board).solution_length
        assert true_distance is not None
        for h in ALL_HEURISTICS:
            assert h(board, goal) <= true_distance


def test_linear_conflict_admissible_on_adversarial_rows() -> None:
    # Reversed row 0 (3 tiles, needs only 2 detours - pair counting would say 3)
    # plus a reversed pair in row 1; parity-corrected so the board is solvable.
    board = Board.from_tiles((3, 2, 1, 5, 4, 6, 7, 8, 0))
    optimal = AStarSolver(manhattan).solve(board).solution_length
    assert optimal is not None
    assert linear_conflict(board, Board.goal(3)) <= optimal


def test_heuristics_admissible_on_4x4_samples() -> None:
    rng = random.Random(3)
    solver = AStarSolver(linear_conflict)
    goal = Board.goal(4)
    for _ in range(5):
        board = generate_scramble(4, rng, moves=18)
        optimal = solver.solve(board).solution_length
        assert optimal is not None
        for h in ALL_HEURISTICS:
            assert h(board, goal) <= optimal
