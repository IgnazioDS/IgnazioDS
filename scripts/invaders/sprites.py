"""Pixel-art assets: classic invader sprites, cannon, UFO, shield, explosion,
and a 3x5 pixel font. All bitmaps are strings of '.'/'X' rows.

Sprites are converted to SVG rects with horizontal run-length merging so a
22x16 shield costs ~30 rects instead of ~300.
"""

SQUID_A = [
    "...XX...",
    "..XXXX..",
    ".XXXXXX.",
    "XX.XX.XX",
    "XXXXXXXX",
    "..X..X..",
    ".X.XX.X.",
    "X.X..X.X",
]
SQUID_B = [
    "...XX...",
    "..XXXX..",
    ".XXXXXX.",
    "XX.XX.XX",
    "XXXXXXXX",
    ".X.XX.X.",
    "X......X",
    ".X....X.",
]
CRAB_A = [
    "..X.....X..",
    "...X...X...",
    "..XXXXXXX..",
    ".XX.XXX.XX.",
    "XXXXXXXXXXX",
    "X.XXXXXXX.X",
    "X.X.....X.X",
    "...XX.XX...",
]
CRAB_B = [
    "..X.....X..",
    "X..X...X..X",
    "X.XXXXXXX.X",
    "XXX.XXX.XXX",
    "XXXXXXXXXXX",
    ".XXXXXXXXX.",
    "..X.....X..",
    ".X.......X.",
]
OCTO_A = [
    "....XXXX....",
    ".XXXXXXXXXX.",
    "XXXXXXXXXXXX",
    "XXX..XX..XXX",
    "XXXXXXXXXXXX",
    "...XX..XX...",
    "..XX.XX.XX..",
    "XX........XX",
]
OCTO_B = [
    "....XXXX....",
    ".XXXXXXXXXX.",
    "XXXXXXXXXXXX",
    "XXX..XX..XXX",
    "XXXXXXXXXXXX",
    "..XXX..XXX..",
    ".XX..XX..XX.",
    "..XX....XX..",
]
CANNON = [
    "......X......",
    ".....XXX.....",
    ".....XXX.....",
    ".XXXXXXXXXXX.",
    "XXXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
]
UFO = [
    ".....XXXXXX.....",
    "...XXXXXXXXXX...",
    "..XXXXXXXXXXXX..",
    ".XX.XX.XX.XX.XX.",
    "XXXXXXXXXXXXXXXX",
    "..XXX..XX..XXX..",
    "....X......X....",
]
BOOM = [
    "X..X.X.X..X",
    ".X..X.X..X.",
    "..X.....X..",
    "X....X....X",
    "..X.....X..",
    ".X..X.X..X.",
    "X..X.X.X..X",
]
SHIELD = [
    "....XXXXXXXXXXXXXX....",
    "...XXXXXXXXXXXXXXXX...",
    "..XXXXXXXXXXXXXXXXXX..",
    ".XXXXXXXXXXXXXXXXXXXX.",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXXXXXXXXXXXXXXXX",
    "XXXXXXXX......XXXXXXXX",
    "XXXXXXX........XXXXXXX",
    "XXXXXX..........XXXXXX",
    "XXXXXX..........XXXXXX",
]

# Row 0: squid, rows 1-2: crab, rows 3-4: octopus. (frame_a, frame_b, points)
INVADER_ROWS = (
    (SQUID_A, SQUID_B, 30),
    (CRAB_A, CRAB_B, 20),
    (CRAB_A, CRAB_B, 20),
    (OCTO_A, OCTO_B, 10),
    (OCTO_A, OCTO_B, 10),
)

FONT_3X5 = {
    "A": ("010", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "C": ("011", "100", "100", "100", "011"),
    "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"),
    "F": ("111", "100", "110", "100", "100"),
    "G": ("011", "100", "101", "101", "011"),
    "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"),
    "J": ("001", "001", "001", "101", "010"),
    "K": ("101", "101", "110", "101", "101"),
    "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"),
    "N": ("110", "101", "101", "101", "101"),
    "O": ("010", "101", "101", "101", "010"),
    "P": ("110", "101", "110", "100", "100"),
    "Q": ("010", "101", "101", "110", "011"),
    "R": ("110", "101", "110", "101", "101"),
    "S": ("011", "100", "010", "001", "110"),
    "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"),
    "V": ("101", "101", "101", "101", "010"),
    "W": ("101", "101", "111", "111", "101"),
    "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"),
    "Z": ("111", "001", "010", "100", "111"),
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "011", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "-": ("000", "000", "111", "000", "000"),
    "=": ("000", "111", "000", "111", "000"),
    "+": ("000", "010", "111", "010", "000"),
    " ": ("000", "000", "000", "000", "000"),
}


def sprite_runs(bitmap):
    """Run-length encode a bitmap into (x, y, width) horizontal runs."""
    runs = []
    for y, row in enumerate(bitmap):
        x = 0
        while x < len(row):
            if row[x] == "X":
                start = x
                while x < len(row) and row[x] == "X":
                    x += 1
                runs.append((start, y, x - start))
            else:
                x += 1
    return tuple(runs)


def sprite_size(bitmap):
    return (len(bitmap[0]), len(bitmap))


def sprite_rects(bitmap, px=1.0):
    """SVG rect elements for a bitmap at pixel scale `px` (fill inherited)."""
    parts = [
        f'<rect x="{run_x * px:g}" y="{run_y * px:g}" width="{w * px:g}" height="{px:g}"/>'
        for run_x, run_y, w in sprite_runs(bitmap)
    ]
    return "".join(parts)


def text_rects(text, px=1.0):
    """Render a string with the 3x5 font as merged rects. Advance = 4 font px."""
    rows = ["".join(_glyph_row(ch, r) for ch in text.upper()) for r in range(5)]
    return sprite_rects(rows, px)


def text_width(text, px=1.0):
    return len(text) * 4 * px


def _glyph_row(ch, row):
    glyph = FONT_3X5.get(ch.upper(), FONT_3X5[" "])
    return glyph[row].replace("1", "X").replace("0", ".") + "."
