"""The dark knight's skeleton and armour, expressed as shaded rig parts.

A Pose holds joint angles (degrees from straight down, positive = rotating
forward, the knight faces right). `build_parts` turns a pose into ordered
rig.Parts plus painted details (ember visor, trim), ready for rig.render.
"""

import math
from dataclasses import dataclass

from . import raster
from .rig import Capsule, Ellipse, Material, Part, Poly, ramp

FRAME_W, FRAME_H = 104, 100
GROUND = 96          # frame row the soles rest on (headroom above for raised blades)
THIGH, SHIN = 11.0, 10.5
TORSO = 17.0
UPPER_ARM, FOREARM = 9.0, 8.5
BLADE_LEN = 30.0

STEEL = Material(ramp("#0b0a11", "#14141d", "#1f202b", "#2d2f3f", "#41455c", "#5f6685"),
                 spec=raster.rgb("#c4cde8"), rim=raster.rgb("#8089b0"),
                 shininess=48, spec_cut=0.9, rim_cut=0.5, ambient=0.14)
CLOTH = Material(ramp("#07050a", "#0f0a12", "#19111b", "#251928", "#342338"),
                 rim=raster.rgb("#4c3558"), ambient=0.12, rim_cut=0.55)
LINING = Material(ramp("#2a050f", "#480a18", "#6f1226", "#9e1d37"), rim=raster.rgb("#c43550"), ambient=0.2)
LEATHER = Material(ramp("#0d090b", "#181114", "#261b1e", "#35272a"), rim=raster.rgb("#4a3a40"))
BLADE = Material(ramp("#262b3a", "#454d61", "#737d93", "#a5afc3", "#d6dde8"),
                 spec=raster.rgb("#ffffff"), rim=raster.rgb("#e6ecf7"),
                 shininess=36, spec_cut=0.72, rim_cut=0.35, ambient=0.3)
GOLD = Material(ramp("#3a2810", "#664a20", "#977033", "#c79f52"), spec=raster.rgb("#f4dc98"), ambient=0.25)
SMEAR = Material((raster.rgba("#8e82d6", 90), raster.rgba("#c9c0ff", 160), raster.rgba("#f4f1ff", 220)),
                 emissive=False, ambient=0.55)
EMBER, EMBER_CORE = raster.rgb("#ff5a2e"), raster.rgb("#ffd48c")
EMBER_HAZE = raster.rgba("#ff5a2e", 90)


@dataclass(frozen=True)
class Pose:
    hip_x: float = 40.0
    lean: float = 5.0                 # torso lean forward (degrees)
    head: float = 0.0                 # extra head tilt forward
    near_thigh: float = 6.0
    near_shin: float = 2.0
    far_thigh: float = -8.0
    far_shin: float = -10.0
    near_upper: float = 18.0
    near_fore: float = 58.0
    far_upper: float = -8.0
    far_fore: float = 14.0
    sword: float = 62.0               # blade direction from down, forward positive
    hip_y: float = None               # None: lock the lowest foot to the ground
    cape: tuple = ()                  # chain points from the cape simulation
    smear: tuple = ()                 # ((upper, fore, sword) from, (upper, fore, sword) to): slash trail swept by the tip
    streak: float = 0.0               # thrust speed-streak length behind the blade (0 none)
    planted: bool = False             # sword tip rests in the ground (sit/kneel)


def seg(origin, angle, length):
    a = math.radians(angle)
    return (origin[0] + math.sin(a) * length, origin[1] + math.cos(a) * length)


def _foot_drop(thigh, shin):
    return THIGH * math.cos(math.radians(thigh)) + SHIN * math.cos(math.radians(shin))


