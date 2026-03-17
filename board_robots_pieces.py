#!/usr/bin/env python3
import os
import sys
import math
import random
import heapq

import pygame
from pygame.locals import *

# ============================================================
# Ricochet Robots
# - Fixed board walls
# - Fixed symbol piece positions
# - Random robot positions
# - Side-panel UI
# - R key or button reloads robots only
# - One active target shown in center
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -----------------------------
# Layout
# -----------------------------
GRID_SIZE = 16
CELL = 44
BOARD_MARGIN = 24
SIDE_PANEL_W = 280

BOARD_PX = GRID_SIZE * CELL
SCREEN_W = BOARD_MARGIN * 2 + BOARD_PX + SIDE_PANEL_W
SCREEN_H = BOARD_MARGIN * 2 + BOARD_PX

BOARD_ORIGIN_X = BOARD_MARGIN
BOARD_ORIGIN_Y = BOARD_MARGIN
PANEL_X = BOARD_ORIGIN_X + BOARD_PX + 20

# -----------------------------
# Colors
# -----------------------------
BG_COLOR = (28, 28, 30)
PANEL_BG = (242, 242, 245)
PANEL_BORDER = (180, 180, 188)
TEXT_COLOR = (25, 25, 30)
MUTED_TEXT = (90, 90, 100)

BOARD_FRAME = (70, 70, 76)
BOARD_INNER = (100, 100, 108)
CELL_COLOR = (235, 232, 210)
CELL_LIGHT = (252, 250, 236)
CELL_DARK = (188, 184, 164)
GRID_LINE = (185, 180, 158)
WALL_COLOR = (52, 52, 52)
CENTER_BLOCK = (70, 70, 74)
CENTER_HIGHLIGHT = (105, 105, 112)
LABEL_COLOR = (215, 215, 220)
SELECT_COLOR = (255, 230, 0)

BUTTON_BG = (230, 230, 235)
BUTTON_BG_HOVER = (218, 218, 224)
BUTTON_BORDER = (95, 95, 105)

WALL_THICKNESS = 5

# -----------------------------
# Assets
# -----------------------------
ROBOT_FILES = {
    "red": "redbot.png",
    "blue": "bluebot.png",
    "green": "greenbot.png",
    "yellow": "yellowbot.png",
}

SYMBOL_FILES = {
    "blue": {
        "bio": "bluebio.png",
        "tar": "bluetar.png",
        "tri": "bluetri.png",
        "hex": "bluehex.png",
    },
    "yellow": {
        "bio": "yellowbio.png",
        "tar": "yellowtar.png",
        "tri": "yellowtri.png",
        "hex": "yellowhex.png",
    },
    "green": {
        "bio": "greenbio.png",
        "tar": "greentar.png",
        "tri": "greentri.png",
        "hex": "greenhex.png",
    },
    "red": {
        "bio": "redbio.png",
        "tar": "redtar.png",
        "tri": "redtri.png",
        "hex": "redhex.png",
    },
}

COLOR_ORDER = ["red", "blue", "green", "yellow"]

# -----------------------------
# Fixed walls
# side in N/S/E/W
# -----------------------------
FIXED_WALLS = [
    (0, 2, "E"),
    (0, 8, "E"),
    (15, 5, "E"),
    (15, 11, "E"),
    (3, 0, "S"),
    (10, 0, "S"),
    (1, 15, "S"),
    (9, 15, "S"),

    (1, 5, "W"), (1, 5, "S"),
    (1, 11, "N"), (1, 11, "W"),
    (2, 7, "S"), (2, 7, "E"),
    (3, 14, "E"), (3, 14, "N"),
    (4, 3, "E"), (4, 3, "S"),
    (4, 9, "S"), (4, 9, "E"),
    (5, 6, "W"), (5, 6, "N"),
    (6, 1, "E"), (6, 1, "N"),
    (6, 12, "W"), (6, 12, "S"),
    (9, 1, "E"), (9, 1, "N"),
    (9, 5, "W"), (9, 5, "N"),
    (10, 8, "E"), (10, 8, "S"),
    (11, 13, "W"), (11, 13, "N"),
    (12, 6, "S"), (12, 6, "E"),
    (13, 9, "W"), (13, 9, "S"),
    (14, 2, "S"), (14, 2, "W"),
    (14, 14, "N"), (14, 14, "E"),
]

