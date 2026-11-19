"""AI Puzzle Solver Game - entry point and game loop.

Role: wires the pure game logic (``game``), the search algorithms (``ai``) and
the pygame UI (``ui``) together. Searches run on a background thread so the
window stays responsive and the live visualizer can show the explored-state
count climbing. Run with ``python main.py`` (see ``--help`` for options).
"""

from __future__ import annotations

import argparse
import math
import random
import struct
import threading
import time
import wave
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pygame

from ai.base_solver import SolveResult, SolverError
from ai.comparator import create_solver
from game.board import Board
from game.game_state import GameState
from game.leaderboard import Leaderboard
from game.scramble import generate_scramble
from ui.animator import AnimationManager, ParticleSystem, pulse
from ui.hud import Hud, HudView, format_time
from ui.input_handler import Action, ActionType, InputHandler
from ui.renderer import Renderer
from ui.theme import THEMES, FontCache, get_theme, next_theme_name
from ui.visualizer import SearchVisualizer
from utils.config import (
    AUTO_SOLVE_STEP_DELAY_MS,
    BOARD_SIZES,
    DEFAULT_BOARD_SIZE,
    DEFAULT_SOLVER_OPTION,
    FPS,
    GRID_MARGIN,
    GRID_PIXELS,
    HINT_PULSE_PERIOD_MS,
    SCRAMBLE_MOVES,
    SLIDE_SOUND_FILE,
    SOLVER_OPTIONS,
    SOUND_ATTACK_S,
    SOUND_DECAY_RATE,
    SOUND_PCM_MAX,
    SOUND_SAMPLE_RATE,
    SOUND_SLIDE_FREQ_HZ,
    SOUND_SLIDE_MS,
    SOUND_SLIDE_VOLUME,
    SOUND_WIN_LAST_NOTE_MS,
    SOUND_WIN_NOTE_MS,
    SOUND_WIN_NOTES_HZ,
    SOUND_WIN_VOLUME,
    SOUNDS_DIR,
    TILE_GRADIENT_STOPS,
    VISUALIZER_HEIGHT,
    VISUALIZER_TOP,
    WIN_BURST_DURATION_MS,
    WIN_BURST_INTERVAL_MS,
    WIN_GLOW_PERIOD_MS,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WIN_SOUND_FILE,
)
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


# --------------------------------------------------------------------------- sound
def _tone(freq_hz: float, duration_ms: int, volume: float) -> list[float]:
    """Synthesize a decaying sine tone as floats in -1..1."""
    count = int(SOUND_SAMPLE_RATE * duration_ms / 1000)
    attack = max(1, int(SOUND_ATTACK_S * SOUND_SAMPLE_RATE))
    return [
        volume
        * math.sin(2 * math.pi * freq_hz * i / SOUND_SAMPLE_RATE)
        * math.exp(-SOUND_DECAY_RATE * i / count)
        * min(1.0, i / attack)
        for i in range(count)
    ]


def _write_wave(path: Path, samples: list[float]) -> None:
    """Write mono 16-bit PCM samples to ``path``."""
    frames = b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, s)) * SOUND_PCM_MAX)) for s in samples
    )
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SOUND_SAMPLE_RATE)
        wav.writeframes(frames)


def generate_sounds(directory: Path = SOUNDS_DIR) -> None:
    """Create ``slide.wav`` and ``win.wav`` with the stdlib if they are missing."""
    directory.mkdir(parents=True, exist_ok=True)
    slide, win = directory / SLIDE_SOUND_FILE, directory / WIN_SOUND_FILE
    if not slide.exists():
        _write_wave(slide, _tone(SOUND_SLIDE_FREQ_HZ, SOUND_SLIDE_MS, SOUND_SLIDE_VOLUME))
    if not win.exists():
        samples: list[float] = []
        for i, note in enumerate(SOUND_WIN_NOTES_HZ):
            last = i == len(SOUND_WIN_NOTES_HZ) - 1
            samples += _tone(note, SOUND_WIN_LAST_NOTE_MS if last else SOUND_WIN_NOTE_MS, SOUND_WIN_VOLUME)
        _write_wave(win, samples)


