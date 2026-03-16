from __future__ import annotations

"This file contains the code for the game board"

"Game board is a 16 x 16 grid of tiles, each tile can be empty, be surrounded by a wall from one or two sides, a player (robot), or a goal"

"""
Ricochet Robots board generator.

Purpose:
- generates only the board layout
- does not place robots or play the game
- saves a PNG preview so you can inspect the layout
- can load the old `.map` format from the existing codebase
- can also be edited directly in Python for custom layouts

Usage examples:
    python3 board_generator.py
    python3 board_generator.py --map first.map --out generated_boards --name board_from_map.png

Later, you can import Board from this file in your robot / AI code.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
import argparse

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Pillow is required. Install it with: pip install pillow"
    ) from exc

Coord = Tuple[int, int]
Wall = Tuple[int, int, str]  # (x, y, direction)

DIRECTIONS = {"left", "right", "up", "down"}
OPPOSITE = {"left": "right", "right": "left", "up": "down", "down": "up"}
DELTAS = {
    "left": (-1, 0),
    "right": (1, 0),
    "up": (0, -1),
    "down": (0, 1),
}

COLOR_MAP = {
    "red": (220, 50, 47),
    "blue": (38, 139, 210),
    "green": (133, 153, 0),
    "yellow": (181, 137, 0),
    "purple": (108, 113, 196),
    "black": (40, 40, 40),
    "gray": (120, 120, 120),
}

SYMBOL_LABELS = {
    "bio": "B",
    "hex": "H",
    "tar": "*",
    "tri": "T",
    "vortex": "V",
}


@dataclass
class Target:
    x: int
    y: int
    color: str
    shape: str


@dataclass
class Board:
    size: int = 16
    walls: Set[Wall] = field(default_factory=set)
    blocked_cells: Set[Coord] = field(default_factory=set)
    targets: List[Target] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError("Board size must be positive.")

    # ---------- editing helpers ----------
    def add_wall(self, x: int, y: int, direction: str, bidirectional: bool = True) -> None:
        self._validate_cell(x, y)
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of {sorted(DIRECTIONS)}")

        self.walls.add((x, y, direction))

        if bidirectional:
            dx, dy = DELTAS[direction]
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                self.walls.add((nx, ny, OPPOSITE[direction]))

    def remove_wall(self, x: int, y: int, direction: str, bidirectional: bool = True) -> None:
        self.walls.discard((x, y, direction))
        if bidirectional and direction in DIRECTIONS:
            dx, dy = DELTAS[direction]
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.size and 0 <= ny < self.size:
                self.walls.discard((nx, ny, OPPOSITE[direction]))

    def add_blocked_cell(self, x: int, y: int) -> None:
        self._validate_cell(x, y)
        self.blocked_cells.add((x, y))

    def add_target(self, x: int, y: int, color: str, shape: str) -> None:
        self._validate_cell(x, y)
        self.targets.append(Target(x=x, y=y, color=color, shape=shape))

    # ---------- loading ----------
    @classmethod
    def from_map_file(cls, map_path: str | Path, size: int = 16) -> "Board":
        """
        Load the legacy `.map` format used by the old project.

        Expected line format:
            (x, y) left right up down redbot bluebot greenbot yellowbot ...targets...

        We only use the first 4 wall flags and the target flags.
        Robot flags are ignored because this file only generates boards.
        """
        board = cls(size=size)
        map_path = Path(map_path)
        if not map_path.exists():
            raise FileNotFoundError(f"Map file not found: {map_path}")

        # outer border walls
        board._add_outer_boundary_walls()

        flag_to_target = {
            10: ("red", "bio"),
            11: ("red", "hex"),
            12: ("red", "tar"),
            13: ("red", "tri"),
            14: ("blue", "bio"),
            15: ("blue", "hex"),
            16: ("blue", "tar"),
            17: ("blue", "tri"),
            18: ("green", "bio"),
            19: ("green", "hex"),
            20: ("green", "tar"),
            21: ("green", "tri"),
            22: ("yellow", "bio"),
            23: ("yellow", "hex"),
            24: ("yellow", "tar"),
            25: ("yellow", "tri"),
        }

        for raw_line in map_path.read_text().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            numbers = [int(tok) for tok in line.replace("(", " ").replace(")", " ").replace(",", " ").split()]
            if len(numbers) < 6:
                continue

            x, y = numbers[0], numbers[1]
            left, right, up, down = numbers[2], numbers[3], numbers[4], numbers[5]

            if left:
                board.add_wall(x, y, "left", bidirectional=True)
            if right:
                board.add_wall(x, y, "right", bidirectional=True)
            if up:
                board.add_wall(x, y, "up", bidirectional=True)
            if down:
                board.add_wall(x, y, "down", bidirectional=True)

            for idx, (color, shape) in flag_to_target.items():
                if idx < len(numbers) and numbers[idx] == 1:
                    board.add_target(x, y, color, shape)

        # center 2x2 blocked zone used in Ricochet Robots
        for coord in [(7, 7), (7, 8), (8, 7), (8, 8)]:
            board.add_blocked_cell(*coord)

        board.metadata["source_map"] = str(map_path)
        return board

    @classmethod
    def default_empty_board(cls, size: int = 16) -> "Board":
        board = cls(size=size)
        board._add_outer_boundary_walls()
        for coord in [(7, 7), (7, 8), (8, 7), (8, 8)]:
            board.add_blocked_cell(*coord)
        return board

    # ---------- rendering ----------
    def save_png(
        self,
        output_path: str | Path,
        cell_size: int = 48,
        margin: int = 28,
        show_grid_coords: bool = False,
        title: Optional[str] = None,
    ) -> Path:
        from pathlib import Path
        script_dir = Path(__file__).parent
        output_path = script_dir / "generated_boards" / "board_layout.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        board_px = self.size * cell_size
        extra_top = 36 if title else 0
        img_w = board_px + 2 * margin
        img_h = board_px + 2 * margin + extra_top

        bg = (248, 248, 245)
        grid_bg = (255, 255, 255)
        wall_color = (190, 30, 45)
        blocked_fill = (70, 70, 70)
        thin_grid = (222, 222, 222)
        text_color = (20, 20, 20)

        image = Image.new("RGB", (img_w, img_h), bg)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        ox = margin
        oy = margin + extra_top

        if title:
            draw.text((margin, 10), title, fill=text_color, font=font)

        # board background
        draw.rectangle([ox, oy, ox + board_px, oy + board_px], fill=grid_bg, outline=(0, 0, 0), width=2)

        # light grid
        for i in range(1, self.size):
            x = ox + i * cell_size
            y = oy + i * cell_size
            draw.line((x, oy, x, oy + board_px), fill=thin_grid, width=1)
            draw.line((ox, y, ox + board_px, y), fill=thin_grid, width=1)

        # blocked cells
        for x, y in sorted(self.blocked_cells):
            x0, y0, x1, y1 = self._cell_box(x, y, cell_size, ox, oy)
            draw.rectangle([x0, y0, x1, y1], fill=blocked_fill)

        # targets
        for target in self.targets:
            self._draw_target(draw, target, cell_size, ox, oy, font)

        # walls
        wall_width = max(3, cell_size // 10)
        for x, y, direction in sorted(self.walls):
            x0, y0, x1, y1 = self._cell_box(x, y, cell_size, ox, oy)
            if direction == "left":
                draw.line((x0, y0, x0, y1), fill=wall_color, width=wall_width)
            elif direction == "right":
                draw.line((x1, y0, x1, y1), fill=wall_color, width=wall_width)
            elif direction == "up":
                draw.line((x0, y0, x1, y0), fill=wall_color, width=wall_width)
            elif direction == "down":
                draw.line((x0, y1, x1, y1), fill=wall_color, width=wall_width)

        if show_grid_coords:
            for x in range(self.size):
                for y in range(self.size):
                    if (x, y) in self.blocked_cells:
                        continue
                    tx = ox + x * cell_size + 4
                    ty = oy + y * cell_size + 3
                    draw.text((tx, ty), f"{x},{y}", fill=(130, 130, 130), font=font)

        image.save(output_path)
        return output_path

    # ---------- internal helpers ----------
    def _cell_box(self, x: int, y: int, cell_size: int, ox: int, oy: int) -> Tuple[int, int, int, int]:
        x0 = ox + x * cell_size
        y0 = oy + y * cell_size
        x1 = x0 + cell_size
        y1 = y0 + cell_size
        return x0, y0, x1, y1

    def _draw_target(
        self,
        draw: ImageDraw.ImageDraw,
        target: Target,
        cell_size: int,
        ox: int,
        oy: int,
        font: ImageFont.ImageFont,
    ) -> None:
        x0, y0, x1, y1 = self._cell_box(target.x, target.y, cell_size, ox, oy)
        pad = max(6, cell_size // 6)
        color = COLOR_MAP.get(target.color, (90, 90, 90))
        shape = target.shape

        if shape == "bio":  # circle
            draw.ellipse((x0 + pad, y0 + pad, x1 - pad, y1 - pad), outline=color, width=3)
        elif shape == "hex":
            mx = (x0 + x1) // 2
            my = (y0 + y1) // 2
            rx = (cell_size - 2 * pad) // 2
            ry = int(rx * 0.9)
            points = [
                (mx - rx // 2, my - ry),
                (mx + rx // 2, my - ry),
                (mx + rx, my),
                (mx + rx // 2, my + ry),
                (mx - rx // 2, my + ry),
                (mx - rx, my),
            ]
            draw.polygon(points, outline=color, width=3)
        elif shape == "tri":
            draw.polygon(
                [(x0 + (x1 - x0) // 2, y0 + pad), (x1 - pad, y1 - pad), (x0 + pad, y1 - pad)],
                outline=color,
                width=3,
            )
        elif shape == "tar":
            cx = (x0 + x1) // 2
            cy = (y0 + y1) // 2
            r = (cell_size - 2 * pad) // 2
            draw.line((cx - r, cy, cx + r, cy), fill=color, width=3)
            draw.line((cx, cy - r, cx, cy + r), fill=color, width=3)
            draw.ellipse((cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2), outline=color, width=2)
        else:
            label = SYMBOL_LABELS.get(shape, shape[:1].upper())
            draw.text((x0 + pad, y0 + pad), label, fill=color, font=font)

    def _validate_cell(self, x: int, y: int) -> None:
        if not (0 <= x < self.size and 0 <= y < self.size):
            raise ValueError(f"Cell {(x, y)} is outside a {self.size}x{self.size} board.")

    def _add_outer_boundary_walls(self) -> None:
        for i in range(self.size):
            self.add_wall(0, i, "left", bidirectional=False)
            self.add_wall(self.size - 1, i, "right", bidirectional=False)
            self.add_wall(i, 0, "up", bidirectional=False)
            self.add_wall(i, self.size - 1, "down", bidirectional=False)


# ---------- example custom builder ----------
def build_custom_board() -> Board:
    """
    Example of direct Python configuration.
    Edit this function to change the board without touching any other code.
    """
    board = Board.default_empty_board(size=16)

    # Example internal walls.
    board.add_wall(2, 2, "right")
    board.add_wall(2, 2, "down")
    board.add_wall(5, 4, "right")
    board.add_wall(5, 4, "down")
    board.add_wall(10, 10, "right")
    board.add_wall(10, 10, "up")
    board.add_wall(14, 14, "left")
    board.add_wall(14, 14, "up")

    # Example targets.
    board.add_target(2, 2, "red", "bio")
    board.add_target(5, 4, "blue", "hex")
    board.add_target(10, 10, "green", "tar")
    board.add_target(14, 14, "yellow", "tri")

    board.metadata["source"] = "custom_python_config"
    return board


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and save a Ricochet Robots board PNG.")
    parser.add_argument("--map", dest="map_path", default=None, help="Optional legacy .map file to load.")
    parser.add_argument("--out", dest="out_dir", default="generated_boards", help="Output folder for the PNG.")
    parser.add_argument("--name", dest="file_name", default="board_layout.png", help="PNG file name.")
    parser.add_argument("--cell-size", dest="cell_size", type=int, default=48, help="Pixel size of one cell.")
    parser.add_argument("--coords", dest="show_coords", action="store_true", help="Draw cell coordinates.")
    args = parser.parse_args()

    if args.map_path:
        board = Board.from_map_file(args.map_path)
        title = f"Board preview from {Path(args.map_path).name}"
    else:
        board = build_custom_board()
        title = "Board preview from Python config"

    output_path = Path(args.out_dir) / args.file_name
    saved = board.save_png(
        output_path=output_path,
        cell_size=args.cell_size,
        show_grid_coords=args.show_coords,
        title=title,
    )
    print(f"Saved board PNG to: {saved.resolve()}")


if __name__ == "__main__":
    main()
