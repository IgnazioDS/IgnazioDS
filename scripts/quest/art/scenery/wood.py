"""Region II: the Hollow Wood.

An ancient forest drowned in green-teal light. Pale trunks recede into mist,
god rays fall through gaps in a heavy canopy, and mossy giants with flaring
roots crowd the path. A crumbling wall runs beside it, glowing fungi at its
foot, and an old sword stands planted in a stump.
"""

import math
import random

from .. import raster
from . import TITLES, Layer, Light, RegionArt, paint

C = raster.rgb
TILE = 830

BACKDROP = (
    (0, C("#b4ecd2")), (26, C("#8fd8bb")), (60, C("#63b79c")), (100, C("#438f7d")),
    (140, C("#2f7063")), (180, C("#235a50")), (214, C("#1a4640")), (240, C("#143a35")),
)


def backdrop():
    canvas = raster.Canvas(415, 240)
    paint.gradient(canvas, BACKDROP)
    return canvas.freeze()


def canopy():
    """Leaf clusters hanging from the top edge, bright gaps between them (screen y 0-80)."""
    canvas = raster.Canvas(TILE, 80, wrap_x=True)
    rng = random.Random("wood-canopy")
    ramp = (C("#0c2521"), C("#15382f"), C("#23503f"), C("#3c7a58"))
    x = 0
    while x < TILE:
        if rng.random() < 0.18:
            x += rng.randint(26, 46)  # a gap where the light pours through
            continue
        for _ in range(rng.randint(3, 6)):
            bx, by, br = x + rng.randint(-10, 22), rng.randint(-6, 22), rng.uniform(8, 17)
            for yy in range(max(0, math.floor(by - br)), math.ceil(by + br) + 1):
                for xx in range(math.floor(bx - br), math.ceil(bx + br) + 1):
                    ox, oy = (xx - bx) / br, (yy - by) / br
                    d2 = ox * ox + oy * oy
                    if d2 > 1 or paint.noise2d(xx, yy, "canopy-leaf", cell=3, octaves=1, period_x=TILE) < 0.3 * d2:
                        continue
                    light = 0.25 - 0.3 * ox + 0.55 * max(0.0, oy) * (1 - d2)
                    index = light * 3 + (paint.bayer(xx, yy) - 0.5) * 0.9
                    canvas.put(xx, yy, ramp[max(0, min(3, int(index)))])
        for _ in range(rng.randint(2, 4)):
            vx, length = x + rng.randint(0, 24), rng.randint(10, 44)
            for k in range(length):
                canvas.put(vx + round(math.sin(k * 0.25 + vx) * 1.4), 18 + k, ramp[1] if k % 5 else ramp[3])
        x += rng.randint(24, 40)
    return canvas.freeze()


def rays():
    """Diagonal god rays falling from the canopy gaps (translucent, screen y 0-214)."""
    canvas = raster.Canvas(TILE, 214, wrap_x=True)
    for sx in (100, 318, 540, 730):
        for y in range(8, 214):
            f = y / 214
            center = sx + y * 0.45
            half = 8 + f * 20
            for x in range(round(center - half), round(center + half)):
                edge = 1 - abs(x - center) / half
                if edge * (0.75 - 0.45 * f) > paint.bayer(x, y):
                    canvas.put(x, y, raster.rgba("#effff4", 64))
    return canvas.freeze()


