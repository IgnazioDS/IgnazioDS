"""Actors: the knight, monsters, and the effects of their fights."""

from .. import layout
from ..art import effects, font, knight, monsters
from ..sim import WISP_FLIGHT
from . import smil

MOVE_FPS, MENACE_FPS = 8, 3
ATTACK_HOLD, FLASH_HOLD = 0.32, 0.09


def _sheet_offsets(track_events, frame_w):
    return [(t, -index * frame_w, 0) for t, index in track_events]


def _clip(sheet, animation):
    return (
        f'<svg width="{sheet.frame_w}" height="{sheet.height}">'
        f'<use href="#{sheet.id}">{animation}</use></svg>'
    )


def knight_actor(script, book, dash=""):
    frames = knight.frames()
    names = layout.KNIGHT_FRAMES
    missing = [name for name in names if name not in frames]
    if missing:
        raise ValueError(f"knight art lacks frames: {missing}")
    sheet = book.sheet("knight", [frames[name] for name in names])
    index = {name: i for i, name in enumerate(names)}
    events = [(t, index[name]) for t, name in script.knight_frames]
    anim = smil.translate(_sheet_offsets(events, sheet.frame_w), script.duration, calc="discrete")
    y = layout.GROUND_Y - layout.KNIGHT_FEET
    return f'<g transform="translate({layout.KNIGHT_X} {y})"><g>{dash}{_clip(sheet, anim)}</g></g>'


def _monster_y(art, tier):
    return layout.GROUND_Y - art.feet_y - layout.FLYER_LIFT.get(tier, 0)


def monster_actors(script, book):
    arts = monsters.roster()
    d = script.duration
    parts = []
    for enc in script.encounters:
        tier = enc.entry.tier
        art = arts[tier]
        frames = (*art.move, *art.attack, art.hurt)
        sheet = book.sheet(f"monster-{art.name}", frames)
        windup_i, strike_i, hurt_i = len(art.move), len(art.move) + 1, len(art.move) + 2
        spawn = enc.path[0][0]
        track = smil.DiscreteTrack(0)
        moves = list(range(len(art.move)))
        track.cycle(spawn, enc.engage_t, MOVE_FPS, moves)
        track.cycle(enc.engage_t, enc.death_t + FLASH_HOLD, MENACE_FPS, moves)
        if enc.attack_t is not None:
            track.override(enc.attack_t, enc.attack_t + ATTACK_HOLD / 2, windup_i)
            track.override(enc.attack_t + ATTACK_HOLD / 2, enc.attack_t + ATTACK_HOLD, strike_i)
        for hit in enc.hits:
            track.override(hit, hit + FLASH_HOLD, hurt_i)
        frame_anim = smil.translate(_sheet_offsets(track.events(), sheet.frame_w), d, calc="discrete")
        y = _monster_y(art, tier)
        motion = smil.translate([(t, x, y) for t, x in enc.path], d)
        knock = smil.translate(
            [(0.0, 0, 0)] + [p for hit in enc.hits for p in ((hit, 3, 0), (hit + FLASH_HOLD, 0, 0))],
            d, calc="discrete",
        )
        parts.append(
            f'<g opacity="0">{smil.windows([(spawn, enc.death_t + FLASH_HOLD)], d)}'
            f'<g>{motion}<g>{knock}{_clip(sheet, frame_anim)}</g></g></g>'
        )
    return "".join(parts)


def _center(enc, arts, book):
    art = arts[enc.entry.tier]
    sheet = book.sheet(f"monster-{art.name}", (*art.move, *art.attack, art.hurt))
    x = layout.engage_x(enc.entry.tier) + sheet.frame_w / 2
    y = _monster_y(art, enc.entry.tier) + sheet.height * 0.55
    return x, y


def death_effects(script, book):
    """Ash bursts and rising '+N' soul counts where each monster falls."""
    d = script.duration
    arts = monsters.roster()
    burst_frames = effects.ash_burst()
    burst = book.sheet("ash", burst_frames)
    parts = []
    for enc in script.encounters:
        cx, cy = _center(enc, arts, book)
        t0 = enc.death_t + FLASH_HOLD
        track = smil.DiscreteTrack(0)
        track.cycle(t0, t0 + 0.5, 10, list(range(len(burst_frames))))
        anim = smil.translate(_sheet_offsets(track.events(), burst.frame_w), d, calc="discrete")
        parts.append(
            f'<g opacity="0" transform="translate({smil.num(cx - burst.frame_w / 2)} {smil.num(cy - 20)})">'
            f'{smil.windows([(t0, t0 + 0.5)], d)}{_clip(burst, anim)}</g>'
        )
        label = book.image(f"gain-{enc.entry.count}", font.render(f"+{enc.entry.count}", font.SOUL))
        lx, ly = cx - label.width / 2, cy - 30
        rise = smil.translate([(t0, lx, ly), (t0 + 1.1, lx, ly - 12)], d)
        parts.append(
            f'<g opacity="0">{smil.windows([(t0, t0 + 1.1)], d)}'
            f'<g>{rise}<use href="#{label.id}"/></g></g>'
        )
    return "".join(parts)


def parry_sparks(script, book):
    if not script.parries:
        return ""
    d = script.duration
    asset = book.image("spark", effects.spark())
    x, y = layout.KNIGHT_X + 58, layout.GROUND_Y - 52
    windows = [(t, t + 0.14) for t in script.parries]
    return (
        f'<g opacity="0" transform="translate({x} {y})">{smil.windows(windows, d)}'
        f'<use href="#{asset.id}"/></g>'
    )


def soul_wisps(script, book):
    """Each kill releases a wisp that arcs into the SOULS counter."""
    d = script.duration
    arts = monsters.roster()
    asset = book.image("wisp", effects.wisp())
    tx, ty = layout.SOULS_ANCHOR
    parts = []
    for enc in script.encounters:
        x0, y0 = _center(enc, arts, book)
        t0, t1 = enc.death_t + 0.12, enc.death_t + WISP_FLIGHT
        path = f"M{smil.num(x0)} {smil.num(y0)} Q{smil.num((x0 + tx) / 2)} {smil.num(min(y0, ty) - 30)} {tx} {ty}"
        parts.append(
            f'<g opacity="0">{smil.windows([(t0, t1)], d)}'
            f'<g>{smil.motion(path, t0, t1, d)}<use href="#{asset.id}" x="-5" y="-5"/></g></g>'
        )
    return "".join(parts)
