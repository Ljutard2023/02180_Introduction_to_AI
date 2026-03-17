#!/usr/bin/env python3
"""
Ricochet Robots – Main Application
====================================
Entry point that wires together the board/pieces model (board.py),
game logic (game.py), and AI solvers (solvers/) into a graphical game.

Controls
--------
  Arrow keys         — move the selected robot
  Tab / R            — cycle to the next robot
  1-4                — select robot by index
  Z / U              — undo last move
  Enter              — confirm solution
  Escape             — reset round to start positions
  F5                 — open the AI Solver panel
  Click a robot      — select that robot

AI Solver panel
---------------
  Opens with F5 or the "Run All AIs" button.
  BFS, DFS, and A* run in background threads.
  When a solution is found:
    • The full move list is shown immediately.
    • Use ◀ Prev / Next ▶ to step through moves one at a time.
    • Use ⏩ Auto to replay the full solution automatically.
    • Use ⟳ Reset to return to the start position.
    • Use 📋 Copy to copy the move list to the clipboard.
"""

from __future__ import annotations

import math
import time
import threading
import random
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from board import (
    Board, CFG, Robots,
    COLORS, DIR_LIST, CENTER, HEX,
    _copy_robots,
)
from game import Game, Move, Solution, _ricocheted
from solvers.bfs_solver   import SolverBFS
from solvers.dfs_solver   import SolverDFS
from solvers.astar_solver import SolverAStar


# ── Solver registry (only BFS, DFS, A*) ───────────────────────────────────────

SOLVERS: dict[str, type] = {
    'BFS': SolverBFS,
    'DFS': SolverDFS,
    'A*':  SolverAStar,
}


