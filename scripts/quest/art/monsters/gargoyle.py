"""Gargoyle (tier 2, the Blood Moon Keep): a horned stone watcher come off its
pillar, gliding low on heavy wings. It dies the way statues do: cracks glow,
it breaks apart, and a heap of rubble with one horned head remains.
"""

import math
from dataclasses import dataclass

from .. import raster
from ..rig import Capsule, Ellipse, Material, Part, Poly, ramp
from .base import C, build_art, combined, turned

SIZE, FEET_Y = (80, 68), 63
STONE = Material(ramp("#1a1720", "#2c2733", "#403948", "#574e60", "#72687c", "#8e8498"), rim=C("#f08aa2"), ambient=0.2, rim_cut=0.58)
WING = Material(ramp("#141118", "#221d27", "#322b38", "#443c4c"), rim=C("#c65a7a"), ambient=0.18, rim_cut=0.5)
DUST = Material((raster.rgba("#6a5c70", 70), raster.rgba("#8a7a90", 120)), ambient=0.5)
EYE, EYE_CORE = C("#ff3a4a"), C("#ffc0b0")
CRACK = C("#ff8a5a")


@dataclass(frozen=True)
class GargoylePose:
    beat: float = 0.0       # -1 wings high .. +1 wings low
    bob: float = 0.0
    reach: float = 0.0      # claws thrown forward
    rear: float = 0.0       # reared back, arms raised
    jaw: float = 0.2
    eyes: bool = True
    cracks: float = 0.0     # glowing fractures (0 none .. 1 about to break)


def _wing(shoulder, beat, shade):
    lift = (beat + 1) / 2
    elbow = (shoulder[0] + 12, shoulder[1] - 16 + 20 * lift)
    wrist = (elbow[0] + 10, elbow[1] - 10 + 18 * lift)
    fingers = [(wrist[0] + 6 + 4 * k, wrist[1] + 8 + 7 * k - 6 * lift * (1 - k / 3)) for k in range(4)]
    outline = [shoulder, elbow, wrist, *fingers]
    outline += [(fingers[-1][0] - 8, fingers[-1][1] + 2), (shoulder[0] + 4, shoulder[1] + 12)]
    parts = [Part(Poly(tuple(outline), bevel=2.4), WING, bulge=0.25, shade=shade, fold=(6.0, 0.3, 0.1), cast=False)]
    parts += [Part(Capsule(wrist, tip, 1.4, 0.6), STONE, shade=shade, seam=False, cast=False) for tip in fingers]
    parts += [Part(Capsule(shoulder, elbow, 3.0, 2.2), STONE, shade=shade), Part(Capsule(elbow, wrist, 2.2, 1.6), STONE, shade=shade)]
    return parts


def _head(p, anchor):
    hx, hy = anchor
    parts = [Part(Poly(((hx + 2, hy - 3), (hx + 12, hy - 14), (hx + 6, hy - 3)), bevel=0.8), STONE, shade=-0.1, seam=False),
             Part(Ellipse((hx, hy), 6.5, 5.8), STONE),
             Part(Poly(((hx - 3, hy + 1), (hx - 11, hy + 3), (hx - 10, hy + 6 + 3 * p.jaw), (hx + 1, hy + 6)), bevel=1.0), STONE, shade=-0.05),
             Part(Poly(((hx - 1, hy - 4), (hx + 7, hy - 16), (hx + 3, hy - 4)), bevel=0.8), STONE, seam=False),
             Part(Poly(((hx + 4, hy - 1), (hx + 10, hy - 4), (hx + 6, hy + 2)), bevel=0.6), STONE, shade=0.05, seam=False)]
    details = [(round(hx - 8), round(hy + 5), C("#e6dcc0")), (round(hx - 5), round(hy + 5), C("#e6dcc0"))]
    if p.eyes:
        details += [(round(hx - 3), round(hy - 1), EYE_CORE), (round(hx - 4), round(hy - 1), EYE),
                    (round(hx - 5), round(hy - 1), raster.rgba("#ff3a4a", 110))]
    return parts, details


