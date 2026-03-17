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
    astar_solver.py      ← A* with admissible heuristic (optimal, fewer nodes)
```

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

Three algorithms run simultaneously in background threads:

| Algorithm | Guarantee        | Description                                      |
|-----------|------------------|--------------------------------------------------|
| **BFS**   | Optimal (fewest moves) | Breadth-first explores all k-move paths before k+1 |
| **DFS**   | Complete within depth limit (`SOLVER_MAX_MOVES=16`) | Depth-first with global visited set; not guaranteed to return the shortest solution, and may miss solutions requiring more than 16 moves |
| **A\***   | Optimal          | BFS-guided by an admissible heuristic; explores fewer nodes |

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

## Contributors
This project was carried out by a group of 4 students:
- s257473
- s253050
- s225786
- s253191

## License
This project is for academic purposes for the course 02180 Introduction to AI, Spring 26.

