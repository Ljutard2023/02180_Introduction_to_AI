"""
Ricochet Robots – A*1 Solver
==============================
A*1 uses heuristic H1 = alignment + ricochet (discrete 0/1/2 scale).

H1 values:
    0 — active robot is on target and ricochet requirement is satisfied
    1 — active robot has ricocheted and is aligned with target
    2 — otherwise

See astar_solver2.py for A*2 (normalized Manhattan + alignment) and
astar_solver3.py for A*3 (Manhattan + alignment + ricochet).

Interface
---------
SolverAStar(game).solve(initial_state, target, active) -> Solution

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

import heapq

from game import Game, Move, Solution, Robots, CFG


class SolverAStar:
    """
    A*1 — A* search with H1 (alignment + ricochet).

    Explores nodes in order of f = g + h, where:
      g = moves made so far
    h = H1 (0/1/2 based on alignment and ricochet)

    Returns a minimum-f score solution under the configured heuristic.
    """

    name  = "A*1"
    color = "#3498DB"

    def __init__(self, game: Game) -> None:
        self.game = game
        self.last_visited_nodes = 0

    def solve(self, initial_state: Robots, target: tuple, active: str,
              max_moves: int = CFG.SOLVER_MAX_MOVES) -> Solution:
        """
        Find the optimal path from *initial_state* to the goal using A*1 (H1).

        Returns the move list, or None if no solution exists within
        *max_moves* steps.
        """
        tpos    = self.game.target_pos(target)
        h0      = self.game.heuristic_1(initial_state, active, tpos, [])
        ctr     = 0
        heap: list = [(h0, 0, ctr, initial_state, [])]
        visited: set[tuple] = set()
        self.last_visited_nodes = 0

        while heap:
            _, g, _, cur, hist = heapq.heappop(heap)
            if g >= max_moves:
                continue
            skey = self.game.state_key(cur, hist, active)
            if skey in visited:
                continue
            visited.add(skey)
            self.last_visited_nodes += 1

            for _, nc, nh in self.game.get_successors(cur, hist, active):
                ng = g + 1
                if self.game.is_goal(nc, nh, active, tpos):
                    return nh
                nskey = self.game.state_key(nc, nh, active)
                if nskey in visited:
                    continue
                h = self.game.heuristic_1(nc, active, tpos, nh)
                ctr += 1
                heapq.heappush(heap, (ng + h, ng, ctr, nc, nh))
        return None