CENTER_BLOCK_CELLS = {(7, 7), (7, 8), (8, 7), (8, 8)}

# -----------------------------
# Fixed stationary symbols
# User gave coordinates as (row, column), i.e. (y, x)
# We convert them to (x, y)
# -----------------------------
FIXED_SYMBOL_POSITIONS_RC = {
    ("blue", "bio"): (4, 9),
    ("blue", "tar"): (1, 5),
    ("blue", "tri"): (3, 14),
    ("blue", "hex"): (11, 13),

    ("yellow", "bio"): (10, 8),
    ("yellow", "tar"): (1, 11),
    ("yellow", "tri"): (6, 1),
    ("yellow", "hex"): (6, 12),

    ("green", "bio"): (5, 6),
    ("green", "tar"): (13, 9),
    ("green", "tri"): (14, 2),
    ("green", "hex"): (9, 1),

    ("red", "bio"): (9, 5),
    ("red", "tar"): (12, 6),
    ("red", "tri"): (14, 14),
    ("red", "hex"): (4, 3),
}

FIXED_SYMBOL_POSITIONS_XY = {
    key: (col, row) for key, (row, col) in FIXED_SYMBOL_POSITIONS_RC.items()
}


class Square:
    def __init__(self, coords):
        self.coords = coords
        self.left = None
        self.right = None
        self.up = None
        self.down = None
        self.robot = None
        self.symbol = None

    @property
    def box(self):
        x, y = self.coords
        return pygame.Rect(
            BOARD_ORIGIN_X + x * CELL,
            BOARD_ORIGIN_Y + y * CELL,
            CELL,
            CELL,
        )


class Robot:
    def __init__(self, img, color):
        self.img = img
        self.color = color
        self.square = None


class Symbol:
    def __init__(self, img, color, sym_type):
        self.img = img
        self.color = color
        self.type = sym_type
        self.square = None


class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text

    def draw(self, surface, font, hovered=False):
        bg = BUTTON_BG_HOVER if hovered else BUTTON_BG
        pygame.draw.rect(surface, bg, self.rect, border_radius=10)
        pygame.draw.rect(surface, BUTTON_BORDER, self.rect, 2, border_radius=10)
        label = font.render(self.text, True, TEXT_COLOR)
        surface.blit(label, label.get_rect(center=self.rect.center))

    def hit(self, pos):
        return self.rect.collidepoint(pos)


def asset_path(filename):
    return os.path.join(BASE_DIR, "Game pieces png", filename)


def load_scaled(path, size):
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(img, (size, size))


def cell_rect(x, y):
    return pygame.Rect(
        BOARD_ORIGIN_X + x * CELL,
        BOARD_ORIGIN_Y + y * CELL,
        CELL,
        CELL,
    )


def all_symbols():
    out = []
    for color in COLOR_ORDER:
        for sym_type in ["bio", "tar", "tri", "hex"]:
            out.append(symbols[color][sym_type])
    return out


def robot_index_from_color(color):
    return COLOR_ORDER.index(color)


def build_grid():
    new_grid = [[Square((x, y)) for y in range(GRID_SIZE)] for x in range(GRID_SIZE)]

    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            if (x, y) in CENTER_BLOCK_CELLS:
                continue

            if x > 0 and (x - 1, y) not in CENTER_BLOCK_CELLS:
                new_grid[x][y].left = new_grid[x - 1][y]
            if x < GRID_SIZE - 1 and (x + 1, y) not in CENTER_BLOCK_CELLS:
                new_grid[x][y].right = new_grid[x + 1][y]
            if y > 0 and (x, y - 1) not in CENTER_BLOCK_CELLS:
                new_grid[x][y].up = new_grid[x][y - 1]
            if y < GRID_SIZE - 1 and (x, y + 1) not in CENTER_BLOCK_CELLS:
                new_grid[x][y].down = new_grid[x][y + 1]

    for x, y, side in FIXED_WALLS:
        sq = new_grid[x][y]
        if side == "N" and sq.up:
            sq.up.down = None
            sq.up = None
        elif side == "S" and sq.down:
            sq.down.up = None
            sq.down = None
        elif side == "W" and sq.left:
            sq.left.right = None
            sq.left = None
        elif side == "E" and sq.right:
            sq.right.left = None
            sq.right = None

    return new_grid


