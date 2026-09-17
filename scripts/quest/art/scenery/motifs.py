"""Small looping sprites that make regions move: flowing water, brazier fire,
flocks crossing the sky, rain, a lightning bolt and eyes watching from the dark.
Each returns a tuple of equally sized frames (a single frame for stills).
"""

import math
import random

from .. import raster

C = raster.rgb


def waterfall_flow(width, height, colors, frames=3, seed=7):
    """Streaks that slide down the cascade: colors = (deep, mid, light, foam)."""
    rng = random.Random(f"flow-{seed}")
    phases = [rng.uniform(0, 7) for _ in range(width)]
    noise = [[rng.uniform(-0.35, 0.35) for _ in range(width)] for _ in range(height)]
    out = []
    for f in range(frames):
        canvas = raster.Canvas(width + 2, height)
        shift = f * math.tau / frames
        for y in range(height):
            sway = round(math.sin(y * 0.18 + seed) * 0.6)
            for dx in range(width):
                streak = math.sin(y * 0.35 - shift + phases[dx]) + noise[y][dx]
                color = colors[2] if streak > 0.65 else colors[1] if streak > -0.4 else colors[0]
                canvas.put(1 + dx + sway, y, color)
        for k in range(6):
            fx = 1 + (k * 5 + f * 3) % width
            canvas.put(fx, height - 1 - (k + f) % 3, colors[3])
        out.append(canvas.freeze())
    return tuple(out)


def brazier_flames(frames=4, width=13, height=22):
    """A tall tongue of fire rising from an iron bowl's rim (the bowl is painted on the bridge)."""
    ramp = (C("#a3241d"), C("#e0542e"), C("#ff9a42"), C("#ffd27a"), C("#fff4c8"))
    out = []
    for f in range(frames):
        rng = random.Random(f"brazier-{f}")
        canvas = raster.Canvas(width, height)
        cx = width / 2 - 0.5
        for y in range(height):
            rise = (height - 1 - y) / (height - 1)
            half = max(0.0, 5.2 * (1 - rise) ** 0.8 - 0.4 + math.sin(rise * 7 + f * 1.7) * 0.9)
            lean = math.sin(rise * 4 + f * 1.3) * 1.6 * rise
            for x in range(width):
                d = abs(x - cx - lean) / (half + 0.01)
                if d > 1:
                    continue
                heat = (1 - d) * (1.15 - rise) + rng.uniform(-0.12, 0.12)
                if heat > 0.02:
                    canvas.put(x, y, ramp[max(0, min(4, int(heat * 5)))])
        for _ in range(2):
            canvas.put(rng.randrange(2, width - 2), rng.randrange(0, 5), ramp[3])
        out.append(canvas.freeze())
    return tuple(out)


def flock(count, spread, body, rim=None, frames=2, seed="flock", size=(5, 3)):
    """A loose group of tiny flapping silhouettes (bats or crows); frames alternate wings up/down."""
    rng = random.Random(seed)
    birds = [(rng.randrange(2, spread[0] - 8), rng.randrange(2, spread[1] - 6), rng.randrange(2)) for _ in range(count)]
    w, h = size
    out = []
    for f in range(frames):
        canvas = raster.Canvas(*spread)
        for bx, by, phase in birds:
            up = (f + phase) % 2 == 0
            canvas.rect(bx + w // 2, by + 1, 1 + (w > 5), 2, body)
            for side in (-1, 1):
                for k in range(1, w // 2 + 2):
                    wy = by + (1 - k if up else k // 2)
                    canvas.put(bx + w // 2 + side * k + (1 if side > 0 and w > 5 else 0), wy, body)
            if rim is not None:
                canvas.put(bx + w // 2, by + 1, rim)
        out.append(canvas.freeze())
    return tuple(out)


def rain_tile(size=128, color=raster.rgba("#d8b0b0", 110), drops=34, seed="rain"):
    """A seamless tile of slanted streaks; slides down one tile per loop."""
    rng = random.Random(seed)
    canvas = raster.Canvas(size, size, wrap_x=True)
    for _ in range(drops):
        x, y, length = rng.randrange(size), rng.randrange(size), rng.randint(5, 10)
        for k in range(length):
            canvas.put(x - k // 4, (y + k) % size, color if k < length - 2 else raster.rgba("#ffffff", 150))
    return (canvas.freeze(),)


def lightning_bolt(width=34, height=126, seed="bolt"):
    """A forked bolt with a white core and a pale violet glow."""
    rng = random.Random(seed)
    canvas = raster.Canvas(width, height)
    core, glow = C("#ffffff"), raster.rgba("#d8c8ff", 150)

    def strike(x, y, length, lean, thick):
        for _ in range(length):
            nx = x + rng.choice((-1, 0, 0, 1)) + lean
            ny = y + rng.randint(3, 6)
            canvas.line(round(x), y, round(nx), ny, core)
            for off in (-1, 1):
                canvas.line(round(x) + off, y, round(nx) + off, ny, glow)
            if thick:
                canvas.line(round(x) + 1, y, round(nx) + 1, ny, core)
            x, y = nx, ny
            if y >= height - 2:
                break
        return x, y

    x, y = strike(width * 0.55, 0, 12, -0.2, True)
    strike(x, y, 12, 0.35, False)
    strike(width * 0.5, 24, 6, 0.8, False)
    return (canvas.freeze(),)


def watching_eyes(frames=10, color=C("#ff3a3a"), core=C("#ffd0b0")):
    """Two eyes in the dark that blink once per loop (the last frame is shut)."""
    out = []
    for f in range(frames):
        canvas = raster.Canvas(9, 3)
        if f != frames - 1:
            for ex in (1, 6):
                canvas.put(ex, 1, color)
                canvas.put(ex + 1, 1, core)
                canvas.put(ex, 0, raster.rgba("#ff3a3a", 90))
        out.append(canvas.freeze())
    return tuple(out)
