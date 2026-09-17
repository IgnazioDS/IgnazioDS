"""Wraith (tier 4): a hooded void with cold eyes and a scythe. When it is cut
down the robe folds in on itself, the spirit tears away in pale wisps, and
only an empty shroud and the scythe are left.
"""

import math

from .. import raster
from ..rig import Capsule, Ellipse, Material, Part, Poly, ramp
from .base import C, build_art, combined, seg

SIZE, FEET_Y = (80, 76), 70
ROBE = Material(ramp("#09070f", "#130f1c", "#1e182c", "#2c243e", "#3e3456"), rim=C("#8a7ac8"), ambient=0.14, rim_cut=0.5)
WISP = Material((raster.rgba("#2c243e", 150), raster.rgba("#3e3456", 110), raster.rgba("#5a4e7c", 70)), ambient=0.3)
VOID = Material(ramp("#030206", "#07050c"), ambient=0.1)
SCYTHE = Material(ramp("#3a4250", "#6a7688", "#a4b0c2", "#dce4f0"), spec=C("#ffffff"), shininess=32, spec_cut=0.75, ambient=0.3)
SPECTRAL = Material((raster.rgba("#7ff6ff", 70), raster.rgba("#b4fbff", 130), raster.rgba("#ffffff", 190)), ambient=0.5)
WOOD = Material(ramp("#1a110c", "#34221a", "#503626", "#6e4c34"), ambient=0.2)
BONE = Material(ramp("#2e2a20", "#5a5242", "#8a8068", "#bab090", "#e2dac0"), ambient=0.2)


def _scythe(hand, swing):
    handle_top = seg(hand, swing, 34)
    handle_bottom = seg(hand, swing + 180, 16)
    parts = [Part(Capsule(handle_bottom, handle_top, 1.2, 1.0), WOOD, cast=False)]
    a = math.radians(swing)
    blade_pts = []
    for k in range(10):
        t = k / 9
        bx = handle_top[0] - math.cos(a) * 20 * t - math.sin(a) * 5 * math.sin(t * math.pi)
        by = handle_top[1] - math.sin(a) * 20 * t + math.cos(a) * 5 * math.sin(t * math.pi) + 6 * t * t
        blade_pts.append((bx, by))
    inner = [(x + 2.5 * (1 - k / 9), y + 2.5 * (1 - k / 9)) for k, (x, y) in enumerate(blade_pts)]
    parts.append(Part(Poly(tuple(blade_pts) + tuple(reversed(inner)), bevel=1.0), SCYTHE, bulge=0.3, cast=False))
    return parts


def _wraith(bob, flutter, swing, swing_from, eyes=True):
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
    parts += _scythe(hand, swing)
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
    details = []
    if eyes:
        details = [(hx - 1, hy, C("#7ff6ff")), (hx, hy, C("#e9ffff")), (hx + 3, hy, C("#7ff6ff")), (hx + 3, hy - 1, C("#e9ffff")),
                   (hx - 2, hy, raster.rgba("#7ff6ff", 90)), (hx + 4, hy, raster.rgba("#7ff6ff", 90))]
    return parts, details


GHOST = Material((raster.rgba("#5fd8ff", 36), raster.rgba("#9ff0ff", 80), raster.rgba("#e6ffff", 140)), ambient=0.45)


def _spirit(rise, spread, size):
    """Faint teardrop wisps tearing up and away from the shroud, trailing downward."""
    parts, details = [], []
    for k, (dx, lag) in enumerate(((-9, 0.0), (3, 0.35), (12, 0.15))):
        x = 42 + dx * spread + (lag - 0.2) * rise * 0.3
        y = 30 - rise * (1 - lag * 0.5)
        r = size * (1 - lag * 0.3)
        parts.append(Part(Capsule((x - dx * 0.08, y + r * 4.5), (x, y), 0.4, r), GHOST, bulge=0.4, seam=False, cast=False))
        details.append((round(x), round(y), raster.rgba("#ffffff", 200)))
    return parts, details


def _shroud(fall):
    """The empty robe collapsing onto the ground, hood last."""
    g = FEET_Y - 1
    heap = ((14, g), (20, g - 6 - 8 * (1 - fall)), (32, g - 10 - 14 * (1 - fall)), (46, g - 12 - 18 * (1 - fall)),
            (58, g - 7 - 10 * (1 - fall)), (68, g - 2), (58, g + 1), (40, g + 1), (24, g + 1))
    hood = (38 + 6 * fall, g - 14 - 20 * (1 - fall))
    parts = [Part(Poly(heap, bevel=3.0), ROBE, bulge=0.5, fold=(4.0, 0.5, 0.2)),
             Part(Poly(((hood[0] - 9, hood[1] + 6), (hood[0] - 5, hood[1] - 6), (hood[0] + 3, hood[1] - 9),
                        (hood[0] + 10, hood[1] - 3), (hood[0] + 9, hood[1] + 7), (hood[0] + 1, hood[1] + 9)), bevel=2.5),
                  ROBE, bulge=0.8, shade=-0.05),
             Part(Ellipse((hood[0] - 3, hood[1] + 1), 3.6, 4.6, 0.15), VOID, bulge=0.2, seam=False, cast=False)]
    return parts, []


def _fallen_scythe():
    return _scythe((58, FEET_Y - 1), 96), []


def build():
    moves = [_wraith(0, 0, 162, None), _wraith(1, 1, 165, None), _wraith(2, 0, 168, None), _wraith(1, 1, 165, None)]
    attack = [_wraith(-1, 0, 215, None), _wraith(2, 1, 70, 215)]
    death = [
        combined(_wraith(-2, 1, 120, None, eyes=False), _spirit(2, 0.6, 2.2)),
        combined(_fallen_scythe(), _shroud(0.45), _spirit(12, 1.0, 2.8)),
        combined(_fallen_scythe(), _shroud(1.0), _spirit(26, 1.4, 2.0)),
        combined(_fallen_scythe(), _shroud(1.0)),
    ]
    return build_art("wraith", SIZE, FEET_Y, moves, attack, _wraith(1, 0, 30, None), death)