# ─────────────────────────────────────────────────────────────────────────────
#  AI RESULTS WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class AIWindow(tk.Toplevel):
    """
    Secondary window that runs BFS, DFS, and A* in background threads and
    displays:
      • A comparison table (moves, time, status) for each algorithm.
      • A bar chart comparing solution lengths.
      • A full move-list text for the selected algorithm's solution.
      • Step-by-step playback controls (Prev / Next / Auto / Reset / Copy).

    The main board reflects the current playback step so the user can
    visually trace each state transition.
    """

    def __init__(self, parent_app: 'App', robots_start: Robots,
                 target: tuple, active: str) -> None:
        super().__init__(parent_app.root)
        self.app          = parent_app
        self.robots_start = robots_start
        self.target       = target
        self.active       = active

        self.title("AI Solver – Ricochet Robots")
        self.resizable(True, False)
        self.minsize(540, 0)
        self.configure(bg='#1A252F')

        self.solutions: dict[str, Solution] = {}
        self.times:     dict[str, float]    = {}

        self._pb_moves:  list[Move] = []
        self._pb_step:   int        = 0
        self._pb_timer:  str | None = None
        self._pb_solver: str        = ''
        self._auto_ms_var = tk.IntVar(value=CFG.AUTO_PLAY_MS)

        self._build_ui()
        self._run_all_solvers()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        tk.Label(self, text="AI SOLVER RESULTS",
                 font=('Helvetica', 14, 'bold'),
                 fg='white', bg='#1A252F').pack(pady=(12, 2))
        tgt = self.target
        tk.Label(self,
                 text=(f"Target: {tgt[2].upper()}  {tgt[3].upper()}"
                       f"  @ row {tgt[0]}, col {tgt[1]}"),
                 font=('Helvetica', 9), fg='#BDC3C7', bg='#1A252F').pack()

        self._build_table()
        self._build_chart()
        self._build_playback()

    def _build_table(self) -> None:
        tf = tk.Frame(self, bg='#2C3E50', padx=8, pady=8)
        tf.pack(padx=14, pady=(10, 4), fill=tk.X)

        headers = ['Algorithm', 'Moves', 'Time (s)', 'Status', '  ', 'Playback']
        widths  = [12, 6, 9, 10, 4, 10]
        for ci, (h, w) in enumerate(zip(headers, widths)):
            tk.Label(tf, text=h, font=('Helvetica', 9, 'bold'),
                     fg='#F39C12', bg='#2C3E50', width=w, anchor='w'
                     ).grid(row=0, column=ci, padx=3, pady=2)

        self._row_widgets: dict[str, tuple] = {}
        for i, name in enumerate(SOLVERS):
            cls   = SOLVERS[name]
            c_hex = cls.color
            row   = i + 1
            tk.Label(tf, text=name, font=('Helvetica', 9, 'bold'),
                     fg=c_hex, bg='#2C3E50', width=widths[0], anchor='w'
                     ).grid(row=row, column=0, padx=3)

            mv = tk.Label(tf, text="…", font=('Helvetica', 9),
                          fg='white', bg='#2C3E50',
                          width=widths[1], anchor='center')
            mv.grid(row=row, column=1, padx=3)

            tm = tk.Label(tf, text="…", font=('Helvetica', 9),
                          fg='white', bg='#2C3E50',
                          width=widths[2], anchor='center')
            tm.grid(row=row, column=2, padx=3)

            st = tk.Label(tf, text="running", font=('Helvetica', 9),
                          fg='#BDC3C7', bg='#2C3E50',
                          width=widths[3], anchor='center')
            st.grid(row=row, column=3, padx=3)

            pb_spin = ttk.Progressbar(tf, mode='indeterminate', length=30)
            pb_spin.grid(row=row, column=4, padx=2)
            pb_spin.start(10)

            pb_btn = tk.Button(
                tf, text="▶ Play", font=('Helvetica', 8, 'bold'),
                bg='#566573', fg='white', width=8,
                state=tk.DISABLED,
                command=lambda n=name: self._start_playback(n))
            pb_btn.grid(row=row, column=5, padx=3, pady=2)

            self._row_widgets[name] = (mv, tm, st, pb_spin, pb_btn)

    def _build_chart(self) -> None:
        self._chart_frame = tk.Frame(self, bg='#1A252F')
        self._chart_frame.pack(padx=14, pady=4, fill=tk.X)
        tk.Label(self._chart_frame, text="SOLUTION COMPARISON",
                 font=('Helvetica', 8, 'bold'), fg='#BDC3C7', bg='#1A252F'
                 ).pack(anchor='w')
        self._chart_cv = tk.Canvas(self._chart_frame,
                                   width=480, height=70,
                                   bg='#2C3E50', highlightthickness=0)
        self._chart_cv.pack(fill=tk.X)
        self._chart_cv.create_text(240, 35, text="Waiting for results…",
                                   fill='#566573', font=('Helvetica', 8))

    def _build_playback(self) -> None:
        tk.Frame(self, height=1, bg='#34495E').pack(fill=tk.X, padx=14)

        tk.Label(self, text="PLAYBACK",
                 font=('Helvetica', 11, 'bold'),
                 fg='#9B59B6', bg='#1A252F').pack(pady=(10, 2))

        # Step label
        self._lbl_pb = tk.Label(
            self, text="Select an algorithm above to play",
            font=('Helvetica', 9), fg='#BDC3C7', bg='#1A252F')
        self._lbl_pb.pack()

        # Full solution text (shown once a solver is selected)
        self._lbl_full = tk.Label(
            self, text="",
            font=('Helvetica', 8), fg='#95A5A6', bg='#1A252F',
            justify=tk.LEFT, wraplength=500)
        self._lbl_full.pack(padx=14, pady=(0, 6))

        # Control buttons
        ctrl = tk.Frame(self, bg='#1A252F')
        ctrl.pack(pady=4)

        def _btn(text: str, cmd, bg: str, w: int = 8) -> tk.Button:
            return tk.Button(ctrl, text=text, width=w, command=cmd,
                             bg=bg, fg='white',
                             font=('Helvetica', 9, 'bold'),
                             state=tk.DISABLED)

        self._btn_prev   = _btn("◀ Prev",  self._pb_prev,   '#2980B9')
        self._btn_next   = _btn("Next ▶",  self._pb_next,   '#2980B9')
        self._btn_auto   = _btn("⏩ Auto",  self._pb_auto,   '#27AE60')
        self._btn_reset  = _btn("⟳ Reset", self._pb_reset,  '#7F8C8D')
        self._btn_export = _btn("📋 Copy",  self._pb_export, '#2C3E50', w=7)
        for b in (self._btn_prev, self._btn_next, self._btn_auto,
                  self._btn_reset, self._btn_export):
            b.pack(side=tk.LEFT, padx=3)

        # Auto-play speed slider
        speed_row = tk.Frame(self, bg='#1A252F')
        speed_row.pack(pady=(4, 10))
        tk.Label(speed_row, text="Auto speed:",
                 font=('Helvetica', 8), fg='#BDC3C7',
                 bg='#1A252F').pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(speed_row, text="Fast", font=('Helvetica', 8),
                 fg='#95A5A6', bg='#1A252F').pack(side=tk.LEFT)
        ttk.Scale(speed_row, from_=200, to=1500, orient='horizontal',
                  length=160, variable=self._auto_ms_var
                  ).pack(side=tk.LEFT, padx=4)
        tk.Label(speed_row, text="Slow", font=('Helvetica', 8),
                 fg='#95A5A6', bg='#1A252F').pack(side=tk.LEFT)

    # ── Solver execution ──────────────────────────────────────────────────────

    def _run_all_solvers(self) -> None:
        """Launch BFS, DFS, and A* each in a daemon background thread."""
        for name, cls in SOLVERS.items():
            threading.Thread(target=self._run_one,
                             args=(name, cls), daemon=True).start()

    def _run_one(self, name: str, cls: type) -> None:
        game   = self.app.game
        tcolor = self.target[2]
        snap   = _copy_robots(self.robots_start)
        solver = cls(game)

        t0 = time.perf_counter()
        if tcolor == 'all':
            best: Solution = None
            for col in COLORS:
                s = solver.solve(snap, self.target, col)
                if s and (best is None or len(s) < len(best)):
                    best = s
            sol = best
        else:
            sol = solver.solve(snap, self.target, tcolor)
        dt = time.perf_counter() - t0

        self.solutions[name] = sol
        self.times[name]     = dt
        self.after(0, self._update_row, name, sol, dt)

    def _update_row(self, name: str, sol: Solution, dt: float) -> None:
        mv, tm, st, pb_spin, pb_btn = self._row_widgets[name]
        mv.config(text=str(len(sol)) if sol else '—')
        tm.config(text=f"{dt:.3f}")
        if sol:
            st.config(text='✓ found', fg='#2ECC71')
            pb_btn.config(state=tk.NORMAL, bg=SOLVERS[name].color)
        else:
            st.config(text='✗ none', fg='#E74C3C')
        pb_spin.stop()
        pb_spin.config(mode='determinate', value=100 if sol else 0)

        if len(self.solutions) == len(SOLVERS):
            self.after(50, self._draw_chart)

    def _draw_chart(self) -> None:
        cv = self._chart_cv
        cv.delete('all')
        results = [(n, self.solutions.get(n)) for n in SOLVERS]
        vals    = [len(s) for _, s in results if s]
        if not vals:
            cv.create_text(240, 35, text="No solutions found",
                           fill='#E74C3C', font=('Helvetica', 8))
            return
        max_v = max(vals)
        W, H  = 480, 70
        pad_l, pad_r, pad_b, pad_t = 30, 10, 18, 8
        bar_w = (W - pad_l - pad_r) / len(SOLVERS) - 4

        for i, (name, sol) in enumerate(results):
            x0    = pad_l + i * (bar_w + 4)
            val   = len(sol) if sol else 0
            bar_h = ((H - pad_t - pad_b) * val / max_v) if max_v else 0
            y1    = H - pad_b - bar_h
            y2    = H - pad_b
            col   = SOLVERS[name].color if sol else '#566573'
            cv.create_rectangle(x0, y1, x0 + bar_w, y2, fill=col, outline='')
            if val:
                cv.create_text(x0 + bar_w / 2, y1 - 4, text=str(val),
                               fill='white', font=('Helvetica', 7, 'bold'))
            cv.create_text(x0 + bar_w / 2, H - 6, text=name,
                           fill='#BDC3C7', font=('Helvetica', 7))

    # ── Playback ──────────────────────────────────────────────────────────────

    def _start_playback(self, name: str) -> None:
        sol = self.solutions.get(name)
        if not sol:
            return
        self._cancel_auto()
        self._pb_moves  = list(sol)
        self._pb_step   = 0
        self._pb_solver = name
        for b in (self._btn_prev, self._btn_next, self._btn_auto,
                  self._btn_reset, self._btn_export):
            b.config(state=tk.NORMAL)
        self._show_full_solution()
        self._pb_reset()

    def _show_full_solution(self) -> None:
        """Display the complete move list as text above the controls."""
        if not self._pb_moves:
            self._lbl_full.config(text="")
            return
        n = self._pb_solver
        steps = "  ".join(
            f"{i + 1}:{col.upper()}{d}"
            for i, (col, d) in enumerate(self._pb_moves)
        )
        self._lbl_full.config(
            text=f"[{n}] Full solution ({len(self._pb_moves)} moves): {steps}")

    def _pb_reset(self) -> None:
        self._cancel_auto()
        self._pb_step = 0
        self.app.playback_apply(self.robots_start, self._pb_moves, 0)
        self._update_pb_label()

    def _pb_next(self) -> None:
        if self._pb_step < len(self._pb_moves):
            self._pb_step += 1
        self.app.playback_apply(self.robots_start, self._pb_moves, self._pb_step)
        self._update_pb_label()

    def _pb_prev(self) -> None:
        if self._pb_step > 0:
            self._pb_step -= 1
        self.app.playback_apply(self.robots_start, self._pb_moves, self._pb_step)
        self._update_pb_label()

    def _pb_auto(self) -> None:
        self._pb_reset()
        self._auto_tick()

    def _auto_tick(self) -> None:
        if self._pb_step < len(self._pb_moves):
            self._pb_next()
            self._pb_timer = self.after(self._auto_ms_var.get(), self._auto_tick)

    def _cancel_auto(self) -> None:
        if self._pb_timer:
            self.after_cancel(self._pb_timer)
            self._pb_timer = None

    def _pb_export(self) -> None:
        if not self._pb_moves:
            return
        text = ', '.join(f"{col.upper()} {d}" for col, d in self._pb_moves)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied!", f"Moves copied:\n{text}", parent=self)

    def _update_pb_label(self) -> None:
        n     = self._pb_solver
        s     = self._pb_step
        total = len(self._pb_moves)

        if s == 0:
            txt = f"[{n}]  Start position  (use Next ▶ to step through)"
        elif s <= total:
            col, d = self._pb_moves[s - 1]
            rh     = _ricocheted(self._pb_moves[:s], self.active)
            rh_str = "✓ ricocheted" if rh else "○ no ricochet yet"
            txt = (f"[{n}]  Step {s}/{total}:  "
                   f"{col.upper()} → {d}   "
                   f"[active: {self.active.upper()}]  {rh_str}")
        else:
            txt = f"[{n}]  ✓ Completed in {total} moves"
        self._lbl_pb.config(text=txt)

    def destroy(self) -> None:
        self._cancel_auto()
        self.app.playback_clear()
        super().destroy()


