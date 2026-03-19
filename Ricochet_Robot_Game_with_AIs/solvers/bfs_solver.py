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

from collections import deque

from game import Game, Move, Solution, Robots, CFG


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
        self.last_visited_nodes = 0

    def solve(self, initial_state: Robots, target: tuple, active: str,
              max_moves: int = CFG.SOLVER_MAX_MOVES) -> Solution:
        """
        Find the shortest path from *initial_state* to the goal.

        The goal is reached when *active* robot is on *target* and has
        changed direction at least once (ricochet requirement).

        Returns the move list, or None if no solution exists within
        *max_moves* steps.
        """
        tpos     = self.game.target_pos(target)
        init_key = self.game.state_key(initial_state, [], active)
        q:   deque[tuple[Robots, list[Move]]] = deque([(initial_state, [])])
        vis: set[tuple]                        = {init_key}
        self.last_visited_nodes = 0

        while q:
            cur, hist = q.popleft()
            self.last_visited_nodes += 1
            if len(hist) >= max_moves:
                continue
            for _, nc, nh in self.game.get_successors(cur, hist, active):
                if self.game.is_goal(nc, nh, active, tpos):
                    return nh
                key = self.game.state_key(nc, nh, active)
                if key not in vis:
                    vis.add(key)
                    q.append((nc, nh))
        return None
