"""Offline tests for the rendered quest SVG: validity, looping, budget, honesty.

Run with::

    python3 -m unittest discover -s scripts -p 'test_quest*.py'
"""
import base64
import re
import unittest
import xml.dom.minidom

from quest import roster, sim
from quest.art import png
from quest.art.scenery import region
from quest.svg import boss, document, hud, world
from test_quest_sim import PATTERN, TODAY, _calendar

SIZE_BUDGET_KIB = 700
SEEDS = [f"quest-2026-{month:02d}-{day:02d}" for month in (1, 6, 9) for day in (3, 11, 19, 27)]


def _x_at(points, t):
    """Piecewise-linear value of [(t, x)] keyframes at time t."""
    if t <= points[0][0]:
        return points[0][1]
    for (t0, x0), (t1, x1) in zip(points, points[1:]):
        if t0 <= t <= t1:
            return x0 if t1 == t0 else x0 + (x1 - x0) * (t - t0) / (t1 - t0)
    return points[-1][1]


class RenderedQuest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = roster.build(_calendar(PATTERN), year_total=5434, today=TODAY, size=24)
        cls.script = sim.simulate(cls.roster, "render-test")
        cls.svg = document.render(cls.script, cls.roster)

    def test_is_well_formed_xml(self):
        xml.dom.minidom.parseString(self.svg)

    def test_has_no_scripts_or_external_resources(self):
        self.assertNotIn("<script", self.svg)
        hrefs = re.findall(r'href="([^"]+)"', self.svg)
        external = [h for h in hrefs if not (h.startswith("#") or h.startswith("data:image/png;base64,")
                                             or h == "https://eleventh.dev")]
        self.assertEqual(external, [])

    def test_every_timeline_shares_one_duration(self):
        self.assertEqual(len(set(re.findall(r'dur="([^"]+)"', self.svg))), 1)

    def test_key_times_are_valid_and_strictly_increasing(self):
        for match in re.finditer(r"<(animate\w*)([^>]*)/>", self.svg):
            attrs = match.group(2)
            keys_attr = re.search(r'keyTimes="([^"]+)"', attrs)
            if not keys_attr:
                continue
            keys = [float(k) for k in keys_attr.group(1).split(";")]
            self.assertEqual(keys[0], 0.0)
            self.assertTrue(all(b > a for a, b in zip(keys, keys[1:])), attrs[:120])
            self.assertLessEqual(keys[-1], 1.0)
            values = re.search(r'values="([^"]+)"', attrs)
            if values:
                self.assertEqual(len(values.group(1).split(";")), len(keys))
            if 'calcMode="linear"' in attrs and "animateMotion" not in match.group(1):
                self.assertEqual(keys[-1], 1.0)

    def test_attribution_survives_in_the_artifact(self):
        self.assertIn("built by Ignazio De Santis", self.svg)
        self.assertIn('<a href="https://eleventh.dev">', self.svg)
        self.assertIn("<desc>", self.svg)

    def test_stays_inside_the_size_budget(self):
        self.assertLess(len(self.svg.encode()) / 1024, SIZE_BUDGET_KIB)

    def test_embedded_images_are_png(self):
        uris = re.findall(r'href="data:image/png;base64,([^"]+)"', self.svg)
        self.assertGreater(len(uris), 10)
        for payload in uris:
            self.assertEqual(base64.b64decode(payload)[:8], png.SIGNATURE)

    def test_souls_counter_ends_at_the_real_total(self):
        self.assertIn(f'id="souls-{self.roster.souls_total}"', self.svg)
        self.assertEqual(self.script.souls[-1][1], self.roster.souls_total)

    def test_every_region_is_painted(self):
        for key in ("violet", "wood", "crimson", "keep"):
            self.assertIn(f'id="{key}-', self.svg)


class ChoreographyAcrossSeeds(unittest.TestCase):
    """Timing invariants swept over many daily seeds (every pattern the dailies can hit)."""

    @classmethod
    def setUpClass(cls):
        cls.roster = roster.build(_calendar(PATTERN), year_total=5434, today=TODAY, size=24)
        cls.scripts = [sim.simulate(cls.roster, seed) for seed in SEEDS]
        cls.tiny = [sim.simulate(roster.build(_calendar(counts), 20, TODAY, size=24), "tiny")
                    for counts in ([0, 7, 0], [3, 0, 9, 0], [2, 5, 0, 8, 0], [1, 2, 3, 0])]

    def test_knight_is_fully_lunged_at_every_blow_on_the_wyrm(self):
        for script in self.scripts + self.tiny:
            points = boss.dash_points(script)
            for hit in script.boss.hits:
                self.assertAlmostEqual(_x_at(points, hit), boss.DASH, places=6)

    def test_knight_dash_never_teleports(self):
        for script in self.scripts:
            points = boss.dash_points(script)
            for (t0, x0), (t1, x1) in zip(points, points[1:]):
                if x1 != x0:
                    self.assertGreaterEqual(t1 - t0, 0.1 - 1e-9)

    def test_date_labels_never_overlap(self):
        for script in self.scripts + self.tiny:
            windows = hud.date_windows(script)
            for (_, _, end), (_, start, _) in zip(windows, windows[1:]):
                self.assertLessEqual(end, start + 1e-9)

    def test_title_cards_never_overlap(self):
        for script in self.scripts + self.tiny:
            cards = hud.card_schedule(script)
            self.assertTrue(any(card.key == "game-title" for card in cards))
            for a, b in zip(cards, cards[1:]):
                self.assertLessEqual(a.end, b.start + 1e-9, (a.key, b.key))


class ScrollingLights(unittest.TestCase):
    def test_lights_on_tiled_layers_repeat_across_the_scroll(self):
        art = region("keep")
        brazier = next(light for light in art.lights if light.flicker == "fire")
        tile = next(layer.image.width for layer in art.layers if layer.parallax == brazier.parallax)
        offsets = world.light_repeats(brazier, art, travel=2500)
        self.assertEqual(offsets[0], 0)
        self.assertTrue(all(b - a == tile for a, b in zip(offsets, offsets[1:])))
        self.assertGreaterEqual(offsets[-1], 2500)

    def test_static_lights_are_not_repeated(self):
        art = region("keep")
        moon = next(light for light in art.lights if light.parallax == 0)
        self.assertEqual(world.light_repeats(moon, art, travel=2500), (0,))


if __name__ == "__main__":
    unittest.main()
