"""Dire wolf (tier 2, the Violet Moor): a moonlit hunter that closes at a full
gallop, crouches with its hackles up and springs jaws first. Struck down, it
yelps, rolls onto its side and lies still in the heather.
"""

import math
from dataclasses import dataclass

from .. import raster
from ..rig import Capsule, Ellipse, Material, Part, Poly, ramp
from .base import C, build_art, combined, seg, turned

SIZE, FEET_Y = (88, 56), 52
FUR = Material(ramp("#0b0910", "#15111b", "#211b29", "#30283a", "#453a52"), rim=C("#9a86c4"), ambient=0.17, rim_cut=0.66)
PALE = Material(ramp("#1a1720", "#2c2733", "#433c4a", "#5e5566"), rim=C("#b4a6d6"), ambient=0.2, rim_cut=0.5)
CLAW = Material(ramp("#2a2622", "#6a625a", "#bab0a0"), ambient=0.35)
MAW = Material(ramp("#1a0508", "#3a0a12", "#6a1a24"), ambient=0.3)
STAIN = Material(ramp("#0c0610", "#160a18"), ambient=0.3)
EYE, EYE_CORE = C("#ff9a2a"), C("#fff0a0")

# (upper, lower) leg angles for a gathered stride, a full extension, and standing square
FRONT = {"gathered": (-18.0, 30.0), "extended": (60.0, 76.0), "stand": (4.0, -2.0)}
HIND = {"gathered": (40.0, -14.0), "extended": (-50.0, -76.0), "stand": (12.0, -20.0)}


@dataclass(frozen=True)
class WolfPose:
    front: float = 0.0        # -1 gathered .. +1 extended (0 = standing square)
    hind: float = 0.0
    far_lag: float = 0.25     # far legs trail the near ones
    bob: float = 0.0
    reach: float = 0.0        # body stretched toward the knight
    crouch: float = 0.0       # hind end low, hackles up
    neck: float = 0.0         # -1 head thrown up, +1 head low
    jaw: float = 0.1          # 0 shut .. 1 wide
    sprawl: float = 0.0       # 0 on its feet .. 1 lying on its side
    eyes: bool = True


def _angles(table, e):
    base = table["stand"]
    target = table["extended"] if e >= 0 else table["gathered"]
    k = abs(e)
    return tuple(b + (t - b) * k for b, t in zip(base, target))


def _leg(root, upper, lower, lengths, shade, sprawl):
    a, b = lengths
    knee = seg(root, upper + sprawl * (upper - 0) * 0.2, a)
    paw = seg(knee, lower, b)
    toe = (paw[0] - 3.5, paw[1] + 0.5)
    return [Part(Capsule(root, knee, 4.2, 2.7), FUR, shade=shade),
            Part(Capsule(knee, paw, 2.6, 1.8), FUR, shade=shade),
            Part(Capsule(paw, toe, 1.9, 1.4), FUR, shade=shade),
            Part(Capsule(toe, (toe[0] - 1.2, toe[1] + 0.8), 0.6, 0.3), CLAW, seam=False, cast=False, shade=shade)]


def _wolf(p):
    lift = p.bob + 4 * p.crouch
    drop = 13 * p.sprawl
    shoulder = (32 - 6 * p.reach, 32 + lift + drop)
    hip = (62 - 2 * p.reach, 31 + lift + 3 * p.crouch + drop)
    parts, details = [], []

    def legs(far):
        shade = -0.2 if far else 0.0
        lag = p.far_lag if far else 0.0
        fu, fl = _angles(FRONT, max(-1.0, min(1.0, p.front - lag)))
        hu, hl = _angles(HIND, max(-1.0, min(1.0, p.hind - lag)))
        if p.sprawl:
            fu, fl = fu + (70 - fu) * p.sprawl, fl + (84 - fl) * p.sprawl
            hu, hl = hu + (-66 - hu) * p.sprawl, hl + (-86 - hl) * p.sprawl
        dx = 3 if far else 0
        return (_leg((shoulder[0] + dx, shoulder[1] + 4), fu, fl, (10.0, 10.0), shade, p.sprawl)
                + _leg((hip[0] + dx, hip[1] + 4), hu, hl, (10.5, 10.0), shade, p.sprawl))

    tail_root = (hip[0] + 8, hip[1] - 2)
    tail = [tail_root]
    for k in range(1, 5):
        wave = math.sin(k * 0.9 + p.front * 1.3) * 1.5 * (1 - p.sprawl)
        tail.append((tail_root[0] + k * 4.2, tail_root[1] + k * (1.6 + 1.2 * p.sprawl) + wave))
    parts += legs(far=True)
    parts += [Part(Capsule(a, b, 3.2 - k * 0.5, 2.7 - k * 0.5), FUR, shade=-0.05) for k, (a, b) in enumerate(zip(tail, tail[1:]))]
    parts += [Part(Ellipse(hip, 10.0, 9.0, 0.1), FUR),
              Part(Ellipse(((shoulder[0] + hip[0]) / 2, (shoulder[1] + hip[1]) / 2 + 1), 15.0, 8.5, 0.0), FUR),
              Part(Ellipse((shoulder[0] + 2, shoulder[1] + 5), 9.0, 5.0, 0.2), PALE, shade=-0.05, seam=False),
              Part(Ellipse(shoulder, 12.0, 10.5, -0.15), FUR)]
    raise_hackles = 2 + 5 * p.crouch
    ridge = [(shoulder[0] - 8, shoulder[1] - 6)]
    for k in range(7):
        x = shoulder[0] - 4 + k * 5
        y = shoulder[1] - 9 + k * 0.6 + (hip[1] - shoulder[1]) * k / 7
        ridge += [(x, y - raise_hackles * (1 - k / 9)), (x + 2.5, y + 1)]
    ridge += [(hip[0] + 4, hip[1] - 4), (shoulder[0], shoulder[1] - 2)]
    parts.append(Part(Poly(tuple(ridge), bevel=1.2), FUR, bulge=0.4, shade=0.05, seam=False))
    neck_angle = 128 - 40 * p.neck - 30 * p.reach + 30 * p.sprawl
    head = seg((shoulder[0] - 4, shoulder[1] - 4), neck_angle, 13)
    head_parts, head_details = _head(head, p)
    parts += [Part(Capsule((shoulder[0] - 1, shoulder[1] - 1), head, 7.5, 5.4), FUR)]
    parts += head_parts
    details += head_details
    parts += legs(far=False)
    return parts, details