def clear_board_robots():
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            if (x, y) in CENTER_BLOCK_CELLS:
                continue
            grid[x][y].robot = None
    for rb in robots.values():
        rb.square = None


def place_fixed_symbols():
    for sym in all_symbols():
        sym.square = None

    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            if (x, y) in CENTER_BLOCK_CELLS:
                continue
            grid[x][y].symbol = None

    for (color, sym_type), (x, y) in FIXED_SYMBOL_POSITIONS_XY.items():
        sq = grid[x][y]
        sym = symbols[color][sym_type]
        sym.square = sq
        sq.symbol = sym


def legal_robot_squares():
    out = []
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            if (x, y) in CENTER_BLOCK_CELLS:
                continue
            sq = grid[x][y]
            if sq.symbol is not None:
                continue
            out.append(sq)
    return out


def randomize_robots_only():
    clear_board_robots()
    candidates = legal_robot_squares()
    chosen = random.sample(candidates, 4)
    for color, sq in zip(COLOR_ORDER, chosen):
        rb = robots[color]
        rb.square = sq
        sq.robot = rb


def get_state():
    return tuple(robots[color].square.coords for color in COLOR_ORDER)


def set_state(state):
    clear_board_robots()
    for color, coords in zip(COLOR_ORDER, state):
        sq = grid[coords[0]][coords[1]]
        robots[color].square = sq
        sq.robot = robots[color]


def slide_from_state(state, robot_idx, direction):
    positions = list(state)
    x, y = positions[robot_idx]
    occupied = set(state)
    occupied.remove((x, y))

    while True:
        sq = grid[x][y]
        if direction == "L":
            nxt = sq.left
        elif direction == "R":
            nxt = sq.right
        elif direction == "U":
            nxt = sq.up
        else:
            nxt = sq.down

        if nxt is None:
            break
        if nxt.coords in occupied:
            break

        x, y = nxt.coords

    if (x, y) == positions[robot_idx]:
        return None

    positions[robot_idx] = (x, y)
    return tuple(positions)


def goal_test(state, target_symbol):
    idx = robot_index_from_color(target_symbol.color)
    return state[idx] == target_symbol.square.coords


def heuristic(state, target_symbol):
    idx = robot_index_from_color(target_symbol.color)
    rx, ry = state[idx]
    tx, ty = target_symbol.square.coords
    return abs(rx - tx) + abs(ry - ty)


def reconstruct_path(parent, end_state):
    path = []
    cur = end_state
    while parent[cur] is not None:
        prev, move = parent[cur]
        path.append(move)
        cur = prev
    path.reverse()
    return path


def solve_astar(start_state, target_symbol, max_depth=30):
    pq = [(heuristic(start_state, target_symbol), 0, start_state)]
    gscore = {start_state: 0}
    parent = {start_state: None}
    closed = set()

    while pq:
        _, g, state = heapq.heappop(pq)
        if state in closed:
            continue
        closed.add(state)

        if goal_test(state, target_symbol):
            return reconstruct_path(parent, state)

        if g >= max_depth:
            continue

        for robot_idx in range(4):
            for d in "LRUD":
                nxt = slide_from_state(state, robot_idx, d)
                if nxt is None:
                    continue
                ng = g + 1
                if ng < gscore.get(nxt, math.inf):
                    gscore[nxt] = ng
                    parent[nxt] = (state, (robot_idx, d))
                    heapq.heappush(pq, (ng + heuristic(nxt, target_symbol), ng, nxt))
    return None


def generate_solvable_robot_layout():
    global target_symbol, cached_solution, selected_square

    all_syms = all_symbols()
    tries = 0
    while True:
        tries += 1
        randomize_robots_only()
        target_symbol = random.choice(all_syms)
        start = get_state()
        plan = solve_astar(start, target_symbol, max_depth=30)
        if plan is not None:
            cached_solution = plan
            selected_square = None
            return


def move_selected(direction):
    global selected_square
    if selected_square is None or selected_square.robot is None:
        return

    sq = selected_square
    rb = sq.robot

    while True:
        if direction == "L":
            nxt = sq.left
        elif direction == "R":
            nxt = sq.right
        elif direction == "U":
            nxt = sq.up
        else:
            nxt = sq.down

        if nxt is None or nxt.robot is not None:
            break

        nxt.robot = rb
        rb.square = nxt
        sq.robot = None
        sq = nxt

    selected_square = sq


