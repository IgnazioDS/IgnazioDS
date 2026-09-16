"""HUD and overlays: health, souls counter, dates, chapter titles, boss bar,
victory banner, fades and the eleventh.dev footer.
"""

import dataclasses
from dataclasses import dataclass

from .. import layout
from ..art import effects, font, raster, sprite
from ..art.scenery import TITLES
from . import smil

MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
ROMAN = ("I", "II", "III", "IV", "V")
BOSS_NAME = "THE ASHEN WYRM"
HP_X, HP_Y, HP_W = 8, 7, 72
BOSS_BAR_W = 150
MIN_CARD_HOLD = 0.5


@dataclass(frozen=True)
class Card:
    key: str
    start: float
    hold: float
    fade: float

    @property
    def end(self):
        return self.start + 2 * self.fade + self.hold


def card_schedule(script):
    """Title cards in play order; overlapping cards are shortened, then delayed.

    Tiny rosters switch chapters faster than a card can play, so a later card
    first trims the earlier one's hold and, if that is not enough, waits for it.
    """
    wanted = [Card("game-title", 0.2, 1.6, 0.35)]
    wanted += [Card(f"title-{c.region}", c.title_t, 1.7, 0.5) for c in script.chapters]
    wanted += [Card("boss-splash", script.boss.land_t, 1.1, 0.3), Card("victory", script.boss.banner_t, 1.9, 0.5)]
    placed = []
    for card in sorted(wanted, key=lambda c: c.start):
        if placed and card.start < placed[-1].end:
            prev = placed[-1]
            placed[-1] = dataclasses.replace(prev, hold=max(MIN_CARD_HOLD, card.start - prev.start - 2 * prev.fade))
            card = dataclasses.replace(card, start=max(card.start, placed[-1].end))
        room = script.duration - 0.05 - card.start - 2 * card.fade
        if room < MIN_CARD_HOLD:
            continue
        placed.append(dataclasses.replace(card, hold=min(card.hold, room)))
    return tuple(placed)


def _card(script, key):
    return next((card for card in card_schedule(script) if card.key == key), None)


def date_windows(script):
    """(iso date, start, end) for the date plaque; each ends before the next begins."""
    raw = [(e.entry.date, e.engage_t - 0.9, e.death_t + 0.7) for e in script.encounters]
    raw.append((script.boss.entry.date, script.boss.enter_t, script.boss.banner_t))
    windows = []
    for i, (iso, start, end) in enumerate(raw):
        if i + 1 < len(raw):
            end = min(end, raw[i + 1][1])
        windows.append((iso, max(0.0, start), end))
    return tuple(windows)


def short_date(iso):
    _, month, day = iso.split("-")
    return f"{MONTHS[int(month) - 1]} {int(day)}"


