"""Broodmother (tier 3, the Hollow Wood): a giant spider with a bone-white
skull marking, a crown of red eyes and dripping fangs. It rears to strike,
and dies screeching, flipping onto its back with its legs curling shut.
"""

import math
from dataclasses import dataclass

from .. import raster
from ..rig import Capsule, Ellipse, Material, Part, Poly, ramp
from .base import C, build_art, combined, grounded, turned

SIZE, FEET_Y = (96, 64), 59
CHITIN = Material(ramp("#060808", "#0c1112", "#141c1c", "#1e2a2a", "#2c3c3a"), spec=C("#7ab8a4"), rim=C("#5aa894"),
                  shininess=26, spec_cut=0.9, ambient=0.14, rim_cut=0.6)
HAIR = Material(ramp("#0a0e0e", "#162020", "#243432"), rim=C("#4a8a78"), ambient=0.2, rim_cut=0.55)
MARK = Material(ramp("#5a5444", "#9a927a", "#d8d0b4"), ambient=0.35)
FANG = Material(ramp("#3a3428", "#9a927a", "#e8e0c8"), spec=C("#ffffff"), spec_cut=0.8, ambient=0.35)
ICHOR = Material(ramp("#081008", "#10200e", "#1c3418"), ambient=0.3)
EYE, EYE_CORE = C("#ff2a2a"), C("#ffc8a8")

NEAR_TIPS = ((4.0, 0.0), (22.0, 0.5), (62.0, 1.5), (88.0, 3.0))   # (x, phase) of each near leg's foot
FAR_TIPS = ((12.0, 0.5), (30.0, 1.0), (70.0, 2.0), (94.0, 3.5))


@dataclass(frozen=True)
class SpiderPose:
    step: float = 0.0       # gait phase (radians)
    rear: float = 0.0       # 0 level .. 1 reared up on the hind legs
    lunge: float = 0.0      # body thrown toward the knight
    fangs: float = 0.3      # 0 closed .. 1 spread
    flip: float = 0.0       # 0 upright .. 1 dead on its back
    curl: float = 0.0       # legs drawn in toward the body
    eyes: bool = True


def _body_anchor(p):
    lift = -6 * p.rear
    return (44 - 8 * p.lunge, 36 + lift + 6 * p.flip), 10 * p.rear - 4 * p.lunge


def _leg_parts(root, tip, knee_height, shade, curl, flip):
    rx, ry = root
    tx, ty = tip
    tx, ty = tx + (rx - tx) * curl * 0.75, ty + (ry - ty) * curl * 0.75
    mx = (rx + tx) / 2
    knee = (mx + (rx - tx) * 0.08, min(ry, ty) - knee_height * (1 - 0.5 * curl) * (1 - 2 * flip))
    claw = (tx + (0.8 if tx > rx else -0.8), ty + (2 if not flip else -2))
    return [Part(Capsule(root, knee, 2.4, 1.8), CHITIN, shade=shade),
            Part(Ellipse(knee, 2.0, 2.0), CHITIN, shade=shade + 0.06),
            Part(Capsule(knee, (tx, ty), 1.7, 0.9), HAIR, shade=shade),
            Part(Capsule((tx, ty), claw, 0.8, 0.4), CHITIN, shade=shade, seam=False, cast=False)]


def _legs(p, center, near):
    tips = NEAR_TIPS if near else FAR_TIPS
    shade = 0.0 if near else -0.25
    parts = []
    for i, (x, phase) in enumerate(tips):
        swing = p.step + phase * math.pi / 2 + (0 if near else math.pi)
        lift = 4 * max(0.0, math.cos(swing)) * (1 - p.flip)
        foot_x = x + 4 * math.sin(swing) - 8 * p.lunge
        foot_y = FEET_Y - lift
        if i < 2:
            foot_x -= 6 * p.rear
            foot_y -= 26 * p.rear * (1.2 if i == 0 else 0.8)
        if p.flip:
            foot_y = foot_y + (center[1] - 18 - foot_y) * p.flip
        root = (center[0] - 6 + i * 4, center[1] - 1)
        knee_height = 18 if i in (1, 2) else 14
        parts += _leg_parts(root, (foot_x, foot_y), knee_height, shade, p.curl, p.flip)
    return parts


