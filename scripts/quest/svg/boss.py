"""The boss set piece: the Ashen Wyrm's descent, fire, flight and swoop, its
wounds and the knight's killing plunge; the crash, the flash, screen shakes,
and the wyrm's great soul.
"""

from .. import layout
from ..art import dragon, effects, font
from ..wyrm import BOSS_WISP_FLIGHT, CRASH_DELAY, RISE_TIME, ROAR_HOLD, SWOOP_TIME
from . import smil

HOVER = (160, 30)            # dragon frame top-left while fighting
ENTRY = (430, -150)          # off-screen start of every descent
HOVER_FPS, BEAT_FPS = 8, 10
CORPSE_TIME, CORPSE_FADE = 3.0, 0.8
OFF_LEFT, OFF_HIGH = -260, -400


def _sheet(book):
    frames = dragon.frames()
    sheet = book.sheet("wyrm", [frames[name] for name in dragon.FRAME_NAMES])
    return sheet, {name: i for i, name in enumerate(dragon.FRAME_NAMES)}


def _frame_track(boss, index):
    end = boss.death_t + CORPSE_TIME
    hover = [index[f"hover{i}"] for i in range(4)]
    track = smil.DiscreteTrack(index["hover0"])
    track.cycle(boss.enter_t, end, HOVER_FPS, hover)
    track.override(boss.land_t, boss.land_t + ROAR_HOLD, index["roar"])
    for start, stop in boss.breaths:
        track.override(start - 0.25, start, index["breath0"])
        track.cycle(start, stop, 12, [index["breath1"], index["breath2"]])
    for flight in boss.flights:
        track.cycle(flight.takeoff, flight.takeoff + RISE_TIME, BEAT_FPS, [index["hover0"], index["hover2"]])
        track.cycle(flight.dive, flight.dive + SWOOP_TIME, BEAT_FPS, [index["dive0"], index["dive1"]])
        track.override(flight.land, flight.land + ROAR_HOLD, index["roar"])
    for hit in boss.hits[:-1]:
        track.override(hit, hit + 0.1, index["hurt"])
    track.override(boss.death_t - 0.5, boss.death_t, index["roar"])
    track.override(boss.death_t, boss.death_t + 0.12, index["hurt"])
    track.override(boss.death_t + 0.12, boss.death_t + 0.45, index["death0"])
    track.override(boss.death_t + 0.45, end, index["death1"])
    return track


def _flight_points(flight):
    hx, hy = HOVER
    return [
        (flight.takeoff, hx, hy), (flight.takeoff + 0.25, hx + 10, hy + 8),
        (flight.takeoff + RISE_TIME, hx + 170, -210),
        (flight.takeoff + RISE_TIME + 0.05, 520, -210), (flight.dive - 0.02, 520, 70), (flight.dive, 430, 70),
        (flight.pass_t, 60, 96), (flight.dive + SWOOP_TIME, OFF_LEFT, 70),
        (flight.dive + SWOOP_TIME + 0.02, OFF_LEFT, OFF_HIGH), (flight.back - 0.04, ENTRY[0], OFF_HIGH),
        (flight.back, *ENTRY), (flight.land, hx, hy),
    ]


def _motion_points(boss):
    hx, hy = HOVER
    points = [(0.0, *ENTRY), (boss.enter_t, *ENTRY), (boss.land_t, hx, hy)]
    for flight in boss.flights:
        points += _flight_points(flight)
    for hit in boss.hits[:-1]:
        points += [(hit, hx, hy), (hit + 0.08, hx + 6, hy - 3), (hit + 0.3, hx, hy)]
    d = boss.death_t
    points += [(d, hx, hy), (d + 0.12, hx + 8, hy + 5), (d + 0.45, hx + 4, hy + 2), (d + CRASH_DELAY, hx + 10, hy + 70)]
    return sorted(points, key=lambda p: p[0])


