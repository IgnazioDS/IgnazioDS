"""Painterly primitives for detailed regions: positional gradients, lumpy
sunset clouds, rim-lit trees and ridges, gothic architecture, water, stone.

Every function paints onto a raster.Canvas and is deterministic for a given
seed. On wrap_x canvases all shapes continue across the tile seam.
"""

import math
import random

from .. import raster


def bayer(x, y):
    return (raster.BAYER4[y % 4][x % 4] + 0.5) / 16


def noise2d(x, y, seed, cell=8, octaves=2, period_x=None):
    """Smooth 2D value noise in [0, 1]; tiles horizontally when period_x is set."""
    total, norm, amp, size = 0.0, 0.0, 1.0, cell
    for octave in range(octaves):
        gx, gy = x / size, y / size
        x0, y0 = math.floor(gx), math.floor(gy)
        fx, fy = gx - x0, gy - y0
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        wrap = max(1, round(period_x / size)) if period_x else None

        def lattice(i, j):
            if wrap:
                i %= wrap
            return random.Random(f"{seed}-{octave}-{i}-{j}").random()

        top = lattice(x0, y0) * (1 - fx) + lattice(x0 + 1, y0) * fx
        bottom = lattice(x0, y0 + 1) * (1 - fx) + lattice(x0 + 1, y0 + 1) * fx
        total += amp * (top * (1 - fy) + bottom * fy)
        norm += amp
        amp *= 0.5
        size = max(1, size // 2)
    return total / norm


def rim_edges(canvas, body_colors, rim, dx=1, dy=-1):
    """Light the silhouette pixels whose neighbour toward the light is empty."""
    lit = []
    for y in range(canvas.height):
        for x in range(canvas.width):
            if canvas.get(x, y) in body_colors and raster.alpha_of(canvas.get(x + dx, y + dy)) == 0:
                lit.append((x, y))
    for x, y in lit:
        canvas.put(x, y, rim)


def gradient(canvas, stops, x0=0, x1=None):
    """Vertical gradient through (y, color) stops with a dithered blend zone."""
    x1 = canvas.width if x1 is None else x1
    for y in range(stops[0][0], min(canvas.height, stops[-1][0] + 1)):
        for (ya, ca), (yb, cb) in zip(stops, stops[1:]):
            if ya <= y <= yb:
                f = (y - ya) / max(1, yb - ya)
                break
        for x in range(x0, x1):
            canvas.put(x, y, cb if f > bayer(x, y) else ca)
    first_y, first_c = stops[0]
    for y in range(0, first_y):
        for x in range(x0, x1):
            canvas.put(x, y, first_c)


def cumulus(canvas, cx, base_y, length, height, ramp, seed):
    """Lumpy cloud lit from below: ramp = (shadow, body, lit, glow)."""
    rng = random.Random(f"cumulus-{seed}")
    lobes = []
    count = max(3, round(length / 11))
    for i in range(count):
        f = i / (count - 1)
        ry = height * (0.35 + 0.65 * math.sin(math.pi * (0.15 + 0.7 * f))) * rng.uniform(0.65, 1.0)
        rx = length / count * rng.uniform(0.9, 1.5)
        lobes.append((cx - length / 2 + f * length, base_y - ry * 0.55, rx, ry))
    for x in range(math.floor(cx - length / 2 - 8), math.ceil(cx + length / 2 + 8)):
        tops = [ly - ry * math.sqrt(max(0.0, 1 - ((x - lx) / rx) ** 2)) for lx, ly, rx, ry in lobes if abs(x - lx) < rx]
        if not tops:
            continue
        top = min(tops)
        if top >= base_y - 0.5:
            continue
        for y in range(math.ceil(top), base_y + 1):
            v = (y - top) / max(1.0, base_y - top)
            level = v * 3.2 + (bayer(x, y) - 0.5) * 0.9
            canvas.put(x, y, ramp[max(0, min(3, int(level)))])


def stratus(canvas, cx, y, length, thickness, ramp, seed):
    """Long tapered cloud band: dark top, glowing underside. ramp = (top, body, lit)."""
    rng = random.Random(f"stratus-{seed}")
    wobble = rng.uniform(0, 6)
    for dx in range(-length // 2, length // 2):
        f = (dx + length / 2) / length
        t = thickness * max(0.0, math.sin(math.pi * f)) ** 0.6 * (0.75 + 0.25 * math.sin(dx * 0.11 + wobble))
        rows = max(0, round(t))
        base = y + round(math.sin(dx * 0.03 + wobble) * 1.2)
        for k in range(rows):
            color = ramp[2] if k == 0 else (ramp[1] if k < rows - 1 else ramp[0])
            canvas.put(cx + dx, base - k, color)


def smoke_plume(canvas, x, base, height, color, seed, lean=-0.35):
    """Dithered translucent column rising and bending with the wind."""
    rng = random.Random(f"smoke-{seed}")
    for y in range(base - height, base):
        f = (base - y) / height
        center = x + lean * (base - y) * f
        half = 2 + f * 14
        for xx in range(round(center - half), round(center + half) + 1):
            edge = 1 - abs(xx - center) / half
            density = edge * (0.9 - 0.7 * f) * (0.7 + 0.3 * noise2d(xx, y, f"plume-{seed}", cell=4, octaves=1))
            if density > bayer(xx, y) + rng.uniform(0, 0.08):
                canvas.put(xx, y, color)


def dry_grass(canvas, top, bottom, blade_colors, tip, density, seed, max_h=9):
    """Field of vertical dry blades, sunlit tips only (no streaks)."""
    rng = random.Random(f"drygrass-{seed}")
    for x in range(canvas.width):
        for _ in range(int(density + rng.random())):
            base = rng.randint(top, bottom)
            h = rng.randint(2, max_h)
            color = rng.choice(blade_colors)
            lean = rng.choice((-1, 0, 0, 1))
            for i in range(h):
                px = x + (lean if i > h * 0.6 else 0)
                canvas.put(px, base - i, tip if i == h - 1 and rng.random() < 0.7 else color)


def planted_blade(canvas, x, base, length, lean, blade, edge, guard, grip, spear=False):
    """A sword or spear stuck in the ground at an angle."""
    dx = lean / max(1, length)
    for i in range(length):
        px = round(x + dx * i)
        canvas.put(px, base - i, blade)
        if not spear and i < length - 5:
            canvas.put(px + 1, base - i, edge)
    top = base - length
    tx = round(x + lean)
    if spear:
        canvas.polygon([(tx - 1.5, top + 1), (tx + 2.5, top + 1), (tx + 0.5, top - 5)], edge)
    else:
        canvas.rect(tx - 3, top, 7, 1, guard)
        canvas.column(tx, top - 4, top, grip)
        canvas.put(tx, top - 5, guard)


def rim_ridge(canvas, heights, body, rim, bottom=None, rim_every=1):
    """Filled skyline with a light rim along its top edge."""
    bottom = canvas.height if bottom is None else bottom
    for x, h in enumerate(heights):
        top = round(h)
        canvas.column(x, top, bottom, body)
        if x % rim_every == 0:
            canvas.put(x, top, rim)
            if round(heights[x - 1]) > top + 1:
                canvas.put(x, top + 1, rim)


def cypress(canvas, x, base, height, body, rim):
    """Tall flame-shaped cypress with a lit edge."""
    for i in range(height):
        f = i / height
        half = max(0, round(math.sin(math.pi * min(1.0, f * 1.15 + 0.05)) * height * 0.13 + (0.4 if f < 0.7 else 0)))
        y = base - i
        for dx in range(-half, half + 1):
            canvas.put(x + dx, y, body)
        if half:
            canvas.put(x + half, y, rim if i % 3 else body)
    canvas.column(x, base - height - 2, base - height, body)


def pine_tree(canvas, x, base, height, body, rim, seed):
    """Conifer built from drooping tiers, rim-lit on the right."""
    rng = random.Random(f"pinetree-{seed}")
    canvas.column(x, base - 3, base + 1, body)
    tiers = max(3, height // 5)
    for t in range(tiers):
        f = t / tiers
        tier_base = base - 2 - round(f * (height - 4))
        half = round((1 - f) * height * 0.28) + 1
        for k in range(6):
            y = tier_base - k
            w = max(0, half - k - rng.choice((0, 0, 1)))
            for dx in range(-w, w + 1):
                canvas.put(x + dx, y, body)
            if w:
                canvas.put(x + w, y, rim)
    canvas.column(x, base - height - 1, base - height + 3, body)


def gothic_castle(canvas, x, base, body, rim, window, banner, seed, height_scale=1.0):
    """A towered keep with steep spires, crenellations, banners and lit slits."""
    rng = random.Random(f"gothic-{seed}")
    towers = ((-36, 18, 2, "flat"), (-29, 30, 2, "spire"), (-20, 24, 3, "cone"), (-11, 40, 3, "spire"),
              (-3, 30, 6, "keep"), (6, 58, 3, "spire"), (14, 34, 3, "cone"), (23, 44, 2, "spire"),
              (31, 26, 3, "cone"), (38, 16, 2, "flat"))
    canvas.rect(x - 40, base - 12, 82, 13, body)
    for cx in range(x - 40, x + 42, 2):
        canvas.put(cx, base - 13, body)
    for dx, h, half, roof in towers:
        h = max(14, round(h * height_scale))
        tx, top = x + dx, base - h
        canvas.rect(tx - half, top, half * 2 + 1, h, body)
        canvas.column(tx + half, top, base - 12, rim)
        if roof in ("spire", "cone"):
            tall = (half * 2 + 3) * (3.2 if roof == "spire" else 1.8) * height_scale
            canvas.polygon([(tx - half - 1.5, top + 1), (tx + half + 2.5, top + 1), (tx + 0.5, top - tall)], body)
            canvas.line(tx + 1, round(top - tall + 2), tx + half + 1, top, rim)
            if roof == "spire" and rng.random() < 0.8:
                flag_top = round(top - tall) - 4
                canvas.column(tx, flag_top, round(top - tall) + 1, body)
                canvas.rect(tx + 1, flag_top, 3, 2, banner)
        elif roof == "keep":
            for cx in range(tx - half - 1, tx + half + 2, 2):
                canvas.put(cx, top - 1, body)
            canvas.disc(tx, top + 8, 2.2, window)
            canvas.disc(tx, top + 8, 1.0, body)
        else:
            for cx in range(tx - half - 1, tx + half + 2, 2):
                canvas.put(cx, top - 1, body)
        for wy in range(top + 4, base - 14, 6):
            if rng.random() < 0.55:
                canvas.column(tx + rng.choice((-1, 0, 0, 1)) * (half > 2), wy, wy + 2, window)
    canvas.polygon([(x - 4, base + 1), (x - 4, base - 6), (x - 1.5, base - 9), (x + 2, base - 6), (x + 2, base + 1)], window)


def waterfall(canvas, x, top, bottom, width, colors, seed):
    """Vertical streaked cascade with foam at its foot: colors = (deep, mid, light, foam)."""
    rng = random.Random(f"falls-{seed}")
    phases = [rng.uniform(0, 7) for _ in range(width)]
    for y in range(top, bottom):
        sway = round(math.sin(y * 0.18 + seed) * 0.6)
        for dx in range(width):
            streak = math.sin(y * 0.35 + phases[dx]) + rng.uniform(-0.35, 0.35)
            color = colors[2] if streak > 0.65 else colors[1] if streak > -0.4 else colors[0]
            canvas.put(x + dx + sway, y, color)
    for k in range(40):
        a = rng.uniform(0, math.pi)
        r = rng.uniform(0, width * 0.9)
        canvas.put(round(x + width / 2 + math.cos(a) * r * 1.4), round(bottom - math.sin(a) * r * 0.5), colors[3])


def mist(canvas, y0, y1, color, seed, density=0.6, period=None):
    """Noise-shaped translucent wisps inside a horizontal band."""
    period = period or canvas.width
    for x in range(canvas.width):
        n = raster.periodic_noise(x, period, f"mist-{seed}", octaves=3, base_cells=6)
        for y in range(y0, y1):
            d = abs((y - y0) / max(1, y1 - y0) * 2 - 1)
            strength = density * max(0.0, n - 0.35) * 1.8 * (1 - d * d)
            if strength > bayer(x, y):
                canvas.put(x, y, color)


def flagstones(canvas, top, bottom, gap, stone, light, shadow, moss, seed):
    """Large irregular paving stones in staggered rows, lit on the upper-left."""
    rng = random.Random(f"flag-{seed}")
    canvas.rect(0, top, canvas.width, bottom - top, gap)
    rows = [(top, (bottom - top) // 2), (top + (bottom - top) // 2, bottom - top - (bottom - top) // 2)]
    for r, (y0, h) in enumerate(rows):
        x = rng.randint(0, 8) + r * 7
        while x < canvas.width + 12:
            w = rng.randint(10, 20)
            inset = [rng.uniform(0, 1.6) for _ in range(4)]
            pts = [(x + inset[0], y0 + 1), (x + w - 1 - inset[1], y0 + 1 + inset[1] * 0.5),
                   (x + w - 1, y0 + h - 1 - inset[2] * 0.5), (x + inset[3], y0 + h - 1)]
            canvas.polygon(pts, stone)
            canvas.line(round(pts[0][0]) + 1, y0 + 1, round(pts[1][0]) - 1, y0 + 1, light)
            canvas.column(round(pts[0][0]), y0 + 2, y0 + h - 2, light)
            canvas.line(round(pts[3][0]) + 1, y0 + h - 2, round(pts[2][0]), y0 + h - 2, shadow)
            if rng.random() < 0.35:
                cx = x + rng.randint(3, w - 4)
                canvas.line(cx, y0 + 2, cx + rng.randint(-2, 2), y0 + h - 3, shadow)
            if rng.random() < 0.4:
                canvas.put(x + w + 1, y0 + rng.randint(1, h - 2), moss)
                canvas.put(x + w + 1, y0 + rng.randint(1, h - 2), moss)
            x += w + rng.randint(2, 3)


def dirt_path(canvas, top, bottom, dirt, speck, stone, light, shadow, edge, seed):
    """Trodden earth with scattered half-buried flat stones and grassy edges."""
    rng = random.Random(f"dirt-{seed}")
    canvas.rect(0, top, canvas.width, bottom - top, dirt)
    for x in range(canvas.width):
        for _ in range(2):
            if rng.random() < 0.3:
                canvas.put(x, rng.randint(top, bottom - 1), speck)
        if rng.random() < 0.6:
            canvas.column(x, top - rng.randint(0, 2), top + 1, edge)
        if rng.random() < 0.5:
            canvas.column(x, bottom - 1, bottom + rng.randint(0, 2), edge)
    x = rng.randint(0, 20)
    while x < canvas.width:
        w, h = rng.randint(5, 12), rng.randint(2, 4)
        y = rng.randint(top + 2, bottom - h - 1)
        canvas.rect(x + 1, y, w - 2, 1, light)
        canvas.rect(x, y + 1, w, h - 1, stone)
        canvas.rect(x + 1, y + h, w - 1, 1, shadow)
        x += w + rng.randint(8, 30)


def crag(canvas, cx, base, width, height, body, rim, shade, seed):
    """Rocky hill: jagged silhouette, lit rim, darker lower flank and a few boulders."""
    rng = random.Random(f"crag-{seed}")
    steps = 14
    top_points = []
    for i in range(steps + 1):
        f = i / steps
        bump = math.sin(math.pi * f) ** 0.7
        top_points.append((cx - width / 2 + f * width, base - height * bump + rng.uniform(-2.2, 2.2) * bump))
    shape = [(cx - width / 2 - 4, base)] + top_points + [(cx + width / 2 + 4, base)]
    canvas.polygon(shape, body)
    for (x1, y1), (x2, y2) in zip(top_points, top_points[1:]):
        canvas.line(round(x1), round(y1), round(x2), round(y2), rim)
    for x in range(round(cx - width / 2), round(cx + width / 2)):
        for y in range(round(base - height * 0.35), base + 1):
            if canvas.get(x, y) == body and paint_threshold(x, y, (y - (base - height * 0.35)) / (height * 0.35)):
                canvas.put(x, y, shade)
    for _ in range(6):
        bx = rng.uniform(cx - width * 0.4, cx + width * 0.4)
        by = base - rng.uniform(0, height * 0.5)
        if canvas.get(round(bx), round(by)) in (body, shade):
            canvas.rect(round(bx), round(by), 3, 2, shade)
            canvas.put(round(bx), round(by) - 1, rim)


def paint_threshold(x, y, strength):
    return strength > bayer(x, y)


def bushes(canvas, base, x0, x1, body, rim, blooms, seed, min_w=6, max_w=15, min_h=4, max_h=8):
    """Row of rounded flowering mounds (lavender, heather) with bloom speckles."""
    rng = random.Random(f"bush-{seed}")
    x = x0
    while x < x1:
        w, h = rng.randint(min_w, max_w), rng.randint(min_h, max_h)
        cx = x + w / 2
        for dx in range(w):
            f = (dx - w / 2 + 0.5) / (w / 2)
            top = base - round(h * math.sqrt(max(0.0, 1 - f * f)))
            canvas.column(x + dx, top, base + 1, body)
            canvas.put(x + dx, top, rim)
            for k in range(rng.randint(0, 2)):
                if rng.random() < 0.8:
                    canvas.put(x + dx, top + rng.randint(0, max(1, (base - top) // 2)), rng.choice(blooms))
        x += w - rng.randint(1, 4)


def blade(canvas, x, base, height, lean, color, tip=None):
    """A single curved grass blade."""
    for i in range(height):
        f = i / max(1, height - 1)
        px = x + round(lean * f * f)
        canvas.put(px, base - i, tip if (tip is not None and i >= height - 2) else color)


def standing_stones(canvas, x, base, body, rim, seed):
    rng = random.Random(f"stones-{seed}")
    for k in range(3):
        w, h = rng.randint(4, 6), rng.randint(9, 17)
        sx = x + k * 9 + rng.randint(-1, 1)
        canvas.polygon([(sx, base), (sx + 0.5, base - h + 2), (sx + w * 0.5, base - h), (sx + w, base - h + 3), (sx + w, base)], body)
        canvas.column(sx + w - 1, base - h + 3, base, rim)


def ruined_arch(canvas, x, base, body, rim, dark):
    """Two broken pillars joined by a half-collapsed arch."""
    for px in (x, x + 22):
        canvas.rect(px, base - 28, 6, 28, body)
        canvas.column(px + 5, base - 28, base, rim)
        for by in range(base - 26, base, 5):
            canvas.rect(px, by, 6, 1, dark)
    for k in range(18):
        a = math.pi * (0.05 + 0.6 * k / 17)
        ax = x + 14 - math.cos(a) * 13
        ay = base - 28 - math.sin(a) * 9
        canvas.rect(round(ax) - 1, round(ay) - 1, 3, 3, body)
        canvas.put(round(ax), round(ay) - 2, rim)
