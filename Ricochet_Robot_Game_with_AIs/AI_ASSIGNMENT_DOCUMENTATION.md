# AI Assignment Documentation - Ricochet Robots

This document is written to support the AI section of the 02180 board game assignment.
It explains the AI design choices, API separation, and experimental setup in a clear and report-ready format.

## 1. Game Type and Implications

Ricochet Robots in this project is modeled as:

- Single-agent puzzle (the solver controls all moves).
- Deterministic (no randomness in transition dynamics once state and action are fixed).
- Perfect-information (full board state is always known).
- Turn-based and discrete.

Implication: classical state-space search methods are appropriate (BFS, DFS, A* variants).

## 2. State, Actions, Transition, Goal, Utility

### Initial state s0

A state is the tuple of all robot positions:

- red, green, blue, yellow -> each with coordinates (row, col).
- Board walls and target definitions are static and shared by all states.

### Players

For the AI part, we model the system as one decision-maker (single-agent planning).

### Actions(s)

An action is a pair (robot_color, direction), where direction is in {N, S, E, W}.
An action is legal if it changes robot position after sliding.

### Result(s, a)

Applying an action slides the selected robot in the chosen direction until blocked by:

- wall,
- another robot,
- center forbidden block.

The result is a new state with one updated robot position.

### Terminal-Test(s)

A state is goal/terminal when:

1. the active robot is on target cell, and
2. the active robot has changed direction at least once in the solution history (ricochet rule).

### Utility(s, p)

For search, path cost is number of moves. We minimize total moves.

## 3. State-Space Size (Order-of-Magnitude)

A rough upper bound ignoring constraints:

- 4 robots on 16x16 board = up to 256 choices per robot,
- no overlap implies roughly 256 * 255 * 254 * 253 > 4e9 placements,
- effective reachable space is smaller due to walls, center block, and move dynamics.

So the reachable state space is large (order of billions in naive count), which motivates informed search (A*).

## 4. AI-Engine Separation and API Contract

Assignment requirement: AI must be clearly separate from game engine internals.

In this project, all solvers use only the public methods exposed by `Game`:

- target_pos(target)
- get_successors(robots, history, active)
- is_goal(robots, history, active, target_pos)
- state_key(robots, history, active)
- heuristic_1(robots, active, target_pos, history)               # H1
- heuristic_2(robots, active, target_pos, history)               # H2
- heuristic_3(robots, active, target_pos, history)               # H3

Important: solver modules do not access low-level board internals directly for transition logic.

## 5. Implemented Search Algorithms

## BFS

- Expands nodes by depth (k-move frontier before k+1).
- Complete within depth bound.
- Optimal in move count when a solution is found within bound.

## DFS

- Stack-based deep exploration with visited set.
- Can find solutions quickly in some instances.
- Not guaranteed to return shortest solution.
- With depth cap, may miss deeper valid solutions.

## A*1 (Heuristic H1: Alignment + Ricochet)

Evaluation function:

f(n) = g(n) + h1(n)

where g(n) is moves so far.

H1 values:

- 0: on target and ricochet satisfied,
- 1: aligned with target and ricochet satisfied,
- 2: otherwise.

This heuristic captures alignment and ricochet status in a compact discrete score.

## A*2 (Heuristic H2: Normalized Manhattan + Alignment)

Evaluation function:

f(n) = g(n) + h2(n)

h2 is defined as:

- Manhattan(active, target) / 30
- plus an alignment penalty (0 if aligned on row/column, else 28/30).

So H2 keeps geometric distance information while still accounting for alignment.

## A*3 (Heuristic H3: Manhattan + Alignment + Ricochet)

h3 combines all three requested components:

- normalized Manhattan distance,
- alignment component,
- ricochet component.

This yields a richer guidance signal than using only one or two components.

Why stronger than H1:

- If not aligned, at least one move is needed to align and one to reach target, so lower bound 2 is valid.
- Therefore H2 >= H1 in all states and remains admissible.

Expected effect: A*2 and A*3 can prioritize different parts of the search space;
their performance is compared empirically in the benchmark.

## 6. Parameters and Benchmarking

Main adjustable parameters:

- `SOLVER_MAX_MOVES` (search depth cap in solving).
- benchmark scenario count (`NUM_SCENARIOS`).
- benchmark depth cap (`BENCH_MAX_MOVES`).

Benchmark script/window compares:

- average move count of found solutions,
- average solver time,
- average visited nodes,
- number of solved scenarios.

This supports empirical comparison among BFS, DFS, A*1, A*2, and A*3.

## 7. Practical Notes on Optimality and Limits

- BFS is optimal in move count under the configured depth bound.
- DFS is not optimal by design.
- Any depth cap can prevent finding existing deeper solutions.

## 8. Future Improvements

Possible next steps:

- Add transposition tables with richer dominance checks.
- Add bidirectional or reverse search variants.
- Add stronger admissible heuristics using wall/stop-point abstractions.
- Add full offline benchmark scripts with CSV export and confidence intervals.
- Extend report with human-vs-AI performance experiments.

## 9. Mapping to Assignment Report Questions

This project directly covers:

1. Game rules (with explicit ricochet condition).
2. Game type analysis (deterministic, perfect-information, single-agent puzzle model).
3. State-space magnitude estimate.
4. s0 / Actions / Result / Terminal-Test / Utility definitions.
5. State and move representation in data structures.
6. Algorithm choice rationale (BFS, DFS, A* variants).
7. Heuristic design and admissibility arguments.
8. Parameters and benchmarking methodology.
9. Future work proposals.

For submission, convert this material into the required 4-6 page PDF report and include group declaration as separate PDF.
