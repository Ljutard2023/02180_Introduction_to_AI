"""
Ricochet Robots – BFS Solver
==============================
Breadth-First Search explores states level by level (by number of moves),
so the first solution found is guaranteed to be optimal (minimum moves).

Interface
---------
SolverBFS(game).solve(initial_state, target, active) -> Solution

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

from collections import deque

from board import Robots, COLORS, DIR_LIST, _copy_robots, CFG
from game import Game, Move, Solution, _state_key, _reached


class SolverBFS:
    """
    Breadth-First Search — guarantees an optimal (minimum-move) solution.

    Explores all states reachable in k moves before exploring states
    reachable in k+1 moves, so the first complete path found is shortest.
    """

    name  = "BFS"
    color = "#2ECC71"

    def __init__(self, game: Game) -> None:
        self.game = game

    def solve(self, initial_state: Robots, target: tuple, active: str,
              max_moves: int = CFG.SOLVER_MAX_MOVES) -> Solution:
        """
        Find the shortest path from *initial_state* to the goal.

        The goal is reached when *active* robot is on *target* and has
        changed direction at least once (ricochet requirement).

        Returns the move list, or None if no solution exists within
        *max_moves* steps.
        """
        tpos     = (target[0], target[1])
        init_key = _state_key(initial_state, [], active)
        q:   deque[tuple[Robots, list[Move]]] = deque([(initial_state, [])])
        vis: set[tuple]                        = {init_key}

        while q:
            cur, hist = q.popleft()
            if len(hist) >= max_moves:
                continue
            for col in COLORS:
                for d in DIR_LIST:
                    npos = self.game.board.slide(cur, col, d)
                    if npos == cur[col]:
                        continue
                    nc = _copy_robots(cur)
                    nc[col] = npos
                    nh = hist + [(col, d)]
                    if _reached(nc, active, tpos, nh):
                        return nh
                    key = _state_key(nc, nh, active)
                    if key not in vis:
                        vis.add(key)
                        q.append((nc, nh))
        return None
