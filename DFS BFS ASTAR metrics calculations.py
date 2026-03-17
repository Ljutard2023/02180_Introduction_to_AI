import math
import heapq
import time
import threading
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Iterator
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

@dataclass(frozen=True)
class Config:
    N: int = 16                  # grid size
    CS: int = 44                 # cell size (px)
    M: int = 24                  # canvas margin (px) for coordinate labels
    TIMEOUT: float = 10.0        # solver timeout (s)
    ANIM_FRAMES: int = 8         # robot slide animation frames
    ANIM_MS: int = 18            # ms per animation frame
    PULSE_MS: int = 800          # target pulse interval (ms)
    AUTO_PLAY_MS: int = 600      # default auto-play interval (ms)

CFG = Config()

COLORS: tuple[str, ...] = ('red', 'green', 'blue', 'yellow')
SYMBOLS: tuple[str, ...] = ('circle', 'square', 'triangle', 'star')
DIR_LIST: tuple[str, ...] = ('N', 'S', 'E', 'W')

CENTER: frozenset[tuple[int, int]] = frozenset({(7, 7), (7, 8), (8, 7), (8, 8)})

HEX: dict[str, str] = {
    'red':    '#E74C3C',
    'green':  '#2ECC71',
    'blue':   '#3498DB',
    'yellow': '#F1C40F',
    'all':    '#9B59B6',
    'silver': '#95A5A6',
}

DIRS: dict[str, tuple[int, int]] = {
    'N': (-1,  0),
    'S': ( 1,  0),
    'W': ( 0, -1),
    'E': ( 0,  1),
}
OPP: dict[str, str] = {'N': 'S', 'S': 'N', 'W': 'E', 'E': 'W'}

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

    # Single Walls -------------------------------------------------------

    (0, 2, "E"),
    (0, 8, "E"),
    (15, 5, "E"),
    (15, 11, "E"),
    (3, 0, "S"),
    (10, 0, "S"),
    (1, 15, "S"),
    (9, 15, "S"),

    # L-walls -------------------------------------------------------

    (1, 5, "W"), (1, 5, "S"),
    (1, 11, "N"), (1, 11, "W"),
    (2, 7, "S"), (2, 7, "E"),
    (3, 14, "E"), (3, 14, "N"),
    (4, 3, "E"), (4, 3, "S"),
    (4, 9, "S"), (4, 9, "E"),
    (5, 6, "W"), (5, 6, "N"),
    (6, 1, "E"), (6, 1, "N"),
    (6, 12, "W"), (6, 12, "S"),
    (9, 1, "E"), (9, 1, "N"),
    (9, 5, "W"), (9, 5, "N"),
    (10, 8, "E"), (10, 8, "S"),
    (11, 13, "W"), (11, 13, "N"),
    (12, 6, "S"), (12, 6, "E"),
    (13, 9, "W"), (13, 9, "S"),
    (14, 2, "S"), (14, 2, "W"),
    (14, 14, "N"), (14, 14, "E"),
]

Robots = dict[str, tuple[int, int]]


class Board:
    """Immutable board with walls and targets; provides robot sliding logic."""
    __slots__ = ('walls', 'targets')

    def __init__(self) -> None:
        self.walls:   set[tuple[int, int, str]]       = set()
        self.targets: list[tuple[int, int, str, str]] = []
        self._build()

    def _add_wall(self, r: int, c: int, d: str) -> None:
        """Add physical wall on side *d* of cell (r, c) and mirror on neighbour."""
        if not (0 <= r < CFG.N and 0 <= c < CFG.N):
            return
        self.walls.add((r, c, d))
        dr, dc = DIRS[d]
        nr, nc = r + dr, c + dc
        if 0 <= nr < CFG.N and 0 <= nc < CFG.N:
            self.walls.add((nr, nc, OPP[d]))

    def _build(self) -> None:
        N = CFG.N
        # Perimeter walls
        for i in range(N):
            self.walls |= {(0, i, 'N'), (N-1, i, 'S'),
                           (i, 0, 'W'), (i, N-1, 'E')}
        # Centre block
        for r, c in CENTER:
            for d, (dr, dc) in DIRS.items():
                if (r + dr, c + dc) not in CENTER:
                    self.walls.add((r, c, d))
        # Targets + pocket walls
        for td in FIXED_TARGETS_DEF:
            r, c, color, sym, wd1, wd2 = td
            self.targets.append((r, c, color, sym))
            self._add_wall(r, c, wd1)
            self._add_wall(r, c, wd2)
        # Extra corridor walls
        for r, c, d in EXTRA_WALLS_DEF:
            self._add_wall(r, c, d)

    def slide(self, robots: Robots, color: str, d: str) -> tuple[int, int]:
        """Slide *color* robot in direction *d* until blocked; return new position."""
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


