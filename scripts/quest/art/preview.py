"""Dev tool: composite a region at several scroll positions into a preview PNG.

    cd scripts && python3 -m quest.art.preview wood --scroll 0 700 1600 --out /tmp/wood.png

Layers are stacked with alpha blending, lights are approximated as soft
radial glows, the knight is placed on the ground line for scale, and the
result is upscaled 2x (the size the README shows). Prints per-layer PNG
sizes and color counts so art stays inside its byte budget.
"""

import argparse
import math
import time

from .. import layout
from . import knight, png, raster
from .scenery import region


def _blend(dst, src):
    a = raster.alpha_of(src) / 255
    if a >= 1:
        return src
    if a <= 0:
        return dst
    out = 0xFF
    for shift in (24, 16, 8):
        s, d = (src >> shift) & 0xFF, (dst >> shift) & 0xFF
        out |= round(d + (s - d) * a) << shift
    return out


def _stamp(buf, image, x0, y0):
    for y in range(image.height):
        yy = y0 + y
        if not 0 <= yy < layout.HEIGHT:
            continue
        for x in range(image.width):
            xx = x0 + x
            if 0 <= xx < layout.WIDTH:
                src = image.pixels[y * image.width + x]
                if raster.alpha_of(src):
                    i = yy * layout.WIDTH + xx
                    buf[i] = _blend(buf[i], src)


def _layer(buf, layer, scroll):
    if layer.parallax == 0:
        _stamp(buf, _faded(layer), 0, layer.y)
        return
    width = layer.image.width
    shift = layer.offset - scroll * layer.parallax
    x = math.floor(shift % width) - width
    faded = _faded(layer)
    while x < layout.WIDTH:
        _stamp(buf, faded, x, layer.y)
        x += width


def _faded(layer):
    if layer.opacity >= 1:
        return layer.image
    k = layer.opacity
    return raster.Image(
        layer.image.width, layer.image.height,
        tuple((p & ~0xFF) | round(raster.alpha_of(p) * k) for p in layer.image.pixels),
    )


def _light(buf, light, scroll):
    cx = light.x - scroll * light.parallax
    color = raster.rgb(light.color) & ~0xFF
    for y in range(max(0, int(light.y - light.ry)), min(layout.HEIGHT, int(light.y + light.ry) + 1)):
        for x in range(max(0, int(cx - light.rx)), min(layout.WIDTH, int(cx + light.rx) + 1)):
            d = math.hypot((x - cx) / light.rx, (y - light.y) / light.ry)
            if d < 1:
                alpha = round(255 * light.opacity * (1 - d) ** 2)
                i = y * layout.WIDTH + x
                buf[i] = _blend(buf[i], color | alpha)


def composite(art, scroll, with_knight=True):
    buf = [raster.rgb("#000000")] * (layout.WIDTH * layout.HEIGHT)
    for layer in art.layers:
        if not layer.front:
            _layer(buf, layer, scroll)
    for light in art.lights:
        if not light.front:
            _light(buf, light, scroll)
    if with_knight:
        _stamp(buf, knight.frames()["idle0"], layout.KNIGHT_X, layout.GROUND_Y - layout.KNIGHT_FEET)
    for layer in art.layers:
        if layer.front:
            _layer(buf, layer, scroll)
    for light in art.lights:
        if light.front:
            _light(buf, light, scroll)
    if art.grade:
        tint = raster.rgba(art.grade[0], round(255 * art.grade[1]))
        buf = [_blend(p, tint) for p in buf]
    return raster.Image(layout.WIDTH, layout.HEIGHT, tuple(buf))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("region")
    parser.add_argument("--scroll", type=float, nargs="+", default=[0.0, 700.0, 1600.0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--no-knight", action="store_true")
    args = parser.parse_args()

    started = time.time()
    art = region(args.region)
    built = time.time() - started
    total = 0
    for layer in art.layers:
        size = len(png.encode(layer.image))
        total += size
        colors = len(set(layer.image.pixels))
        print(f"  {layer.name:<14} {layer.image.width:>4}x{layer.image.height:<4} y={layer.y:<4} "
              f"parallax={layer.parallax:<5} front={layer.front!s:<5} {size / 1024:6.1f} KiB {colors:>4} colors")
    print(f"built in {built:.2f}s, layers total {total / 1024:.1f} KiB (budget 70 KiB), lights {len(art.lights)}")

    frames = [composite(art, s, not args.no_knight) for s in args.scroll]
    sheet = raster.Canvas(layout.WIDTH, layout.HEIGHT * len(frames) + 4 * (len(frames) - 1), raster.rgb("#111111"))
    for i, frame in enumerate(frames):
        sheet.blit(frame, 0, i * (layout.HEIGHT + 4))
    with open(args.out, "wb") as handle:
        handle.write(png.encode(raster.scale(sheet.freeze(), 2)))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
