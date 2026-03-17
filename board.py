"""
Ricochet Robots – Board Model
==============================
Holds the board representation and all piece information.

Defines:
  - Board dimensions / coordinate system  (Config / CFG)
  - Piece types and their properties       (COLORS, SYMBOLS, HEX, …)
  - Fixed wall and target definitions      (FIXED_TARGETS_DEF, EXTRA_WALLS_DEF)
  - State representation                   (Robots dict)
  - Helpers for cloning/hashing state      (_skey, _copy_robots)
  - Board class with wall data + slide()
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Configuration ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Config:
    N: int   = 16    # grid size (cells per side)
    CS: int  = 44    # cell size in pixels
    M: int   = 24    # canvas margin in pixels (for coordinate labels)
    TIMEOUT: float = 10.0    # solver timeout in seconds
    ANIM_FRAMES: int = 8     # robot slide animation frames
    ANIM_MS: int     = 18    # ms per animation frame
    PULSE_MS: int    = 800   # target pulse interval (ms)
    AUTO_PLAY_MS: int = 600  # default auto-play interval (ms)
    SOLVER_MAX_MOVES: int = 16  # search depth limit for all solvers

CFG = Config()


# ── Piece / direction constants ────────────────────────────────────────────────

COLORS:   tuple[str, ...] = ('red', 'green', 'blue', 'yellow')
SYMBOLS:  tuple[str, ...] = ('circle', 'square', 'triangle', 'star')
DIR_LIST: tuple[str, ...] = ('N', 'S', 'E', 'W')

# The unreachable 2×2 centre block
CENTER: frozenset[tuple[int, int]] = frozenset({(7, 7), (7, 8), (8, 7), (8, 8)})

# Hex colour codes for each robot / special colour
HEX: dict[str, str] = {
    'red':    '#E74C3C',
    'green':  '#2ECC71',
    'blue':   '#3498DB',
    'yellow': '#F1C40F',
    'all':    '#9B59B6',
    'silver': '#95A5A6',
}

# Direction vectors (row-delta, col-delta)
DIRS: dict[str, tuple[int, int]] = {
    'N': (-1,  0),
    'S': ( 1,  0),
    'W': ( 0, -1),
    'E': ( 0,  1),
}

# Opposite directions
OPP: dict[str, str] = {'N': 'S', 'S': 'N', 'W': 'E', 'E': 'W'}


# ── Fixed board definitions ────────────────────────────────────────────────────

# (row, col, color, symbol, wall_dir_A, wall_dir_B)
FIXED_TARGETS_DEF: list[tuple] = [
    (1,  2,  'red',    'circle',   'S', 'E'),
    (2,  13, 'red',    'square',   'N', 'W'),
    (11, 5,  'red',    'triangle', 'S', 'E'),
    (9,  12, 'red',    'star',     'N', 'W'),
    (3,  1,  'green',  'circle',   'N', 'E'),
    (4,  9,  'green',  'square',   'S', 'W'),
    (1,  6,  'green',  'triangle', 'S', 'W'),
    (13, 3,  'green',  'star',     'N', 'E'),
    (5,  4,  'blue',   'circle',   'N', 'E'),
    (2,  10, 'blue',   'square',   'S', 'W'),
    (10, 2,  'blue',   'triangle', 'S', 'E'),
    (6,  14, 'blue',   'star',     'N', 'W'),
    (4,  6,  'yellow', 'circle',   'S', 'E'),
    (1,  11, 'yellow', 'square',   'N', 'W'),
    (12, 9,  'yellow', 'triangle', 'S', 'W'),
    (14, 13, 'yellow', 'star',     'N', 'W'),
    (8,  11, 'all',    'vortex',   'S', 'W'),
]

EXTRA_WALLS_DEF: list[tuple[int, int, str]] = [
    (2,  3,  'E'),  (3,  3,  'S'),
    (5,  2,  'N'),  (5,  2,  'E'),
    (6,  5,  'S'),  (6,  5,  'W'),
    (3,  7,  'S'),
    (2,  8,  'S'),
    (3,  12, 'N'),  (3,  12, 'E'),
    (5,  10, 'S'),  (5,  11, 'W'),
    (6,  8,  'N'),
    (9,  1,  'S'),  (9,  4,  'N'),
    (10, 6,  'E'),  (11, 7,  'S'),
    (13, 5,  'N'),  (14, 2,  'E'),
    (9,  9,  'S'),  (9,  13, 'N'),
    (11, 11, 'E'),  (12, 10, 'N'),
    (13, 14, 'S'),  (14, 8,  'E'),
    (6,  3,  'N'),  (9,  6,  'S'),
    (6,  13, 'S'),  (9,  10, 'N'),
]


# ── State type ─────────────────────────────────────────────────────────────────

# Mapping from robot colour to its (row, col) position
Robots = dict[str, tuple[int, int]]


# ── State helpers ──────────────────────────────────────────────────────────────

def _skey(robots: Robots) -> tuple:
    """Return a canonical, hashable key for a robots-position dict."""
    return tuple(sorted(robots.items()))


def _copy_robots(robots: Robots) -> Robots:
    """Return a shallow copy of a robots dict."""
    return dict(robots)


# ── Board class ────────────────────────────────────────────────────────────────

class Board:
    """
    Immutable board with walls and targets.

    Attributes
    ----------
    walls   : set of (row, col, direction) wall segments
    targets : list of (row, col, color, symbol) target definitions

    Methods
    -------
    slide(robots, color, direction) -> (row, col)
        Slide the named robot in a direction until it hits a wall or another
        robot, and return its final position.
    """

    __slots__ = ('walls', 'targets')

    def __init__(self) -> None:
        self.walls:   set[tuple[int, int, str]]       = set()
        self.targets: list[tuple[int, int, str, str]] = []
        self._build()

    def _add_wall(self, r: int, c: int, d: str) -> None:
        """Add a wall on side *d* of cell (r, c) and its mirror on the neighbour."""
        if not (0 <= r < CFG.N and 0 <= c < CFG.N):
            return
        self.walls.add((r, c, d))
        dr, dc = DIRS[d]
        nr, nc = r + dr, c + dc
        if 0 <= nr < CFG.N and 0 <= nc < CFG.N:
            self.walls.add((nr, nc, OPP[d]))

    def _build(self) -> None:
        """Populate walls and targets from the fixed definitions."""
        N = CFG.N
        # Perimeter walls
        for i in range(N):
            self.walls |= {(0, i, 'N'), (N - 1, i, 'S'),
                           (i, 0, 'W'), (i, N - 1, 'E')}
        # Centre block walls (robots cannot enter)
        for r, c in CENTER:
            for d, (dr, dc) in DIRS.items():
                if (r + dr, c + dc) not in CENTER:
                    self.walls.add((r, c, d))
        # Target pocket walls
        for td in FIXED_TARGETS_DEF:
            r, c, color, sym, wd1, wd2 = td
            self.targets.append((r, c, color, sym))
            self._add_wall(r, c, wd1)
            self._add_wall(r, c, wd2)
        # Extra corridor walls
        for r, c, d in EXTRA_WALLS_DEF:
            self._add_wall(r, c, d)

    def slide(self, robots: Robots, color: str, d: str) -> tuple[int, int]:
        """
        Slide robot *color* in direction *d* until blocked.

        A robot stops when it reaches:
          - a wall on the current or next cell face in the travel direction,
          - another robot, or
          - the boundary of the centre block.

        Returns the final (row, col) position (unchanged if already blocked).
        """
        r, c = robots[color]
        dr, dc = DIRS[d]
        others = {pos for col, pos in robots.items() if col != color}
        while True:
            if (r, c, d) in self.walls:
                break
            nr, nc = r + dr, c + dc
            if not (0 <= nr < CFG.N and 0 <= nc < CFG.N):
                break
            if (nr, nc, OPP[d]) in self.walls:
                break
            if (nr, nc) in others:
                break
            if (nr, nc) in CENTER:
                break
            r, c = nr, nc
        return (r, c)
