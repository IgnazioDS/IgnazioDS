"""Monsters, one per contribution-intensity tier, built on the shaded rig and
facing left toward the knight: bat (tier 1), ghoul (2), skeleton warrior (3),
wraith (4).

Each MonsterArt has a looping movement cycle, a two-frame attack (windup,
strike) and a hurt flash, all the same frame size.
"""

import dataclasses
import math
from dataclasses import dataclass
from functools import lru_cache

from . import raster, rig
from .rig import Capsule, Ellipse, Material, Part, Poly, ramp


@dataclass(frozen=True)
class MonsterArt:
    name: str
    move: tuple      # looping movement frames
    attack: tuple    # (windup, strike)
    hurt: object     # white flash silhouette
    feet_y: int      # frame row resting on the ground line (flyers hover via layout.FLYER_LIFT)


FLASH = Material(ramp("#eadcf4", "#fbf4ff", "#ffffff"), ambient=0.7)
C = raster.rgb


def seg(origin, angle, length):
    """Point at `length` from origin; angle in degrees, 0 = down, +90 = left (toward the knight)."""
    a = math.radians(angle)
    return (origin[0] - math.sin(a) * length, origin[1] + math.cos(a) * length)


def _render(parts, details, size, flash=False):
    if flash:
        parts = [dataclasses.replace(p, material=FLASH, shade=0.0) for p in parts]
        details = []
    return rig.render(parts, size[0], size[1], details)


def _art(name, builder, size, move_poses, attack_poses, hurt_pose, feet_y):
    move = tuple(_render(*builder(p), size) for p in move_poses)
    attack = tuple(_render(*builder(p), size) for p in attack_poses)
    hurt = _render(*builder(hurt_pose), size, flash=True)
    return MonsterArt(name, move, attack, hurt, feet_y)


# -- bat ----------------------------------------------------------------------------

FUR = Material(ramp("#0e0910", "#1c1222", "#2e2036", "#443250"), rim=C("#7a5a94"), ambient=0.18)
WEB = Material(ramp("#140a18", "#241028", "#381838", "#4e2248"), rim=C("#9a4a7a"), ambient=0.2, rim_cut=0.4)


def _bat(pose):
    beat, bob, dive = pose
    cx, cy = 24, 17 + bob
    parts, details = [], []
    for side in (1, -1):
        shoulder = (cx + 3 * side, cy - 2)
        elbow = (cx + 10 * side, cy - 6 + 7 * beat)
        wrist = (cx + 17 * side, cy - 9 + 12 * beat)
        tips = [(cx + 23 * side, cy - 2 + 14 * beat), (cx + 20 * side, cy + 5 + 9 * beat), (cx + 13 * side, cy + 7 + 4 * beat)]
        outline = [shoulder, elbow, wrist, tips[0]]
        for a, b in zip(tips, tips[1:]):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            outline += [(mid[0] + (wrist[0] - mid[0]) * 0.35, mid[1] + (wrist[1] - mid[1]) * 0.35), b]
        outline.append((cx + 3 * side, cy + 5))
        shade = -0.12 if side == 1 else 0.0
        parts.append(Part(Poly(tuple(outline), bevel=1.5), WEB, bulge=0.3, shade=shade, cast=False))
        parts += [Part(Capsule(wrist, tip, 0.8, 0.5), FUR, shade=shade, seam=False, cast=False) for tip in tips]
        parts += [Part(Capsule(shoulder, elbow, 1.4, 1.0), FUR, shade=shade), Part(Capsule(elbow, wrist, 1.0, 0.8), FUR, shade=shade)]
    parts.append(Part(Ellipse((cx, cy + 1 + dive), 4.6, 6.0, 0.2 * dive), FUR))
    head = (cx - 1 - dive * 2, cy - 5 + dive)
    parts += [Part(Poly(((head[0] - 3, head[1] - 2), (head[0] - 4, head[1] - 8), (head[0] - 0.5, head[1] - 3)), bevel=0.6), FUR, seam=False),
              Part(Poly(((head[0] + 1, head[1] - 3), (head[0] + 3, head[1] - 8), (head[0] + 3.5, head[1] - 2)), bevel=0.6), FUR, seam=False),
              Part(Ellipse(head, 4.0, 3.4), FUR)]
    hx, hy = round(head[0]), round(head[1])
    details += [(hx - 2, hy - 1, C("#ff3b3b")), (hx + 1, hy - 1, C("#ff3b3b")), (hx - 1, hy + 2, C("#f2ead8"))]
    if dive:
        details.append((hx, hy + 2, C("#f2ead8")))
    return parts, details


