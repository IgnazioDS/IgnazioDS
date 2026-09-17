"""The world layer: per-scene parallax scenery, glow lights, ambient motes,
foreground framing and bonfires.

A scene is the prologue vista or a chapter's region. Each is split into a back
group (sky, sky actors, distant and ground layers, back lights, motes) drawn
behind the actors and a front group (foreground layers, front lights, color
grade) drawn over them.
"""

import math
import random
from dataclasses import dataclass

from .. import layout
from ..art import effects, scenery
from ..sim import scroll_at
from . import smil

FLICKER_CLASS = {"fire": "lf-fire", "pulse": "lf-pulse", "lightning": "lf-bolt"}


@dataclass(frozen=True)
class Scene:
    region: str
    start: float
    end: float


def scenes(script):
    """The prologue vista, then every chapter, in play order."""
    vista = Scene("overlook", 0.0, script.prologue.end)
    return (vista,) + tuple(Scene(c.region, c.start, c.end) for c in script.chapters)


def _hex(color):
    return f"#{color >> 8:06x}"


def _scroll_samples(script, scene):
    start = scroll_at(script.scroll, scene.start)
    inside = [(t, s) for t, s in script.scroll if scene.start < t < scene.end]
    samples = [(scene.start, start)] + inside + [(scene.end, scroll_at(script.scroll, scene.end))]
    return start, samples


def _layer(script, scene, layer, asset):
    start, samples = _scroll_samples(script, scene)
    effect = f' class="{layer.effect}"' if layer.effect else ""
    if layer.parallax == 0:
        return f'<g{effect}><use href="#{asset.id}" y="{layer.y}"{_opacity(layer.opacity)}/></g>'
    points = [(t, layer.offset - (s - start) * layer.parallax, layer.y) for t, s in samples]
    travel = max(abs(x) for _, x, _ in points)
    copies = math.ceil((travel + layout.WIDTH) / asset.width) + 1
    first = -asset.width if layer.offset > 0 else 0
    uses = "".join(f'<use href="#{asset.id}" x="{first + k * asset.width}"/>' for k in range(copies + 1))
    if effect:
        uses = f"<g{effect}>{uses}</g>"
    return (
        f'<g transform="translate({layer.offset} {layer.y})"{_opacity(layer.opacity)}>'
        f"{smil.translate(points, script.duration)}{uses}</g>"
    )


def _opacity(value):
    return "" if value >= 1 else f' opacity="{smil.num(value)}"'


def light_repeats(light, art, travel):
    """x offsets that repeat a scrolling light (or motif) at its layer's tile width across `travel` px."""
    if light.parallax == 0:
        return (0,)
    tiles = [layer.image.width for layer in art.layers if layer.parallax == light.parallax]
    if not tiles:
        return (0,)
    period = tiles[0]
    return tuple(k * period for k in range(math.ceil(travel / period) + 1))


def _lights(script, scene, art, lights, gradients):
    if not lights:
        return ""
    start, samples = _scroll_samples(script, scene)
    scroll_span = samples[-1][1] - start
    parts = []
    for light in lights:
        grad = gradients.setdefault(light.color, f"lg{len(gradients)}")
        css = FLICKER_CLASS.get(light.flicker, "")
        ellipse = "".join(
            f'<ellipse cx="{smil.num(light.x + offset)}" cy="{smil.num(light.y)}" rx="{smil.num(light.rx)}" '
            f'ry="{smil.num(light.ry)}" fill="url(#{grad})" opacity="{smil.num(light.opacity)}"/>'
            for offset in light_repeats(light, art, scroll_span * light.parallax)
        )
        if css:  # flicker on a wrapper so the light's own opacity is preserved
            ellipse = f'<g class="{css}">{ellipse}</g>'
        if light.parallax:
            points = [(t, -(s - start) * light.parallax, 0) for t, s in samples]
            ellipse = f"<g>{smil.translate(points, script.duration)}{ellipse}</g>"
        parts.append(ellipse)
    return f'<g style="mix-blend-mode:screen">{"".join(parts)}</g>'


