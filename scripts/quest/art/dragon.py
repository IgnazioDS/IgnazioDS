"""The Ashen Wyrm: the boss, built on the shaded rig and facing left.

A pose drives wing beat, neck curve, head/jaw angles, body bob and tail wave;
`frames()` renders the hover cycle, breath, roar, hurt flash and death slump.
"""

import dataclasses
import math
from dataclasses import dataclass
from functools import lru_cache

from . import raster, rig
from .rig import Capsule, Ellipse, Material, Part, Poly, ramp

FRAME_W, FRAME_H = 224, 184
SHIFT = (12, 24)  # rig coordinates -> frame, leaves room for raised wings and the tail

SCALES = Material(ramp("#0a0407", "#16080e", "#261018", "#3a1622", "#561e2c", "#76293a"),
                  spec=raster.rgb("#a4566a"), rim=raster.rgb("#b04a60"),
                  shininess=26, spec_cut=0.93, rim_cut=0.64, ambient=0.14)
BELLY = Material(ramp("#1e0e0c", "#36180f", "#542a18", "#74442a"), rim=raster.rgb("#9a5a36"), ambient=0.2)
SPINE = Material(ramp("#0e0909", "#241a17", "#40322a", "#62523f"), spec=raster.rgb("#b8a88c"), ambient=0.2)
MEMBRANE = Material(ramp("#12040a", "#240812", "#3c0e1c", "#5a1628"), rim=raster.rgb("#b8344c"), ambient=0.18, rim_cut=0.4)
HORN = Material(ramp("#161210", "#3a2e24", "#6a5a48", "#a89880"), spec=raster.rgb("#efe4d0"), ambient=0.25)
FLASH = Material(ramp("#f0d8d8", "#fff0ec", "#ffffff"), ambient=0.7)
EYE, EYE_CORE = raster.rgb("#ff7a2e"), raster.rgb("#ffe07a")
MAW = raster.rgb("#ffb040")


@dataclass(frozen=True)
class WyrmPose:
    bob: float = 0.0
    wing: float = 0.0        # -1 wings raised, +1 wings swept down
    neck: float = 0.0        # -1 reared back, +1 lunging low
    head: float = 0.0        # head pitch in degrees (+ = nose down)
    jaw: float = 4.0         # jaw opening in degrees
    tail: float = 0.0        # tail wave phase (radians)
    slump: float = 0.0       # 0 alive, 1 collapsed


def _rot(points, origin, degrees):
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    return tuple((origin[0] + x * ca - y * sa, origin[1] + x * sa + y * ca) for x, y in points)


def _bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * d for a, b, c, d in zip(p0, p1, p2, p3))


def _wing(shoulder, attach, beat, far):
    """Arm bones, four long fingers and scalloped membrane panels; beat -1 raised, +1 swept down."""
    shade = -0.22 if far else 0.0
    lift = (beat + 1) / 2
    upper = -80 + 70 * lift + (6 if far else 0)
    elbow = (shoulder[0] + math.cos(math.radians(upper)) * 34, shoulder[1] + math.sin(math.radians(upper)) * 34)
    fore = -100 + 95 * lift + (8 if far else 0)
    wrist = (elbow[0] + math.cos(math.radians(fore)) * 28, elbow[1] + math.sin(math.radians(fore)) * 28)
    fingers = []
    for spread, length in ((0, 44), (24, 58), (48, 52), (72, 40)):
        angle = fore + 58 + spread - 20 * lift
        fingers.append((wrist[0] + math.cos(math.radians(angle)) * length,
                        wrist[1] + math.sin(math.radians(angle)) * length))
    outline = [shoulder, elbow, wrist, fingers[0]]
    for a, b in zip(fingers, fingers[1:]):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        outline += [(mid[0] + (wrist[0] - mid[0]) * 0.38, mid[1] + (wrist[1] - mid[1]) * 0.38), b]
    outline += [((fingers[-1][0] + attach[0]) / 2 + 4, (fingers[-1][1] + attach[1]) / 2 + 6), attach]
    parts = [Part(Poly(tuple(outline), bevel=3.5), MEMBRANE, bulge=0.2, shade=shade, fold=(11.0, 0.3, 0.2), cast=False)]
    parts += [Part(Capsule(wrist, tip, 2.2, 0.8), SPINE, shade=shade - 0.05, seam=False, cast=False) for tip in fingers]
    parts += [Part(Capsule(shoulder, elbow, 5.0, 3.4), SCALES, shade=shade),
              Part(Capsule(elbow, wrist, 3.4, 2.4), SCALES, shade=shade),
              Part(Capsule(wrist, (wrist[0] - 4, wrist[1] - 6), 1.8, 0.6), SPINE, shade=shade)]
    return parts


