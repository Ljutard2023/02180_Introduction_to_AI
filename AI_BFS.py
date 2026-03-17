from collections import deque

class AI_BFS:

    def starting_state(self, board:Board):
        self.board = board
    
    def solve(self, robots: Robots, target: tuple, active: str, max_moves: 15):
        tpos = target(target[0], target[1])
        init = _state_key(robots, [], active)
        q: deque[tuple[Robot, list[Move]]] = deque([(robots, [])])
        visited: set[tuple] = {init}

        while q:
            cur, hist = q.popleft()
            if len(hist) > max_moves:
                continue
            for col in COLORS:
                for d in DIR_LIST:
                    npos = self.board.slide(cur, col, d)
                    if npos == cur[col]:
                        continue
                    nc =  _copy_robots(cur)
                    nc[col] = npos
                    nh = hist + [(col, d)]
                    if _reached(cur, active, tpos, nh):
                        return nh
                    key = _state_key(nc, nh, active)
                    if key not in visited:
                        visited.add(key)
                        q.append((nc, nh))
        return None
    
