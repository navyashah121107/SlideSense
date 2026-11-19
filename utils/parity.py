"""Solvability test for sliding puzzles via inversion parity.

Role: decide, in O(n^2), whether a board can reach the goal
(1, 2, ..., n^2-1, blank). Pure module with no side effects.

Rules (goal has the blank in the bottom-right corner):
    * Odd board width: solvable iff the number of inversions is even.
    * Even board width: solvable iff (inversions + blank row counted from the
      bottom, 1-indexed) is odd.
"""

from __future__ import annotations

from math import isqrt
from typing import Sequence

from utils.config import BLANK


def count_inversions(tiles: Sequence[int]) -> int:
    """Count tile pairs that appear in the wrong relative order.

    Args:
        tiles: Flattened board; the blank (0) is ignored.

    Returns:
        Number of pairs (i < j) with ``tiles[i] > tiles[j]``.
    """
    values = [t for t in tiles if t != BLANK]
    return sum(
        1
        for i in range(len(values))
        for j in range(i + 1, len(values))
        if values[i] > values[j]
    )


def is_solvable(state: Sequence[int], size: int | None = None) -> bool:
    """Return True if ``state`` can be solved.

    Args:
        state: A flattened tile sequence, or any object with a ``tiles``
            attribute (such as ``game.board.Board``).
        size: Board width. Inferred from the length when omitted.

    Returns:
        True when the puzzle is solvable.

    Raises:
        ValueError: If the tile count is not a perfect square.
    """
    tiles = tuple(getattr(state, "tiles", state))
    width = size if size is not None else isqrt(len(tiles))
    if width * width != len(tiles):
        raise ValueError(f"{len(tiles)} tiles do not form a square board")

    inversions = count_inversions(tiles)
    if width % 2 == 1:
        return inversions % 2 == 0
    blank_row_from_bottom = width - tiles.index(BLANK) // width
    return (inversions + blank_row_from_bottom) % 2 == 1


if __name__ == "__main__":
    print("goal 3x3      :", is_solvable((1, 2, 3, 4, 5, 6, 7, 8, 0)))
    print("swapped 7<->8 :", is_solvable((1, 2, 3, 4, 5, 6, 8, 7, 0)))
