"""Offline tests for the quest roster and battle simulation.

Deterministic, no network. Run with::

    python3 -m unittest discover -s scripts -p 'test_quest*.py'
"""
import datetime
import unittest

from quest import bestiary, combat, layout, roster, sim, wyrm

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
            self.assertAlmostEqual(x_last, bestiary.KINDS[enc.kind].engage_x)
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
            self.assertGreaterEqual(x_b, bestiary.KINDS[a.kind].engage_x + 24)

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


class Bestiary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = roster.build(_calendar(PATTERN), year_total=5434, today=TODAY, size=24)
        cls.script = sim.simulate(cls.roster, "bestiary")

    def test_each_day_takes_its_regions_shape_for_its_tier(self):
        for enc in self.script.encounters:
            region = self.script.chapters[enc.chapter].region
            self.assertEqual(enc.kind, bestiary.kind_for(region, enc.entry.tier).key)

    def test_every_region_fields_its_own_line_up(self):
        seen = {}
        for enc in self.script.encounters:
            seen.setdefault(self.script.chapters[enc.chapter].region, set()).add(enc.kind)
        for region, kinds in seen.items():
            self.assertTrue(kinds <= set(bestiary.LINEUPS[region]), region)

    def test_each_long_chapter_crowns_its_busiest_day(self):
        for chapter in range(len(self.script.chapters)):
            fights = [e for e in self.script.encounters if e.chapter == chapter]
            elites = [e for e in fights if e.elite]
            self.assertLessEqual(len(elites), 1)
            if len(fights) >= bestiary.ELITE_MIN_FOES and elites:
                self.assertEqual(elites[0].entry.count, max(e.entry.count for e in fights))

    def test_elites_strike_back_and_take_longer_to_fell(self):
        elites = [e for e in self.script.encounters if e.elite]
        self.assertTrue(elites)
        for enc in elites:
            self.assertEqual(len(enc.attacks), 2)
            self.assertEqual(len(enc.hits), sim.HITS_BY_TIER[enc.entry.tier] + sim.ELITE_EXTRA_HITS)

    def test_small_or_quiet_chapters_have_no_champion(self):
        low = [roster.Entry("2026-01-0%d" % i, 1, 1, 0) for i in range(1, 5)]
        self.assertIsNone(bestiary.elite_index(low))
        self.assertIsNone(bestiary.elite_index(low[:2]))

    def test_remains_stay_then_drift_away_with_the_ground(self):
        for enc in self.script.encounters:
            remains = enc.remains
            self.assertEqual(remains[0], (enc.death_t, float(bestiary.KINDS[enc.kind].engage_x)))
            times = [t for t, _ in remains]
            xs = [x for _, x in remains]
            self.assertEqual(times, sorted(times))
            self.assertEqual(xs, sorted(xs, reverse=True))
            self.assertLessEqual(times[-1], min(enc.death_t + sim.REMAINS_TIME, self.script.chapters[enc.chapter].end) + 1e-6)
            self.assertGreater(times[-1], enc.death_t)

    def test_unknown_region_or_tier_fails_loudly(self):
        with self.assertRaises(ValueError):
            bestiary.kind_for("atlantis", 2)
        with self.assertRaises(ValueError):
            bestiary.kind_for("wood", 5)


