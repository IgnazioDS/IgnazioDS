"""Embedded image assets: every PNG is defined once in <defs> as a data URI and
referenced with <use>, so a sprite sheet shown fifty times is stored once.
"""

from dataclasses import dataclass

from ..art import png, sprite


@dataclass(frozen=True)
class Asset:
    id: str
    width: int
    height: int
    frame_w: int  # sheet frame width (== width for single images)


class AssetBook:
    """Collects images while the document is built, then emits <defs>."""

    def __init__(self):
        self._assets = {}
        self._uris = {}

    def image(self, asset_id, image):
        if asset_id in self._assets:
            return self._assets[asset_id]
        asset = Asset(asset_id, image.width, image.height, image.width)
        self._assets[asset_id] = asset
        self._uris[asset_id] = png.data_uri(image)
        return asset

    def sheet(self, asset_id, frames):
        if asset_id in self._assets:
            return self._assets[asset_id]
        strip = sprite.sheet(list(frames))
        asset = Asset(asset_id, strip.width, strip.height, frames[0].width)
        self._assets[asset_id] = asset
        self._uris[asset_id] = png.data_uri(strip)
        return asset

    def defs(self):
        images = "".join(
            f'<image id="{a.id}" width="{a.width}" height="{a.height}" href="{self._uris[a.id]}"/>'
            for a in self._assets.values()
        )
        return f"<defs>{images}</defs>"