def bat():
    moves = ((-1.0, 0, 0), (-0.3, 1, 0), (0.8, 2, 0), (0.1, 1, 0))
    return _art("bat", _bat, (48, 36), moves, ((-1.0, -1, 1), (0.9, 2, 2)), (0.2, 1, 0), feet_y=34)


# -- ghoul ---------------------------------------------------------------------------

SKIN = Material(ramp("#141a17", "#243029", "#3a4a3f", "#566b5a", "#7c937c"), rim=C("#b4cca0"), ambient=0.16, rim_cut=0.55)
RAG = Material(ramp("#140f0d", "#261c18", "#3a2c24", "#4e3c30"), rim=C("#6a5646"), ambient=0.2)
CLAW = Material(ramp("#3a3428", "#8a8068", "#d8cfb2"), ambient=0.4)


def _ghoul(pose):
    stride, bob, reach, jaw = pose
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
    details = [(hx - 3, hy - 1, C("#e9ff7a")), (hx - 4, hy - 1, C("#fbffd0")), (hx, hy - 1, C("#9aa84a")),
               (hx - 6, hy + 2, C("#e6dcc0")), (hx - 4, hy + 3, C("#e6dcc0")), (hx - 7, hy + 3, C("#1a0a0a"))]
    for k in range(3):
        rx, ry = round(mid[0] - 2 + k * 3), round(mid[1] - 1)
        details += [(rx, ry, C("#243029")), (rx, ry + 2, C("#243029"))]
    return parts, details


def ghoul():
    moves = tuple((i / 4 * math.tau, (0, 1, 0, 1)[i], 0.0, 2) for i in range(4))
    return _art("ghoul", _ghoul, (64, 58), moves, ((0.4, 0, -0.4, 4), (1.0, 1, 1.0, 7)), (0.2, 1, 0.2, 5),
                feet_y=54)


# -- skeleton warrior ---------------------------------------------------------------

BONE = Material(ramp("#2e2a20", "#5a5242", "#8a8068", "#bab090", "#e2dac0"), spec=C("#fff8e2"), rim=C("#fff2cc"),
                shininess=20, spec_cut=0.92, ambient=0.2)
RUST = Material(ramp("#24160f", "#4a2c1c", "#7a4a2a", "#a86a3a"), spec=C("#d8a070"), ambient=0.2)
IRON = Material(ramp("#24242a", "#44444c", "#6e6e78", "#9c9ca6"), spec=C("#e6e6f0"), shininess=30, spec_cut=0.85, ambient=0.2)
WOOD = Material(ramp("#1a110c", "#34221a", "#503626", "#6e4c34"), ambient=0.2)
SMEAR = Material((raster.rgba("#bdb4a0", 80), raster.rgba("#e6dcc4", 150), raster.rgba("#fff8e8", 210)), ambient=0.55)


