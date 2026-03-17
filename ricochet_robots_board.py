"""
Ricochet Robots - Board Generator
Generates a 16x16 board closely matching the classic physical game aesthetic.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Board configuration ────────────────────────────────────────────────────
GRID_SIZE    = 16
CELL         = 46          # pixels per cell
LABEL_MARGIN = 24          # margin around grid for row/col labels
BORDER_W     = 18          # thick outer border width
IMG_SIZE = 2 * LABEL_MARGIN + 2 * BORDER_W + GRID_SIZE * CELL
GRID_ORIGIN  = LABEL_MARGIN + BORDER_W  # pixel where the grid starts

# ── Colour palette ─────────────────────────────────────────────────────────
CELL_COLOR        = (235, 232, 210)   # warm off-white cell fill
CELL_BEVEL_LIGHT  = (255, 255, 248)   # top/left bevel highlight
CELL_BEVEL_DARK   = (190, 185, 165)   # bottom/right bevel shadow
BORDER_OUTER      = (50,  50,  50)    # very dark grey outer frame
BORDER_INNER      = (80,  80,  80)    # slightly lighter inner edge
BORDER_HIGHLIGHT  = (110, 110, 110)   # bevel on border face
GRID_LINE_COLOR   = (180, 176, 155)   # subtle grid line
CENTER_COLOR      = (65,  65,  65)    # dark grey centre zone
CENTER_HIGHLIGHT  = (90,  90,  90)
WALL_COLOR        = (50,  50,  50)    # inner wall segments

# Wall segment covers ~65% of a cell edge
WALL_COVERAGE = 1.0
WALL_THICKNESS = 5


# ── Wall definitions ───────────────────────────────────────────────────────
# (row, col, side)  — side ∈ N S E W
# Walls are drawn on the inside edge of the named cell.
# Each L-wall = two perpendicular line segments meeting at a corner.
FIXED_WALLS = [

    # Single Walls -------------------------------------------------------

    # Row 1, between C & D (East wall of C1)
    (0,  2, "E"),
    # Row 1, between I & J
    (0,  8, "E"),
    # Row 16, between F & G
    (15, 5, "E"),
    # Row 16, between L & M
    (15, 11, "E"),
    # Column 1, betweek 4 & 5
    (3,  0, "S"),   # S of A4 (horizontal, touches left border)
    # Column 1, betweek 11 & 12
    (10, 0, "S"),   # S of A11
    # Column 15, betweek 2 & 3
    (1, 15, "S"),   # N of O3 (horizontal, touches right border)
    # Column 15, betweek 10 & 11
    (9, 15, "S"),   # N of O10

    # L-walls -------------------------------------------------------

    # L-bracket at F/G cols, rows 2-3: vertical between F&G at row2, horizontal below G row2
    (1,  5, "W"),
    (1,  5, "S"),

    # L-bracket at H/I cols, rows 3-4: horizontal below I row3, vertical between H&I at row3
    (1,  11, "N"),
    (1,  11, "W"),

    # L-bracket at A/B cols, rows 4-5: horizontal below A row4, vertical between A&B at row4
    (2,  7, "S"),
    (2,  7, "E"),

    # L-bracket at E/F cols, rows 5-6: vertical between E&F at row5, horizontal below E row5
    (3,  14, "E"),
    (3,  14, "N"),

    # L-bracket at C/D cols, rows 6: vertical between C&D row6, horizontal below C row6
    (4,  3, "E"),
    (4,  3, "S"),

    # L-bracket at G/H cols, rows 6-7: horizontal below G row6, vertical between G&H row7
    (4,  9, "S"),
    (4,  9, "E"),

    # L-bracket at J/K cols, rows 4-5: vertical between J&K at row4, horizontal below J row4
    (5,  6, "W"),
    (5,  6, "N"),

    # L-bracket at L/M cols, rows 2: vertical between L&M row2, horizontal below L row2
    (6, 1, "E"),
    (6, 1, "N"),

    # L-bracket at N/O cols, rows 3-4: vertical between N&O rows 3-4, horizontal above O row4
    (6, 12, "W"),
    (6, 12, "S"),

    # L-bracket at B/C cols, rows 9-10: vertical between B&C row10, horizontal below B row10
    (9,  1, "E"),
    (9,  1, "N"),

    # L-bracket at B/C cols, rows 6-7: vertical between B&C row6-7, horizontal below B row7
    (9,  5, "W"),
    (9,  5, "N"),

    # L-bracket at L/M cols, rows 7: vertical between L&M row7, horizontal below L row7
    (10, 8, "E"),
    (10, 8, "S"),

    # L-bracket at M/N cols, rows 7-8: horizontal above N row8, vertical between M&N row7
    (11, 13, "W"),
    (11, 13, "N"),

    # Row 11, between A&B (touches left border): horizontal S of A11
    (12, 6, "S"),
    (12, 6, "E"),

    # L-bracket at F/G cols, rows 9-10: vertical between F&G row9, horizontal below F row9
    (13,  9, "W"),
    (13,  9, "S"),

    # L-bracket at J/K cols, rows 11: horizontal below J row11, vertical between J&K row11
    (14, 2, "S"),
    (14, 2, "W"),

    # Row 14, between O&P (touches right border): horizontal S of P10
    (14, 14, "N"),
    (14, 14, "E"),
]


# ── Helpers ────────────────────────────────────────────────────────────────

def cell_rect(r, c):
    x0 = GRID_ORIGIN + c * CELL
    y0 = GRID_ORIGIN + r * CELL
    return x0, y0, x0 + CELL, y0 + CELL


def draw_beveled_cell(draw, r, c):
    x0, y0, x1, y1 = cell_rect(r, c)
    draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=CELL_COLOR)
    draw.line([(x0, y0), (x1 - 1, y0)], fill=CELL_BEVEL_LIGHT, width=1)
    draw.line([(x0, y0), (x0, y1 - 1)], fill=CELL_BEVEL_LIGHT, width=1)
    draw.line([(x0, y1 - 1), (x1 - 1, y1 - 1)], fill=CELL_BEVEL_DARK, width=1)
    draw.line([(x1 - 1, y0), (x1 - 1, y1 - 1)], fill=CELL_BEVEL_DARK, width=1)


def draw_wall(draw, r, c, side):
    """Draw a thick wall segment covering WALL_COVERAGE of the cell edge."""
    x0, y0, x1, y1 = cell_rect(r, c)
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    half = (CELL * WALL_COVERAGE) / 2
    wt = WALL_THICKNESS
    if side == "N":
        draw.line([(cx - half, y0), (cx + half, y0)], fill=WALL_COLOR, width=wt)
    elif side == "S":
        draw.line([(cx - half, y1), (cx + half, y1)], fill=WALL_COLOR, width=wt)
    elif side == "W":
        draw.line([(x0, cy - half), (x0, cy + half)], fill=WALL_COLOR, width=wt)
    elif side == "E":
        draw.line([(x1, cy - half), (x1, cy + half)], fill=WALL_COLOR, width=wt)


def draw_outer_border(draw):
    g0 = GRID_ORIGIN
    g1 = GRID_ORIGIN + GRID_SIZE * CELL
    # Four border bands
    for bx0, by0, bx1, by1 in [
        (g0 - BORDER_W, g0 - BORDER_W, g1 + BORDER_W, g0 - 1),
        (g0 - BORDER_W, g1 + 1,        g1 + BORDER_W, g1 + BORDER_W),
        (g0 - BORDER_W, g0,            g0 - 1,         g1),
        (g1 + 1,        g0,            g1 + BORDER_W,  g1),
    ]:
        draw.rectangle([bx0, by0, bx1, by1], fill=BORDER_OUTER)
    # Outer highlight ring
    inset = 3
    draw.rectangle(
        [g0 - BORDER_W + inset, g0 - BORDER_W + inset,
         g1 + BORDER_W - inset, g1 + BORDER_W - inset],
        outline=BORDER_HIGHLIGHT, width=2
    )
    # Inner border edge
    draw.rectangle([g0 - 2, g0 - 2, g1 + 2, g1 + 2],
                   outline=BORDER_INNER, width=3)


# ── Main generator ─────────────────────────────────────────────────────────

def generate_board(output_path=None):
    if output_path is None:
        output_path = Path(__file__).parent / "Ricochet_Robots_board.png"
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), (25, 25, 25))
    draw = ImageDraw.Draw(img)

    g0 = GRID_ORIGIN
    g1 = GRID_ORIGIN + GRID_SIZE * CELL

    # Draw all cells with bevel
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            draw_beveled_cell(draw, r, c)

    # Grid lines
    for i in range(1, GRID_SIZE):
        x = g0 + i * CELL
        y = g0 + i * CELL
        draw.line([(x, g0), (x, g1)], fill=GRID_LINE_COLOR, width=1)
        draw.line([(g0, y), (g1, y)], fill=GRID_LINE_COLOR, width=1)

    # Centre 2×2 zone (rows 7–8, cols 7–8)
    cx0, cy0, _, _ = cell_rect(7, 7)
    _, _, cx1, cy1 = cell_rect(8, 8)
    draw.rectangle([cx0, cy0, cx1, cy1], fill=CENTER_COLOR)
    draw.rectangle([cx0, cy0, cx1, cy1], outline=CENTER_HIGHLIGHT, width=2)

    # Inner walls
    for (r, c, side) in FIXED_WALLS:
        if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE:
            draw_wall(draw, r, c, side)

    # Outer border
    draw_outer_border(draw)

    # Labels
    font = ImageFont.load_default(size=15)
    label_col = (190, 190, 190)
    for i in range(GRID_SIZE):
        cc = g0 + i * CELL + CELL // 2
        col_label = chr(ord("A") + i)
        draw.text((cc, LABEL_MARGIN // 2 + 2),         col_label, fill=label_col, anchor="mm", font=font)
        draw.text((cc, IMG_SIZE - LABEL_MARGIN // 2),   col_label, fill=label_col, anchor="mm", font=font)
        draw.text((LABEL_MARGIN // 2, cc),               str(i + 1), fill=label_col, anchor="mm", font=font)
        draw.text((IMG_SIZE - LABEL_MARGIN // 2, cc),    str(i + 1), fill=label_col, anchor="mm", font=font)

    img.save(output_path)
    print(f"Board saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_board()