def draw_cell(surface, x, y):
    rect = cell_rect(x, y)
    pygame.draw.rect(surface, CELL_COLOR, rect)
    pygame.draw.line(surface, CELL_LIGHT, rect.topleft, rect.topright, 1)
    pygame.draw.line(surface, CELL_LIGHT, rect.topleft, rect.bottomleft, 1)
    pygame.draw.line(surface, CELL_DARK, rect.bottomleft, rect.bottomright, 1)
    pygame.draw.line(surface, CELL_DARK, rect.topright, rect.bottomright, 1)


def draw_wall(surface, x, y, side):
    rect = cell_rect(x, y)
    if side == "N":
        pygame.draw.line(surface, WALL_COLOR, rect.topleft, rect.topright, WALL_THICKNESS)
    elif side == "S":
        pygame.draw.line(surface, WALL_COLOR, rect.bottomleft, rect.bottomright, WALL_THICKNESS)
    elif side == "W":
        pygame.draw.line(surface, WALL_COLOR, rect.topleft, rect.bottomleft, WALL_THICKNESS)
    elif side == "E":
        pygame.draw.line(surface, WALL_COLOR, rect.topright, rect.bottomright, WALL_THICKNESS)


def draw_board():
    screen.fill(BG_COLOR)

    board_frame = pygame.Rect(
        BOARD_ORIGIN_X - 10,
        BOARD_ORIGIN_Y - 10,
        BOARD_PX + 20,
        BOARD_PX + 20,
    )
    pygame.draw.rect(screen, BOARD_FRAME, board_frame, border_radius=14)
    pygame.draw.rect(screen, BOARD_INNER, board_frame, 3, border_radius=14)

    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            if (x, y) in CENTER_BLOCK_CELLS:
                continue
            draw_cell(screen, x, y)

    for i in range(1, GRID_SIZE):
        px = BOARD_ORIGIN_X + i * CELL
        py = BOARD_ORIGIN_Y + i * CELL
        pygame.draw.line(screen, GRID_LINE, (px, BOARD_ORIGIN_Y), (px, BOARD_ORIGIN_Y + BOARD_PX), 1)
        pygame.draw.line(screen, GRID_LINE, (BOARD_ORIGIN_X, py), (BOARD_ORIGIN_X + BOARD_PX, py), 1)

    c0 = cell_rect(7, 7)
    c1 = cell_rect(8, 8)
    center_rect = pygame.Rect(c0.left, c0.top, c1.right - c0.left, c1.bottom - c0.top)
    pygame.draw.rect(screen, CENTER_BLOCK, center_rect, border_radius=8)
    pygame.draw.rect(screen, CENTER_HIGHLIGHT, center_rect, 2, border_radius=8)

    for x, y, side in FIXED_WALLS:
        draw_wall(screen, x, y, side)

    # Labels
    for i in range(GRID_SIZE):
        col_label = font_small.render(chr(ord("A") + i), True, LABEL_COLOR)
        row_label = font_small.render(str(i + 1), True, LABEL_COLOR)

        cx = BOARD_ORIGIN_X + i * CELL + CELL // 2
        cy = BOARD_ORIGIN_Y + i * CELL + CELL // 2

        screen.blit(col_label, col_label.get_rect(center=(cx, BOARD_ORIGIN_Y - 14)))
        screen.blit(col_label, col_label.get_rect(center=(cx, BOARD_ORIGIN_Y + BOARD_PX + 14)))
        screen.blit(row_label, row_label.get_rect(center=(BOARD_ORIGIN_X - 12, cy)))
        screen.blit(row_label, row_label.get_rect(center=(BOARD_ORIGIN_X + BOARD_PX + 12, cy)))

    # Fixed symbols
    for sym in all_symbols():
        if sym.square:
            rect = sym.square.box
            img_rect = sym.img.get_rect(center=rect.center)
            screen.blit(sym.img, img_rect)

    # Robots
    for color in COLOR_ORDER:
        rb = robots[color]
        if rb.square:
            rect = rb.square.box
            img_rect = rb.img.get_rect(center=rect.center)
            screen.blit(rb.img, img_rect)

    # Active target shown in center
    if target_symbol:
        img_rect = target_symbol.img.get_rect(center=center_rect.center)
        screen.blit(target_symbol.img, img_rect)

    if selected_square is not None:
        pygame.draw.rect(screen, SELECT_COLOR, selected_square.box, 2)

    # Side panel
    panel = pygame.Rect(PANEL_X, BOARD_ORIGIN_Y, SIDE_PANEL_W - 40, BOARD_PX)
    pygame.draw.rect(screen, PANEL_BG, panel, border_radius=16)
    pygame.draw.rect(screen, PANEL_BORDER, panel, 2, border_radius=16)

    title = font_title.render("Ricochet Robots", True, TEXT_COLOR)
    screen.blit(title, (panel.x + 18, panel.y + 18))

    subtitle = font_info.render("Fixed pieces, random robots", True, MUTED_TEXT)
    screen.blit(subtitle, (panel.x + 18, panel.y + 60))

    # draw buttons lower so they don't overlap text
    reload_button.rect.topleft = (panel.x + 18, panel.y + 110)
    new_target_button.rect.topleft = (panel.x + 18, panel.y + 166)
    show_solution_button.rect.topleft = (panel.x + 18, panel.y + 222)

    hover_reload = reload_button.hit(pygame.mouse.get_pos())
    hover_new_target = new_target_button.hit(pygame.mouse.get_pos())
    hover_show_solution = show_solution_button.hit(pygame.mouse.get_pos())

    reload_button.draw(screen, font_button, hover_reload)
    new_target_button.draw(screen, font_button, hover_new_target)
    show_solution_button.draw(screen, font_button, hover_show_solution)

    y = panel.y + 290
    screen.blit(font_section.render("Current target", True, TEXT_COLOR), (panel.x + 18, y))
    y += 34

    if target_symbol:
        target_text = f"{target_symbol.color.capitalize()} {target_symbol.type}"
        screen.blit(font_info.render(target_text, True, TEXT_COLOR), (panel.x + 18, y))
        y += 28
        coords = target_symbol.square.coords
        coords_text = f"Board square: ({coords[0]}, {coords[1]})"
        screen.blit(font_info.render(coords_text, True, MUTED_TEXT), (panel.x + 18, y))
        y += 32

    solvable_text = "Solvable: Yes" if cached_solution is not None else "Solvable: No"
    screen.blit(font_info.render(solvable_text, True, TEXT_COLOR), (panel.x + 18, y))
    y += 26

    if cached_solution is not None:
        move_preview = " ".join(
            f"{COLOR_ORDER[idx][0].upper()}{d}" for idx, d in cached_solution[:8]
        )
        if len(cached_solution) > 8:
            move_preview += " ..."
        screen.blit(font_info.render(f"Moves: {len(cached_solution)}", True, TEXT_COLOR), (panel.x + 18, y))
        y += 24
        screen.blit(font_small.render(move_preview, True, MUTED_TEXT), (panel.x + 18, y))
        y += 38

        screen.blit(font_section.render("Controls", True, TEXT_COLOR), (panel.x + 18, y))
    y += 34

    controls = [
        "R = reload robots",
        "T = new target only",
        "Mouse click or 1/2/3/4 = select robot",
        "Arrow keys = move selected robot",
        "Esc = quit",
    ]

    for line in controls:
        text_rect = pygame.Rect(panel.x + 18, y, panel.width - 36, 100)
        y = draw_text_wrapped(screen, line, font_info, MUTED_TEXT, text_rect)
        y += 6


