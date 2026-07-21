"""Offline unit tests for the Space Invaders SVG generator.

Deterministic, no network. Run with::

    python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import re
import unittest
import xml.dom.minidom

from invaders import render, sim, sprites

DAY_COUNTS = [(i * 7) % 23 for i in range(55)]  # mixed zero/non-zero pattern
SEED = "test-seed"


def _script():
    return sim.simulate(DAY_COUNTS, SEED)


class SimulationInvariants(unittest.TestCase):
    def setUp(self):
        self.script = _script()

    def test_every_invader_dies_exactly_once(self):
        killed = sorted(k.invader for k in self.script.kills)
        self.assertEqual(killed, list(range(55)))

    def test_kill_times_strictly_increase_and_fit_duration(self):
        times = [k.t for k in self.script.kills]
        self.assertEqual(times, sorted(times))
        self.assertEqual(len(times), len(set(times)))
        self.assertLess(times[-1], self.script.duration)

    def test_score_totals_contributions_plus_ufo(self):
        expected = sum(DAY_COUNTS) + sim.UFO_POINTS
        self.assertEqual(self.script.score_states[-1][1], expected)

    def test_march_stays_inside_bounds(self):
        for _, ox, oy in self.script.march:
            self.assertLessEqual(abs(ox), sim.MARCH_BOUND)
            self.assertLessEqual(oy, sim.MAX_DESCEND)

    def test_cannon_path_times_monotonic(self):
        times = [t for t, _ in self.script.cannon_path]
        self.assertEqual(times, sorted(times))

    def test_shots_land_before_duration(self):
        for shot in self.script.shots:
            self.assertLess(shot.t_fire, shot.t_impact)
            self.assertLess(shot.t_impact, self.script.duration)

    def test_set_pieces_scheduled(self):
        self.assertIn("t_die", self.script.ufo)
        self.assertIn("t_respawn", self.script.cannon_death)

    def test_deterministic_for_same_seed(self):
        self.assertEqual(_script(), sim.simulate(DAY_COUNTS, SEED))

    def test_different_seed_changes_game(self):
        other = sim.simulate(DAY_COUNTS, "other-seed")
        self.assertNotEqual(self.script.shots, other.shots)

    def test_rejects_wrong_day_count(self):
        with self.assertRaises(ValueError):
            sim.simulate([1, 2, 3], SEED)


class RenderOutput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.svg = render.render(_script(), DAY_COUNTS, hi_score=1234, wave_label="042")

    def test_is_well_formed_xml(self):
        xml.dom.minidom.parseString(self.svg)

    def test_no_script_tags(self):
        self.assertNotIn("<script", self.svg)

    def test_all_keytimes_within_unit_interval(self):
        for match in re.finditer(r'keyTimes="([^"]+)"', self.svg):
            values = [float(v) for v in match.group(1).split(";")]
            self.assertEqual(values, sorted(values))
            self.assertGreaterEqual(values[0], 0.0)
            self.assertLessEqual(values[-1], 1.0)

    def test_keytimes_match_values_count(self):
        for match in re.finditer(
            r'values="([^"]+)" keyTimes="([^"]+)"', self.svg
        ):
            self.assertEqual(
                len(match.group(1).split(";")), len(match.group(2).split(";"))
            )

    def test_every_timeline_shares_one_duration(self):
        durations = set(re.findall(r'dur="([^"]+)"', self.svg))
        self.assertEqual(len(durations), 1)

    def test_hud_contains_hi_score_and_wave(self):
        self.assertIn('aria-label', self.svg)
        self.assertIn("indefinite", self.svg)


class SpriteHelpers(unittest.TestCase):
    def test_run_length_merge_covers_bitmap(self):
        runs = sprites.sprite_runs(sprites.SHIELD)
        painted = sum(w for _, _, w in runs)
        expected = sum(row.count("X") for row in sprites.SHIELD)
        self.assertEqual(painted, expected)

    def test_font_has_all_needed_glyphs(self):
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-=+ ":
            self.assertIn(ch, sprites.FONT_3X5)

    def test_text_width_matches_advance(self):
        self.assertEqual(sprites.text_width("WAVE", 2), 4 * 4 * 2)


if __name__ == "__main__":
    unittest.main()
