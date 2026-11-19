"""SQLite leaderboard of best times per board size.

Role: persistence layer. Only clean solves (no AI help, no undo) should be
saved by the caller. Use ``":memory:"`` as the path for tests and demos. A
``Leaderboard`` owns one connection and must be used from a single thread.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType

from utils.config import LEADERBOARD_DB_PATH, LEADERBOARD_TOP_N
from utils.logger import get_logger

logger = get_logger(__name__)

IN_MEMORY = ":memory:"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scores (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    board_size   INTEGER NOT NULL,
    time_seconds REAL    NOT NULL,
    moves        INTEGER NOT NULL,
    created_at   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scores_size_time ON scores (board_size, time_seconds, moves);
"""


@dataclass(frozen=True)
class ScoreEntry:
    """One saved result.

    Attributes:
        id: Database row id.
        board_size: Board width (3, 4 or 5).
        time_seconds: Solve time.
        moves: Number of moves used.
        created_at: ISO-8601 UTC timestamp.
    """

    id: int
    board_size: int
    time_seconds: float
    moves: int
    created_at: str


class Leaderboard:
    """Save and load best times per board size.

    Args:
        db_path: SQLite file path, or ``":memory:"``. Parent folders are created.
    """

    def __init__(self, db_path: str | Path = LEADERBOARD_DB_PATH) -> None:
        if str(db_path) != IN_MEMORY:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_SCHEMA)

    def save_score(self, board_size: int, time_seconds: float, moves: int) -> ScoreEntry:
        """Insert a result and return the stored row."""
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO scores (board_size, time_seconds, moves, created_at) VALUES (?, ?, ?, ?)",
                (board_size, time_seconds, moves, created),
            )
        logger.info("Saved score: %dx%d %.2fs %d moves", board_size, board_size, time_seconds, moves)
        return ScoreEntry(int(cursor.lastrowid), board_size, time_seconds, moves, created)

    def best_times(self, board_size: int, limit: int = LEADERBOARD_TOP_N) -> list[ScoreEntry]:
        """Return the fastest results for a board size (ties broken by fewer moves)."""
        rows = self._conn.execute(
            "SELECT id, board_size, time_seconds, moves, created_at FROM scores "
            "WHERE board_size = ? ORDER BY time_seconds ASC, moves ASC, id ASC LIMIT ?",
            (board_size, limit),
        ).fetchall()
        return [ScoreEntry(**dict(row)) for row in rows]

    def best_time(self, board_size: int) -> ScoreEntry | None:
        """Return the single best result for a board size, if any."""
        top = self.best_times(board_size, limit=1)
        return top[0] if top else None

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> Leaderboard:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


if __name__ == "__main__":
    with Leaderboard(IN_MEMORY) as demo:
        demo.save_score(3, 42.5, 31)
        demo.save_score(3, 37.0, 35)
        print(demo.best_times(3))
