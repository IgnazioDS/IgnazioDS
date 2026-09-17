"""Region III: the Crimson Waste.

A battlefield after the slaughter, under a sky the color of an open wound.
A pale sun sinks behind a ruined cathedral whose arches still show the
light; smoke rises from the ridge; dead trees and tattered war banners stand
over dry grass where the swords of the fallen were driven into the earth.
"""

import math
import random

from .. import raster
from . import TITLES, Layer, Light, Motif, RegionArt, common, motifs, paint

C = raster.rgb
TILE = 830
RAIN_TILE = 128   # the rain falls four tiles for every one it drifts left: the streaks' own 1:4 slant
SUN = (300, 182, 34)

SKY = (
    (0, C("#1c060d")), (40, C("#360a15")), (80, C("#5a0f1f")), (116, C("#861a25")),
    (146, C("#b02e29")), (168, C("#d44e30")), (186, C("#ec743e")), (202, C("#f49656")), (240, C("#f2aa62")),
)
RUIN, RUIN_RIM = C("#2e0a16"), C("#b8502e")
STRATUS_HIGH = (C("#2a0812"), C("#4a0f1e"), C("#8a2a2a"))
STRATUS_LOW = (C("#6a1420"), C("#a0302a"), C("#ffb070"))


def sky():
    canvas = raster.Canvas(415, 240)
    paint.gradient(canvas, SKY)
    common.stars(canvas, 26, "crimson-5", 2, 60, C("#8a4a52"), C("#ffd8d0"))
    _sun(canvas, *SUN)
    sx, sy = 110, 44
    for dx, dy, color in ((0, 0, "#fff0f0"), (1, 0, "#ff4a4a"), (-1, 0, "#ff4a4a"), (0, 1, "#ff4a4a"),
                          (0, -1, "#ff4a4a"), (2, 0, "#a01a24"), (-2, 0, "#a01a24"), (0, 2, "#a01a24"), (0, -2, "#a01a24")):
        canvas.put(sx + dx, sy + dy, C(color))
    rng = random.Random("crimson-5-clouds")
    for i in range(9):
        y = rng.randrange(46, 170)
        ramp = STRATUS_LOW if y > 120 else STRATUS_HIGH
        paint.stratus(canvas, rng.randrange(0, 415), y, rng.randrange(80, 200), rng.randrange(5, 10), ramp, f"c{i}")
    return canvas.freeze()


def _sun(canvas, cx, cy, r):
    for y in range(cy - r - 26, cy + r + 27):
        for x in range(cx - r - 26, cx + r + 27):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d <= r:
                f = d / r
                color = C("#fff3d2") if f < 0.55 else C("#ffdca6") if f < 0.85 else C("#f8b47c")
                canvas.put(x, y, color)
            elif d <= r + 26 and (1 - (d - r) / 26) * 0.75 > paint.bayer(x, y):
                canvas.put(x, y, C("#f59a5e") if d < r + 11 else C("#e8784a"))


def ruins():
    """Ruined cathedral on the far ridge with sky-lit arch holes and smoke (screen y 90-210)."""
    canvas = raster.Canvas(TILE, 120, wrap_x=True)
    ridge = common.ridge_heights(TILE, "crimson-5-ridge", base=112, amplitude=12, base_cells=6)
    paint.rim_ridge(canvas, ridge, C("#3a0c18"), C("#8a2a26"))
    _cathedral_ruin(canvas, 470, 104)
    for tx, h in ((120, 42), (170, 30), (640, 50), (700, 34), (760, 26)):
        _broken_spire(canvas, tx, round(ridge[tx]) + 2, h, random.Random(f"spire-{tx}"))
    paint.rim_edges(canvas, (RUIN,), RUIN_RIM, dx=1, dy=0)
    return canvas.freeze()


