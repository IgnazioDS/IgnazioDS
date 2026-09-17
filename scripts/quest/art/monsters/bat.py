"""Blood bat (tier 1): leathery wings, red eyes, a shriek and a spiralling fall."""

from ..rig import Capsule, Ellipse, Material, Part, Poly, ramp
from .base import C, build_art, turned

SIZE, FEET_Y = (48, 36), 34
FUR = Material(ramp("#0e0910", "#1c1222", "#2e2036", "#443250"), rim=C("#7a5a94"), ambient=0.18)
WEB = Material(ramp("#140a18", "#241028", "#381838", "#4e2248"), rim=C("#9a4a7a"), ambient=0.2, rim_cut=0.4)
BLOOD = Material(ramp("#2a0610", "#4a0c1a", "#6a1424"), ambient=0.3)


def _bat(beat, bob, dive):
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


def _remains():
    """On its back in a small dark stain, wings splayed and limp."""
    stain = ([Part(Ellipse((24, 33), 11, 2.2), BLOOD, bulge=0.1, seam=False, cast=False)], [])
    body = turned(_bat(0.25, 0, 0), rotate=180, pivot=(24, 17), offset=(0, 13))
    parts, details = body
    details = [(x, y, color) for x, y, color in details if color != C("#ff3b3b")]
    return stain[0] + parts, details


def build():
    moves = [_bat(-1.0, 0, 0), _bat(-0.3, 1, 0), _bat(0.8, 2, 0), _bat(0.1, 1, 0)]
    attack = [_bat(-1.0, -1, 1), _bat(0.9, 2, 2)]
    death = [
        turned(_bat(-1.0, 0, 1), rotate=-28, pivot=(24, 17)),
        turned(_bat(0.6, 0, 2), rotate=150, pivot=(24, 18), offset=(0, 4)),
        _remains(),
    ]
    return build_art("bat", SIZE, FEET_Y, moves, attack, _bat(0.2, 1, 0), death)
