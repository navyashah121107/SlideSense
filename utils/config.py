"""Central configuration for the AI Puzzle Solver Game.

Role: the single source of truth for every tunable constant (sizes, timings,
search limits, file paths, colours, layout). Pure module: importing it has no
side effects. Run ``python -m utils.config`` to print a summary.
"""

from __future__ import annotations

from pathlib import Path

Color = tuple[int, int, int]

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
LOG_DIR: Path = PROJECT_ROOT / "logs"
LOG_FILE: Path = LOG_DIR / "game.log"
DATA_DIR: Path = PROJECT_ROOT / "data"
LEADERBOARD_DB_PATH: Path = DATA_DIR / "leaderboard.db"
ASSETS_DIR: Path = PROJECT_ROOT / "assets"
SOUNDS_DIR: Path = ASSETS_DIR / "sounds"
FONTS_DIR: Path = ASSETS_DIR / "fonts"
SLIDE_SOUND_FILE = "slide.wav"
WIN_SOUND_FILE = "win.wav"

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
LOGGER_ROOT_NAME = "puzzle"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 3

# ----------------------------------------------------------------------------
# Board / game rules
# ----------------------------------------------------------------------------
BOARD_SIZES: tuple[int, ...] = (3, 4, 5)
DEFAULT_BOARD_SIZE = 3
MIN_BOARD_SIZE = 2
BLANK = 0

# (row delta, col delta) the blank can move in. Order is part of the contract
# so search results are deterministic.
BLANK_DIRECTIONS: tuple[tuple[int, int], ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))

# Direction a *tile* travels for each arrow key (row delta, col delta).
DIRECTION_UP = (-1, 0)
DIRECTION_DOWN = (1, 0)
DIRECTION_LEFT = (0, -1)
DIRECTION_RIGHT = (0, 1)

# Scrambling. ``None`` = uniform random permutation fixed up by inversion
# parity (any difficulty). An int = random walk of that many moves from the
# goal, which keeps 4x4 / 5x5 puzzles solvable by pure-Python A* in seconds.
SCRAMBLE_MOVES: dict[int, int | None] = {3: None, 4: 30, 5: 24}
SCRAMBLE_MAX_ATTEMPTS = 1000

# ----------------------------------------------------------------------------
# Search limits
# ----------------------------------------------------------------------------
SOLVER_OPTIONS: tuple[str, ...] = ("A* (Manhattan)",)
DEFAULT_SOLVER_OPTION = "A* (Manhattan)"
COMPARE_SOLVER_OPTIONS: tuple[str, ...] = ("BFS", "A* (Manhattan)", "A* (Linear Conflict)")  # used only by ai.comparator benchmark

BFS_NODE_CAP = 500_000
BFS_MAX_SIZE = 5  # BFS refuses boards with size >= this (memory blow-up)
ASTAR_NODE_CAP = 400_000
DFS_DEFAULT_DEPTH_LIMIT = 30
DFS_NODE_CAP = 500_000
PROGRESS_INTERVAL = 512  # nodes between progress callbacks / cancel checks

# ----------------------------------------------------------------------------
# Window and layout
# ----------------------------------------------------------------------------
WINDOW_TITLE = "AI Puzzle Solver"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700
FPS = 60
GRID_PANEL_SIZE = 600
SIDE_PANEL_WIDTH = 300
GRID_MARGIN = 20
GRID_PIXELS = GRID_PANEL_SIZE - 2 * GRID_MARGIN
GRID_CORNER_RADIUS = 18
TILE_PADDING = 6
TILE_CORNER_RADIUS = 14
TILE_SHADE = 0.18
TILE_FONT_RATIO = 0.42
TILE_SHADOW_OFFSET = 2

VISUALIZER_TOP = GRID_MARGIN + GRID_PIXELS + 12
VISUALIZER_HEIGHT = WINDOW_HEIGHT - VISUALIZER_TOP - GRID_MARGIN
PANEL_CORNER_RADIUS = 12
PANEL_INNER_PADDING = 14
SPARKLINE_MAX_POINTS = 120
SPARKLINE_WIDTH = 2

