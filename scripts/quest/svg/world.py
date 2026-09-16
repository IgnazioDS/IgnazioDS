"""The world layer: per-chapter parallax scenery, glow lights, ambient motes,
foreground framing and bonfires.

Each chapter is split into a back group (sky, distant and ground layers,
back lights, motes) drawn behind the actors and a front group (foreground
layers, front lights, color grade) drawn over them.
"""

import math
import random

from .. import layout
from ..art import effects, scenery
from ..sim import scroll_at
from . import smil

FLICKER_CLASS = {"fire": "lf-fire", "pulse": "lf-pulse", "lightning": "lf-bolt"}


def _hex(color):
    return f"#{color >> 8:06x}"


def _scroll_samples(script, chapter):
    start = scroll_at(script.scroll, chapter.start)
    inside = [(t, s) for t, s in script.scroll if chapter.start < t < chapter.end]
    samples = [(chapter.start, start)] + inside + [(chapter.end, scroll_at(script.scroll, chapter.end))]
    return start, samples


def _layer(script, chapter, layer, asset):
    start, samples = _scroll_samples(script, chapter)
    if layer.parallax == 0:
        return f'<use href="#{asset.id}" y="{layer.y}"{_opacity(layer.opacity)}/>'
    points = [(t, layer.offset - (s - start) * layer.parallax, layer.y) for t, s in samples]
    travel = max(abs(x) for _, x, _ in points)
    copies = math.ceil((travel + layout.WIDTH) / asset.width) + 1
    first = -asset.width if layer.offset > 0 else 0
    uses = "".join(f'<use href="#{asset.id}" x="{first + k * asset.width}"/>' for k in range(copies + 1))
    return (
        f'<g transform="translate({layer.offset} {layer.y})"{_opacity(layer.opacity)}>'
        f"{smil.translate(points, script.duration)}{uses}</g>"
    )


def _opacity(value):
    return "" if value >= 1 else f' opacity="{smil.num(value)}"'


def light_repeats(light, art, travel):
    """x offsets that repeat a scrolling light at its layer's tile width across `travel` px."""
    if light.parallax == 0:
        return (0,)
    tiles = [layer.image.width for layer in art.layers if layer.parallax == light.parallax]
    if not tiles:
        return (0,)
    period = tiles[0]
    return tuple(k * period for k in range(math.ceil(travel / period) + 1))


def _lights(script, chapter, art, lights, gradients):
    if not lights:
        return ""
    start, samples = _scroll_samples(script, chapter)
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


def _visibility(script, chapter, index):
    if chapter.start <= 0 and chapter.end >= script.duration:
        return "", "1"
    return smil.windows([(chapter.start, chapter.end)], script.duration), "1" if index == 0 else "0"


def chapters(script, book, gradients):
    """(back, front) SVG fragments for every chapter's scenery."""
    back_groups, front_groups = [], []
    for index, chapter in enumerate(script.chapters):
        art = scenery.region(chapter.region)
        back, front = [], []
        for layer in art.layers:
            asset = book.image(f"{art.key}-{layer.name}", layer.image)
            (front if layer.front else back).append(_layer(script, chapter, layer, asset))
        back.append(_lights(script, chapter, art, [l for l in art.lights if not l.front], gradients))
        back.append(_particles(art, index))
        front.append(_lights(script, chapter, art, [l for l in art.lights if l.front], gradients))
        if art.grade:
            color, alpha = art.grade
            front.append(f'<rect width="{layout.WIDTH}" height="{layout.HEIGHT}" fill="{color}" opacity="{smil.num(alpha)}"/>')
        visibility, base = _visibility(script, chapter, index)
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
    if not script.rests:
        return ""
    d = script.duration
    frames = effects.bonfire()
    sheet = book.sheet("bonfire", frames)
    glow = gradients.setdefault("#ff9a3c", f"lg{len(gradients)}")
    parts = []
    for rest in script.rests:
        start, end = rest.path[0][0], rest.path[-1][0]
        y = layout.GROUND_Y - (sheet.height - 3)
        track = smil.DiscreteTrack(0)
        track.cycle(start, end, 8, list(range(len(frames))))
        flames = smil.translate([(t, -i * sheet.frame_w, 0) for t, i in track.events()], d, calc="discrete")
        motion = smil.translate([(t, x, y) for t, x in rest.path], d)
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
    )
