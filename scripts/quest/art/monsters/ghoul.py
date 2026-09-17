"""Ghoul (tier 2): a starved, hunched corpse-eater that lunges claws first,
reels when it dies, drops to its knees and sinks face down into its ichor.
"""

import math

from ..rig import Capsule, Ellipse, Material, Part, Poly, ramp
from .base import C, build_art, combined, seg, turned

SIZE, FEET_Y = (64, 58), 54
SKIN = Material(ramp("#141a17", "#243029", "#3a4a3f", "#566b5a", "#7c937c"), rim=C("#b4cca0"), ambient=0.16, rim_cut=0.55)
RAG = Material(ramp("#140f0d", "#261c18", "#3a2c24", "#4e3c30"), rim=C("#6a5646"), ambient=0.2)
CLAW = Material(ramp("#3a3428", "#8a8068", "#d8cfb2"), ambient=0.4)
ICHOR = Material(ramp("#0a120c", "#15261a", "#223a28"), spec=C("#5a8a5e"), spec_cut=0.6, ambient=0.3)


def _ghoul(stride, bob, reach, jaw, eyes=True):
    hips = (38, 32 + bob)
    mid = (33, 25 + bob)
    shoulders = (27 - reach * 4, 22 + bob - reach * 2)
    head = (18 - reach * 6, 22 + bob - reach * 2)
    parts = []

    def leg(side, phase):
        swing = math.sin(stride + phase) * 22
        hip = (hips[0] + side, hips[1] + 2)
        knee = seg(hip, -10 + swing, 10)
        ankle = seg(knee, -25 + swing * 0.4 + 28, 10)
        foot = (ankle[0] - 4, ankle[1] + 1)
        shade = -0.18 if side > 0 else 0.0
        return [Part(Capsule(hip, knee, 2.8, 2.2), SKIN, shade=shade), Part(Capsule(knee, ankle, 2.2, 1.6), SKIN, shade=shade),
                Part(Capsule(ankle, foot, 1.5, 1.2), SKIN, shade=shade)]

    def arm(side, phase):
        swing = math.sin(stride + phase) * 18
        shoulder = (shoulders[0] + side * 2, shoulders[1] + 2)
        elbow = seg(shoulder, 35 + swing + reach * 50, 11)
        hand = seg(elbow, 20 + swing * 0.5 + reach * 60, 11)
        shade = -0.2 if side > 0 else 0.0
        claws = [Part(Capsule(hand, seg(hand, a + reach * 60, 4.5), 0.8, 0.3), CLAW, seam=False, cast=False, shade=shade)
                 for a in (10, 35, 60)]
        return [Part(Capsule(shoulder, elbow, 2.2, 1.7), SKIN, shade=shade), Part(Capsule(elbow, hand, 1.7, 1.3), SKIN, shade=shade)] + claws

    parts += arm(3, math.pi) + leg(3, math.pi)
    parts += [Part(Capsule(hips, mid, 6.0, 5.0), SKIN), Part(Capsule(mid, shoulders, 5.2, 4.4), SKIN),
              Part(Poly(((hips[0] - 7, hips[1] - 2), (hips[0] + 7, hips[1] - 3), (hips[0] + 8, hips[1] + 7),
                         (hips[0] + 4, hips[1] + 5), (hips[0] + 1, hips[1] + 9), (hips[0] - 3, hips[1] + 5),
                         (hips[0] - 7, hips[1] + 8)), bevel=1.2), RAG, bulge=0.4)]
    parts += leg(-2, 0.0)
    parts += [Part(Capsule(shoulders, (head[0] + 4, head[1]), 2.8, 2.4), SKIN),
              Part(Ellipse(head, 6.5, 5.2, -0.25), SKIN),
              Part(Poly(((head[0] - 1, head[1] + 2), (head[0] - 7, head[1] + 3 + jaw * 0.35),
                         (head[0] - 6, head[1] + 5 + jaw * 0.45), (head[0] + 2, head[1] + 5)), bevel=1.0), SKIN, shade=-0.1)]
    parts += arm(-2, 0.0)
    hx, hy = round(head[0]), round(head[1])
    glow = (C("#e9ff7a"), C("#fbffd0"), C("#9aa84a")) if eyes else (C("#2a3024"), C("#3a4232"), C("#1a2018"))
    details = [(hx - 3, hy - 1, glow[0]), (hx - 4, hy - 1, glow[1]), (hx, hy - 1, glow[2]),
               (hx - 6, hy + 2, C("#e6dcc0")), (hx - 4, hy + 3, C("#e6dcc0")), (hx - 7, hy + 3, C("#1a0a0a"))]
    for k in range(3):
        rx, ry = round(mid[0] - 2 + k * 3), round(mid[1] - 1)
        details += [(rx, ry, C("#243029")), (rx, ry + 2, C("#243029"))]
    return parts, details


