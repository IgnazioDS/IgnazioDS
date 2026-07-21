"""Render a GameScript as a self-contained, infinitely looping animated SVG.

Every animation is a SMIL timeline with the same duration and
repeatCount="indefinite", so the whole game loops seamlessly. No JS —
GitHub serves README images through camo, which strips scripts but keeps
declarative animation.
"""

from . import sim, sprites

SCALE = 2
VIEW_W, VIEW_H = sim.WIDTH * SCALE, sim.HEIGHT * SCALE

BG = "#010409"
BORDER = "#30363d"
LABEL = "#7d8590"
VALUE = "#e6edf3"
WHITE = "#f0f6fc"
CANNON_COLOR = "#7ee787"
SHIELD_COLOR = "#2ea043"
UFO_COLOR = "#ff7b72"
GROUND = "#238636"
GHOST = "#21262d"
GREENS = ("#0e4429", "#006d32", "#26a641", "#39d353")

FONT_PX = 2
MAX_NOTCH_DEPTH = 3


def _f(x):
    return f"{x:.4f}".rstrip("0").rstrip(".")


def _opacity_window(t0, t1, dur, start_visible=False):
    if start_visible:
        values, times = "1;0", f"0;{_f(t1 / dur)}"
    else:
        values, times = "0;1;0", f"0;{_f(t0 / dur)};{_f(t1 / dur)}"
    return (
        f'<animate attributeName="opacity" values="{values}" keyTimes="{times}" '
        f'calcMode="discrete" dur="{_f(dur)}s" repeatCount="indefinite"/>'
    )


def _blink_windows(t0, t1, period, dur):
    """Opacity flicker between t0..t1 (visible/hidden alternating)."""
    values, times, t, on = ["0"], ["0"], t0, True
    while t < t1:
        values.append("1" if on else "0")
        times.append(_f(t / dur))
        on, t = not on, t + period
    values.append("0")
    times.append(_f(t1 / dur))
    return (
        f'<animate attributeName="opacity" values="{";".join(values)}" '
        f'keyTimes="{";".join(times)}" calcMode="discrete" '
        f'dur="{_f(dur)}s" repeatCount="indefinite"/>'
    )


def _translate_anim(points, dur, calc="linear"):
    """points: [(t, x, y)] -> animateTransform. Must span t=0..dur for linear."""
    values = ";".join(f"{_f(x)} {_f(y)}" for _, x, y in points)
    times = ";".join(_f(min(t / dur, 1.0)) for t, _, _ in points)
    return (
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="{values}" keyTimes="{times}" calcMode="{calc}" '
        f'dur="{_f(dur)}s" repeatCount="indefinite"/>'
    )


def _defs():
    inv = [
        ("sqA", sprites.SQUID_A), ("sqB", sprites.SQUID_B),
        ("crA", sprites.CRAB_A), ("crB", sprites.CRAB_B),
        ("ocA", sprites.OCTO_A), ("ocB", sprites.OCTO_B),
        ("cannon", sprites.CANNON), ("ufo", sprites.UFO),
        ("boom", sprites.BOOM), ("shield", sprites.SHIELD),
    ]
    parts = [f'<g id="{gid}">{sprites.sprite_rects(bm)}</g>' for gid, bm in inv]
    parts += [
        f'<g id="d{n}">{sprites.text_rects(str(n), FONT_PX)}</g>' for n in range(10)
    ]
    return f"<defs>{''.join(parts)}</defs>"


def _style():
    return (
        "<style>"
        ".fA{animation:fA 1s steps(1) infinite}"
        ".fB{animation:fB 1s steps(1) infinite}"
        "@keyframes fA{0%,49%{opacity:1}50%,100%{opacity:0}}"
        "@keyframes fB{0%,49%{opacity:0}50%,100%{opacity:1}}"
        "</style>"
    )


