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
game          : Game  — provides the public engine API used by the solver
initial_state : Robots — starting robot positions
target        : tuple  — (row, col, color, symbol) target descriptor
active        : str    — color of the robot that must reach the target

Returns
-------
list[(color, direction)] describing each move, or None if unsolvable
within *max_moves* steps.
"""

from __future__ import annotations

from game import Game, Move, Solution, Robots, CFG


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
        self.last_visited_nodes = 0

    def solve(self, initial_state: Robots, target: tuple, active: str,
              max_moves: int = CFG.SOLVER_MAX_MOVES) -> Solution:
        """
        Search depth-first from *initial_state* for a solution where
        *active* robot reaches *target* after ricocheting.

        Returns the move list of the first solution found, or None if
        no solution exists within *max_moves* steps.
        """
        tpos     = self.game.target_pos(target)
        init_key = self.game.state_key(initial_state, [], active)
        stack: list[tuple[Robots, list[Move]]] = [(initial_state, [])]
        vis:   set[tuple]                       = {init_key}
        self.last_visited_nodes = 0

        while stack:
            cur, hist = stack.pop()
            self.last_visited_nodes += 1
            if len(hist) >= max_moves:
                continue
            for _, nc, nh in self.game.get_successors(cur, hist, active):
                if self.game.is_goal(nc, nh, active, tpos):
                    return nh
                key = self.game.state_key(nc, nh, active)
                if key not in vis:
                    vis.add(key)
                    stack.append((nc, nh))
        return None
