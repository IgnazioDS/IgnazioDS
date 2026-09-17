"""Region IV: the Blood Moon Keep — the final region and the dragon's arena.

Night. A vast blood moon hangs over a gothic cathedral city, its towers rim
lit in pink. Crimson blossom trees and gargoyle pillars line an abyss where
fog drifts, and the knight walks a great stone bridge between braziers.
"""

import math
import random

from .. import raster
from . import TITLES, Layer, Light, Motif, RegionArt, common, motifs, paint

C = raster.rgb
TILE = 830
MOON = (300, 100, 50)

SKY = (
    (0, C("#07060f")), (48, C("#0f0920")), (96, C("#1c0d31")), (134, C("#2e1140")),
    (164, C("#461440")), (190, C("#5e1a43")), (240, C("#6e2046")),
)
MOON_RAMP = tuple(C(h) for h in ("#4e1026", "#7c1c34", "#aa2a44", "#d44258", "#ee6a7c", "#ff9aa6"))
CITY, CITY_RIM, WINDOW = C("#190b1e"), C("#8e3c5e"), C("#ffb070")


def sky():
    canvas = raster.Canvas(415, 240)
    paint.gradient(canvas, SKY)
    common.stars(canvas, 90, "keep-4", 3, 120, C("#5c4a7a"), C("#f0e4ff"))
    cx, cy, r = MOON
    _halo(canvas, cx, cy, r)
    _moon(canvas, cx, cy, r)
    rng = random.Random("keep-4-wisps")
    for i, (x, y, length, height) in enumerate(((262, 96, 96, 7), (344, 120, 70, 6), (186, 72, 60, 5))):
        paint.cumulus(canvas, x, y, length, height,
                      (C("#1c0a1e"), C("#2c0e26"), C("#5c1c3c"), C("#c24e6c")), f"keep-{i}")
    return canvas.freeze()


def _halo(canvas, cx, cy, r):
    rings = ((r + 34, C("#2a0f30"), 0.9), (r + 22, C("#3a1236"), 0.8), (r + 12, C("#5a1a40"), 0.7))
    for outer, color, strength in rings:
        for y in range(cy - outer, cy + outer + 1):
            for x in range(cx - outer, cx + outer + 1):
                d = math.hypot(x - cx, y - cy)
                if r <= d <= outer and strength * (1 - (d - r) / (outer - r)) > paint.bayer(x, y):
                    canvas.put(x, y, color)


def _moon(canvas, cx, cy, r):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = (x + 0.5 - cx) / r, (y + 0.5 - cy) / r
            d2 = dx * dx + dy * dy
            if d2 > 1:
                continue
            nz = math.sqrt(1 - d2)
            light = max(0.0, -0.42 * dx - 0.38 * dy + 0.82 * nz)
            value = 0.22 + 0.8 * light
            maria = paint.noise2d(x, y, "keep-maria", cell=14, octaves=3)
            if maria > 0.56:
                value -= 0.2 + (maria - 0.56) * 0.6
            index = value * (len(MOON_RAMP) - 1) + (paint.bayer(x, y) - 0.5) * 0.7
            color = MOON_RAMP[max(0, min(len(MOON_RAMP) - 1, int(index)))]
            if d2 > 0.9 and dx < -0.1 and dy < 0.25:
                color = MOON_RAMP[-1]
            canvas.put(x, y, color)


def city():
    """Cathedral city skyline, moon-rim-lit (screen y 60-200)."""
    canvas = raster.Canvas(TILE, 140, wrap_x=True)
    rng = random.Random("keep-4-city")
    base = 128
    x = 0
    while x < TILE - 20:
        roll = rng.random()
        if 180 <= x <= 260:
            x = _cathedral(canvas, x, base, rng) + rng.randint(2, 6)
        elif roll < 0.5:
            x = _house(canvas, x, base, rng) + rng.randint(0, 3)
        elif roll < 0.78:
            x = _church(canvas, x, base, rng) + rng.randint(2, 6)
        else:
            x = _tower(canvas, x, base, rng) + rng.randint(3, 8)
    canvas.rect(0, base, TILE, 140 - base, CITY)
    paint.rim_edges(canvas, (CITY,), CITY_RIM, dx=1, dy=-1)
    for _ in range(46):
        wx, wy = rng.randrange(TILE), rng.randrange(70, base - 2)
        if canvas.get(wx, wy) == CITY and canvas.get(wx, wy + 2) == CITY:
            canvas.column(wx, wy, wy + 2, WINDOW)
    return canvas.freeze()


