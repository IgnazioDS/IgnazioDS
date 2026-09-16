"""Sprite sheet helpers: strip equally sized frames and pad images."""

from . import raster


def sheet(frames):
    """Lay equally sized frames left to right into one strip."""
    first = frames[0]
    for i, frame in enumerate(frames):
        if (frame.width, frame.height) != (first.width, first.height):
            raise ValueError(
                f"frame {i} is {frame.width}x{frame.height}, "
                f"expected {first.width}x{first.height}"
            )
    canvas = raster.Canvas(first.width * len(frames), first.height)
    for i, frame in enumerate(frames):
        canvas.blit(frame, i * first.width, 0)
    return canvas.freeze()


def pad(image, width, height, anchor_x, anchor_y):
    """Place an image on a larger transparent canvas at an offset."""
    canvas = raster.Canvas(width, height)
    canvas.blit(image, anchor_x, anchor_y)
    return canvas.freeze()
