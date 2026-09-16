"""Immutable event log produced by the simulation and consumed by the renderer.

Times are seconds from the start of the loop. Screen x values are game pixels
(the renderer scales by layout.SCALE).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Phase:
    kind: str     # intro | walk | fight | rest | transition | boss | outro
    start: float
    end: float


@dataclass(frozen=True)
class Chapter:
    region: str   # violet | wood | crimson | keep
    start: float  # region becomes visible (under the fade)
    end: float
    title_t: float


@dataclass(frozen=True)
class Encounter:
    index: int
    entry: object         # roster.Entry
    chapter: int
    path: tuple           # ((t, screen_x), ...) spawn -> engage, piecewise linear
    engage_t: float
    attack_t: object      # float or None: the monster's own swing
    knight_hurt: bool     # True: the swing lands; False: parried
    hits: tuple           # times the knight's blade connects
    death_t: float


@dataclass(frozen=True)
class Rest:
    path: tuple           # bonfire ((t, screen_x), ...)
    sit_start: float
    sit_end: float
    chapter: int


@dataclass(frozen=True)
class BossFight:
    entry: object
    enter_t: float        # dragon starts its descent
    land_t: float         # dragon reaches its hover spot (screen shake)
    breaths: tuple        # ((start, end), ...) fire breath windows
    hits: tuple           # times the knight's blade connects
    death_t: float
    banner_t: float


@dataclass(frozen=True)
class QuestScript:
    duration: float
    scroll: tuple         # ((t, world_px), ...) piecewise linear, non-decreasing
    knight_frames: tuple  # ((t, frame_name), ...) discrete
    phases: tuple         # Phase, contiguous
    chapters: tuple       # Chapter
    encounters: tuple     # Encounter
    rests: tuple          # Rest
    boss: BossFight
    souls: tuple          # ((t, total), ...) starts at (0, 0)
    health: tuple         # ((t, fraction), ...) linear keyframes
    fades: tuple          # ((t, black_opacity), ...) linear keyframes
    parries: tuple        # times of parry sparks