def _roof(canvas, x, top, width, height):
    canvas.polygon([(x - 0.5, top + 0.5), (x + width + 0.5, top + 0.5), (x + width / 2, top - height)], CITY)


def _house(canvas, x, base, rng):
    w, h = rng.randint(9, 16), rng.randint(10, 20)
    canvas.rect(x, base - h, w, h, CITY)
    _roof(canvas, x, base - h, w, w * rng.uniform(0.6, 0.9))
    if rng.random() < 0.4:
        canvas.rect(x + w - 3, base - h - 6, 2, 5, CITY)
    return x + w


def _church(canvas, x, base, rng):
    nave_w, nave_h = rng.randint(20, 28), rng.randint(16, 22)
    canvas.rect(x, base - nave_h, nave_w, nave_h, CITY)
    _roof(canvas, x, base - nave_h, nave_w, nave_w * 0.45)
    tw, th = rng.randint(5, 7), nave_h + rng.randint(14, 22)
    tx = x + (0 if rng.random() < 0.5 else nave_w - tw)
    canvas.rect(tx, base - th, tw, th, CITY)
    _roof(canvas, tx - 1, base - th, tw + 2, rng.randint(16, 26))
    return x + nave_w


def _tower(canvas, x, base, rng):
    w, h = rng.randint(5, 8), rng.randint(34, 50)
    canvas.rect(x, base - h, w, h, CITY)
    if rng.random() < 0.7:
        _roof(canvas, x - 1, base - h, w + 2, rng.randint(14, 24))
    else:
        for cx in range(x - 1, x + w + 1, 2):
            canvas.put(cx, base - h - 1, CITY)
    return x + w


def _cathedral(canvas, x, base, rng):
    """West towers with spires, a nave with flying buttresses and a crossing spire."""
    width = 64
    canvas.rect(x + 8, base - 34, width - 16, 34, CITY)
    _roof(canvas, x + 8, base - 34, width - 16, 14)
    for tx in (x, x + width - 9):
        canvas.rect(tx, base - 56, 9, 56, CITY)
        _roof(canvas, tx - 1, base - 56, 11, 34)
        canvas.column(tx + 4, base - 92, base - 88, CITY)
    canvas.rect(x + 29, base - 60, 6, 26, CITY)
    _roof(canvas, x + 28, base - 60, 8, 40)
    for bx in range(x + 12, x + width - 12, 8):
        canvas.line(bx, base - 32, bx - 4, base - 18, CITY)
        canvas.rect(bx - 5, base - 20, 2, 20, CITY)
    canvas.disc(x + width / 2, base - 24, 3.2, C("#7a2a3e"))
    canvas.disc(x + width / 2, base - 24, 1.8, CITY)
    canvas.put(round(x + width / 2), base - 24, C("#c86a50"))
    return x + width


def grove():
    """Crimson blossom trees and gargoyle pillars along the abyss (screen y 118-218)."""
    canvas = raster.Canvas(TILE, 100, wrap_x=True)
    rng = random.Random("keep-4-grove")
    for gx in (40, 190, 330, 520, 660, 780):
        _blossom_tree(canvas, gx + rng.randint(-10, 10), 96, rng.randint(46, 66), rng)
    for px in (120, 450, 610):
        _gargoyle_pillar(canvas, px, 98, rng.randint(52, 64))
    return canvas.freeze()