def _tail(root, phase, slump):
    points = [root]
    for k in range(1, 10):
        x = root[0] + k * 5.4 + math.sin(k * 0.6 + phase) * 3 * (1 - slump)
        y = root[1] + k * (4.6 + 1.5 * slump) + math.sin(k * 0.8 + phase) * 2.5 * (1 - slump)
        points.append((x, y))
    parts = []
    for k, (a, b) in enumerate(zip(points, points[1:])):
        r0, r1 = 9.0 - k * 0.85, 9.0 - (k + 1) * 0.85
        parts.append(Part(Capsule(a, b, max(1.3, r0), max(1.1, r1)), SCALES, seam=False))
    tx, ty = points[-1]
    parts.append(Part(Poly(((tx - 3, ty - 2), (tx + 6, ty - 5), (tx + 4, ty + 2), (tx + 5, ty + 9), (tx - 3, ty + 3)), bevel=1.2), SPINE))
    return parts


def build_parts(pose):
    b = pose.bob + 26 * pose.slump
    hips, body, chest = (134, 104 + b), (112, 92 + b), (92, 80 + b)
    neck_base = (86, 70 + b)
    head_base = (42 - 6 * pose.neck, 50 + b + 26 * pose.neck + 34 * pose.slump)
    ctrl1 = (76, 40 + b + 12 * pose.neck)
    ctrl2 = (52, 30 + b + 20 * pose.neck)

    parts = _wing((116, 66 + b), (140, 96 + b), pose.wing, far=True)
    parts += _tail((146, 110 + b), pose.tail, pose.slump)
    parts += [Part(Ellipse((138, 118 + b), 7, 11, 0.4), SCALES, shade=-0.12),
              Part(Capsule((138, 124 + b), (132, 140 + b), 4.0, 2.8), SCALES, shade=-0.12),
              Part(Capsule((132, 140 + b), (125, 145 + b), 2.0, 1.0), SPINE)]
    parts += [Part(Ellipse(hips, 18, 15, 0.2), SCALES), Part(Ellipse(body, 30, 20, -0.5), SCALES),
              Part(Ellipse(chest, 20, 18, -0.2), SCALES)]
    neck = [_bezier(neck_base, ctrl1, ctrl2, head_base, k / 8) for k in range(9)]
    for k, (a, c) in enumerate(zip(neck, neck[1:])):
        parts.append(Part(Capsule(a, c, 11.0 - k * 0.55, 11.0 - (k + 1) * 0.55), SCALES, seam=False, cast=False))
    for k, (a, c) in enumerate(zip(neck, neck[1:])):
        r = 5.0 - k * 0.3
        parts.append(Part(Capsule((a[0] - 4, a[1] + 5), (c[0] - 4, c[1] + 5), r, r - 0.3), BELLY,
                          seam=False, cast=False, bulge=0.6))
    for k, a in enumerate(neck[1:-1]):
        size = 5.5 - k * 0.45
        parts.append(Part(Poly(((a[0] - size * 0.4, a[1] - 7), (a[0] + size, a[1] - 9 - size), (a[0] + size * 0.9, a[1] - 5)),
                               bevel=0.8), SPINE, seam=False, cast=False))
    for k, sx in enumerate(range(100, 150, 8)):
        size = 6 - abs(k - 2) * 0.9
        top = body[1] - 18 - (150 - sx) * 0.28 + (sx - 100) * 0.55
        parts.append(Part(Poly(((sx - 2, top + 4), (sx + size, top - size), (sx + size * 0.8, top + 4)), bevel=0.8),
                          SPINE, seam=False, cast=False))
    parts += [Part(Capsule((88, 94 + b), (82, 108 + b), 4.0, 3.0), SCALES),
              Part(Capsule((82, 108 + b), (76, 112 + b), 2.2, 1.0), SPINE)]
    head_parts, details = _head(head_base, pose)
    parts += head_parts
    parts += _wing((102, 72 + b), (128, 100 + b), pose.wing * 0.92, far=False)
    return parts, details