def joints(pose):
    """Joint positions for a pose (dict of name -> (x, y))."""
    drop = max(_foot_drop(pose.near_thigh, pose.near_shin), _foot_drop(pose.far_thigh, pose.far_shin))
    hip_y = pose.hip_y if pose.hip_y is not None else GROUND - 2.5 - drop
    hip = (pose.hip_x, hip_y)
    lean = math.radians(pose.lean)
    neck = (hip[0] + math.sin(lean) * TORSO, hip[1] - math.cos(lean) * TORSO)
    j = {"hip": hip, "neck": neck}
    j["head"] = (neck[0] + math.sin(lean) * 5.5 + 1.2, neck[1] - math.cos(lean) * 5.5)
    j["near_shoulder"] = (neck[0] + 0.5, neck[1] + 3.0)
    j["far_shoulder"] = (neck[0] - 2.0, neck[1] + 3.5)
    j["near_elbow"] = seg(j["near_shoulder"], pose.near_upper, UPPER_ARM)
    j["near_hand"] = seg(j["near_elbow"], pose.near_fore, FOREARM)
    j["far_elbow"] = seg(j["far_shoulder"], pose.far_upper, UPPER_ARM)
    j["far_hand"] = seg(j["far_elbow"], pose.far_fore, FOREARM)
    for side, dx in (("near", 1.8), ("far", -1.8)):
        top = (hip[0] + dx, hip[1] + 1.0)
        knee = seg(top, getattr(pose, f"{side}_thigh"), THIGH)
        ankle = seg(knee, getattr(pose, f"{side}_shin"), SHIN)
        j[f"{side}_hip"], j[f"{side}_knee"], j[f"{side}_ankle"] = top, knee, ankle
    return j


def _rotate(points, origin, degrees):
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    ox, oy = origin
    return tuple((ox + (x - ox) * ca - (y - oy) * sa, oy + (x - ox) * sa + (y - oy) * ca) for x, y in points)


def _leg(j, side, far):
    shade = -0.16 if far else 0.0
    hip, knee, ankle = j[f"{side}_hip"], j[f"{side}_knee"], j[f"{side}_ankle"]
    ax, ay = ankle
    sabaton = Poly(((ax - 2.6, ay - 2.2), (ax + 2.0, ay - 2.0), (ax + 6.2, ay + 0.8),
                    (ax + 6.0, ay + 2.6), (ax - 3.0, ay + 2.6)), bevel=1.5)
    return [
        Part(Capsule(hip, knee, 4.4, 3.3), STEEL, shade=shade),
        Part(Capsule(knee, ankle, 3.3, 2.6), STEEL, shade=shade),
        Part(sabaton, STEEL, bulge=0.7, shade=shade),
        Part(Ellipse(knee, 3.5, 3.1), STEEL, shade=shade + 0.08),
    ]


def _arm(j, side, far):
    shade = -0.18 if far else 0.0
    shoulder, elbow, hand = j[f"{side}_shoulder"], j[f"{side}_elbow"], j[f"{side}_hand"]
    return [
        Part(Capsule(shoulder, elbow, 3.4, 2.9), STEEL, shade=shade),
        Part(Capsule(elbow, hand, 3.0, 2.5), STEEL, shade=shade),
        Part(Ellipse(elbow, 3.1, 2.8), STEEL, shade=shade + 0.08),
        Part(Ellipse(hand, 3.1, 2.7), LEATHER if far else STEEL, shade=shade),
    ]


def _torso(j, pose):
    hx, hy = j["hip"]
    outline = ((-7.0, 0.5), (-7.8, -8.0), (-6.8, -15.8), (-2.0, -19.0), (4.5, -18.2),
               (8.6, -12.5), (8.8, -6.5), (6.4, -1.0), (5.0, 1.0))
    body = _rotate(tuple((hx + x, hy + y) for x, y in outline), (hx, hy), pose.lean)
    fauld_top = _rotate(((hx - 7.4, hy - 1.0), (hx + 6.2, hy - 1.5), (hx + 7.8, hy + 3.4), (hx - 8.2, hy + 3.6)),
                        (hx, hy), pose.lean * 0.5)
    fauld_low = _rotate(((hx - 8.0, hy + 2.8), (hx + 7.4, hy + 2.6), (hx + 8.8, hy + 7.0), (hx - 8.6, hy + 7.2)),
                        (hx, hy), pose.lean * 0.3)
    belt = _rotate(((hx - 7.4, hy - 2.8), (hx + 6.6, hy - 3.2), (hx + 6.6, hy - 1.2), (hx - 7.4, hy - 0.8)),
                   (hx, hy), pose.lean)
    return [
        Part(Poly(fauld_low, bevel=1.6), STEEL, bulge=0.6, shade=-0.04),
        Part(Poly(fauld_top, bevel=1.6), STEEL, bulge=0.6),
        Part(Poly(body, bevel=3.0), STEEL, bulge=0.75, tilt=(0.25, -0.1)),
        Part(Poly(belt, bevel=0.8), LEATHER, bulge=0.3, cast=False),
    ]