def wyrm(script, book):
    boss = script.boss
    d = script.duration
    sheet, index = _sheet(book)
    end = boss.death_t + CORPSE_TIME
    frames = smil.translate([(t, -i * sheet.frame_w, 0) for t, i in _frame_track(boss, index).events()], d, calc="discrete")
    motion = smil.translate(_motion_points(boss), d)
    fade = smil.linear("opacity", [(0.0, "1"), (end - CORPSE_FADE, "1"), (end, "0")], d)
    return (
        f'<g opacity="0">{smil.windows([(boss.enter_t, end)], d)}'
        f'<g>{motion}<g>{fade}<svg width="{sheet.frame_w}" height="{sheet.height}">'
        f'<g>{frames}<use href="#{sheet.id}"/></g></svg></g></g></g>'
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
        f'<g>{anim}<use href="#{sheet.id}"/></g></svg></g></g>'
    )


def _burst(sheet, count, t0, span, x, y, duration):
    track = smil.DiscreteTrack(0)
    track.cycle(t0, t0 + span, count / span, list(range(count)))
    anim = smil.translate([(t, -i * sheet.frame_w, 0) for t, i in track.events()], duration, calc="discrete")
    return (
        f'<g opacity="0" transform="translate({smil.num(x)} {smil.num(y)})">{smil.windows([(t0, t0 + span)], duration)}'
        f'<svg width="{sheet.frame_w}" height="{sheet.height}"><g>{anim}<use href="#{sheet.id}"/></g></svg></g>'
    )


def embers(script, book):
    """Embers scatter from the wound, the wyrm's count rises, and dust rolls out when it crashes."""
    boss = script.boss
    d = script.duration
    ember_frames = effects.ember_burst()
    ember_sheet = book.sheet("wyrm-embers", ember_frames)
    t0 = boss.death_t + 0.05
    x, y = HOVER[0] + 20, HOVER[1] + 50
    dust_frames = effects.dust_cloud()
    dust = book.sheet("crash-dust", dust_frames)
    crash = boss.death_t + CRASH_DELAY
    label = book.image(f"gain-{boss.entry.count}", font.render(f"+{boss.entry.count}", font.SOUL))
    rise = smil.translate([(t0, x + 40, y + 20), (t0 + 1.6, x + 40, y)], d)
    return (
        _burst(ember_sheet, len(ember_frames), t0, 0.9, x, y, d)
        + _burst(dust, len(dust_frames), crash - 0.05, 0.8, HOVER[0] + 112 - dust.frame_w / 2, layout.GROUND_Y - dust.height + 6, d)
        + f'<g opacity="0">{smil.windows([(t0, t0 + 1.6)], d)}<g>{rise}<use href="#{label.id}"/></g></g>'
    )


def marks(script, book):
    """Cut marks on the wyrm for every blow; the plunge's gold mark where the blade goes in."""
    boss = script.boss
    d = script.duration
    parts = []
    for hit, blow in zip(boss.hits, boss.blows):
        plunge = blow == "plunge"
        frames = effects.hit_flash(blow, plunge)
        sheet = book.sheet(f"cut-{blow}-{'gold' if plunge else 'cold'}", frames)
        cx, cy = (222, 126) if plunge else (214, 146)
        parts.append(_burst(sheet, len(frames), hit, 0.24 if plunge else 0.21, cx - sheet.frame_w / 2, cy - sheet.height / 2, d))
    return "".join(parts)


def flash(script):
    """The screen whitens for an instant as the blade goes in."""
    t = script.boss.death_t
    anim = smil.linear("opacity", [(0.0, "0"), (t, "0"), (t + 0.03, "0.75"), (t + 0.2, "0")], script.duration)
    return f'<rect width="{layout.WIDTH}" height="{layout.HEIGHT}" fill="#fff4e0" opacity="0">{anim}</rect>'


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


def shake(script):
    """Screen shake for every crushing moment the simulation recorded."""
    points = [(0.0, 0, 0)]
    for t, amp in sorted(script.shakes):
        for k, (dx, dy) in enumerate(((amp, -1), (-amp, 1), (amp - 1, 1), (-1, -1), (0, 0))):
            points.append((t + k * 0.05, dx, dy))
    return smil.translate(points, script.duration, calc="discrete")