def _skeleton(pose):
    stride, bob, sword, swing_from = pose
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
    parts += [Part(Ellipse(skull, 5.6, 5.0), BONE),
              Part(Poly(((skull[0] - 2, skull[1] - 1), (skull[0] - 8, skull[1] + 1), (skull[0] - 8, skull[1] + 5),
                         (skull[0] + 1, skull[1] + 5)), bevel=1.2), BONE, bulge=0.6),
              Part(Poly(((skull[0] - 5.5, skull[1] - 3), (skull[0] - 3, skull[1] - 7.5), (skull[0] + 3, skull[1] - 8),
                         (skull[0] + 6, skull[1] - 3.5), (skull[0] + 8, skull[1] - 2), (skull[0] - 8, skull[1] - 1.5)),
                        bevel=1.6), IRON, bulge=0.8),
              Part(Capsule((skull[0] - 4, skull[1] - 2), (skull[0] - 4.5, skull[1] + 2.5), 0.8, 0.6), IRON, seam=False)]
    sx, sy = round(skull[0]), round(skull[1])
    details = [(sx - 4, sy, C("#0e0a08")), (sx - 5, sy, C("#0e0a08")), (sx - 4, sy + 1, C("#0e0a08")),
               (sx - 4, sy, C("#ff3b30")), (sx - 1, sy, C("#0e0a08")), (sx - 7, sy + 4, C("#0e0a08")),
               (sx - 5, sy + 4, C("#0e0a08")), (sx + 5, sy - 4, C("#c88a50"))]
    shoulder = (neck[0] - 1, neck[1] + 3)
    elbow = seg(shoulder, 30 + sword * 0.35, 9)
    hand = seg(elbow, 45 + sword * 0.6, 8)
    blade_dir = sword
    tip = seg(hand, blade_dir, 20)
    base = seg(hand, blade_dir, 2.5)
    perp = math.radians(blade_dir)
    nx, ny = math.cos(perp), math.sin(perp)
    parts += [Part(Capsule(shoulder, elbow, 1.5, 1.2), BONE), Part(Capsule(elbow, hand, 1.2, 1.0), BONE)]
    parts += [Part(Poly(((base[0] + nx * 1.6, base[1] + ny * 1.6), tip, (base[0] - nx * 1.6, base[1] - ny * 1.6)), bevel=1.0),
                   IRON, bulge=0.3, cast=False),
              Part(Capsule((base[0] + nx * 3.5, base[1] + ny * 3.5), (base[0] - nx * 3.5, base[1] - ny * 3.5), 0.8, 0.8), RUST),
              Part(Ellipse(hand, 1.5, 1.4), BONE)]
    for k in (0.35, 0.55, 0.8):
        rx, ry = seg(hand, blade_dir, 20 * k)
        details.append((round(rx + nx), round(ry + ny), C("#8a5230")))
    if swing_from is not None:
        outer, inner = [], []
        for k in range(9):
            t = k / 8
            angle = swing_from + (blade_dir - swing_from) * (0.5 + 0.5 * t)
            e = seg(shoulder, 30 + angle * 0.35, 9)
            hnd = seg(e, 45 + angle * 0.6, 8)
            outer.append(seg(hnd, angle, 21.5))
            inner.append(seg(hnd, angle, 16 + 3 * (1 - t)))
        parts.append(Part(Poly(tuple(outer) + tuple(reversed(inner)), bevel=2.0), SMEAR, bulge=0.2, seam=False, cast=False))
    return parts, details


def skeleton():
    moves = tuple((i / 4 * math.tau, (0, 1, 0, 1)[i], 70, None) for i in range(4))
    attack = ((0.3, 0, 170, None), (1.2, 1, 40, 170))
    return _art("skeleton", _skeleton, (72, 66), moves, attack, (0.3, 0, 90, None), feet_y=61)


# -- wraith ---------------------------------------------------------------------------

ROBE = Material(ramp("#09070f", "#130f1c", "#1e182c", "#2c243e", "#3e3456"), rim=C("#8a7ac8"), ambient=0.14, rim_cut=0.5)
WISP = Material((raster.rgba("#2c243e", 150), raster.rgba("#3e3456", 110), raster.rgba("#5a4e7c", 70)), ambient=0.3)
VOID = Material(ramp("#030206", "#07050c"), ambient=0.1)
SCYTHE = Material(ramp("#3a4250", "#6a7688", "#a4b0c2", "#dce4f0"), spec=C("#ffffff"), shininess=32, spec_cut=0.75, ambient=0.3)
SPECTRAL = Material((raster.rgba("#7ff6ff", 70), raster.rgba("#b4fbff", 130), raster.rgba("#ffffff", 190)), ambient=0.5)