def start_solution_animation():
    global animation_queue, animation_active, animation_last_step
    if cached_solution is None:
        return
    animation_queue = list(cached_solution)
    animation_active = True
    animation_last_step = pygame.time.get_ticks()


def animate_solution_step():
    global animation_active, animation_last_step
    if not animation_active:
        return
    now = pygame.time.get_ticks()
    if now - animation_last_step < 260:
        return
    animation_last_step = now

    if not animation_queue:
        animation_active = False
        return

    move = animation_queue.pop(0)
    apply_move(move)

    if not animation_queue:
        animation_active = False


def apply_move(move):
    robot_idx, direction = move
    rb = robots[COLOR_ORDER[robot_idx]]
    sq = rb.square

    while True:
        if direction == "L":
            nxt = sq.left
        elif direction == "R":
            nxt = sq.right
        elif direction == "U":
            nxt = sq.up
        else:
            nxt = sq.down

        if nxt is None or nxt.robot is not None:
            break

        nxt.robot = rb
        rb.square = nxt
        sq.robot = None
        sq = nxt

def draw_text_wrapped(surface, text, font, color, rect, line_spacing=4):
    words = text.split(" ")
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if font.size(test_line)[0] <= rect.width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    y = rect.y
    for line in lines:
        rendered = font.render(line, True, color)
        surface.blit(rendered, (rect.x, y))
        y += rendered.get_height() + line_spacing

    return y  # return new y position

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Ricochet Robots")
clock = pygame.time.Clock()

