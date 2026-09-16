"""Deterministic quest simulation: Roster + seed -> QuestScript.

The knight's timeline is authored forward (walk, fight, rest, transition,
boss). Monster approach paths are solved backward from the instant each one
must stand at its engage point, through the world scroll already recorded,
so enemies always arrive exactly on cue whatever happened before.
Same roster + same seed => identical script.
"""

import random

from . import layout
from .script import BossFight, Chapter, Encounter, Phase, QuestScript, Rest

WALK_SPEED = 74.0
MONSTER_SPEED = {1: 95.0, 2: 58.0, 3: 50.0, 4: 66.0}  # charging, px/s over the ground
WALK_FPS, IDLE_FPS, REST_FPS = 12.0, 4.0, 2.0
# anticipation, peak, smear (the hit lands here), impact, follow-through, recover
STRIKE_TIMING = (0.08, 0.1, 0.06, 0.08, 0.08, 0.08)
HIT_FRAME = 2
HITS_BY_TIER = {1: 1, 2: 2, 3: 2, 4: 3}
REST_GAP, MAX_RESTS, SIT_TIME = 5, 2, 1.7
WISP_FLIGHT, BOSS_WISP_FLIGHT = 0.8, 1.3
FADE, INTRO_FADE, OUTRO_FADE = 0.45, 0.8, 0.9
MIN_HEALTH = 0.2
GAME_TITLE_HOLD = 2.6  # chapter I's card waits for the opening title card
REGIONS = ("violet", "wood", "crimson")
BOSS_PATTERNS = (
    ("breath", "strike", "strike", "breath", "strike", "strike"),
    ("strike", "breath", "strike", "strike", "breath", "strike"),
    ("breath", "strike", "breath", "strike", "strike", "strike"),
)


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


