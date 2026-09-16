"""The boss set piece: the Ashen Wyrm's descent, roar, fire breath, wounds and
death; the knight's dashes; screen shake; and the wyrm's great soul.
"""

from .. import layout
from ..art import dragon, effects, font
from ..sim import BOSS_WISP_FLIGHT
from . import smil

HOVER = (160, 30)            # dragon frame top-left while fighting
ENTRY = (430, -150)          # off-screen start of the descent
HOVER_FPS = 8
DASH = 38                    # how far the knight lunges for each blow
LUNGE_LEAD, LUNGE_TAIL = 0.22, 0.5   # lunge window around each blow
DASH_IN, DASH_OUT = 0.12, 0.18       # time to close in / fall back


def _sheet(book):
    frames = dragon.frames()
    sheet = book.sheet("wyrm", [frames[name] for name in dragon.FRAME_NAMES])
    return sheet, {name: i for i, name in enumerate(dragon.FRAME_NAMES)}


def wyrm(script, book):
    boss = script.boss
    d = script.duration
    sheet, index = _sheet(book)
    hover = [index[f"hover{i}"] for i in range(4)]
    end = boss.death_t + 1.8

    track = smil.DiscreteTrack(index["hover0"])
    track.cycle(boss.enter_t, end, HOVER_FPS, hover)
    track.override(boss.land_t, boss.land_t + 0.7, index["roar"])
    for start, stop in boss.breaths:
        track.override(start - 0.25, start, index["breath0"])
        track.cycle(start, stop, 12, [index["breath1"], index["breath2"]])
    for hit in boss.hits[:-1]:
        track.override(hit, hit + 0.1, index["hurt"])
    track.override(boss.death_t, boss.death_t + 0.1, index["hurt"])
    track.override(boss.death_t + 0.1, boss.death_t + 0.45, index["death0"])
    track.override(boss.death_t + 0.45, end, index["death1"])
    frames = smil.translate([(t, -i * sheet.frame_w, 0) for t, i in track.events()], d, calc="discrete")

    hx, hy = HOVER
    motion_points = [(0.0, *ENTRY), (boss.enter_t, *ENTRY), (boss.land_t, hx, hy)]
    for hit in boss.hits[:-1]:
        motion_points += [(hit, hx, hy), (hit + 0.08, hx + 6, hy - 3), (hit + 0.3, hx, hy)]
    motion_points += [(boss.death_t + 0.45, hx + 4, hy), (end, hx + 10, hy + 70)]
    motion = smil.translate(motion_points, d)
    fade = smil.linear("opacity", [(0.0, "1"), (boss.death_t + 0.9, "1"), (end, "0")], d)
    return (
        f'<g opacity="0">{smil.windows([(boss.enter_t, end)], d)}'
        f'<g>{motion}<g>{fade}<svg width="{sheet.frame_w}" height="{sheet.height}">'
        f'<use href="#{sheet.id}">{frames}</use></svg></g></g></g>'
    )


def fire(script, book, gradients):
    boss = script.boss
    if not boss.breaths:
        return ""
    d = script.duration
    frames = effects.fire_breath()
    sheet = book.sheet("fire", frames)
    mouth = dragon.mouth("breath1")
    x = HOVER[0] + mouth[0] - effects.FIRE_MOUTH[0]
    y = HOVER[1] + mouth[1] - effects.FIRE_MOUTH[1]
    track = smil.DiscreteTrack(0)
    for start, stop in boss.breaths:
        track.cycle(start, stop, 14, list(range(len(frames))))
    anim = smil.translate([(t, -i * sheet.frame_w, 0) for t, i in track.events()], d, calc="discrete")
    glow = gradients.setdefault("#ff8a30", f"lg{len(gradients)}")
    windows = smil.windows(list(boss.breaths), d)
    return (
        f'<g opacity="0">{windows}'
        f'<g style="mix-blend-mode:screen"><ellipse cx="{layout.KNIGHT_X + 50}" cy="{layout.GROUND_Y - 30}" '
        f'rx="90" ry="60" fill="url(#{glow})" opacity="0.55"/></g>'
        f'<g transform="translate({smil.num(x)} {smil.num(y)})"><svg width="{sheet.frame_w}" height="{sheet.height}">'
        f'<use href="#{sheet.id}">{anim}</use></svg></g></g>'
    )


def embers(script, book):
    boss = script.boss
    d = script.duration
    frames = effects.ember_burst()
    sheet = book.sheet("wyrm-embers", frames)
    t0 = boss.death_t + 0.5
    track = smil.DiscreteTrack(0)
    track.cycle(t0, t0 + 0.9, 7, list(range(len(frames))))
    anim = smil.translate([(t, -i * sheet.frame_w, 0) for t, i in track.events()], d, calc="discrete")
    x, y = HOVER[0] + 70, HOVER[1] + 70
    label = book.image(f"gain-{boss.entry.count}", font.render(f"+{boss.entry.count}", font.SOUL))
    rise = smil.translate([(t0, x + 40, y + 20), (t0 + 1.6, x + 40, y)], d)
    return (
        f'<g opacity="0" transform="translate({x} {y})">{smil.windows([(t0, t0 + 0.9)], d)}'
        f'<svg width="{sheet.frame_w}" height="{sheet.height}"><use href="#{sheet.id}">{anim}</use></svg></g>'
        f'<g opacity="0">{smil.windows([(t0, t0 + 1.6)], d)}<g>{rise}<use href="#{label.id}"/></g></g>'
    )


def soul(script, book):
    boss = script.boss
    d = script.duration
    asset = book.image("wisp", effects.wisp())
    x0, y0 = HOVER[0] + 110, HOVER[1] + 100
    tx, ty = layout.SOULS_ANCHOR
    t0, t1 = boss.death_t + 0.2, boss.death_t + BOSS_WISP_FLIGHT
    path = f"M{x0} {y0} Q{(x0 + tx) // 2} {min(y0, ty) - 40} {tx} {ty}"
    return (
        f'<g opacity="0">{smil.windows([(t0, t1)], d)}<g>{smil.motion(path, t0, t1, d)}'
        f'<g transform="scale(2)"><use href="#{asset.id}" x="-5" y="-5"/></g></g></g>'
    )


def dash_points(script):
    """(t, x) keyframes of the knight's dash; chained blows share one lunge."""
    windows = []
    for hit in script.boss.hits:
        start, end = hit - LUNGE_LEAD, hit + LUNGE_TAIL
        if windows and start <= windows[-1][1]:
            windows[-1] = (windows[-1][0], end)
        else:
            windows.append((start, end))
    points = [(0.0, 0.0)]
    for start, end in windows:
        points += [(start, 0.0), (start + DASH_IN, float(DASH)), (end - DASH_OUT, float(DASH)), (end, 0.0)]
    return points


def knight_dash(script):
    """Translate animation for the knight group: a forward dash into each blow on the wyrm."""
    return smil.translate([(t, x, 0) for t, x in dash_points(script)], script.duration)


def shake(script):
    """Screen shake when the wyrm lands, breathes fire, and dies."""
    boss = script.boss
    moments = [(boss.land_t, 3)] + [(start, 1) for start, _ in boss.breaths] + [(boss.death_t, 3)]
    points = [(0.0, 0, 0)]
    for t, amp in moments:
        for k, (dx, dy) in enumerate(((amp, -1), (-amp, 1), (amp - 1, 1), (-1, -1), (0, 0))):
            points.append((t + k * 0.05, dx, dy))
    return smil.translate(points, script.duration, calc="discrete")