def _invader_sprite(row):
    frame_a, _, _ = sprites.INVADER_ROWS[row]
    names = {id(sprites.SQUID_A): ("sqA", "sqB"), id(sprites.CRAB_A): ("crA", "crB"),
             id(sprites.OCTO_A): ("ocA", "ocB")}
    return names[id(frame_a)]


def _invader_color(count, thresholds):
    if count <= 0:
        return GHOST
    level = sum(1 for t in thresholds if count >= t)
    return GREENS[min(level, len(GREENS) - 1)]


def _formation(script, day_counts, thresholds):
    kills_by_idx = {k.invader: k for k in script.kills}
    cells = []
    for idx, count in enumerate(day_counts):
        row, col = divmod(idx, sim.COLS)
        ref_a, ref_b = _invader_sprite(row)
        width, _ = sprites.sprite_size(sprites.INVADER_ROWS[row][0])
        x = sim.FORM_X + col * sim.COL_SPACING + (sim.CELL_W - width) / 2
        y = sim.slot_y(row)
        kill = kills_by_idx[idx]
        die = _opacity_window(0, kill.t, script.duration, start_visible=True)
        color = _invader_color(count, thresholds)
        cells.append(
            f'<g transform="translate({_f(x)} {_f(y)})" fill="{color}">'
            f'<use href="#{ref_a}" class="fA"/><use href="#{ref_b}" class="fB"/>'
            f"{die}</g>"
        )
        boom_x = sim.slot_center_x(col) - 5.5
        cells.append(
            f'<g transform="translate({_f(boom_x)} {_f(y)})" fill="{WHITE}" opacity="0">'
            f'<use href="#boom"/>'
            f"{_opacity_window(kill.t, kill.t + 0.28, script.duration)}</g>"
        )
    march = _translate_anim(
        [(t, ox, oy) for t, ox, oy in script.march], script.duration, calc="discrete"
    )
    return f'<g>{march}{"".join(cells)}</g>'


def _cannon(script):
    death = script.cannon_death
    path = [(t, x, sim.CANNON_Y) for t, x in script.cannon_path]
    move = _translate_anim(path, script.duration)
    hide = ""
    boom = ""
    if death:
        hide = _opacity_window(death["t"], death["t_respawn"], script.duration)
        hide = hide.replace('values="0;1;0"', 'values="1;0;1"')
        boom = (
            f'<g fill="{WHITE}" opacity="0">'
            f'<use href="#boom" x="-5.5" y="0"/>'
            f"{_blink_windows(death['t'], death['t'] + 1.0, 0.14, script.duration)}"
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="{_f(death["x"])} {sim.CANNON_Y}" dur="{_f(script.duration)}s" '
            f'repeatCount="indefinite"/></g>'
        )
    body = (
        f'<g fill="{CANNON_COLOR}">{move}'
        f'<g><use href="#cannon" x="-6.5" y="0"/>{hide}</g></g>'
    )
    return body + boom


def _bullets(script):
    parts = []
    for shot in script.shots:
        pts = [
            (0, shot.x, sim.BULLET_START_Y),
            (shot.t_fire, shot.x, sim.BULLET_START_Y),
            (shot.t_impact, shot.x, shot.y_impact),
            (script.duration, shot.x, shot.y_impact),
        ]
        parts.append(
            f'<g opacity="0"><rect x="-0.75" y="0" width="1.5" height="5" fill="{WHITE}"/>'
            f"{_translate_anim(pts, script.duration)}"
            f"{_opacity_window(shot.t_fire, shot.t_impact, script.duration)}</g>"
        )
    return "".join(parts)