# ─────────────────────────────────────────────────────────────────────────────
#  SEARCH UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _skey(robots: Robots) -> tuple:
    """Canonical hashable key for a robots dict."""
    return tuple(sorted(robots.items()))

def _copy_robots(robots: Robots) -> Robots:
    """Shallow copy of robots dict."""
    return dict(robots)

def _active_dirs(hist: list[tuple[str, str]], active: str) -> list[str]:
    """Extract direction list for the active robot from move history."""
    return [d for col, d in hist if col == active]

def _ricocheted(hist: list[tuple[str, str]], active: str) -> bool:
    """Return True if *active* robot changed direction at least once in *hist*."""
    dirs = _active_dirs(hist, active)
    for i in range(1, len(dirs)):
        if dirs[i] != dirs[i - 1]:
            return True
    return False

def _reached(robots: Robots, active: str, tpos: tuple[int, int],
             hist: list[tuple[str, str]]) -> bool:
    """Win condition: active robot on target AND has ricocheted."""
    return robots.get(active) == tpos and _ricocheted(hist, active)

def _heuristic(robots: Robots, active: str,
               tpos: tuple[int, int], rh: bool) -> int:
    """
    Admissible heuristic shared by A* and IDA*.
      0  — already at goal with ricochet done
      1  — ricochet done, just need to reach target
      2  — ricochet not done yet
    """
    if robots.get(active) == tpos and rh:
        return 0
    return 1 if rh else 2

def _state_key(robots: Robots, hist: list[tuple[str, str]],
               active: str) -> tuple:
    """Visited-set key: (robot positions, ricochet_done)."""
    return (_skey(robots), _ricocheted(hist, active))



# Solvers

Move = tuple[str, str]          # (color, direction)
Solution = list[Move] | None

class SolverBFS:
    name  = "BFS"
    color = "#2ECC71"

    def __init__(self, board: Board) -> None:
        self.board = board

    def solve(self, robots: Robots, target: tuple, active: str,
            max_moves: int = 16):

        t_start = time.time()
        generated = 0

        tpos = (target[0], target[1])
        init_key = _state_key(robots, [], active)
        q = deque([(robots, [])])
        vis = {init_key}

        while q:
            cur, hist = q.popleft()

            if len(hist) >= max_moves:
                continue

            for col in COLORS:
                for d in DIR_LIST:
                    generated += 1

                    npos = self.board.slide(cur, col, d)
                    if npos == cur[col]:
                        continue

                    nc = _copy_robots(cur)
                    nc[col] = npos
                    nh = hist + [(col, d)]

                    if _reached(nc, active, tpos, nh):
                        t_end = time.time()
                        return {
                            "solution": nh,
                            "generated": generated,
                            "time": t_end - t_start,
                            "length": len(nh)
                        }

                    key = _state_key(nc, nh, active)
                    if key not in vis:
                        vis.add(key)
                        q.append((nc, nh))

        t_end = time.time()
        return {
            "solution": None,
            "generated": generated,
            "time": t_end - t_start,
            "length": None
        }

        return None


