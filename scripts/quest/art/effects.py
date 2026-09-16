"""Procedural effects: death ash, soul wisp, parry spark, bonfire flames."""

import math
import random

from . import raster

C = raster.rgb
SMOKE = (C("#1b1420"), C("#2e2433"), C("#453848"))
EMBERS = (C("#ff8a3d"), C("#ffd08a"), C("#ff5a2e"))


def ash_burst(size=32, frames=5):
    """Dark smoke puffs expanding from the kill point with flying embers."""
    rng = random.Random("ash")
    puffs = [(rng.uniform(0, math.tau), rng.uniform(0.6, 1.0)) for _ in range(9)]
    sparks = [(rng.uniform(-math.pi, 0), rng.uniform(0.7, 1.3)) for _ in range(10)]
    out = []
    for f in range(frames):
        canvas = raster.Canvas(size, size)
        progress = (f + 1) / frames
        cx, cy = size / 2, size * 0.62
        for angle, reach in puffs:
            r = 2 + progress * 11 * reach
            px, py = cx + math.cos(angle) * r, cy + math.sin(angle) * r * 0.7 - progress * 4
            radius = max(0.8, 3.4 * (1 - progress) + 0.8)
            color = SMOKE[min(2, int(progress * 3))]
            _dithered_disc(canvas, px, py, radius, color, keep=1.15 - progress)
        for angle, speed in sparks:
            r = progress * 14 * speed
            canvas.put(round(cx + math.cos(angle) * r), round(cy + math.sin(angle) * r), EMBERS[f % 3])
        out.append(canvas.freeze())
    return tuple(out)


def _dithered_disc(canvas, cx, cy, radius, color, keep):
    for y in range(math.floor(cy - radius), math.ceil(cy + radius) + 1):
        for x in range(math.floor(cx - radius), math.ceil(cx + radius) + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 > radius * radius:
                continue
            if keep < 1 and (raster.BAYER4[y % 4][x % 4] + 0.5) / 16 > keep:
                continue
            canvas.put(x, y, color)


def wisp(size=11):
    """A glowing soul: white core, cyan body, soft translucent halo."""
    canvas = raster.Canvas(size, size)
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c)
            if d <= 1.2:
                canvas.put(x, y, C("#ffffff"))
            elif d <= 2.4:
                canvas.put(x, y, C("#bff3ff"))
            elif d <= 3.6:
                canvas.put(x, y, raster.rgba("#5fc9ff", 210))
            elif d <= 5.2 and (x + y) % 2 == 0:
                canvas.put(x, y, raster.rgba("#2a6fa8", 120))
    return canvas.freeze()


def spark(size=15):
    """Parry spark: a four-point star with diagonal glints."""
    canvas = raster.Canvas(size, size)
    c = size // 2
    for i in range(-c, c + 1):
        fade = abs(i) / c
        color = C("#fff4c2") if fade < 0.5 else C("#ffb347")
        if fade < 0.95:
            canvas.put(c + i, c, color)
            canvas.put(c, c + i, color)
        if abs(i) <= c // 2:
            canvas.put(c + i, c + i, C("#ffb347"))
            canvas.put(c + i, c - i, C("#ffb347"))
    canvas.put(c, c, C("#ffffff"))
    return canvas.freeze()


FIRE_W, FIRE_H = 136, 64
FIRE_MOUTH, FIRE_TARGET = (130, 10), (12, 46)
FIRE_RAMP = tuple(raster.rgb(h) for h in ("#6a1414", "#b82e1a", "#ee6a24", "#ffab3c", "#ffd878", "#fff6d6"))