class Duels(unittest.TestCase):
    """Combat choreography swept over several daily seeds."""

    @classmethod
    def setUpClass(cls):
        r = roster.build(_calendar(PATTERN), year_total=5434, today=TODAY, size=24)
        cls.scripts = [sim.simulate(r, f"duel-{k}") for k in range(8)]

    def encounters(self):
        return [enc for script in self.scripts for enc in script.encounters]

    def test_every_hit_names_its_blow(self):
        for enc in self.encounters():
            self.assertEqual(len(enc.blows), len(enc.hits))
            self.assertTrue(set(enc.blows) <= set(combat.BLOWS))

    def test_combos_run_slash_rise_thrust(self):
        for enc in self.encounters():
            chain = [b for b in enc.blows if b != "riposte"]
            self.assertEqual(chain, [combat.COMBO[i % 3] for i in range(len(chain))])

    def test_a_parry_is_answered_by_a_riposte(self):
        seen = 0
        for enc in self.encounters():
            for attack in enc.attacks:
                if attack.outcome != "parry":
                    continue
                answer = next(i for i, hit in enumerate(enc.hits) if hit > attack.t)
                self.assertEqual(enc.blows[answer], "riposte")
                seen += 1
        self.assertGreater(seen, 0)

    def test_only_tough_or_elite_foes_strike_back(self):
        for enc in self.encounters():
            if enc.entry.tier < 3 and not enc.elite:
                self.assertEqual(enc.attacks, ())
            else:
                self.assertGreaterEqual(len(enc.attacks), 1)
                self.assertLessEqual(enc.attacks[0].t, enc.hits[0])
            outcomes = {a.outcome for a in enc.attacks}
            self.assertTrue(outcomes <= {"hurt", "parry", "dodge"})

    def test_every_outcome_happens_somewhere(self):
        outcomes = {a.outcome for enc in self.encounters() for a in enc.attacks}
        self.assertEqual(outcomes, {"hurt", "parry", "dodge"})

    def test_knight_always_returns_to_his_mark(self):
        for script in self.scripts:
            moves = script.knight_moves
            self.assertEqual([t for t, _, _ in moves], sorted(t for t, _, _ in moves))
            self.assertEqual(moves[-1][1:], (0.0, 0.0))
            duels = [(dx, dy) for t, dx, dy in moves if t < script.boss.enter_t]
            self.assertTrue(all(-combat.DODGE_BACK <= dx <= 0.0 and dy == 0.0 for dx, dy in duels))

    def test_each_answer_to_an_attack_plays_its_frames(self):
        expected = {"dodge": "roll1", "hurt": "hurt1", "parry": "parry1"}
        for script in self.scripts:
            for enc in script.encounters:
                for attack in enc.attacks:
                    names = [name for t, name in script.knight_frames if attack.t <= t < attack.t + 0.5]
                    self.assertIn(expected[attack.outcome], names)

    def test_dodges_and_wounds_move_the_knight_off_his_mark_and_parries_do_not(self):
        reach = {"dodge": -combat.DODGE_BACK, "hurt": -combat.KNOCKBACK, "parry": 0.0}
        for script in self.scripts:
            for enc in script.encounters:
                for attack, following in zip(enc.attacks, (*enc.attacks[1:], None)):
                    end = min(attack.t + 1.0, following.t if following else attack.t + 1.0)
                    window = [dx for t, dx, _ in script.knight_moves if attack.t <= t < end]
                    furthest = min(window, default=0.0)
                    self.assertAlmostEqual(furthest, reach[attack.outcome], msg=(enc.index, attack))

    def test_every_heavy_blow_shakes_and_ripostes_are_heavy(self):
        for script in self.scripts:
            shaken = {round(t, 6) for t, _ in script.shakes}
            for enc in script.encounters:
                self.assertEqual(len(enc.heavy), len(enc.hits))
                for hit, blow, heavy in zip(enc.hits, enc.blows, enc.heavy):
                    if blow == "riposte":
                        self.assertTrue(heavy)
                    self.assertEqual(round(hit, 6) in shaken, heavy)

    def test_killing_blows_on_tough_foes_shake_the_screen(self):
        for script in self.scripts:
            shaken = {round(t, 6) for t, _ in script.shakes}
            for enc in script.encounters:
                if enc.entry.tier >= 3 or enc.elite:
                    self.assertIn(round(enc.death_t, 6), shaken)


class WyrmFight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        r = roster.build(_calendar(PATTERN), year_total=5434, today=TODAY, size=24)
        cls.scripts = [sim.simulate(r, f"wyrm-{k}") for k in range(10)]

    def test_the_plunge_is_the_killing_blow(self):
        for script in self.scripts:
            boss = script.boss
            self.assertEqual(len(boss.blows), len(boss.hits))
            self.assertEqual(boss.blows[-1], "plunge")
            self.assertEqual(boss.hits[-1], boss.death_t)
            self.assertNotIn("plunge", boss.blows[:-1])

    def test_the_wyrm_takes_to_the_air_once_between_rounds(self):
        for script in self.scripts:
            boss = script.boss
            self.assertEqual(len(boss.flights), 1)
            flight = boss.flights[0]
            self.assertLess(boss.land_t, flight.takeoff)
            self.assertLess(flight.takeoff, flight.dive)
            self.assertLess(flight.dive, flight.pass_t)
            self.assertLess(flight.pass_t, flight.back)
            self.assertLess(flight.back, flight.land)
            self.assertLess(flight.land, boss.death_t)
            self.assertIn(flight.outcome, ("dodge", "hurt"))
            self.assertTrue(any(h < flight.takeoff for h in boss.hits))
            self.assertTrue(any(h > flight.land for h in boss.hits[:-1]))

    def test_no_fire_or_blade_while_the_wyrm_is_away(self):
        for script in self.scripts:
            boss = script.boss
            for flight in boss.flights:
                for start, end in boss.breaths:
                    self.assertTrue(end <= flight.takeoff or start >= flight.land)
                for hit in boss.hits:
                    self.assertFalse(flight.takeoff < hit < flight.land)

    def test_the_swoop_is_dodged_or_endured(self):
        outcomes = {script.boss.flights[0].outcome for script in self.scripts}
        self.assertIn("dodge", outcomes)
        for script in self.scripts:
            flight = script.boss.flights[0]
            names = [n for t, n in script.knight_frames if flight.pass_t - 0.4 <= t <= flight.pass_t + 0.2]
            self.assertIn("roll1" if flight.outcome == "dodge" else "hurt1", names)

    def test_crushing_moments_shake_the_screen(self):
        for script in self.scripts:
            boss = script.boss
            moments = {round(t, 6) for t, _ in script.shakes}
            for t in (boss.land_t, boss.flights[0].land, boss.death_t, boss.death_t + wyrm.CRASH_DELAY):
                self.assertIn(round(t, 6), moments)


