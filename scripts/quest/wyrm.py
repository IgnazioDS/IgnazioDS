"""The Ashen Wyrm set piece, authored on the simulation's timeline (a mixin).

Round one on the bridge (fire, blades), then the wyrm takes to the air,
vanishes over the city and swoops back low across the bridge while the knight
rolls clear; it lands again, a second round in a seed-chosen order, and the
knight ends it with a leaping plunge into its neck. Then the aftermath:
catch breath, sword raised, kneel.
"""

from .combat import BLOWS, COMBO, HIT_FRAME
from .script import BossFight, Flight, Phase

DESCENT, ROAR_HOLD = 1.6, 0.7
BREATH_LEAD, BREATH_TIME = 0.25, 1.1
DASH, LUNGE_LEAD, LUNGE_TAIL, DASH_IN, DASH_OUT = 38.0, 0.22, 0.5, 0.12, 0.18
RISE_TIME, AWAY_TIME, PASS_AT, SWOOP_TIME, RETURN_DELAY = 0.9, 0.6, 0.45, 0.9, 0.3
DIVE_CATCHES = 0.2                 # chance the swoop catches the knight instead of him rolling clear
ROUND_TWO = (("strike", "breath", "strike"), ("breath", "strike", "strike"), ("strike", "strike", "breath"))
LEAP = (("leap0", 0.16), ("leap1", 0.24))
LEAP_REACH = (100.0, -84.0)        # knight offset when the blade meets the wyrm's neck
PLUNGE_HOLD, DROP_TIME = 0.16, 0.34
BOSS_WISP_FLIGHT = 1.3
CATCH_BREATH, CHEER_TIME, CHEER_FPS, KNEEL_TIME, KNEEL_FPS = 0.7, 1.8, 3.0, 0.8, 2.0
BANNER_DELAY, CRASH_DELAY = 1.0, 0.9


class WyrmFight:
    """Mixin: expects the Combat mixin plus walk/hold/_cycle/bank and the builder's timeline state."""

    def boss_fight(self):
        self.walk(1.0)
        enter_t = self.t
        land_t = enter_t + DESCENT
        self.shakes.append((land_t, 3))
        self.hold(land_t + ROAR_HOLD - self.t)
        fight = {"breaths": [], "hits": [], "blows": [], "flights": []}
        self._breath(fight)
        self._blows(fight, 2)
        self._dive(fight)
        for step in self.rng.choice(ROUND_TWO):
            if step == "breath":
                self._breath(fight)
            else:
                self._blows(fight, 1)
        death_t = self._plunge(fight)
        self.shakes.append((death_t + CRASH_DELAY, 3))
        self.hold(max(0.0, death_t + CATCH_BREATH - self.t))
        cheer_t = self.t
        self._cycle(("cheer0", "cheer1"), CHEER_FPS, CHEER_TIME)
        self._cycle(("kneel0", "kneel1"), KNEEL_FPS, KNEEL_TIME)
        self.bank(death_t + BOSS_WISP_FLIGHT, self.roster.boss.count)
        self.phases.append(Phase("boss", enter_t, self.t))
        boss = BossFight(self.roster.boss, enter_t, land_t, tuple(fight["breaths"]), tuple(fight["hits"]), death_t,
                         death_t + BANNER_DELAY, tuple(fight["blows"]), tuple(fight["flights"]))
        return boss, cheer_t

    def _breath(self, fight):
        start = self.t + BREATH_LEAD
        self.hold(0.5)
        self.hurt(0.22)
        self.hold(start + BREATH_TIME - self.t + 0.2)
        fight["breaths"].append((start, start + BREATH_TIME))
        self.shakes.append((start, 1))

    def _blows(self, fight, count):
        """Blows on the hovering wyrm, each one a dash in; chained blows share one lunge."""
        windows = []
        for k in range(count):
            blow = COMBO[len(fight["hits"]) % len(COMBO)]
            lead = sum(hold for _, hold in BLOWS[blow][:HIT_FRAME[blow]])
            if k == 0:  # never start a lunge before the last movement has settled
                self.hold(max(0.0, self.moves[-1][0] - (self.t + lead - LUNGE_LEAD)))
            hit = self.t + lead
            if windows and hit - LUNGE_LEAD <= windows[-1][1]:
                windows[-1] = (windows[-1][0], hit + LUNGE_TAIL)
            else:
                windows.append((hit - LUNGE_LEAD, hit + LUNGE_TAIL))
            fight["hits"].append(self.strike(blow))
            fight["blows"].append(blow)
            self.hold(0.1)
        for start, end in windows:
            self._move([(start, 0.0, 0.0), (start + DASH_IN, DASH, 0.0), (end - DASH_OUT, DASH, 0.0), (end, 0.0, 0.0)])
        self.hold(max(0.0, windows[-1][1] - self.t))

    def _dive(self, fight):
        """The wyrm climbs away, then swoops low over the bridge; the knight rolls clear or is struck."""
        takeoff = self.t
        self.hold(RISE_TIME + AWAY_TIME)
        dive = self.t
        pass_t = dive + PASS_AT
        if self.rng.random() < DIVE_CATCHES:
            self.hold(pass_t - self.t)
            self.hurt(0.15)
            outcome = "hurt"
        else:
            self.hold(pass_t - 0.3 - self.t)
            self.dodge()
            outcome = "dodge"
        back = dive + SWOOP_TIME + RETURN_DELAY
        land = back + DESCENT
        self.shakes.append((land, 3))
        self.hold(max(0.0, land + ROAR_HOLD - self.t))
        fight["flights"].append(Flight(takeoff, dive, pass_t, back, land, outcome))

    def _plunge(self, fight):
        """Crouch, spring at the wyrm and drive the blade down into its neck; returns the killing instant."""
        self.hold(0.3)
        leap_t = t = self.t
        for name, hold in LEAP:
            self._frame(t, name)
            t += hold
        plunge_t = t
        self._frame(plunge_t, "leap2")
        dx, dy = LEAP_REACH
        self._move([(leap_t + LEAP[0][1] * 0.6, 0.0, 0.0), (plunge_t - 0.1, dx * 0.72, dy * 1.2), (plunge_t, dx, dy)])
        fight["hits"].append(plunge_t)
        fight["blows"].append("plunge")
        self.shakes.append((plunge_t, 4))
        landed = plunge_t + PLUNGE_HOLD + DROP_TIME
        self._move([(plunge_t + PLUNGE_HOLD, dx, dy), (landed, 0.0, 0.0)])
        self._frame(landed, "roll3")
        self._frame(landed + 0.16, "idle0")
        self.t = landed + 0.2
        return plunge_t
