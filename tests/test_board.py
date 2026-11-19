"""Tests for game.board.Board and utils.parity."""

from dataclasses import FrozenInstanceError

import pytest

from game.board import Board
from utils.parity import count_inversions, is_solvable


def test_goal_board_is_goal() -> None:
    for size in (2, 3, 4, 5):
        goal = Board.goal(size)
        assert goal.is_goal()
        assert goal.tiles[-1] == 0
        assert goal.get_blank() == size * size - 1


def test_neighbor_counts_corner_edge_center() -> None:
    corner = Board.from_tiles((0, 1, 2, 3, 4, 5, 6, 7, 8))
    edge = Board.from_tiles((1, 0, 2, 3, 4, 5, 6, 7, 8))
    center = Board.from_tiles((1, 2, 3, 4, 0, 5, 6, 7, 8))
    assert (len(corner.neighbors()), len(edge.neighbors()), len(center.neighbors())) == (2, 3, 4)


def test_neighbors_are_valid_single_moves() -> None:
    board = Board.from_tiles((1, 2, 3, 4, 0, 6, 7, 5, 8))
    for neighbor in board.neighbors():
        differing = [i for i in range(9) if board.tiles[i] != neighbor.tiles[i]]
        assert len(differing) == 2  # blank and one tile swapped
        assert neighbor.size == 3


def test_slide_moves_tile_into_blank() -> None:
    board = Board.from_tiles((1, 2, 3, 4, 5, 6, 7, 0, 8))
    after = board.slide(8)
    assert after.is_goal()
    assert not board.is_goal()  # original untouched (immutability)


def test_slide_illegal_tile_raises() -> None:
    board = Board.goal(3)
    assert not board.can_move(0)
    with pytest.raises(ValueError):
        board.slide(0)


def test_board_is_frozen_and_hashable() -> None:
    board = Board.goal(3)
    with pytest.raises(FrozenInstanceError):
        board.size = 4  # type: ignore[misc]
    assert board == Board.goal(3)
    assert len({board, Board.goal(3)}) == 1


def test_invalid_boards_rejected() -> None:
    with pytest.raises(ValueError):
        Board((1, 2, 3, 4, 5, 6, 7, 8, 8), 3)  # duplicate tile
    with pytest.raises(ValueError):
        Board((1, 2, 3), 3)  # wrong length
    with pytest.raises(ValueError):
        Board.from_tiles((0, 1, 2))  # not a square


def test_direction_mapping_is_tile_travel_direction() -> None:
    board = Board.from_tiles((1, 2, 3, 4, 0, 5, 6, 7, 8))  # blank in the centre (index 4)
    assert board.tile_index_for_direction(0, -1) == 5  # Left: tile right of blank moves left
    assert board.tile_index_for_direction(0, 1) == 3   # Right: tile left of blank
    assert board.tile_index_for_direction(-1, 0) == 7  # Up: tile below blank
    assert board.tile_index_for_direction(1, 0) == 1   # Down: tile above blank
    corner = Board.goal(3)  # blank bottom-right: nothing to its right/below
    assert corner.tile_index_for_direction(0, 1) == 7
    assert corner.tile_index_for_direction(0, -1) is None
    assert corner.tile_index_for_direction(-1, 0) is None  # nothing below the blank
    assert corner.tile_index_for_direction(1, 0) == 5      # tile above slides down


def test_changed_tile_identifies_moved_tile() -> None:
    board = Board.from_tiles((1, 2, 3, 4, 5, 6, 7, 0, 8))
    after = board.slide(8)
    assert board.changed_tile(after) == 8
    assert board.tiles[board.changed_tile(after)] == 8


def test_parity_known_cases() -> None:
    assert is_solvable((1, 2, 3, 4, 5, 6, 7, 8, 0))
    assert not is_solvable((1, 2, 3, 4, 5, 6, 8, 7, 0))
    assert is_solvable(tuple(range(1, 16)) + (0,))
    # the classic unsolvable 15-puzzle (14 and 15 swapped)
    assert not is_solvable((1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 14, 0))
    assert count_inversions((2, 1, 0, 3)) == 1


def test_every_move_preserves_solvability() -> None:
    board = Board.goal(4)
    for _ in range(3):
        for neighbor in board.neighbors():
            assert is_solvable(neighbor)
        board = board.neighbors()[0]
