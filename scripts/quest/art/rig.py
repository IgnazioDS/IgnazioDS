"""2.5D shaded part renderer for characters.

A frame is a list of Parts painted back to front. Each part is a simple
volume — tapered capsule, ellipse, or bevelled polygon — that yields a surface
normal per pixel. Pixels are lit with a key light (diffuse), a metallic
highlight (Blinn-Phong) and a cold rim light from behind, kept as continuous
values while parts overlap (so later parts can cast contact shadows), then
quantized onto small per-material color ramps with ordered dithering.

The result reads as hand-shaded pixel art, but animations can use as many
frames as they need with perfectly consistent volume and lighting.
"""

import math
from dataclasses import dataclass

from . import raster


def _norm(v):
    length = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / length for c in v)


KEY = _norm((-0.55, -0.72, 0.62))    # upper-left, in front
RIM = _norm((0.85, -0.45, -0.35))    # behind, upper right (the moon)
HALF = _norm((KEY[0], KEY[1], KEY[2] + 1.0))


@dataclass(frozen=True)
class Material:
    ramp: tuple                 # raster colors, dark -> light
    spec: object = None         # highlight color or None
    rim: object = None          # rim-light color or None
    shininess: float = 22.0
    spec_cut: float = 0.82
    rim_cut: float = 0.5
    ambient: float = 0.16
    emissive: bool = False      # ignores lighting, always the brightest ramp entry


@dataclass(frozen=True)
class Capsule:
    a: tuple
    b: tuple
    r0: float
    r1: float


@dataclass(frozen=True)
class Ellipse:
    c: tuple
    rx: float
    ry: float
    angle: float = 0.0


@dataclass(frozen=True)
class Poly:
    points: tuple
    bevel: float = 2.0


@dataclass(frozen=True)
class Part:
    shape: object
    material: Material
    bulge: float = 1.0          # 0 flat plate, 1 fully rounded
    tilt: tuple = (0.0, 0.0)    # base normal lean for flat plates
    shade: float = 0.0          # constant value offset (-darker / +lighter)
    seam: bool = True           # dark separation line where it overlaps earlier parts
    cast: bool = True           # darken earlier parts just below/right of it
    fold: tuple = None          # (period_px, strength, phase) vertical cloth folds


@dataclass
class _Pixel:
    material: Material
    value: float
    spec: bool = False
    rim: bool = False
    part: int = 0


def _capsule(shape, px, py):
    ax, ay = shape.a
    bx, by = shape.b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy or 1e-9
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    cx, cy = ax + dx * t, ay + dy * t
    r = shape.r0 + (shape.r1 - shape.r0) * t
    ox, oy = px - cx, py - cy
    d = math.hypot(ox, oy)
    if d > r:
        return None
    k = d / r if r else 0.0
    nz = math.sqrt(max(0.0, 1 - k * k))
    return (ox / r if r else 0.0, oy / r if r else 0.0, nz)


def _ellipse(shape, px, py):
    ca, sa = math.cos(-shape.angle), math.sin(-shape.angle)
    lx = (px - shape.c[0]) * ca - (py - shape.c[1]) * sa
    ly = (px - shape.c[0]) * sa + (py - shape.c[1]) * ca
    qx, qy = lx / shape.rx, ly / shape.ry
    k2 = qx * qx + qy * qy
    if k2 > 1:
        return None
    ca2, sa2 = math.cos(shape.angle), math.sin(shape.angle)
    return (qx * ca2 - qy * sa2, qx * sa2 + qy * ca2, math.sqrt(1 - k2))


def _poly(shape, px, py):
    pts = shape.points
    inside, best, edge = False, float("inf"), (0.0, 0.0)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
        ex, ey = x2 - x1, y2 - y1
        length2 = ex * ex + ey * ey or 1e-9
        t = max(0.0, min(1.0, ((px - x1) * ex + (py - y1) * ey) / length2))
        d = math.hypot(px - (x1 + ex * t), py - (y1 + ey * t))
        if d < best:
            best = d
            length = math.sqrt(length2)
            edge = (ey / length, -ex / length)
    if not inside:
        return None
    if best >= shape.bevel:
        return (0.0, 0.0, 1.0)
    k = 1 - best / shape.bevel
    # outward normal sign depends on winding; point it away from the interior
    nx, ny = edge
    if _poly_contains(pts, px + nx * 0.5, py + ny * 0.5):
        nx, ny = -nx, -ny
    return (nx * k * 0.85, ny * k * 0.85, math.sqrt(max(0.05, 1 - (k * 0.85) ** 2)))


def _poly_contains(pts, px, py):
    inside = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


_SAMPLERS = {Capsule: _capsule, Ellipse: _ellipse, Poly: _poly}


def _bounds(shape, width, height):
    if isinstance(shape, Capsule):
        r = max(shape.r0, shape.r1) + 1
        xs, ys = (shape.a[0], shape.b[0]), (shape.a[1], shape.b[1])
        box = (min(xs) - r, min(ys) - r, max(xs) + r, max(ys) + r)
    elif isinstance(shape, Ellipse):
        r = max(shape.rx, shape.ry) + 1
        box = (shape.c[0] - r, shape.c[1] - r, shape.c[0] + r, shape.c[1] + r)
    else:
        xs = [p[0] for p in shape.points]
        ys = [p[1] for p in shape.points]
        box = (min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1)
    return (max(0, math.floor(box[0])), max(0, math.floor(box[1])),
            min(width - 1, math.ceil(box[2])), min(height - 1, math.ceil(box[3])))


