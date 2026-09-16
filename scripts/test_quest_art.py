"""Offline tests for the quest art pipeline: PNG encoding, rasters, sprites.

Run with::

    python3 -m unittest discover -s scripts -p 'test_quest*.py'
"""
import base64
import struct
import unittest
import zlib

from quest.art import png, raster, sprite


def _decode_png(data):
    """Reference decoder (all filter types) -> (width, height, pixels)."""
    if data[:8] != png.SIGNATURE:
        raise AssertionError("bad signature")
    pos, chunks = 8, {}
    idat = b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        if zlib.crc32(tag + body) & 0xFFFFFFFF != crc:
            raise AssertionError(f"bad CRC in {tag!r}")
        if tag == b"IDAT":
            idat += body
        else:
            chunks[tag] = body
        pos += 12 + length
    width, height, depth, ctype = struct.unpack(">IIBB", chunks[b"IHDR"][:10])
    channels = {3: 1, 6: 4}[ctype]
    bits_pp = depth * channels
    stride = (width * bits_pp + 7) // 8
    bpp = max(1, bits_pp // 8)
    raw = zlib.decompress(idat)
    rows, prev = [], bytes(stride)
    for r in range(height):
        start = r * (stride + 1)
        ftype, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if ftype == 1:
                line[i] = (line[i] + a) & 0xFF
            elif ftype == 2:
                line[i] = (line[i] + b) & 0xFF
            elif ftype == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif ftype == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if pa <= pb and pa <= pc else b if pb <= pc else c
                line[i] = (line[i] + pred) & 0xFF
        rows.append(bytes(line))
        prev = bytes(line)
    pixels = []
    if ctype == 6:
        for line in rows:
            for x in range(width):
                r_, g, b_, a_ = line[x * 4:x * 4 + 4]
                pixels.append((r_ << 24) | (g << 16) | (b_ << 8) | a_)
        return width, height, tuple(pixels)
    plte = chunks[b"PLTE"]
    trns = chunks.get(b"tRNS", b"")
    for line in rows:
        for x in range(width):
            bit = x * depth
            idx = (line[bit // 8] >> (8 - depth - bit % 8)) & ((1 << depth) - 1)
            r_, g, b_ = plte[idx * 3:idx * 3 + 3]
            a_ = trns[idx] if idx < len(trns) else 255
            pixels.append((r_ << 24) | (g << 16) | (b_ << 8) | a_)
    return width, height, tuple(pixels)


def _checker(width, height, colors):
    return raster.Image(
        width, height,
        tuple(colors[(x + y) % len(colors)] for y in range(height) for x in range(width)),
    )


class PngEncoding(unittest.TestCase):
    def assertRoundTrip(self, image):
        w, h, px = _decode_png(png.encode(image))
        self.assertEqual((w, h), (image.width, image.height))
        self.assertEqual(px, image.pixels)

    def test_two_colors_use_one_bit_depth(self):
        image = _checker(9, 5, [raster.CLEAR, raster.rgb("#ff5a36")])
        data = png.encode(image)
        self.assertEqual(data[24], 1)  # IHDR bit depth
        self.assertRoundTrip(image)

    def test_sixteen_colors_round_trip(self):
        colors = [raster.rgb(f"#{i:02x}{255 - i:02x}40") for i in range(0, 240, 16)]
        self.assertRoundTrip(_checker(33, 7, colors + [raster.CLEAR]))

    def test_partial_alpha_survives_indexed_mode(self):
        colors = [raster.rgba("#ffffff", 128), raster.rgb("#000000")]
        self.assertRoundTrip(_checker(4, 4, colors))

    def test_many_colors_fall_back_to_rgba(self):
        pixels = tuple((i << 8) | 0xFF for i in range(300))
        image = raster.Image(300, 1, pixels)
        self.assertEqual(png.encode(image)[25], 6)  # IHDR color type
        self.assertRoundTrip(image)

    def test_data_uri_is_base64_png(self):
        uri = png.data_uri(_checker(2, 2, [raster.CLEAR]))
        self.assertTrue(uri.startswith("data:image/png;base64,"))
        payload = base64.b64decode(uri.split(",", 1)[1])
        self.assertEqual(payload[:8], png.SIGNATURE)

    def test_rejects_pixel_count_mismatch(self):
        with self.assertRaises(ValueError):
            png.encode(raster.Image(3, 3, (0,) * 8))


class RasterPrimitives(unittest.TestCase):
    def test_colors_pack_rgba(self):
        self.assertEqual(raster.rgb("#102030"), 0x102030FF)
        self.assertEqual(raster.rgba("#102030", 7), 0x10203007)
        with self.assertRaises(ValueError):
            raster.rgb("102030")

    def test_canvas_clips_out_of_bounds_writes(self):
        canvas = raster.Canvas(4, 3)
        canvas.rect(-2, -2, 10, 10, raster.rgb("#ffffff"))
        image = canvas.freeze()
        self.assertEqual(len(image.pixels), 12)
        self.assertTrue(all(p == raster.rgb("#ffffff") for p in image.pixels))

    def test_wrapping_canvas_continues_across_edges(self):
        canvas = raster.Canvas(5, 1, wrap_x=True)
        canvas.rect(3, 0, 4, 1, raster.rgb("#ffffff"))
        white = raster.rgb("#ffffff")
        self.assertEqual(canvas.freeze().pixels, (white, white, raster.CLEAR, white, white))

    def test_freeze_is_a_snapshot(self):
        canvas = raster.Canvas(2, 1)
        first = canvas.freeze()
        canvas.put(0, 0, raster.rgb("#ffffff"))
        self.assertEqual(first.pixels, (raster.CLEAR, raster.CLEAR))

    def test_blit_skips_transparent_pixels(self):
        base = raster.Canvas(3, 1, raster.rgb("#000000"))
        stamp = raster.Image(2, 1, (raster.CLEAR, raster.rgb("#ffffff")))
        base.blit(stamp, 1, 0)
        self.assertEqual(
            base.freeze().pixels,
            (raster.rgb("#000000"), raster.rgb("#000000"), raster.rgb("#ffffff")),
        )

    def test_scale_nearest_neighbour(self):
        image = raster.Image(2, 1, (1, 2))
        self.assertEqual(raster.scale(image, 2).pixels, (1, 1, 2, 2, 1, 1, 2, 2))

    def test_periodic_noise_wraps(self):
        period = 64
        for x in (0, 5, 17):
            self.assertAlmostEqual(
                raster.periodic_noise(x, period, seed=3),
                raster.periodic_noise(x + period, period, seed=3),
            )


class SpriteHelpers(unittest.TestCase):
    def test_sheet_lays_frames_left_to_right(self):
        white, black = raster.rgb("#ffffff"), raster.rgb("#000000")
        frames = [raster.Image(1, 1, (white,)), raster.Image(1, 1, (black,))]
        sheet = sprite.sheet(frames)
        self.assertEqual((sheet.width, sheet.height, sheet.pixels), (2, 1, (white, black)))
        with self.assertRaises(ValueError):
            sprite.sheet([frames[0], raster.Image(2, 1, (white, white))])

    def test_pad_places_image_on_larger_canvas(self):
        white = raster.rgb("#ffffff")
        padded = sprite.pad(raster.Image(1, 1, (white,)), 3, 2, 2, 1)
        self.assertEqual(padded.pixels, (raster.CLEAR,) * 5 + (white,))


class ArtContracts(unittest.TestCase):
    """The renderer relies on these shapes; broken art should fail here, not in CI's SVG."""

    def test_knight_has_every_animation_frame_at_one_size(self):
        from quest import layout
        from quest.art import knight
        frames = knight.frames()
        self.assertEqual(set(layout.KNIGHT_FRAMES), set(frames))
        sizes = {(f.width, f.height) for f in frames.values()}
        self.assertEqual(len(sizes), 1)
        width, height = sizes.pop()
        self.assertGreater(height, layout.KNIGHT_FEET)

    def test_monsters_cover_all_tiers_with_consistent_frames(self):
        from quest.art import monsters
        arts = monsters.roster()
        self.assertEqual(sorted(arts), [1, 2, 3, 4])
        for art in arts.values():
            frames = (*art.move, *art.attack, art.hurt)
            self.assertEqual(len(art.attack), 2)
            self.assertEqual(len({(f.width, f.height) for f in frames}), 1, art.name)
            self.assertLess(art.feet_y, frames[0].height)

    def test_dragon_frames_complete(self):
        from quest.art import dragon
        frames = dragon.frames()
        self.assertEqual(set(dragon.FRAME_NAMES), set(frames))
        self.assertEqual(len({(f.width, f.height) for f in frames.values()}), 1)

    def test_regions_honour_the_layer_contract(self):
        from quest import layout
        from quest.art import png
        from quest.art.scenery import TITLES, region
        for key, title in TITLES.items():
            art = region(key)
            self.assertEqual((art.key, art.title), (key, title))
            self.assertEqual(art.layers[0].parallax, 0.0, key)
            self.assertGreaterEqual(art.layers[0].image.width, layout.WIDTH, key)
            for layer in art.layers:
                if layer.parallax > 0:
                    self.assertGreaterEqual(layer.image.width, layout.WIDTH, f"{key}/{layer.name}")
            self.assertIn(art.motion, ("drift", "rise", "fall"))
            budget = sum(len(png.encode(layer.image)) for layer in art.layers) / 1024
            self.assertLess(budget, 70, key)

    def test_unknown_region_fails_loudly(self):
        from quest.art.scenery import region
        with self.assertRaises(ValueError):
            region("atlantis")

    def test_effect_sheets_are_uniform(self):
        from quest.art import effects
        for frames in (effects.fire_breath(), effects.ember_burst(), effects.ash_burst(), effects.bonfire()):
            self.assertEqual(len({(f.width, f.height) for f in frames}), 1)


if __name__ == "__main__":
    unittest.main()