def _wraith(pose):
    bob, flutter, swing, swing_from = pose
    cx, top = 44, 8 + bob
    hood = (cx - 2, top + 12)
    parts = []
    hem = []
    for k in range(9):
        x = cx + 20 - k * 5.5
        drop = 60 + bob + (4 if (k + flutter) % 2 else -2)
        hem.append((x, drop))
    robe = ((cx - 8, top + 16), (cx + 9, top + 12), (cx + 16, top + 34), (cx + 21, top + 52)) + tuple(hem) + \
           ((cx - 26, top + 50), (cx - 16, top + 30))
    wisps = tuple((x, y + 3) for x, y in hem) + ((cx - 22, 70 + bob), (cx + 18, 70 + bob))
    parts.append(Part(Poly(wisps[::-1] + tuple(hem), bevel=2.0), WISP, bulge=0.2, seam=False, cast=False))
    shoulder = (cx - 2, top + 22)
    elbow = seg(shoulder, 60 + (swing - 160) * 0.3, 10)
    hand = seg(elbow, 100 + (swing - 160) * 0.35, 9)
    handle_top = seg(hand, swing, 34)
    handle_bottom = seg(hand, swing + 180, 16)
    parts.append(Part(Capsule(handle_bottom, handle_top, 1.2, 1.0), WOOD, cast=False))
    a = math.radians(swing)
    blade_pts = []
    for k in range(10):
        t = k / 9
        bx = handle_top[0] - math.cos(a) * 20 * t - math.sin(a) * 5 * math.sin(t * math.pi)
        by = handle_top[1] - math.sin(a) * 20 * t + math.cos(a) * 5 * math.sin(t * math.pi) + 6 * t * t
        blade_pts.append((bx, by))
    inner = [(x + 2.5 * (1 - k / 9), y + 2.5 * (1 - k / 9)) for k, (x, y) in enumerate(blade_pts)]
    parts.append(Part(Poly(tuple(blade_pts) + tuple(reversed(inner)), bevel=1.0), SCYTHE, bulge=0.3, cast=False))
    parts.append(Part(Poly(robe, bevel=3.0), ROBE, bulge=0.55, fold=(5.0, 0.55, 0.1 * flutter)))
    parts += [Part(Poly(((hood[0] - 11, hood[1] + 6), (hood[0] - 7, hood[1] - 9), (hood[0] + 2, hood[1] - 14),
                         (hood[0] + 11, hood[1] - 6), (hood[0] + 12, hood[1] + 8), (hood[0] + 2, hood[1] + 12)), bevel=3.0), ROBE, bulge=0.8),
              Part(Ellipse((hood[0] - 4, hood[1] + 1), 5.0, 7.0, 0.15), VOID, bulge=0.2, seam=False, cast=False)]
    parts += [Part(Capsule(shoulder, elbow, 3.2, 2.6), ROBE, shade=0.05), Part(Capsule(elbow, hand, 2.6, 2.2), ROBE, shade=0.05),
              Part(Ellipse(hand, 1.9, 1.7), BONE)]
    if swing_from is not None:
        outer, inner_arc = [], []
        for k in range(9):
            t = k / 8
            ang = swing_from + (swing - swing_from) * t
            e = seg(shoulder, 60 + (ang - 160) * 0.3, 10)
            h = seg(e, 100 + (ang - 160) * 0.35, 9)
            outer.append(seg(h, ang, 40))
            inner_arc.append(seg(h, ang, 26))
        parts.append(Part(Poly(tuple(outer) + tuple(reversed(inner_arc)), bevel=2.0), SPECTRAL, bulge=0.2, seam=False, cast=False))
    hx, hy = round(hood[0] - 5), round(hood[1])
    details = [(hx - 1, hy, C("#7ff6ff")), (hx, hy, C("#e9ffff")), (hx + 3, hy, C("#7ff6ff")), (hx + 3, hy - 1, C("#e9ffff")),
               (hx - 2, hy, raster.rgba("#7ff6ff", 90)), (hx + 4, hy, raster.rgba("#7ff6ff", 90))]
    return parts, details


def wraith():
    moves = ((0, 0, 162, None), (1, 1, 165, None), (2, 0, 168, None), (1, 1, 165, None))
    attack = ((-1, 0, 215, None), (2, 1, 70, 215))
    return _art("wraith", _wraith, (80, 76), moves, attack, (1, 0, 30, None), feet_y=70)


@lru_cache(maxsize=1)
def roster():
    """Tier (1-4) -> MonsterArt."""
    return {1: bat(), 2: ghoul(), 3: skeleton(), 4: wraith()}
