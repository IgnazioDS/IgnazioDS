"""Deterministic Space Invaders simulation.

Produces a GameScript: an immutable event log (march steps, shots, kills,
bombs, set pieces) that the renderer turns into SMIL timelines. Same seed +
same contribution data => byte-identical game.
"""

import random
from dataclasses import dataclass, field

# Playfield in game pixels (rendered at 2x in the SVG).
WIDTH, HEIGHT = 360, 210
COLS, ROWS = 11, 5
COL_SPACING, ROW_SPACING = 26, 18
CELL_W = 12
FORM_X, FORM_Y = 44, 42
MARCH_BOUND, MARCH_STEP, DESCEND_STEP, MAX_DESCEND = 16, 4, 4, 24
SHIELD_CENTERS = (72, 144, 216, 288)
SHIELD_HALF_W, SHIELD_TOP, SHIELD_BOTTOM = 11, 158, 174
CANNON_Y, BULLET_START_Y, GROUND_Y = 180, 178, 196
BULLET_SPEED, CANNON_SPEED = 260, 105
AIM_SETTLE, FIRE_COOLDOWN = 0.12, 0.1
BOMB_SPEED = 55
UFO_Y, UFO_SPEED, UFO_TRIGGER_ALIVE, UFO_POINTS = 22, 45, 30, 150
DEATH_TRIGGER_ALIVE = 18
INTRO_DELAY, OUTRO_DELAY = 0.8, 2.6


@dataclass(frozen=True)
class Shot:
    x: float
    t_fire: float
    t_impact: float
    y_impact: float


@dataclass(frozen=True)
class Kill:
    invader: int
    t: float
    points: int


@dataclass(frozen=True)
class Bomb:
    x: float
    y_start: float
    t_drop: float
    t_land: float
    y_land: float
    hits_shield: bool


@dataclass(frozen=True)
class Notch:
    shield: int
    x: float
    depth: int
    from_top: bool
    t: float


@dataclass(frozen=True)
class GameScript:
    duration: float
    march: tuple          # (t, ox, oy)
    cannon_path: tuple    # (t, x) waypoints, linear interpolation
    shots: tuple          # Shot
    kills: tuple          # Kill
    bombs: tuple          # Bomb
    notches: tuple        # Notch
    score_states: tuple   # (t, value)
    ufo: dict             # set-piece timing
    cannon_death: dict    # set-piece timing
    wave_text_t: float


def slot_center_x(col):
    return FORM_X + col * COL_SPACING + CELL_W / 2


def slot_y(row):
    return FORM_Y + row * ROW_SPACING


def march_interval(alive):
    return 0.10 + 0.72 * (alive / (COLS * ROWS)) ** 1.4


@dataclass
class _MarchState:
    next_t: float
    ox: int = 0
    oy: int = 0
    direction: int = 1

    def step(self):
        if abs(self.ox + MARCH_STEP * self.direction) > MARCH_BOUND:
            self.oy = min(self.oy + DESCEND_STEP, MAX_DESCEND)
            self.direction = -self.direction
        else:
            self.ox += MARCH_STEP * self.direction

    def copy(self):
        return _MarchState(self.next_t, self.ox, self.oy, self.direction)