def fire_breath(frames=3):
    """A roaring cone of dragon fire from the mouth (right) to the target (left)."""
    out = []
    mx, my = FIRE_MOUTH
    tx, ty = FIRE_TARGET
    length = math.hypot(tx - mx, ty - my)
    ux, uy = (tx - mx) / length, (ty - my) / length
    for f in range(frames):
        rng = random.Random(f"fire-{f}")
        canvas = raster.Canvas(FIRE_W, FIRE_H)
        for y in range(FIRE_H):
            for x in range(FIRE_W):
                along = (x - mx) * ux + (y - my) * uy
                if not 0 <= along <= length + 8:
                    continue
                across = abs(-(x - mx) * uy + (y - my) * ux)
                progress = along / length
                width = 2.5 + progress * 17
                ripple = math.sin(along * 0.35 + f * 2.1) * 2.2 * progress
                if across > width + ripple:
                    continue
                heat = (1 - across / (width + 2.5)) * (1.1 - progress * 0.75)
                heat += (random.Random(f"{f}-{x // 3}-{y // 3}").random() - 0.5) * 0.35
                if progress > 0.92 and rng.random() < 0.5:
                    continue
                index = heat * (len(FIRE_RAMP) - 1) + ((raster.BAYER4[y % 4][x % 4] + 0.5) / 16 - 0.5) * 0.9
                canvas.put(x, y, FIRE_RAMP[max(0, min(len(FIRE_RAMP) - 1, int(index)))])
        for _ in range(26):
            t = rng.uniform(0.3, 1.0)
            px = mx + ux * length * t + rng.uniform(-14, 14) * t
            py = my + uy * length * t + rng.uniform(-14, 14) * t
            canvas.put(round(px), round(py), FIRE_RAMP[rng.randint(3, 5)])
        out.append(canvas.freeze())
    return tuple(out)


def ember_burst(frames=6, size=96):
    """Embers and ash scattering outward as the wyrm dissolves."""
    rng = random.Random("wyrm-embers")
    motes = [(rng.uniform(0, math.tau), rng.uniform(0.3, 1.0), rng.randint(0, 5)) for _ in range(90)]
    out = []
    for f in range(frames):
        canvas = raster.Canvas(size, size)
        progress = (f + 1) / frames
        for angle, speed, tone in motes:
            r = progress * size * 0.48 * speed
            x = size / 2 + math.cos(angle) * r
            y = size / 2 + math.sin(angle) * r * 0.8 - progress * 10
            if rng.random() < progress * 0.5:
                continue
            color = FIRE_RAMP[min(5, tone + (0 if progress < 0.5 else -2))] if tone > 1 else SMOKE[tone]
            canvas.put(round(x), round(y), color)
        out.append(canvas.freeze())
    return tuple(out)


def bonfire(frames=4, width=28, height=34):
    """Coiled sword planted in a ring of stones, flames licking up the blade."""
    out = []
    for f in range(frames):
        rng = random.Random(f"bonfire-{f}")
        canvas = raster.Canvas(width, height)
        base_y = height - 3
        cx = width // 2
        for i, dx in enumerate(range(-9, 10, 3)):
            canvas.rect(cx + dx - 1, base_y - (1 if i % 2 else 0), 3, 3, C("#2a2622"))
            canvas.put(cx + dx - 1, base_y - (1 if i % 2 else 0), C("#4a443c"))
        canvas.rect(cx - 7, base_y - 2, 14, 2, C("#3a2418"))
        canvas.line(cx - 7, base_y - 3, cx + 6, base_y - 1, C("#5a3a24"))
        canvas.line(cx - 6, base_y - 1, cx + 7, base_y - 3, C("#4a2f1e"))
        for step in range(height - 10):
            y = base_y - 3 - step
            flame_half = max(0, 6 - step * 0.45 + rng.uniform(-1.2, 1.2))
            for dx in range(-round(flame_half), round(flame_half) + 1):
                heat = 1 - abs(dx) / (flame_half + 0.5) - step / 26
                color = (C("#fff2b0") if heat > 0.6 else C("#ffb347") if heat > 0.35
                         else C("#ff6a2a") if heat > 0.12 else C("#a3241d"))
                if heat > -0.05:
                    canvas.put(cx + dx + round(math.sin(step * 0.6 + f) * 0.8), y, color)
        canvas.column(cx, 4, base_y - 1, C("#59607a"))
        canvas.column(cx + 1, 6, base_y - 1, C("#2d2f3c"))
        canvas.rect(cx - 3, 8, 7, 1, C("#2b2430"))
        canvas.rect(cx, 5, 2, 3, C("#2b2430"))
        canvas.put(cx, 3, C("#a01f35"))
        for _ in range(4):
            canvas.put(cx + rng.randint(-6, 6), rng.randint(0, 12), EMBERS[rng.randint(0, 2)])
        out.append(canvas.freeze())
    return tuple(out)
