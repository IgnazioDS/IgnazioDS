"""Immutable event log produced by the simulation and consumed by the renderer.

Times are seconds from the start of the loop. Screen x values are game pixels
(the renderer scales by layout.SCALE).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Phase:
    kind: str     # prologue | walk | fight | rest | transition | boss | epilogue
    start: float
    end: float


@dataclass(frozen=True)
class Chapter:
    region: str   # violet | wood | crimson | keep
    start: float  # region becomes visible (under the fade)
    end: float
    title_t: float


@dataclass(frozen=True)
class Attack:
    t: float              # the monster starts its windup
    outcome: str          # hurt | parry | dodge


@dataclass(frozen=True)
class Encounter:
    index: int
    entry: object         # roster.Entry
    chapter: int
    kind: str             # bestiary key of the creature this day takes the shape of
    elite: bool           # the chapter's champion: marked, tougher, strikes back
    path: tuple           # ((t, screen_x), ...) spawn -> engage, piecewise linear
    engage_t: float
    attacks: tuple        # Attack, in order: the monster's own swings and how each ended
    hits: tuple           # times the knight's blade connects
    blows: tuple          # blow name per hit: slash | rise | thrust | riposte
    heavy: tuple          # per hit: a crushing blow (killing blow on a tough foe, or a riposte) that freezes and shakes
    death_t: float
    remains: tuple = ()   # ((t, screen_x), ...) the body, carried off by the scroll until gone


@dataclass(frozen=True)
class Rest:
    path: tuple           # bonfire ((t, screen_x), ...)
    sit_start: float
    sit_end: float
    chapter: int


@dataclass(frozen=True)
class Flight:
    takeoff: float        # the wyrm climbs away over the city
    dive: float           # it reappears at the right edge, swooping low
    pass_t: float         # directly over the knight
    back: float           # it re-enters from the sky for a second descent
    land: float           # back at its hover spot (screen shake, roar)
    outcome: str          # dodge | hurt


@dataclass(frozen=True)
class BossFight:
    entry: object
    enter_t: float        # dragon starts its descent
    land_t: float         # dragon reaches its hover spot (screen shake)
    breaths: tuple        # ((start, end), ...) fire breath windows
    hits: tuple           # times the knight's blade connects
    death_t: float        # the plunge
    banner_t: float
    blows: tuple = ()     # blow per hit; the last is the plunge
    flights: tuple = ()   # Flight


@dataclass(frozen=True)
class Prologue:
    title_t: float        # the game's title card begins
    flyby: tuple          # (start, end): the wyrm crosses the blood moon
    rise_t: float         # the knight gets up from the fire
    depart_t: float       # ...and sets off; the vista starts to scroll
    end: float            # chapter I replaces the vista under the fade
    camp: tuple           # bonfire ((t, screen_x), ...)


@dataclass(frozen=True)
class Epilogue:
    cheer_t: float        # the knight raises his sword over the fallen wyrm
    camp_t: float         # he plants it, and the fire takes
    stats_t: float        # the quest-complete card begins
    fade_t: float         # the final fade to black begins (everything drawn over it must fade too)
    camp: tuple           # bonfire ((t, screen_x), ...)


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
    knight_moves: tuple   # ((t, dx, dy), ...) linear: lunges, dodge rolls, knockbacks and the leap
    shakes: tuple         # ((t, amplitude), ...) screen shakes for crushing blows
    prologue: Prologue
    epilogue: Epilogue
