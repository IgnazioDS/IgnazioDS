"""The dark knight's animation library, rendered with the shaded rig.

Animations are sequences of Poses. The cape is a verlet chain pinned at the
shoulders, simulated across several loops of each cycle so the recorded
cloth motion is periodic and settles naturally (streaming back while he
walks, swinging on a lunge, pooling when he kneels).
"""

import dataclasses
import math
from functools import lru_cache

from . import raster, rig
from .knight_rig import FRAME_H, FRAME_W, GROUND, Pose, build_parts, joints

CAPE_LINKS, CAPE_LINK_LEN = 9, 3.7
FLASH = rig.Material(rig.ramp("#e9dcd6", "#f6ece6", "#fff8f2"), ambient=0.6)


def _walk_pose(i, frames=8):
    p = i / frames * math.tau
    s, c = math.sin(p), math.cos(p)
    near_thigh, far_thigh = 30 * s, -30 * s
    return Pose(
        lean=7 + 1.5 * math.cos(2 * p),
        near_thigh=near_thigh, near_shin=near_thigh - (5 + 40 * max(0.0, c)),
        far_thigh=far_thigh, far_shin=far_thigh - (5 + 40 * max(0.0, -c)),
        near_upper=14 - 5 * s, near_fore=52 - 6 * s, sword=66 + 5 * s,
        far_upper=22 * s, far_fore=22 * s + 14 + 8 * max(0.0, s),
    )


IDLE = tuple(
    Pose(lean=5 + d, near_thigh=8, near_shin=3, far_thigh=-10, far_shin=-12,
         near_upper=16, near_fore=56 + d, sword=64 - d, far_upper=-8 + d, far_fore=10)
    for d in (0.0, 0.8, 1.4, 0.8)
)

LUNGE_LEGS = dict(near_thigh=36, near_shin=18, far_thigh=-30, far_shin=-18)
STEP_LEGS = dict(near_thigh=22, near_shin=12, far_thigh=-18, far_shin=-22)
ATTACK = (
    Pose(lean=0, **STEP_LEGS, near_upper=150, near_fore=175, sword=205, far_upper=120, far_fore=160),
    Pose(lean=-6, **STEP_LEGS, near_upper=165, near_fore=195, sword=232, far_upper=140, far_fore=185),
    Pose(lean=12, **LUNGE_LEGS, near_upper=115, near_fore=100, sword=110, far_upper=95, far_fore=90,
         smear=((165, 195, 232), (115, 100, 110))),
    Pose(lean=18, **LUNGE_LEGS, near_upper=88, near_fore=86, sword=86, far_upper=70, far_fore=80,
         smear=((122, 112, 130), (88, 86, 86))),
    Pose(lean=16, **LUNGE_LEGS, near_upper=60, near_fore=62, sword=58, far_upper=40, far_fore=60),
    Pose(lean=10, near_thigh=18, near_shin=8, far_thigh=-16, far_shin=-18,
         near_upper=30, near_fore=58, sword=62, far_upper=0, far_fore=20),
)

BRACED = dict(near_thigh=14, near_shin=4, far_thigh=-22, far_shin=-26)
PARRY = (
    Pose(lean=-2, **BRACED, near_upper=95, near_fore=150, sword=160, far_upper=80, far_fore=140),
    Pose(lean=-5, **BRACED, near_upper=92, near_fore=146, sword=150, far_upper=76, far_fore=136),
)

HURT = Pose(lean=-14, head=-10, near_thigh=18, near_shin=26, far_thigh=-20, far_shin=-8,
            near_upper=45, near_fore=95, sword=115, far_upper=-30, far_fore=-10)

SIT = tuple(
    Pose(hip_y=GROUND - 5.5, lean=12 + d, head=8, near_thigh=82, near_shin=14, far_thigh=76, far_shin=24,
         near_upper=40, near_fore=96, sword=0, far_upper=30, far_fore=70, planted=True)
    for d in (0.0, 1.2)
)

