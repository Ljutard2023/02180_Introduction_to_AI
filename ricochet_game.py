#!/usr/bin/env python3

import pygame
import sys
import random
from pathlib import Path

import ricochet_robots_board as board

# ============================================
# CONFIG
# ============================================
GRID_SIZE = 16
CELL = board.CELL
GRID_ORIGIN = board.GRID_ORIGIN

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "Game pieces png"

COLORS = ["red", "blue", "green", "yellow"]

FIXED_SYMBOLS = {
    ("blue","bio"): (4,9),
    ("blue","tar"): (1,5),
    ("blue","tri"): (3,14),
    ("blue","hex"): (11,13),

    ("yellow","bio"): (10,8),
    ("yellow","tar"): (1,11),
    ("yellow","tri"): (6,1),
    ("yellow","hex"): (6,12),

    ("green","bio"): (5,6),
    ("green","tar"): (13,9),
    ("green","tri"): (14,2),
    ("green","hex"): (9,1),

    ("red","bio"): (9,5),
    ("red","tar"): (12,6),
    ("red","tri"): (14,14),
    ("red","hex"): (4,3),
}

# ============================================
# GRID
# ============================================
class Square:
    def __init__(self, x, y):
        self.coords = (x, y)
        self.left = None
        self.right = None
        self.up = None
        self.down = None


def build_grid():
    grid = [[Square(x, y) for y in range(16)] for x in range(16)]

    for x in range(16):
        for y in range(16):
            if (x, y) in [(7,7),(7,8),(8,7),(8,8)]:
                continue

            if x > 0:
                grid[x][y].left = grid[x-1][y]
            if x < 15:
                grid[x][y].right = grid[x+1][y]
            if y > 0:
                grid[x][y].up = grid[x][y-1]
            if y < 15:
                grid[x][y].down = grid[x][y+1]

    for r, c, side in board.FIXED_WALLS:
        sq = grid[c][r]

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

    return grid


grid = build_grid()

# ============================================
# IMAGE LOADING
# ============================================
def load_img(name, size):
    img = pygame.image.load(ASSETS_DIR / name).convert_alpha()
    return pygame.transform.smoothscale(img, (size, size))


# ============================================
# INIT
# ============================================
pygame.init()
screen = pygame.display.set_mode((1100, 800))
pygame.display.set_caption("Ricochet Robots")
clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 26)

# UI colors
BUTTON_COLOR = (200, 200, 210)
BUTTON_HOVER = (180, 180, 190)
BUTTON_BORDER = (100, 100, 110)

reset_button = pygame.Rect(820, 80, 200, 50)

# ============================================
# LOAD BOARD
# ============================================
board_path = board.generate_board()
board_surface = pygame.image.load(board_path)

# ============================================
# LOAD ASSETS
# ============================================
robot_imgs = {
    "red": load_img("redbot.png", int(CELL * 0.8)),
    "blue": load_img("bluebot.png", int(CELL * 0.8)),
    "green": load_img("greenbot.png", int(CELL * 0.8)),
    "yellow": load_img("yellowbot.png", int(CELL * 0.8)),
}

symbol_imgs = {}
for color in COLORS:
    symbol_imgs[color] = {}
    for t in ["bio", "tar", "tri", "hex"]:
        symbol_imgs[color][t] = load_img(f"{color}{t}.png", int(CELL * 0.6))

# ============================================
# GAME STATE
# ============================================
robots = {}
symbols = []
target = None


def place_symbols():
    global symbols
    symbols = []

    for (color, typ), (r, c) in FIXED_SYMBOLS.items():
        symbols.append({
            "color": color,
            "type": typ,
            "pos": (c, r),
        })


def place_robots():
    global robots
    robots = {}

    occupied = {(c, r) for (_, _), (r, c) in FIXED_SYMBOLS.items()}

    free = [
        (x, y)
        for x in range(GRID_SIZE)
        for y in range(GRID_SIZE)
        if (x, y) not in occupied
        and (x, y) not in [(7,7),(7,8),(8,7),(8,8)]
    ]

    chosen = random.sample(free, 4)

    for color, pos in zip(COLORS, chosen):
        robots[color] = pos


def reset():
    place_robots()
    global target
    target = random.choice(symbols)


place_symbols()
reset()

# ============================================
# HELPERS
# ============================================
def grid_to_pixel(x, y):
    return (
        GRID_ORIGIN + x * CELL + CELL // 2,
        GRID_ORIGIN + y * CELL + CELL // 2,
    )

# ============================================
# DRAW
# ============================================
def draw():
    screen.fill((30, 30, 30))

    screen.blit(board_surface, (0, 0))

    # 🎯 TARGET IN CENTER ONLY
    if target:
        center_x = GRID_ORIGIN + (7.5 * CELL)
        center_y = GRID_ORIGIN + (7.5 * CELL)

        img = symbol_imgs[target["color"]][target["type"]]
        rect = img.get_rect(center=(center_x, center_y))
        screen.blit(img, rect)

    # symbols
    for s in symbols:
        px, py = grid_to_pixel(*s["pos"])
        img = symbol_imgs[s["color"]][s["type"]]
        rect = img.get_rect(center=(px, py))
        screen.blit(img, rect)

    # robots
    for color, pos in robots.items():
        px, py = grid_to_pixel(*pos)
        img = robot_imgs[color]
        rect = img.get_rect(center=(px, py))
        screen.blit(img, rect)

    # UI panel
    pygame.draw.rect(screen, (240, 240, 245), (800, 0, 300, 800))

    mouse_pos = pygame.mouse.get_pos()

    title = font.render("Ricochet Robots", True, (0, 0, 0))
    screen.blit(title, (820, 20))

    # button
    if reset_button.collidepoint(mouse_pos):
        pygame.draw.rect(screen, BUTTON_HOVER, reset_button, border_radius=8)
    else:
        pygame.draw.rect(screen, BUTTON_COLOR, reset_button, border_radius=8)

    pygame.draw.rect(screen, BUTTON_BORDER, reset_button, 2, border_radius=8)

    btn_text = font.render("Reset Robots", True, (0, 0, 0))
    screen.blit(btn_text, btn_text.get_rect(center=reset_button.center))

    txt = font.render("Press R to reload", True, (80, 80, 80))
    screen.blit(txt, (820, 150))


# ============================================
# LOOP
# ============================================
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                reset()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if reset_button.collidepoint(event.pos):
                reset()

    draw()
    pygame.display.flip()
    clock.tick(60)