"""Skeleton warrior (tier 3): an iron-helmed dead soldier with a rusted sword
and a broken shield. Slain, it comes apart and clatters into a bone pile.
"""

import math

from .. import raster
from ..rig import Capsule, Ellipse, Material, Part, Poly, ramp
from .base import C, build_art, grounded, seg, turned

SIZE, FEET_Y = (72, 66), 61
BONE = Material(ramp("#2e2a20", "#5a5242", "#8a8068", "#bab090", "#e2dac0"), spec=C("#fff8e2"), rim=C("#fff2cc"),
                shininess=20, spec_cut=0.92, ambient=0.2)
RUST = Material(ramp("#24160f", "#4a2c1c", "#7a4a2a", "#a86a3a"), spec=C("#d8a070"), ambient=0.2)
IRON = Material(ramp("#24242a", "#44444c", "#6e6e78", "#9c9ca6"), spec=C("#e6e6f0"), shininess=30, spec_cut=0.85, ambient=0.2)
WOOD = Material(ramp("#1a110c", "#34221a", "#503626", "#6e4c34"), ambient=0.2)
SMEAR = Material((raster.rgba("#bdb4a0", 80), raster.rgba("#e6dcc4", 150), raster.rgba("#fff8e8", 210)), ambient=0.55)
DUST = Material((raster.rgba("#8a8068", 60), raster.rgba("#bab090", 110), raster.rgba("#e2dac0", 150)), ambient=0.5)


def _skull(skull, lit_eye=True):
    parts = [Part(Ellipse(skull, 5.6, 5.0), BONE),
             Part(Poly(((skull[0] - 2, skull[1] - 1), (skull[0] - 8, skull[1] + 1), (skull[0] - 8, skull[1] + 5),
                        (skull[0] + 1, skull[1] + 5)), bevel=1.2), BONE, bulge=0.6),
             Part(Poly(((skull[0] - 5.5, skull[1] - 3), (skull[0] - 3, skull[1] - 7.5), (skull[0] + 3, skull[1] - 8),
                        (skull[0] + 6, skull[1] - 3.5), (skull[0] + 8, skull[1] - 2), (skull[0] - 8, skull[1] - 1.5)),
                       bevel=1.6), IRON, bulge=0.8),
             Part(Capsule((skull[0] - 4, skull[1] - 2), (skull[0] - 4.5, skull[1] + 2.5), 0.8, 0.6), IRON, seam=False)]
    sx, sy = round(skull[0]), round(skull[1])
    eye = C("#ff3b30") if lit_eye else C("#0e0a08")
    details = [(sx - 4, sy, C("#0e0a08")), (sx - 5, sy, C("#0e0a08")), (sx - 4, sy + 1, C("#0e0a08")),
               (sx - 4, sy, eye), (sx - 1, sy, C("#0e0a08")), (sx - 7, sy + 4, C("#0e0a08")),
               (sx - 5, sy + 4, C("#0e0a08")), (sx + 5, sy - 4, C("#c88a50"))]
    return parts, details


def _blade(hand, direction, swing_from=None, shoulder=None):
    tip = seg(hand, direction, 20)
    base = seg(hand, direction, 2.5)
    perp = math.radians(direction)
    nx, ny = math.cos(perp), math.sin(perp)
    parts = [Part(Poly(((base[0] + nx * 1.6, base[1] + ny * 1.6), tip, (base[0] - nx * 1.6, base[1] - ny * 1.6)), bevel=1.0),
                  IRON, bulge=0.3, cast=False),
             Part(Capsule((base[0] + nx * 3.5, base[1] + ny * 3.5), (base[0] - nx * 3.5, base[1] - ny * 3.5), 0.8, 0.8), RUST)]
    details = []
    for k in (0.35, 0.55, 0.8):
        rx, ry = seg(hand, direction, 20 * k)
        details.append((round(rx + nx), round(ry + ny), C("#8a5230")))
    return parts, details


