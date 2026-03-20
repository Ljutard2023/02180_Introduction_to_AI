"""
Ricochet Robots – Game Rules and Logic
=======================================
Implements the game mechanics on top of the Board model.

Defines:
  - Move / Solution types
  - Helper functions for ricochet detection, goal testing, and heuristic
  - Game class exposing:
      get_moves()        — legal moves from a state
      apply_move()       — produce a new state from a move
      is_goal()          — win-condition check
      get_successors()   — iterator over (move, new_state, new_history)
    state_key()        — hashable state key for visited sets
        heuristic_1()      — H1 for A*1 (alignment + ricochet)
        heuristic_2()      — H2 for A*2 (normalized Manhattan + alignment)
        heuristic_3()      — H3 for A*3 (Manhattan + alignment + ricochet)
"""

from __future__ import annotations

from typing import Iterator
from collections import deque


from board import Board, Robots, COLORS, DIR_LIST, CFG, _copy_robots, _skey


# ── Types ──────────────────────────────────────────────────────────────────────

Move     = tuple[str, str]       # (color, direction)
Solution = list[Move] | None


# ── Game state helpers ─────────────────────────────────────────────────────────

def _active_dirs(hist: list[Move], active: str) -> list[str]:
    """Return the sequence of directions the active robot moved in *hist*."""
    return [d for col, d in hist if col == active]


def _ricocheted(hist: list[Move], active: str) -> bool:
    """Return True if *active* robot changed direction at least once in *hist*."""
    dirs = _active_dirs(hist, active)
    for i in range(1, len(dirs)):
        if dirs[i] != dirs[i - 1]:
            return True
    return False


def _reached(robots: Robots, active: str,
             tpos: tuple[int, int], hist: list[Move]) -> bool:
    """Win condition: active robot is on target AND has already ricocheted."""
    return robots.get(active) == tpos and _ricocheted(hist, active)


def _aligned(pos: tuple[int, int] | None, tpos: tuple[int, int]) -> bool:
    """Return True when *pos* is on the same row or column as *tpos*."""
    return pos is not None and (pos[0] == tpos[0] or pos[1] == tpos[1])


def _manhattan_norm(pos: tuple[int, int] | None, tpos: tuple[int, int]) -> float:
    """Return Manhattan distance normalized by 30 (max on 16x16 grid)."""
    if pos is None:
        return 0.0
    return (abs(pos[0] - tpos[0]) + abs(pos[1] - tpos[1])) / 30.0


def _heuristic_1(robots: Robots, active: str,
                 tpos: tuple[int, int], rh: bool) -> int:
    """
    Heuristic H1 for A*1 (alignment + ricochet).

    Returns 0/1/2 based on goal, alignment, and ricochet state.
    """
    pos = robots.get(active)
    if pos == tpos and rh:
        return 0
    if rh and pos is not None:
        if _aligned(pos, tpos):
            return 1
        return 2
    return 2


def _heuristic_2(robots: Robots, active: str,
                 tpos: tuple[int, int]) -> float:
    """
    Heuristic H2 for A*2 (normalized Manhattan + alignment).

        Uses only a geometric term and an alignment term.
    """
    pos = robots.get(active)
    if pos is None:
        return 0.0
    manhattan = (abs(pos[0] - tpos[0]) + abs(pos[1] - tpos[1])) / 30.0
    align_penalty = 0.0 if _aligned(pos, tpos) else (28.0 / 30.0)
    return manhattan + align_penalty


def _heuristic_3(robots: Robots, active: str,
                 tpos: tuple[int, int], rh: bool) -> float:
    """
    Heuristic H3 for A*3 (Manhattan + alignment + ricochet).

    Uses all three requested components without depending on H1/H2.
    """
    pos = robots.get(active)
    manhattan = _manhattan_norm(pos, tpos)
    align_penalty = 0.0 if _aligned(pos, tpos) else (28.0 / 30.0)
    ricochet_penalty = 0.0 if rh else 1.0
    return manhattan + align_penalty + ricochet_penalty

"""
def _can_slide_to(board, robots: Robots, active: str,
                  tpos: tuple[int, int]) -> bool:
    for d in DIR_LIST:
        if board.slide(robots, active, d) == tpos:
            return True
    return False


def _heuristic_4(board, robots: Robots, active: str,
                 tpos: tuple[int, int], rh: bool) -> int:
    pos = robots.get(active)
    if pos == tpos and rh:
        return 0
    if _can_slide_to(board, robots, active, tpos):
        return 1 if rh else 2
    return 2
"""

def _min_moves_to_target(board, robots: Robots, active: str,
                          tpos: tuple[int, int],
                          max_depth: int = 4) -> int:   # ← limite à 4
    start = robots.get(active)
    if start == tpos:
        return 0
    queue   = deque([(start, 0)])
    visited = {start}
    while queue:
        pos, moves = queue.popleft()
        if moves >= max_depth:        # ← stop si trop profond
            continue
        temp = dict(robots)
        temp[active] = pos
        for d in DIR_LIST:
            npos = board.slide(temp, active, d)
            if npos == pos or npos in visited:
                continue
            if npos == tpos:
                return moves + 1
            visited.add(npos)
            queue.append((npos, moves + 1))
    return max_depth + 1   # ← valeur par défaut si non trouvé


