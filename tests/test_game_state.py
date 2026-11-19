"""Tests for game.game_state.GameState and game.leaderboard.Leaderboard."""

from game.board import Board
from game.game_state import GameState
from game.leaderboard import Leaderboard


class FakeClock:
    """Deterministic clock: advance manually."""

    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


ONE_MOVE_FROM_GOAL = (1, 2, 3, 4, 5, 6, 7, 0, 8)


def test_slide_counts_moves_and_detects_win() -> None:
    clock = FakeClock()
    state = GameState(Board.from_tiles(ONE_MOVE_FROM_GOAL), clock=clock)
    assert state.elapsed() == 0.0  # timer starts on the first move
    assert not state.slide(0)  # illegal move is rejected
    assert state.moves == 0
    clock.now += 5
    assert state.slide(8)
    clock.now += 99
    assert state.won and state.moves == 1
    assert state.elapsed() == 0.0  # started and finished on the same tick
    assert state.is_clean_solve


def test_timer_runs_until_win() -> None:
    clock = FakeClock()
    state = GameState(Board.from_tiles((1, 2, 3, 4, 5, 6, 0, 7, 8)), clock=clock)
    state.slide(7)
    clock.now += 12.5
    assert state.elapsed() == 12.5
    state.slide(8)
    clock.now += 50
    assert state.elapsed() == 12.5  # frozen after the win


def test_undo_redo_roundtrip() -> None:
    state = GameState(Board.from_tiles((1, 2, 3, 4, 5, 6, 0, 7, 8)))
    start = state.board
    state.slide(7)
    after_one = state.board
    assert state.undo() and state.board == start and state.moves == 0
    assert state.redo() and state.board == after_one and state.moves == 1
    assert not state.redo()


def test_new_move_clears_redo_and_undo_blocks_clean_solve() -> None:
    state = GameState(Board.from_tiles((1, 2, 3, 4, 5, 6, 0, 7, 8)))
    state.slide(7)
    state.undo()
    state.slide(7)
    assert not state.redo_stack
    state.slide(8)
    assert state.won and not state.is_clean_solve  # an undo was used


def test_auto_moves_disqualify_clean_solve() -> None:
    state = GameState(Board.from_tiles(ONE_MOVE_FROM_GOAL))
    state.slide(8, auto=True)
    assert state.won and state.auto_solved and not state.is_clean_solve


def test_no_moves_after_win() -> None:
    state = GameState(Board.from_tiles(ONE_MOVE_FROM_GOAL))
    state.slide(8)
    assert not state.slide(7)
    assert not state.undo()


def test_leaderboard_orders_by_time_then_moves() -> None:
    with Leaderboard(":memory:") as board:
        board.save_score(3, 30.0, 40)
        board.save_score(3, 20.0, 50)
        board.save_score(3, 20.0, 45)
        board.save_score(4, 5.0, 10)
        top = board.best_times(3)
        assert [(e.time_seconds, e.moves) for e in top] == [(20.0, 45), (20.0, 50), (30.0, 40)]
        assert board.best_time(4).time_seconds == 5.0
        assert board.best_time(5) is None
        assert len(board.best_times(3, limit=2)) == 2
