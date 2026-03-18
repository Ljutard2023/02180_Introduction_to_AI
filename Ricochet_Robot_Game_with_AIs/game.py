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
"""

from __future__ import annotations

from typing import Iterator

from board import Board, Robots, COLORS, DIR_LIST, _copy_robots, _skey


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


def _heuristic(robots: Robots, active: str,
               tpos: tuple[int, int], rh: bool) -> int:
    """
    Admissible heuristic used by A*1 (phase heuristic).

    Returns
    -------
    0  — active robot is already on target and has ricocheted  (goal)
    1  — robot has ricocheted but hasn't reached the target yet
    2  — robot hasn't ricocheted yet  (needs at least two more moves)

    This is admissible: each case is a lower bound on the remaining moves.
    """
    if robots.get(active) == tpos and rh:
        return 0
    return 1 if rh else 2


def _heuristic_aligned(robots: Robots, active: str,
                       tpos: tuple[int, int], rh: bool) -> int:
    """
    Stronger admissible heuristic used by A*2 (alignment-aware).

    Rationale
    ---------
    In Ricochet Robots a robot can only stop *on* the target cell when it
    slides along the same row or column and is not blocked before it.
    Therefore:

    • If the active robot has already ricocheted **and** is on the same row
      or column as the target → at best 1 more slide needed  →  h = 1.
    • If the active robot has ricocheted but is **not** aligned with the
      target → it needs ≥ 1 slide to reach the target's row/column PLUS
      ≥ 1 slide to reach the target itself  →  h = 2.
    • If the robot has not yet ricocheted, at least 2 more moves are always
      needed (same as the phase heuristic)  →  h = 2.

    This is always ≥ _heuristic() (never overestimates) and therefore
    admissible.  It is strictly stronger in the "ricocheted, not aligned"
    case, so A*2 typically expands fewer nodes than A*1.

    Returns
    -------
    0, 1, or 2  — admissible lower bound on remaining moves.
    """
    pos = robots.get(active)
    if pos == tpos and rh:
        return 0
    if rh and pos is not None:
        if pos[0] == tpos[0] or pos[1] == tpos[1]:
            return 1   # aligned with target — at least 1 more move needed
        return 2       # not aligned — need ≥ 2 more slides to align then reach
    return 2           # ricochet not yet satisfied — need ≥ 2 more moves


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

    def apply_move(self, robots: Robots, move: Move) -> Robots:
        """Apply *move* to *robots* and return the resulting state (new dict)."""
        col, d = move
        nc = _copy_robots(robots)
        nc[col] = self.board.slide(robots, col, d)
        return nc

    def is_goal(self, robots: Robots, history: list[Move],
                active: str, target_pos: tuple[int, int]) -> bool:
        """
        Return True when *active* robot is on *target_pos* AND has already
        changed direction at least once (ricochet requirement).
        """
        return _reached(robots, active, target_pos, history)

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
