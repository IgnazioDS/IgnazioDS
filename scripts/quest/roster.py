"""Turn a contribution calendar into the quest's roster of monsters.

The roster is the last N *active* days (days with at least one contribution),
not the last N calendar days: a quiet month should not mean an empty screen.
Quiet stretches survive as `gap_before` (they become bonfire rests), the
biggest day becomes the dragon, and the rest are tiered by intensity.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Entry:
    date: str        # ISO date
    count: int       # real contributions that day
    tier: int        # 1..4 for monsters, 5 for the dragon
    gap_before: int  # quiet days since the previous roster day


@dataclass(frozen=True)
class Roster:
    entries: tuple   # Entry, chronological, dragon excluded
    boss: Entry
    year_total: int

    @property
    def souls_total(self):
        return sum(e.count for e in self.entries) + self.boss.count


def build(days, year_total, today, size=24):
    """days: [{"date": "YYYY-MM-DD", "count": int}], oldest first."""
    cutoff = today.isoformat()
    complete = [d for d in days if d["date"] < cutoff]
    active_idx = [i for i, d in enumerate(complete) if d["count"] > 0]
    if not active_idx:
        raise ValueError("no contributions in the calendar window; nothing to fight")
    chosen = active_idx[-size:]

    picks = []
    for n, idx in enumerate(chosen):
        prev = chosen[n - 1] if n else None
        gap = 0 if prev is None else idx - prev - 1
        picks.append((complete[idx]["date"], complete[idx]["count"], gap))

    boss_pos = max(range(len(picks)), key=lambda i: (picks[i][1], picks[i][0]))
    boss_date, boss_count, boss_gap = picks[boss_pos]
    rest = []
    for i, (date, count, gap) in enumerate(picks):
        if i == boss_pos:
            continue
        if i == boss_pos + 1:
            gap = max(gap, boss_gap)  # the dragon leaves the line-up; its quiet lead-in stays
        rest.append((date, count, gap))
    thresholds = _thresholds([count for _, count, _ in rest])
    entries = tuple(
        Entry(date, count, _tier(count, thresholds), gap) for date, count, gap in rest
    )
    return Roster(entries, Entry(boss_date, boss_count, 5, boss_gap), int(year_total))


def _thresholds(counts):
    """Quartile cut points; a monster's tier is how many cuts its count strictly exceeds.

    Equal counts always share a tier (a busier day is never an easier monster),
    so rosters with many tied days may skip a tier entirely.
    """
    ordered = sorted(counts)
    if not ordered:
        return (2, 3, 4)
    n = len(ordered)
    return tuple(ordered[min(n - 1, (n * q) // 4)] for q in (1, 2, 3))


def _tier(count, thresholds):
    return 1 + sum(1 for cut in thresholds if count > cut)