def _light(part, normal, px):
    nx, ny, nz = normal
    tx, ty = part.tilt
    b = part.bulge
    n = _norm((tx * (1 - b) + nx * b, ty * (1 - b) + ny * b, (1 - b) + nz * b))
    if part.fold:
        period, strength, phase = part.fold
        wave = math.sin((px / period + phase) * math.tau)
        n = _norm((n[0] + wave * strength, n[1], n[2]))
    diffuse = max(0.0, n[0] * KEY[0] + n[1] * KEY[1] + n[2] * KEY[2])
    mat = part.material
    value = mat.ambient + (1 - mat.ambient) * diffuse + part.shade
    spec = mat.spec is not None and max(0.0, sum(a * c for a, c in zip(n, HALF))) ** mat.shininess > mat.spec_cut
    rim = mat.rim is not None and sum(a * c for a, c in zip(n, RIM)) > mat.rim_cut
    return value, spec, rim


def render(parts, width, height, details=None):
    """Paint parts back to front, then quantize. details: [(x, y, color)] overrides."""
    buf = [None] * (width * height)
    for index, part in enumerate(parts, start=1):
        sampler = _SAMPLERS[type(part.shape)]
        x0, y0, x1, y1 = _bounds(part.shape, width, height)
        mask = set()
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                normal = sampler(part.shape, x + 0.5, y + 0.5)
                if normal is None:
                    continue
                if part.material.emissive:
                    buf[y * width + x] = _Pixel(part.material, 1.0, part=index)
                else:
                    value, spec, rim = _light(part, normal, x)
                    buf[y * width + x] = _Pixel(part.material, value, spec, rim, index)
                mask.add((x, y))
        _seams_and_shadows(buf, width, height, part, index, mask)
    return _quantize(buf, width, height, details or ())


def _seams_and_shadows(buf, width, height, part, index, mask):
    for x, y in mask:
        pixel = buf[y * width + x]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (nx, ny) in mask or not (0 <= nx < width and 0 <= ny < height):
                continue
            below = buf[ny * width + nx]
            if below is None:
                continue
            if part.seam and below.part < index:
                pixel.value -= 0.22
                pixel.spec = False
            if part.cast and below.part < index and (dx, dy) in ((1, 0), (0, 1)):
                below.value -= 0.2
                below.rim = False


def _quantize(buf, width, height, details):
    canvas = raster.Canvas(width, height)
    for y in range(height):
        for x in range(width):
            pixel = buf[y * width + x]
            if pixel is None:
                continue
            mat = pixel.material
            if pixel.rim and mat.rim is not None:
                color = mat.rim
            elif pixel.spec and mat.spec is not None:
                color = mat.spec
            else:
                color = raster.banded_pick(mat.ramp, pixel.value, x, y)
            canvas.put(x, y, color)
    for x, y, color in details:
        canvas.put(x, y, color)
    return canvas.freeze()


def ramp(*hexes):
    return tuple(raster.rgb(h) for h in hexes)


def _map_shape(shape, point, k):
    if isinstance(shape, Capsule):
        return Capsule(point(shape.a), point(shape.b), shape.r0 * k, shape.r1 * k)
    if isinstance(shape, Ellipse):
        return Ellipse(point(shape.c), shape.rx * k, shape.ry * k, shape.angle)
    return Poly(tuple(point(p) for p in shape.points), shape.bevel * k)


def transform(parts, details=(), scale=1.0, offset=(0.0, 0.0), mirror=None, rotate=0.0, pivot=(0.0, 0.0)):
    """Rotated, scaled, shifted and optionally mirrored copies of parts and details.

    Geometry is transformed *before* shading, so the key light stays upper
    left: a mirrored or banking character is lit correctly instead of carrying
    baked highlights around. Order: rotate (degrees, clockwise on screen)
    about `pivot`, scale, offset, then mirror across x = `mirror`.
    """
    ox, oy = offset
    a = math.radians(rotate)
    ca, sa = math.cos(a), math.sin(a)
    px, py = pivot

    def point(p):
        rx, ry = p[0] - px, p[1] - py
        x = (px + rx * ca - ry * sa) * scale + ox
        y = (py + rx * sa + ry * ca) * scale + oy
        return (mirror - x, y) if mirror is not None else (x, y)

    moved = []
    for part in parts:
        shape = _map_shape(part.shape, point, scale)
        tx, ty = part.tilt
        tilt = (tx * ca - ty * sa, tx * sa + ty * ca)
        if isinstance(shape, Ellipse):
            angle = shape.angle + a
            shape = Ellipse(shape.c, shape.rx, shape.ry, -angle if mirror is not None else angle)
        if mirror is not None:
            tilt = (-tilt[0], tilt[1])
        fold = (part.fold[0] * scale, *part.fold[1:]) if part.fold else None
        moved.append(Part(shape, part.material, part.bulge, tilt, part.shade, part.seam, part.cast, fold))
    marks = []
    for x, y, color in details:
        mx, my = point((x, y))
        marks.append((round(mx), round(my), color))
    return moved, marks
