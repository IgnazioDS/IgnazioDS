"""Revenant (tier 4, the Violet Moor and the Crimson Waste): a knight who fell
on this road long ago and rose again in rusted plate, soul-fire behind the
visor and a notched greatsword in hand. Built on the dark knight's own rig,
mirrored to face him and re-armoured. It kneels when it dies, then collapses,
leaving empty armour and the blade.
"""

import dataclasses

from .. import raster, rig
from .. import knight_rig as kr
from ..knight import ATTACK, HURT, IDLE, KNEEL, _walk_pose, _with_capes
from ..knight_rig import Pose, build_parts
from ..rig import Material, ramp
from .base import build_art

SIZE, FEET_Y = (kr.FRAME_W, kr.FRAME_H), kr.GROUND
C = raster.rgb

PALETTE = {
    kr.STEEL: Material(ramp("#0e0907", "#1b120d", "#2b1d14", "#3e2a1c", "#553b27", "#6e5034"),
                       spec=C("#b08a64"), rim=C("#c8674a"), shininess=30, spec_cut=0.9, rim_cut=0.5, ambient=0.14),
    kr.CLOTH: Material(ramp("#060806", "#0d110d", "#161c16", "#212a20", "#2c382a"), rim=C("#4e6a4a"), ambient=0.12, rim_cut=0.55),
    kr.LINING: Material(ramp("#0a1a0e", "#133018", "#1e4a24", "#2c6a34"), rim=C("#5aba6a"), ambient=0.2),
    kr.BLADE: Material(ramp("#15171b", "#2a2d33", "#44474e", "#62656c", "#85878e"), spec=C("#c8c8d0"), rim=C("#9aa0aa"),
                       shininess=30, spec_cut=0.8, rim_cut=0.4, ambient=0.28),
    kr.GOLD: Material(ramp("#1a1208", "#33250f", "#4e3a1a", "#6a5026"), spec=C("#a88a52"), ambient=0.22),
    kr.SMEAR: Material((raster.rgba("#1e5a2c", 50), raster.rgba("#3e9a52", 90), raster.rgba("#9ae8a8", 130)), ambient=0.55),
}
SOUL_FIRE = {kr.EMBER: C("#5aff7a"), kr.EMBER_CORE: C("#e4ffe4"), kr.EMBER_HAZE: raster.rgba("#5aff7a", 90)}


def _scene(pose, eyes=True):
    parts, details = build_parts(pose)
    parts = [dataclasses.replace(p, material=PALETTE.get(p.material, p.material)) for p in parts]
    recolored = []
    for x, y, color in details:
        if color in SOUL_FIRE:
            if not eyes:
                continue
            color = SOUL_FIRE[color]
        elif raster.alpha_of(color) < 255 and not eyes:
            continue
        recolored.append((x, y, color))
    return rig.transform(parts, recolored, mirror=kr.FRAME_W)


FALLEN = Pose(hip_y=kr.GROUND - 5.0, lean=84, head=8, near_thigh=-78, near_shin=-88, far_thigh=-84, far_shin=-92,
              near_upper=120, near_fore=100, sword=96, far_upper=150, far_fore=130, planted=True)
HEAP = Pose(hip_y=kr.GROUND - 3.5, lean=90, head=26, near_thigh=-84, near_shin=-92, far_thigh=-88, far_shin=-94,
            near_upper=160, near_fore=140, sword=92, far_upper=170, far_fore=160, planted=True)


def _caped(poses, gust):
    return _with_capes(tuple(poses), lambda f: gust)


def build():
    walk = _caped((dataclasses.replace(_walk_pose(i * 2), lean=12) for i in range(4)), -0.3)
    attack = _caped((ATTACK[1], ATTACK[2]), -0.5)
    recoil, kneel = _caped((dataclasses.replace(HURT, lean=-20, head=-18),), 0.4)[0], _caped((KNEEL[0],), -0.05)[0]
    hurt = _caped((HURT,), 0.35)[0]
    death = [_scene(recoil), _scene(kneel, eyes=False), _scene(FALLEN, eyes=False), _scene(HEAP, eyes=False)]
    guard = _caped((dataclasses.replace(IDLE[0], lean=9), dataclasses.replace(IDLE[2], lean=10)), -0.12)
    return build_art("revenant", SIZE, FEET_Y, [_scene(p) for p in walk], [_scene(p) for p in attack], _scene(hurt), death,
                     idle=[_scene(p) for p in guard])