# ─────────────────────────────────────────────────────────────────────────────
#  APPLICATION
# ─────────────────────────────────────────────────────────────────────────────

class App:
    """Main application — board, UI, game logic, animation."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Ricochet Robots")
        self.root.resizable(False, False)
        self.root.configure(bg='#1A252F')

        self.board       = Board()
        self.game        = Game(self.board)
        self.players:    list[str]        = []
        self.scores:     dict[str, int]   = {}
        self.win_goal:   int              = 5
        self.robots:     Robots           = {}
        self.round_start: Robots          = {}
        self.chips:      list[tuple]      = []
        self.cur_chip:   tuple | None     = None
        self.cur_target: tuple | None     = None
        self.selected:   str              = COLORS[0]
        self.history:    list[Move]       = []
        self.move_count: int              = 0
        self.bids:       dict[str, int]   = {}
        self.bid_order:  list[tuple]      = []
        self.bid_try:    int              = 0
        self.timer_id:   str | None       = None
        self.time_left:  int              = 60
        self._pulse_id:  str | None       = None
        self._pulse_fat: bool             = False
        self._animating: bool             = False
        self._ai_window: AIWindow | None  = None

        self._run()

    def _run(self) -> None:
        self.root.withdraw()
        self._ask_players()
        self._place_robots()
        self._init_chips()
        self._build_ui()
        self.root.deiconify()
        self._new_round()
        self.root.mainloop()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _ask_players(self) -> None:
        n = (simpledialog.askinteger(
                "Ricochet Robots", "Number of players (1–6):",
                minvalue=1, maxvalue=6, parent=self.root) or 1)
        self.win_goal = {2: 8, 3: 6, 4: 5}.get(n, 17)
        for i in range(n):
            name = (simpledialog.askstring(
                "Player Name", f"Name for Player {i + 1}:",
                parent=self.root) or f"P{i + 1}")
            self.players.append(name)
            self.scores[name] = 0

    def _place_robots(self) -> None:
        forbidden = set(CENTER) | {(t[0], t[1]) for t in self.board.targets}
        self.robots = {}
        for col in COLORS:
            while True:
                r = random.randint(0, CFG.N - 1)
                c = random.randint(0, CFG.N - 1)
                if (r, c) not in forbidden and (r, c) not in self.robots.values():
                    self.robots[col] = (r, c)
                    forbidden.add((r, c))
                    break
        self.round_start = _copy_robots(self.robots)

    def _init_chips(self) -> None:
        self.chips = [(t[2], t[3]) for t in self.board.targets]
        random.shuffle(self.chips)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        WH = CFG.N * CFG.CS + 2 * CFG.M

        lf = tk.Frame(self.root, bg='#1A252F')
        lf.pack(side=tk.LEFT, padx=10, pady=10)

        self.cv = tk.Canvas(lf, width=WH, height=WH, bg='#1B2631',
                            highlightthickness=2,
                            highlightbackground='#566573')
        self.cv.pack()
        self.cv.bind('<Button-1>', self._on_click)

        rf = tk.Frame(self.root, bg='#1A252F', width=290)
        rf.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        rf.pack_propagate(False)
        self._build_panel(rf)

        for key, d in [('<Up>', 'N'), ('<Down>', 'S'),
                       ('<Left>', 'W'), ('<Right>', 'E')]:
            self.root.bind(key, lambda e, d=d: self._move(d))
        self.root.bind('<Tab>',    lambda e: self._cycle(1))
        self.root.bind('<r>',      lambda e: self._cycle(1))
        self.root.bind('<z>',      lambda e: self._undo())
        self.root.bind('<u>',      lambda e: self._undo())
        self.root.bind('<Return>', lambda e: self._confirm())
        self.root.bind('<Escape>', lambda e: self._reset_round())
        self.root.bind('<F5>',     lambda e: self._open_ai())
        for i in range(4):
            self.root.bind(str(i + 1), lambda e, i=i: self._sel(i))
        self.root.focus_set()

    def _build_panel(self, f: tk.Frame) -> None:
        def sep() -> None:
            tk.Frame(f, height=1, bg='#34495E').pack(fill=tk.X, padx=6, pady=5)

        def lbl(text: str, size: int = 9, bold: bool = False,
                color: str = '#BDC3C7', pady: tuple = (3, 0)) -> None:
            tk.Label(f, text=text,
                     font=('Helvetica', size, 'bold' if bold else 'normal'),
                     fg=color, bg='#1A252F').pack(pady=pady)

        lbl("RICOCHET ROBOTS", 13, bold=True, color='white', pady=(10, 2))
        sep()

        lbl("TARGET", bold=True)
        self.lbl_target = tk.Label(f, text="—",
                                   font=('Helvetica', 14, 'bold'),
                                   fg='white', bg='#1A252F')
        self.lbl_target.pack()

        row = tk.Frame(f, bg='#1A252F')
        row.pack(pady=2)
        for text in ("MOVES", "CHIPS"):
            tk.Label(row, text=text, font=('Helvetica', 8, 'bold'),
                     fg='#BDC3C7', bg='#1A252F').pack(side=tk.LEFT, padx=14)
        row2 = tk.Frame(f, bg='#1A252F')
        row2.pack()
        self.lbl_moves = tk.Label(row2, text="0", width=4,
                                  font=('Helvetica', 24, 'bold'),
                                  fg='#E74C3C', bg='#1A252F')
        self.lbl_moves.pack(side=tk.LEFT, padx=10)
        self.lbl_chips = tk.Label(row2, text="17", width=4,
                                  font=('Helvetica', 24, 'bold'),
                                  fg='#3498DB', bg='#1A252F')
        self.lbl_chips.pack(side=tk.LEFT, padx=10)

        sep()
        lbl("SELECTED ROBOT", bold=True)
        self.lbl_sel = tk.Label(f, text=COLORS[0].upper(),
                                font=('Helvetica', 13, 'bold'),
                                fg=HEX[COLORS[0]], bg='#1A252F')
        self.lbl_sel.pack()
        lbl("Tab/R cycle  |  1-4 pick  |  Click robot", size=8, color='#566573')

        sep()
        lbl("SCORES", bold=True)
        sf = tk.Frame(f, bg='#1A252F')
        sf.pack(fill=tk.X, padx=8, pady=2)
        self.score_lbls: dict[str, tk.Label] = {}
        for p in self.players:
            pr = tk.Frame(sf, bg='#2C3E50')
            pr.pack(fill=tk.X, pady=1)
            tk.Label(pr, text=p, font=('Helvetica', 9),
                     fg='white', bg='#2C3E50', anchor='w').pack(side=tk.LEFT, padx=4)
            sl = tk.Label(pr, text="0", font=('Helvetica', 9, 'bold'),
                          fg='#F39C12', bg='#2C3E50')
            sl.pack(side=tk.RIGHT, padx=4)
            self.score_lbls[p] = sl

        sep()
        lbl("PLACE BID", bold=True)
        br = tk.Frame(f, bg='#1A252F')
        br.pack(pady=3)
        self.bid_var = tk.StringVar()
        tk.Entry(br, textvariable=self.bid_var,
                 width=5, font=('Helvetica', 11)).pack(side=tk.LEFT, padx=3)
        tk.Button(br, text="Bid", command=self._place_bid,
                  bg='#27AE60', fg='white',
                  font=('Helvetica', 9, 'bold'), width=5).pack(side=tk.LEFT)

        self.lbl_timer = tk.Label(f, text="",
                                  font=('Helvetica', 13, 'bold'),
                                  fg='#E74C3C', bg='#1A252F')
        self.lbl_timer.pack()
        self.lbl_bids = tk.Label(f, text="", font=('Helvetica', 8),
                                 fg='#BDC3C7', bg='#1A252F',
                                 justify=tk.LEFT, wraplength=270)
        self.lbl_bids.pack()

        sep()
        buttons: list[tuple[str, object, str]] = [
            ("Confirm    ↵",      self._confirm,      '#2980B9'),
            ("Undo       U/Z",    self._undo,         '#7F8C8D'),
            ("Reset Round  Esc",  self._reset_round,  '#16A085'),
            ("Skip Chip",         self._skip_chip,    '#E67E22'),
            ("Run All AIs  F5",   self._open_ai,      '#8E44AD'),
            ("New Map",           self._new_map,      '#C0392B'),
        ]
        for txt, cmd, bg in buttons:
            tk.Button(f, text=txt, command=cmd, bg=bg, fg='white',
                      font=('Helvetica', 9, 'bold'),
                      width=28, anchor='w').pack(pady=2, padx=6)

        lbl("Arrows → move  |  Tab/R cycle  |  1-4 pick",
            size=8, color='#566573', pady=(8, 2))

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _cell_xy(self, r: int, c: int) -> tuple[int, int]:
        return c * CFG.CS + CFG.M, r * CFG.CS + CFG.M

    def _draw(self, pb_robots: Robots | None = None,
              pb_highlight: str | None = None) -> None:
        robots = pb_robots if pb_robots is not None else self.robots
        cv     = self.cv
        cv.delete('all')

        self._draw_grid_coords()
        self._draw_cells()
        self._draw_center_icon()
        for t in self.board.targets:
            self._draw_target(*t)
        self._draw_walls()
        if pb_robots is None:
            self._draw_trails()
        for col, (r, c) in robots.items():
            self._draw_robot(r, c, col, glow=(col == pb_highlight))
        if pb_robots is None and self.selected in self.robots:
            r, c = self.robots[self.selected]
            x1, y1 = self._cell_xy(r, c)
            cv.create_rectangle(x1 + 2, y1 + 2,
                                 x1 + CFG.CS - 3, y1 + CFG.CS - 3,
                                 outline='white', width=2, dash=(4, 3))
        self._draw_target_highlight()

    def _draw_grid_coords(self) -> None:
        cv = self.cv
        for i in range(CFG.N):
            cx = i * CFG.CS + CFG.M + CFG.CS // 2
            cv.create_text(cx, CFG.M // 2,
                           text=str(i), fill='#4A6278', font=('Helvetica', 7))
            cy = i * CFG.CS + CFG.M + CFG.CS // 2
            cv.create_text(CFG.M // 2, cy,
                           text=str(i), fill='#4A6278', font=('Helvetica', 7))

    def _draw_cells(self) -> None:
        cv = self.cv
        for r in range(CFG.N):
            for c in range(CFG.N):
                x1, y1 = self._cell_xy(r, c)
                if (r, c) in CENTER:
                    fill = '#3D566E'
                elif (r + c) % 2 == 0:
                    fill = '#2C3E50'
                else:
                    fill = '#243444'
                cv.create_rectangle(x1, y1, x1 + CFG.CS, y1 + CFG.CS,
                                    fill=fill, outline='')

    def _draw_center_icon(self) -> None:
        cx = 8 * CFG.CS + CFG.M
        cy = 8 * CFG.CS + CFG.M
        self.cv.create_text(cx, cy, text='⚙',
                            font=('Helvetica', 26, 'bold'), fill='#5D6D7E')

    def _draw_trails(self) -> None:
        if not self.history:
            return
        for col in COLORS:
            positions = [self.round_start[col]]
            snap = _copy_robots(self.round_start)
            for c2, d in self.history:
                snap[c2] = self.board.slide(snap, c2, d)
                if c2 == col:
                    positions.append(snap[col])
            if len(positions) < 2:
                continue
            rgb = HEX[col]
            for i in range(len(positions) - 1):
                r0, c0 = positions[i]
                r1, c1 = positions[i + 1]
                x0, y0 = self._cell_xy(r0, c0)
                x1, y1 = self._cell_xy(r1, c1)
                cx0 = x0 + CFG.CS // 2
                cy0 = y0 + CFG.CS // 2
                cx1 = x1 + CFG.CS // 2
                cy1 = y1 + CFG.CS // 2
                self.cv.create_line(cx0, cy0, cx1, cy1,
                                    fill=rgb, width=2,
                                    dash=(3, 5), capstyle='round')

    def _draw_target(self, r: int, c: int, color: str, sym: str) -> None:
        x1, y1 = self._cell_xy(r, c)
        cx  = x1 + CFG.CS // 2
        cy  = y1 + CFG.CS // 2
        col = HEX.get(color, '#9B59B6')
        s   = CFG.CS // 4 + 2
        cv  = self.cv
        if sym == 'circle':
            cv.create_oval(cx - s, cy - s, cx + s, cy + s,
                           fill=col, outline='white', width=1)
        elif sym == 'square':
            cv.create_rectangle(cx - s, cy - s, cx + s, cy + s,
                                fill=col, outline='white', width=1)
        elif sym == 'triangle':
            cv.create_polygon(cx, cy - s, cx - s, cy + s, cx + s, cy + s,
                              fill=col, outline='white')
        elif sym == 'star':
            pts: list[float] = []
            for i in range(5):
                a = math.pi * i * 2 / 5 - math.pi / 2
                pts += [cx + s * math.cos(a), cy + s * math.sin(a)]
                a += math.pi / 5
                pts += [cx + s * .42 * math.cos(a), cy + s * .42 * math.sin(a)]
            cv.create_polygon(pts, fill=col, outline='white')
        elif sym == 'vortex':
            cv.create_text(cx, cy, text='✦',
                           font=('Helvetica', s * 2, 'bold'), fill=col)

    def _draw_walls(self) -> None:
        cv  = self.cv
        wc  = '#ECF0F1'
        ww  = 4
        ins = 1
        for r, c, d in self.board.walls:
            x1, y1 = self._cell_xy(r, c)
            x2, y2 = x1 + CFG.CS, y1 + CFG.CS
            if   d == 'N':
                cv.create_line(x1 + ins, y1, x2 - ins, y1, fill=wc, width=ww)
            elif d == 'S':
                cv.create_line(x1 + ins, y2, x2 - ins, y2, fill=wc, width=ww)
            elif d == 'W':
                cv.create_line(x1, y1 + ins, x1, y2 - ins, fill=wc, width=ww)
            elif d == 'E':
                cv.create_line(x2, y1 + ins, x2, y2 - ins, fill=wc, width=ww)

    def _draw_robot(self, r: int, c: int, color: str,
                    glow: bool = False) -> None:
        x1, y1  = self._cell_xy(r, c)
        p        = 6
        outline  = '#FFFF00' if glow else 'white'
        width    = 3        if glow else 2
        self.cv.create_oval(x1 + p, y1 + p,
                             x1 + CFG.CS - p, y1 + CFG.CS - p,
                             fill=HEX[color], outline=outline, width=width)
        self.cv.create_text(x1 + CFG.CS // 2, y1 + CFG.CS // 2,
                            text=color[0].upper(),
                            font=('Helvetica', 12, 'bold'), fill='white')

    def _draw_target_highlight(self) -> None:
        if not self.cur_target:
            return
        tr, tc = self.cur_target[0], self.cur_target[1]
        x1, y1 = self._cell_xy(tr, tc)
        w = 4 if self._pulse_fat else 2
        self.cv.create_rectangle(x1 + 1, y1 + 1,
                                  x1 + CFG.CS - 1, y1 + CFG.CS - 1,
                                  outline='#F39C12', width=w)

    def _start_pulse(self) -> None:
        self._cancel_pulse()
        self._pulse_tick()

    def _pulse_tick(self) -> None:
        self._pulse_fat = not self._pulse_fat
        self._draw()
        self._pulse_id = self.root.after(CFG.PULSE_MS, self._pulse_tick)

    def _cancel_pulse(self) -> None:
        if self._pulse_id:
            self.root.after_cancel(self._pulse_id)
            self._pulse_id = None

    # ── Robot slide animation ─────────────────────────────────────────────────

    def _animate_move(self, color: str,
                      old: tuple[int, int],
                      new: tuple[int, int],
                      callback: object) -> None:
        frames = CFG.ANIM_FRAMES
        r0, c0 = old
        r1, c1 = new

        def tick(frame: int) -> None:
            t = frame / frames
            r = r0 + (r1 - r0) * t
            c = c0 + (c1 - c0) * t
            snap        = _copy_robots(self.robots)
            snap[color] = (int(round(r)), int(round(c)))
            self._draw_anim(snap, color, r, c)
            if frame < frames:
                self.root.after(CFG.ANIM_MS, tick, frame + 1)
            else:
                self._animating = False
                callback()

        self._animating = True
        tick(1)

    def _draw_anim(self, robots: Robots, moving: str,
                   fr: float, fc: float) -> None:
        cv = self.cv
        cv.delete('all')
        self._draw_grid_coords()
        self._draw_cells()
        self._draw_center_icon()
        for t in self.board.targets:
            self._draw_target(*t)
        self._draw_walls()
        self._draw_trails()
        for col, (r, c) in robots.items():
            if col == moving:
                x1 = fc * CFG.CS + CFG.M
                y1 = fr * CFG.CS + CFG.M
                p  = 6
                cv.create_oval(x1 + p, y1 + p,
                               x1 + CFG.CS - p, y1 + CFG.CS - p,
                               fill=HEX[col], outline='#FFFF00', width=3)
                cv.create_text(x1 + CFG.CS // 2, y1 + CFG.CS // 2,
                               text=col[0].upper(),
                               font=('Helvetica', 12, 'bold'), fill='white')
            else:
                self._draw_robot(r, c, col)
        self._draw_target_highlight()

    # ── Input ─────────────────────────────────────────────────────────────────

    def _on_click(self, e: tk.Event) -> None:
        c = (e.x - CFG.M) // CFG.CS
        r = (e.y - CFG.M) // CFG.CS
        for col, pos in self.robots.items():
            if pos == (r, c):
                self.selected = col
                self._refresh_sel()
                self._draw()
                return

    def _move(self, d: str) -> None:
        if self._animating:
            return
        old = self.robots[self.selected]
        new = self.board.slide(self.robots, self.selected, d)
        if new == old:
            return
        self.history.append((self.selected, d))
        self.robots[self.selected] = new
        self.move_count += 1
        self.lbl_moves.config(text=str(self.move_count))

        col = self.selected

        def after_anim() -> None:
            self._draw()
            self._check_win()

        self._animate_move(col, old, new, after_anim)

    def _undo(self) -> None:
        if not self.history or self._animating:
            return
        self.history.pop()
        self.robots = _copy_robots(self.round_start)
        for col, d in self.history:
            self.robots[col] = self.board.slide(self.robots, col, d)
        self.move_count = max(0, self.move_count - 1)
        self.lbl_moves.config(text=str(self.move_count))
        self._draw()

    def _cycle(self, delta: int) -> None:
        idx = (list(COLORS).index(self.selected) + delta) % len(COLORS)
        self.selected = COLORS[idx]
        self._refresh_sel()
        self._draw()

    def _sel(self, idx: int) -> None:
        self.selected = COLORS[idx]
        self._refresh_sel()
        self._draw()

    def _refresh_sel(self) -> None:
        self.lbl_sel.config(text=self.selected.upper(),
                            fg=HEX[self.selected])

    # ── Game logic ────────────────────────────────────────────────────────────

    def _check_win(self) -> None:
        if not self.cur_target:
            return
        tr, tc, tcolor, _ = self.cur_target
        tpos = (tr, tc)

        if tcolor == 'all':
            active = next(
                (col for col, pos in self.robots.items() if pos == tpos), None)
            if not active:
                return
        else:
            active = tcolor
            if self.robots.get(active) != tpos:
                return

        if not _ricocheted(self.history, active):
            messagebox.showwarning(
                "Ricochet Required",
                f"The {active.upper()} robot must change direction at least\n"
                "once before reaching the target!\n\n"
                "Keep moving — use another robot as a reflector.")
            return

        self._on_win()

    def _confirm(self) -> None:
        self._check_win()

    def _on_win(self) -> None:
        self._cancel_timer()
        if self.bid_order:
            player, bid = self.bid_order[self.bid_try]
            if self.move_count <= bid:
                self._award(player)
            else:
                messagebox.showwarning(
                    "Failed",
                    f"{player} used {self.move_count} moves but bid {bid}.\n"
                    "Passing to next bidder.")
                self.bid_try += 1
                self._try_bidder()
        else:
            messagebox.showinfo("Solved!",
                                f"Done in {self.move_count} move(s)! 🎉")
            self._next_round()

    def _award(self, player: str) -> None:
        self.scores[player] += 1
        self.score_lbls[player].config(text=str(self.scores[player]))
        messagebox.showinfo(
            "Chip Won! 🏆",
            f"{player} wins the chip!\n"
            f"Score: {self.scores[player]} / {self.win_goal}")
        if self.scores[player] >= self.win_goal:
            messagebox.showinfo(
                "Game Over",
                f"🏆 {player} wins with {self.scores[player]} chip(s)!")
            self.root.quit()
            return
        self._next_round()

    # ── Round management ──────────────────────────────────────────────────────

    def _new_round(self) -> None:
        if not self.chips:
            best = max(self.scores.values())
            wrs  = [p for p, s in self.scores.items() if s == best]
            messagebox.showinfo("Game Over",
                                f"All chips done!\n"
                                f"Winner(s): {', '.join(wrs)} — {best} chips.")
            self.root.quit()
            return

        self.history.clear()
        self.move_count = 0
        self.lbl_moves.config(text="0")
        self.bids.clear()
        self.bid_order.clear()
        self.bid_try = 0
        self.lbl_timer.config(text="")
        self.lbl_bids.config(text="")
        self._cancel_timer()
        self._start_pulse()

        self.round_start = _copy_robots(self.robots)
        self.cur_chip    = self.chips.pop(0)
        self.cur_target  = next(
            (t for t in self.board.targets
             if t[2] == self.cur_chip[0] and t[3] == self.cur_chip[1]), None)

        tcolor, tsym = self.cur_chip
        self.lbl_target.config(
            text=f"{tcolor.upper()}  {tsym.upper()}",
            fg=HEX.get(tcolor, 'white'))
        self.lbl_chips.config(text=str(len(self.chips)))
        self.selected = tcolor if tcolor in COLORS else COLORS[0]
        self._refresh_sel()
        self._draw()

    def _next_round(self) -> None:
        self.round_start = _copy_robots(self.robots)
        self._new_round()

    def _reset_round(self) -> None:
        self._cancel_timer()
        self.robots     = _copy_robots(self.round_start)
        self.history.clear()
        self.move_count = 0
        self.lbl_moves.config(text="0")
        self._draw()

    def _skip_chip(self) -> None:
        self._cancel_timer()
        if self.cur_chip:
            self.chips.append(self.cur_chip)
            random.shuffle(self.chips)
        self.robots = _copy_robots(self.round_start)
        self.history.clear()
        self.move_count = 0
        self.lbl_moves.config(text="0")
        self._new_round()

    def _new_map(self) -> None:
        self._cancel_timer()
        self._place_robots()
        self.history.clear()
        self.move_count = 0
        self.bids.clear()
        self.bid_order.clear()
        self.lbl_bids.config(text="")
        self._new_round()

    # ── Bidding ───────────────────────────────────────────────────────────────

    def _place_bid(self) -> None:
        try:
            val = int(self.bid_var.get())
            if val < 1:
                return
        except ValueError:
            return

        if len(self.players) == 1:
            player = self.players[0]
        else:
            names = '\n'.join(f"{i + 1}. {p}" for i, p in enumerate(self.players))
            idx = simpledialog.askinteger(
                "Who bids?", f"Enter player number:\n{names}",
                minvalue=1, maxvalue=len(self.players), parent=self.root)
            if not idx:
                return
            player = self.players[idx - 1]

        if player in self.bids and val >= self.bids[player]:
            messagebox.showwarning("Invalid Bid", "You can only lower your bid!")
            return
        self.bids[player] = val
        self.bid_var.set("")
        if not self.timer_id:
            self.time_left = 60
            self._tick()
        self.lbl_bids.config(
            text="Bids:\n" + '\n'.join(
                f"  {p}: {b}"
                for p, b in sorted(self.bids.items(), key=lambda x: x[1])))

    def _tick(self) -> None:
        self.lbl_timer.config(text=f"⏱  {self.time_left}s")
        if self.time_left > 0:
            self.time_left -= 1
            self.timer_id = self.root.after(1000, self._tick)
        else:
            self.timer_id = None
            self.lbl_timer.config(text="⏱  Time's up!")
            if self.bids:
                self._start_execution()

    def _cancel_timer(self) -> None:
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.lbl_timer.config(text="")

    def _start_execution(self) -> None:
        self.bid_order = sorted(
            self.bids.items(),
            key=lambda x: (x[1], self.scores[x[0]]))
        self.bid_try = 0
        self._try_bidder()

    def _try_bidder(self) -> None:
        if self.bid_try >= len(self.bid_order):
            messagebox.showinfo("Round Over",
                                "No player succeeded. Chip reshuffled.")
            self._skip_chip()
            return
        player, bid = self.bid_order[self.bid_try]
        self.robots = _copy_robots(self.round_start)
        self.history.clear()
        self.move_count = 0
        self.lbl_moves.config(text="0")
        self._draw()
        ok = messagebox.askokcancel(
            "Demonstrate",
            f"{player}  —  you bid {bid} move(s).\n\n"
            "Use arrow keys to demonstrate your solution.\n"
            "OK to start  |  Cancel to forfeit.")
        if not ok:
            self.bid_try += 1
            self._try_bidder()

    # ── AI panel ──────────────────────────────────────────────────────────────

    def _open_ai(self) -> None:
        if not self.cur_target:
            return
        if self._ai_window and self._ai_window.winfo_exists():
            self._ai_window.lift()
            return
        tcolor = self.cur_target[2]
        active = tcolor if tcolor in COLORS else COLORS[0]
        self._ai_window = AIWindow(
            self, _copy_robots(self.round_start), self.cur_target, active)

    # ── Playback API (called by AIWindow) ─────────────────────────────────────

    def playback_apply(self, robots_start: Robots,
                       moves: list[Move], step: int) -> None:
        """Replay *moves[:step]* from *robots_start* and redraw the board."""
        robots    = _copy_robots(robots_start)
        highlight = None
        for i, (col, d) in enumerate(moves[:step]):
            robots[col] = self.board.slide(robots, col, d)
            if i == step - 1:
                highlight = col
        self._draw(pb_robots=robots, pb_highlight=highlight)

    def playback_clear(self) -> None:
        """Return the board to normal (non-playback) rendering."""
        self._draw()


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    App()
