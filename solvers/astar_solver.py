"""
Ricochet Robots – A* Solver
=============================
A* combines BFS's guarantee of optimality with a heuristic to focus the
search toward the goal, typically exploring fewer nodes than plain BFS.

Admissible heuristic h(state, rh):
  0 — active robot is already on the target and has ricocheted  (goal)
  1 — active robot has ricocheted but hasn't reached the target yet
  2 — active robot hasn't ricocheted yet

This heuristic never overestimates the remaining cost:
  - When rh is False, at least two more moves are always needed
    (one to ricochet, one to reach the target).
  - When rh is True, at least one more move is needed to reach the target
    (unless already there).
So h is admissible and A* returns an optimal solution.

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
    A* search with an admissible heuristic.

    Explores nodes in order of f = g + h, where:
      g = moves made so far
      h = admissible lower bound on remaining moves

    Guarantees an optimal (minimum-move) solution.
    """

    name  = "A*"
    color = "#3498DB"

    def __init__(self, game: Game) -> None:
        self.game = game

    def solve(self, initial_state: Robots, target: tuple, active: str,
              max_moves: int = CFG.SOLVER_MAX_MOVES) -> Solution:
        """
        Find the optimal path from *initial_state* to the goal using A*.

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
