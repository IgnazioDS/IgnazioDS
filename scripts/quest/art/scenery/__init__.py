"""Region registry and the contract every region module fulfils.

A region module (violet.py, wood.py, crimson.py, keep.py) exposes
``build() -> RegionArt``. Layers are painted back to front; any layer with
parallax > 0 must tile horizontally (paint it on a wrap_x Canvas). Layers
flagged ``front`` are drawn over the actors for foreground framing.
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
class RegionArt:
    key: str
    title: str
    layers: tuple          # Layer, back -> front
    lights: tuple = ()     # Light
    particles: tuple = ()  # raster colors for ambient motes
    motion: str = "drift"  # drift | rise | fall
    grade: tuple = None    # ("#rrggbb", opacity) mood tint over the world, or None


TITLES = {
    "violet": "THE VIOLET MOOR",
    "wood": "THE HOLLOW WOOD",
    "crimson": "THE CRIMSON WASTE",
    "keep": "THE BLOOD MOON KEEP",
}


@lru_cache(maxsize=None)
def region(key):
    """RegionArt for a region key; unknown keys fail loudly."""
    if key not in TITLES:
        raise ValueError(f"unknown region {key!r}")
    module = importlib.import_module(f"{__name__}.{key}")
    art = module.build()
    if art.key != key:
        raise ValueError(f"region module {key!r} built art for {art.key!r}")
    return art