def _stack(top, bottom, gap=1):
    width = max(top.width, bottom.width)
    canvas = raster.Canvas(width, top.height + gap + bottom.height)
    canvas.blit(top, (width - top.width) // 2, 0)
    canvas.blit(bottom, (width - bottom.width) // 2, top.height + gap)
    return canvas.freeze()


def _centered_use(asset, cy):
    return f'<use href="#{asset.id}" x="{smil.num(layout.WIDTH / 2 - asset.width / 2)}" y="{cy}"/>'


def _fade_card(card, duration):
    t_in, fade, hold = card.start, card.fade, card.hold
    points = [(0.0, "0"), (t_in, "0"), (t_in + fade, "1"), (t_in + fade + hold, "1"), (t_in + 2 * fade + hold, "0")]
    return smil.linear("opacity", points, duration)


def fade_overlay(script):
    points = [(t, smil.num(o)) for t, o in script.fades]
    return (
        f'<rect width="{layout.WIDTH}" height="{layout.HEIGHT}" fill="#050308" opacity="0">'
        f'{smil.linear("opacity", points, script.duration)}</rect>'
    )


def health_bar(script):
    d = script.duration
    widths = [(t, smil.num(HP_W * hp)) for t, hp in script.health]
    anim = smil.linear("width", widths, d)
    return (
        f'<rect x="{HP_X - 2}" y="{HP_Y - 2}" width="{HP_W + 4}" height="9" fill="#07050a"/>'
        f'<rect x="{HP_X - 1}" y="{HP_Y - 1}" width="{HP_W + 2}" height="7" fill="#1a0f14" stroke="#4a3a55" stroke-width="1"/>'
        f'<rect x="{HP_X}" y="{HP_Y}" width="{HP_W}" height="5" fill="#8e1a2b">{anim}</rect>'
        f'<rect x="{HP_X}" y="{HP_Y}" width="{HP_W}" height="1" fill="#e0485c">{anim}</rect>'
    )


def souls_counter(script, roster, book):
    d = script.duration
    ax, ay = layout.SOULS_ANCHOR
    icon = book.image("wisp", effects.wisp())
    parts = [f'<use href="#{icon.id}" x="{ax - 5}" y="{ay - 5}"/>']
    states = list(script.souls)
    for i, (t, value) in enumerate(states):
        end = states[i + 1][0] if i + 1 < len(states) else d
        label = book.image(f"souls-{value}", font.render(f"{value:04d}", font.SOUL))
        visibility = smil.windows([(t, end)], d) if len(states) > 1 else ""
        base = "1" if i == 0 else "0"
        parts.append(
            f'<g opacity="{base}">{visibility}<use href="#{label.id}" x="{ax + 8}" y="{ay - 5}"/></g>'
        )
    year = book.image("year", font.render(f"YEAR {roster.year_total}", font.BONE))
    parts.append(f'<use href="#{year.id}" x="{layout.WIDTH - 6 - year.width}" y="{ay + 6}" opacity="0.8"/>')
    return "".join(parts)


def date_labels(script, book):
    d = script.duration
    parts = []
    for iso, start, end in date_windows(script):
        if end <= start:
            continue
        label = book.image(f"date-{iso}", font.render(short_date(iso), font.EMBER))
        parts.append(f'<g opacity="0">{smil.windows([(start, end)], d)}{_centered_use(label, 4)}</g>')
    return "".join(parts)


def chapter_titles(script, book):
    d = script.duration
    parts = []
    for i, chapter in enumerate(script.chapters):
        card = _card(script, f"title-{chapter.region}")
        if card is None:
            continue
        top = font.render(f"CHAPTER {ROMAN[i]}", font.BONE)
        bottom = raster.scale(font.render(TITLES[chapter.region], font.GOLD), 2)
        image = book.image(f"title-{chapter.region}", _stack(top, bottom))
        parts.append(f'<g opacity="0">{_fade_card(card, d)}{_centered_use(image, 46)}</g>')
    return "".join(parts)


def game_title(script, book):
    """Opening card: the quest's name over the first region."""
    top = raster.scale(font.render("THE ELEVENTH KNIGHT", font.GOLD), 2)
    sub = font.render("A QUEST THROUGH MY LAST DAYS OF CODE", font.BONE)
    image = book.image("game-title", _stack(top, sprite.pad(sub, sub.width, sub.height + 2, 0, 2)))
    card = _card(script, "game-title")
    if card is None:
        return ""
    return f'<g opacity="0">{_fade_card(card, script.duration)}{_centered_use(image, 52)}</g>'


def boss_intro(script, book):
    """Letterbox bars while the wyrm descends, and its name splashed as it lands."""
    boss, d = script.boss, script.duration
    bars = [(0.0, "0"), (boss.enter_t, "0"), (boss.enter_t + 0.5, "16"), (boss.land_t + 1.6, "16"), (boss.land_t + 2.1, "0")]
    height = smil.linear("height", bars, d)
    offset = smil.linear("y", [(t, smil.num(layout.HEIGHT - float(v))) for t, v in bars], d)
    bars_svg = (
        f'<rect x="0" y="0" width="{layout.WIDTH}" height="0" fill="#050308">{height}</rect>'
        f'<rect x="0" y="{layout.HEIGHT}" width="{layout.WIDTH}" height="0" fill="#050308">{height}{offset}</rect>'
    )
    card = _card(script, "boss-splash")
    if card is None:
        return bars_svg
    image = book.image("boss-splash", raster.scale(font.render(BOSS_NAME, font.EMBER), 2))
    return f'{bars_svg}<g opacity="0">{_fade_card(card, d)}{_centered_use(image, 66)}</g>'


def boss_bar(script, book):
    d = script.duration
    boss = script.boss
    name = book.image("boss-name", font.render(BOSS_NAME, font.BONE))
    total = max(1, len(boss.hits))
    widths = [(0.0, BOSS_BAR_W), (boss.land_t, BOSS_BAR_W)]
    for i, hit in enumerate(boss.hits, start=1):
        widths += [(hit, BOSS_BAR_W * (1 - (i - 1) / total)), (hit + 0.12, BOSS_BAR_W * (1 - i / total))]
    anim = smil.linear("width", [(t, smil.num(w)) for t, w in widths], d)
    x = layout.WIDTH / 2 - BOSS_BAR_W / 2
    return (
        f'<g opacity="0">{smil.windows([(boss.land_t, boss.death_t + 0.6)], d)}'
        f'{_centered_use(name, 15)}'
        f'<rect x="{smil.num(x - 1)}" y="27" width="{BOSS_BAR_W + 2}" height="5" fill="#07050a" stroke="#4a3a55"/>'
        f'<rect x="{smil.num(x)}" y="28" width="{BOSS_BAR_W}" height="3" fill="#b8402a">{anim}</rect></g>'
    )


def victory_banner(script, book):
    boss = script.boss
    top = raster.scale(font.render("WYRM FELLED", font.GOLD), 2)
    sub = font.render(
        f"BIGGEST DAY · {short_date(boss.entry.date)} · {boss.entry.count} CONTRIBUTIONS", font.BONE
    )
    image = book.image("victory", _stack(top, sprite.pad(sub, sub.width, sub.height + 2, 0, 2)))
    card = _card(script, "victory")
    if card is None:
        return ""
    return f'<g opacity="0">{_fade_card(card, script.duration)}{_centered_use(image, 52)}</g>'


def footer(book):
    label = book.image("footer", font.render("ELEVENTH.DEV", font.BONE))
    x = layout.WIDTH - 6 - label.width
    y = layout.HEIGHT - label.height - 3
    return f'<a href="https://eleventh.dev"><use href="#{label.id}" x="{x}" y="{y}" opacity="0.75"/></a>'