def _blossom_tree(canvas, x, base, height, rng):
    trunk, bark_lit = C("#12060e"), C("#3a1426")
    for i in range(height - 16):
        w = 3 if i < 10 else 2
        sway = round(math.sin(i * 0.12) * 1.5)
        for k in range(w):
            canvas.put(x + sway + k, base - i, trunk)
        canvas.put(x + sway + w, base - i, bark_lit)
    top = base - height + 18
    ramp = (C("#3a0c24"), C("#6a1634"), C("#9a2244"), C("#cc3a62"), C("#f07898"))
    blobs = [(x + rng.randint(-14, 14), top + rng.randint(-8, 6), rng.uniform(6, 11)) for _ in range(6)]
    for bx, by, br in blobs:
        for yy in range(math.floor(by - br), math.ceil(by + br) + 1):
            for xx in range(math.floor(bx - br), math.ceil(bx + br) + 1):
                ox, oy = (xx - bx) / br, (yy - by) / br
                d2 = ox * ox + oy * oy
                if d2 > 1 or paint.noise2d(xx, yy, "leaves", cell=3, octaves=1, period_x=TILE) < 0.28 * d2:
                    continue
                light = 0.5 + 0.35 * ox - 0.3 * oy + (1 - d2) * 0.2
                index = light * (len(ramp) - 1) + (paint.bayer(xx, yy) - 0.5) * 1.1
                canvas.put(xx, yy, ramp[max(0, min(len(ramp) - 1, int(index)))])
    for _ in range(10):
        canvas.put(x + rng.randint(-18, 18), top + rng.randint(10, 40), ramp[3])


def _gargoyle_pillar(canvas, x, base, height):
    stone, lit, dark = C("#221826"), C("#6e4a66"), C("#120c14")
    canvas.rect(x - 1, base - 4, 9, 4, stone)
    canvas.rect(x, base - height, 7, height - 4, stone)
    canvas.column(x + 6, base - height, base - 4, lit)
    for by in range(base - height + 4, base - 4, 7):
        canvas.rect(x, by, 7, 1, dark)
    canvas.rect(x - 1, base - height - 2, 9, 2, stone)
    top = base - height - 2
    canvas.polygon([(x + 1, top), (x + 6, top), (x + 5, top - 6), (x + 2, top - 6)], stone)
    canvas.polygon([(x + 2, top - 4), (x - 4, top - 11), (x - 2, top - 3)], stone)
    canvas.polygon([(x + 5, top - 4), (x + 11, top - 12), (x + 8, top - 3)], stone)
    canvas.rect(x + 5, top - 8, 3, 3, stone)
    canvas.put(x + 7, top - 7, C("#ff5a6e"))
    canvas.line(x + 5, top - 6, x + 10, top - 12, lit)


def fog():
    canvas = raster.Canvas(TILE, 40, wrap_x=True)
    paint.mist(canvas, 4, 36, raster.rgba("#7a2a52", 120), "keep-fog", density=0.9)
    paint.mist(canvas, 12, 40, raster.rgba("#b04a70", 70), "keep-fog-2", density=0.7)
    return canvas.freeze()


BRAZIER_POSTS = (2, 10, 18, 26)
POST_GAP = 28
BRAZIER_XS = tuple(post * POST_GAP + 3 for post in BRAZIER_POSTS)


def bridge():
    """Balustrade, braziers, flagstone deck and arched bridge face (screen y 184-240)."""
    canvas = raster.Canvas(840, 56, wrap_x=True)  # a whole number of balustrade bays
    stone, lit, dark = C("#3a2c3c"), C("#7a6478"), C("#1c141e")
    for x in range(0, canvas.width):
        if x % 3 == 0 and x % POST_GAP not in range(0, 7):
            canvas.column(x, 8, 20, stone)
            canvas.put(x, 13, lit)
    canvas.rect(0, 5, canvas.width, 3, stone)
    canvas.rect(0, 5, canvas.width, 1, lit)
    canvas.rect(0, 20, canvas.width, 2, dark)
    for i, px in enumerate(range(0, canvas.width, POST_GAP)):
        canvas.rect(px, 1, 6, 21, stone)
        canvas.column(px, 1, 21, lit)
        canvas.column(px + 5, 1, 21, dark)
        canvas.rect(px - 1, 0, 8, 2, lit)
        if i in BRAZIER_POSTS:
            _brazier(canvas, px + 3, 0)
    paint.flagstones(canvas, 22, 36, C("#140e18"), C("#2c2230"), C("#4c3e4e"), C("#18101a"), C("#3a2a3a"), "keep")
    canvas.rect(0, 22, canvas.width, 1, C("#6a5668"))
    canvas.rect(0, 36, canvas.width, 20, C("#221a26"))
    for by in range(38, 56, 5):
        offset = 0 if by % 10 == 3 else 6
        for bx in range(offset, canvas.width, 12):
            canvas.column(bx, by, by + 4, C("#150f18"))
        canvas.rect(0, by + 4, canvas.width, 1, C("#150f18"))
    for ax in range(60, canvas.width, 140):
        _arch(canvas, ax, 56, 34, 16)
    return canvas.freeze()