def _stepper(sheet, count, fps, styles):
    """CSS class that steps a sprite sheet through `count` frames (none for stills)."""
    if count < 2:
        return ""
    name = f"st{count}w{sheet.frame_w}f{round(fps * 10)}"
    styles[name] = (f".{name}{{animation:{name} {count / fps:.2f}s steps({count}) infinite}}"
                    f"@keyframes {name}{{to{{transform:translateX(-{count * sheet.frame_w}px)}}}}")
    return name


def _flight(key, motif, styles):
    if not motif.flight:
        return ""
    name = f"fl-{key}-{motif.name}"
    stops = "".join(f"{pct}%{{transform:translate({dx}px,{dy}px);opacity:1}}" for pct, dx, dy in motif.flight)
    delay = f";animation-delay:-{motif.delay:.2f}s" if motif.delay else ""
    styles[name] = f".{name}{{animation:{name} {motif.period:.2f}s linear infinite{delay}}}@keyframes {name}{{{stops}}}"
    return name


def _motif(script, scene, art, motif, book, styles):
    sheet = book.sheet(f"{art.key}-{motif.name}", motif.frames)
    step = _stepper(sheet, len(motif.frames), motif.fps, styles)
    cols, rows = motif.tile
    sprite = "".join(
        f'<svg x="{c * sheet.frame_w}" y="{r * sheet.height}" width="{sheet.frame_w}" height="{sheet.height}">'
        f'<use href="#{sheet.id}"{f" class={chr(34)}{step}{chr(34)}" if step else ""}/></svg>'
        for r in range(rows) for c in range(cols)
    )
    flight = _flight(art.key, motif, styles)
    if flight:  # hidden unless the flight's CSS animation runs (its keyframes restore the opacity)
        sprite = f'<g opacity="0" class="{flight}">{sprite}</g>'
    if motif.effect == "bolt":
        sprite = f'<g opacity="0" class="{FLICKER_CLASS["lightning"]}">{sprite}</g>'
    start, samples = _scroll_samples(script, scene)
    span = samples[-1][1] - start
    copies = "".join(
        f'<g transform="translate({smil.num(motif.x + offset)} {smil.num(motif.y)})">{sprite}</g>'
        for offset in light_repeats(motif, art, span * motif.parallax)
    )
    if motif.parallax:
        points = [(t, -(s - start) * motif.parallax, 0) for t, s in samples]
        copies = f"<g>{smil.translate(points, script.duration)}{copies}</g>"
    return copies


def _motifs(script, scene, art, book, styles, where):
    chosen = [m for m in art.motifs if where(m)]
    return "".join(_motif(script, scene, art, m, book, styles) for m in chosen)


def _particles(art, seed):
    if not art.particles:
        return ""
    rng = random.Random(f"particles-{art.key}-{seed}")
    parts = []
    for i in range(22):
        x = rng.randrange(0, layout.WIDTH)
        y = rng.randrange(70, 225) if art.motion != "fall" else rng.randrange(0, 170)
        size = 2 if rng.random() < 0.22 else 1
        color = _hex(art.particles[i % len(art.particles)])
        style = f"animation-duration:{rng.uniform(4.5, 9.0):.2f}s;animation-delay:-{rng.uniform(0, 9):.2f}s"
        parts.append(
            f'<rect class="p-{art.motion}" x="{x}" y="{y}" width="{size}" height="{size}" '
            f'fill="{color}" style="{style}"/>'
        )
    return "".join(parts)


def _visibility(script, scene, index):
    if scene.start <= 0 and scene.end >= script.duration:
        return "", "1"
    return smil.windows([(scene.start, scene.end)], script.duration), "1" if index == 0 else "0"


