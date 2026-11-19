# AI Puzzle Solver Game

> A playable 3x3 / 4x4 / 5x5 sliding puzzle in Pygame where you can watch BFS and A\* search for the answer, live.

<!-- Replace with your own recording: -->
![Gameplay GIF placeholder](docs/demo.gif)

## Features

- Play manually with the mouse or arrow keys; undo/redo; timer and move counter
- **Hint**: the AI highlights the optimal next move with a pulsing border
- **Auto-Solve**: watch the AI solve it with smooth ease-in-out tile animation
- **Live metrics**: nodes explored (updating while the search runs), time, solution length
- Solvers: BFS (optimal), DFS (depth-limited, non-optimal, educational), A\* with Misplaced / Manhattan / Linear Conflict
- Guaranteed-solvable scrambles (inversion parity), SQLite leaderboard (clean solves only)
- Dark/light theme, gradient tiles, win glow + confetti + generated sound effects

## Architecture

```
                         main.py  (PuzzleApp: game loop, background SolveJob threads)
                            |
        +-------------------+--------------------+
        |                   |                    |
      ui/                 game/                 ai/
 renderer  hud       board  game_state     base_solver (Solver, SolveResult)
 animator  theme     scramble leaderboard   bfs  dfs  astar  heuristics
 visualizer                                 comparator (create_solver, compare_solvers)
 input_handler
        \                   |                    /
         +-------------- utils/ -----------------+
                 config  logger  parity
```

Dependencies point downward only: `game/` and `ai/` never import pygame, so all logic is unit-testable headlessly. The UI never blocks on search: solvers run on a worker thread and report progress through a callback.

## Algorithms

**BFS** expands states level by level, so the first time it pops the goal the path is shortest. It must remember every state it has seen (roughly b^d memory), which is why it is capped at 500k nodes and refuses 5x5.

**A\*** orders its open set by `f(n) = g(n) + h(n)`. If `h` never overestimates (is *admissible*), the first time the goal is popped its `g` is optimal: any cheaper path would have had a lower `f` and been expanded first. All heuristics here are also *consistent* (`h(n) <= 1 + h(n')` for neighbours), so a closed node never needs re-opening. `heapq` cannot decrease a key, so duplicates are left in the heap and skipped when popped ("stale entries").

**Why Manhattan is admissible:** one move slides exactly one tile exactly one square, so a tile that is `d` squares from home needs at least `d` moves, and the tiles' moves are disjoint. Summing gives a lower bound on the total.

**Linear conflict** adds the detours Manhattan cannot see: if two tiles are both in their goal row (or column) but reversed, one must step out and back, costing 2 extra moves. The implementation counts the *minimum number of tiles that must leave each line* (`line length - longest increasing subsequence`) rather than conflicting pairs, because counting pairs over-estimates three reversed tiles and would break admissibility.

**DFS** (depth-limited) is included to show the contrast: it finds *a* solution quickly but not the shortest one.

## Performance

Measured on this repo's code (pure Python, single thread, seeded boards; `nodes` = states popped from the frontier):

| Board | Solver | Avg nodes explored | Avg time (ms) | Avg moves | Solved |
|---|---|---:|---:|---:|---:|
| 3x3, 20 uniform-random boards | BFS | 94,027 | 387.9 | 22.1 | 20/20 |
| | A\* (Manhattan) | 851 | 6.3 | 22.1 | 20/20 |
| | A\* (Linear Conflict) | 454 | 5.9 | 22.1 | 20/20 |
| 4x4, 8 random-walk boards (22 moves) | BFS | 447,949 | 2,654.6 | 14.0* | 1/8* |
| | A\* (Manhattan) | 146 | 1.6 | 20.8 | 8/8 |
| | A\* (Linear Conflict) | 81 | 1.7 | 20.8 | 8/8 |

\* BFS hit its 500,000-node cap on 7 of the 8 4x4 boards, so its node/time figures are lower bounds and its move average covers only the one board it finished. That is the point: BFS stops being practical at 4x4. Your numbers will differ by machine; re-run with `python -m ai.comparator`.

4x4 and 5x5 start positions use a bounded random walk (`SCRAMBLE_MOVES` in `utils/config.py`) so pure-Python A\* stays responsive; 3x3 uses a uniform random permutation. Fully random 4x4 boards can need millions of nodes without IDA\* or pattern databases.

## Installation

```bash
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
python main.py            # options: --size {3,4,5} --theme {dark,light} --no-sound --seed N
```

Requires Python 3.11+.

| Key | Action | Key | Action |
|---|---|---|---|
| Arrows | slide a tile into the blank | H | hint |
| S | auto-solve / stop | | |
| R | new game | T | toggle theme |
| Z / Y | undo / redo | 3 / 4 / 5 | board size |

## Testing

```bash
pytest tests/ -v
```

Covers: board rules and parity; BFS and A\* returning the same optimal length on 100 boards; A\* exploring fewer nodes than BFS on >= 90% of them; valid A\* paths on 4x4; heuristic admissibility; linear-conflict >= Manhattan; 1000 scrambles all solvable; game state, undo/redo and the leaderboard.

## What I learned

- Why admissibility and consistency matter, and a real bug class: counting linear-conflict *pairs* silently breaks optimality; the fix is a longest-increasing-subsequence argument.
- Parity as a design tool: shuffle, then fix with one swap, instead of generate-and-test.
- Keeping search code pure and pygame-free so it can be tested, benchmarked and visualized from the same implementation.
- Running CPU-heavy search on a worker thread with a progress callback and a cancel event, so the UI stays at 60 FPS.
- Measuring instead of assuming: BFS's memory wall on 4x4 shows up in seconds.

## License

MIT, see [LICENSE](LICENSE).
