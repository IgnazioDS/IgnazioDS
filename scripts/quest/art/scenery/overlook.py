"""Prologue vista: a moonlit crag above the valley of the Blood Moon Keep.

The knight rests by a bonfire among the graves of the ten knights who came
before him. Far below, fog fills the valley; beyond it the cathedral city
stands under the blood moon. Sky, skyline and fog are the keep's own images,
shared in the SVG, so the vista only pays for its near layers.
"""

import dataclasses
import random

from .. import raster
from . import Layer, Light, RegionArt, common, paint, region

C = raster.rgb
TILE = 830
SURFACE = 84                      # canvas row of the walking line (screen y 214)
ROCK, ROCK_LIT, ROCK_DARK = C("#170c19"), C("#6e3052"), C("#0c060e")
STONE, STONE_LIT = C("#2e2232"), C("#8a4c6c")
GRAVES_X = (212, 232, 251, 268, 289, 306, 327, 345, 364, 382)


def hills():
    """Two far ridges closing the valley under the city (screen y 172-236)."""
    canvas = raster.Canvas(TILE, 64, wrap_x=True)
    back = common.ridge_heights(TILE, "overlook-back", base=30, amplitude=20, base_cells=5)
    paint.rim_ridge(canvas, back, C("#1f0c22"), C("#7a2c50"))
    common.haze(canvas, 20, 64, C("#3a1432"), density=0.45)
    near = common.ridge_heights(TILE, "overlook-near", base=44, amplitude=16, base_cells=7)
    paint.rim_ridge(canvas, near, C("#12070f"), C("#4e1c3e"))
    return canvas.freeze()


def _surface(x):
    return SURFACE + round(1.6 * raster.periodic_noise(x, TILE, "overlook-surface", octaves=3, base_cells=10))


def crag():
    """The ledge path, a boulder with a dead tree, and ten old graves (screen y 130-240)."""
    canvas = raster.Canvas(TILE, 110, wrap_x=True)
    for x in range(TILE):
        canvas.column(x, _surface(x), 109, ROCK)
    paint.crag(canvas, 30, SURFACE + 2, 92, 34, ROCK, ROCK_LIT, ROCK_DARK, "overlook-boulder")
    paint.crag(canvas, 520, SURFACE + 2, 70, 16, ROCK, ROCK_LIT, ROCK_DARK, "overlook-rise")
    paint.crag(canvas, 700, SURFACE + 2, 110, 24, ROCK, ROCK_LIT, ROCK_DARK, "overlook-shoulder")
    common.dead_tree(canvas, 38, SURFACE - 26, 64, "overlook", C("#0e070f"))
    common.dead_tree(canvas, 716, SURFACE - 16, 40, "overlook-2", C("#0e070f"))
    paint.rim_edges(canvas, (ROCK,), ROCK_LIT, dx=1, dy=-1)
    _strata(canvas)
    paint.dry_grass(canvas, SURFACE - 1, SURFACE + 1, (C("#241222"), C("#301828")), C("#7a3a5a"), 0.35,
                    "overlook", max_h=6)
    for i, gx in enumerate(GRAVES_X):
        _grave(canvas, gx, _surface(gx) + 1, i)
    return canvas.freeze()


def _strata(canvas):
    rng = random.Random("overlook-strata")
    for _ in range(70):
        x, y = rng.randrange(TILE), rng.randrange(SURFACE + 4, 108)
        length = rng.randint(4, 16)
        for k in range(length):
            if canvas.get(x + k, y) == ROCK:
                canvas.put(x + k, y, ROCK_DARK)
        if canvas.get(x, y - 1) == ROCK:
            canvas.put(x, y - 1, C("#2a1428"))


def _grave(canvas, x, base, index):
    """Every other marker is a sword driven into the earth; the rest are weathered stones."""
    if index % 3 == 1:
        paint.planted_blade(canvas, x, base, 14 + index % 2 * 3, (index % 2) * 2 - 1,
                            C("#4a4656"), C("#8e8aa0"), C("#7a5a2a"), C("#2a1a14"))
        return
    if index % 3 == 0:
        canvas.rect(x - 1, base - 13, 3, 13, STONE)
        canvas.rect(x - 4, base - 10, 9, 3, STONE)
        canvas.column(x + 1, base - 13, base - 1, STONE_LIT)
        canvas.rect(x - 4, base - 10, 9, 1, STONE_LIT)
        return
    lean = (index % 2) * 2 - 1
    canvas.polygon([(x - 4, base), (x - 4 + lean, base - 8), (x - 1 + lean, base - 11), (x + 2 + lean, base - 11),
                    (x + 5 + lean, base - 8), (x + 5, base)], STONE)
    for y in range(base - 10, base):
        canvas.put(x + 4 + (lean if y < base - 6 else 0), y, STONE_LIT)
    canvas.put(x, base - 7, C("#140a14"))


def front():
    """Dark tufts and pebbles breaking the bottom edge (screen y 226-240)."""
    canvas = raster.Canvas(TILE, 14, wrap_x=True)
    rng = random.Random("overlook-front")
    x = 20
    while x < TILE:
        for k in range(rng.randint(5, 9)):
            paint.blade(canvas, x + k * 2, 14, rng.randint(5, 12), rng.choice((-2, -1, 1, 2)), C("#08040a"))
        canvas.rect(x + rng.randint(14, 30), 11, rng.randint(4, 8), 3, C("#0c070e"))
        x += rng.randint(120, 220)
    return canvas.freeze()


def build():
    keep = {layer.name: layer for layer in region("keep").layers}
    shared = dict(source="keep", front=False)
    return RegionArt(
        key="overlook",
        title="",
        layers=(
            dataclasses.replace(keep["sky"], **shared),
            dataclasses.replace(keep["city"], y=62, parallax=0.04, offset=80, **shared),
            Layer("hills", hills(), 172, 0.12),
            dataclasses.replace(keep["fog"], y=186, parallax=0.2, effect="sway", **shared),
            Layer("crag", crag(), 130, 1.0),
            Layer("front", front(), 226, 1.3, front=True),
        ),
        lights=(
            Light(300, 100, 120, 110, "#ff5a78", 0.18),
            Light(210, 196, 150, 22, "#b04a70", 0.12, parallax=0.2),
        ),
        particles=(C("#d04a70"), C("#ff8aa0"), C("#8a1a3a")),
        motion="fall",
        grade=("#2a0a1e", 0.05),
    )
