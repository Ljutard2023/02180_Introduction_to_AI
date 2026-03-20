from __future__ import annotations
import heapq
from game import Game, Move, Solution, Robots, CFG


class SolverAStarH4:
    name  = "A*4"
    color = "#E67E22"   # orange

    def __init__(self, game: Game) -> None:
        self.game = game
        self.last_visited_nodes = 0

    def solve(self, initial_state: Robots, target: tuple, active: str,
              max_moves: int = CFG.SOLVER_MAX_MOVES) -> Solution:
        tpos = self.game.target_pos(target)
        h0   = self.game.heuristic_4(initial_state, active, tpos, [])
        ctr  = 0
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
                h = self.game.heuristic_4(nc, active, tpos, nh)
                ctr += 1
                heapq.heappush(heap, (ng + h, ng, ctr, nc, nh))
        return None