def _body(p):
    hover = p.bob
    hips = (46, 42 + hover)
    chest = (38 - 3 * p.reach + 2 * p.rear, 31 + hover - 2 * p.rear)
    parts, details = [], []
    tail = [(hips[0] + 4, hips[1] + 2)]
    for k in range(1, 5):
        tail.append((tail[0][0] + 5 * k, tail[0][1] + 3 * k - 0.6 * k * k + math.sin(k + p.beat) * 1.2))
    parts += [Part(Capsule(a, b, 2.2 - k * 0.35, 1.8 - k * 0.35), STONE, shade=-0.1) for k, (a, b) in enumerate(zip(tail, tail[1:]))]
    tx, ty = tail[-1]
    parts.append(Part(Poly(((tx - 1, ty - 3), (tx + 5, ty), (tx - 1, ty + 3)), bevel=0.6), STONE, shade=-0.1))
    for side, shade in ((3, -0.22), (-2, 0.0)):
        knee = (hips[0] - 8 + side, hips[1] + 8)
        ankle = (hips[0] - 2 + side, hips[1] + 15)
        foot = (ankle[0] - 7, ankle[1] + 3)
        parts += [Part(Capsule((hips[0] + side, hips[1]), knee, 4.2, 3.0), STONE, shade=shade),
                  Part(Capsule(knee, ankle, 2.8, 2.0), STONE, shade=shade),
                  Part(Capsule(ankle, foot, 1.8, 1.2), STONE, shade=shade)]
        parts += [Part(Capsule(foot, (foot[0] - 2, foot[1] + 1.5 - k), 0.7, 0.3), STONE, shade=shade + 0.1, seam=False, cast=False) for k in (0, 2)]
    parts += [Part(Ellipse(hips, 8.5, 7.5), STONE), Part(Capsule(hips, chest, 8.0, 9.0), STONE)]
    for side, shade in ((2, -0.2), (-3, 0.0)):
        shoulder = (chest[0] + side, chest[1] - 2)
        elbow = (shoulder[0] - 8 - 6 * p.reach, shoulder[1] + 8 - 14 * p.rear)
        hand = (elbow[0] - 6 - 10 * p.reach, elbow[1] + 5 - 12 * p.rear)
        arm = [Part(Capsule(shoulder, elbow, 3.0, 2.3), STONE, shade=shade), Part(Capsule(elbow, hand, 2.3, 1.8), STONE, shade=shade)]
        arm += [Part(Capsule(hand, (hand[0] - 4, hand[1] + 1 + 2 * k), 0.8, 0.3), STONE, shade=shade + 0.12, seam=False, cast=False)
                for k in (-1, 0, 1)]
        parts += arm if side < 0 else arm
    head_parts, head_details = _head(p, (chest[0] - 8, chest[1] - 9))
    return parts, head_parts, details + head_details


def _gargoyle(p):
    body, head, details = _body(p)
    shoulder = (44, 26 + p.bob)
    parts = _wing((shoulder[0] + 3, shoulder[1] - 1), p.beat * 0.9 - 0.1, -0.22) + body + head + _wing(shoulder, p.beat, 0.0)
    if p.cracks:
        for x0, y0, x1, y1 in ((36, 24, 42, 34), (42, 34, 39, 42), (30, 16, 34, 22), (50, 40, 46, 50)):
            steps = 6
            for k in range(steps + 1):
                if k / steps <= p.cracks:
                    details.append((round(x0 + (x1 - x0) * k / steps), round(y0 + p.bob + (y1 - y0) * k / steps), CRACK))
    return parts, details


def _rubble(settle):
    g = FEET_Y + 1
    chunks = ((20, 7, 5, 0.3), (32, 9, 7, -0.2), (46, 8, 6, 0.5), (57, 6, 4, -0.4), (27, 5, 3, 0.1), (52, 4, 3, 0.2))
    parts = [Part(Ellipse((40, g), 30, 2.0), DUST, bulge=0.1, seam=False, cast=False)]
    for x, w, h, spin in chunks:
        y = g - h * 0.6 - (1 - settle) * 2
        pts = tuple((x + math.cos(a + spin) * w * 0.7, y + math.sin(a + spin) * h * 0.7) for a in (0.2, 1.4, 2.5, 3.6, 4.7, 5.6))
        parts.append(Part(Poly(pts, bevel=1.4), STONE, bulge=0.5, shade=-0.05 * (x % 3)))
    head = turned(_head(GargoylePose(eyes=False, jaw=0.6), (0, 0)), rotate=-35, offset=(40, g - 8))
    return combined((parts, []), head)


def build():
    moves = [_gargoyle(GargoylePose(beat=b, bob=o)) for b, o in ((-1.0, -2), (-0.2, 0), (0.9, 2), (0.2, 1))]
    attack = [_gargoyle(GargoylePose(beat=-1.0, bob=-4, rear=1.0, jaw=0.8)), _gargoyle(GargoylePose(beat=0.7, bob=3, reach=1.0, jaw=1.0))]
    death = [
        _gargoyle(GargoylePose(beat=0.4, bob=2, rear=0.4, jaw=1.0, cracks=0.6)),
        combined(turned(_gargoyle(GargoylePose(beat=0.9, bob=6, eyes=False, cracks=1.0)), rotate=-18, pivot=(44, 60)), _rubble(0.0)),
        _rubble(1.0),
    ]
    return build_art("gargoyle", SIZE, FEET_Y, moves, attack, _gargoyle(GargoylePose(beat=0.2)), death)
