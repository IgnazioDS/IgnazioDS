"""Shared contract and helpers for monster art.

Every kind is built on the shaded rig, faces left toward the knight, and
renders all of its frames at one size so a single sprite sheet serves the
whole creature: a movement loop, a two-frame attack, a hurt flash, and a
death sequence whose last frame is the remains left on the ground.
"""

import dataclasses
import math
from dataclasses import dataclass

from .. import raster, rig
from ..rig import Capsule, Ellipse, Material, ramp

C = raster.rgb
FLASH = Material(ramp("#eadcf4", "#fbf4ff", "#ffffff"), ambient=0.7)


@dataclass(frozen=True)
class MonsterArt:
    name: str
    move: tuple      # looping movement frames
    idle: tuple      # looping guard stance while it squares up to the knight
    attack: tuple    # (windup, strike)
    hurt: object     # white flash silhouette
    death: tuple     # dying frames; the last is the remains left on the ground
    feet_y: int      # frame row resting on the ground line (flyers hover above it)

    @property
    def shares_idle(self):
        """Flyers keep beating their wings while squaring up: the idle loop is the movement loop."""
        return self.idle is self.move

    @property
    def frames(self):
        """Sheet order: move..., idle... (unless shared with move), windup, strike, hurt, death..."""
        idle = () if self.shares_idle else self.idle
        return (*self.move, *idle, *self.attack, self.hurt, *self.death)

    def index(self, part, k=0):
        """Sheet index of a frame: part in move | idle | windup | strike | hurt | death."""
        m, i = len(self.move), 0 if self.shares_idle else len(self.idle)
        offsets = {"move": 0, "idle": 0 if self.shares_idle else m, "windup": m + i, "strike": m + i + 1,
                   "hurt": m + i + 2, "death": m + i + 3}
        return offsets[part] + k


def seg(origin, angle, length):
    """Point at `length` from origin; angle in degrees, 0 = down, +90 = left (toward the knight)."""
    a = math.radians(angle)
    return (origin[0] - math.sin(a) * length, origin[1] + math.cos(a) * length)


def render(scene, size, flash=False):
    parts, details = scene
    if flash:
        parts = [dataclasses.replace(p, material=FLASH, shade=0.0) for p in parts]
        details = []
    return rig.render(parts, size[0], size[1], details)


def turned(scene, rotate=0.0, pivot=(0.0, 0.0), offset=(0.0, 0.0)):
    """A scene rotated (degrees, clockwise on screen) about pivot, then shifted."""
    parts, details = scene
    return rig.transform(parts, details, rotate=rotate, pivot=pivot, offset=offset)


def extent(parts):
    """Geometric bounds (x0, y0, x1, y1) of a scene's parts."""
    xs, ys = [], []
    for part in parts:
        shape = part.shape
        if isinstance(shape, Capsule):
            for (x, y), r in ((shape.a, shape.r0), (shape.b, shape.r1)):
                xs += [x - r, x + r]
                ys += [y - r, y + r]
        elif isinstance(shape, Ellipse):
            r = max(shape.rx, shape.ry)
            xs += [shape.c[0] - r, shape.c[0] + r]
            ys += [shape.c[1] - r, shape.c[1] + r]
        else:
            xs += [x for x, _ in shape.points]
            ys += [y for _, y in shape.points]
    return min(xs), min(ys), max(xs), max(ys)


def grounded(scene, ground_y, x=None):
    """Shift a scene so its lowest point rests on ground_y (and its middle sits at x, if given)."""
    x0, _, x1, y1 = extent(scene[0])
    dx = 0.0 if x is None else x - (x0 + x1) / 2
    return turned(scene, offset=(dx, ground_y - y1))


def combined(*scenes):
    """Scenes painted in order into one (later scenes over earlier ones)."""
    parts, details = [], []
    for scene_parts, scene_details in scenes:
        parts += scene_parts
        details += scene_details
    return parts, details


def build_art(name, size, feet_y, move, attack, hurt, death, idle=None):
    """move/idle/attack/death: sequences of (parts, details) scenes; hurt: one scene.

    Without an idle stance the movement loop doubles as one (flyers keep beating their wings).
    """
    moving = tuple(render(scene, size) for scene in move)
    return MonsterArt(
        name,
        moving,
        moving if idle is None else tuple(render(scene, size) for scene in idle),
        tuple(render(scene, size) for scene in attack),
        render(hurt, size, flash=True),
        tuple(render(scene, size) for scene in death),
        feet_y,
    )
