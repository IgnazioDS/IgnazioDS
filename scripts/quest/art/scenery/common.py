"""Procedural painting primitives shared by every region.

Everything here paints onto a raster.Canvas; tile layers use wrap_x canvases
so ridges, trees and castles continue seamlessly across the tile seam.
"""

import math
import random

from .. import raster


def stars(canvas, count, seed, top, bottom, dim, bright):
    rng = random.Random(f"stars-{seed}")
    for _ in range(count):
        x, y = rng.randrange(canvas.width), rng.randrange(top, bottom)
        if rng.random() < 0.12:
            canvas.put(x, y, bright)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                canvas.put(x + dx, y + dy, dim)
        else:
            canvas.put(x, y, bright if rng.random() < 0.3 else dim)


def halo(canvas, cx, cy, inner, outer, color):
    """Dithered ring of light that fades out between two radii."""
    for y in range(int(cy - outer) - 1, int(cy + outer) + 2):
        for x in range(int(cx - outer) - 1, int(cx + outer) + 2):
            d = math.hypot(x - cx, y - cy)
            if inner <= d <= outer:
                strength = 1 - (d - inner) / (outer - inner)
                if strength * 16 > raster.BAYER4[y % 4][x % 4] + 0.5 + 6:
                    canvas.put(x, y, color)


def moon(canvas, cx, cy, radius, lit, shade, crater, phase_offset=None):
    """Full disc with craters, or a crescent when phase_offset=(dx, dy)."""
    rng = random.Random(f"moon-{cx}-{cy}")
    craters = [
        (cx + rng.uniform(-0.5, 0.5) * radius, cy + rng.uniform(-0.5, 0.5) * radius,
         rng.uniform(0.12, 0.25) * radius)
        for _ in range(5)
    ]
    for y in range(int(cy - radius) - 1, int(cy + radius) + 2):
        for x in range(int(cx - radius) - 1, int(cx + radius) + 2):
            if math.hypot(x - cx, y - cy) > radius:
                continue
            if phase_offset and math.hypot(x - cx - phase_offset[0], y - cy - phase_offset[1]) <= radius:
                continue
            color = lit
            if math.hypot(x - cx + radius * 0.35, y - cy + radius * 0.35) > radius * 1.05:
                color = shade
            if any(math.hypot(x - kx, y - ky) <= kr for kx, ky, kr in craters):
                color = crater if color == lit else shade
            canvas.put(x, y, color)


def ridge_heights(width, seed, base, amplitude, octaves=4, base_cells=4):
    """Tileable skyline heights (one per column)."""
    return [
        base - amplitude * raster.periodic_noise(x, width, seed, octaves=octaves, base_cells=base_cells)
        for x in range(width)
    ]


def haze(canvas, top, bottom, color, density=0.5):
    """Dithered veil that thickens toward `bottom` (atmospheric depth)."""
    span = max(1, bottom - top)
    for y in range(top, bottom):
        strength = (y - top) / span * density
        for x in range(canvas.width):
            if strength * 16 > raster.BAYER4[y % 4][x % 4] + 0.5:
                canvas.put(x, y, color)


def dead_tree(canvas, x, base_y, height, seed, color):
    """Bare, twisted tree grown from recursive branches."""
    rng = random.Random(f"dead-{seed}-{x}")

    def branch(bx, by, angle, length, width):
        if length < 2:
            return
        ex = bx + math.cos(angle) * length
        ey = by + math.sin(angle) * length
        steps = max(1, int(length * 2))
        for s in range(steps + 1):
            px = bx + (ex - bx) * s / steps
            py = by + (ey - by) * s / steps
            for w in range(width):
                canvas.put(round(px) + w - width // 2, round(py), color)
        for _ in range(2 if length > 4 else 1):
            branch(ex, ey, angle + rng.uniform(-0.8, 0.8), length * rng.uniform(0.55, 0.75), max(1, width - 1))

    branch(x, base_y, -math.pi / 2 + rng.uniform(-0.15, 0.15), height * 0.45, 3)


