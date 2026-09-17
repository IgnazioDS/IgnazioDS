"""Carrion crow (tier 1, the Crimson Waste): a battlefield scavenger lit red
by the sky. It dives beak first; struck, it bursts into feathers and drops.
"""

import math

from ..rig import Capsule, Ellipse, Material, Part, Poly, ramp
from .base import C, build_art, combined, turned

SIZE, FEET_Y = (48, 36), 34
FEATHER = Material(ramp("#060508", "#0e0b10", "#18131a", "#241d26"), rim=C("#c05a48"), ambient=0.16, rim_cut=0.5)
QUILL = Material(ramp("#08070a", "#141016", "#201a22"), rim=C("#a04a3e"), ambient=0.2, rim_cut=0.45)
BEAK = Material(ramp("#2a2418", "#6a5c40", "#b0a07a"), spec=C("#e8dcc0"), spec_cut=0.8, ambient=0.3)
BLOOD = Material(ramp("#2a0608", "#4a0c10"), ambient=0.3)
EYE = C("#ff4a2a")


def _wing(shoulder, beat, shade, spread=1.0):
    lift = (beat + 1) / 2
    wrist = (shoulder[0] + 8 * spread, shoulder[1] - 9 + 16 * lift)
    tips = [(wrist[0] + (7 + 3 * k) * spread, wrist[1] - 3 + (5 + 2 * k) * lift + k * 1.5) for k in range(4)]
    outline = (shoulder, wrist) + tuple(tips) + ((shoulder[0] + 6, shoulder[1] + 4),)
    parts = [Part(Poly(outline, bevel=1.4), FEATHER, bulge=0.3, shade=shade, cast=False)]
    parts += [Part(Capsule(wrist, tip, 1.1, 0.5), QUILL, shade=shade, seam=False, cast=False) for tip in tips]
    return parts


def _crow(beat, bob, dive=0.0, beak_open=0.0, eyes=True):
    cx, cy = 24, 19 + bob
    tilt = -0.2 + 0.5 * dive
    parts = _wing((cx + 2, cy - 2), beat * 0.9 - 0.15, -0.2)
    tail = ((cx + 6, cy), (cx + 17, cy - 3 + 6 * dive), (cx + 18, cy + 2 + 6 * dive), (cx + 7, cy + 3))
    parts.append(Part(Poly(tail, bevel=1.2), QUILL, bulge=0.3))
    parts.append(Part(Ellipse((cx, cy), 8.0, 4.8, tilt), FEATHER))
    head = (cx - 8, cy - 3 + 5 * dive)
    parts.append(Part(Ellipse(head, 4.0, 3.6), FEATHER))
    tip = (head[0] - 9, head[1] + 1.5 + 4 * dive)
    parts.append(Part(Poly(((head[0] - 2, head[1] - 1.2), tip, (head[0] - 2, head[1] + 1.4 + beak_open)), bevel=0.6), BEAK, bulge=0.4))
    if beak_open:
        parts.append(Part(Poly(((head[0] - 2, head[1] + 1.8), (tip[0] + 2, tip[1] + beak_open + 1), (head[0] - 2, head[1] + 2.6 + beak_open)),
                               bevel=0.5), BEAK, bulge=0.3, shade=-0.1))
    parts += [Part(Capsule((cx - 1, cy + 4), (cx - 3, cy + 8), 0.7, 0.5), BEAK, shade=-0.2, seam=False),
              Part(Capsule((cx + 2, cy + 4), (cx + 1, cy + 8), 0.7, 0.5), BEAK, shade=-0.3, seam=False)]
    parts += _wing((cx, cy - 1), beat, 0.0)
    details = [(round(head[0]) - 1, round(head[1]) - 1, EYE if eyes else C("#07050a"))]
    return parts, details


def _feathers(spread, drop):
    rng_pts = ((-14, -6, 30), (-8, -12, -40), (6, -13, 60), (13, -5, -20), (-3, 6, 80), (10, 7, 10), (-12, 5, -70))
    parts = []
    for dx, dy, angle in rng_pts:
        x, y = 24 + dx * spread, 18 + dy * spread + drop
        a = math.radians(angle)
        parts.append(Part(Capsule((x - math.cos(a) * 2.5, y - math.sin(a) * 2.5), (x + math.cos(a) * 2.5, y + math.sin(a) * 2.5), 1.0, 0.4),
                          QUILL, seam=False, cast=False))
    return parts, []


def _remains():
    stain = [Part(Ellipse((24, FEET_Y), 10, 1.8), BLOOD, bulge=0.1, seam=False, cast=False)], []
    body = turned(_crow(0.2, 0, eyes=False), rotate=176, pivot=(24, 19), offset=(0, 11))
    return combined(stain, body, _feathers(1.3, 12))


def build():
    moves = [_crow(-1.0, 0), _crow(-0.2, 1), _crow(0.9, 2), _crow(0.2, 1)]
    attack = [_crow(-1.0, -2, dive=0.2, beak_open=1.5), _crow(0.6, 3, dive=1.0, beak_open=0.5)]
    death = [
        combined(turned(_crow(-0.8, 0, beak_open=2.0), rotate=-30, pivot=(24, 19)), _feathers(0.9, 0)),
        combined(turned(_crow(0.8, 0, eyes=False), rotate=140, pivot=(24, 19), offset=(0, 5)), _feathers(1.5, 4)),
        _remains(),
    ]
    return build_art("crow", SIZE, FEET_Y, moves, attack, _crow(0.2, 1), death)