# --------------------------------------------------------------------------- background search
@dataclass
class SolveJob:
    """A solver running on a worker thread.

    The UI thread only reads ``nodes`` / ``history`` / ``done`` and the result
    fields after ``done`` is True; the worker only writes them.
    """

    purpose: str  # "hint" | "auto"
    label: str
    start_board: Board
    cancel_event: threading.Event = field(default_factory=threading.Event)
    nodes: int = 0
    history: list[tuple[float, int]] = field(default_factory=list)
    result: SolveResult | None = None
    error: str | None = None
    done: bool = False
    started_at: float = field(default_factory=time.perf_counter)

    def on_progress(self, nodes: int) -> None:
        """Progress callback handed to solvers."""
        self.nodes = nodes
        self.history.append((time.perf_counter() - self.started_at, nodes))

    def start(self) -> None:
        """Launch the worker thread."""
        threading.Thread(target=self._run_single, daemon=True, name=f"solve-{self.purpose}").start()

    def _run_single(self) -> None:
        try:
            solver = create_solver(self.label, progress_callback=self.on_progress,
                                   cancel_event=self.cancel_event)
            self.result = solver.solve(self.start_board)
        except SolverError as exc:
            self.error = str(exc)
        except Exception:  # noqa: BLE001 - never let a worker die silently
            logger.exception("Solver crashed")
            self.error = "Solver crashed - see logs/game.log"
        finally:
            self.done = True


