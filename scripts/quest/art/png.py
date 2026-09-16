"""Minimal stdlib PNG encoder tuned for pixel art.

Images with at most 256 distinct colors are written as indexed PNGs (PLTE +
tRNS) at the smallest bit depth that fits; that is what keeps an embedded
parallax layer or sprite sheet down to a few KB. Richer images fall back to
8-bit RGBA. Indexed scanlines use filter 0, as the PNG spec recommends for
palette images.
"""

import base64
import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
_COLOR_INDEXED, _COLOR_RGBA = 3, 6


def encode(image):
    """Encode a raster.Image to PNG bytes."""
    if len(image.pixels) != image.width * image.height:
        raise ValueError(
            f"pixel count {len(image.pixels)} != {image.width}x{image.height}"
        )
    palette = _palette(image.pixels)
    if palette is None:
        return _encode_rgba(image)
    return _encode_indexed(image, palette)


def data_uri(image):
    return "data:image/png;base64," + base64.b64encode(encode(image)).decode("ascii")


def _chunk(tag, data):
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def _header(width, height, depth, color_type):
    return _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, depth, color_type, 0, 0, 0))


def _palette(pixels):
    """Distinct colors, translucent ones first so tRNS can stay short."""
    distinct = set(pixels)
    if len(distinct) > 256:
        return None
    return sorted(distinct, key=lambda c: (c & 0xFF == 0xFF, c))


def _encode_indexed(image, palette):
    index = {color: i for i, color in enumerate(palette)}
    depth = next(d for d in (1, 2, 4, 8) if len(palette) <= 1 << d)
    raw = bytearray()
    for y in range(image.height):
        raw.append(0)
        row = image.pixels[y * image.width:(y + 1) * image.width]
        raw.extend(_pack_row([index[c] for c in row], depth))
    plte = b"".join(struct.pack(">BBB", c >> 24, (c >> 16) & 0xFF, (c >> 8) & 0xFF) for c in palette)
    alphas = [c & 0xFF for c in palette]
    translucent = sum(1 for a in alphas if a < 255)
    chunks = [_header(image.width, image.height, depth, _COLOR_INDEXED), _chunk(b"PLTE", plte)]
    if translucent:
        chunks.append(_chunk(b"tRNS", bytes(alphas[:translucent])))
    chunks.append(_chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
    chunks.append(_chunk(b"IEND", b""))
    return SIGNATURE + b"".join(chunks)


def _pack_row(indices, depth):
    if depth == 8:
        return bytes(indices)
    out, acc, bits = bytearray(), 0, 0
    for value in indices:
        acc = (acc << depth) | value
        bits += depth
        if bits == 8:
            out.append(acc)
            acc, bits = 0, 0
    if bits:
        out.append(acc << (8 - bits))
    return bytes(out)


def _encode_rgba(image):
    raw = bytearray()
    for y in range(image.height):
        raw.append(0)
        for color in image.pixels[y * image.width:(y + 1) * image.width]:
            raw.extend(struct.pack(">I", color))
    return SIGNATURE + b"".join([
        _header(image.width, image.height, 8, _COLOR_RGBA),
        _chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
        _chunk(b"IEND", b""),
    ])
