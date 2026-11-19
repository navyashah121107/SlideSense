"""Admissible heuristics for the sliding puzzle.

Role: three estimates of the remaining moves, each a lower bound on the true
distance (admissible) and also consistent, so A* never needs to re-open a
closed node:

    misplaced_tiles < manhattan <= linear_conflict <= true distance

Pure module: no side effects on import.
"""

from __future__ import annotations

from bisect import bisect_left
from functools import lru_cache
from typing import Callable, Sequence

from game.board import Board
from utils.config import BLANK

Heuristic = Callable[[Board, Board], int]

LINEAR_CONFLICT_PENALTY = 2  # each tile that must leave its line costs >= 2 extra moves


@lru_cache(maxsize=32)
def _goal_coords(goal_tiles: tuple[int, ...], size: int) -> tuple[tuple[int, int], ...]:
    """Map tile value -> (row, col) in the goal arrangement."""
    coords = [(0, 0)] * len(goal_tiles)
    for index, value in enumerate(goal_tiles):
        coords[value] = divmod(index, size)
    return tuple(coords)


def misplaced_tiles(state: Board, goal: Board) -> int:
    """Count tiles (excluding the blank) that are not on their goal square.

    Admissible because every misplaced tile needs at least one move.
    """
    return sum(1 for s, g in zip(state.tiles, goal.tiles) if s != BLANK and s != g)


def manhattan(state: Board, goal: Board) -> int:
    """Sum of |row diff| + |col diff| of every tile to its goal square.

    Admissible because one move shifts exactly one tile by exactly one square,
    so reaching the goal needs at least this many moves.
    """
    coords = _goal_coords(goal.tiles, goal.size)
    size = state.size
    total = 0
    for index, value in enumerate(state.tiles):
        if value != BLANK:
            row, col = divmod(index, size)
            g_row, g_col = coords[value]
            total += abs(row - g_row) + abs(col - g_col)
    return total


def _min_removals(goal_positions: Sequence[int]) -> int:
    """Fewest tiles to remove from a line so the rest are in goal order.

    ``goal_positions`` are the goal coordinates of the line's tiles, listed in
    their current order. Tiles that stay form the longest increasing
    subsequence, so removals = length - LIS.
    """
    tails: list[int] = []
    for position in goal_positions:
        slot = bisect_left(tails, position)
        if slot == len(tails):
            tails.append(position)
        else:
            tails[slot] = position
    return len(goal_positions) - len(tails)


def linear_conflict(state: Board, goal: Board) -> int:
    """Manhattan distance plus 2 per forced detour caused by linear conflicts.

    Two tiles are in linear conflict when both sit in their goal row (or
    column) but in reversed order: one must leave the line and come back,
    costing 2 extra moves that Manhattan does not see. For each line we count
    the *minimum* number of tiles that must leave (length minus the longest
    increasing subsequence), which keeps the heuristic admissible - naively
    counting conflicting pairs would over-estimate three or more reversed tiles.
    """
    coords = _goal_coords(goal.tiles, goal.size)
    size = state.size
    tiles = state.tiles
    removals = 0

    for line in range(size):
        row_goal_cols: list[int] = []
        col_goal_rows: list[int] = []
        for offset in range(size):
            row_value = tiles[line * size + offset]  # walking along row `line`
            if row_value != BLANK and coords[row_value][0] == line:
                row_goal_cols.append(coords[row_value][1])
            col_value = tiles[offset * size + line]  # walking down column `line`
            if col_value != BLANK and coords[col_value][1] == line:
                col_goal_rows.append(coords[col_value][0])
        removals += _min_removals(row_goal_cols) + _min_removals(col_goal_rows)

    return manhattan(state, goal) + LINEAR_CONFLICT_PENALTY * removals


HEURISTICS: dict[str, Heuristic] = {
    "misplaced": misplaced_tiles,
    "manhattan": manhattan,
    "linear_conflict": linear_conflict,
}

HEURISTIC_LABELS: dict[str, str] = {
    "misplaced_tiles": "Misplaced Tiles",
    "manhattan": "Manhattan",
    "linear_conflict": "Linear Conflict",
}


if __name__ == "__main__":
    reversed_row = Board.from_tiles((3, 2, 1, 4, 5, 6, 7, 8, 0))
    goal_board = Board.goal(3)
    for label, fn in HEURISTICS.items():
        print(f"{label:16s}: {fn(reversed_row, goal_board)}")