def _skeleton(stride, bob, sword, swing_from, lit_eye=True):
    pelvis = (40, 36 + bob)
    neck = (37, 18 + bob)
    skull = (33, 11 + bob)
    parts = []

    def leg(side, phase):
        swing = math.sin(stride + phase) * 20
        hip = (pelvis[0] + side, pelvis[1] + 1)
        knee = seg(hip, swing, 11)
        ankle = seg(knee, swing * 0.3 - (8 if math.sin(stride + phase) > 0 else 0), 11)
        shade = -0.2 if side > 0 else 0.0
        return [Part(Capsule(hip, knee, 1.8, 1.4), BONE, shade=shade), Part(Ellipse(knee, 1.9, 1.6), BONE, shade=shade + 0.06),
                Part(Capsule(knee, ankle, 1.4, 1.1), BONE, shade=shade),
                Part(Poly(((ankle[0] + 1, ankle[1] - 1), (ankle[0] - 5, ankle[1] + 1), (ankle[0] - 5, ankle[1] + 2.5),
                           (ankle[0] + 1.5, ankle[1] + 2.5)), bevel=0.8), BONE, shade=shade)]

    shield_arm_shoulder = (neck[0] + 3, neck[1] + 3)
    shield_hand = seg(seg(shield_arm_shoulder, 25 + math.sin(stride) * 10, 9), 60, 8)
    parts.append(Part(Capsule(shield_arm_shoulder, shield_hand, 1.4, 1.1), BONE, shade=-0.2))
    parts.append(Part(Poly(tuple((shield_hand[0] + 8 * math.cos(a) * 0.55, shield_hand[1] + 8 * math.sin(a))
                                 for a in [k / 10 * math.tau for k in range(10)] if not 0.2 < a < 1.2), bevel=2.0), WOOD, bulge=0.6))
    parts.append(Part(Ellipse(shield_hand, 1.6, 1.6), RUST))
    parts += leg(2, math.pi)
    parts.append(Part(Capsule(pelvis, neck, 1.6, 1.4), BONE))
    for k in range(5):
        y = neck[1] + 4 + k * 3
        back, front = (neck[0] + 1.5 - k * 0.2, y), (neck[0] - 6 + k * 0.4, y + 2)
        parts.append(Part(Capsule(back, ((back[0] + front[0]) / 2, y - 1.5), 0.9, 0.9), BONE, seam=False))
        parts.append(Part(Capsule(((back[0] + front[0]) / 2, y - 1.5), front, 0.9, 0.8), BONE, seam=False))
    parts.append(Part(Capsule((neck[0] - 6, neck[1] + 5), (neck[0] - 5, neck[1] + 17), 0.9, 0.8), BONE, seam=False))
    parts.append(Part(Ellipse(pelvis, 6.0, 3.4), BONE))
    parts.append(Part(Poly(((pelvis[0] - 6, pelvis[1]), (pelvis[0] + 6, pelvis[1] - 1), (pelvis[0] + 7, pelvis[1] + 8),
                            (pelvis[0] + 3, pelvis[1] + 6), (pelvis[0] - 1, pelvis[1] + 10), (pelvis[0] - 6, pelvis[1] + 7)),
                           bevel=1.0), RAG, bulge=0.4))
    parts += leg(-1, 0.0)
    skull_parts, details = _skull(skull, lit_eye)
    arm_parts, arm_details = _sword_arm((neck[0] - 1, neck[1] + 3), sword, swing_from)
    return parts + skull_parts + arm_parts, details + arm_details


def _sword_arm(shoulder, sword, swing_from):
    """The sword arm, the rusted blade and, mid-swing, the smear it leaves."""
    elbow = seg(shoulder, 30 + sword * 0.35, 9)
    hand = seg(elbow, 45 + sword * 0.6, 8)
    blade_parts, details = _blade(hand, sword)
    parts = [Part(Capsule(shoulder, elbow, 1.5, 1.2), BONE), Part(Capsule(elbow, hand, 1.2, 1.0), BONE)]
    parts += blade_parts + [Part(Ellipse(hand, 1.5, 1.4), BONE)]
    if swing_from is not None:
        outer, inner = [], []
        for k in range(9):
            t = k / 8
            angle = swing_from + (sword - swing_from) * (0.5 + 0.5 * t)
            swing_hand = seg(seg(shoulder, 30 + angle * 0.35, 9), 45 + angle * 0.6, 8)
            outer.append(seg(swing_hand, angle, 21.5))
            inner.append(seg(swing_hand, angle, 16 + 3 * (1 - t)))
        parts.append(Part(Poly(tuple(outer) + tuple(reversed(inner)), bevel=2.0), SMEAR, bulge=0.2, seam=False, cast=False))
    return parts, details


RAG = Material(ramp("#140f0d", "#261c18", "#3a2c24", "#4e3c30"), rim=C("#6a5646"), ambient=0.2)


def _bone(a, b, r=1.2):
    return Part(Capsule(a, b, r, r * 0.8), BONE)


def _pile(settle):
    """The warrior in pieces: shield propped on the heap, ribs, long bones, blade, and the helmed skull."""
    g = 61
    parts = [Part(Ellipse((38, g + 0.5), 20 + 3 * settle, 1.6), DUST, bulge=0.1, seam=False, cast=False)]
    shield = tuple((52 + 8 * math.cos(a) * 0.55, g - 7 + 8 * math.sin(a)) for a in [k / 10 * math.tau for k in range(10)]
                   if not 0.2 < a < 1.2)
    parts.append(Part(Poly(shield, bevel=2.0), WOOD, bulge=0.6, shade=-0.1))
    parts += [_bone((22, g - 1), (36, g - 2)), _bone((40, g - 1), (55, g)), _bone((30, g - 3), (44, g - 5), 1.1)]
    parts.append(Part(Ellipse((42, g - 4), 6.0, 3.0, 0.25), BONE))
    for k in range(4):
        cx = 29 + k * 4
        parts.append(Part(Capsule((cx - 2, g - 2), (cx, g - 7 + k % 2), 0.9, 0.8), BONE, seam=False))
        parts.append(Part(Capsule((cx, g - 7 + k % 2), (cx + 2.5, g - 3), 0.9, 0.8), BONE, seam=False))
    blade = _blade((58, g - 1), 95)
    parts += blade[0]
    skull = turned(_skull((0, 0), lit_eye=False), rotate=-100 + 20 * settle, pivot=(0, 0), offset=(14, g - 5))
    parts += skull[0]
    return parts, blade[1] + skull[1]


def build():
    moves = [_skeleton(i / 4 * math.tau, (0, 1, 0, 1)[i], 70, None) for i in range(4)]
    attack = [_skeleton(0.3, 0, 170, None), _skeleton(1.2, 1, 40, 170)]
    death = [
        turned(_skeleton(0.4, -1, 210, None, lit_eye=False), rotate=12, pivot=(40, 61)),
        grounded(turned(_skeleton(1.6, 4, 120, None, lit_eye=False), rotate=-34, pivot=(40, 61)), 62, x=38),
        _pile(0.0),
        _pile(1.0),
    ]
    idle = [_skeleton(0.5, 0, 96, None), _skeleton(0.5, 1, 104, None)]
    return build_art("skeleton", SIZE, FEET_Y, moves, attack, _skeleton(0.3, 0, 90, None), death, idle=idle)
