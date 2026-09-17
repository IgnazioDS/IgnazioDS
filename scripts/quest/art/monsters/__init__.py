"""The bestiary's art. Each monster kind lives in its own module exposing
``build() -> MonsterArt``; `art(kind)` builds and caches one on demand.
"""

import importlib
from functools import lru_cache

from .base import MonsterArt

KINDS = ("bat", "crow", "wolf", "ghoul", "gargoyle", "skeleton", "spider", "wraith", "revenant")


@lru_cache(maxsize=None)
def art(kind):
    """MonsterArt for a kind; unknown kinds fail loudly."""
    if kind not in KINDS:
        raise ValueError(f"unknown monster kind {kind!r}")
    built = importlib.import_module(f"{__name__}.{kind}").build()
    if built.name != kind:
        raise ValueError(f"monster module {kind!r} built art for {built.name!r}")
    return built


__all__ = ["KINDS", "MonsterArt", "art"]
