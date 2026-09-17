"""Actors: the knight and the monsters (charging, squaring up, striking,
dying, and the remains they leave).
"""

from functools import lru_cache

from .. import bestiary, layout
from ..art import knight, monsters, raster, sprite
from ..combat import WINDUP_LEAD
from . import smil

MOVE_FPS, MENACE_FPS, DEATH_FPS = 8, 3, 9
ATTACK_HOLD, FLASH_HOLD = 0.32, 0.09
REMAINS_FADE = 0.45
LUNGE = 10
AURA_INNER, AURA_OUTER = raster.rgba("#ff3a52", 220), raster.rgba("#b0102a", 110)


def _sheet_offsets(track_events, frame_w):
    return [(t, -index * frame_w, 0) for t, index in track_events]


def _clip(sheet, animation, extra=""):
    return (
        f'<svg width="{sheet.frame_w}" height="{sheet.height}">'
        f'<g>{animation}{extra}<use href="#{sheet.id}"/></g></svg>'
    )


def knight_actor(script, book):
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
    moves = ""
    if any(dx or dy for _, dx, dy in script.knight_moves):
        moves = smil.translate(list(script.knight_moves), script.duration)
    return f'<g transform="translate({layout.KNIGHT_X} {y})"><g>{moves}{_clip(sheet, anim)}</g></g>'


def standing_y(enc):
    """Frame top while alive (flyers hover `lift` px higher)."""
    art = monsters.art(enc.kind)
    return layout.GROUND_Y - art.feet_y - bestiary.KINDS[enc.kind].lift


def _fall_end(enc):
    art = monsters.art(enc.kind)
    return enc.death_t + FLASH_HOLD + (len(art.death) - 1) / DEATH_FPS


def _frame_track(enc, art):
    track = smil.DiscreteTrack(0)
    moves = list(range(len(art.move)))
    stance = [art.index("idle", k) for k in range(len(art.idle))]
    spawn, dying = enc.path[0][0], enc.death_t + FLASH_HOLD
    track.cycle(spawn, enc.engage_t, MOVE_FPS, moves)
    track.cycle(enc.engage_t, dying, MENACE_FPS, stance)
    for attack in enc.attacks:
        land = attack.t + WINDUP_LEAD - 0.02
        track.override(attack.t, land, art.index("windup"))
        track.override(land, attack.t + ATTACK_HOLD, art.index("strike"))
    for hit in enc.hits:
        track.override(hit, hit + FLASH_HOLD, art.index("hurt"))
    gone = enc.remains[-1][0]
    last = len(art.death) - 1
    for k in range(len(art.death)):
        start = dying + k / DEATH_FPS
        end = gone if k == last else dying + (k + 1) / DEATH_FPS
        if start < end:
            track.override(start, end, art.index("death", k))
    return track


def _path_points(enc):
    """(t, x, y): the charge in, then the body falling (flyers) and scrolling away."""
    y_alive = standing_y(enc)
    y_dead = layout.GROUND_Y - monsters.art(enc.kind).feet_y
    points = [(t, x, y_alive) for t, x in enc.path]
    fall_end = _fall_end(enc)
    remains = list(enc.remains)
    times = sorted({t for t, _ in remains} | ({fall_end} if fall_end < remains[-1][0] else set()))
    for t in times:
        x = _lerp(remains, t)
        k = min(1.0, max(0.0, (t - enc.death_t) / max(1e-6, fall_end - enc.death_t)))
        points.append((t, x, y_alive + (y_dead - y_alive) * k * k))
    return points


def _lerp(path, t):
    if t <= path[0][0]:
        return path[0][1]
    for (t0, x0), (t1, x1) in zip(path, path[1:]):
        if t0 <= t <= t1:
            return x0 if t1 - t0 < 1e-9 else x0 + (x1 - x0) * (t - t0) / (t1 - t0)
    return path[-1][1]


@lru_cache(maxsize=None)
def _aura_frames(kind):
    return tuple(sprite.aura(frame, AURA_INNER, AURA_OUTER) for frame in monsters.art(kind).frames)


def monster_actors(script, book):
    d = script.duration
    parts = []
    for enc in script.encounters:
        art = monsters.art(enc.kind)
        sheet = book.sheet(f"monster-{art.name}", art.frames)
        spawn, gone = enc.path[0][0], enc.remains[-1][0]
        frames = smil.translate(_sheet_offsets(_frame_track(enc, art).events(), sheet.frame_w), d, calc="discrete")
        motion = smil.translate(_path_points(enc), d)
        lunges = [p for a in enc.attacks for p in ((a.t + WINDUP_LEAD - 0.02, -LUNGE, 0), (a.t + ATTACK_HOLD, 0, 0))]
        recoils = [p for hit in enc.hits for p in ((hit, 3, 0), (hit + FLASH_HOLD, 0, 0))]
        knock = smil.translate([(0.0, 0, 0)] + lunges + recoils, d, calc="discrete")
        fade = smil.linear("opacity", [(0.0, "1"), (max(spawn, gone - REMAINS_FADE), "1"), (gone, "0")], d)
        aura = ""
        if enc.elite:
            glow = book.sheet(f"aura-{art.name}", _aura_frames(enc.kind))
            aura = (f'<g opacity="0">{smil.windows([(spawn, enc.death_t + FLASH_HOLD)], d)}'
                    f'<g class="lf-pulse"><use href="#{glow.id}"/></g></g>')
        parts.append(
            f'<g opacity="0">{smil.windows([(spawn, gone)], d)}<g>{fade}'
            f'<g>{motion}<g>{knock}{_clip(sheet, frames, aura)}</g></g></g></g>'
        )
    return "".join(parts)