def _brazier(canvas, cx, top):
    """Iron fire bowl on a post, flames tall enough to read at game scale."""
    canvas.rect(cx - 5, top - 4, 11, 4, C("#2a2028"))
    canvas.rect(cx - 5, top - 4, 11, 1, C("#5a4852"))
    canvas.rect(cx - 3, top, 7, 1, C("#140e14"))
    flame = ((0, 13, "#fff4c8"), (-1, 11, "#ffd27a"), (1, 11, "#ffd27a"), (-2, 8, "#ff9a42"),
             (2, 9, "#ff9a42"), (-3, 5, "#e0542e"), (3, 5, "#e0542e"))
    for dx, height, color in flame:
        canvas.column(cx + dx, top - 4 - height, top - 4, C(color))
    for dx, dy in ((-1, -18), (2, -20), (0, -23)):
        canvas.put(cx + dx, top + dy, C("#ffb050"))


def _arch(canvas, cx, base, width, height):
    for x in range(cx - width // 2, cx + width // 2 + 1):
        f = (x - cx) / (width / 2)
        top = base - round(height * math.sqrt(max(0.0, 1 - f * f)))
        canvas.column(x, top, base, C("#07050b"))
        canvas.put(x, top - 1, C("#6a5668"))
        canvas.put(x, top - 2, C("#2c2230"))


def front():
    """Parapet stones breaking the bottom edge in front of the actors (screen y 226-240)."""
    canvas = raster.Canvas(TILE, 14, wrap_x=True)
    rng = random.Random("keep-4-front")
    x = 40
    while x < TILE:
        w, h = rng.randint(10, 22), rng.randint(5, 12)
        canvas.rect(x, 14 - h, w, h, C("#0c080e"))
        canvas.rect(x, 14 - h, w, 1, C("#3a2c3a"))
        x += w + rng.randint(90, 180)
    return canvas.freeze()


def build():
    return RegionArt(
        key="keep",
        title=TITLES["keep"],
        layers=(
            Layer("sky", sky(), 0, 0.0),
            Layer("city", city(), 60, 0.1, offset=-20),
            Layer("grove", grove(), 118, 0.35),
            Layer("fog", fog(), 176, 0.25, effect="sway"),
            Layer("bridge", bridge(), 184, 1.0),
            Layer("front", front(), 226, 1.3, front=True),
        ),
        lights=(
            Light(MOON[0], MOON[1], 120, 110, "#ff5a78", 0.16),
            Light(59, 172, 34, 30, "#ff8a3a", 0.45, parallax=1.0, flicker="fire"),
            Light(283, 172, 34, 30, "#ff8a3a", 0.45, parallax=1.0, flicker="fire"),
            Light(507, 172, 34, 30, "#ff8a3a", 0.45, parallax=1.0, flicker="fire"),
            Light(731, 172, 34, 30, "#ff8a3a", 0.45, parallax=1.0, flicker="fire"),
            Light(230, 150, 40, 30, "#ffb070", 0.1, parallax=0.1, flicker="pulse"),
        ),
        particles=(C("#d04a70"), C("#ff8aa0"), C("#8a1a3a")),
        motion="fall",
        grade=("#2a0a1e", 0.06),
        motifs=tuple(
            Motif(f"flame-{i}", motifs.brazier_flames(), x - 6, 159, parallax=1.0, fps=10)
            for i, x in enumerate(BRAZIER_XS)
        ) + (
            Motif("bats", motifs.flock(6, (70, 24), C("#0c0610"), seed="keep-bats"), 436, 64, sky=True, fps=7,
                  flight=((0, 0, 0), (32, -560, 30), (100, -560, 30)), period=17.0, delay=9.0),
        ),
    )