def scene_layers(script, book, gradients, styles, sky=None):
    """(back, front) SVG fragments for every scene; `sky` maps a scene index to sky actors.

    `styles` collects the CSS rules the scenes' motifs need (name -> rule).
    """
    sky = sky or {}
    back_groups, front_groups = [], []
    for index, scene in enumerate(scenes(script)):
        art = scenery.region(scene.region)
        back, front = [], []
        for i, layer in enumerate(art.layers):
            if i == art.sky_layers:
                back.append(sky.get(index, ""))
                back.append(_motifs(script, scene, art, book, styles, lambda m: m.sky))
            asset = book.image(f"{layer.source or art.key}-{layer.name}", layer.image)
            (front if layer.front else back).append(_layer(script, scene, layer, asset))
        back.append(_motifs(script, scene, art, book, styles, lambda m: not m.sky and not m.front))
        back.append(_lights(script, scene, art, [l for l in art.lights if not l.front], gradients))
        back.append(_particles(art, index))
        front.append(_motifs(script, scene, art, book, styles, lambda m: m.front))
        front.append(_lights(script, scene, art, [l for l in art.lights if l.front], gradients))
        if art.grade:
            color, alpha = art.grade
            front.append(f'<rect width="{layout.WIDTH}" height="{layout.HEIGHT}" fill="{color}" opacity="{smil.num(alpha)}"/>')
        visibility, base = _visibility(script, scene, index)
        back_groups.append(f'<g opacity="{base}">{visibility}{"".join(back)}</g>')
        front_groups.append(f'<g opacity="{base}">{visibility}{"".join(front)}</g>')
    return "".join(back_groups), "".join(front_groups)


def gradient_defs(gradients):
    return "".join(
        f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="1"/>'
        f'<stop offset="0.45" stop-color="{color}" stop-opacity="0.45"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
        for color, gid in gradients.items()
    )


def bonfires(script, book, gradients):
    """The prologue's fire, every rest along the way, and the fire lit when the wyrm falls."""
    d = script.duration
    frames = effects.bonfire()
    sheet = book.sheet("bonfire", frames)
    glow = gradients.setdefault("#ff9a3c", f"lg{len(gradients)}")
    paths = [script.prologue.camp, *(rest.path for rest in script.rests), script.epilogue.camp]
    parts = []
    for path in paths:
        start, end = path[0][0], path[-1][0]
        y = layout.GROUND_Y - (sheet.height - 3)
        track = smil.DiscreteTrack(0)
        track.cycle(start, end, 8, list(range(len(frames))))
        flames = smil.translate([(t, -i * sheet.frame_w, 0) for t, i in track.events()], d, calc="discrete")
        motion = smil.translate([(t, x, y) for t, x in path], d)
        parts.append(
            f'<g opacity="0">{smil.windows([(start, end)], d)}<g>{motion}'
            f'<g class="lf-fire" style="mix-blend-mode:screen">'
            f'<ellipse cx="14" cy="24" rx="46" ry="26" fill="url(#{glow})" opacity="0.5"/></g>'
            f'<svg width="{sheet.frame_w}" height="{sheet.height}">'
            f'<use href="#{sheet.id}">{flames}</use></svg></g></g>'
        )
    return "".join(parts)


def css():
    return (
        ".p-drift{animation-name:drift;animation-timing-function:ease-in-out;animation-iteration-count:infinite}"
        ".p-rise{animation-name:rise;animation-timing-function:linear;animation-iteration-count:infinite}"
        ".p-fall{animation-name:fall;animation-timing-function:linear;animation-iteration-count:infinite}"
        ".lf-fire{animation:lfire .45s steps(3) infinite}"
        ".lf-pulse{animation:lpulse 3.2s ease-in-out infinite}"
        ".lf-bolt{animation:lbolt 7.3s linear infinite}"
        "@keyframes drift{0%,100%{transform:translate(0,0);opacity:.15}50%{transform:translate(7px,-6px);opacity:1}}"
        "@keyframes rise{0%{transform:translate(0,0);opacity:0}15%{opacity:1}100%{transform:translate(-26px,-64px);opacity:0}}"
        "@keyframes fall{0%{transform:translate(0,0);opacity:0}15%{opacity:1}100%{transform:translate(-44px,72px);opacity:0}}"
        "@keyframes lfire{0%{opacity:.8}33%{opacity:1}66%{opacity:.65}}"
        "@keyframes lpulse{0%,100%{opacity:.55}50%{opacity:1}}"
        "@keyframes lbolt{0%,88%,92%,95%,100%{opacity:0}89%,93%{opacity:1}}"
        ".shimmer{animation:shimmer 6.5s ease-in-out infinite}"
        ".sway{animation:sway 11s ease-in-out infinite alternate}"
        "@keyframes shimmer{0%,100%{opacity:.55}50%{opacity:1}}"
        "@keyframes sway{from{transform:translateX(0)}to{transform:translateX(-16px)}}"
    )
