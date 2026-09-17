"""HUD and overlays: the knight's portrait and health, the souls counter, foe
nameplates, the quest's contribution strip, the wyrm's bar, fades and the
eleventh.dev footer.
"""

from .. import bestiary, layout
from ..art import effects, font
from ..art import hud as art
from . import smil
from .assets import centered_use
from .cards import BOSS_NAME, short_date

PORTRAIT = (4, 3)
HP_FRAME, HP_FRAME_W = (28, 10), 86
HP_X, HP_Y, HP_W, HP_H = 31, 12, 80, 6
SOULS_PLATE = (layout.WIDTH - 108, 4)
BOSS_BAR_W, BOSS_BAR_Y = 150, 22
PLATE_Y, PLATE_LOW_Y, PLATE_MARGIN = 4, 36, 3
STRIP_X, STRIP_Y, SQUARE, SQUARE_STEP = 8, layout.HEIGHT - 11, 5, 6
EMPTY_DAY = "#161b22"
HUD_FADE_IN = 0.6


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


def visibility(script):
    """Hidden over the prologue vista, in with chapter I, and out with the world in the final fade.

    The HUD is drawn above the black fade overlay, so it must fade itself or it
    would hang lit over black and blink out at the loop seam.
    """
    start, fade = script.prologue.end, script.epilogue.fade_t
    points = [(0.0, "0"), (start, "0"), (start + HUD_FADE_IN, "1"), (fade, "1"), (script.duration, "0")]
    return smil.linear("opacity", points, script.duration)


def fade_overlay(script):
    points = [(t, smil.num(o)) for t, o in script.fades]
    return (
        f'<rect width="{layout.WIDTH}" height="{layout.HEIGHT}" fill="#050308" opacity="0">'
        f'{smil.linear("opacity", points, script.duration)}</rect>'
    )


def health_bar(script, book):
    """The knight's portrait medallion beside an iron-framed health bar."""
    d = script.duration
    widths = [(t, smil.num(HP_W * hp)) for t, hp in script.health]
    anim = smil.linear("width", widths, d)
    portrait = book.image("hud-portrait", art.portrait())
    frame = book.image("hud-hp-frame", art.bar_frame(HP_FRAME_W))
    return (
        f'<use href="#{frame.id}" x="{HP_FRAME[0]}" y="{HP_FRAME[1]}"/>'
        f'<rect x="{HP_X}" y="{HP_Y}" width="{HP_W}" height="{HP_H}" fill="#8e1a2b">{anim}</rect>'
        f'<rect x="{HP_X}" y="{HP_Y}" width="{HP_W}" height="2" fill="#e0485c">{anim}</rect>'
        f'<use href="#{portrait.id}" x="{PORTRAIT[0]}" y="{PORTRAIT[1]}"/>'
    )


def souls_counter(script, roster, book):
    d = script.duration
    ax, ay = layout.SOULS_ANCHOR
    icon = book.image("wisp", effects.wisp())
    plate = book.image("hud-souls-plate", art.souls_plate())
    parts = [f'<use href="#{plate.id}" x="{SOULS_PLATE[0]}" y="{SOULS_PLATE[1]}"/>',
             f'<use href="#{icon.id}" x="{ax - 5}" y="{ay - 5}"/>']
    states = list(script.souls)
    for i, (t, value) in enumerate(states):
        end = states[i + 1][0] if i + 1 < len(states) else d
        label = book.image(f"souls-{value}", font.render(f"{value:04d}", font.SOUL))
        shown = smil.windows([(t, end)], d) if len(states) > 1 else ""
        base = "1" if i == 0 else "0"
        parts.append(
            f'<g opacity="{base}">{shown}<use href="#{label.id}" x="{ax + 8}" y="{ay - 5}"/></g>'
        )
    year = book.image("year", font.render(f"YEAR {roster.year_total}", font.BONE))
    parts.append(f'<use href="#{year.id}" x="{layout.WIDTH - 10 - year.width}" y="{SOULS_PLATE[1] + 16}" opacity="0.8"/>')
    return "".join(parts)


