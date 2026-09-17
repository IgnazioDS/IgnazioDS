"""Prologue and epilogue set pieces: the distant wyrm crossing the blood moon,
and the fire that takes when the knight plants his sword after the quest.
"""

from .. import layout
from ..art import dragon, effects
from . import smil

FLYBY_PATH = ((430.0, 16.0), (226.0, 58.0), (-140.0, 24.0))   # frame top-left: enter, over the moon, exit
FLYBY_FPS = 6
IGNITION_TIME = 0.8


def flyby(script, book):
    """Sky actor for the vista: the wyrm glides across the moon toward the knight's road."""
    t0, t1 = script.prologue.flyby
    d = script.duration
    frames = dragon.flyby_frames()
    sheet = book.sheet("wyrm-flyby", frames)
    track = smil.DiscreteTrack(0)
    track.cycle(t0, t1, FLYBY_FPS, list(range(len(frames))))
    beats = smil.translate([(t, -i * sheet.frame_w, 0) for t, i in track.events()], d, calc="discrete")
    (x0, y0), (x1, y1), (x2, y2) = FLYBY_PATH
    motion = smil.translate([(t0, x0, y0), (t0 + (t1 - t0) * 0.45, x1, y1), (t1, x2, y2)], d)
    return (
        f'<g opacity="0">{smil.windows([(t0, t1)], d)}<g>{motion}'
        f'<svg width="{sheet.frame_w}" height="{sheet.height}"><use href="#{sheet.id}">{beats}</use></svg></g></g>'
    )


def ignition(script, book, gradients):
    """Embers burst and light flares as the epilogue's fire catches."""
    t0 = script.epilogue.camp_t
    d = script.duration
    frames = effects.ember_burst()
    sheet = book.sheet("wyrm-embers", frames)
    track = smil.DiscreteTrack(0)
    track.cycle(t0, t0 + IGNITION_TIME, len(frames) / IGNITION_TIME, list(range(len(frames))))
    burst = smil.translate([(t, -i * sheet.frame_w, 0) for t, i in track.events()], d, calc="discrete")
    cx, cy = layout.BONFIRE_X + 14, layout.GROUND_Y - 16
    glow = gradients.setdefault("#ffb45a", f"lg{len(gradients)}")
    flare = smil.linear("opacity", [(0.0, "0"), (t0, "0"), (t0 + 0.12, "0.85"), (t0 + 0.9, "0")], d)
    return (
        f'<g style="mix-blend-mode:screen"><ellipse cx="{cx}" cy="{cy}" rx="70" ry="44" fill="url(#{glow})" '
        f'opacity="0">{flare}</ellipse></g>'
        f'<g opacity="0" transform="translate({cx - sheet.frame_w // 2} {cy - sheet.height // 2 - 8})">'
        f'{smil.windows([(t0, t0 + IGNITION_TIME)], d)}'
        f'<svg width="{sheet.frame_w}" height="{sheet.height}"><use href="#{sheet.id}">{burst}</use></svg></g>'
    )
