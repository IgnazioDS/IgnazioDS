"""Cinematic cards: the game title, chapter titles, the wyrm's entrance, the
victory banner and the quest-complete tally.

Cards are scheduled together so they never overlap: when chapters switch
faster than a card can play, a later card first trims the earlier one's hold
and, if that is not enough, waits for it.
"""

import dataclasses
from dataclasses import dataclass

from .. import layout
from ..art import font, raster, sprite
from ..art.hud import TIER_COLORS
from ..art.scenery import TITLES
from . import smil
from .assets import centered_use

ROMAN = ("I", "II", "III", "IV", "V")
BOSS_NAME = "THE ASHEN WYRM"
MIN_CARD_HOLD = 0.5
STATS_FADE = 0.4
PANEL_W, PANEL_H, PANEL_Y = 264, 86, 34
SQUARE, SQUARE_GAP = 7, 2
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
C = raster.rgb


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
    """Every card in play order, trimmed or delayed so none overlap, all inside the loop."""
    boss, epilogue = script.boss, script.epilogue
    stats_hold = epilogue.fade_t - epilogue.stats_t - 2 * STATS_FADE
    wanted = [Card("game-title", script.prologue.title_t, 2.4, 0.5)]
    wanted += [Card(f"title-{c.region}", c.title_t, 1.7, 0.5) for c in script.chapters]
    wanted += [
        Card("boss-splash", boss.land_t, 1.1, 0.3),
        Card("victory", boss.banner_t, 1.6, 0.5),
        Card("quest-complete", epilogue.stats_t, max(MIN_CARD_HOLD, stats_hold), STATS_FADE),
    ]
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


def short_date(iso):
    _, month, day = iso.split("-")
    return f"{MONTHS[int(month) - 1]} {int(day)}"


