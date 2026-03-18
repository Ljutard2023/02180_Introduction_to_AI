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
SYMBOLS:  tuple[str, ...] = ('bio', 'tar', 'tri', 'hex')
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
    (4,  9,  'blue',   'bio', 'S', 'E'),
    (1,  5,  'blue',   'tar', 'W', 'S'),
    (3,  14, 'blue',   'tri', 'E', 'N'),
    (11, 13, 'blue',   'hex', 'W', 'N'),
    (10, 8,  'yellow', 'bio', 'E', 'S'),
    (1,  11, 'yellow', 'tar', 'N', 'W'),
    (6,  1,  'yellow', 'tri', 'E', 'N'),
    (6,  12, 'yellow', 'hex', 'W', 'S'),
    (5,  6,  'green',  'bio', 'W', 'N'),
    (13, 9,  'green',  'tar', 'W', 'S'),
    (14, 2,  'green',  'tri', 'S', 'W'),
    (9,  1,  'green',  'hex', 'E', 'N'),
    (9,  5,  'red',    'bio', 'W', 'N'),
    (12, 6,  'red',    'tar', 'S', 'E'),
    (14, 14, 'red',    'tri', 'N', 'E'),
    (4,  3,  'red',    'hex', 'E', 'S'),
]

EXTRA_WALLS_DEF: list[tuple[int, int, str]] = [
    # Single walls touching borders
    (0,  2,  'E'),  (0,  8,  'E'),
    (15, 5,  'E'),  (15, 11, 'E'),
    (3,  0,  'S'),  (10, 0,  'S'),
    (1,  15, 'S'),  (9,  15, 'S'),
    # Extra L-wall (no target)
    (2,  7,  'S'),  (2,  7,  'E'),
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