def _trunk(canvas, x, top, base, width, body, lit, shade, moss=None, seed=0, flare=0.0):
    """Swaying trunk with bark stripes, knots, moss on the lit side and flared roots."""
    rng = random.Random(f"trunk-{seed}")
    lean, sway, phase = rng.uniform(-0.05, 0.05), rng.uniform(0.6, 2.2), rng.uniform(0, 6)
    stripes = [rng.randint(1, max(1, width - 2)) for _ in range(max(1, width // 4))]
    for y in range(top, base):
        f = (y - top) / max(1, base - top)
        root = round(max(0.0, f - 0.86) * flare)
        w = max(2, round(width * (0.85 + 0.15 * f)) + root)
        cx = x + round((y - top) * lean + math.sin(y * 0.02 + phase) * sway)
        left = cx - w // 2
        canvas.rect(left, y, w, 1, body)
        canvas.put(left, y, lit)
        if w > 6:
            canvas.put(left + 1, y, lit)
        canvas.put(left + w - 1, y, shade)
        for s in stripes:
            if (y + s * 3) % 9 < 5:
                canvas.put(left + min(w - 2, s), y, shade)
        if moss and paint.noise2d(left, y, f"moss-{seed}", cell=6, octaves=2) > 0.62:
            for k in range(min(3, w - 1)):
                canvas.put(left + k, y, moss)
    if moss:
        for _ in range(rng.randint(1, 3)):
            ky = rng.randint(top + 20, base - 30)
            kx = x + round((ky - top) * lean)
            canvas.disc(kx, ky, 1.6, shade)
            canvas.put(kx - 1, ky - 1, lit)


def far_trunks():
    canvas = raster.Canvas(TILE, 215, wrap_x=True)
    rng = random.Random("wood-far")
    x = 0
    while x < TILE - 10:
        width = rng.randint(3, 8)
        _trunk(canvas, x, 0, 214, width, C("#6aa996"), C("#88c4b0"), C("#58937f"), seed=x)
        for _ in range(rng.randint(0, 2)):
            by = rng.randint(30, 130)
            direction = rng.choice((-1, 1))
            canvas.line(x, by, x + direction * rng.randint(8, 18), by - rng.randint(6, 14), C("#6aa996"))
        x += rng.randint(26, 58)
    paint.mist(canvas, 140, 215, raster.rgba("#7cc4aa", 160), "wood-far-mist", density=1.0)
    return canvas.freeze()


def mist_band():
    canvas = raster.Canvas(TILE, 60, wrap_x=True)
    paint.mist(canvas, 0, 60, raster.rgba("#b8ecd4", 90), "wood-mist", density=0.85)
    return canvas.freeze()


def mid_trunks():
    canvas = raster.Canvas(TILE, 225, wrap_x=True)
    rng = random.Random("wood-mid")
    for i, x in enumerate((48, 170, 290, 420, 528, 662, 774)):
        width = rng.randint(11, 19)
        x += rng.randint(-14, 14)
        _trunk(canvas, x, 0, 222, width, C("#2b5448"), C("#5c947e"), C("#17322b"),
               moss=C("#5c9a4a"), seed=100 + i, flare=90)
        for _ in range(rng.randint(1, 2)):
            by = rng.randint(24, 100)
            direction = rng.choice((-1, 1))
            end = x + direction * rng.randint(16, 30)
            rise = rng.randint(4, 12)
            canvas.line(x, by, end, by - rise, C("#244a41"))
            canvas.line(x, by + 1, end, by - rise + 1, C("#1a3a33"))
            for k in range(1, 6):
                vx = x + (end - x) * k / 6
                length = rng.randint(4, 20)
                for s in range(length):
                    canvas.put(round(vx + math.sin(s * 0.4 + k) * 0.8), by - round(rise * k / 6) + 1 + s, C("#3d7a52"))
    return canvas.freeze()


def ruins():
    """Crumbling mossy wall, glowing fungi, a planted sword, the path and fern floor (screen y 180-240)."""
    canvas = raster.Canvas(TILE, 60, wrap_x=True)
    rng = random.Random("wood-ruins")
    stone_tones = (C("#3a524b"), C("#445e56"), C("#4e6a60"))
    lit, mortar, moss, moss_lit = C("#72928a"), C("#1e302a"), C("#4f8a45"), C("#8ac468")
    tops = {}
    for x in range(TILE):
        height = 10 + round(14 * raster.periodic_noise(x, TILE, "wood-wall", octaves=4, base_cells=9))
        if raster.periodic_noise(x, TILE, "wood-breach", octaves=2, base_cells=5) > 0.7:
            height = rng.randint(1, 4)
        tops[x] = 27 - height
        canvas.column(x, tops[x], 27, mortar)
    y = 26
    while y > 1:
        h = rng.randint(4, 6)
        x = rng.randint(0, 6)
        while x < TILE:
            w = rng.randint(6, 14)
            tone = rng.choice(stone_tones)
            for bx in range(x, min(TILE, x + w - 1)):
                for by in range(y - h + 1, y):
                    if by > tops[bx]:
                        canvas.put(bx, by, tone)
                if y - h + 1 > tops[bx]:
                    canvas.put(bx, y - h + 1, lit)
            x += w
        y -= h
    for x in range(TILE):
        t = tops[x]
        canvas.put(x, t, moss_lit)
        canvas.put(x, t + 1, moss)
        if rng.random() < 0.35:
            canvas.column(x, t + 2, min(26, t + 2 + rng.randint(1, 7)), moss)
    for _ in range(14):
        rx = rng.randrange(TILE)
        canvas.rect(rx, 23, rng.randint(3, 6), 3, rng.choice(stone_tones))
        canvas.put(rx, 23, moss_lit)
    for fx in (90, 250, 470, 610, 700):
        for k in range(rng.randint(3, 5)):
            mx = fx + rng.randint(-6, 6)
            canvas.column(mx, 23, 26, C("#cfe8d8"))
            canvas.rect(mx - 1, 22, 3, 1, C("#7ff0d0"))
            canvas.put(mx, 21, C("#c8fff0"))
    _stump_sword(canvas, 560, 26)
    canvas.rect(0, 26, TILE, 16, C("#2a3a30"))
    for x in range(TILE):
        if rng.random() < 0.25:
            canvas.put(x, rng.randint(27, 41), C("#34483a"))
        if rng.random() < 0.05:
            canvas.put(x, rng.randint(28, 40), rng.choice((C("#8a6a2e"), C("#a8482e"))))
        canvas.column(x, 26, 26 + rng.randint(0, 2), C("#3c6a3e"))
    for rx in (130, 390, 640):
        for k in range(26):
            canvas.put(rx + k, 32 + round(math.sin(k * 0.3) * 2), C("#3a2e24"))
            canvas.put(rx + k, 31 + round(math.sin(k * 0.3) * 2), C("#5a4a38"))
    canvas.rect(0, 42, TILE, 18, C("#16302a"))
    for x in range(0, TILE, 2):
        paint.blade(canvas, x, 59, rng.randint(4, 14), rng.randint(-3, 3), C("#23493a"), C("#4f8a58"))
    return canvas.freeze()


def _stump_sword(canvas, x, base):
    canvas.rect(x - 7, base - 7, 14, 7, C("#3a2e24"))
    canvas.rect(x - 7, base - 8, 14, 1, C("#5c8a4a"))
    canvas.column(x - 7, base - 7, base, C("#5a4a38"))
    canvas.column(x, base - 30, base - 7, C("#9aa8b4"))
    canvas.column(x + 1, base - 30, base - 7, C("#5c6a78"))
    canvas.rect(x - 4, base - 30, 10, 2, C("#6a5a3a"))
    canvas.rect(x - 1, base - 36, 3, 6, C("#2e2620"))
    canvas.put(x, base - 37, C("#b8943c"))


def ferns():
    """Foreground fern fronds along the bottom edge, drawn over the actors."""
    canvas = raster.Canvas(TILE, 240, wrap_x=True)
    rng = random.Random("wood-front")
    x = 10
    while x < TILE:
        for k in range(rng.randint(3, 6)):
            length = rng.randint(10, 22)
            angle = math.radians(rng.uniform(-70, -20) if k % 2 else rng.uniform(-160, -110))
            ox = x + rng.randint(-4, 4)
            for s in range(length):
                px = ox + math.cos(angle) * s
                py = 239 + math.sin(angle) * s + (s / length) ** 2 * 6
                canvas.put(round(px), round(py), C("#0c2218"))
                if s % 2 == 0 and s > 2:
                    canvas.put(round(px), round(py) - 1, C("#153a26"))
        x += rng.randint(50, 110)
    return canvas.freeze()


def build():
    return RegionArt(
        key="wood",
        title=TITLES["wood"],
        layers=(
            Layer("backdrop", backdrop(), 0, 0.0),
            Layer("far", far_trunks(), 0, 0.12),
            Layer("rays", rays(), 0, 0.05),
            Layer("mist", mist_band(), 150, 0.22),
            Layer("mid", mid_trunks(), 0, 0.4),
            Layer("canopy", canopy(), 0, 0.3),
            Layer("ruins", ruins(), 180, 1.0),
            Layer("ferns", ferns(), 0, 1.3, front=True),
        ),
        lights=(
            Light(170, 60, 70, 110, "#d8ffe8", 0.14, front=True),
            Light(330, 90, 60, 120, "#d8ffe8", 0.1, front=True),
            Light(90, 203, 18, 8, "#7ff0d0", 0.45, parallax=1.0, flicker="pulse"),
            Light(250, 203, 18, 8, "#7ff0d0", 0.45, parallax=1.0, flicker="pulse"),
            Light(470, 203, 18, 8, "#7ff0d0", 0.45, parallax=1.0, flicker="pulse"),
            Light(610, 203, 18, 8, "#7ff0d0", 0.45, parallax=1.0, flicker="pulse"),
            Light(700, 203, 18, 8, "#7ff0d0", 0.45, parallax=1.0, flicker="pulse"),
        ),
        particles=(C("#e8ffb0"), C("#b8f0d0"), C("#ffffff")),
        motion="rise",
    )