class SolverAStar:
    name  = "A*"
    color = "#3498DB"

    def __init__(self, board: Board) -> None:
        self.board = board

    def solve(self, robots: Robots, target: tuple, active: str,
              max_moves: int = 16):

        t_start = time.time()
        generated = 0

        tpos = (target[0], target[1])
        rh0 = False
        h0 = _heuristic(robots, active, tpos, rh0)

        ctr = 0
        heap = [(h0, 0, ctr, robots, [], rh0)]
        visited = set()

        while heap:
            f, g, _, cur, hist, rh = heapq.heappop(heap)

            if g >= max_moves:
                continue

            skey = (_skey(cur), rh)
            if skey in visited:
                continue
            visited.add(skey)

            for col in COLORS:
                for d in DIR_LIST:
                    generated += 1

                    npos = self.board.slide(cur, col, d)
                    if npos == cur[col]:
                        continue

                    nc = _copy_robots(cur)
                    nc[col] = npos
                    nh = hist + [(col, d)]
                    ng = g + 1

                    new_rh = rh or _ricocheted(nh, active)

                    if _reached(nc, active, tpos, nh):
                        t_end = time.time()
                        return {
                            "solution": nh,
                            "generated": generated,
                            "time": t_end - t_start,
                            "length": len(nh)
                        }

                    nskey = (_skey(nc), new_rh)
                    if nskey in visited:
                        continue

                    h = _heuristic(nc, active, tpos, new_rh)

                    ctr += 1
                    heapq.heappush(heap, (ng + h, ng, ctr, nc, nh, new_rh))

        t_end = time.time()
        return {
            "solution": None,
            "generated": generated,
            "time": t_end - t_start,
            "length": None
        }
    
class SolverDFS:
    name  = "DFS"
    color = "#E67E22"

    def __init__(self, board: Board) -> None:
        self.board = board

    def solve(self, robots: Robots, target: tuple, active: str,
              max_moves: int = 16):

        t_start = time.time()
        generated = 0

        tpos = (target[0], target[1])

        stack = [(robots, [])]   # LIFO stack
        visited = set()

        while stack:
            cur, hist = stack.pop()

            if len(hist) >= max_moves:
                continue

            skey = _state_key(cur, hist, active)
            if skey in visited:
                continue
            visited.add(skey)

            for col in COLORS:
                for d in DIR_LIST:
                    generated += 1

                    npos = self.board.slide(cur, col, d)
                    if npos == cur[col]:
                        continue

                    nc = _copy_robots(cur)
                    nc[col] = npos
                    nh = hist + [(col, d)]

                    if _reached(nc, active, tpos, nh):
                        t_end = time.time()
                        return {
                            "solution": nh,
                            "generated": generated,
                            "time": t_end - t_start,
                            "length": len(nh)
                        }

                    stack.append((nc, nh))  # DFS push

        t_end = time.time()
        return {
            "solution": None,
            "generated": generated,
            "time": t_end - t_start,
            "length": None
        }
    



if __name__ == "__main__":
    board = Board()

    robots = {
        'red': (0, 0),
        'green': (0, 5),
        'blue': (5, 0),
        'yellow': (5, 5),
    }

    target = board.targets[0]
    active = target[2]

    bfs_solver = SolverBFS(board)
    astar_solver = SolverAStar(board)
    dfs_solver = SolverDFS(board)

    bfs_result = bfs_solver.solve(robots, target, active)
    astar_result = astar_solver.solve(robots, target, active)
    dfs_result = dfs_solver.solve(robots, target, active)

    print("\n=== BFS Metrics ===")
    print(f"Generated states : {bfs_result['generated']}")
    print(f"Time (s)         : {bfs_result['time']:.4f}")
    print(f"Solution length  : {bfs_result['length']}")

    print("\n=== DFS Metrics ===")
    print(f"Generated states : {dfs_result['generated']}")
    print(f"Time (s)         : {dfs_result['time']:.4f}")
    print(f"Solution length  : {dfs_result['length']}")


    print("\n=== A* Metrics ===")
    print(f"Generated states : {astar_result['generated']}")
    print(f"Time (s)         : {astar_result['time']:.4f}")
    print(f"Solution length  : {astar_result['length']}")