def _helm(j, pose):
    hx, hy = j["head"]
    shape = ((-5.2, 4.2), (-5.9, -1.6), (-4.1, -6.4), (0.0, -8.0), (4.0, -6.7), (6.0, -2.9),
             (6.9, 1.7), (5.8, 5.4), (1.7, 6.9), (-3.4, 6.5))
    helm = _rotate(tuple((hx + x, hy + y) for x, y in shape), (hx, hy), pose.lean * 0.6 + pose.head)
    crest = _rotate(((hx - 3.8, hy - 5.2), (hx + 3.2, hy - 5.8)), (hx, hy), pose.lean * 0.6 + pose.head)
    return [Part(Poly(helm, bevel=3.2), STEEL, bulge=0.85), Part(Capsule(crest[0], crest[1], 1.0, 0.8), STEEL, shade=0.1)]


def _visor(j, pose):
    hx, hy = j["head"]
    slit = [(x, 0.0) for x in (0.8, 1.8, 2.8, 3.8, 4.8)]
    holes = [(3.2, 3.0), (4.6, 2.6)]
    angle = pose.lean * 0.6 + pose.head
    pts = _rotate(tuple((hx + x, hy + y) for x, y in slit + holes), (hx, hy), angle)
    out = []
    for i, (x, y) in enumerate(pts[:5]):
        out.append((round(x), round(y), EMBER_CORE if i in (2, 3) else EMBER))
    ex, ey = pts[4]
    out.append((round(ex) + 1, round(ey), EMBER_HAZE))
    out.append((round(ex) + 2, round(ey), raster.rgba("#ff5a2e", 45)))
    for x, y in pts[5:]:
        out.append((round(x), round(y), raster.rgb("#07060b")))
    return out


def _pauldron(j):
    sx, sy = j["near_shoulder"]
    lames = [
        (Ellipse((sx - 1.4, sy + 5.4), 7.6, 3.0, -0.15), -0.05),
        (Ellipse((sx - 0.7, sy + 2.6), 8.0, 3.8, -0.1), 0.0),
        (Ellipse((sx, sy - 0.8), 7.6, 5.0, -0.05), 0.06),
    ]
    parts = [Part(shape, STEEL, shade=shade) for shape, shade in lames]
    parts.append(Part(Capsule((sx - 6.9, sy + 2.6), (sx + 6.7, sy + 2.0), 0.75, 0.75), GOLD, seam=False, cast=False))
    return parts


def _sword(j, pose):
    hx, hy = j["near_hand"]
    direction = pose.sword
    tip = seg((hx, hy), direction, BLADE_LEN)
    base = seg((hx, hy), direction, 3.2)
    half = 1.7
    a = math.radians(direction)
    px, py = math.cos(a), -math.sin(a)  # perpendicular to the blade
    blade = Poly(((base[0] + px * half, base[1] + py * half), (tip[0], tip[1]),
                  (base[0] - px * half, base[1] - py * half)), bevel=1.2)
    fuller_end = seg((hx, hy), direction, BLADE_LEN * 0.62)
    guard_c = seg((hx, hy), direction, 2.4)
    guard = Capsule((guard_c[0] + px * 4.6, guard_c[1] + py * 4.6), (guard_c[0] - px * 4.6, guard_c[1] - py * 4.6), 1.1, 1.1)
    pommel = seg((hx, hy), direction, -4.6)
    return [
        Part(Capsule(seg((hx, hy), direction, -3.6), base, 1.1, 1.0), LEATHER, seam=False),
        Part(blade, BLADE, bulge=0.35, cast=False),
        Part(Capsule(base, fuller_end, 0.45, 0.25), BLADE, shade=-0.45, seam=False, cast=False),
        Part(guard, GOLD, seam=False),
        Part(Ellipse(pommel, 1.6, 1.6), GOLD),
    ]


