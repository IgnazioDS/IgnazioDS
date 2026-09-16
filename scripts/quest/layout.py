"""Screen layout shared by the simulation, the renderer and the art (game px).

The playfield is 415x240 rendered at exactly 2x (830x480), which matches the
profile README's 830px image width: every art pixel lands on a crisp 2x2
block instead of being resampled.
"""

WIDTH, HEIGHT = 415, 240
SCALE = 2

GROUND_Y = 214         # feet touch the path here
KNIGHT_X = 80          # left edge of the 104x76 knight frame (hip at +40)
KNIGHT_FEET = 72       # frame row of the knight's soles
SPAWN_X = WIDTH + 12   # monsters enter from beyond the right edge
BONFIRE_X = 148        # bonfire frame left edge while the knight rests

# Monster frame left edge while fighting, tuned per silhouette so claws,
# blades and scythes meet the knight's reach.
ENGAGE_X = {1: 144, 2: 140, 3: 130, 4: 137}
FLYER_LIFT = {1: 30, 4: 2}  # hover height above the ground line

KNIGHT_FRAMES = (
    "idle0", "idle1", "idle2", "idle3",
    "walk0", "walk1", "walk2", "walk3", "walk4", "walk5", "walk6", "walk7",
    "atk0", "atk1", "atk2", "atk3", "atk4", "atk5",
    "parry0", "parry1", "hurt0", "hurt1", "sit0", "sit1", "kneel0", "kneel1",
)
WALK_FRAMES = 8
IDLE_FRAMES = 4

SOULS_ANCHOR = (WIDTH - 99, 10)  # soul icon centre; wisps fly here, counter sits to its right


def engage_x(tier):
    return ENGAGE_X[tier]