class _Sim:
    """Mutable working state for one playthrough; emits immutable records."""

    def __init__(self, day_counts, seed):
        self.rng = random.Random(seed)
        self.day_counts = list(day_counts)
        self.alive = [True] * (COLS * ROWS)
        self.t = INTRO_DELAY
        self.cannon_x = WIDTH / 2
        self.march_state = _MarchState(next_t=0.6)
        self.march_log = [(0.0, 0, 0)]
        self.cannon_path = [(0.0, self.cannon_x)]
        self.shots, self.kills, self.bombs, self.notches = [], [], [], []
        self.shield_damage = {}
        self.score = 0
        self.score_states = [(0.0, 0)]
        self.ufo = {}
        self.cannon_death = {}
        self.ufo_done = self.death_done = False

    # -- march ------------------------------------------------------------
    def _advance_march(self, until):
        while self.march_state.next_t <= until and self.alive_count() > 0:
            self.march_state.step()
            self.march_log.append(
                (self.march_state.next_t, self.march_state.ox, self.march_state.oy)
            )
            self.march_state.next_t += march_interval(self.alive_count())

    def _predict_offsets(self, at_time):
        probe = self.march_state.copy()
        interval = march_interval(self.alive_count())
        while probe.next_t <= at_time:
            probe.step()
            probe.next_t += interval
        return probe.ox, probe.oy

    def alive_count(self):
        return sum(self.alive)

    # -- cannon -----------------------------------------------------------
    def _move_cannon(self, target_x):
        travel = abs(target_x - self.cannon_x) / CANNON_SPEED
        if travel > 0.01:
            self.cannon_path.append((self.t, self.cannon_x))
            self.t += travel
            self.cannon_path.append((self.t, target_x))
            self.cannon_x = target_x
        self.t += AIM_SETTLE

    def _fire_at(self, x, y_impact):
        t_fire = self.t
        flight = (BULLET_START_Y - y_impact) / BULLET_SPEED
        self.shots.append(Shot(x, t_fire, t_fire + flight, y_impact))
        self._notch_from_bullet(x, t_fire)
        return t_fire + flight

    def _notch_from_bullet(self, x, t):
        for i, cx in enumerate(SHIELD_CENTERS):
            if abs(x - cx) <= SHIELD_HALF_W:
                self._add_notch(i, x, t + 0.04, from_top=False)

    def _add_notch(self, shield, x, t, from_top):
        bucket = (shield, round(x / 4), from_top)
        depth = self.shield_damage.get(bucket, 0) + 1
        self.shield_damage[bucket] = depth
        self.notches.append(Notch(shield, x, depth, from_top, t))

    # -- targeting --------------------------------------------------------
    def _pick_target(self):
        cols_alive = [c for c in range(COLS) if self._lowest_alive(c) is not None]
        if self.rng.random() < 0.22:
            col = self.rng.choice(cols_alive)
        else:
            col = min(
                cols_alive,
                key=lambda c: (abs(slot_center_x(c) + self.march_state.ox - self.cannon_x),
                               self.rng.random()),
            )
        return col, self._lowest_alive(col)

    def _lowest_alive(self, col):
        rows = [r for r in range(ROWS) if self.alive[r * COLS + col]]
        return max(rows) if rows else None

    def _kill_one(self):
        col, row = self._pick_target()
        idx = row * COLS + col
        fire_x, y_impact = self._solve_intercept(col, row)
        self._move_cannon(fire_x)
        t_impact = self._fire_at(fire_x, y_impact)
        self._advance_march(t_impact)
        self.alive[idx] = False
        self.score += self.day_counts[idx]
        self.kills.append(Kill(idx, t_impact, self.day_counts[idx]))
        self.score_states.append((t_impact, self.score))
        self.t = t_impact + FIRE_COOLDOWN

    def _solve_intercept(self, col, row):
        y_impact = slot_y(row) + 4
        fire_x = slot_center_x(col) + self.march_state.ox
        for _ in range(3):
            travel = abs(fire_x - self.cannon_x) / CANNON_SPEED
            t_fire = self.t + travel + AIM_SETTLE
            t_hit = t_fire + (BULLET_START_Y - y_impact) / BULLET_SPEED
            ox, oy = self._predict_offsets(t_hit)
            fire_x = slot_center_x(col) + ox
            y_impact = slot_y(row) + oy + 4
        return fire_x, y_impact

    # -- set pieces -------------------------------------------------------
    def _ufo_run(self):
        self._move_cannon(WIDTH / 2)
        t_enter = self.t + 0.4
        hit_x = WIDTH / 2
        t_hit = t_enter + (hit_x + 16 - 8) / UFO_SPEED
        flight = (BULLET_START_Y - (UFO_Y + 4)) / BULLET_SPEED
        self.shots.append(Shot(hit_x, t_hit - flight, t_hit, UFO_Y + 4))
        self.score += UFO_POINTS
        self.score_states.append((t_hit, self.score))
        self.ufo = {"t_enter": t_enter, "t_die": t_hit, "x_die": hit_x}
        self._advance_march(t_hit)
        self.t = t_hit + 0.6

    def _death_run(self):
        gap_x = self._clear_gap_x()
        drop_col = min(
            (c for c in range(COLS) if self._lowest_alive(c) is not None),
            key=lambda c: abs(slot_center_x(c) + self.march_state.ox - gap_x),
        )
        row = self._lowest_alive(drop_col)
        bomb_x = slot_center_x(drop_col) + self.march_state.ox
        bomb_y = slot_y(row) + self.march_state.oy + 8
        self._move_cannon(bomb_x)
        t_drop = self.t + 0.2
        t_land = t_drop + (CANNON_Y - bomb_y) / BOMB_SPEED
        self.bombs.append(Bomb(bomb_x, bomb_y, t_drop, t_land, CANNON_Y, False))
        self.cannon_death = {"t": t_land, "x": bomb_x, "t_respawn": t_land + 1.8}
        self._advance_march(t_land + 1.8)
        self.t = t_land + 1.8 + FIRE_COOLDOWN

    def _clear_gap_x(self):
        gaps = [(SHIELD_CENTERS[i] + SHIELD_CENTERS[i + 1]) / 2
                for i in range(len(SHIELD_CENTERS) - 1)]
        return self.rng.choice(gaps)

    def _decor_bomb(self):
        candidates = [i for i, a in enumerate(self.alive) if a]
        if not candidates:
            return
        idx = self.rng.choice(candidates)
        col, row = idx % COLS, idx // COLS
        x = slot_center_x(col) + self.march_state.ox
        y = slot_y(row) + self.march_state.oy + 8
        shield = next(
            (i for i, cx in enumerate(SHIELD_CENTERS) if abs(x - cx) <= SHIELD_HALF_W),
            None,
        )
        y_land = SHIELD_TOP if shield is not None else GROUND_Y - 4
        t_land = self.t + (y_land - y) / BOMB_SPEED
        self.bombs.append(Bomb(x, y, self.t, t_land, y_land, shield is not None))
        if shield is not None:
            self._add_notch(shield, x, t_land, from_top=True)

    # -- main loop --------------------------------------------------------
    def run(self):
        decor_at = {8, 16, 27, 37, 47}
        killed = 0
        while self.alive_count() > 0:
            if not self.ufo_done and self.alive_count() <= UFO_TRIGGER_ALIVE:
                self.ufo_done = True
                self._ufo_run()
            if not self.death_done and self.alive_count() <= DEATH_TRIGGER_ALIVE:
                self.death_done = True
                self._death_run()
            if killed in decor_at:
                self._decor_bomb()
            self._kill_one()
            killed += 1
        wave_t = self.t + 0.5
        duration = wave_t + OUTRO_DELAY
        self.cannon_path.append((duration, self.cannon_x))
        return GameScript(
            duration=duration,
            march=tuple(self.march_log),
            cannon_path=tuple(self.cannon_path),
            shots=tuple(self.shots),
            kills=tuple(self.kills),
            bombs=tuple(self.bombs),
            notches=tuple(self.notches),
            score_states=tuple(self.score_states),
            ufo=self.ufo,
            cannon_death=self.cannon_death,
            wave_text_t=wave_t,
        )


def simulate(day_counts, seed):
    """Run one full game. day_counts: 55 ints, oldest first (top-left slot)."""
    if len(day_counts) != COLS * ROWS:
        raise ValueError(f"expected {COLS * ROWS} day counts, got {len(day_counts)}")
    return _Sim(day_counts, seed).run()