class _Builder:
    """Mutable working state for one quest; emits immutable records."""

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
        self.parries = []
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

    def hold(self, duration):
        """Stand still (idle breathing); records no phase of its own."""
        end, t, i = self.t + duration, self.t, 0
        while t < end - 1e-9:
            self._frame(t, f"idle{i % layout.IDLE_FRAMES}")
            t, i = t + 1 / IDLE_FPS, i + 1
        self.t = end

    def strike(self):
        """Six-frame overhead slash; returns the instant the blade connects."""
        t, hit = self.t, None
        for index, hold in enumerate(STRIKE_TIMING):
            self._frame(t, f"atk{index}")
            if index == HIT_FRAME:
                hit = t
            t += hold
        self._frame(t, "idle0")
        self.t = t
        return hit

    def hurt(self, damage):
        before = self.hp
        self.hp = max(MIN_HEALTH, self.hp - damage)
        self._frame(self.t, "hurt1")
        self._frame(self.t + 0.06, "hurt0")
        self.health += [(self.t, before), (self.t + 0.08, self.hp)]
        self.t += 0.28
        self._frame(self.t, "idle0")

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
    def encounter(self, index, entry, chapter):
        tier = entry.tier
        speed, engage_x = MONSTER_SPEED[tier], layout.engage_x(tier)
        base = 0.45 + 0.08 * min(entry.gap_before, 5) + self.rng.uniform(0.0, 0.25)
        self.walk(self._walk_until_clear_spawn(base, engage_x, speed))
        engage_t = self.t
        path = solve_approach(self.scroll, engage_t, engage_x, speed)
        self.barrier = max(self.barrier, engage_t)  # the next foe waits for this duel
        self.hold(0.1)
        attack_t, knight_hurt = None, False
        if tier >= 3:
            attack_t = self.t
            knight_hurt = tier == 4 or self.rng.random() < 0.3
            self.hold(0.18)
            if knight_hurt:
                self.hurt(0.12 if tier == 4 else 0.08)
            else:
                self._frame(self.t, "parry0")
                self._frame(self.t + 0.1, "parry1")
                self.parries.append(self.t + 0.1)
                self.t += 0.26
                self._frame(self.t, "idle0")
        strikes = HITS_BY_TIER[tier]
        if strikes > 1 and self.rng.random() < 0.25:
            strikes -= 1  # a critical blow ends it early
        hits = tuple(self.strike() for _ in range(strikes))
        self.bank(hits[-1] + WISP_FLIGHT, entry.count)
        self.phases.append(Phase("fight", engage_t, self.t))
        self.encounters.append(
            Encounter(index, entry, chapter, path, engage_t, attack_t, knight_hurt, hits, hits[-1])
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

    def boss_fight(self):
        self.walk(1.0)
        enter_t = self.t
        land_t = enter_t + 1.6
        self.hold(land_t + 0.7 - self.t)
        breaths, hits = [], []
        for step in self.rng.choice(BOSS_PATTERNS):
            if step == "breath":
                start = self.t + 0.25
                self.hold(0.5)
                self.hurt(0.22)
                self.hold(start + 1.1 - self.t + 0.2)
                breaths.append((start, start + 1.1))
            else:
                hits.append(self.strike())
                self.hold(0.1)
        death_t = hits[-1]
        self.hold(0.8)
        for k in range(int((death_t + 4.1 - self.t) * REST_FPS)):
            self._frame(self.t + k / REST_FPS, f"kneel{k % 2}")
        self.bank(death_t + BOSS_WISP_FLIGHT, self.roster.boss.count)
        banner_t = death_t + 1.2
        self.t = banner_t + 2.9
        self.phases.append(Phase("boss", enter_t, self.t))
        return BossFight(self.roster.boss, enter_t, land_t, tuple(breaths), tuple(hits), death_t, banner_t)

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
        index = 0
        for chapter, (region, size) in enumerate(plan):
            if chapter == 0:
                self.chapters.append({"region": region, "start": 0.0, "title_t": GAME_TITLE_HOLD})
                self.walk(1.2, kind="intro")
            else:
                self.transition(region)
            for _ in range(size):
                if index in rest_before:
                    self.rest(chapter)
                self.encounter(index, self.roster.entries[index], chapter)
                index += 1
        boss = self.boss_fight()
        self.fades += [(self.t, 0.0), (self.t + OUTRO_FADE, 1.0)]
        self.phases.append(Phase("outro", self.t, self.t + OUTRO_FADE))
        self.t += OUTRO_FADE
        return self._freeze(boss)

    def _freeze(self, boss):
        duration = self.t
        self.scroll.append((duration, self.world))
        self.health.append((duration, self.hp))
        chapters = tuple(
            Chapter(c["region"], c["start"],
                    self.chapters[i + 1]["start"] if i + 1 < len(self.chapters) else duration,
                    c["title_t"])
            for i, c in enumerate(self.chapters)
        )
        rests = tuple(self._rest_record(mark, duration) for mark in self.rest_marks)
        return QuestScript(
            duration=duration,
            scroll=tuple(self.scroll),
            knight_frames=tuple(self.frames),
            phases=tuple(self.phases),
            chapters=chapters,
            encounters=tuple(self.encounters),
            rests=rests,
            boss=boss,
            souls=tuple(self.souls),
            health=tuple(self.health),
            fades=tuple(self.fades),
            parries=tuple(self.parries),
        )

    def _rest_record(self, mark, duration):
        spawn_t, sit_start, sit_end, chapter = mark
        path = [(spawn_t, float(layout.SPAWN_X)), (sit_start, float(layout.BONFIRE_X))]
        anchor = scroll_at(self.scroll, sit_end)
        for t, s in self.scroll:
            if t <= sit_end:
                continue
            x = layout.BONFIRE_X - (s - anchor)
            if x < -40:
                prev_t, prev_x = path[-1]
                exit_t = prev_t + (t - prev_t) * (prev_x + 40) / (prev_x - x)
                path.append((exit_t, -40.0))
                break
            path.append((t, x))
        return Rest(tuple(path), sit_start, sit_end, chapter)
