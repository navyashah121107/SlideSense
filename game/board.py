"""Immutable sliding-puzzle board.

Role: the core domain object. A ``Board`` is a frozen, hashable dataclass
holding a flattened tuple of tiles (0 = blank) and the board width. Because it
is hashable it can be used directly as a key in search ``closed`` sets and
``parents`` dictionaries. Pure module: no side effects on import.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import isqrt
from typing import Sequence

from utils.config import BLANK, BLANK_DIRECTIONS, MIN_BOARD_SIZE


@lru_cache(maxsize=None)
def _goal_tiles(size: int) -> tuple[int, ...]:
    """Return the goal tuple (1..n^2-1 followed by the blank) for ``size``."""
    return tuple(range(1, size * size)) + (BLANK,)


@dataclass(frozen=True, slots=True)
class Board:
    """An immutable N x N sliding-puzzle position.

    Attributes:
        tiles: Row-major flattened tiles; ``0`` marks the blank.
        size: Board width/height (3 for the classic 8-puzzle).
    """

    tiles: tuple[int, ...]
    size: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "tiles", tuple(self.tiles))
        if self.size < MIN_BOARD_SIZE:
            raise ValueError(f"size must be >= {MIN_BOARD_SIZE}, got {self.size}")
        if len(self.tiles) != self.size * self.size:
            raise ValueError(f"expected {self.size ** 2} tiles, got {len(self.tiles)}")
        if sorted(self.tiles) != list(range(self.size * self.size)):
            raise ValueError("tiles must be a permutation of 0..n^2-1")

    # ------------------------------------------------------------------ factories
    @classmethod
    def goal(cls, size: int) -> Board:
        """Build the solved board for ``size``."""
        return cls._unchecked(_goal_tiles(size), size)

    @classmethod
    def from_tiles(cls, tiles: Sequence[int]) -> Board:
        """Build a board, inferring the size from the tile count.

        Raises:
            ValueError: If the tile count is not a perfect square or the
                tiles are not a valid permutation.
        """
        size = isqrt(len(tiles))
        if size * size != len(tiles):
            raise ValueError(f"{len(tiles)} tiles do not form a square board")
        return cls(tuple(tiles), size)

    @classmethod
    def _unchecked(cls, tiles: tuple[int, ...], size: int) -> Board:
        """Fast constructor that skips validation (internal, hot search path)."""
        board = object.__new__(cls)
        object.__setattr__(board, "tiles", tiles)
        object.__setattr__(board, "size", size)
        return board

    # ------------------------------------------------------------------ queries
    def get_blank(self) -> int:
        """Return the flat index of the blank."""
        return self.tiles.index(BLANK)

    def row_col(self, index: int) -> tuple[int, int]:
        """Convert a flat index into ``(row, col)``."""
        return divmod(index, self.size)

    def is_goal(self) -> bool:
        """Return True when the board is solved."""
        return self.tiles == _goal_tiles(self.size)

    def can_move(self, index: int) -> bool:
        """Return True if the tile at ``index`` is adjacent to the blank."""
        if not 0 <= index < len(self.tiles) or self.tiles[index] == BLANK:
            return False
        r, c = self.row_col(index)
        br, bc = self.row_col(self.get_blank())
        return abs(r - br) + abs(c - bc) == 1

    def tile_index_for_direction(self, d_row: int, d_col: int) -> int | None:
        """Find the tile that moves in direction ``(d_row, d_col)`` into the blank.

        Pressing the Left arrow means "a tile slides left", so the tile
        sits to the *right* of the blank.

        Returns:
            Flat index of that tile, or None if it would be off the board.
        """
        br, bc = self.row_col(self.get_blank())
        r, c = br - d_row, bc - d_col
        if 0 <= r < self.size and 0 <= c < self.size:
            return r * self.size + c
        return None

    def changed_tile(self, other: Board) -> int:
        """Index (in ``self``) of the tile that slid to reach adjacent ``other``.

        After a slide the blank sits where the moved tile used to be.
        """
        return other.get_blank()

    # ------------------------------------------------------------------ moves
    def slide(self, index: int) -> Board:
        """Return the board after sliding the tile at ``index`` into the blank.

        Raises:
            ValueError: If that tile is not adjacent to the blank.
        """
        if not self.can_move(index):
            raise ValueError(f"tile at index {index} cannot move")
        blank = self.get_blank()
        tiles = list(self.tiles)
        tiles[blank], tiles[index] = tiles[index], BLANK
        return Board._unchecked(tuple(tiles), self.size)

    def neighbors(self) -> list[Board]:
        """Return every board reachable in one move (2 to 4 boards)."""
        size, tiles = self.size, self.tiles
        blank = tiles.index(BLANK)
        row, col = divmod(blank, size)
        result: list[Board] = []
        for d_row, d_col in BLANK_DIRECTIONS:
            n_row, n_col = row + d_row, col + d_col
            if 0 <= n_row < size and 0 <= n_col < size:
                n_idx = n_row * size + n_col
                moved = list(tiles)
                moved[blank], moved[n_idx] = moved[n_idx], BLANK
                result.append(Board._unchecked(tuple(moved), size))
        return result

    # ------------------------------------------------------------------ display
    def to_rows(self) -> list[tuple[int, ...]]:
        """Return the tiles as a list of rows."""
        return [self.tiles[r * self.size:(r + 1) * self.size] for r in range(self.size)]

    def __str__(self) -> str:
        width = len(str(self.size * self.size - 1))
        return "\n".join(
            " ".join("." if t == BLANK else str(t).rjust(width) for t in row)
            for row in self.to_rows()
        )


if __name__ == "__main__":
    demo = Board.from_tiles((1, 2, 3, 4, 0, 6, 7, 5, 8))
    print(demo, "\n")
    print("blank index:", demo.get_blank(), "| goal?", demo.is_goal())
    print("neighbors  :", len(demo.neighbors()))
