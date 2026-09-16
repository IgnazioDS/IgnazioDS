"""Pixel rasters: an immutable Image plus a Canvas builder to paint one.

Colors are packed 0xRRGGBBAA ints. Canvas is the only mutable type in the
art pipeline; it is local to whatever function paints a layer and hands out
frozen Image snapshots, mirroring how the simulation keeps its working state
private and emits immutable records.
"""

import math
import random
from dataclasses import dataclass

CLEAR = 0x00000000

# 4x4 ordered-dither thresholds (0..15), the classic pixel-art gradient tool.
BAYER4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


@dataclass(frozen=True)
class Image:
    width: int
    height: int
    pixels: tuple  # row-major 0xRRGGBBAA

    def at(self, x, y):
        return self.pixels[y * self.width + x]


def rgb(hex_color):
    return rgba(hex_color, 255)


def rgba(hex_color, alpha):
    if not (isinstance(hex_color, str) and len(hex_color) == 7 and hex_color[0] == "#"):
        raise ValueError(f"expected '#rrggbb', got {hex_color!r}")
    if not 0 <= alpha <= 255:
        raise ValueError(f"alpha out of range: {alpha}")
    return (int(hex_color[1:], 16) << 8) | alpha


def alpha_of(color):
    return color & 0xFF


class Canvas:
    """Mutable pixel buffer. Writes outside the bounds are silently clipped.

    With wrap_x=True the canvas is a horizontal tile: x wraps around, so any
    shape drawn across an edge continues seamlessly on the other side.
    """

    def __init__(self, width, height, fill=CLEAR, wrap_x=False):
        if width <= 0 or height <= 0:
            raise ValueError(f"canvas must be non-empty, got {width}x{height}")
        self.width = width
        self.height = height
        self.wrap_x = wrap_x
        self._px = [fill] * (width * height)

    def put(self, x, y, color):
        if self.wrap_x:
            x %= self.width
        if 0 <= x < self.width and 0 <= y < self.height:
            self._px[y * self.width + x] = color

    def get(self, x, y):
        if self.wrap_x:
            x %= self.width
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._px[y * self.width + x]
        return CLEAR

    def rect(self, x, y, w, h, color):
        if self.wrap_x:
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    self.put(xx, yy, color)
            return
        for yy in range(max(0, y), min(self.height, y + h)):
            row = yy * self.width
            for xx in range(max(0, x), min(self.width, x + w)):
                self._px[row + xx] = color

    def blit(self, image, x, y):
        """Stamp an image; fully transparent source pixels are skipped."""
        for sy in range(image.height):
            for sx in range(image.width):
                color = image.pixels[sy * image.width + sx]
                if alpha_of(color):
                    self.put(x + sx, y + sy, color)

    def column(self, x, y_top, y_bottom, color):
        for yy in range(max(0, y_top), min(self.height, y_bottom)):
            self.put(x, yy, color)

    def disc(self, cx, cy, radius, color):
        r2 = radius * radius
        for yy in range(math.floor(cy - radius), math.ceil(cy + radius) + 1):
            for xx in range(math.floor(cx - radius), math.ceil(cx + radius) + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r2:
                    self.put(xx, yy, color)

    def polygon(self, points, color):
        """Scanline fill of a simple polygon given as [(x, y), ...]."""
        points = list(points)
        ys = [p[1] for p in points]
        for yy in range(max(0, math.floor(min(ys))), min(self.height, math.ceil(max(ys)) + 1)):
            scan = yy + 0.5
            crossings = []
            for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
                if (y1 <= scan < y2) or (y2 <= scan < y1):
                    crossings.append(x1 + (scan - y1) * (x2 - x1) / (y2 - y1))
            crossings.sort()
            for left, right in zip(crossings[::2], crossings[1::2]):
                for xx in range(round(left), round(right)):
                    self.put(xx, yy, color)

    def line(self, x0, y0, x1, y1, color):
        """Bresenham line between integer endpoints."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.put(x0, y0, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def freeze(self):
        return Image(self.width, self.height, tuple(self._px))


def scale(image, factor):
    """Nearest-neighbour upscale (previews and pre-scaled text)."""
    rows = []
    for y in range(image.height):
        row = image.pixels[y * image.width:(y + 1) * image.width]
        wide = tuple(c for c in row for _ in range(factor))
        rows.extend([wide] * factor)
    return Image(image.width * factor, image.height * factor, tuple(c for r in rows for c in r))


def banded_pick(colors, t, x, y, band=0.1):
    """Pick from a color ramp at t in [0, 1], dithering only near each step.

    Small sprites read as clean clusters of flat color; a little dither at the
    boundary keeps curved surfaces from looking posterised.
    """
    if len(colors) == 1:
        return colors[0]
    span = max(0.0, min(1.0, t)) * (len(colors) - 1)
    base = min(int(span), len(colors) - 2)
    frac = span - base
    if frac < 0.5 - band:
        return colors[base]
    if frac > 0.5 + band:
        return colors[base + 1]
    threshold = (BAYER4[y % 4][x % 4] + 0.5) / 16
    return colors[base + 1] if (frac - 0.5 + band) / (2 * band) > threshold else colors[base]


def periodic_noise(x, period, seed, octaves=4, persistence=0.5, base_cells=4):
    """1D fractal value noise in [0, 1] that repeats every `period` pixels.

    Each octave doubles the lattice resolution; because every lattice wraps
    after an integer number of cells, the sum tiles seamlessly.
    """
    total, norm, amp = 0.0, 0.0, 1.0
    for octave in range(octaves):
        cells = base_cells * (2 ** octave)
        lattice = _lattice(seed, octave, cells)
        pos = (x % period) / period * cells
        i0 = int(pos) % cells
        i1 = (i0 + 1) % cells
        t = pos - int(pos)
        t = t * t * (3 - 2 * t)
        total += amp * (lattice[i0] * (1 - t) + lattice[i1] * t)
        norm += amp
        amp *= persistence
    return total / norm


_LATTICE_CACHE = {}


def _lattice(seed, octave, cells):
    key = (seed, octave, cells)
    if key not in _LATTICE_CACHE:
        rng = random.Random(f"lattice-{seed}-{octave}-{cells}")
        _LATTICE_CACHE[key] = tuple(rng.random() for _ in range(cells))
    return _LATTICE_CACHE[key]