KNEEL = tuple(
    Pose(hip_y=GROUND - 14.5, lean=22 + d, head=16, near_thigh=2, near_shin=-88, far_thigh=88, far_shin=4,
         near_upper=58, near_fore=72, sword=0, far_upper=52, far_fore=66, planted=True)
    for d in (0.0, 1.0)
)


def _cape_anchor(pose):
    j = joints(pose)
    nx, ny = j["neck"]
    return (nx - 3.0, ny + 2.5), j["hip"]


def _simulate_cape(poses, wind, cycles=6):
    """Periodic cape chains for a looping sequence of poses."""
    anchors = [_cape_anchor(p) for p in poses]
    (ax, ay), _ = anchors[0]
    points = [(ax - i * 0.6, ay + i * CAPE_LINK_LEN) for i in range(CAPE_LINKS)]
    previous = list(points)
    recorded = []
    for cycle in range(cycles):
        for f, pose in enumerate(poses):
            (ax, ay), (hx, hy) = anchors[f]
            gust = wind(f)
            for _ in range(4):
                moved = [(ax, ay)]
                for i in range(1, CAPE_LINKS):
                    x, y = points[i]
                    px, py = previous[i]
                    weight = i / (CAPE_LINKS - 1)
                    moved.append((x + (x - px) * 0.86 + gust * weight * 0.2, y + (y - py) * 0.86 + 0.14))
                previous, points = points, moved
                points = _constrain(points, hx, hy)
            if cycle == cycles - 1:
                recorded.append(tuple(points))
    return recorded


def _constrain(points, hip_x, hip_y):
    out = list(points)
    for _ in range(3):
        for i in range(1, len(out)):
            (x0, y0), (x1, y1) = out[i - 1], out[i]
            dx, dy = x1 - x0, y1 - y0
            dist = math.hypot(dx, dy) or 1e-6
            k = CAPE_LINK_LEN / dist
            out[i] = (x0 + dx * k, y0 + dy * k)
        for i in range(2, len(out)):
            x, y = out[i]
            back = hip_x - 5.5 if y < hip_y + 14 else hip_x - 3.0
            if x > back:
                out[i] = (back, y)
            if y > GROUND:
                out[i] = (x - (y - GROUND) * 0.6, GROUND)
    return out


def _with_capes(poses, wind):
    chains = _simulate_cape(poses, wind)
    return tuple(dataclasses.replace(p, cape=c) for p, c in zip(poses, chains))


def _render(pose, flash=False):
    parts, details = build_parts(pose)
    if flash:
        parts = [dataclasses.replace(part, material=FLASH, shade=0.0) for part in parts]
        details = [(x, y, c) for x, y, c in details if raster.alpha_of(c) == 255]
    return rig.render(parts, FRAME_W, FRAME_H, details)


@lru_cache(maxsize=1)
def frames():
    """All knight frames by name, in sheet order."""
    walk = _with_capes(tuple(_walk_pose(i) for i in range(8)), lambda f: -0.42 - 0.12 * math.sin(f / 8 * math.tau))
    idle = _with_capes(IDLE, lambda f: -0.08 + 0.06 * math.sin(f / 4 * math.tau))
    attack = _with_capes(ATTACK, lambda f: (-0.1, -0.2, -0.7, -0.8, -0.45, -0.2)[f])
    parry = _with_capes(PARRY, lambda f: 0.15)
    hurt = _with_capes((HURT, HURT), lambda f: 0.35)
    sit = _with_capes(SIT, lambda f: -0.03)
    kneel = _with_capes(KNEEL, lambda f: -0.05)
    named = {}
    for group, poses in (("idle", idle), ("walk", walk), ("atk", attack), ("parry", parry), ("sit", sit), ("kneel", kneel)):
        for i, pose in enumerate(poses):
            named[f"{group}{i}"] = _render(pose)
    named["hurt0"] = _render(hurt[0])
    named["hurt1"] = _render(hurt[1], flash=True)
    return named
