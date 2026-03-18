"""
Ricochet Robots – DFS Solver
==============================
Depth-First Search uses a stack to explore deep paths before backtracking.
A global visited set prevents revisiting equivalent states, keeping memory
usage manageable.

DFS is NOT guaranteed to find the shortest solution (unlike BFS or A*),
but it often finds a solution quickly on solvable puzzles and can serve
as a fast baseline.

Interface
---------
SolverDFS(game).solve(initial_state, target, active) -> Solution

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

from board import Robots, COLORS, DIR_LIST, _copy_robots, CFG
from game import Game, Move, Solution, _state_key, _reached


class SolverDFS:
    """
    Depth-First Search with a visited set and depth limit.

    Implemented iteratively (using an explicit stack) to avoid Python's
    recursion limit on deep puzzles.

    Not guaranteed to return the optimal solution; returns the first
    complete path found via depth-first traversal.
    """

    name  = "DFS"
    color = "#E67E22"

    def __init__(self, game: Game) -> None:
        self.game = game

    def solve(self, initial_state: Robots, target: tuple, active: str,
              max_moves: int = CFG.SOLVER_MAX_MOVES) -> Solution:
        """
        Search depth-first from *initial_state* for a solution where
        *active* robot reaches *target* after ricocheting.

        Returns the move list of the first solution found, or None if
        no solution exists within *max_moves* steps.
        """
        tpos     = (target[0], target[1])
        init_key = _state_key(initial_state, [], active)
        stack: list[tuple[Robots, list[Move]]] = [(initial_state, [])]
        vis:   set[tuple]                       = {init_key}

        while stack:
            cur, hist = stack.pop()
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
                        stack.append((nc, nh))
        return None