def _bombs(script):
    parts = []
    for bomb in script.bombs:
        pts = [
            (0, bomb.x, bomb.y_start),
            (bomb.t_drop, bomb.x, bomb.y_start),
            (bomb.t_land, bomb.x, bomb.y_land),
            (script.duration, bomb.x, bomb.y_land),
        ]
        parts.append(
            f'<g opacity="0"><rect x="-1" y="0" width="2" height="5" fill="{WHITE}"/>'
            f"{_translate_anim(pts, script.duration)}"
            f"{_opacity_window(bomb.t_drop, bomb.t_land, script.duration)}</g>"
        )
        is_death_bomb = script.cannon_death and abs(bomb.t_land - script.cannon_death["t"]) < 1e-9
        if not is_death_bomb:
            parts.append(
                f'<g opacity="0" fill="{WHITE}">'
                f'<rect x="{_f(bomb.x - 2)}" y="{_f(bomb.y_land + 2)}" width="4" height="2"/>'
                f"{_opacity_window(bomb.t_land, bomb.t_land + 0.2, script.duration)}</g>"
            )
    return "".join(parts)


def _shields(script):
    parts = []
    for i, cx in enumerate(sim.SHIELD_CENTERS):
        parts.append(
            f'<g fill="{SHIELD_COLOR}" transform="translate({cx - sim.SHIELD_HALF_W} '
            f'{sim.SHIELD_TOP})"><use href="#shield"/></g>'
        )
    for notch in script.notches:
        if notch.depth > MAX_NOTCH_DEPTH:
            continue
        height = 5
        if notch.from_top:
            y = sim.SHIELD_TOP + (notch.depth - 1) * height
        else:
            y = sim.SHIELD_BOTTOM - notch.depth * height
        parts.append(
            f'<g opacity="0"><rect x="{_f(notch.x - 2)}" y="{_f(y)}" width="4" '
            f'height="{height}" fill="{BG}"/>'
            f'<animate attributeName="opacity" values="0;1" '
            f'keyTimes="0;{_f(notch.t / script.duration)}" calcMode="discrete" '
            f'dur="{_f(script.duration)}s" repeatCount="indefinite"/></g>'
        )
    return "".join(parts)


def _ufo(script):
    ufo = script.ufo
    if not ufo:
        return ""
    t_enter, t_die, x_die = ufo["t_enter"], ufo["t_die"], ufo["x_die"]
    pts = [
        (0, -20, sim.UFO_Y),
        (t_enter, -20, sim.UFO_Y),
        (t_die, x_die - 8, sim.UFO_Y),
        (script.duration, x_die - 8, sim.UFO_Y),
    ]
    saucer = (
        f'<g opacity="0" fill="{UFO_COLOR}"><use href="#ufo"/>'
        f"{_translate_anim(pts, script.duration)}"
        f"{_opacity_window(t_enter, t_die, script.duration)}</g>"
    )
    boom = (
        f'<g opacity="0" fill="{UFO_COLOR}">'
        f'<use href="#boom" x="{_f(x_die - 5.5)}" y="{_f(sim.UFO_Y)}"/>'
        f"{_opacity_window(t_die, t_die + 0.35, script.duration)}</g>"
    )
    bonus = (
        f'<g opacity="0" fill="{UFO_COLOR}" '
        f'transform="translate({_f(x_die - 8)} {sim.UFO_Y + 12})">'
        f"{sprites.text_rects(f'+{sim.UFO_POINTS}', 1.5)}"
        f"{_opacity_window(t_die + 0.3, t_die + 1.5, script.duration)}</g>"
    )
    return saucer + boom + bonus


def _text(x, y, content, color, px=FONT_PX):
    return (
        f'<g fill="{color}" transform="translate({_f(x)} {_f(y)})">'
        f"{sprites.text_rects(content, px)}</g>"
    )


def _score_counter(script, x, y):
    width = max(4, len(str(script.score_states[-1][1])))
    parts = []
    states = list(script.score_states)
    for i, (t, value) in enumerate(states):
        t_end = states[i + 1][0] if i + 1 < len(states) else script.duration
        digits = str(value).zfill(width)
        uses = "".join(
            f'<use href="#d{d}" x="{n * 4 * FONT_PX}"/>' for n, d in enumerate(digits)
        )
        window = (
            _opacity_window(0, t_end, script.duration, start_visible=True)
            if i == 0
            else _opacity_window(t, t_end, script.duration)
        )
        opacity = "1" if i == 0 else "0"
        parts.append(f'<g opacity="{opacity}">{uses}{window}</g>')
    return (
        f'<g fill="{VALUE}" transform="translate({_f(x)} {_f(y)})">{"".join(parts)}</g>'
    )


