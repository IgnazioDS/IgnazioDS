"""Region registry and the contract every region module fulfils.

A region module (violet.py, wood.py, crimson.py, keep.py, and the prologue's
overlook.py) exposes ``build() -> RegionArt``. Layers are painted back to
front; any layer with parallax > 0 must tile horizontally (paint it on a
wrap_x Canvas). Layers flagged ``front`` are drawn over the actors for
foreground framing. Sky actors (a distant dragon, bat flocks) are drawn
after the first ``sky_layers`` layers, so skylines pass in front of them.
"""

import importlib
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Layer:
    name: str
    image: object          # raster.Image; tileable horizontally when parallax > 0
    y: int                 # top edge on screen (game px)
    parallax: float        # 0 static sky, <1 distant, 1 ground plane, >1 foreground
    offset: int = 0        # initial x shift (frames a landmark on arrival)
    front: bool = False    # drawn over the actors (keep it sparse / near the bottom edge)
    opacity: float = 1.0
    source: str = None     # region that owns the image when a layer is shared (one copy in the SVG)
    effect: str = ""       # ambient CSS motion: "" | "shimmer" (rays breathe) | "sway" (fog and smoke drift)


@dataclass(frozen=True)
class Light:
    """Soft glow rendered as an SVG radial gradient over the painted layers."""
    x: float
    y: float
    rx: float
    ry: float
    color: str             # "#rrggbb"
    opacity: float
    parallax: float = 0.0  # moves with the matching layer so glows stay on their source
    flicker: str = "none"  # none | fire | pulse | lightning
    front: bool = False    # True: over the actors (god rays, lightning wash)


@dataclass(frozen=True)
class Motif:
    """A small looping sprite that brings a region to life (CSS-animated on its own short period).

    x, y: the sprite's top-left on screen at scroll 0. Pinned motifs ride the
    layer with the same parallax (repeating at its tile width); flights travel
    by `flight` keyframes ((percent, dx, dy), ...) over `period` seconds and are
    only visible while that CSS animation runs, so a browser without CSS
    animation shows none. A flight must loop without a visible jump: tiled
    flights move by whole tiles, others finish out of view.
    """
    name: str
    frames: tuple           # raster Images of one size; a single frame for stills
    x: float
    y: float
    parallax: float = 0.0
    fps: float = 8.0
    front: bool = False     # over the actors
    sky: bool = False       # behind the skyline, with the other sky actors
    flight: tuple = ()
    period: float = 0.0
    delay: float = 0.0
    tile: tuple = (1, 1)    # (columns, rows) copies laid edge to edge (rain)
    effect: str = ""        # "bolt": hidden except during the region's lightning flashes


@dataclass(frozen=True)
class RegionArt:
    key: str
    title: str
    layers: tuple          # Layer, back -> front
    lights: tuple = ()     # Light
    particles: tuple = ()  # raster colors for ambient motes
    motion: str = "drift"  # drift | rise | fall
    grade: tuple = None    # ("#rrggbb", opacity) mood tint over the world, or None
    sky_layers: int = 1    # back layers painted before sky actors
    motifs: tuple = ()     # Motif


TITLES = {
    "violet": "THE VIOLET MOOR",
    "wood": "THE HOLLOW WOOD",
    "crimson": "THE CRIMSON WASTE",
    "keep": "THE BLOOD MOON KEEP",
}
SCENES = ("overlook",)     # untitled story scenes: the prologue vista


@lru_cache(maxsize=None)
def region(key):
    """RegionArt for a region key; unknown keys fail loudly."""
    if key not in TITLES and key not in SCENES:
        raise ValueError(f"unknown region {key!r}")
    module = importlib.import_module(f"{__name__}.{key}")
    art = module.build()
    if art.key != key:
        raise ValueError(f"region module {key!r} built art for {art.key!r}")
    return art