def _head(center, p):
    hx, hy = center
    tilt = -8 * p.neck + 18 * p.sprawl
    jaw_drop = 1 + 7 * p.jaw
    skull = Ellipse((hx, hy), 6.8, 5.6, math.radians(tilt * 0.5))
    snout_tip = seg((hx - 4, hy + 1), 96 - tilt, 9)
    jaw_tip = seg((hx - 3, hy + 3), 96 - tilt - 6 - 10 * p.jaw, 8.5)
    parts = [Part(Poly(((hx + 1, hy - 3), (hx + 3, hy - 12), (hx + 7, hy - 3)), bevel=0.8), FUR, shade=-0.1, seam=False),
             Part(Capsule((hx - 3, hy + 3), jaw_tip, 2.4, 1.5), FUR, shade=-0.08),
             Part(Capsule((hx - 3, hy + 2), (jaw_tip[0] + 1, jaw_tip[1] - 1.2 * jaw_drop * 0.4), 1.6, 0.8), MAW, seam=False)
             if p.jaw > 0.3 else None,
             Part(skull, FUR),
             Part(Capsule((hx - 4, hy + 1), snout_tip, 3.4, 2.3), FUR),
             Part(Poly(((hx - 3, hy - 4), (hx - 1, hy - 13), (hx + 3, hy - 5)), bevel=0.8), FUR, seam=False)]
    parts = [part for part in parts if part is not None]
    ex, ey = round(hx - 3), round(hy - 1)
    nose = (round(snout_tip[0]), round(snout_tip[1]))
    details = [(nose[0], nose[1], C("#050305"))]
    if p.eyes:
        details += [(ex, ey, EYE_CORE), (ex - 1, ey, EYE), (ex + 1, ey, raster.rgba("#ff9a2a", 120))]
    else:
        details += [(ex, ey, C("#07050a")), (ex - 1, ey, C("#07050a"))]
    if p.jaw > 0.3:
        details += [(round(snout_tip[0]) + 2, round(snout_tip[1]) + 2, C("#f2ead8")),
                    (round(jaw_tip[0]) + 2, round(jaw_tip[1]) - 1, C("#f2ead8"))]
    return parts, details


def _stain():
    return [Part(Ellipse((42, FEET_Y + 2), 26, 2.2), STAIN, bulge=0.1, seam=False, cast=False)], []


def build():
    moves = [
        _wolf(WolfPose(front=-1.0, hind=-0.8, bob=0)),
        _wolf(WolfPose(front=-0.1, hind=-0.3, bob=-3)),
        _wolf(WolfPose(front=1.0, hind=0.9, bob=-2, reach=0.3)),
        _wolf(WolfPose(front=0.35, hind=0.55, bob=0)),
    ]
    attack = [
        _wolf(WolfPose(front=-0.4, hind=-0.9, crouch=1.0, neck=0.8, jaw=0.4)),
        _wolf(WolfPose(front=1.0, hind=1.0, bob=-4, reach=1.0, neck=0.3, jaw=1.0)),
    ]
    death = [
        turned(_wolf(WolfPose(front=0.5, hind=-0.3, neck=-1.0, jaw=1.0)), rotate=10, pivot=(62, 52)),
        _wolf(WolfPose(front=0.6, hind=0.4, sprawl=0.55, neck=0.4, jaw=0.5, eyes=False)),
        combined(_stain(), _wolf(WolfPose(front=0.8, hind=0.8, sprawl=1.0, neck=0.8, jaw=0.2, eyes=False))),
    ]
    idle = [_wolf(WolfPose(front=0.05, hind=-0.15, far_lag=0.1, crouch=0.35, neck=0.6, jaw=0.2)),
            _wolf(WolfPose(front=0.05, hind=-0.15, far_lag=0.1, crouch=0.45, bob=1, neck=0.75, jaw=0.55))]
    return build_art("wolf", SIZE, FEET_Y, moves, attack, _wolf(WolfPose()), death, idle=idle)
