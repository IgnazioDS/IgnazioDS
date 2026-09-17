"""HUD pixel art: the knight's portrait medallion, the iron health frame, the
souls plate, foe nameplates and the wyrm's bar. Everything is drawn at game
resolution with the palette of the rest of the quest (iron, gold, ember).
"""

import dataclasses
import math
from functools import lru_cache

from . import font, knight, raster, rig
from .knight_rig import EMBER, EMBER_CORE, build_parts, joints

C = raster.rgb
IRON, IRON_LIT, IRON_DARK = C("#3a3044"), C("#6e5f7e"), C("#150f1a")
GOLD, GOLD_LIT = C("#b8862e"), C("#f5c55c")
BACKING = raster.rgba("#07050a", 222)
MEDALLION = 26
PORTRAIT_SCALE = 1.2
# GitHub's dark-theme contribution greens by monster tier; the wyrm's day burns.
TIER_COLORS = {1: "#0e4429", 2: "#006d32", 3: "#26a641", 4: "#39d353", 5: "#ff6a2e"}


def _ring(canvas, cx, cy, radius, color, thickness=1.0):
    for y in range(canvas.height):
        for x in range(canvas.width):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if radius - thickness <= d <= radius:
                canvas.put(x, y, color)


@lru_cache(maxsize=1)
def portrait():
    """The dark knight's helm and pauldron in a gold-studded iron medallion."""
    size = MEDALLION
    c = size / 2
    canvas = raster.Canvas(size, size)
    for y in range(size):
        for x in range(size):
            if math.hypot(x + 0.5 - c, y + 0.5 - c) <= c - 2:
                canvas.put(x, y, C("#1a1024") if y < c else C("#120a18"))
    pose = dataclasses.replace(knight.IDLE[0], head=4)
    hx, hy = joints(pose)["head"]
    scale = PORTRAIT_SCALE
    parts, details = rig.transform(*build_parts(pose), scale=scale, offset=(c - 1 - hx * scale, c - 1 - hy * scale))
    bust = rig.render(parts, size, size, [(x + dx, y, color) for x, y, color in details
                                          if color in (EMBER, EMBER_CORE) for dx in (0, 1)])
    for y in range(size):
        for x in range(size):
            if math.hypot(x + 0.5 - c, y + 0.5 - c) <= c - 2.5 and raster.alpha_of(bust.at(x, y)):
                canvas.put(x, y, bust.at(x, y))
    _ring(canvas, c, c, c - 0.5, IRON_DARK)
    _ring(canvas, c, c, c - 1.5, IRON)
    _ring(canvas, c, c, c - 2.3, IRON_LIT, thickness=0.8)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        canvas.put(round(c + math.cos(a) * (c - 1.6) - 0.5), round(c + math.sin(a) * (c - 1.6) - 0.5), GOLD_LIT if k % 2 else GOLD)
    return canvas.freeze()


def bar_frame(width, height=10):
    """An iron slot with gold end caps; the fill is animated over it by the renderer."""
    canvas = raster.Canvas(width, height, BACKING)
    canvas.rect(0, 0, width, 1, IRON_LIT)
    canvas.rect(0, height - 1, width, 1, IRON_DARK)
    canvas.rect(0, 0, 1, height, IRON)
    canvas.rect(width - 1, 0, 1, height, IRON)
    canvas.rect(1, 1, width - 2, height - 2, C("#1a0f14"))
    for x in (0, width - 3):
        canvas.rect(x, 2, 3, height - 4, GOLD)
        canvas.put(x + 1, 3, GOLD_LIT)
    return canvas.freeze()


def souls_plate(width=104, height=15):
    """Dark capsule behind the souls count, with gold fleurons at both ends."""
    canvas = raster.Canvas(width, height)
    r = height / 2
    for y in range(height):
        for x in range(width):
            dx = max(r - x - 0.5, x + 0.5 - (width - r), 0)
            dy = y + 0.5 - r
            if dx * dx + dy * dy <= r * r:
                edge = dx * dx + dy * dy > (r - 1.2) ** 2
                canvas.put(x, y, IRON if edge else BACKING)
    for x in (3, width - 4):
        canvas.put(x, height // 2, GOLD_LIT)
        canvas.put(x, height // 2 - 1, GOLD)
        canvas.put(x, height // 2 + 1, GOLD)
    return canvas.freeze()


def crown():
    """A small gold crown with blood-red gems: the mark of a chapter's champion."""
    rows = ("#.#.#", "#####", "#r#r#", "#####")
    canvas = raster.Canvas(7, 6)
    for y, row in enumerate(rows):
        for x, cell in enumerate(row):
            if cell != ".":
                canvas.put(x + 1, y + 1, C("#ff3a4a") if cell == "r" else GOLD_LIT if y == 0 else GOLD)
    return canvas.freeze()


def nameplate(title, date, count, tier, style="foe"):
    """[tier square] (crown) NAME · DATE · COUNT on a thin iron-edged plate. style: foe | elite | boss."""
    name_ramp = font.BONE if style == "foe" else font.EMBER
    pieces = [font.render(title, name_ramp), font.render(f"· {date} ·", font.GOLD), font.render(str(count), font.SOUL)]
    if style == "elite":
        pieces.insert(0, crown())
    gap, square = 3, 7
    width = 6 + square + gap + sum(p.width for p in pieces) + gap * (len(pieces) - 1) + 4
    height = max(p.height for p in pieces) + 3
    canvas = raster.Canvas(width, height, BACKING)
    edge = C("#8a2a2a") if style != "foe" else IRON
    canvas.rect(0, 0, width, 1, edge)
    canvas.rect(0, height - 1, width, 1, IRON_DARK)
    for x in (0, width - 1):
        canvas.rect(x, 0, 1, height, edge)
    sy = (height - square) // 2
    canvas.rect(4, sy, square, square, C(TIER_COLORS[tier]))
    canvas.rect(4, sy, square, 1, raster.rgba("#ffffff", 60))
    x = 4 + square + gap
    for piece in pieces:
        canvas.blit(piece, x, (height - piece.height) // 2 + 1)
        x += piece.width + gap
    return canvas.freeze()
