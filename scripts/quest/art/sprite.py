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


def aura(image, inner, outer):
    """A glow hugging a sprite's silhouette: a 1px `inner` ring and a 2px `outer` ring (body left clear)."""
    width, height = image.width, image.height
    solid = [[raster.alpha_of(image.pixels[y * width + x]) > 0 for x in range(width)] for y in range(height)]
    out = []
    for y in range(height):
        for x in range(width):
            if solid[y][x]:
                out.append(raster.CLEAR)
                continue
            near = _within(solid, x, y, 1, width, height)
            out.append(inner if near else outer if _within(solid, x, y, 2, width, height) else raster.CLEAR)
    return raster.Image(width, height, tuple(out))


def _within(solid, x, y, reach, width, height):
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            if abs(dx) + abs(dy) > reach + (1 if reach > 1 else 0):
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and solid[ny][nx]:
                return True
    return False
