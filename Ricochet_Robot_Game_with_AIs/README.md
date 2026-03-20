# 02180_Introduction_to_AI
## Ricochet Robots AI - DTU 02180
This repository contains the implementation of the board game Ricochet Robots and an AI-based solver developed as part of the 02180 Introduction to AI course at the Technical University of Denmark (DTU).

## Project Overview

The goal of this assignment is to implement a functional version of Ricochet Robots and design an AI capable of finding the shortest sequence of moves to reach a target.

- **Objective**: Move a specific coloured robot to a designated target square.
- **Movement**: Robots slide horizontally or vertically until they hit a wall or another robot; they cannot stop in the middle of a path.
- **Ricochet rule**: The active robot must change direction at least once before reaching the target.
- **Complexity**: Each collision-to-collision slide counts as one move.
- **Game type**: Deterministic, perfect information, single-agent puzzle.

---

## File / Module Structure

```
main.py                  ← entry point; graphical game UI + AI panel
board.py                 ← board model: dimensions, pieces, walls, slide()
game.py                  ← game rules: move generation, goal test, successors
solvers/
    __init__.py
    bfs_solver.py        ← Breadth-First Search  (optimal)
    dfs_solver.py        ← Depth-First Search    (fast, not necessarily optimal)
    astar_solver.py      ← A*1 (H1: alignment + ricochet)
    astar_solver2.py     ← A*2 (H2: normalized Manhattan + alignment)
    astar_solver3.py     ← A*3 (H3: Manhattan + alignment + ricochet)
    astar_solver4.py     ← skipped 
    astar_solver5.py     ← skipped   
    astar_solver6.py     ← A*6 (H6: Mini-BFS on relaxed problem)
```

---

## AI–Engine API Boundary (Assignment Compliance)

The project is structured so AI solvers interact with the game engine only through the **public API** of `Game`.
Solvers do **not** access board internals directly.

Public API used by solvers:

| API method (Game) | Purpose |
|-------------------|---------|
| `target_pos(target)` | Extract `(row, col)` from target descriptor |
| `get_successors(robots, history, active)` | Generate legal transitions `(move, next_state, next_history)` |
| `is_goal(robots, history, active, target_pos)` | Goal check including ricochet condition |
| `state_key(robots, history, active)` | Hashable visited-state key |
| `heuristic_1(...)` | H1 for A*1 (alignment + ricochet) |
| `heuristic_2(...)` | H2 for A*2 (normalized Manhattan + alignment) |
| `heuristic_3(...)` | H3 for A*3 (Manhattan + alignment + ricochet) |
| `heuristic_3(...)` | H6 for A*6 (Mini-BFS on relaxed problem)      |

This separation makes the AI code independent from rendering and low-level board implementation details, as required by the assignment.

---

## Dependencies

The game uses only the **Python standard library** — no third-party packages are required.

| Requirement | Version |
|-------------|---------|
| Python      | ≥ 3.10  |
| tkinter     | bundled with Python (standard) |

### Install Python (if needed)

```bash
# Ubuntu / Debian
sudo apt install python3 python3-tk

# macOS (Homebrew)
brew install python-tk

# Windows
# Download from https://www.python.org — tick "tcl/tk" during install
```

---

## How to Run

```bash
python main.py
```

This opens the graphical Ricochet Robots game.  
At startup you will be asked for the number of players and each player's name.

---

## Controls

| Key / Action          | Effect                                  |
|-----------------------|-----------------------------------------|
| Arrow keys            | Slide the selected robot                |
| Tab or R              | Cycle to the next robot                 |
| 1 – 4                 | Select robot by index (red/green/blue/yellow) |
| Z or U                | Undo last move                          |
| Enter                 | Confirm solution (checks win condition) |
| Escape                | Reset round to start positions          |
| **F5**                | **Open the AI Solver panel**            |
| Click a robot         | Select that robot                       |

---

## Using the AI Solvers

Press **F5** (or click **"Run All AIs"** in the side panel) to open the AI Solver window.

Five algorithms run sequentially in a background worker:

| Algorithm | Guarantee        | Description                                      |
|-----------|------------------|--------------------------------------------------|
| **BFS**   | Optimal (fewest moves) | Breadth-first explores all k-move paths before k+1 |
| **DFS**   | Complete within depth limit (`SOLVER_MAX_MOVES=16`) | Depth-first with global visited set; not guaranteed to return the shortest solution, and may miss solutions requiring more than 16 moves |
| **A\*1**  | Heuristic-guided | H1 = alignment + ricochet |
| **A\*2**  | Heuristic-guided | H2 = normalized Manhattan + alignment |
| **A\*3**  | Heuristic-guided | H3 = Manhattan + alignment + ricochet |
| **A\*6**  | Heuristic-guided | H6 = Mini-BFS on relaxed problem      |

### Viewing solutions

Once a solver finishes and finds a solution:

1. The **full move list** is shown immediately in the results table row (e.g. `1:RED→S  2:BLUE→W  3:RED→N  4:RED→E`).
2. Click **▶ Play** next to any algorithm to load its solution into the playback panel.
3. Use the controls to analyse the solution:

| Button      | Action                                          |
|-------------|-------------------------------------------------|
| **◀ Prev**  | Step one move backward                          |
| **Next ▶**  | Step one move forward                           |
| **⏩ Auto**  | Replay the full solution automatically          |
| **⟳ Reset** | Return to the round's start position            |
| **📋 Copy** | Copy the move list to the clipboard             |
| Speed slider | Adjust the auto-play interval (Fast ↔ Slow)   |

The main board updates in sync with each step so you can trace every state transition visually.

---

## Assignment-Focused AI Documentation

Detailed technical documentation for the AI design and assignment criteria is provided in:

- `AI_ASSIGNMENT_DOCUMENTATION.md`

This includes:

- State/action/result/terminal/utility definitions.
- State-space estimate and implications for search.
- Solver design (BFS, DFS, A*1, A*2, A*3, A*6).
- Heuristic definitions and admissibility rationale.
- Tunable parameters and benchmark methodology (moves/time/visited nodes).
- Explicit API-separation argument.
- Future-work discussion.

---

## Contributors
This project was carried out by a group of 4 students:
- s257473
- s253050
- s225786
- s253191

## License
This project is for academic purposes for the course 02180 Introduction to AI, Spring 26.

