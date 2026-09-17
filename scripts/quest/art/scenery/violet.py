"""Region I: the Violet Moor.

Dusk sinking into night. A crescent moon and the first stars over a bruised
violet sky; a band of peach light on the horizon that backlights the knight;
a gothic keep with burning windows on a far hill; a cliff where a waterfall
spills into a small lake that holds the last of the glow; cypress groves, a
ruined arch and standing stones; and a lavender moor crossed by a worn
flagstone path.
"""

import random

from .. import raster
from . import TITLES, Layer, Light, Motif, RegionArt, common, motifs, paint

C = raster.rgb
TILE = 830

SKY = (
    (0, C("#0c091d")), (38, C("#161030")), (76, C("#241747")), (108, C("#3a2160")),
    (132, C("#562a6e")), (150, C("#7c3877")), (164, C("#a64c7b")), (176, C("#cd677c")),
    (188, C("#e8867e")), (202, C("#f2a283")), (240, C("#f5b489")),
)
WARM_CLOUD = (C("#6a3272"), C("#9a4478"), C("#e0787c"), C("#ffb08e"))
COOL_CLOUD = (C("#2e1f4c"), C("#48296a"), C("#7a3c7a"), C("#b8587e"))


def sky():
    canvas = raster.Canvas(415, 240)
    paint.gradient(canvas, SKY)
    common.stars(canvas, 120, "violet-3", 3, 104, C("#6b5a9a"), C("#efe6ff"))
    common.halo(canvas, 334, 50, 13, 38, C("#2c1f50"))
    common.halo(canvas, 334, 50, 13, 25, C("#40306a"))
    common.moon(canvas, 334, 50, 13, C("#fbf0dc"), C("#d8c2ae"), C("#ecdcc6"), phase_offset=(-6, -3))
    rng = random.Random("violet-3-clouds")
    for i in range(10):
        y = rng.randrange(66, 156)
        ramp = WARM_CLOUD if y > 118 else COOL_CLOUD
        paint.cumulus(canvas, rng.randrange(-20, 435), y, rng.randrange(36, 118), rng.randrange(4, 10), ramp, f"v3-{i}")
    return canvas.freeze()


def far():
    """Hazy ranges low on the horizon and the keep on its hill (screen y 40-200)."""
    canvas = raster.Canvas(TILE, 160, wrap_x=True)
    distant = common.ridge_heights(TILE, "violet-3-distant", base=142, amplitude=20, base_cells=6)
    paint.rim_ridge(canvas, distant, C("#b85e80"), C("#e58c8a"))
    back = common.ridge_heights(TILE, "violet-3-back", base=156, amplitude=18, base_cells=5)
    paint.rim_ridge(canvas, back, C("#8e4a7c"), C("#c26c88"))
    common.haze(canvas, 134, 160, C("#c26a82"), density=0.35)
    paint.crag(canvas, 522, 160, 150, 44, C("#43275a"), C("#7a4476"), C("#34204a"), "violet-keep")
    road = [(470, 158), (500, 150), (478, 140), (512, 132), (518, 124)]
    for (x1, y1), (x2, y2) in zip(road, road[1:]):
        canvas.line(x1, y1, x2, y2, C("#5e3a66"))
    paint.gothic_castle(canvas, 522, 122, C("#2c1a40"), C("#5e3466"), C("#ffc46a"), C("#c4364e"),
                        "violet", height_scale=0.78)
    return canvas.freeze()


FALLS = (C("#6c8fd0"), C("#9cc8ee"), C("#e0f2ff"), C("#f4f8ff"))


def cliffs():
    """A rugged cliff with a waterfall feeding a lake that mirrors the glow (screen y 100-210)."""
    canvas = raster.Canvas(TILE, 110, wrap_x=True)
    outline = [(46, 110), (52, 74), (60, 58), (68, 52), (76, 40), (86, 34), (96, 38), (104, 30),
               (114, 36), (124, 34), (134, 44), (146, 50), (156, 64), (166, 82), (172, 110)]
    for y in range(28, 110):
        shade = C("#4a2d61") if y < 56 else C("#3a2352") if y < 80 else C("#2c1a42")
        for x in range(40, 180):
            if _inside(outline, x + 0.5, y + 0.5):
                canvas.put(x, y, shade if paint.bayer(x, y) > 0.12 else C("#2c1a42"))
    for (x1, y1), (x2, y2) in zip(outline[1:-2], outline[2:-1]):
        canvas.line(x1, y1, x2, y2, C("#8a4d82"))
    rng = random.Random("violet-3-ledges")
    for _ in range(9):
        lx, ly = rng.randrange(62, 158), rng.randrange(48, 92)
        if _inside(outline, lx, ly) and _inside(outline, lx + 6, ly):
            canvas.line(lx, ly, lx + rng.randint(4, 9), ly, C("#6a3d76"))
            canvas.line(lx, ly + 1, lx + rng.randint(3, 8), ly + 1, C("#24163a"))
    _lake(canvas, 12, 236, 80, 94)
    paint.waterfall(canvas, 108, 32, 82, 7, FALLS, 7)
    return canvas.freeze()


