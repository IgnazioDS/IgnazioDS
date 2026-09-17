"""The bestiary: which creature embodies a day in each region, how it moves
and where it stands to fight.

Difficulty still comes from the day's tier (busier day, tougher fight); the
region only decides the shape the day takes: a tier-2 day is a dire wolf on
the Violet Moor, a ghoul in the Hollow Wood, a gargoyle at the Keep. Each
chapter's busiest day (when the chapter is long enough to have one) comes as
an elite: marked, harder, and it strikes back.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Kind:
    key: str
    title: str        # nameplate
    speed: float      # charge speed over the ground (px/s)
    engage_x: int     # frame left edge while fighting, where its reach meets the knight's
    lift: int = 0     # hover height above the ground line (the dead fall this far)


KINDS = {kind.key: kind for kind in (
    Kind("bat", "BLOOD BAT", 95.0, 144, lift=30),
    Kind("crow", "CARRION CROW", 104.0, 146, lift=26),
    Kind("wolf", "DIRE WOLF", 118.0, 148),
    Kind("ghoul", "GHOUL", 58.0, 140),
    Kind("gargoyle", "GARGOYLE", 72.0, 136, lift=10),
    Kind("skeleton", "SKELETON", 50.0, 130),
    Kind("spider", "BROODMOTHER", 64.0, 140),
    Kind("wraith", "WRAITH", 66.0, 137, lift=2),
    Kind("revenant", "REVENANT", 52.0, 108),
)}

# region -> creature for tiers 1..4
LINEUPS = {
    "violet": ("bat", "wolf", "skeleton", "revenant"),
    "wood": ("bat", "ghoul", "spider", "wraith"),
    "crimson": ("crow", "ghoul", "skeleton", "revenant"),
    "keep": ("bat", "gargoyle", "skeleton", "wraith"),
}

ELITE_MIN_FOES, ELITE_MIN_TIER = 3, 2


def kind_for(region, tier):
    """The Kind that embodies a tier-1..4 day in a region; bad input fails loudly."""
    if region not in LINEUPS:
        raise ValueError(f"no line-up for region {region!r}")
    if not 1 <= tier <= 4:
        raise ValueError(f"monster tiers run 1-4, got {tier!r}")
    return KINDS[LINEUPS[region][tier - 1]]


def elite_index(entries):
    """Index of a chapter's champion: its busiest day (latest on ties), if the chapter earns one."""
    if len(entries) < ELITE_MIN_FOES:
        return None
    best = max(range(len(entries)), key=lambda i: (entries[i].count, entries[i].date))
    return best if entries[best].tier >= ELITE_MIN_TIER else None