HUD_PADDING = 20
HUD_TOP = 16
HUD_SECTION_GAP = 14
HUD_BUTTON_HEIGHT = 40
HUD_BUTTON_GAP = 10
HUD_SIZE_BUTTON_HEIGHT = 30
HUD_SIZE_BUTTON_GAP = 8
HUD_DROPDOWN_HEIGHT = 34
HUD_METRICS_HEIGHT = 140
HUD_METRICS_LINE_HEIGHT = 24
HUD_CORNER_RADIUS = 10
HUD_SHORTCUT_LINE_HEIGHT = 18
HUD_SHORTCUT_LINES: tuple[str, ...] = (
    "Arrows: slide  |  H: hint  |  S: solve",
    "R: new  |  T: theme",
    "Z: undo  |  Y: redo  |  3/4/5: size",
)

FONT_SIZE_TITLE = 28
FONT_SIZE_TIMER = 52
FONT_SIZE_LABEL = 20
FONT_SIZE_SMALL = 16
FONT_SIZE_BIG_NUMBER = 28
FONT_SIZE_CARD_TITLE = 18

COMPARISON_MARGIN = 20
COMPARISON_GAP = 12
COMPARISON_OVERLAY_ALPHA = 240
COMPARISON_BAR_HEIGHT = 12
COMPARISON_ROW_GAP = 14

# ----------------------------------------------------------------------------
# Animation and effects
# ----------------------------------------------------------------------------
SLIDE_DURATION_MS = 150
AUTO_SOLVE_STEP_DELAY_MS = 60
HINT_PULSE_PERIOD_MS = 800
HINT_BORDER_MIN = 3
HINT_BORDER_MAX = 7
HINT_ALPHA_MIN = 110
HINT_ALPHA_MAX = 255
WIN_GLOW_PERIOD_MS = 1200
WIN_GLOW_LAYERS = 3
WIN_GLOW_SPREAD = 4
WIN_GLOW_ALPHA_MAX = 200
GLOW_MIN_STRENGTH = 0.35
WIN_GLOW_BORDER = 3
WIN_BURST_DURATION_MS = 2500
WIN_BURST_INTERVAL_MS = 250
PARTICLES_PER_BURST = 36
PARTICLE_SPEED_MIN = 80.0
PARTICLE_SPEED_MAX = 380.0
PARTICLE_LIFE_MS_MIN = 600.0
PARTICLE_LIFE_MS_MAX = 1400.0
PARTICLE_GRAVITY = 420.0
PARTICLE_RADIUS_MIN = 3.0
PARTICLE_RADIUS_MAX = 7.0
SPINNER_DOTS = 4
SPINNER_PERIOD_MS = 1000

# ----------------------------------------------------------------------------
# Colours (themes live in ui/theme.py)
# ----------------------------------------------------------------------------
COLORS: dict[str, Color] = {"white": (255, 255, 255), "black": (0, 0, 0)}
# blue -> green -> yellow -> red, sampled by tile number
TILE_GRADIENT_STOPS: tuple[Color, ...] = (
    (52, 120, 246),
    (46, 204, 113),
    (241, 196, 15),
    (231, 76, 60),
)

# ----------------------------------------------------------------------------
# Leaderboard and sound
# ----------------------------------------------------------------------------
LEADERBOARD_TOP_N = 5
SOUND_SAMPLE_RATE = 22_050
SOUND_SLIDE_FREQ_HZ = 520.0
SOUND_SLIDE_MS = 70
SOUND_SLIDE_VOLUME = 0.35
SOUND_WIN_NOTES_HZ: tuple[float, ...] = (523.25, 659.25, 783.99, 1046.50)
SOUND_WIN_NOTE_MS = 140
SOUND_WIN_LAST_NOTE_MS = 420
SOUND_WIN_VOLUME = 0.4
SOUND_PCM_MAX = 32767
SOUND_DECAY_RATE = 4.0
SOUND_ATTACK_S = 0.005


if __name__ == "__main__":
    print(f"Project root : {PROJECT_ROOT}")
    print(f"Board sizes  : {BOARD_SIZES}")
    print(f"Window       : {WINDOW_WIDTH}x{WINDOW_HEIGHT} @ {FPS} FPS")
    print(f"Solvers      : {SOLVER_OPTIONS}")