class StoryBookends(unittest.TestCase):
    """The prologue vista opens the loop; the epilogue camp closes it."""

    @classmethod
    def setUpClass(cls):
        cls.roster = roster.build(_calendar(PATTERN), year_total=5434, today=TODAY, size=24)
        cls.script = sim.simulate(cls.roster, "bookends")

    def test_prologue_plays_in_order_before_chapter_one(self):
        pro = self.script.prologue
        self.assertEqual(self.script.phases[0].kind, "prologue")
        self.assertLess(pro.title_t, pro.rise_t)
        self.assertLess(pro.flyby[0], pro.flyby[1])
        self.assertLessEqual(pro.flyby[1], pro.rise_t)
        self.assertLess(pro.rise_t, pro.depart_t)
        self.assertLess(pro.depart_t, pro.end)
        self.assertAlmostEqual(pro.end, self.script.chapters[0].start)

    def test_knight_sits_by_the_fire_until_he_rises(self):
        pro = self.script.prologue
        seated = {name for t, name in self.script.knight_frames if t < pro.rise_t}
        self.assertEqual(seated, {"sit0", "sit1"})
        self.assertEqual(sim.scroll_at(self.script.scroll, pro.depart_t), 0.0)

    def test_prologue_fire_is_left_behind_inside_the_vista(self):
        pro = self.script.prologue
        self.assertEqual(pro.camp[0], (0.0, float(layout.BONFIRE_X)))
        xs = [x for _, x in pro.camp]
        self.assertEqual(xs, sorted(xs, reverse=True))
        self.assertLess(xs[-1], layout.BONFIRE_X)
        self.assertLessEqual(pro.camp[-1][0], pro.end + 1e-9)

    def test_no_monster_appears_before_chapter_one(self):
        first = self.script.chapters[0].start
        for enc in self.script.encounters:
            self.assertGreaterEqual(enc.path[0][0], first - 1e-6)

    def test_epilogue_follows_the_wyrm_in_order(self):
        boss, epi = self.script.boss, self.script.epilogue
        self.assertLess(boss.death_t, epi.cheer_t)
        self.assertLess(epi.cheer_t, epi.camp_t)
        self.assertLess(epi.camp_t, epi.stats_t)
        self.assertLess(epi.stats_t, self.script.duration)
        self.assertEqual(self.script.phases[-1].kind, "epilogue")
        window = (epi.cheer_t, epi.cheer_t + wyrm.CHEER_TIME)
        cheering = {name for t, name in self.script.knight_frames if window[0] <= t < window[1]}
        self.assertEqual(cheering, {"cheer0", "cheer1"})

    def test_epilogue_fire_burns_to_the_end_of_the_loop(self):
        camp = self.script.epilogue.camp
        self.assertEqual(camp[0], (self.script.epilogue.camp_t, float(layout.BONFIRE_X)))
        self.assertAlmostEqual(camp[-1][0], self.script.duration)

    def test_last_fire_mends_the_knight(self):
        mended = [hp for t, hp in self.script.health if t >= self.script.epilogue.camp_t + 1.4]
        self.assertTrue(mended)
        self.assertTrue(all(hp == 1.0 for hp in mended))

    def test_final_fade_starts_when_the_epilogue_says(self):
        fades = self.script.fades
        self.assertEqual(fades[-2], (self.script.epilogue.fade_t, 0.0))
        self.assertLess(self.script.epilogue.stats_t, self.script.epilogue.fade_t)

    def test_loop_opens_and_closes_in_black(self):
        fades = self.script.fades
        self.assertEqual(fades[0], (0.0, 1.0))
        self.assertAlmostEqual(fades[-1][0], self.script.duration)
        self.assertEqual(fades[-1][1], 1.0)


if __name__ == "__main__":
    unittest.main()
