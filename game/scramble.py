"""Guaranteed-solvable puzzle scrambling.

Role: generate start positions that are always solvable. The default mode
shuffles uniformly and, if the permutation has the wrong inversion parity,
swaps two tiles - which flips the parity and makes it solvable. The optional
random-walk mode scrambles by making legal moves from the goal, which bounds
the difficulty (handy for 4x4 / 5x5 boards).
"""

from __future__ import annotations

import random

from game.board import Board
from utils.config import BLANK, SCRAMBLE_MAX_ATTEMPTS
from utils.parity import is_solvable


def generate_scramble(
    size: int,
    rng: random.Random | None = None,
    moves: int | None = None,
) -> Board:
    """Create a solvable, non-goal board.

    Args:
        size: Board width.
        rng: Random generator (pass a seeded one for reproducibility).
        moves: When given, scramble by a random walk of this many moves
            (never undoing the previous move). When None, shuffle uniformly
            and repair parity.

    Returns:
        A solvable board that is not already solved.

    Raises:
        RuntimeError: If no valid scramble was produced (practically impossible).
    """
    rng = rng or random.Random()
    for _ in range(SCRAMBLE_MAX_ATTEMPTS):
        board = _random_walk(size, rng, moves) if moves else _parity_shuffle(size, rng)
        if not board.is_goal():
            return board
    raise RuntimeError("could not generate a non-trivial scramble")


def _parity_shuffle(size: int, rng: random.Random) -> Board:
    """Uniformly shuffle, then fix inversion parity with one tile swap."""
    tiles = list(range(size * size))
    rng.shuffle(tiles)
    if not is_solvable(tiles, size):
        non_blank = [i for i, t in enumerate(tiles) if t != BLANK]
        a, b = non_blank[0], non_blank[1]
        tiles[a], tiles[b] = tiles[b], tiles[a]
    return Board(tuple(tiles), size)


def _random_walk(size: int, rng: random.Random, moves: int) -> Board:
    """Walk ``moves`` legal moves away from the goal without immediate undo."""
    board = Board.goal(size)
    previous: Board | None = None
    for _ in range(moves):
        options = [b for b in board.neighbors() if b != previous]
        previous, board = board, rng.choice(options)
    return board


if __name__ == "__main__":
    demo_rng = random.Random(7)
    sample = generate_scramble(3, demo_rng)
    print(sample, "\nsolvable:", is_solvable(sample))