# --------------------------------------------------------------------------- application
class PuzzleApp:
    """The game window and main loop.

    Args:
        size: Initial board size.
        theme_name: "dark" or "light".
        sound: Enable sound effects.
        seed: Optional RNG seed for reproducible scrambles.
    """

    def __init__(self, size: int, theme_name: str, sound: bool, seed: int | None) -> None:
        setup_logging()
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.rng = random.Random(seed)

        self.fonts = FontCache()
        self.theme_name = theme_name
        self.renderer = Renderer(self.screen, theme_name, self.fonts)
        solver_index = SOLVER_OPTIONS.index(DEFAULT_SOLVER_OPTION)
        self.hud = Hud(get_theme(theme_name), self.fonts, size, SOLVER_OPTIONS, solver_index)
        self.input = InputHandler(self.hud, self.renderer.grid_rect)
        self.visualizer = SearchVisualizer(self.fonts)
        self.visualizer_rect = pygame.Rect(GRID_MARGIN, VISUALIZER_TOP, GRID_PIXELS, VISUALIZER_HEIGHT)
        self.animations = AnimationManager()
        self.particles = ParticleSystem(self.rng)
        self.leaderboard = Leaderboard()
        self.sounds: dict[str, pygame.mixer.Sound] = self._load_sounds() if sound else {}

        self.running = True
        self.size = size
        self.state = GameState(Board.goal(size))
        self.job: SolveJob | None = None
        self.auto_queue: deque[Board] = deque()
        self.auto_active = False
        self._auto_delay_ms = 0.0
        self.hint_index: int | None = None
        self.hint_board: Board | None = None
        self.metrics: dict[str, Any] | None = None
        self.win_started_ms: int | None = None
        self._last_burst_ms = 0
        self.status = ""
        self.best_text = ""
        self.new_game(size)

    # ------------------------------------------------------------------ setup helpers
    def _load_sounds(self) -> dict[str, pygame.mixer.Sound]:
        try:
            generate_sounds()
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            return {
                "slide": pygame.mixer.Sound(str(SOUNDS_DIR / SLIDE_SOUND_FILE)),
                "win": pygame.mixer.Sound(str(SOUNDS_DIR / WIN_SOUND_FILE)),
            }
        except (pygame.error, OSError) as exc:
            logger.warning("Sound disabled: %s", exc)
            return {}

    def _play(self, name: str) -> None:
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    @property
    def theme(self) -> dict[str, tuple[int, int, int]]:
        """Active colour theme."""
        return get_theme(self.theme_name)

    @property
    def solver_option(self) -> str:
        """Label of the solver selected in the dropdown."""
        return SOLVER_OPTIONS[self.hud.solver_index]

    def _best_text(self) -> str:
        entry = self.leaderboard.best_time(self.size)
        if entry is None:
            return f"No record for {self.size}x{self.size} yet"
        return f"Best {self.size}x{self.size}: {format_time(entry.time_seconds)} ({entry.moves} moves)"

    # ------------------------------------------------------------------ game flow
    def new_game(self, size: int | None = None) -> None:
        """Start a fresh scrambled game (optionally changing the board size)."""
        self._cancel_everything()
        if size is not None:
            self.size = size
        board = generate_scramble(self.size, self.rng, SCRAMBLE_MOVES.get(self.size))
        self.state = GameState(board)
        self.animations.clear()
        self.particles.clear()
        self.hint_index = self.hint_board = None
        self.metrics = None
        self.win_started_ms = None
        self.status = "Slide the tiles into order - or ask the AI for help"
        self.hud.set_board_size(self.size)
        self.best_text = self._best_text()
        logger.info("New %dx%d game", self.size, self.size)

    def _cancel_everything(self) -> None:
        if self.job is not None:
            self.job.cancel_event.set()
            self.job = None
        self.auto_queue.clear()
        self.auto_active = False

    def _animate(self, old: Board, new: Board) -> None:
        moved_index = old.changed_tile(new)
        self.animations.start_slide(
            old.tiles[moved_index],
            self.renderer.index_to_pos(moved_index, self.size),
            self.renderer.index_to_pos(old.get_blank(), self.size),
        )

    def _apply_slide(self, index: int, auto: bool) -> bool:
        old = self.state.board
        if not self.state.slide(index, auto=auto):
            return False
        self._animate(old, self.state.board)
        self._play("slide")
        if self.state.won:
            self._on_win()
        return True

    def _manual_slide(self, index: int) -> None:
        if self.state.won or self.animations.is_animating():
            return
        if self.job is not None or self.auto_active:
            self.status = "The AI is working - press S to stop it"
            return
        self._apply_slide(index, auto=False)

    def _undo_redo(self, undo: bool) -> None:
        if self.job is not None or self.auto_active or self.animations.is_animating():
            return
        old = self.state.board
        if (self.state.undo() if undo else self.state.redo()):
            self._animate(old, self.state.board)
            self._play("slide")
            if self.state.won:
                self._on_win()

    def _on_win(self) -> None:
        self.win_started_ms = pygame.time.get_ticks()
        self._last_burst_ms = 0
        self._play("win")
        elapsed, moves = self.state.elapsed(), self.state.moves
        if self.state.is_clean_solve:
            previous = self.leaderboard.best_time(self.size)
            self.leaderboard.save_score(self.size, elapsed, moves)
            record = previous is None or elapsed < previous.time_seconds
            self.status = f"Solved in {format_time(elapsed)} with {moves} moves" + (" - new record!" if record else "")
            self.best_text = self._best_text()
        elif self.state.auto_solved:
            self.status = f"The AI solved it in {moves} moves (not ranked)"
        else:
            self.status = f"Solved in {moves} moves (undo used, not ranked)"

    # ------------------------------------------------------------------ AI actions
    def _can_start_search(self) -> bool:
        if self.state.won:
            self.status = "Already solved - press R for a new game"
            return False
        return self.job is None and not self.auto_active

    def _start_job(self, purpose: str, label: str, status: str) -> None:
        self.job = SolveJob(purpose, label, self.state.board)
        self.job.start()
        self.status = status

    def _hint(self) -> None:
        if self._can_start_search():
            self._start_job("hint", self.solver_option, "Finding the best next move...")

    def _toggle_auto(self) -> None:
        if self.job is not None or self.auto_active:
            self._cancel_everything()
            self.status = "Stopped"
        elif self._can_start_search():
            self._start_job("auto", self.solver_option, "Searching for a solution...")

    def _poll_job(self) -> None:
        job = self.job
        if job is None or not job.done:
            return
        self.job = None
        if job.cancel_event.is_set():
            return
        if job.error:
            self.status = job.error
            return
        result = job.result
        if result is None or result.path is None:
            self.status = "No solution found within the search limits"
            return
        self.metrics = {
            "solver": job.label,
            "nodes_explored": result.nodes_explored,
            "time_ms": result.time_ms,
            "solution_length": len(result.path) - 1,
        }
        if job.purpose == "hint":
            if len(result.path) > 1:
                self.hint_board = job.start_board
                self.hint_index = job.start_board.changed_tile(result.path[1])
                self.status = f"Hint: slide the pulsing tile ({len(result.path) - 1} moves to go)"
        else:
            self.auto_queue = deque(result.path[1:])
            self.auto_active = bool(self.auto_queue)
            self._auto_delay_ms = 0.0
            self.status = f"Auto-solving: {len(result.path) - 1} moves"

    def _advance_autoplay(self, dt_ms: float) -> None:
        if not self.auto_queue:
            return
        self._auto_delay_ms += dt_ms
        if self.animations.is_animating() or self._auto_delay_ms < AUTO_SOLVE_STEP_DELAY_MS:
            return
        self._auto_delay_ms = 0.0
        target = self.auto_queue.popleft()
        self._apply_slide(self.state.board.changed_tile(target), auto=True)
        if not self.auto_queue:
            self.auto_active = False

    # ------------------------------------------------------------------ events and loop
    def _dispatch(self, action: Action) -> None:
        kind, value = action.type, action.value
        if kind is ActionType.QUIT:
            self.running = False
        elif kind is ActionType.NEW_GAME:
            self.new_game()
        elif kind is ActionType.SET_SIZE:
            if value != self.size:
                self.new_game(int(value))  # type: ignore[arg-type]
        elif kind is ActionType.SET_SOLVER:
            self.status = f"Solver: {self.solver_option}"
        elif kind is ActionType.TOGGLE_THEME:
            self.theme_name = next_theme_name(self.theme_name)
            self.renderer.set_theme(self.theme_name)
            self.hud.set_theme(self.theme)
        elif kind is ActionType.SLIDE_INDEX:
            self._manual_slide(int(value))  # type: ignore[arg-type]
        elif kind is ActionType.SLIDE_DIRECTION:
            index = self.state.board.tile_index_for_direction(*value)  # type: ignore[misc]
            if index is not None:
                self._manual_slide(index)
        elif kind is ActionType.UNDO:
            self._undo_redo(undo=True)
        elif kind is ActionType.REDO:
            self._undo_redo(undo=False)
        elif kind is ActionType.HINT:
            self._hint()
        elif kind is ActionType.AUTO_SOLVE:
            self._toggle_auto()
        elif kind is ActionType.CANCEL:
            if self.job is not None or self.auto_active:
                self._cancel_everything()
                self.status = "Stopped"

    def _update(self, dt_ms: float) -> None:
        self.animations.update(dt_ms)
        self.particles.update(dt_ms)
        self._poll_job()
        self._advance_autoplay(dt_ms)
        self._spawn_win_bursts()

    def _spawn_win_bursts(self) -> None:
        if self.win_started_ms is None:
            return
        now = pygame.time.get_ticks()
        since_win = now - self.win_started_ms
        if since_win > WIN_BURST_DURATION_MS or now - self._last_burst_ms < WIN_BURST_INTERVAL_MS:
            return
        self._last_burst_ms = now
        grid = self.renderer.grid_rect
        self.particles.burst(
            self.rng.uniform(grid.left, grid.right),
            self.rng.uniform(grid.top, grid.centery),
            TILE_GRADIENT_STOPS,
        )

    def _draw(self) -> None:
        now = pygame.time.get_ticks()
        theme = self.theme
        self.renderer.clear()

        hint_index = None
        if self.hint_board is not None and self.hint_board == self.state.board and not self.state.won:
            hint_index = self.hint_index
        glow = None
        if self.state.won and self.win_started_ms is not None:
            glow = pulse(now - self.win_started_ms, WIN_GLOW_PERIOD_MS)
        self.renderer.draw_board(self.state.board, self.animations.positions(), hint_index,
                                 pulse(now, HINT_PULSE_PERIOD_MS), glow)
        self.renderer.draw_particles(self.particles.particles)

        job = self.job
        self.visualizer.draw(
            self.screen, self.visualizer_rect, theme,
            active=job is not None,
            label=job.label if job else "",
            nodes=job.nodes if job else 0,
            history=list(job.history) if job else (),
            status=self.status,
            now_ms=now,
        )
        self.hud.draw(self.screen, HudView(
            elapsed_s=self.state.elapsed(),
            moves=self.state.moves,
            metrics=self.metrics,
            live_nodes=job.nodes if job else None,
            best_text=self.best_text,
            board_size=self.size,
            busy=job is not None,
            autoplaying=self.auto_active,
            won=self.state.won,
        ))
        pygame.display.flip()

    def run(self) -> None:
        """Run the main loop until the window is closed."""
        try:
            while self.running:
                dt_ms = self.clock.tick(FPS)
                for event in pygame.event.get():
                    action = self.input.translate(event, self.size)
                    if action is not None:
                        self._dispatch(action)
                self._update(dt_ms)
                self._draw()
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Stop background work and release resources."""
        self._cancel_everything()
        self.leaderboard.close()
        pygame.quit()
        logger.info("Game closed")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="AI Puzzle Solver Game")
    parser.add_argument("--size", type=int, choices=BOARD_SIZES, default=DEFAULT_BOARD_SIZE,
                        help="initial board size (default: %(default)s)")
    parser.add_argument("--theme", choices=list(THEMES), default="dark", help="colour theme")
    parser.add_argument("--no-sound", action="store_true", help="disable sound effects")
    parser.add_argument("--seed", type=int, default=None, help="seed for reproducible scrambles")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Program entry point."""
    args = parse_args(argv)
    PuzzleApp(args.size, args.theme, sound=not args.no_sound, seed=args.seed).run()


if __name__ == "__main__":
    main()