def _cape(pose):
    chain = pose.cape
    if len(chain) < 3:
        return []
    leading, trailing = [], []
    last = len(chain) - 1
    for i, (x, y) in enumerate(chain):
        f = i / last
        dx = chain[min(i + 1, last)][0] - chain[max(i - 1, 0)][0]
        dy = chain[min(i + 1, last)][1] - chain[max(i - 1, 0)][1]
        length = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / length, dx / length          # left of the downward chain = behind the knight
        out, inn = 1.8 + 6.2 * f, 1.2 + 3.8 * f
        trailing.append((x + nx * out, y + ny * out))
        leading.append((x - nx * inn, y - ny * inn))
    hem = []
    (lx, ly), (tx, ty) = leading[-1], trailing[-1]
    for k in range(1, 8):
        t = k / 8
        hem.append((lx + (tx - lx) * t, ly + (ty - ly) * t + (2.4 if k % 2 else -0.4)))
    cloth = Poly(tuple(leading) + tuple(hem) + tuple(reversed(trailing)), bevel=2.5)
    half = len(trailing) // 2
    inner = [(x + 1.9 * (leading[i][0] - x) / max(1.0, math.hypot(leading[i][0] - x, leading[i][1] - y)),
              y + 1.9 * (leading[i][1] - y) / max(1.0, math.hypot(leading[i][0] - x, leading[i][1] - y)))
             for i, (x, y) in enumerate(trailing)]
    lining = Poly(tuple(trailing[half:]) + tuple(reversed(inner[half:])), bevel=0.8)
    return [
        Part(cloth, CLOTH, bulge=0.5, fold=(4.0, 0.65, 0.3), cast=False),
        Part(lining, LINING, bulge=0.3, seam=False, cast=False),
    ]


def _smear(j, pose):
    """Translucent trail of the area the blade swept since the previous frame (kept above the ground)."""
    if not pose.smear:
        return []
    (u0, f0, s0), (u1, f1, s1) = pose.smear
    shoulder = j["near_shoulder"]
    outer, inner = [], []
    for k in range(13):
        t = k / 12
        elbow = seg(shoulder, u0 + (u1 - u0) * t, UPPER_ARM)
        hand = seg(elbow, f0 + (f1 - f0) * t, FOREARM)
        angle = s0 + (s1 - s0) * t
        ox, oy = seg(hand, angle, BLADE_LEN + 1.5)
        ix, iy = seg(hand, angle, BLADE_LEN * (0.75 - 0.35 * t))
        outer.append((ox, min(oy, GROUND - 1.0)))
        inner.append((ix, min(iy, GROUND - 1.5)))
    return [Part(Poly(tuple(outer) + tuple(reversed(inner)), bevel=2.5), SMEAR, bulge=0.2, seam=False, cast=False)]


def _streak(j, pose):
    """Thrust speed lines: a long tapering wedge trailing back along the blade from past its tip."""
    if not pose.streak:
        return []
    hand = j["near_hand"]
    a = math.radians(pose.sword)
    px, py = math.cos(a), -math.sin(a)
    tip = seg(hand, pose.sword, BLADE_LEN + 4)
    tail = seg(hand, pose.sword, BLADE_LEN - pose.streak)
    wedge = Poly(((tail[0] + px * 0.6, tail[1] + py * 0.6), (tip[0], tip[1]), (tail[0] - px * 2.8, tail[1] - py * 2.8)), bevel=1.0)
    return [Part(wedge, SMEAR, bulge=0.2, seam=False, cast=False)]


def build_parts(pose):
    """Ordered parts (back to front) and painted details for a pose."""
    j = joints(pose)
    parts = []
    parts += _cape(pose)
    parts += _arm(j, "far", far=True)
    parts += _leg(j, "far", far=True)
    parts += _torso(j, pose)
    parts += _leg(j, "near", far=False)
    parts += _helm(j, pose)
    parts += _pauldron(j)
    parts += _sword(j, pose)
    parts += _arm(j, "near", far=False)
    parts += _smear(j, pose)
    parts += _streak(j, pose)
    return parts, _visor(j, pose)