def _stack(*images, gap=1):
    width = max(image.width for image in images)
    canvas = raster.Canvas(width, sum(image.height for image in images) + gap * (len(images) - 1))
    y = 0
    for image in images:
        canvas.blit(image, (width - image.width) // 2, y)
        y += image.height + gap
    return canvas.freeze()


def _divider(width):
    """Gold rule with a diamond at its heart, fading out toward both ends."""
    canvas = raster.Canvas(width, 5)
    mid = width // 2
    for x in range(width):
        reach = abs(x - mid) / mid
        if reach < 0.92 and (reach < 0.6 or (x % 2 == 0)):
            canvas.put(x, 2, C("#c9862e") if reach > 0.3 else C("#f5c55c"))
    for dy, half in ((0, 0), (1, 1), (2, 2), (3, 1), (4, 0)):
        for dx in range(-half, half + 1):
            canvas.put(mid + dx, dy, C("#fff1c1") if dx == 0 else C("#e0a53f"))
    return canvas.freeze()


def _fade_card(card, duration):
    t_in, fade, hold = card.start, card.fade, card.hold
    points = [(0.0, "0"), (t_in, "0"), (t_in + fade, "1"), (t_in + fade + hold, "1"), (t_in + 2 * fade + hold, "0")]
    return smil.linear("opacity", points, duration)


def _shown(card, duration, body):
    return f'<g opacity="0">{_fade_card(card, duration)}{body}</g>'


def game_title(script, roster, book):
    """Opening card over the vista: the quest's name and what it is made of."""
    card = _card(script, "game-title")
    if card is None:
        return ""
    title = raster.scale(font.render("THE ELEVENTH KNIGHT", font.GOLD), 2)
    days = len(roster.entries) + 1
    sub = font.render(f"A QUEST THROUGH MY LAST {days} DAYS OF CODE", font.BONE)
    image = book.image("game-title", _stack(title, _divider(title.width - 40), sprite.pad(sub, sub.width, sub.height + 1, 0, 1), gap=2))
    return _shown(card, script.duration, centered_use(image, 26))


def chapter_titles(script, book):
    parts = []
    for i, chapter in enumerate(script.chapters):
        card = _card(script, f"title-{chapter.region}")
        if card is None:
            continue
        top = font.render(f"CHAPTER {ROMAN[i]}", font.BONE)
        bottom = raster.scale(font.render(TITLES[chapter.region], font.GOLD), 2)
        image = book.image(f"title-{chapter.region}", _stack(top, bottom))
        parts.append(_shown(card, script.duration, centered_use(image, 46)))
    return "".join(parts)


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
    return bars_svg + _shown(card, d, centered_use(image, 66))


def victory_banner(script, book):
    card = _card(script, "victory")
    if card is None:
        return ""
    boss = script.boss
    top = raster.scale(font.render("WYRM FELLED", font.GOLD), 2)
    sub = font.render(f"BIGGEST DAY · {short_date(boss.entry.date)} · {boss.entry.count} CONTRIBUTIONS", font.BONE)
    image = book.image("victory", _stack(top, sprite.pad(sub, sub.width, sub.height + 2, 0, 2)))
    return _shown(card, script.duration, centered_use(image, 52))


def _panel(width, height):
    """Translucent dark plate with an iron border and gold corner fleurons."""
    canvas = raster.Canvas(width, height, raster.rgba("#07050a", 214))
    iron, shadow, gold, bright = C("#4a3a55"), C("#1a1220"), C("#c9862e"), C("#f5c55c")
    canvas.rect(0, 0, width, 1, iron)
    canvas.rect(0, height - 1, width, 1, iron)
    canvas.rect(0, 0, 1, height, iron)
    canvas.rect(width - 1, 0, 1, height, iron)
    canvas.rect(2, 2, width - 4, 1, shadow)
    canvas.rect(2, height - 3, width - 4, 1, shadow)
    for cx, cy, sx, sy in ((0, 0, 1, 1), (width - 1, 0, -1, 1), (0, height - 1, 1, -1), (width - 1, height - 1, -1, -1)):
        for k in range(6):
            canvas.put(cx + sx * k, cy, gold)
            canvas.put(cx, cy + sy * k, gold)
        canvas.put(cx + sx * 2, cy + sy * 2, bright)
        canvas.put(cx + sx * 3, cy + sy * 2, gold)
        canvas.put(cx + sx * 2, cy + sy * 3, gold)
    return canvas.freeze()


def _strip(script, roster, card, x0, y):
    """The quest as a contribution-graph row: one square per day, lit in order."""
    days = sorted([*roster.entries, roster.boss], key=lambda entry: entry.date)
    first = card.start + card.fade + 0.15
    step = min(0.07, card.hold * 0.45 / max(1, len(days)))
    parts = []
    for i, entry in enumerate(days):
        x = x0 + i * (SQUARE + SQUARE_GAP)
        pop = smil.discrete("opacity", [(0.0, "0"), (first + i * step, "1")], script.duration)
        fill = TIER_COLORS[entry.tier]
        ring = ' stroke="#f5c55c" stroke-width="1"' if entry.tier == 5 else ""
        parts.append(f'<rect x="{x}.5" y="{y}.5" width="{SQUARE - 1}" height="{SQUARE - 1}" rx="1" fill="{fill}"{ring} opacity="0">{pop}</rect>')
    return "".join(parts)


def quest_complete(script, roster, book):
    """Epilogue tally: the quest's days as a contribution row, souls and the year."""
    card = _card(script, "quest-complete")
    if card is None:
        return ""
    days = len(roster.entries) + 1
    panel = book.image("quest-panel", _panel(PANEL_W, PANEL_H))
    title = book.image("quest-title", raster.scale(font.render("QUEST COMPLETE", font.GOLD), 2))
    stats = book.image("quest-stats", font.render(
        f"{days} DAYS · {roster.souls_total} SOULS · {roster.year_total} IN A YEAR", font.BONE))
    dawn = book.image("quest-dawn", font.render("A NEW QUEST AT DAWN", font.EMBER))
    strip_w = days * (SQUARE + SQUARE_GAP) - SQUARE_GAP
    x0 = round(layout.WIDTH / 2 - strip_w / 2)
    body = (
        f'<use href="#{panel.id}" x="{(layout.WIDTH - PANEL_W) // 2}" y="{PANEL_Y}"/>'
        f"{centered_use(title, PANEL_Y + 8)}"
        f"{_strip(script, roster, card, x0, PANEL_Y + 36)}"
        f"{centered_use(stats, PANEL_Y + 50)}"
        f"{centered_use(dawn, PANEL_Y + 66)}"
    )
    return _shown(card, script.duration, body)
