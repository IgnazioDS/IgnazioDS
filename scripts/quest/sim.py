"""Deterministic quest simulation: Roster + seed -> QuestScript.

The knight's timeline is authored forward (walk, fight, rest, transition,
boss). Monster approach paths are solved backward from the instant each one
must stand at its engage point, through the world scroll already recorded,
so enemies always arrive exactly on cue whatever happened before.
Same roster + same seed => identical script.
"""

import dataclasses
import math
import random

from . import bestiary, layout
from .combat import Combat
from .script import Chapter, Encounter, Epilogue, Phase, Prologue, QuestScript, Rest
from .wyrm import WyrmFight

WALK_SPEED = 74.0
WALK_FPS, IDLE_FPS, REST_FPS = 12.0, 4.0, 2.0
HITS_BY_TIER = {1: 1, 2: 2, 3: 2, 4: 3}
ELITE_EXTRA_HITS = 1
REMAINS_TIME, REMAINS_EXIT_X = 3.2, -110.0   # how long bodies linger; where they leave the screen
CAMP_EXIT_X = -40.0                          # a bonfire is gone once it scrolls past here
REST_GAP, MAX_RESTS, SIT_TIME = 5, 2, 1.7
WISP_FLIGHT = 0.8
FADE, INTRO_FADE, OUTRO_FADE = 0.45, 1.0, 0.9
MIN_HEALTH = 0.2
# prologue: seated by the fire while the title plays and the wyrm flies over
PROLOGUE_SIT, PROLOGUE_TITLE, FLYBY = 4.6, 1.0, (0.5, 4.2)
RISE, RISE_TIME = (("kneel1", 0.0), ("kneel0", 0.22), ("idle0", 0.44)), 0.6
# epilogue: the fire takes, then the quest's tally
STATS_DELAY, STATS_TIME = 0.35, 4.6
REGIONS = ("violet", "wood", "crimson")


def simulate(roster, seed):
    return _Builder(roster, seed).run()


def scroll_at(scroll, t):
    """World scroll at time t from piecewise-linear keyframes."""
    if t <= scroll[0][0]:
        return scroll[0][1]
    for (t0, s0), (t1, s1) in zip(scroll, scroll[1:]):
        if t0 <= t <= t1:
            return s0 if t1 - t0 < 1e-12 else s0 + (s1 - s0) * (t - t0) / (t1 - t0)
    return scroll[-1][1]


def solve_approach(scroll, engage_t, engage_x, speed):
    """Monster path solved backward from its engage point to the spawn edge.

    While the knight walks, the world scrolls left, so a monster's screen
    velocity is its own speed plus the scroll speed; while he fights, only its
    own. Walking keyframes backward accumulates distance until SPAWN_X.
    """
    keys = [k for k in scroll if k[0] <= engage_t + 1e-9]
    if keys[-1][0] < engage_t - 1e-9:
        keys.append((engage_t, keys[-1][1]))
    points, x = [(engage_t, float(engage_x))], float(engage_x)
    for (t0, s0), (t1, s1) in reversed(list(zip(keys, keys[1:]))):
        if t1 - t0 < 1e-9:
            continue
        velocity = (s1 - s0) / (t1 - t0) + speed
        reach = x + velocity * (t1 - t0)
        if reach >= layout.SPAWN_X:
            points.append((t1 - (layout.SPAWN_X - x) / velocity, float(layout.SPAWN_X)))
            return tuple(reversed(points))
        x = reach
        points.append((t0, x))
    return tuple(reversed(points))


def chapter_sizes(count, chapters=4):
    base, extra = divmod(count, chapters)
    return [base + (1 if i < extra else 0) for i in range(chapters)]


