"""Tests for game.scramble: scrambles must always be solvable."""

import random

from ai.astar import AStarSolver
from ai.heuristics import linear_conflict
from game.scramble import generate_scramble
from utils.parity import is_solvable

ITERATIONS = 1000


def test_generate_scramble_3x3_always_solvable() -> None:
    rng = random.Random(42)
    for _ in range(ITERATIONS):
        board = generate_scramble(3, rng)
        assert is_solvable(board)
        assert not board.is_goal()


def test_generate_scramble_other_sizes_solvable() -> None:
    rng = random.Random(43)
    for size in (2, 4, 5):
        for _ in range(200):
            assert is_solvable(generate_scramble(size, rng))


def test_random_walk_scramble_solvable_and_reproducible() -> None:
    first = generate_scramble(4, random.Random(5), moves=20)
    second = generate_scramble(4, random.Random(5), moves=20)
    assert first == second
    assert is_solvable(first)


def test_scrambles_are_actually_solvable_by_search() -> None:
    rng = random.Random(44)
    solver = AStarSolver(linear_conflict)
    for _ in range(10):
        assert solver.solve(generate_scramble(3, rng)).path is not None