def _broken_spire(canvas, x, base, height, rng):
    w = rng.randint(4, 7)
    canvas.rect(x, base - height, w, height, RUIN)
    for k in range(w):
        canvas.column(x + k, base - height - rng.randint(0, 6), base - height, RUIN)
    for wy in range(base - height + 6, base - 4, 9):
        canvas.column(x + w // 2, wy, wy + 3, C("#f08a4a"))


def _cathedral_ruin(canvas, x, base):
    """Nave wall with pointed-arch holes, one broken tower, one standing tower, a broken rose window."""
    canvas.rect(x - 46, base - 34, 92, 34, RUIN)
    for k in range(92):
        jag = round(4 * abs(math.sin(k * 0.37)) + (6 if 30 < k < 44 else 0))
        canvas.column(x - 46 + k, base - 34, base - 34 + jag, raster.CLEAR)
    for ax in range(x - 38, x + 40, 13):
        canvas.rect(ax, base - 24, 6, 16, raster.CLEAR)
        canvas.polygon([(ax - 0.5, base - 24), (ax + 6.5, base - 24), (ax + 3, base - 30)], raster.CLEAR)
    canvas.rect(x - 60, base - 70, 16, 70, RUIN)
    _roof_spire(canvas, x - 60, base - 70, 16, 36)
    canvas.rect(x + 44, base - 58, 14, 58, RUIN)
    for k in range(14):
        canvas.column(x + 44 + k, base - 58, base - 58 + round(9 * abs(math.sin(k * 0.8))), raster.CLEAR)
    canvas.disc(x - 52, base - 46, 5, raster.CLEAR)
    canvas.disc(x - 52, base - 46, 2, RUIN)
    canvas.line(x - 57, base - 46, x - 47, base - 46, RUIN)
    for k in range(-2, 3):
        canvas.rect(x + k * 20 - 2, base - 3, 4, 3, RUIN)


def _roof_spire(canvas, x, top, width, height):
    canvas.polygon([(x - 1, top + 0.5), (x + width + 1, top + 0.5), (x + width / 2, top - height)], RUIN)


def smoke():
    canvas = raster.Canvas(TILE, 150, wrap_x=True)
    for i, x in enumerate((210, 540, 760)):
        paint.smoke_plume(canvas, x, 146, 140, raster.rgba("#3a2226", 150), f"crimson-{i}", lean=-0.45)
    return canvas.freeze()


def battlefield_mid():
    """Dead trees with crows and tattered war banners on the near ridge (screen y 130-230)."""
    canvas = raster.Canvas(TILE, 100, wrap_x=True)
    hills = common.ridge_heights(TILE, "crimson-5-mid", base=78, amplitude=9, base_cells=5)
    paint.rim_ridge(canvas, hills, C("#24060e"), C("#6a1c1c"))
    rng = random.Random("crimson-5-mid")
    for tx in (60, 250, 430, 610, 780):
        ground = round(hills[tx]) + 2
        common.dead_tree(canvas, tx, ground, rng.randint(46, 70), tx, C("#16040a"))
        for _ in range(rng.randint(1, 3)):
            cx, cy = tx + rng.randint(-14, 14), ground - rng.randint(24, 44)
            if raster.alpha_of(canvas.get(cx, cy + 1)):
                canvas.rect(cx, cy - 2, 3, 2, C("#0a0206"))
                canvas.put(cx + 3, cy - 2, C("#0a0206"))
    for bx in (150, 350, 520, 700):
        ground = round(hills[bx]) + 2
        lean = rng.choice((-3, -2, 2, 3))
        canvas.line(bx, ground, bx + lean, ground - 44, C("#1a0a0a"))
        top = ground - 44
        canvas.polygon([(bx + lean, top + 1), (bx + lean + 12, top + 2), (bx + lean + 10, top + 18),
                        (bx + lean + 7, top + 14), (bx + lean + 4, top + 20), (bx + lean, top + 16)], C("#4a0a18"))
        canvas.line(bx + lean, top + 1, bx + lean + 12, top + 2, C("#8a2030"))
    return canvas.freeze()


BLADE, EDGE, GUARD, GRIP = C("#7a7478"), C("#cfc6c2"), C("#4a3424"), C("#2a1a14")


def field():
    """Dry grass, planted swords and spears, trampled path, fallen helm and shield (screen y 184-240)."""
    canvas = raster.Canvas(TILE, 56, wrap_x=True)
    grass = (C("#3a1410"), C("#5a2414"), C("#7a3616"))
    canvas.rect(0, 14, TILE, 42, C("#22080a"))
    paint.dry_grass(canvas, 12, 22, grass, C("#e08a42"), 1.6, "crimson-back", max_h=11)
    rng = random.Random("crimson-5-field")
    for i in range(12):
        x = int(i * TILE / 12 + rng.randint(0, 40))
        spear = rng.random() < 0.35
        paint.planted_blade(canvas, x, 21, rng.randint(20, 28) if spear else rng.randint(13, 18),
                            rng.randint(-5, 5), C("#5a4a3a") if spear else BLADE, EDGE, GUARD, GRIP, spear=spear)
    canvas.rect(0, 22, TILE, 16, C("#3a1a12"))
    for x in range(TILE):
        if rng.random() < 0.3:
            canvas.put(x, rng.randint(23, 36), C("#4a2616"))
        canvas.column(x, 21, 22 + rng.randint(0, 2), C("#5a2414"))
        if rng.random() < 0.5:
            canvas.column(x, 36, 38 + rng.randint(0, 2), C("#4a1c12"))
    for track in (27, 32):
        for x in range(0, TILE, 3):
            canvas.put(x, track, C("#2e140e"))
    canvas.rect(0, 38, TILE, 18, C("#2a0c0a"))
    paint.dry_grass(canvas, 44, 56, grass, C("#f09a52"), 2.2, "crimson-front", max_h=14)
    for hx in (180, 610):
        canvas.disc(hx, 46, 4, C("#5c5a60"))
        canvas.rect(hx - 4, 46, 9, 3, C("#3a383e"))
        canvas.put(hx - 1, 44, C("#b8b4bc"))
        canvas.rect(hx + 1, 45, 3, 1, C("#1a181c"))
        canvas.disc(hx + 16, 48, 6, C("#4a2a1e"))
        canvas.disc(hx + 16, 48, 2, C("#8a7a5a"))
    return canvas.freeze()


def front():
    """Tall dry grass tufts and a planted greatsword over the actors (screen y 196-240)."""
    canvas = raster.Canvas(TILE, 44, wrap_x=True)
    rng = random.Random("crimson-5-front")
    x = 30
    while x < TILE:
        for _ in range(rng.randint(8, 14)):
            paint.blade(canvas, x + rng.randint(-10, 10), 43, rng.randint(10, 30), rng.randint(-5, 5),
                        C("#140406"), C("#6a2a18"))
        x += rng.randint(80, 150)
    paint.planted_blade(canvas, 520, 43, 34, 4, C("#1a1214"), C("#3a2a2a"), C("#120a08"), C("#0a0606"))
    return canvas.freeze()


def build():
    return RegionArt(
        key="crimson",
        title=TITLES["crimson"],
        layers=(
            Layer("sky", sky(), 0, 0.0),
            Layer("smoke", smoke(), 50, 0.06, effect="sway"),
            Layer("ruins", ruins(), 90, 0.1, offset=-230),
            Layer("mid", battlefield_mid(), 130, 0.4),
            Layer("field", field(), 184, 1.0),
            Layer("front", front(), 196, 1.25, front=True),
        ),
        lights=(
            Light(SUN[0], SUN[1], 130, 70, "#ffb070", 0.2),
            Light(90, 110, 110, 70, "#ffe0e8", 0.3, flicker="lightning"),
        ),
        particles=(C("#ff8a3d"), C("#ffd08a"), C("#8a8a8a")),
        motion="rise",
        grade=("#3a0808", 0.05),
        motifs=(
            Motif("bolt", motifs.lightning_bolt(), 74, -2, sky=True, effect="bolt"),
            Motif("crows", motifs.flock(3, (40, 16), C("#140608"), rim=C("#c05a48"), seed="crimson-crows", size=(7, 3)),
                  432, 58, sky=True, fps=5, flight=((0, 0, 0), (50, -500, -26), (100, -500, -26)), period=12.0, delay=6.0),
            Motif("rain", motifs.rain_tile(), 0, -RAIN_TILE * 4, front=True, tile=(5, 6),
                  flight=((0, 0, 0), (100, -RAIN_TILE, RAIN_TILE * 4)), period=1.68),
        ),
    )