def _inside(points, px, py):
    inside = False
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def _lake(canvas, x0, x1, y0, y1):
    for y in range(y0, y1):
        f = (y - y0) / (y1 - y0)
        for x in range(x0, x1):
            edge = min(x - x0, x1 - x) / 14
            if edge < paint.bayer(x, y) * 0.8:
                continue
            color = C("#e08a86") if f < 0.25 else C("#b85f80") if f < 0.6 else C("#7a3e76")
            if (y - y0) % 3 == 1 and (x * 7 + y * 13) % 11 < 4:
                color = C("#5a2e62")
            if f < 0.35 and (x * 5 + y) % 17 == 0:
                color = C("#ffd2a8")
            canvas.put(x, y, color)


def mid():
    """Rolling moor with cypress groves, standing stones and a ruined arch (screen y 140-240)."""
    canvas = raster.Canvas(TILE, 100, wrap_x=True)
    hills = common.ridge_heights(TILE, "violet-3-mid", base=62, amplitude=9, base_cells=4)
    paint.rim_ridge(canvas, hills, C("#271838"), C("#553468"))
    body, rim = C("#1c1030"), C("#43295c")
    rng = random.Random("violet-3-groves")
    for gx in (26, 160, 318, 468, 574, 742):
        for k in range(rng.randint(2, 5)):
            x = gx + k * rng.randint(5, 9)
            ground = round(hills[x % TILE]) + 2
            if rng.random() < 0.65:
                paint.cypress(canvas, x, ground, rng.randint(22, 44), body, rim)
            else:
                paint.pine_tree(canvas, x, ground, rng.randint(16, 32), body, rim, f"{gx}-{k}")
    paint.standing_stones(canvas, 392, round(hills[402]) + 3, C("#2a1c3e"), C("#5e4674"), "violet")
    paint.ruined_arch(canvas, 648, round(hills[660]) + 3, C("#2c1e42"), C("#604878"), C("#1e1430"))
    return canvas.freeze()


def field():
    """Lavender mounds, a flagstone path and a dense flowering foreground (screen y 196-240)."""
    canvas = raster.Canvas(TILE, 44, wrap_x=True)
    lavender = (C("#6a42a0"), C("#8a5cc4"), C("#b48ae8"), C("#d9c0ff"))
    canvas.rect(0, 8, TILE, 4, C("#1e1330"))
    paint.bushes(canvas, 11, 0, TILE, C("#2a1b40"), C("#3d2a58"), lavender, "violet-back", 7, 16, 3, 9)
    paint.dirt_path(canvas, 12, 26, C("#241a34"), C("#2e2342"), C("#32284a"), C("#4a3f62"), C("#170f24"),
                    C("#2a1c3e"), "violet")
    canvas.rect(0, 26, TILE, 18, C("#1a1028"))
    paint.bushes(canvas, 43, 0, TILE, C("#24173a"), C("#3a2856"), lavender, "violet-front", 8, 18, 6, 14)
    return canvas.freeze()


def front():
    """Sparse tall stalks drawn over the actors at the bottom edge (screen y 208-240)."""
    canvas = raster.Canvas(TILE, 32, wrap_x=True)
    rng = random.Random("violet-3-front")
    x = 20
    while x < TILE:
        for _ in range(rng.randint(5, 10)):
            bx = x + rng.randint(-8, 8)
            height = rng.randint(8, 26)
            paint.blade(canvas, bx, 31, height, rng.randint(-4, 4), C("#120a1c"), C("#2e1f44"))
            if rng.random() < 0.3:
                canvas.put(bx + rng.randint(-1, 1), 31 - height - 1, C("#8a5ec4"))
        x += rng.randint(70, 130)
    return canvas.freeze()


def build():
    return RegionArt(
        key="violet",
        title=TITLES["violet"],
        layers=(
            Layer("sky", sky(), 0, 0.0),
            Layer("far", far(), 40, 0.08, offset=-250),
            Layer("cliffs", cliffs(), 100, 0.2, offset=-30),
            Layer("mid", mid(), 140, 0.45),
            Layer("field", field(), 196, 1.0),
            Layer("front", front(), 208, 1.25, front=True),
        ),
        lights=(
            Light(334, 50, 42, 42, "#fbe7cf", 0.16),
            Light(207, 184, 250, 42, "#ffae88", 0.12),
            Light(270, 132, 34, 22, "#ffb85c", 0.2, parallax=0.08, flicker="pulse"),
            Light(82, 182, 22, 9, "#e6f3ff", 0.3, parallax=0.2),
        ),
        particles=(C("#ffe9a8"), C("#ffd0f0"), C("#d2b0ff")),
        motion="drift",
        motifs=(
            Motif("falls", motifs.waterfall_flow(7, 50, FALLS), 77, 132, parallax=0.2, fps=10),
            Motif("bats", motifs.flock(5, (60, 22), C("#120a1c"), seed="violet-bats"), 430, 30, sky=True, fps=6,
                  flight=((0, 0, 0), (38, -540, 22), (100, -540, 22)), period=15.0, delay=4.0),
        ),
    )