def nameplates(script, book):
    """Who the knight is fighting: the creature, its day, and that day's real contribution count."""
    d = script.duration
    foes = [(enc.entry, bestiary.KINDS[enc.kind].title, "elite" if enc.elite else "foe") for enc in script.encounters]
    foes.append((script.boss.entry, BOSS_NAME, "boss"))
    parts = []
    for (iso, start, end), (entry, title, style) in zip(date_windows(script), foes):
        if end <= start:
            continue
        plate = art.nameplate(title, short_date(iso), entry.count, entry.tier, style)
        asset = book.image(f"plate-{iso}", plate)
        x, y = plate_position(plate.width)
        parts.append(f'<g opacity="0">{smil.windows([(start, end)], d)}<use href="#{asset.id}" x="{x}" y="{y}"/></g>')
    return "".join(parts)


def plate_position(width):
    """Centred in the gap between the health frame and the souls plate, or on a second row if too wide."""
    left, right = HP_FRAME[0] + HP_FRAME_W + PLATE_MARGIN, SOULS_PLATE[0] - PLATE_MARGIN
    if width > right - left:
        return round((layout.WIDTH - width) / 2), PLATE_LOW_Y
    return min(max(round((layout.WIDTH - width) / 2), left), right - width), PLATE_Y


def quest_strip(script, roster, book):
    """The quest as a contribution-graph row: each day lights up in its green when its foe falls."""
    d = script.duration
    fallen = {enc.entry.date: enc.death_t for enc in script.encounters}
    fallen[script.boss.entry.date] = script.boss.death_t
    days = sorted([*roster.entries, roster.boss], key=lambda entry: entry.date)
    column = {entry.date: i for i, entry in enumerate(days)}
    parts = []
    for i, entry in enumerate(days):
        x = STRIP_X + i * SQUARE_STEP
        lit = smil.discrete("fill", [(0.0, EMPTY_DAY), (fallen[entry.date], art.TIER_COLORS[entry.tier])], d)
        parts.append(f'<rect x="{x}" y="{STRIP_Y}" width="{SQUARE}" height="{SQUARE}" rx="1" fill="{EMPTY_DAY}">{lit}</rect>')
    windows = date_windows(script)
    marks = [(start, STRIP_X + column[iso] * SQUARE_STEP - 1.5, STRIP_Y - 1.5) for iso, start, end in windows if end > start]
    if marks:
        hop = smil.translate([(t, x, y) for t, x, y in marks], d, calc="discrete")
        shown = smil.windows([(start, end) for _, start, end in windows if end > start], d)
        parts.append(f'<g opacity="0">{shown}<g>{hop}<rect width="{SQUARE + 3}" height="{SQUARE + 3}" rx="1.5" '
                     f'fill="none" stroke="#f5c55c" stroke-width="1" class="lf-pulse"/></g></g>')
    return "".join(parts)


def boss_bar(script, book):
    d = script.duration
    boss = script.boss
    frame = book.image("hud-boss-frame", art.bar_frame(BOSS_BAR_W + 6, 9))
    total = max(1, len(boss.hits))
    widths = [(0.0, BOSS_BAR_W), (boss.land_t, BOSS_BAR_W)]
    for i, hit in enumerate(boss.hits, start=1):
        widths += [(hit, BOSS_BAR_W * (1 - (i - 1) / total)), (hit + 0.12, BOSS_BAR_W * (1 - i / total))]
    anim = smil.linear("width", [(t, smil.num(w)) for t, w in widths], d)
    x = layout.WIDTH / 2 - BOSS_BAR_W / 2
    return (
        f'<g opacity="0">{smil.windows([(boss.land_t, boss.death_t + 0.6)], d)}'
        f'{centered_use(frame, BOSS_BAR_Y)}'
        f'<rect x="{smil.num(x)}" y="{BOSS_BAR_Y + 2}" width="{BOSS_BAR_W}" height="5" fill="#b8402a">{anim}</rect>'
        f'<rect x="{smil.num(x)}" y="{BOSS_BAR_Y + 2}" width="{BOSS_BAR_W}" height="1" fill="#ff8a5a">{anim}</rect></g>'
    )


def footer(book):
    label = book.image("footer", font.render("ELEVENTH.DEV", font.BONE))
    x = layout.WIDTH - 6 - label.width
    y = layout.HEIGHT - label.height - 3
    return f'<a href="https://eleventh.dev"><use href="#{label.id}" x="{x}" y="{y}" opacity="0.75"/></a>'
