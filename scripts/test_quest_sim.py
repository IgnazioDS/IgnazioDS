"""Offline tests for the quest roster and battle simulation.

Deterministic, no network. Run with::

    python3 -m unittest discover -s scripts -p 'test_quest*.py'
"""
import datetime
import unittest

from quest import layout, roster, sim

TODAY = datetime.date(2026, 9, 16)


def _calendar(counts, end=TODAY):
    """Daily counts ending on `end` (inclusive), oldest first."""
    start = end - datetime.timedelta(days=len(counts) - 1)
    return [
        {"date": (start + datetime.timedelta(days=i)).isoformat(), "count": c}
        for i, c in enumerate(counts)
    ]


# 60 days: bursts, quiet stretches (long enough for bonfires), a clear max day.
PATTERN = [3, 0, 0, 7, 1, 0, 12, 0, 0, 0, 0, 0, 0, 5, 2, 9, 0, 1, 46, 44,
           29, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 13, 16, 0, 2, 1, 7,
           0, 1, 0, 0, 22, 1, 0, 1, 14, 3, 0, 0, 0, 0, 0, 0, 0, 0, 11, 9]


def _x_at(path, t):
    for (t0, x0), (t1, x1) in zip(path, path[1:]):
        if t0 <= t <= t1:
            return x0 if t1 == t0 else x0 + (x1 - x0) * (t - t0) / (t1 - t0)
    return path[-1][1] if t > path[-1][0] else path[0][1]


class RosterSelection(unittest.TestCase):
    def setUp(self):
        self.days = _calendar(PATTERN)
        self.roster = roster.build(self.days, year_total=5434, today=TODAY, size=24)

    def test_excludes_today_partial_day(self):
        dates = [e.date for e in self.roster.entries] + [self.roster.boss.date]
        self.assertNotIn(TODAY.isoformat(), dates)

    def test_takes_most_recent_active_days(self):
        active = [d for d in self.days[:-1] if d["count"] > 0]
        expected = {d["date"] for d in active[-24:]}
        chosen = {e.date for e in self.roster.entries} | {self.roster.boss.date}
        self.assertEqual(chosen, expected)
        self.assertEqual(len(self.roster.entries), 23)

    def test_boss_is_the_biggest_day(self):
        self.assertEqual(self.roster.boss.count, 46)
        self.assertNotIn(self.roster.boss.date, [e.date for e in self.roster.entries])

    def test_entries_stay_chronological(self):
        dates = [e.date for e in self.roster.entries]
        self.assertEqual(dates, sorted(dates))

    def test_souls_total_is_exact_sum(self):
        active = [d["count"] for d in self.days[:-1] if d["count"] > 0][-24:]
        self.assertEqual(self.roster.souls_total, sum(active))

    def test_tiers_cover_range(self):
        tiers = {e.tier for e in self.roster.entries}
        self.assertTrue(tiers <= {1, 2, 3, 4})
        self.assertIn(1, tiers)
        self.assertIn(4, tiers)

    def test_gap_counts_quiet_days_between_entries(self):
        by_date = {e.date: e for e in self.roster.entries}
        # 22 on day 44, then counts 1 (day 45) — the next active day is day 45: gap 0.
        # Day 58 (11) follows day 49 (3) after 8 quiet days.
        start = TODAY - datetime.timedelta(days=len(PATTERN) - 1)
        day58 = (start + datetime.timedelta(days=58)).isoformat()
        self.assertEqual(by_date[day58].gap_before, 8)

    def test_quiet_gap_before_the_dragon_day_still_earns_a_rest(self):
        counts = [3, 4] + [0] * 12 + [40, 5, 2, 0]
        r = roster.build(_calendar(counts), year_total=54, today=TODAY, size=24)
        after_dragon = next(e for e in r.entries if e.count == 5)
        self.assertGreaterEqual(after_dragon.gap_before, 12)
        self.assertEqual(len(sim.simulate(r, "gap").rests), 1)

    def test_ties_pick_most_recent_as_boss(self):
        days = _calendar([5, 9, 0, 9, 1, 0])
        r = roster.build(days, year_total=24, today=TODAY, size=24)
        self.assertEqual(r.boss.date, days[3]["date"])

    def test_small_rosters_still_work(self):
        r = roster.build(_calendar([0, 4, 0]), year_total=4, today=TODAY, size=24)
        self.assertEqual(r.entries, ())
        self.assertEqual(r.boss.count, 4)

    def test_no_activity_fails_loudly(self):
        with self.assertRaisesRegex(ValueError, "no contributions"):
            roster.build(_calendar([0, 0, 0]), year_total=0, today=TODAY, size=24)


class QuestSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = roster.build(_calendar(PATTERN), year_total=5434, today=TODAY, size=24)
        cls.script = sim.simulate(cls.roster, "seed-a")

    def test_every_encounter_dies_once_in_order(self):
        deaths = [e.death_t for e in self.script.encounters]
        self.assertEqual(len(deaths), len(self.roster.entries))
        self.assertEqual(deaths, sorted(deaths))
        self.assertEqual(len(set(deaths)), len(deaths))

    def test_souls_end_at_real_total(self):
        values = [v for _, v in self.script.souls]
        self.assertEqual(values[0], 0)
        self.assertEqual(values[-1], self.roster.souls_total)
        self.assertEqual(values, sorted(values))

    def test_each_kill_banks_its_own_count(self):
        increments = [b - a for (_, a), (_, b) in zip(self.script.souls, self.script.souls[1:])]
        expected = [e.count for e in self.roster.entries] + [self.roster.boss.count]
        self.assertEqual(increments, expected)

    def test_everything_happens_inside_the_loop(self):
        d = self.script.duration
        self.assertLess(self.script.boss.death_t, d)
        self.assertLess(self.script.souls[-1][0], d)
        for enc in self.script.encounters:
            self.assertLess(enc.path[0][0], enc.engage_t)
            self.assertLessEqual(enc.engage_t, enc.hits[0])
            self.assertEqual(enc.hits[-1], enc.death_t)

    def test_monsters_arrive_exactly_at_engage_point(self):
        for enc in self.script.encounters:
            t_last, x_last = enc.path[-1]
            self.assertAlmostEqual(t_last, enc.engage_t)
            self.assertAlmostEqual(x_last, layout.engage_x(enc.entry.tier))
            self.assertGreaterEqual(enc.path[0][1], layout.SPAWN_X - 1e-6)

    def test_monsters_never_spawn_before_their_region_appears(self):
        for enc in self.script.encounters:
            spawn_t, spawn_x = enc.path[0]
            self.assertAlmostEqual(spawn_x, layout.SPAWN_X)
            self.assertGreaterEqual(spawn_t, self.script.chapters[enc.chapter].start - 1e-6)

    def test_monsters_never_spawn_during_a_bonfire_rest(self):
        for enc in self.script.encounters:
            for rest in self.script.rests:
                self.assertFalse(rest.path[0][0] < enc.path[0][0] < rest.sit_end + 0.25)

    def test_next_monster_sets_off_only_once_the_current_duel_starts(self):
        for a, b in zip(self.script.encounters, self.script.encounters[1:]):
            self.assertGreaterEqual(b.path[0][0], a.engage_t - 1e-6)

    def test_next_monster_waits_behind_the_current_one(self):
        for a, b in zip(self.script.encounters, self.script.encounters[1:]):
            if b.path[0][0] >= a.death_t:
                continue
            x_b = _x_at(b.path, a.death_t)
            self.assertGreaterEqual(x_b, layout.engage_x(a.entry.tier) + 24)

    def test_monster_paths_only_move_toward_the_knight(self):
        for enc in self.script.encounters:
            xs = [x for _, x in enc.path]
            self.assertEqual(xs, sorted(xs, reverse=True))

    def test_scroll_is_monotonic_and_frozen_during_fights(self):
        scroll = self.script.scroll
        self.assertEqual([t for t, _ in scroll], sorted(t for t, _ in scroll))
        self.assertEqual([s for _, s in scroll], sorted(s for _, s in scroll))
        for enc in self.script.encounters:
            self.assertAlmostEqual(sim.scroll_at(scroll, enc.engage_t), sim.scroll_at(scroll, enc.death_t))

    def test_phases_tile_the_timeline(self):
        phases = self.script.phases
        self.assertAlmostEqual(phases[0].start, 0.0)
        for a, b in zip(phases, phases[1:]):
            self.assertAlmostEqual(a.end, b.start)
        self.assertAlmostEqual(phases[-1].end, self.script.duration)

    def test_knight_frames_are_known_and_ordered(self):
        times = [t for t, _ in self.script.knight_frames]
        self.assertEqual(times, sorted(times))
        self.assertTrue({name for _, name in self.script.knight_frames} <= set(layout.KNIGHT_FRAMES))

    def test_four_chapters_end_in_the_keep(self):
        regions = [c.region for c in self.script.chapters]
        self.assertEqual(len(regions), 4)
        self.assertEqual(regions[-1], "keep")
        self.assertEqual(sorted(regions[:3]), ["crimson", "violet", "wood"])

    def test_long_quiet_gaps_become_bonfire_rests(self):
        self.assertGreaterEqual(len(self.script.rests), 1)
        for rest in self.script.rests:
            self.assertLess(rest.sit_start, rest.sit_end)

    def test_health_never_empties(self):
        self.assertTrue(all(0.0 < hp <= 1.0 for _, hp in self.script.health))

    def test_deterministic_for_same_seed(self):
        self.assertEqual(sim.simulate(self.roster, "seed-a"), self.script)

    def test_different_seed_changes_the_quest(self):
        other = sim.simulate(self.roster, "seed-b")
        self.assertNotEqual(other.knight_frames, self.script.knight_frames)

    def test_boss_only_roster(self):
        tiny = roster.build(_calendar([0, 4, 0]), year_total=4, today=TODAY, size=24)
        script = sim.simulate(tiny, "seed")
        self.assertEqual(script.encounters, ())
        self.assertEqual(script.souls[-1][1], 4)


if __name__ == "__main__":
    unittest.main()