font_title = pygame.font.SysFont(None, 34)
font_section = pygame.font.SysFont(None, 28)
font_button = pygame.font.SysFont(None, 26)
font_info = pygame.font.SysFont(None, 24)
font_small = pygame.font.SysFont(None, 20)

robot_size = int(CELL * 0.82)
symbol_size = int(CELL * 0.68)

robots = {
    color: Robot(load_scaled(asset_path(filename), robot_size), color)
    for color, filename in ROBOT_FILES.items()
}

symbols = {}
for color in COLOR_ORDER:
    symbols[color] = {}
    for sym_type, filename in SYMBOL_FILES[color].items():
        symbols[color][sym_type] = Symbol(
            load_scaled(asset_path(filename), symbol_size),
            color,
            sym_type,
        )

grid = build_grid()
place_fixed_symbols()

selected_square = None
target_symbol = None
cached_solution = None

reload_button = Button((PANEL_X + 20, BOARD_ORIGIN_Y + 92, 200, 44), "Reload robots")
new_target_button = Button((PANEL_X + 20, BOARD_ORIGIN_Y + 146, 200, 44), "New target")
show_solution_button = Button((PANEL_X + 20, BOARD_ORIGIN_Y + 200, 200, 44), "Show solution")

animation_queue = []
animation_active = False
animation_last_step = 0

generate_solvable_robot_layout()

while True:
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == KEYDOWN:
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()
            elif event.key == K_r:
                animation_active = False
                generate_solvable_robot_layout()
            elif event.key == K_t:
                animation_active = False
                # keep robots, just pick a new solvable target
                tries = 0
                while True:
                    tries += 1
                    candidate = random.choice(all_symbols())
                    plan = solve_astar(get_state(), candidate, max_depth=30)
                    if plan is not None:
                        target_symbol = candidate
                        cached_solution = plan
                        break
            elif event.key == K_1 and robots["red"].square:
                selected_square = robots["red"].square
            elif event.key == K_2 and robots["blue"].square:
                selected_square = robots["blue"].square
            elif event.key == K_3 and robots["green"].square:
                selected_square = robots["green"].square
            elif event.key == K_4 and robots["yellow"].square:
                selected_square = robots["yellow"].square
            elif event.key == K_LEFT:
                animation_active = False
                move_selected("L")
            elif event.key == K_RIGHT:
                animation_active = False
                move_selected("R")
            elif event.key == K_UP:
                animation_active = False
                move_selected("U")
            elif event.key == K_DOWN:
                animation_active = False
                move_selected("D")

        elif event.type == MOUSEBUTTONDOWN:
            pos = event.pos

            if reload_button.hit(pos):
                animation_active = False
                generate_solvable_robot_layout()

            elif new_target_button.hit(pos):
                animation_active = False
                while True:
                    candidate = random.choice(all_symbols())
                    plan = solve_astar(get_state(), candidate, max_depth=30)
                    if plan is not None:
                        target_symbol = candidate
                        cached_solution = plan
                        break

            elif show_solution_button.hit(pos):
                animation_active = False
                start_solution_animation()

            else:
                for x in range(GRID_SIZE):
                    for y in range(GRID_SIZE):
                        if (x, y) in CENTER_BLOCK_CELLS:
                            continue
                        sq = grid[x][y]
                        if sq.box.collidepoint(pos) and sq.robot is not None:
                            selected_square = sq

    animate_solution_step()
    draw_board()
    pygame.display.flip()
    clock.tick(60)