def _hud(script, hi_score, wave):
    hi = str(hi_score)
    center = sim.WIDTH / 2
    parts = [
        _text(10, 6, "SCORE", LABEL),
        _score_counter(script, 10, 19),
        _text(center - sprites.text_width("HI-SCORE", FONT_PX) / 2, 6, "HI-SCORE", LABEL),
        _text(center - sprites.text_width(hi, FONT_PX) / 2, 19, hi, VALUE),
        _text(sim.WIDTH - 10 - sprites.text_width("WAVE", FONT_PX), 6, "WAVE", LABEL),
        _text(sim.WIDTH - 10 - sprites.text_width(wave, FONT_PX), 19, wave, VALUE),
    ]
    return "".join(parts)


def _bottom_hud(script):
    lives_extra = (
        f'<g fill="{CANNON_COLOR}" transform="translate(24 199.5) scale(0.7)">'
        f'<use href="#cannon"/>'
        + (
            _opacity_window(0, script.cannon_death["t"], script.duration, start_visible=True)
            if script.cannon_death
            else ""
        )
        + "</g>"
    )
    credit = _text(
        sim.WIDTH - 10 - sprites.text_width("CREDIT 00", FONT_PX), 199, "CREDIT 00", LABEL
    )
    return (
        f'<rect x="6" y="{sim.GROUND_Y}" width="{sim.WIDTH - 12}" height="1" fill="{GROUND}"/>'
        f'<g fill="{CANNON_COLOR}" transform="translate(10 199.5) scale(0.7)">'
        f'<use href="#cannon"/></g>'
        f"{lives_extra}{credit}"
    )


def _wave_banner(script, wave):
    label = f"WAVE {wave} CLEARED"
    x = sim.WIDTH / 2 - sprites.text_width(label, FONT_PX) / 2
    return (
        f'<g opacity="0" fill="{VALUE}" transform="translate({_f(x)} 96)">'
        f"{sprites.text_rects(label, FONT_PX)}"
        f"{_blink_windows(script.wave_text_t, script.duration - 0.3, 0.45, script.duration)}"
        "</g>"
    )


def _thresholds(day_counts):
    nonzero = sorted(c for c in day_counts if c > 0)
    if not nonzero:
        return (1, 2, 3, 4)
    quart = max(1, len(nonzero) // 4)
    return (
        1,
        nonzero[min(quart, len(nonzero) - 1)],
        nonzero[min(2 * quart, len(nonzero) - 1)],
        nonzero[min(3 * quart, len(nonzero) - 1)],
    )


def render(script, day_counts, hi_score, wave_label):
    """Full SVG document string."""
    thresholds = _thresholds(day_counts)
    layers = [
        f'<rect width="{sim.WIDTH}" height="{sim.HEIGHT}" rx="6" fill="{BG}"/>',
        f'<rect x="0.5" y="0.5" width="{sim.WIDTH - 1}" height="{sim.HEIGHT - 1}" '
        f'rx="6" fill="none" stroke="{BORDER}" stroke-width="1"/>',
        _hud(script, hi_score, wave_label),
        _bullets(script),
        _bombs(script),
        _formation(script, day_counts, thresholds),
        _shields(script),
        _cannon(script),
        _ufo(script),
        _wave_banner(script, wave_label),
        _bottom_hud(script),
    ]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {VIEW_W} {VIEW_H}" width="{VIEW_W}" height="{VIEW_H}" '
        f'role="img" aria-label="Self-playing Space Invaders over real GitHub '
        f'contribution data">'
        f"{_style()}{_defs()}"
        f'<g transform="scale({SCALE})">{"".join(layers)}</g>'
        "</svg>"
    )
