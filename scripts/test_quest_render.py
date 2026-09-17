"""Offline tests for the rendered quest SVG: validity, looping, budget, honesty.

Run with::

    python3 -m unittest discover -s scripts -p 'test_quest*.py'
"""
import base64
import re
import unittest
import xml.dom.minidom

from quest import roster, sim, wyrm
from quest.art import png
from quest.art.scenery import region
from quest.svg import cards, document, hud, world
from test_quest_sim import PATTERN, TODAY, _calendar

SIZE_BUDGET_KIB = 700
SEEDS = [f"quest-2026-{month:02d}-{day:02d}" for month in (1, 6, 9) for day in (3, 11, 19, 27)]


def _move_at(moves, t):
    """(dx, dy) of the knight's piecewise-linear offset track at time t."""
    xs = [(k[0], k[1]) for k in moves]
    ys = [(k[0], k[2]) for k in moves]
    return (_x_at(xs, t), _x_at(ys, t))


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

    def assertInSvg(self, needle):
        """Containment without dumping half a megabyte of SVG on failure."""
        if needle not in self.svg:
            self.fail(f"not in the rendered SVG: {needle[:160]!r}")

    def assertNotInSvg(self, needle):
        if needle in self.svg:
            self.fail(f"unexpectedly in the rendered SVG: {needle[:160]!r}")

    def test_is_well_formed_xml(self):
        xml.dom.minidom.parseString(self.svg)

    def test_has_no_scripts_or_external_resources(self):
        self.assertNotInSvg("<script")
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
        self.assertInSvg("built by Ignazio De Santis")
        self.assertInSvg('<a href="https://eleventh.dev">')
        self.assertInSvg("<desc>")

    def test_stays_inside_the_size_budget(self):
        self.assertLess(len(self.svg.encode()) / 1024, SIZE_BUDGET_KIB)

    def test_embedded_images_are_png(self):
        uris = re.findall(r'href="data:image/png;base64,([^"]+)"', self.svg)
        self.assertGreater(len(uris), 10)
        for payload in uris:
            self.assertEqual(base64.b64decode(payload)[:8], png.SIGNATURE)

    def test_souls_counter_ends_at_the_real_total(self):
        self.assertInSvg(f'id="souls-{self.roster.souls_total}"')
        self.assertEqual(self.script.souls[-1][1], self.roster.souls_total)

    def test_every_region_is_painted(self):
        for key in ("violet", "wood", "crimson", "keep"):
            self.assertInSvg(f'id="{key}-')

    def test_prologue_vista_shares_the_keep_images(self):
        self.assertInSvg('id="overlook-crag"')
        for shared in ("sky", "city", "fog"):
            self.assertNotInSvg(f'id="overlook-{shared}"')
            self.assertEqual(self.svg.count(f'id="keep-{shared}"'), 1)

    def test_elites_glow_and_every_kind_on_screen_is_embedded(self):
        kinds = {enc.kind for enc in self.script.encounters}
        for kind in kinds:
            self.assertEqual(self.svg.count(f'id="monster-{kind}"'), 1)
        for kind in {enc.kind for enc in self.script.encounters if enc.elite}:
            self.assertInSvg(f'href="#aura-{kind}"')

    def test_every_blow_and_parry_leaves_its_mark(self):
        hits = sum(len(enc.hits) for enc in self.script.encounters) + len(self.script.boss.hits)
        parries = sum(1 for enc in self.script.encounters for a in enc.attacks if a.outcome == "parry")
        marks = len(re.findall(r'href="#cut-(?:slash|rise|thrust|riposte|plunge)-(?:gold|cold)"', self.svg))
        self.assertEqual(marks, hits + parries)

    def test_every_animated_class_has_its_css_rule(self):
        style = re.search(r"<style>(.*?)</style>", self.svg).group(1)
        used = set()
        for attr in re.findall(r'class="([^"]+)"', self.svg):
            used.update(attr.split())
        for name in used:
            self.assertIn(f".{name}{{", style, name)
        self.assertTrue(any(name.startswith("st") for name in used))
        self.assertTrue(any(name.startswith("fl-") for name in used))

    def test_flights_stay_hidden_without_css_animation(self):
        style = re.search(r"<style>(.*?)</style>", self.svg).group(1)
        wrappers = re.findall(r'<g([^>]*) class="(fl-[^"]+)"', self.svg)
        self.assertTrue(wrappers)
        for attrs, name in wrappers:
            self.assertIn('opacity="0"', attrs, name)
            keyframes = re.search(rf"@keyframes {re.escape(name)}{{(.*?)}}}}", style).group(1)
            self.assertEqual(keyframes.count("opacity:1"), keyframes.count("%{"), name)

    def test_every_foe_gets_a_nameplate_with_its_real_count(self):
        from quest.svg import hud
        shown = [w for w in hud.date_windows(self.script) if w[2] > w[1]]
        self.assertEqual(len(re.findall(r'id="plate-\d{4}-\d\d-\d\d"', self.svg)), len({iso for iso, _, _ in shown}))
        self.assertInSvg(f'id="plate-{self.roster.boss.date}"')

    def test_nameplates_never_cover_the_health_frame_or_souls_plate(self):
        from quest import bestiary
        from quest.art import hud as hud_art
        from quest.svg import hud
        frame_right = hud.HP_FRAME[0] + hud.HP_FRAME_W
        titles = [(k.title, s) for k in bestiary.KINDS.values() for s in ("foe", "elite")] + [(cards.BOSS_NAME, "boss")]
        for title, style in titles:
            for count in (1, 144, 99999):
                width = hud_art.nameplate(title, "SEP 30", count, 4, style).width
                x, y = hud.plate_position(width)
                if y == hud.PLATE_Y:
                    self.assertGreaterEqual(x, frame_right, (title, count))
                    self.assertLessEqual(x + width, hud.SOULS_PLATE[0], (title, count))
                self.assertGreaterEqual(x, 0)
                self.assertLessEqual(x + width, 415)

    def test_contribution_strip_lights_each_day_when_its_foe_falls(self):
        from quest.art import hud as hud_art
        from quest.svg import hud
        days = sorted([*self.roster.entries, self.roster.boss], key=lambda e: e.date)
        squares = re.findall(rf'<rect x="(\d+)" y="{hud.STRIP_Y}" width="{hud.SQUARE}"[^>]*><animate attributeName="fill" '
                             r'values="([^"]+)" keyTimes="([^"]+)"', self.svg)
        self.assertEqual(len(squares), len(days))
        deaths = {e.entry.date: e.death_t for e in self.script.encounters}
        deaths[self.roster.boss.date] = self.script.boss.death_t
        for (x, values, keys), entry in zip(squares, days):
            self.assertEqual(values.split(";"), [hud.EMPTY_DAY, hud_art.TIER_COLORS[entry.tier]])
            lit_at = float(keys.split(";")[1]) * self.script.duration
            self.assertAlmostEqual(lit_at, deaths[entry.date], delta=0.01)

    def test_boss_finale_is_drawn(self):
        for asset in ("crash-dust", "cut-plunge-gold", "wyrm"):
            self.assertInSvg(f'id="{asset}"')
        self.assertInSvg('fill="#fff4e0" opacity="0"><animate attributeName="opacity"')

    def test_bookend_set_pieces_are_drawn(self):
        for asset in ("wyrm-flyby", "game-title", "quest-panel", "quest-title"):
            self.assertInSvg(f'id="{asset}"')
        fires = self.svg.count('href="#bonfire"')
        self.assertEqual(fires, 2 + len(self.script.rests))

    def test_hud_waits_for_chapter_one(self):
        anim = hud.visibility(self.script)
        self.assertInSvg(f'<g opacity="0">{anim}<use href="#hud-hp-frame"')
        values = re.search(r'values="([^"]+)"', anim).group(1).split(";")
        keys = [float(k) for k in re.search(r'keyTimes="([^"]+)"', anim).group(1).split(";")]
        self.assertEqual(values, ["0", "0", "1", "1", "0"])
        self.assertAlmostEqual(keys[1] * self.script.duration, self.script.prologue.end, delta=0.01)
        self.assertAlmostEqual(keys[3] * self.script.duration, self.script.epilogue.fade_t, delta=0.01)
        self.assertEqual(keys[-1], 1.0)


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
            boss = script.boss
            for hit, blow in zip(boss.hits, boss.blows):
                dx = _move_at(script.knight_moves, hit)
                if blow == "plunge":
                    self.assertAlmostEqual(dx[0], wyrm.LEAP_REACH[0], places=6)
                    self.assertAlmostEqual(dx[1], wyrm.LEAP_REACH[1], places=6)
                else:
                    self.assertAlmostEqual(dx[0], wyrm.DASH, places=6)

    def test_knight_movement_never_teleports(self):
        for script in self.scripts + self.tiny:
            moves = script.knight_moves
            for (t0, x0, y0), (t1, x1, y1) in zip(moves, moves[1:]):
                if (x1, y1) != (x0, y0):
                    self.assertGreaterEqual(t1 - t0, 0.05 - 1e-9, (t0, t1))

    def test_knight_is_back_on_his_feet_before_raising_his_sword(self):
        for script in self.scripts + self.tiny:
            self.assertEqual(_move_at(script.knight_moves, script.epilogue.cheer_t), (0.0, 0.0))

    def test_date_labels_never_overlap(self):
        for script in self.scripts + self.tiny:
            windows = hud.date_windows(script)
            for (_, _, end), (_, start, _) in zip(windows, windows[1:]):
                self.assertLessEqual(end, start + 1e-9)

    def test_title_cards_never_overlap(self):
        for script in self.scripts + self.tiny:
            schedule = cards.card_schedule(script)
            keys = {card.key for card in schedule}
            self.assertTrue({"game-title", "victory", "quest-complete"} <= keys, keys)
            for a, b in zip(schedule, schedule[1:]):
                self.assertLessEqual(a.end, b.start + 1e-9, (a.key, b.key))
            self.assertLessEqual(schedule[-1].end, script.duration)

    def test_game_title_plays_over_the_vista(self):
        for script in self.scripts + self.tiny:
            title = next(card for card in cards.card_schedule(script) if card.key == "game-title")
            self.assertLessEqual(title.end, script.prologue.rise_t + 1e-9)


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