def _head(base, pose):
    angle = pose.head
    k = 1.35
    skull = _rot(tuple((x * k, y * k) for x, y in
                       ((10, -2), (4, -10), (-10, -9), (-24, -6), (-32, -3), (-34, 1), (-28, 3), (-8, 5), (6, 7))), base, angle)
    hinge = (4 * k, 4 * k)
    jaw_local = _rot(tuple((x * k, y * k) for x, y in ((0, 0), (-26, 2), (-29, 5), (-8, 7), (2, 4))), hinge, pose.jaw)
    jaw = _rot(jaw_local, base, angle)
    horn_a = _rot(tuple((x * k, y * k) for x, y in ((4, -8), (20, -18), (30, -16))), base, angle)
    horn_b = _rot(tuple((x * k, y * k) for x, y in ((0, -7), (12, -20), (18, -24))), base, angle)
    brow = _rot(tuple((x * k, y * k) for x, y in ((-6, -9), (-20, -8))), base, angle)
    parts = [
        Part(Capsule(horn_b[0], horn_b[1], 2.4, 1.6), HORN, shade=-0.15),
        Part(Capsule(horn_b[1], horn_b[2], 1.6, 0.6), HORN, shade=-0.15),
        Part(Poly(jaw, bevel=2.0), SCALES, bulge=0.7),
        Part(Poly(skull, bevel=3.2), SCALES, bulge=0.8),
        Part(Capsule(brow[0], brow[1], 1.8, 1.2), SCALES, shade=0.12, seam=False),
        Part(Capsule(horn_a[0], horn_a[1], 2.8, 1.8), HORN),
        Part(Capsule(horn_a[1], horn_a[2], 1.8, 0.6), HORN),
    ]
    for cheek in ((6, 4, 16, 9), (8, 0, 19, 2), (2, 8, 10, 14)):
        a, c = _rot(((cheek[0] * k, cheek[1] * k), (cheek[2] * k, cheek[3] * k)), base, angle)
        parts.append(Part(Capsule(a, c, 1.4, 0.4), SPINE, seam=False, cast=False))
    nose_a, nose_c = _rot(((-30 * k, -3 * k), (-27 * k, -8 * k)), base, angle)
    parts.append(Part(Capsule(nose_a, nose_c, 1.6, 0.5), HORN, seam=False, cast=False))
    ex, ey = _rot(((-16, -5),), base, angle)[0]
    nx, ny = _rot(((-40, -3),), base, angle)[0]
    details = [(round(ex), round(ey), EYE_CORE), (round(ex) - 1, round(ey), EYE), (round(ex) + 1, round(ey), EYE),
               (round(ex) - 2, round(ey), raster.rgba("#ff7a2e", 120)), (round(nx), round(ny), raster.rgb("#060204"))]
    if pose.jaw > 14:
        for t in (0.25, 0.45, 0.65):
            mx, my = _rot((((-35 * t) + 3, 4 + pose.jaw * 0.1),), base, angle)[0]
            details.append((round(mx), round(my), MAW))
    return parts, details


def _shift_shape(shape, dx, dy):
    if isinstance(shape, Capsule):
        return Capsule((shape.a[0] + dx, shape.a[1] + dy), (shape.b[0] + dx, shape.b[1] + dy), shape.r0, shape.r1)
    if isinstance(shape, Ellipse):
        return Ellipse((shape.c[0] + dx, shape.c[1] + dy), shape.rx, shape.ry, shape.angle)
    return Poly(tuple((x + dx, y + dy) for x, y in shape.points), shape.bevel)


def _render(pose, flash=False):
    parts, details = build_parts(pose)
    dx, dy = SHIFT
    parts = [dataclasses.replace(p, shape=_shift_shape(p.shape, dx, dy)) for p in parts]
    details = [(x + dx, y + dy, c) for x, y, c in details]
    if flash:
        parts = [dataclasses.replace(p, material=FLASH, shade=0.0) for p in parts]
        details = []
    return rig.render(parts, FRAME_W, FRAME_H, details)


HOVER = tuple(WyrmPose(bob=bob, wing=wing, tail=tail, neck=-0.1, head=-4)
              for bob, wing, tail in ((0, -1.0, 0.0), (2, -0.2, 1.6), (4, 0.9, 3.1), (2, 0.1, 4.7)))
BREATH = (
    WyrmPose(bob=1, wing=-0.6, neck=-0.6, head=-18, jaw=10, tail=1.0),
    WyrmPose(bob=3, wing=0.5, neck=0.7, head=16, jaw=30, tail=2.2),
    WyrmPose(bob=3, wing=0.7, neck=0.8, head=20, jaw=34, tail=3.0),
)
ROAR = WyrmPose(bob=0, wing=-1.0, neck=-0.8, head=-30, jaw=36, tail=0.5)
HURT = WyrmPose(bob=5, wing=0.3, neck=-0.5, head=-26, jaw=22, tail=2.5)
DEATH = (WyrmPose(bob=6, wing=0.8, neck=0.4, head=24, jaw=18, tail=1.0, slump=0.4),
         WyrmPose(bob=8, wing=1.0, neck=0.9, head=38, jaw=10, tail=0.5, slump=1.0))

FRAME_NAMES = ("hover0", "hover1", "hover2", "hover3", "breath0", "breath1", "breath2",
               "roar", "hurt", "death0", "death1")


@lru_cache(maxsize=1)
def frames():
    poses = (*HOVER, *BREATH, ROAR, HURT, *DEATH)
    named = {}
    for name, pose in zip(FRAME_NAMES, poses):
        named[name] = _render(pose, flash=(name == "hurt"))
    return named


def mouth(pose_name):
    """Approximate mouth position in frame coordinates for fire placement."""
    base = {"breath1": (40, 104), "breath2": (38, 108)}.get(pose_name, (30, 66))
    return (base[0] + SHIFT[0], base[1] + SHIFT[1])
