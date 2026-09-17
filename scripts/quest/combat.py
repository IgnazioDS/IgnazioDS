"""The knight's side of every duel: blows, parries, dodges and wounds.

A mixin for the simulation's builder. Each method writes knight frames onto
the shared timeline, advances time, and records what the renderer needs:
hit times, blow names, monster attacks and their outcomes, the knight's
sidesteps (knight_moves) and screen shakes. All randomness comes from the
builder's seeded rng, so a quest replays identically.
"""

from .script import Attack

# (frame, hold) per blow; the blade connects at HIT_FRAME
BLOWS = {
    "slash": (("atk0", 0.08), ("atk1", 0.10), ("atk2", 0.06), ("atk3", 0.08), ("atk4", 0.08), ("atk5", 0.08)),
    "rise": (("swp0", 0.10), ("swp1", 0.05), ("swp2", 0.06), ("swp3", 0.10), ("swp4", 0.08)),
    "thrust": (("thr0", 0.12), ("thr1", 0.05), ("thr2", 0.10), ("thr3", 0.10)),
    "riposte": (("thr1", 0.05), ("thr2", 0.12), ("thr3", 0.10)),
}
HIT_FRAME = {"slash": 2, "rise": 2, "thrust": 1, "riposte": 0}
COMBO = ("slash", "rise", "thrust")
HIT_STOP = 0.06                   # the killing blow's contact frame lingers
ROLL = (("roll0", 0.06), ("roll1", 0.09), ("roll2", 0.09), ("roll3", 0.08))
DODGE_BACK, STEP_IN = 30.0, 0.3   # px rolled away; seconds to walk back into guard
KNOCKBACK = 7.0
WINDUP_LEAD = 0.18                # a monster's blow lands this long after its windup starts
OUTCOMES = {                      # tier -> (hurt, parry) thresholds; the rest dodge
    3: (0.25, 0.60),
    4: (0.45, 0.70),
}


class Combat:
    """Mixin: expects self.t, self.rng, self.hp, self.health, self._frame, self.hold, self.moves, self.shakes."""

    def strike(self, blow="slash", heavy=False, shake=2):
        """Play one blow; returns the instant the blade connects. Heavy blows freeze on contact and shake."""
        t, hit = self.t, None
        for index, (name, hold) in enumerate(BLOWS[blow]):
            self._frame(t, name)
            if index == HIT_FRAME[blow]:
                hit = t
                hold += HIT_STOP if heavy else 0.0
            t += hold
        self._frame(t, "idle0")
        self.t = t
        if heavy:
            self.shakes.append((hit, shake))
        return hit

    def hurt(self, damage):
        before = self.hp
        self.hp = max(self.min_health, self.hp - damage)
        start = self.t
        self._frame(start, "hurt1")
        self._frame(start + 0.06, "hurt0")
        self.health += [(start, before), (start + 0.08, self.hp)]
        self._move([(start, 0.0, 0.0), (start + 0.06, -KNOCKBACK, 0.0), (start + 0.28, 0.0, 0.0)])
        self.t = start + 0.28
        self._frame(self.t, "idle0")

    def parry(self):
        self._frame(self.t, "parry0")
        self._frame(self.t + 0.1, "parry1")
        self.t += 0.26
        self._frame(self.t, "idle0")

    def dodge(self):
        """Roll back out of reach, then walk straight back into guard."""
        start = t = self.t
        for name, hold in ROLL:
            self._frame(t, name)
            t += hold
        landed = t
        for k in range(4):
            self._frame(landed + k * STEP_IN / 4, f"walk{(6 - k) % 8}")
        self._move([(start, 0.0, 0.0), (landed, -DODGE_BACK, 0.0), (landed + STEP_IN, 0.0, 0.0)])
        self.t = landed + STEP_IN
        self._frame(self.t, "idle0")

    def monster_attack(self, tier):
        """The foe swings; the knight is hit, parries or dodges. Returns the Attack."""
        start = self.t
        hurt_below, parry_below = OUTCOMES[min(4, max(3, tier))]
        roll = self.rng.random()
        outcome = "hurt" if roll < hurt_below else "parry" if roll < parry_below else "dodge"
        if outcome == "dodge":
            self.hold(0.06)
            self.dodge()
        else:
            self.hold(WINDUP_LEAD)
            if outcome == "hurt":
                self.hurt(0.12 if tier >= 4 else 0.08)
            else:
                self.parry()
        return Attack(start, outcome)

    def duel(self, tier, elite, strikes):
        """The exchange after engaging: returns (attacks, hits, blows, heavy)."""
        attacks, hits, blows, weights = [], [], [], []
        if tier >= 3 or elite:
            attacks.append(self.monster_attack(tier))
        combo = 0
        for i in range(strikes):
            if elite and i == 2:
                self.hold(0.12)
                attacks.append(self.monster_attack(tier))
            riposte = attacks and attacks[-1].outcome == "parry" and attacks[-1].t > (hits[-1] if hits else -1.0)
            blow = "riposte" if riposte else COMBO[combo % len(COMBO)]
            combo += 0 if riposte else 1
            killing = i == strikes - 1 and (tier >= 3 or elite)
            heavy = killing or blow == "riposte"
            hits.append(self.strike(blow, heavy=heavy, shake=2 if killing else 1))
            blows.append(blow)
            weights.append(heavy)
        return tuple(attacks), tuple(hits), tuple(blows), tuple(weights)

    def _move(self, keys):
        """Append knight offset keyframes (t, dx, dy), keeping the track time-ordered."""
        for key in keys:
            if self.moves and key[0] < self.moves[-1][0] - 1e-9:
                raise ValueError(f"knight move at t={key[0]:.3f}s recorded after one at t={self.moves[-1][0]:.3f}s")
            self.moves.append(key)