def _puddle(width):
    return [Part(Ellipse((30, 55), width, 2.6), ICHOR, bulge=0.25, seam=False, cast=False)], []


def _corpse(sink):
    """Prone and still, one arm flung forward, sinking into its ichor."""
    y = 49 + sink
    hips, shoulders, head = (40, y), (25, y + 1), (15, y + 1.5)
    parts = [
        Part(Capsule((hips[0] + 1, y + 1), (50, y + 2), 2.6, 2.1), SKIN, shade=-0.18),
        Part(Capsule((50, y + 2), (59, y + 3), 2.1, 1.5), SKIN, shade=-0.18),
        Part(Capsule(shoulders, (10, y + 4), 1.8, 1.3), SKIN, shade=-0.2),
        Part(Capsule(hips, (33, y - 0.5), 6.0, 5.2), SKIN),
        Part(Capsule((33, y - 0.5), shoulders, 5.2, 4.4), SKIN),
        Part(Poly(((hips[0] - 5, y - 5), (hips[0] + 6, y - 5), (hips[0] + 8, y + 1), (hips[0] + 3, y + 3),
                   (hips[0] - 4, y + 2)), bevel=1.2), RAG, bulge=0.4),
        Part(Capsule((hips[0] + 2, y), (51, y + 0.5), 2.8, 2.2), SKIN),
        Part(Capsule((51, y + 0.5), (60, y + 1), 2.2, 1.6), SKIN),
        Part(Ellipse(head, 6.0, 4.6, 0.15), SKIN),
        Part(Capsule((shoulders[0] + 2, y + 2), (18, y + 5), 2.2, 1.7), SKIN),
        Part(Capsule((18, y + 5), (5, y + 4), 1.7, 1.3), SKIN),
    ]
    parts += [Part(Capsule((5, y + 4), (1 + k, y + 3 + k), 0.8, 0.3), CLAW, seam=False, cast=False) for k in (0, 1, 2)]
    hx, hy = round(head[0]), round(head[1])
    details = [(hx - 3, hy - 1, C("#2a3024")), (hx - 5, hy + 2, C("#e6dcc0")), (hx - 2, hy + 3, C("#1a0a0a"))]
    return parts, details


def build():
    moves = [_ghoul(i / 4 * math.tau, (0, 1, 0, 1)[i], 0.0, 2) for i in range(4)]
    attack = [_ghoul(0.4, 0, -0.4, 4), _ghoul(1.0, 1, 1.0, 7)]
    death = [
        turned(_ghoul(0.2, -1, -0.8, 9), rotate=14, pivot=(40, 54)),
        turned(_ghoul(1.6, 3, 0.3, 6), rotate=-22, pivot=(40, 54), offset=(0, 7)),
        combined(_puddle(13), _corpse(0.0)),
        combined(_puddle(21), _corpse(1.5)),
    ]
    idle = [_ghoul(0.0, 0, 0.15, 3), _ghoul(0.0, 1, 0.3, 6)]
    return build_art("ghoul", SIZE, FEET_Y, moves, attack, _ghoul(0.2, 1, 0.2, 5), death, idle=idle)
