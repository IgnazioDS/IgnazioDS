"""Procedural effects: death ash, soul wisp, parry spark, bonfire flames."""

import math
import random
from functools import lru_cache

from . import raster, sprite

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


SLASH_SIZE = 44
CUT_ANGLES = {"slash": 52.0, "rise": -38.0, "thrust": 0.0, "riposte": 0.0, "plunge": 90.0}   # degrees, screen space
COLD = (C("#ffffff"), raster.rgba("#bfe8ff", 230), raster.rgba("#5fb8ff", 150))
GILDED = (C("#ffffff"), raster.rgba("#ffe7a0", 235), raster.rgba("#ff9a3a", 160))


def slash_mark(blow, palette=COLD, frames=3):
    """A bright cut across the target along the blow's line: full stroke, thinning, then fading glints."""
    angle = math.radians(CUT_ANGLES[blow])
    ux, uy = math.cos(angle), math.sin(angle)
    half = 19 if blow in ("slash", "rise", "plunge") else 16
    c = (SLASH_SIZE - 1) / 2
    rng = random.Random(f"slash-{blow}")
    out = []
    for f in range(frames):
        canvas = raster.Canvas(SLASH_SIZE, SLASH_SIZE)
        width = (3.2, 1.8, 0.9)[f]
        reach = half * (1.0, 1.12, 1.18)[f]
        for y in range(SLASH_SIZE):
            for x in range(SLASH_SIZE):
                along = (x - c) * ux + (y - c) * uy
                across = abs(-(x - c) * uy + (y - c) * ux)
                color = _cut_color(f, x, y, along, across, width, reach, palette)
                if color is not None:
                    canvas.put(x, y, color)
        for _ in range(6 if f < 2 else 3):
            t = rng.uniform(-reach, reach)
            off = rng.uniform(2, 6 + 3 * f) * rng.choice((-1, 1))
            canvas.put(round(c + ux * t - uy * off), round(c + uy * t + ux * off), palette[1 + (f > 0)])
        out.append(canvas.freeze())
    return tuple(out)


def _cut_color(frame, x, y, along, across, width, reach, palette):
    """Color of one pixel of a cut mark: a lens-shaped stroke, then a dotted fading line on the last frame."""
    if abs(along) > reach:
        return None
    if frame == 2:
        return palette[2] if across < 0.8 and (x * 7 + y * 3) % 4 == 0 else None
    w = width * math.sin(math.pi * (0.5 + along / (2 * reach)))
    if across <= w * 0.45:
        return palette[0]
    if across <= w:
        return palette[1]
    return palette[2] if across <= w + 1.0 and frame == 0 else None


BURST_SIZE = 26


def impact_burst(palette=COLD, frames=3):
    """Contact flash where steel meets: a hot core with rays, a thin ring, then scattered sparks."""
    c = (BURST_SIZE - 1) / 2
    rng = random.Random("burst")
    sparks = [(rng.uniform(0, math.tau), rng.uniform(6, 12)) for _ in range(9)]
    out = []
    for f in range(frames):
        canvas = raster.Canvas(BURST_SIZE, BURST_SIZE)
        if f == 0:
            canvas.disc(c, c, 2.6, palette[1])
            canvas.disc(c, c, 1.4, palette[0])
            for k in range(4):
                a = k * math.pi / 2 + math.pi / 4
                for r in range(3, 11):
                    canvas.put(round(c + math.cos(a) * r), round(c + math.sin(a) * r), palette[1] if r < 7 else palette[2])
        elif f == 1:
            for k in range(28):
                a = k / 28 * math.tau
                canvas.put(round(c + math.cos(a) * 7), round(c + math.sin(a) * 7), palette[1] if k % 2 else palette[2])
            canvas.put(round(c), round(c), palette[0])
        for a, r in sparks:
            dist = r * (0.6 + 0.35 * f)
            if f > 0 or r > 9:
                canvas.put(round(c + math.cos(a) * dist), round(c + math.sin(a) * dist), palette[2 if f == 2 else 1])
        out.append(canvas.freeze())
    return tuple(out)


@lru_cache(maxsize=None)
def hit_flash(blow, heavy):
    """The cut mark over its contact burst, one SLASH_SIZE sheet per blow and weight."""
    palette = GILDED if heavy else COLD
    offset = (SLASH_SIZE - BURST_SIZE) // 2
    frames = []
    for mark, burst in zip(slash_mark(blow, palette), impact_burst(palette)):
        canvas = raster.Canvas(SLASH_SIZE, SLASH_SIZE)
        canvas.blit(sprite.pad(burst, SLASH_SIZE, SLASH_SIZE, offset, offset), 0, 0)
        canvas.blit(mark, 0, 0)
        frames.append(canvas.freeze())
    return tuple(frames)


DUST_W, DUST_H = 150, 56
DUST = (raster.rgba("#2a2230", 230), raster.rgba("#4a3e52", 200), raster.rgba("#6e5f7a", 160))


def dust_cloud(frames=6):
    """A wide cloud of stone dust rolling out along the ground when something huge falls."""
    rng = random.Random("crash-dust")
    puffs = [(rng.uniform(-1, 1), rng.uniform(0.2, 1.0), rng.uniform(0.6, 1.2)) for _ in range(26)]
    out = []
    for f in range(frames):
        canvas = raster.Canvas(DUST_W, DUST_H)
        progress = (f + 1) / frames
        for side, lift, size in puffs:
            x = DUST_W / 2 + side * progress * DUST_W * 0.45
            y = DUST_H - 6 - lift * progress * 26
            radius = size * (4 + 9 * progress) * (1.1 - 0.5 * progress)
            tone = DUST[min(2, int(lift * 3))]
            _dithered_disc(canvas, x, y, radius, tone, keep=1.2 - progress * 0.9)
        out.append(canvas.freeze())
    return tuple(out)