def _heuristic_4(board, robots: Robots, active: str,
                 tpos: tuple[int, int], rh: bool) -> int:
    pos = robots.get(active)
    if pos == tpos and rh:
        return 0
    min_moves = _min_moves_to_target(board, robots, active, tpos)
    if not rh and min_moves <= 1:
        return min_moves + 1
    return min_moves

def _state_key(robots: Robots, hist: list[Move], active: str) -> tuple:
    """
    Compact, hashable visited-set key that captures everything that matters
    for future search decisions: robot positions + whether the active robot
    has already satisfied the ricochet requirement.
    """
    return (_skey(robots), _ricocheted(hist, active))


# ── Game class ─────────────────────────────────────────────────────────────────

class Game:
    """
    Wraps a Board and exposes higher-level game-rule methods.

    This is the object passed to each solver so that solvers remain
    decoupled from low-level board details.
    """

    def __init__(self, board: Board) -> None:
        self.board = board

    def get_moves(self, robots: Robots) -> list[Move]:
        """
        Return every legal move from *robots* — i.e. every (color, direction)
        pair that actually changes a robot's position.
        """
        moves: list[Move] = []
        for col in COLORS:
            for d in DIR_LIST:
                if self.board.slide(robots, col, d) != robots[col]:
                    moves.append((col, d))
        return moves

    def target_pos(self, target: tuple) -> tuple[int, int]:
        """Return `(row, col)` from a target descriptor tuple."""
        return (target[0], target[1])

    def apply_move(self, robots: Robots, move: Move) -> Robots:
        """Apply *move* to *robots* and return the resulting state (new dict)."""
        col, d = move
        nc = _copy_robots(robots)
        nc[col] = self.board.slide(robots, col, d)
        return nc

    def has_ricocheted(self, history: list[Move], active: str) -> bool:
        """Return True if the active robot changed direction at least once."""
        return _ricocheted(history, active)

    def state_key(self, robots: Robots, history: list[Move], active: str) -> tuple:
        """Return a compact, hashable key suitable for visited-state sets."""
        return _state_key(robots, history, active)

    def is_goal(self, robots: Robots, history: list[Move],
                active: str, target_pos: tuple[int, int]) -> bool:
        """
        Return True when *active* robot is on *target_pos* AND has already
        changed direction at least once (ricochet requirement).
        """
        return _reached(robots, active, target_pos, history)

    def heuristic_1(self, robots: Robots, active: str,
                    target_pos: tuple[int, int], history: list[Move]) -> int:
        """H1 used by A*1: alignment + ricochet."""
        return _heuristic_1(robots, active, target_pos,
                            self.has_ricocheted(history, active))

    def heuristic_2(self, robots: Robots, active: str,
                    target_pos: tuple[int, int], history: list[Move]) -> float:
        """H2 used by A*2: normalized Manhattan + alignment."""
        _ = history
        return _heuristic_2(robots, active, target_pos)

    def heuristic_3(self, robots: Robots, active: str,
                    target_pos: tuple[int, int], history: list[Move]) -> float:
        """H3 used by A*3: Manhattan + alignment + ricochet."""
        return _heuristic_3(robots, active, target_pos,
                            self.has_ricocheted(history, active))
    """
    def heuristic_4(self, robots: Robots, active: str,
                    target_pos: tuple[int, int], history: list[Move]) -> int:
        #H4 : reachability réelle + ricochet. Domine H1.
        return _heuristic_4(self.board, robots, active, target_pos,
                        self.has_ricocheted(history, active))

    def heuristic_5(self, robots: Robots, active: str,
                    target_pos: tuple[int, int], history: list[Move]) -> float:
        #H5 : max(H3, H4) — domine les deux, admissible.
        return max(
            self.heuristic_3(robots, active, target_pos, history),
            self.heuristic_4(robots, active, target_pos, history)
    )
    """
    def heuristic_4(self, robots: Robots, active: str,
                    target_pos: tuple[int, int], history: list[Move]) -> int:
        """H4 : mini-BFS exact sur robot actif."""
        return _heuristic_4(self.board, robots, active, target_pos,
                            self.has_ricocheted(history, active))

    def get_successors(
        self, robots: Robots, history: list[Move], active: str
    ) -> Iterator[tuple[Move, Robots, list[Move]]]:
        """
        Yield (move, new_robots, new_history) for every legal move from the
        current state.  Skips moves that leave a robot in place.
        """
        for col in COLORS:
            for d in DIR_LIST:
                npos = self.board.slide(robots, col, d)
                if npos == robots[col]:
                    continue
                nc = _copy_robots(robots)
                nc[col] = npos
                nh = history + [(col, d)]
                yield (col, d), nc, nh
