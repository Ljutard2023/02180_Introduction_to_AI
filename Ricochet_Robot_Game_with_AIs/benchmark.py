"""
Ricochet Robots – Benchmark Window
====================================
Runs all AI solvers on a set of randomly generated board states and reports:
  • Average solution length (moves) per solver
  • Average time (seconds) per solver
  • Number of scenarios where a solution was found

The benchmark runs in a background thread and shows a progress bar so that
the main GUI stays responsive.  It is designed to finish quickly (≤ ~30 s
for the default 20 scenarios, due to per-solve timeouts).
"""

from __future__ import annotations

import random
import time
import threading
import tkinter as tk
from tkinter import ttk

from board import Board, CFG, COLORS, CENTER, _copy_robots
from game import Game
from solvers.bfs_solver    import SolverBFS
from solvers.dfs_solver    import SolverDFS
from solvers.astar_solver  import SolverAStar
from solvers.astar_solver2 import SolverAStarH2


# Solvers to benchmark (name → class)
BENCH_SOLVERS: dict[str, type] = {
    'BFS':  SolverBFS,
    'DFS':  SolverDFS,
    'A*1':  SolverAStar,
    'A*2':  SolverAStarH2,
}

# How many random (board-state, target) scenarios to test
NUM_SCENARIOS = 20

# Maximum depth passed to each solver during benchmarking (keeps it snappy)
BENCH_MAX_MOVES = 8


def _random_robots(board: Board) -> dict[str, tuple[int, int]]:
    """Generate a random, valid robot placement (not in CENTER, not on targets)."""
    forbidden = set(CENTER) | {(t[0], t[1]) for t in board.targets}
    robots: dict[str, tuple[int, int]] = {}
    for col in COLORS:
        while True:
            r = random.randint(0, CFG.N - 1)
            c = random.randint(0, CFG.N - 1)
            if (r, c) not in forbidden and (r, c) not in robots.values():
                robots[col] = (r, c)
                forbidden.add((r, c))
                break
    return robots