def _spider(p):
    center, tilt = _body_anchor(p)
    cx, cy = center
    parts = _legs(p, center, near=False)
    abdomen = (cx + 21, cy - 9 + 12 * p.flip + 0.4 * tilt)
    parts.append(Part(Ellipse(abdomen, 17.5, 14.0, math.radians(-14 + tilt - 40 * p.flip)), CHITIN))
    if not p.flip:
        marking = ((abdomen[0] - 3, abdomen[1] - 7), (abdomen[0] + 5, abdomen[1] - 8), (abdomen[0] + 7, abdomen[1] - 2),
                   (abdomen[0] + 3, abdomen[1] + 2), (abdomen[0] - 1, abdomen[1] + 1), (abdomen[0] - 4, abdomen[1] - 3))
        parts.append(Part(Poly(marking, bevel=1.2), MARK, bulge=0.4, seam=False, cast=False))
    parts.append(Part(Ellipse(center, 11.5, 8.5, math.radians(tilt)), CHITIN))
    head = (cx - 13 - 3 * p.lunge, cy + 1 - 3 * p.rear + 5 * p.flip)
    parts.append(Part(Ellipse(head, 7.0, 6.0, math.radians(tilt)), CHITIN, shade=0.03))
    spread = 2 + 5 * p.fangs
    fang_parts = []
    for side, shade in ((1, -0.2), (-1, 0.0)):
        base = (head[0] - 4, head[1] + 3 + side)
        tip = (base[0] - 3 - 2 * p.fangs, base[1] + 7 - side * spread * 0.4 - 10 * p.flip)
        fang_parts += [Part(Capsule(base, tip, 2.0, 1.0), CHITIN, shade=shade),
                       Part(Capsule(tip, (tip[0] + 1.5, tip[1] + 3 - 6 * p.flip), 0.9, 0.3), FANG, seam=False, cast=False)]
    parts += fang_parts
    parts += _legs(p, center, near=True)
    details = []
    hx, hy = round(head[0]), round(head[1])
    if p.eyes and not p.flip:
        details += [(hx - 4, hy - 2, EYE_CORE), (hx - 5, hy - 2, EYE), (hx - 1, hy - 3, EYE_CORE), (hx - 2, hy - 3, EYE),
                    (hx - 6, hy, EYE), (hx - 3, hy - 4, EYE), (hx, hy - 4, EYE), (hx - 4, hy, raster.rgba("#ff2a2a", 150))]
        if p.fangs > 0.6:
            details.append((round(head[0] - 9), round(head[1] + 12), raster.rgba("#6aff9a", 200)))
    return parts, details


def _on_back(curl):
    """Dead on its back: belly up, legs hooked into the air and drawn shut."""
    g = FEET_Y
    body, abdomen, head = (46, g - 7), (66, g - 10), (31, g - 6)
    parts, details = [], []

    def legs(near):
        shade = 0.0 if near else -0.25
        out = []
        for i, spread in enumerate((-20, -8, 7, 19)):
            root = (body[0] - 5 + i * 4 + (2 if not near else 0), body[1] - 5)
            knee = (root[0] + spread * 0.8, root[1] - 15 + 4 * curl)
            tip = (root[0] + spread * (1.0 - 0.9 * curl), root[1] - 6 - 10 * curl)
            out += [Part(Capsule(root, knee, 2.2, 1.7), CHITIN, shade=shade),
                    Part(Ellipse(knee, 1.9, 1.9), CHITIN, shade=shade + 0.06),
                    Part(Capsule(knee, tip, 1.6, 0.8), HAIR, shade=shade)]
        return out

    parts += legs(near=False)
    parts += [Part(Ellipse(abdomen, 17.0, 11.5, math.radians(8)), CHITIN, shade=-0.05),
              Part(Ellipse((abdomen[0] - 2, abdomen[1] - 6), 10.0, 4.5, math.radians(8)), HAIR, shade=0.05, seam=False),
              Part(Ellipse(body, 11.0, 7.5), CHITIN),
              Part(Ellipse(head, 6.5, 5.5), CHITIN, shade=0.03),
              Part(Capsule((head[0] - 4, head[1] - 3), (head[0] - 7, head[1] - 10), 1.8, 0.9), CHITIN),
              Part(Capsule((head[0] - 7, head[1] - 10), (head[0] - 5, head[1] - 13), 0.8, 0.3), FANG, seam=False, cast=False)]
    parts += legs(near=True)
    return parts, details


def _puddle():
    return [Part(Ellipse((50, FEET_Y + 2), 30, 2.4), ICHOR, bulge=0.2, seam=False, cast=False)], []


def build():
    moves = [_spider(SpiderPose(step=k * math.pi / 2)) for k in range(4)]
    attack = [_spider(SpiderPose(rear=1.0, fangs=1.0)), _spider(SpiderPose(step=1.0, lunge=1.0, fangs=0.8))]
    death = [
        _spider(SpiderPose(step=0.6, rear=0.7, fangs=1.0, curl=0.2)),
        grounded(turned(_spider(SpiderPose(step=2.2, curl=0.35, fangs=0.4, eyes=False)), rotate=150, pivot=(50, 36)),
                 FEET_Y + 1, x=48),
        combined(_puddle(), _on_back(0.55)),
        combined(_puddle(), _on_back(1.0)),
    ]
    idle = [_spider(SpiderPose(step=0.0, fangs=0.2)), _spider(SpiderPose(step=0.0, rear=0.12, fangs=0.7))]
    return build_art("spider", SIZE, FEET_Y, moves, attack, _spider(SpiderPose(step=0.4)), death, idle=idle)
