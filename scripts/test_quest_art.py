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


class RigTransforms(unittest.TestCase):
    def setUp(self):
        from quest.art import rig
        self.rig = rig
        self.mat = rig.Material(rig.ramp("#000000", "#ffffff"))

    def test_scale_and_offset_move_points_and_radii(self):
        rig = self.rig
        parts = [rig.Part(rig.Capsule((2, 4), (6, 4), 2.0, 1.0), self.mat)]
        (moved,), marks = rig.transform(parts, [(2, 4, 7)], scale=0.5, offset=(10, 20))
        self.assertEqual((moved.shape.a, moved.shape.b), ((11.0, 22.0), (13.0, 22.0)))
        self.assertEqual((moved.shape.r0, moved.shape.r1), (1.0, 0.5))
        self.assertEqual(marks, [(11, 22, 7)])

    def test_mirror_flips_geometry_but_keeps_the_light(self):
        rig = self.rig
        part = rig.Part(rig.Ellipse((6, 8), 5, 3, 0.4), self.mat)
        (flipped,), _ = rig.transform([part], mirror=20)
        self.assertEqual(flipped.shape.c, (14.0, 8.0))
        self.assertAlmostEqual(flipped.shape.angle, -0.4)
        original = rig.render([part], 20, 16)
        mirrored = rig.render([flipped], 20, 16)
        mask = lambda img: [[raster.alpha_of(img.at(x, y)) > 0 for x in range(20)] for y in range(16)]
        self.assertEqual(mask(mirrored), [row[::-1] for row in mask(original)])
        self.assertNotEqual(mirrored.pixels, tuple(p for row in range(16) for p in reversed(original.pixels[row * 20:(row + 1) * 20])))

    def test_rotation_turns_about_the_pivot(self):
        rig = self.rig
        parts = [rig.Part(rig.Poly(((10, 0), (12, 0), (12, 2))), self.mat)]
        (turned,), _ = rig.transform(parts, rotate=90, pivot=(10, 0))
        for got, want in zip(turned.shape.points, ((10, 0), (10, 2), (8, 2))):
            self.assertAlmostEqual(got[0], want[0])
            self.assertAlmostEqual(got[1], want[1])


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

    def test_every_monster_kind_has_a_complete_uniform_sheet(self):
        from quest import bestiary
        from quest.art import monsters
        self.assertEqual(set(monsters.KINDS), set(bestiary.KINDS))
        for kind in monsters.KINDS:
            art = monsters.art(kind)
            self.assertEqual(art.name, kind)
            self.assertGreaterEqual(len(art.move), 4, kind)
            self.assertGreaterEqual(len(art.idle), 2, kind)
            self.assertEqual(len(art.attack), 2, kind)
            self.assertGreaterEqual(len(art.death), 3, kind)
            self.assertEqual(len({(f.width, f.height) for f in art.frames}), 1, kind)
            self.assertLess(art.feet_y, art.frames[0].height, kind)

    def test_remains_lie_on_the_ground_line(self):
        from quest.art import monsters
        for kind in monsters.KINDS:
            art = monsters.art(kind)
            remains = art.death[-1]
            rows = [y for y in range(remains.height)
                    if any(raster.alpha_of(remains.at(x, y)) for x in range(remains.width))]
            self.assertTrue(rows, kind)
            self.assertLessEqual(abs(rows[-1] - art.feet_y), 4, f"{kind} remains float or sink")

    def test_sheet_indices_follow_the_documented_order(self):
        from quest.art import monsters
        art = monsters.art("wolf")
        self.assertIs(art.frames[art.index("idle", 1)], art.idle[1])
        self.assertIs(art.frames[art.index("windup")], art.attack[0])
        self.assertIs(art.frames[art.index("strike")], art.attack[1])
        self.assertIs(art.frames[art.index("hurt")], art.hurt)
        self.assertIs(art.frames[art.index("death", 2)], art.death[2])

    def test_unknown_monster_kind_fails_loudly(self):
        from quest.art import monsters
        with self.assertRaises(ValueError):
            monsters.art("kraken")

    def test_aura_hugs_the_silhouette_without_covering_it(self):
        white, red, dim = raster.rgb("#ffffff"), raster.rgba("#ff0000", 200), raster.rgba("#800000", 90)
        body = raster.Image(5, 5, tuple(white if (x, y) == (2, 2) else raster.CLEAR for y in range(5) for x in range(5)))
        glow = sprite.aura(body, red, dim)
        self.assertEqual(glow.at(2, 2), raster.CLEAR)
        for x, y in ((1, 2), (3, 2), (2, 1), (2, 3)):
            self.assertEqual(glow.at(x, y), red)
        self.assertEqual(glow.at(0, 2), dim)

    def test_dragon_frames_complete(self):
        from quest.art import dragon
        frames = dragon.frames()
        self.assertEqual(set(dragon.FRAME_NAMES), set(frames))
        self.assertEqual(len({(f.width, f.height) for f in frames.values()}), 1)

    def test_distant_wyrm_flies_on_uniform_frames(self):
        from quest.art import dragon
        frames = dragon.flyby_frames()
        self.assertEqual(len(frames), 4)
        self.assertEqual({(f.width, f.height) for f in frames}, {(dragon.FLYBY_W, dragon.FLYBY_H)})
        for frame in frames:
            rows = [y for y in range(frame.height) if any(raster.alpha_of(frame.at(x, y)) for x in range(frame.width))]
            self.assertGreater(rows[0], 0, "wing tips clipped at the top edge")
            self.assertLess(rows[-1], frame.height - 1, "tail clipped at the bottom edge")

    def test_prologue_vista_borrows_the_keep_backdrop(self):
        from quest import layout
        from quest.art import png
        from quest.art.scenery import region
        vista, keep = region("overlook"), region("keep")
        keep_images = {layer.name: layer.image for layer in keep.layers}
        own_bytes = 0
        for layer in vista.layers:
            if layer.source == "keep":
                self.assertIs(layer.image, keep_images[layer.name])
            else:
                own_bytes += len(png.encode(layer.image))
                if layer.parallax > 0:
                    self.assertGreaterEqual(layer.image.width, layout.WIDTH, layer.name)
        self.assertLess(own_bytes / 1024, 12)

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

    def test_region_motifs_are_well_formed(self):
        from quest import layout
        from quest.art.scenery import SCENES, TITLES, region
        for key in (*TITLES, *SCENES):
            art = region(key)
            parallaxes = {layer.parallax for layer in art.layers}
            for motif in art.motifs:
                label = f"{key}/{motif.name}"
                self.assertEqual(len({(f.width, f.height) for f in motif.frames}), 1, label)
                self.assertTrue(motif.parallax == 0 or motif.parallax in parallaxes, label)
                if motif.flight:
                    self.assertGreater(motif.period, 0, label)
                    self.assertEqual(motif.flight[0][:2], (0, 0), label)
                    self.assertEqual(motif.flight[-1][0], 100, label)
                    self._assert_flight_loops_seamlessly(motif, label)

    def _assert_flight_loops_seamlessly(self, motif, label):
        from quest import layout
        frame_w, frame_h = motif.frames[0].width, motif.frames[0].height
        _, dx, dy = motif.flight[-1]
        _, x0, y0 = motif.flight[0]
        if motif.tile != (1, 1):
            self.assertEqual((dx % frame_w, dy % frame_h), (0, 0), f"{label} must drift by whole tiles")
            cols, rows = motif.tile
            for sx, sy in ((x0, y0), (dx, dy)):
                self.assertLessEqual(motif.x + sx, 0, label)
                self.assertGreaterEqual(motif.x + sx + cols * frame_w, layout.WIDTH, label)
                self.assertLessEqual(motif.y + sy, 0, label)
                self.assertGreaterEqual(motif.y + sy + rows * frame_h, layout.HEIGHT, label)
            return
        for sx, sy in ((x0, y0), (dx, dy)):
            x, y = motif.x + sx, motif.y + sy
            out = x >= layout.WIDTH or x + frame_w <= 0 or y + frame_h <= 0 or y >= layout.HEIGHT
            self.assertTrue(out, f"{label} must start and finish out of view")

    def test_rain_tiles_seamlessly(self):
        from quest.art.scenery import motifs
        (tile,) = motifs.rain_tile(size=32, drops=40)
        wrapped = raster.Canvas(32, 32, wrap_x=True)
        wrapped.blit(tile, 0, 0)
        self.assertEqual(wrapped.freeze().pixels, tile.pixels)

    def test_hud_art_fits_its_slots(self):
        from quest.art import hud
        self.assertEqual((hud.portrait().width, hud.portrait().height), (hud.MEDALLION, hud.MEDALLION))
        short = hud.nameplate("GHOUL", "JUL 4", 3, 2)
        long = hud.nameplate("BROODMOTHER", "SEP 14", 144, 3, style="elite")
        self.assertEqual(hud.crown().height, 6)
        self.assertLess(short.width, long.width)
        self.assertEqual(short.height, long.height)
        self.assertLessEqual(hud.nameplate("THE ASHEN WYRM", "DEC 31", 9999, 5, style="boss").width, 230)

    def test_unknown_region_fails_loudly(self):
        from quest.art.scenery import region
        with self.assertRaises(ValueError):
            region("atlantis")

    def test_effect_sheets_are_uniform(self):
        from quest.art import effects
        sheets = [effects.fire_breath(), effects.ember_burst(), effects.ash_burst(), effects.bonfire()]
        sheets += [effects.hit_flash(blow, heavy) for blow in effects.CUT_ANGLES for heavy in (False, True)]
        for frames in sheets:
            self.assertEqual(len({(f.width, f.height) for f in frames}), 1)

    def test_walkers_square_up_instead_of_running_in_place(self):
        from quest.art import monsters
        for kind in ("wolf", "ghoul", "skeleton", "spider", "revenant"):
            art = monsters.art(kind)
            self.assertFalse(set(map(id, art.idle)) & set(map(id, art.move)), kind)
        bat = monsters.art("bat")
        self.assertIs(bat.idle, bat.move)
        self.assertEqual(len(bat.frames), len(bat.move) + len(bat.attack) + 1 + len(bat.death))
        self.assertIs(bat.frames[bat.index("idle", 1)], bat.move[1])
        self.assertIs(bat.frames[bat.index("windup")], bat.attack[0])


if __name__ == "__main__":
    unittest.main()