class BenchmarkWindow(tk.Toplevel):
    """
    Standalone benchmark window.  Press **Start** to kick off the test.
    A progress bar tracks the scenarios as they run in a background thread.
    Results are shown in a table and a summary bar chart when done.
    """

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.title("AI Benchmark – Ricochet Robots")
        self.resizable(False, False)
        self.configure(bg='#1A252F')
        self._running = False
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        pad = dict(padx=14, pady=6)

        # Title
        tk.Label(self, text="AI Solver Benchmark",
                 font=('Helvetica', 14, 'bold'),
                 fg='white', bg='#1A252F').pack(pady=(12, 2))
        tk.Label(self,
                 text=f"Runs each solver on {NUM_SCENARIOS} random scenarios  "
                      f"(max {BENCH_MAX_MOVES} moves / solve)",
                 font=('Helvetica', 9), fg='#BDC3C7', bg='#1A252F').pack()

        # Progress bar
        pf = tk.Frame(self, bg='#1A252F')
        pf.pack(fill=tk.X, **pad)
        self._progress_var = tk.IntVar(value=0)
        self._progress = ttk.Progressbar(
            pf, variable=self._progress_var,
            maximum=NUM_SCENARIOS * len(BENCH_SOLVERS),
            length=480, mode='determinate')
        self._progress.pack(fill=tk.X)
        self._progress_lbl = tk.Label(
            pf, text="Press Start to begin.", font=('Helvetica', 8),
            fg='#BDC3C7', bg='#1A252F', anchor='w')
        self._progress_lbl.pack(fill=tk.X, pady=(2, 0))

        # Results table
        tf = tk.Frame(self, bg='#2C3E50', padx=8, pady=8)
        tf.pack(fill=tk.X, padx=14, pady=4)
        headers = ['Solver', 'Scenarios', 'Avg Moves', 'Avg Time (s)', 'Found']
        widths  = [8,        10,          10,           13,             6]
        for ci, (h, w) in enumerate(zip(headers, widths)):
            tk.Label(tf, text=h,
                     font=('Helvetica', 9, 'bold'),
                     fg='#F39C12', bg='#2C3E50',
                     width=w, anchor='w').grid(row=0, column=ci, padx=3, pady=2)

        self._row_labels: dict[str, tuple[tk.Label, ...]] = {}
        for i, (name, cls) in enumerate(BENCH_SOLVERS.items()):
            col_hex = cls.color
            row = i + 1
            name_lbl = tk.Label(tf, text=name,
                                 font=('Helvetica', 9, 'bold'),
                                 fg=col_hex, bg='#2C3E50', width=8, anchor='w')
            name_lbl.grid(row=row, column=0, padx=3, pady=1)
            lbls = []
            for ci in range(1, len(headers)):
                w = widths[ci]
                l = tk.Label(tf, text='—',
                             font=('Helvetica', 9),
                             fg='#ECF0F1', bg='#2C3E50', width=w, anchor='w')
                l.grid(row=row, column=ci, padx=3, pady=1)
                lbls.append(l)
            self._row_labels[name] = tuple(lbls)

        # Bar chart canvas
        self._chart_cv = tk.Canvas(self, width=500, height=80,
                                   bg='#1B2631', highlightthickness=0)
        self._chart_cv.pack(padx=14, pady=(4, 2))

        # Start / Close buttons
        bf = tk.Frame(self, bg='#1A252F')
        bf.pack(pady=(4, 12))
        self._btn_start = tk.Button(
            bf, text="▶  Start Benchmark",
            command=self._start,
            bg='#27AE60', fg='white',
            font=('Helvetica', 10, 'bold'), width=20)
        self._btn_start.pack(side=tk.LEFT, padx=6)
        tk.Button(bf, text="Close", command=self.destroy,
                  bg='#566573', fg='white',
                  font=('Helvetica', 10), width=10).pack(side=tk.LEFT, padx=6)

    # ── Benchmark logic ───────────────────────────────────────────────────────

    def _start(self) -> None:
        if self._running:
            return
        self._running = True
        self._btn_start.config(state=tk.DISABLED)
        # Reset table
        for lbls in self._row_labels.values():
            for l in lbls:
                l.config(text='—')
        self._progress_var.set(0)
        self._progress_lbl.config(text="Running…")
        threading.Thread(target=self._run_benchmark, daemon=True).start()

    def _run_benchmark(self) -> None:
        board = Board()
        game  = Game(board)
        targets = board.targets           # list of (r, c, color, sym)
        total = NUM_SCENARIOS * len(BENCH_SOLVERS)
        done  = 0

        # Accumulate: name → list of (moves, time) for solved scenarios
        results: dict[str, list[tuple[int, float]]] = {n: [] for n in BENCH_SOLVERS}

        for scenario_idx in range(NUM_SCENARIOS):
            # Pick a random target and robot placement
            target = random.choice(targets)
            tcolor = target[2]
            active = tcolor if tcolor in COLORS else COLORS[0]
            robots = _random_robots(board)

            for name, cls in BENCH_SOLVERS.items():
                solver = cls(game)
                t0 = time.perf_counter()
                try:
                    sol = solver.solve(
                        _copy_robots(robots), target, active,
                        max_moves=BENCH_MAX_MOVES)
                except Exception as exc:
                    print(f"[benchmark] {name} scenario {scenario_idx}: {exc}")
                    sol = None
                dt = time.perf_counter() - t0

                if sol is not None:
                    results[name].append((len(sol), dt))

                done += 1
                # Schedule progress update on the GUI thread
                self.after(0, self._update_progress, done, total,
                           scenario_idx + 1)

        self.after(0, self._show_results, results)

    def _update_progress(self, done: int, total: int,
                         scenario: int) -> None:
        self._progress_var.set(done)
        self._progress_lbl.config(
            text=f"Scenario {scenario}/{NUM_SCENARIOS}  "
                 f"({done}/{total} solver calls done)")

    def _show_results(self, results: dict[str, list[tuple[int, float]]]) -> None:
        self._running = False
        self._btn_start.config(state=tk.NORMAL)
        self._progress_lbl.config(text="Done ✓")

        avg_moves_vals: list[float] = []
        for name, data in results.items():
            lbls = self._row_labels[name]
            n    = NUM_SCENARIOS
            found = len(data)
            if data:
                avg_m = sum(m for m, _ in data) / len(data)
                avg_t = sum(t for _, t in data) / len(data)
            else:
                avg_m = avg_t = 0.0
            avg_moves_vals.append(avg_m)
            lbls[0].config(text=str(n))
            lbls[1].config(text=f"{avg_m:.1f}" if data else "—")
            lbls[2].config(text=f"{avg_t:.3f}"  if data else "—")
            lbls[3].config(text=str(found))

        self._draw_chart(results, avg_moves_vals)

    def _draw_chart(self, results: dict[str, list[tuple[int, float]]],
                    avg_moves: list[float]) -> None:
        cv = self._chart_cv
        cv.delete('all')
        if not any(avg_moves):
            cv.create_text(250, 40, text="No solutions found",
                           fill='#E74C3C', font=('Helvetica', 9))
            return

        max_v = max(avg_moves) or 1
        W, H  = 500, 80
        pad_l, pad_r, pad_b, pad_t = 30, 10, 18, 8
        bar_w = (W - pad_l - pad_r) / len(BENCH_SOLVERS) - 4

        for i, (name, cls) in enumerate(BENCH_SOLVERS.items()):
            x0    = pad_l + i * (bar_w + 4)
            val   = avg_moves[i]
            bar_h = ((H - pad_t - pad_b) * val / max_v) if max_v else 0
            y1    = H - pad_b - bar_h
            y2    = H - pad_b
            col   = cls.color if val else '#566573'
            cv.create_rectangle(x0, y1, x0 + bar_w, y2, fill=col, outline='')
            if val:
                cv.create_text(x0 + bar_w / 2, y1 - 4,
                               text=f"{val:.1f}",
                               fill='white', font=('Helvetica', 7, 'bold'))
            cv.create_text(x0 + bar_w / 2, H - 6, text=name,
                           fill='#BDC3C7', font=('Helvetica', 7))
