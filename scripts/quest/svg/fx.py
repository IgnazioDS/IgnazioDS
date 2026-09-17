"""Fight effects: cut marks and contact bursts on every blow, parry sparks,
ash and soul counts where monsters fall, and the wisps that carry their souls
to the counter.
"""

from functools import lru_cache

from .. import bestiary, layout
from ..art import effects, font, monsters, raster
from ..combat import WINDUP_LEAD
from ..sim import WISP_FLIGHT
from . import smil
from .actors import FLASH_HOLD, standing_y

MARK_TIME = 0.21
PARRY_AT = WINDUP_LEAD + 0.1


def _clip(sheet, animation):
    return f'<svg width="{sheet.frame_w}" height="{sheet.height}"><g>{animation}<use href="#{sheet.id}"/></g></svg>'


def _frames(sheet, t0, span, count, duration):
    track = smil.DiscreteTrack(0)
    track.cycle(t0, t0 + span, count / span, list(range(count)))
    return smil.translate([(t, -i * sheet.frame_w, 0) for t, i in track.events()], duration, calc="discrete")


@lru_cache(maxsize=None)
def _front(kind):
    """(front column, middle row) of a creature's guard stance, in frame pixels."""
    frame = monsters.art(kind).idle[0]
    opaque = [(x, y) for y in range(frame.height) for x in range(frame.width) if raster.alpha_of(frame.at(x, y))]
    rows = [y for _, y in opaque]
    return min(x for x, _ in opaque), (min(rows) + max(rows)) / 2


def contact(enc):
    """Where the knight's blade meets this foe on screen."""
    front_x, mid_y = _front(enc.kind)
    return bestiary.KINDS[enc.kind].engage_x + front_x + 8, standing_y(enc) + mid_y


def center(enc):
    """Screen point at the heart of a monster while it fights."""
    frame = monsters.art(enc.kind).frames[0]
    return bestiary.KINDS[enc.kind].engage_x + frame.width / 2, standing_y(enc) + frame.height * 0.55


def hit_marks(script, book):
    d = script.duration
    parts = []
    for enc in script.encounters:
        cx, cy = contact(enc)
        for hit, blow, heavy in zip(enc.hits, enc.blows, enc.heavy):
            frames = effects.hit_flash(blow, heavy)
            sheet = book.sheet(f"cut-{blow}-{'gold' if heavy else 'cold'}", frames)
            x, y = smil.num(cx - sheet.frame_w / 2), smil.num(cy - sheet.height / 2)
            parts.append(
                f'<g opacity="0" transform="translate({x} {y})">{smil.windows([(hit, hit + MARK_TIME)], d)}'
                f'{_clip(sheet, _frames(sheet, hit, MARK_TIME, len(frames), d))}</g>'
            )
    return "".join(parts)


def parry_sparks(script, book):
    moments = [a.t + PARRY_AT for enc in script.encounters for a in enc.attacks if a.outcome == "parry"]
    if not moments:
        return ""
    d = script.duration
    frames = effects.hit_flash("thrust", True)
    sheet = book.sheet("cut-thrust-gold", frames)
    x, y = layout.KNIGHT_X + 60 - sheet.frame_w // 2, layout.GROUND_Y - 54 - sheet.height // 2
    star = book.image("spark", effects.spark())
    parts = []
    for t in moments:
        parts.append(
            f'<g opacity="0" transform="translate({x} {y})">{smil.windows([(t, t + MARK_TIME)], d)}'
            f'{_clip(sheet, _frames(sheet, t, MARK_TIME, len(frames), d))}'
            f'<use href="#{star.id}" x="{sheet.frame_w // 2 - 7}" y="{sheet.height // 2 - 7}"/></g>'
        )
    return "".join(parts)


def death_effects(script, book):
    """Ash bursts and rising '+N' soul counts where each monster falls."""
    d = script.duration
    burst_frames = effects.ash_burst()
    burst = book.sheet("ash", burst_frames)
    parts = []
    for enc in script.encounters:
        cx, cy = center(enc)
        t0 = enc.death_t + FLASH_HOLD
        parts.append(
            f'<g opacity="0" transform="translate({smil.num(cx - burst.frame_w / 2)} {smil.num(cy - 20)})">'
            f'{smil.windows([(t0, t0 + 0.5)], d)}{_clip(burst, _frames(burst, t0, 0.5, len(burst_frames), d))}</g>'
        )
        label = book.image(f"gain-{enc.entry.count}", font.render(f"+{enc.entry.count}", font.SOUL))
        lx, ly = cx - label.width / 2, cy - 30
        rise = smil.translate([(t0, lx, ly), (t0 + 1.1, lx, ly - 12)], d)
        parts.append(
            f'<g opacity="0">{smil.windows([(t0, t0 + 1.1)], d)}'
            f'<g>{rise}<use href="#{label.id}"/></g></g>'
        )
    return "".join(parts)


def soul_wisps(script, book):
    """Each kill releases a wisp that arcs into the SOULS counter."""
    d = script.duration
    asset = book.image("wisp", effects.wisp())
    tx, ty = layout.SOULS_ANCHOR
    parts = []
    for enc in script.encounters:
        x0, y0 = center(enc)
        t0, t1 = enc.death_t + 0.12, enc.death_t + WISP_FLIGHT
        path = f"M{smil.num(x0)} {smil.num(y0)} Q{smil.num((x0 + tx) / 2)} {smil.num(min(y0, ty) - 30)} {tx} {ty}"
        parts.append(
            f'<g opacity="0">{smil.windows([(t0, t1)], d)}'
            f'<g>{smil.motion(path, t0, t1, d)}<use href="#{asset.id}" x="-5" y="-5"/></g></g>'
        )
    return "".join(parts)
