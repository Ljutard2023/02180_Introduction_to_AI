"""
Ricochet Robots – A*2 Solver (alignment heuristic H2)
=======================================================
A second A* variant that uses the *alignment-aware* heuristic H2 instead of
the simple phase heuristic H1 used by A*1.

Admissible heuristic H2 (alignment-aware):
  0 — active robot is at the target and has already ricocheted  (goal)
  1 — robot has ricocheted AND is on the same row or column as the target
      (it can reach the target in ≥ 1 more slide)
  2 — robot has ricocheted but is NOT aligned with the target
      (needs ≥ 1 slide to align + ≥ 1 slide to reach → at least 2 more)
  2 — robot has NOT ricocheted yet (at least 2 more moves required)
Why H2 is admissible
--------------------
A robot can only stop *on* a target cell by sliding along the same row or
column.  Therefore, if the robot is not aligned (same row or col) with the
target, it necessarily needs ≥ 2 more slides: one to get into alignment and
one to reach the target.  This makes h = 2 a valid lower bound.

Why H2 is stronger than H1
---------------------------
H1 returns h = 1 whenever the robot has ricocheted (regardless of alignment).
H2 also returns h = 1 only when the robot is aligned; it returns h = 2 when
the robot is ricocheted but off-axis with the target.  Because H2 ≥ H1
everywhere, A*2 prunes more branches and typically expands fewer nodes than
A*1 — while still guaranteeing an optimal solution.

Interface
---------
SolverAStarH2(game).solve(initial_state, target, active) -> Solution

Parameters
----------
game          : Game  — provides board.slide() and shared helpers
initial_state : Robots — starting robot positions
target        : tuple  — (row, col, color, symbol) target descriptor
active        : str    — color of the robot that must reach the target

Returns
-------
list[(color, direction)] describing each move, or None if unsolvable
within *max_moves* steps.
"""

from __future__ import annotations

import heapq

from board import Robots, COLORS, DIR_LIST, _copy_robots, _skey, CFG
from game import Game, Move, Solution, _reached, _heuristic_aligned, _ricocheted


class SolverAStarH2:
    """
    A*2 — A* search with the alignment-aware heuristic (H2).

    Explores nodes in order of f = g + h, where:
      g = moves made so far
      h = H2 (0/1/2 based on ricochet status *and* whether the active robot
               is aligned with the target on the same row or column)

    H2 is strictly stronger than H1 in states where the robot has already
    ricocheted but is not yet on the same row or column as the target.
    This lets A*2 prune more of the search tree than A*1, while still
    guaranteeing an optimal (minimum-move) solution.
    """

    name  = "A*2"
    color = "#1ABC9C"   # teal — visually distinct from A*1's blue

    def __init__(self, game: Game) -> None:
        self.game = game

    def solve(self, initial_state: Robots, target: tuple, active: str,
              max_moves: int = CFG.SOLVER_MAX_MOVES) -> Solution:
        """
        Find the optimal path from *initial_state* to the goal using A*2 (H2).

        Returns the move list, or None if no solution exists within
        *max_moves* steps.
        """
        tpos    = (target[0], target[1])
        rh0     = False
        h0      = _heuristic_aligned(initial_state, active, tpos, rh0)
        ctr     = 0
        heap: list = [(h0, 0, ctr, initial_state, [], rh0)]
        visited: set[tuple] = set()

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
                    npos = self.game.board.slide(cur, col, d)
                    if npos == cur[col]:
                        continue
                    nc      = _copy_robots(cur)
                    nc[col] = npos
                    nh      = hist + [(col, d)]
                    ng      = g + 1
                    new_rh  = rh or _ricocheted(nh, active)
                    if _reached(nc, active, tpos, nh):
                        return nh
                    nskey = (_skey(nc), new_rh)
                    if nskey in visited:
                        continue
                    h = _heuristic_aligned(nc, active, tpos, new_rh)
                    ctr += 1
                    heapq.heappush(heap, (ng + h, ng, ctr, nc, nh, new_rh))
        return None
