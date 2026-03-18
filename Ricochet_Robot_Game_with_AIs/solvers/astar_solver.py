"""
Ricochet Robots – A*1 Solver
==============================
A* with the phase heuristic (H1) combines BFS's optimality guarantee with a
heuristic to focus the search toward the goal.

Admissible heuristic H1 (phase heuristic):
  0 — active robot is already on the target and has ricocheted  (goal)
  1 — active robot has ricocheted but hasn't reached the target yet
  2 — active robot hasn't ricocheted yet

This heuristic never overestimates the remaining cost:
  - When rh is False, at least two more moves are always needed.
  - When rh is True, at least one more move is needed to reach the target.
So H1 is admissible and A*1 returns an optimal solution.

For a stronger variant see astar_solver2.py (A*2 / alignment heuristic H2).

Interface
---------
SolverAStar(game).solve(initial_state, target, active) -> Solution

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
from game import Game, Move, Solution, _reached, _heuristic, _ricocheted


class SolverAStar:
    """
    A*1 — A* search with the phase heuristic (H1).

    Explores nodes in order of f = g + h, where:
      g = moves made so far
      h = H1 (0/1/2 based on whether the robot has ricocheted and/or
               reached the target)

    Guarantees an optimal (minimum-move) solution.
    See SolverAStarH2 for a stronger heuristic variant.
    """

    name  = "A*1"
    color = "#3498DB"

    def __init__(self, game: Game) -> None:
        self.game = game

    def solve(self, initial_state: Robots, target: tuple, active: str,
              max_moves: int = CFG.SOLVER_MAX_MOVES) -> Solution:
        """
        Find the optimal path from *initial_state* to the goal using A*1 (H1).

        Returns the move list, or None if no solution exists within
        *max_moves* steps.
        """
        tpos    = (target[0], target[1])
        rh0     = False
        h0      = _heuristic(initial_state, active, tpos, rh0)
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
                    h = _heuristic(nc, active, tpos, new_rh)
                    ctr += 1
                    heapq.heappush(heap, (ng + h, ng, ctr, nc, nh, new_rh))
        return None