class _Builder(WyrmFight, Combat):
    """Mutable working state for one quest; emits immutable records."""

    min_health = MIN_HEALTH

    def __init__(self, roster, seed):
        self.rng = random.Random(seed)
        self.roster = roster
        self.t = 0.0
        self.world = 0.0
        self.scroll = [(0.0, 0.0)]
        self.frames = []
        self.phases = []
        self.walk_clock = 0.0
        self.chapters, self.encounters, self.rest_marks = [], [], []
        self.souls, self.banked = [(0.0, 0)], 0
        self.hp, self.health = 1.0, [(0.0, 1.0)]
        self.fades = [(0.0, 1.0), (INTRO_FADE, 0.0)]
        self.moves = [(0.0, 0.0, 0.0)]
        self.shakes = []
        self.barrier = 0.0

    # -- timeline primitives ---------------------------------------------------
    def _frame(self, t, name):
        if self.frames and abs(self.frames[-1][0] - t) < 1e-9:
            self.frames[-1] = (t, name)
        elif not self.frames or self.frames[-1][1] != name:
            self.frames.append((t, name))

    def walk(self, duration, kind="walk"):
        start, end = self.t, self.t + duration
        t, clock = start, self.walk_clock
        while t < end - 1e-9:
            step = int(clock * WALK_FPS + 1e-6)
            self._frame(t, f"walk{step % layout.WALK_FRAMES}")
            dt = (step + 1) / WALK_FPS - clock
            t, clock = t + dt, clock + dt
        self.walk_clock += duration
        if self.scroll[-1][0] < start - 1e-9:
            self.scroll.append((start, self.world))
        self.world += WALK_SPEED * duration
        self.scroll.append((end, self.world))
        self.phases.append(Phase(kind, start, end))
        self.t = end

    def _cycle(self, names, fps, duration):
        """Alternate `names` at `fps` for `duration` seconds from now."""
        start = self.t
        for k in range(max(1, math.ceil(duration * fps - 1e-9))):
            self._frame(start + k / fps, names[k % len(names)])
        self.t = start + duration

    def hold(self, duration):
        """Stand still (idle breathing); records no phase of its own."""
        end, t, i = self.t + duration, self.t, 0
        while t < end - 1e-9:
            self._frame(t, f"idle{i % layout.IDLE_FRAMES}")
            t, i = t + 1 / IDLE_FPS, i + 1
        self.t = end

    def bank(self, t, count):
        self.banked += count
        self.souls.append((t, self.banked))

    def _planned_scroll(self, walk):
        """Scroll keyframes as they would be after walking `walk` more seconds."""
        keys = list(self.scroll)
        if keys[-1][0] < self.t - 1e-9:
            keys.append((self.t, self.world))
        keys.append((self.t + walk, self.world + WALK_SPEED * walk))
        return keys

    def _walk_until_clear_spawn(self, base_walk, engage_x, speed):
        """Lengthen the approach walk until the monster spawns after the barrier.

        The barrier is the last region switch or bonfire rest: nothing may
        wander on screen before it.
        """
        walk = base_walk
        for _ in range(16):
            path = solve_approach(self._planned_scroll(walk), self.t + walk, engage_x, speed)
            spawned = path[0][1] >= layout.SPAWN_X - 1e-6
            spawn_t = path[0][0] if spawned else float("-inf")
            if spawn_t >= self.barrier - 1e-9:
                return walk
            deficit = self.barrier - spawn_t if spawned else 1.0
            walk += max(0.05, deficit)
        return walk

    # -- set pieces ------------------------------------------------------------
    def encounter(self, index, entry, chapter, region, elite=False):
        tier = entry.tier
        kind = bestiary.kind_for(region, tier)
        speed, engage_x = kind.speed, kind.engage_x
        base = 0.45 + 0.08 * min(entry.gap_before, 5) + self.rng.uniform(0.0, 0.25)
        self.walk(self._walk_until_clear_spawn(base, engage_x, speed))
        engage_t = self.t
        path = solve_approach(self.scroll, engage_t, engage_x, speed)
        self.barrier = max(self.barrier, engage_t)  # the next foe waits for this duel
        self.hold(0.1)
        strikes = HITS_BY_TIER[tier] + (ELITE_EXTRA_HITS if elite else 0)
        if strikes > 1 and not elite and self.rng.random() < 0.25:
            strikes -= 1  # a critical blow ends it early
        attacks, hits, blows, heavy = self.duel(tier, elite, strikes)
        self.bank(hits[-1] + WISP_FLIGHT, entry.count)
        self.phases.append(Phase("fight", engage_t, self.t))
        self.encounters.append(
            Encounter(index, entry, chapter, kind.key, elite, path, engage_t, attacks, hits, blows, heavy, hits[-1])
        )

    def rest(self, chapter):
        spawn_t = self.t
        self.walk((layout.SPAWN_X - layout.BONFIRE_X) / WALK_SPEED)
        sit_start = self.t
        for k in range(int(SIT_TIME * REST_FPS)):
            self._frame(sit_start + k / REST_FPS, f"sit{k % 2}")
        self.health += [(sit_start + 0.3, self.hp), (sit_start + SIT_TIME * 0.8, 1.0)]
        self.hp = 1.0
        self.t += SIT_TIME
        sit_end = self.t
        self.hold(0.25)
        self.phases.append(Phase("rest", sit_start, self.t))
        self.rest_marks.append((spawn_t, sit_start, sit_end, chapter))
        self.barrier = self.t

    def transition(self, region):
        self.walk(0.6)
        self.fades += [(self.t, 0.0), (self.t + FADE, 1.0)]
        self.walk(FADE, kind="transition")
        switch = self.t
        self.walk(0.2, kind="transition")
        self.fades += [(self.t, 1.0), (self.t + FADE, 0.0)]
        self.chapters.append({"region": region, "start": switch, "title_t": self.t})
        self.barrier = switch
        self.walk(FADE, kind="transition")

    def prologue(self):
        """Seated by the fire while the title plays and the wyrm flies over, then up."""
        self._cycle(("sit0", "sit1"), REST_FPS, PROLOGUE_SIT)
        rise_t = self.t
        for name, delay in RISE:
            self._frame(rise_t + delay, name)
        self.t = rise_t + RISE_TIME
        self.phases.append(Phase("prologue", 0.0, self.t))
        return rise_t, self.t

    def epilogue(self):
        """The fire takes; he sits while the quest's tally plays, then the loop fades out."""
        camp_t = self.t
        self.health += [(camp_t + 0.3, self.hp), (camp_t + 1.4, 1.0)]  # every bonfire mends
        self.hp = 1.0
        stats_t = camp_t + STATS_DELAY
        end = stats_t + STATS_TIME
        self._cycle(("sit0", "sit1"), REST_FPS, end + OUTRO_FADE - camp_t)
        self.fades += [(end, 0.0), (end + OUTRO_FADE, 1.0)]
        self.phases.append(Phase("epilogue", camp_t, self.t))
        return camp_t, stats_t, end

    # -- orchestration -----------------------------------------------------------
    def _rest_before(self):
        gaps = sorted(
            ((e.gap_before, -i) for i, e in enumerate(self.roster.entries) if e.gap_before >= REST_GAP),
            reverse=True,
        )
        return {-neg_i for _, neg_i in gaps[:MAX_RESTS]}

    def run(self):
        order = list(REGIONS)
        self.rng.shuffle(order)
        sizes = chapter_sizes(len(self.roster.entries))
        plan = [(order[i], sizes[i]) for i in range(3) if sizes[i]] + [("keep", sizes[3])]
        rest_before = self._rest_before()
        prologue_marks = self.prologue()
        index = 0
        for chapter, (region, size) in enumerate(plan):
            self.transition(region)
            champion = bestiary.elite_index(self.roster.entries[index:index + size])
            for k in range(size):
                if index in rest_before:
                    self.rest(chapter)
                self.encounter(index, self.roster.entries[index], chapter, region, elite=k == champion)
                index += 1
        boss, cheer_t = self.boss_fight()
        epilogue_marks = (cheer_t, *self.epilogue())
        return self._freeze(boss, prologue_marks, epilogue_marks)

    def _freeze(self, boss, prologue_marks, epilogue_marks):
        duration = self.t
        self.scroll.append((duration, self.world))
        self.health.append((duration, self.hp))
        chapters = tuple(
            Chapter(c["region"], c["start"],
                    self.chapters[i + 1]["start"] if i + 1 < len(self.chapters) else duration,
                    c["title_t"])
            for i, c in enumerate(self.chapters)
        )
        rests = tuple(self._rest_record(mark, chapters) for mark in self.rest_marks)
        encounters = tuple(self._with_remains(enc, chapters) for enc in self.encounters)
        fire = float(layout.BONFIRE_X)
        rise_t, depart_t = prologue_marks
        prologue = Prologue(PROLOGUE_TITLE, FLYBY, rise_t, depart_t, chapters[0].start,
                            self._camp_path(((0.0, fire), (depart_t, fire)), depart_t, chapters[0].start))
        cheer_t, camp_t, stats_t, fade_t = epilogue_marks
        epilogue = Epilogue(cheer_t, camp_t, stats_t, fade_t, ((camp_t, fire), (duration, fire)))
        return QuestScript(
            duration=duration,
            scroll=tuple(self.scroll),
            knight_frames=tuple(self.frames),
            phases=tuple(self.phases),
            chapters=chapters,
            encounters=encounters,
            rests=rests,
            boss=boss,
            souls=tuple(self.souls),
            health=tuple(self.health),
            fades=tuple(self.fades),
            knight_moves=tuple(self.moves),
            shakes=tuple(self.shakes),
            prologue=prologue,
            epilogue=epilogue,
        )

    def _rest_record(self, mark, chapters):
        spawn_t, sit_start, sit_end, chapter = mark
        head = ((spawn_t, float(layout.SPAWN_X)), (sit_start, float(layout.BONFIRE_X)))
        return Rest(self._camp_path(head, sit_end, chapters[chapter].end), sit_start, sit_end, chapter)

    def _with_remains(self, enc, chapters):
        """The body stays where it fell and scrolls away once the knight walks on."""
        head = ((enc.death_t, float(bestiary.KINDS[enc.kind].engage_x)),)
        until = min(enc.death_t + REMAINS_TIME, chapters[enc.chapter].end)
        return dataclasses.replace(enc, remains=self._carried(head, enc.death_t, until, REMAINS_EXIT_X))

    def _camp_path(self, head, leave_t, until):
        """A bonfire's screen path: the `head` keyframes, then carried off by the scroll."""
        return self._carried(head, leave_t, until, CAMP_EXIT_X)

    def _carried(self, head, leave_t, until, exit_x):
        """Screen path of something left on the ground: `head` keyframes, then carried off by the scroll.

        It rests at the last head keyframe's x until the knight walks on after
        `leave_t`, and the path ends where it leaves the screen (`exit_x`) or at `until`.
        """
        path = list(head)
        rest_x, anchor = path[-1][1], scroll_at(self.scroll, leave_t)
        for t, s in self.scroll:
            if t <= leave_t:
                continue
            final = t >= until
            if final:
                t, s = until, scroll_at(self.scroll, until)
            x = rest_x - (s - anchor)
            if x < exit_x:
                prev_t, prev_x = path[-1]
                path.append((prev_t + (t - prev_t) * (prev_x - exit_x) / (prev_x - x), exit_x))
                return tuple(path)
            path.append((t, x))
            if final:
                break
        if path[-1][0] < until:
            path.append((until, path[-1][1]))
        return tuple(path)
