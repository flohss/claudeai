"""A pseudo-3D view of the real Thronglets simulation, with an optional
external "sensor" (microphone and/or webcam) that can startle the
population - loosely inspired by the show's idea of a camera/microphone
giving the Thronglets an outside signal to react to.

This is NOT true VR: no headset, no stereoscopic/OpenXR/WebXR output,
nothing this environment could test even if it existed. It's the classic
"pseudo-3D driving game" trick - a ground plane projected onto a normal 2D
screen so things shrink and converge toward a horizon line - viewed on a
regular monitor.

Unlike the first version of this file, the population here is the real
thing: a genuine simulation.py World, stepped every frame, with creatures
that actually evolved their own colors. There are no predators in this
version - the world is a safe one - so the sensors don't touch the
simulation at all: a loud room or something moving in front of the camera
just flashes a visible alert on screen, nothing more.

Both sensors are OFF by default - nothing is captured unless you press A
(microphone) or C (camera) yourself, and the HUD always shows their
current state so it's never listening without a visible indicator. Either
one failing to open (library not installed, no hardware, no permission)
just leaves it unavailable - the game never crashes over something this
optional, and this environment has neither piece of hardware to test
against, so treat the default threshold as a starting point to recalibrate
with [ and ] once you're on a real machine.

The world starts with exactly one creature, not hatched yet - it sits on
screen as an egg. Left-click it a few times to crack it open; nothing
else in the world moves or steps until it hatches.

Every creature born afterward, through reproduction, gets the same
treatment: it starts life as an egg at its real (moving) position - it's
fully alive and simulated the whole time, but doesn't render, sound, or
otherwise reveal itself until you go find it and click it open too
(BirthEggs). One that dies before being hatched just quietly disappears,
no leftover egg.

Once hatched, a small needs panel appears top-left: pizza (hunger), a
glass of water (thirst), soap (cleanliness), and a toy (joy). Each need
drains slowly on its own; click an item to top its need back up to full.
Feeding the pizza also tops up the creature's *real* simulation.py energy
- the rest are cosmetic, local to this file's single-companion mode, not
part of the shared simulation model. Neglect all four for long enough and
the creature's expression turns visibly worried; there's no harsher
penalty than that.

A fifth button sits right after the four needs: an egg icon. Click it to
add a brand-new creature to the world, near wherever the current
population already is - like any other birth, it starts life as a
pending egg you have to go find and click open. This matters because the
solo starting creature is deliberately unable to reproduce on its own,
no matter how much energy it has (install_solo_reproduction_guard);
reproduction (pairing and budding both) only ever becomes automatic once
a second creature exists, whether that second one came from this button
or arrived some other way. There's no limit on how many times you can
use it.

The panel's last two buttons are the episode's dark side, included on
purpose: a flame and a knife. Clicking one arms it - its border turns
red and the HUD says so - and clicking it again puts it away. Neither
is a clean kill. With the knife armed, clicking a creature makes it
agonize - it collapses and writhes where it stands, screaming - and
only then dies, leaving a blood mark that fades from the grass. With
fire armed, clicking a creature sets it alight: it screams and bolts in
panic, burning, for a second or two before it dies, leaving a scorch
mark. Both finish through World.kill_creature(), the same path as a
natural death, so the family tree and the death count stay honest about
what you did. Creatures still waiting inside their birth egg can't be
targeted - only ones you've already hatched.

These creatures are meant to read as sentient beings, not dots, so they
FEEL what happens - to themselves and to each other (see
SentienceState). Every hatched creature carries an emotion, worked out
each frame from its situation, and wears it on its face: pain (a
screwed-shut, screaming face) when it is itself burning or under the
knife; fear (wide eyes, a small round mouth) when it can see another
creature in agony nearby, and it flees from the sight; sadness (a
downturned mouth and a tear) where a companion has just died - the
survivors grieve the spot for a while - or when its own needs are
neglected; and plain joy (a smile and happy eyes) when it is safe and
not alone. The whole population has a voice to match: a strident scream
rises whenever anyone is in pain, a lower frightened whimper while
others are merely afraid, and quiet otherwise (the master mute silences
it like everything else).

The creature design is an original, simplified, geometric interpretation
of the look (round yellow body, big eyes, blue lower half) - not a
reproduction of the show's or the licensed game's actual pixel art.
Each one blinks on its own schedule and wanders a couple of
pixels in place even when the simulation isn't moving it, so a standing
creature still reads as alive rather than a frozen sprite.

By default, the whole population sounds at once: every evolved signal
(token) currently used by a living creature plays continuously, all
together - a running chorus of the group's communication rather than
silence until you go looking for it. Press G to turn that off and hear
only individual creatures instead. Hovering the mouse over a creature
always plays a sustained tone for its evolved signal too - same idea as
the proximity-listening sound in main.py/main_web.py, but judged by
*screen* distance instead of world distance, since depth already
changes how big and how far apart things look here - independently of
the chorus toggle. Press M to mute all of it.

The landscape is scaled the way a real one would be, and reads coherently
back to front: a jagged rocky mountain range spans the entire horizon (the
true back of the world, not an isolated outcrop), a dense forest runs edge
to edge at middle distance in front of it, and the open plain - where the population
actually lives - has just a handful of trees standing on their own near
the camera, plus scattered boulders. Trees tower several times a
creature's height and rocks are boulders rather than pebbles. A river
winds across the field toward the camera - a muddy shore fringe, a darker
deep-water band, and a lighter shallow center with a couple of gently
drifting sparkle lines, instead of one flat-colored ribbon. Its source
sits at the horizon line itself, glued under the green foothill band
without overlapping it, so the water emerges from beneath the hills and
threads down through the forest toward the plain - and the trees make
room for its bed (generate_landscape() never places one in the water).
Trees and rocks are depth-sorted together with the creatures (same
painter's-algorithm pass draw_scene() uses for everything else), so a
creature correctly stands in front of a nearby
tree or vanishes behind a farther one instead of scenery and population
clashing as two unrelated layers - and, like the population, they pan
with the view.

Every new game (a fresh launch, or pressing R) gets its own random
landscape via generate_landscape(): different tree/rock/grass
placement, hill silhouette, and river position each time, built from a
random seed. Passing that function a specific seed instead of None
reproduces the exact same landscape again - not used yet, but there for
a future save/load feature to restore a saved game's terrain rather
than generating a new one over it.

Lighting is faked, not real 3D: cast shadows stretch and swing around
over the course of the day (short and centered at zenith, long and
leaning near sunrise/sunset) via light_direction(day_phase). The ground
is also scattered with small grass-tuft marks instead of being a single
flat color band, for texture.

The scroll wheel zooms, Minecraft-style: it magnifies the ground-plane
scene around a fixed point on the horizon rather than moving the camera
forward, so every distance keeps the same size ratio to every other
distance as you zoom - things get uniformly bigger or smaller, the
perspective itself never distorts.

Controls:
  LEFT CLICK     crack an egg / use the needs panel (feed, add an egg,
                 or arm the fire/knife and click a creature to use it)
  CLICK + DRAG   pan the view with the mouse
  LEFT / RIGHT   pan the view with the keyboard
  SCROLL         zoom in / out
  SPACE          pause / resume
  UP / DOWN      simulation speed
  G              toggle the population chorus (on by default)
  M              mute/unmute all sound
  R              reset to a fresh egg
  A              toggle the microphone sensor
  C              toggle the camera sensor
  [ / ]          lower / raise the alert sensitivity threshold
  ESC            quit
"""

import math
import random
import sys
import threading
from collections import namedtuple

import numpy as np
import pygame

from simulation import BUD_ENERGY, HEIGHT, MAX_ENERGY, WIDTH, World

SCREEN_W, SCREEN_H = 1000, 700
HORIZON_Y = int(SCREEN_H * 0.42)

# Dragging the mouse across the full window width pans by roughly 1.6
# stage units (a bit more than half the visible field of view).
PAN_DRAG_SENSITIVITY = 1.6 / SCREEN_W
# A mouse-up is treated as a click (egg / needs panel) rather than a pan
# if the total travel while the button was held stayed under this, in
# pixels - lets a light click and a deliberate drag coexist on the same
# button.
PAN_DRAG_CLICK_THRESHOLD = 6

# Scroll-wheel zoom, Minecraft-style: it magnifies the ground-plane scene
# around a fixed screen point rather than moving the camera, so
# perspective proportions between near and far objects stay the same as
# you zoom - everything just gets uniformly bigger or smaller.
ZOOM_MIN = 0.6
ZOOM_MAX = 3.5
ZOOM_STEP = 0.1

# A full in-game day lasts 24 real minutes - one in-game hour per real
# minute, same ratio the show's clock-obsessed episode would approve of.
DAY_CYCLE_SECONDS = 24 * 60.0

# Day/night is one continuous blend, not a hard swap: every "landscape"
# color below has a day and a night version, plus a warm twilight accent
# that peaks for a moment at each sunrise/sunset (see celestial_state()).
SKY_TOP_DAY = (40, 70, 130)
SKY_HORIZON_DAY = (178, 212, 235)
SKY_TOP_NIGHT = (8, 10, 28)
SKY_HORIZON_NIGHT = (24, 28, 52)
SKY_TOP_TWILIGHT = (70, 45, 80)
SKY_HORIZON_TWILIGHT = (240, 145, 110)

# The far layer is a proper rocky mountain range - the true back of the
# horizon - with the near layer as green foothills in front of it,
# before the forest band and then the plain (see draw_background()).
HILL_FAR_DAY = (118, 112, 108)
HILL_NEAR_DAY = (80, 125, 95)
HILL_FAR_NIGHT = (24, 24, 28)
HILL_NEAR_NIGHT = (20, 30, 36)

GROUND_FAR_DAY = (95, 165, 100)
GROUND_NEAR_DAY = (55, 130, 65)
GROUND_FAR_NIGHT = (30, 48, 52)
GROUND_NEAR_NIGHT = (16, 28, 34)

TWILIGHT_WARM = (210, 140, 80)  # a low-weight tint blended into ground/hills at sunrise/sunset

GRID_COLOR_DAY = (70, 150, 80)
GRID_COLOR_NIGHT = (35, 55, 60)
TREE_TRUNK_DAY = (90, 65, 45)
TREE_LEAVES_DAY = (55, 115, 60)
TREE_TRUNK_NIGHT = (40, 32, 28)
TREE_LEAVES_NIGHT = (25, 45, 32)

ROCK_COLOR_DAY = (150, 145, 140)
ROCK_COLOR_NIGHT = (55, 55, 60)
ROCK_SHADE_DAY = (105, 100, 96)
ROCK_SHADE_NIGHT = (35, 35, 40)

RIVER_COLOR_DAY = (55, 115, 165)        # deep water along the banks
RIVER_COLOR_NIGHT = (14, 26, 48)
RIVER_HIGHLIGHT_DAY = (130, 195, 215)   # lighter shallow band down the center
RIVER_HIGHLIGHT_NIGHT = (32, 52, 74)
RIVER_BANK_DAY = (150, 128, 88)         # wet shoreline fringe
RIVER_BANK_NIGHT = (32, 28, 20)
RIVER_SPARKLE_DAY = (215, 235, 240)
RIVER_SPARKLE_NIGHT = (75, 92, 108)

# A winding band cutting across the field, described as (x, z, half-width)
# waypoints in stage coordinates, widening as it comes toward the camera.
# A per-game river_offset (see generate_landscape()) shifts every x here
# sideways, so the river doesn't sit in the exact same place every game.
# Its source (first waypoint) sits at z=0 - the horizon line itself - so
# the water emerges from directly under the green foothill band and then
# threads down through the forest toward the plain. The trees make room
# for it (see generate_landscape()), it never runs over one.
RIVER_PATH = [
    (0.5, 0.0, 0.015), (0.6, 0.18, 0.03), (0.7, 0.32, 0.045),
    (0.64, 0.48, 0.06), (0.78, 0.63, 0.08), (0.92, 0.8, 0.11),
    (1.08, 1.0, 0.15),
]


def river_lane_at(z):
    """The river's centerline x and half-width at a given depth,
    interpolated between RIVER_PATH waypoints (clamped at both ends).
    Before river_offset - callers shift the x themselves."""
    if z <= RIVER_PATH[0][1]:
        return RIVER_PATH[0][0], RIVER_PATH[0][2]
    for (x0, z0, w0), (x1, z1, w1) in zip(RIVER_PATH, RIVER_PATH[1:]):
        if z <= z1:
            f = (z - z0) / (z1 - z0)
            return x0 + (x1 - x0) * f, w0 + (w1 - w0) * f
    return RIVER_PATH[-1][0], RIVER_PATH[-1][2]

GRASS_TUFT_COLOR_DAY = (35, 95, 40)
GRASS_TUFT_COLOR_NIGHT = (10, 22, 18)
GRASS_TUFT_COUNT = 220

SUN_COLOR = (255, 236, 180)
SUN_COLOR_HORIZON = (255, 140, 80)
MOON_COLOR = (222, 226, 235)
MOON_CRATER_COLOR = (195, 200, 212)
STAR_COLOR = (255, 255, 255)
NIGHT_OVERLAY_COLOR = (20, 25, 65)

# A fixed, seeded star field - generated once at import, not per frame, so
# the stars hold still instead of jittering; they fade in/out by blending
# toward the current sky color rather than needing per-pixel alpha.
_star_rng = random.Random(7)
STAR_POSITIONS = [
    (_star_rng.uniform(0.02, 0.98), _star_rng.uniform(0.02, 0.9), _star_rng.choice((1, 1, 1, 2)))
    for _ in range(70)
]

BODY_COLOR = (245, 210, 70)
EYE_WHITE = (250, 250, 245)
EYE_PUPIL = (35, 30, 30)
MOUTH_COLOR = (100, 65, 45)
PANTS_COLOR = (70, 165, 210)
SHADOW_COLOR = (25, 60, 30)
FOOD_COLOR = (110, 220, 90)
PREDATOR_COLOR = (215, 40, 40)

# Same 6-color palette as the other renderers, so a creature's ring here
# means the same thing it does in main.py/main_tui.py/main_web.py.
TOKEN_COLORS = [
    (120, 120, 120),
    (235, 70, 70),
    (70, 140, 235),
    (245, 200, 60),
    (200, 90, 230),
    (70, 225, 210),
]

# Same tones as main.py/main_web.py's proximity-listening sound, keyed by
# token (index 0, the "no signal" gray, deliberately has none to play).
TOKEN_FREQS = [0, 261.63, 293.66, 329.63, 392.00, 440.00]
# Screen pixels, not world/stage units - depth already changes a
# creature's apparent size and position here, so "closest to the cursor"
# has to be judged the same way the eye judges it: on screen.
LISTEN_RADIUS_PX = 70

ALERT_DURATION = 2.5    # seconds a sensor alert stays active
ALERT_COOLDOWN = 4.0    # seconds before another alert can trigger
DEFAULT_ALERT_THRESHOLD = 0.5

EGG_CLICKS_NEEDED = 6
EGG_STAGE_X = 0.0
EGG_STAGE_Z = 0.88
EGG_COLOR = (240, 232, 205)
EGG_SPECKLE = (200, 180, 140)
EGG_CRACK_COLOR = (95, 78, 58)
# Fixed crack polylines (relative to the egg's half-width/half-height),
# revealed one at a time as clicks land - not randomized per frame, so the
# cracks accumulate in place instead of jittering around.
EGG_CRACK_LINES = [
    [(-0.10, -0.42), (0.04, -0.12), (-0.06, 0.18), (0.14, 0.44)],
    [(0.30, -0.32), (0.14, -0.02), (0.34, 0.24)],
    [(-0.32, -0.18), (-0.16, 0.05), (-0.36, 0.30)],
    [(0.02, -0.46), (-0.10, -0.20)],
    [(0.26, 0.08), (0.40, -0.08)],
    [(-0.20, 0.36), (-0.36, 0.14)],
]

# The needs panel - a little care-taking loop on top of the real
# simulation: feeding the pizza also tops up the creature's actual
# simulation.py energy, but thirst/cleanliness/joy are purely cosmetic
# local state, tracked here rather than in simulation.py since they only
# make sense for this file's single-companion mode.
NEED_ITEMS = ("hunger", "thirst", "clean", "joy")
NEED_LABELS = {"hunger": "pizza", "thirst": "water", "clean": "soap", "joy": "toy"}
NEED_COLORS = {
    "hunger": (235, 140, 60),
    "thirst": (90, 170, 230),
    "clean": (210, 225, 200),
    "joy": (230, 120, 170),
}
NEED_DECAY_PER_SECOND = 1.0 / 120.0  # empties in 2 minutes if never fed
NEED_LOW_THRESHOLD = 0.2
FEED_ENERGY_BOOST = 40.0
NEED_PANEL_X = 10
NEED_PANEL_Y = 90
NEED_BUTTON_SIZE = 44
NEED_BUTTON_GAP = 56

# The episode's dark side, faithfully included: the panel's last two
# slots are weapons, not care. Fire burns a creature alive for
# BURN_DURATION seconds - it screams and bolts in panic the whole time -
# before it dies; the knife doesn't kill on the spot either, the
# creature agonizes for AGONY_DURATION, writhing where it stands, and
# then dies. Both leave a mark on the ground that fades over
# DECAL_DURATION.
BURN_DURATION = 1.6
AGONY_DURATION = 1.4
DECAL_DURATION = 1.0
FLAME_COLORS = ((255, 110, 25), (255, 185, 55), (255, 240, 150))
BLOOD_COLOR = (150, 20, 20)
SCORCH_COLOR = (45, 38, 32)
ARMED_BORDER_COLOR = (230, 50, 40)

# Sentience: every hatched creature feels something, computed each frame
# from its situation, and shows it on its face, in how it moves, and in
# the sound the population makes. Emotions, in priority order:
#   pain  - it is itself burning or being knifed
#   fear  - it can see another creature in pain within SENSE_RADIUS, and
#           flees from it (empathy: others' suffering frightens it)
#   sad   - a companion died near here recently (grief), or its own
#           needs are critically low
#   joy   - content and not alone: a companion within COMPANION_RADIUS
#   calm  - none of the above
# The radii and speeds are in world units (the World is 200x140).
SENSE_RADIUS = 46.0
COMPANION_RADIUS = 55.0
GRIEF_RADIUS = 42.0
GRIEF_DURATION = 6.0      # seconds a death keeps grieving the survivors near it
PANIC_RUN_SPEED = 34.0    # a burning creature bolting, world units / second
FEAR_FLEE_SPEED = 20.0    # fleeing a nearby horror, world units / second
TEAR_COLOR = (150, 205, 245)

# Bundles the three "how should this frame be projected/lit" values that
# almost every draw_* function needs together, instead of three separate
# parameters spreading through every signature.
RenderCtx = namedtuple("RenderCtx", ["zoom", "shadow_dx", "shadow_len"])
DEFAULT_CTX = RenderCtx(zoom=1.0, shadow_dx=0.0, shadow_len=1.0)

# A coherent back-to-front reading: mountains (the far hill ridge, see
# draw_background) -> a dense forest band at middle distance -> the open
# plain with just a few trees standing on their own, near the camera.
# The forest's lateral range is much wider than the plain trees' because
# perspective converges toward the center with depth: at forest depths,
# +/-1.3 only covers the middle of the screen, leaving bare gaps on both
# sides. +/-4.5 keeps the band filled edge to edge (and through pans).
FOREST_COUNT_RANGE = (70, 90)
FOREST_X_RANGE = (-4.5, 4.5)
FOREST_Z_RANGE = (0.10, 0.28)
TREE_COUNT_RANGE = (3, 6)
TREE_X_RANGE = (-1.3, 1.3)
TREE_Z_RANGE = (0.35, 0.9)
ROCK_COUNT_RANGE = (4, 8)

# Everything about a game's terrain that should be different from one
# new game to the next, but reproducible if a specific seed is supplied
# (e.g. by a future save/load feature restoring a saved game's terrain).
Landscape = namedtuple("Landscape", [
    "seed", "forest", "trees", "rocks", "grass", "hill_far_phase", "hill_near_phase", "river_offset",
])


def generate_landscape(seed=None):
    """Builds one random landscape - forest/tree/rock/grass placement,
    plus a little hill-silhouette and river variation - from a seed.
    Leave seed as None for a fresh, different layout (what every new
    game gets); pass a specific seed to reproduce that exact layout
    again later."""
    rng = random.Random(seed)
    # The river's sideways shift is drawn first so tree placement can
    # avoid its bed: the river runs down through the middle of the
    # forest, and a tree standing in the water would read as a mistake.
    river_offset = rng.uniform(-0.25, 0.25)

    def scatter_trees(count, x_range, z_range):
        pts = []
        while len(pts) < count:
            x, z = rng.uniform(*x_range), rng.uniform(*z_range)
            lane_x, half_w = river_lane_at(z)
            if abs(x - (lane_x + river_offset)) > half_w + 0.06:
                pts.append((x, z))
        return pts

    forest = scatter_trees(rng.randint(*FOREST_COUNT_RANGE), FOREST_X_RANGE, FOREST_Z_RANGE)
    trees = scatter_trees(rng.randint(*TREE_COUNT_RANGE), TREE_X_RANGE, TREE_Z_RANGE)
    rocks = [(rng.uniform(-1.3, 1.3), rng.uniform(0.04, 0.85), rng.uniform(0.6, 1.6))
             for _ in range(rng.randint(*ROCK_COUNT_RANGE))]
    grass = [(rng.uniform(-1.3, 1.3), rng.uniform(0.03, 0.99), rng.uniform(-1.0, 1.0))
             for _ in range(GRASS_TUFT_COUNT)]
    return Landscape(
        seed=seed,
        forest=forest,
        trees=trees,
        rocks=rocks,
        grass=grass,
        hill_far_phase=rng.uniform(0.0, 2 * math.pi),
        hill_near_phase=rng.uniform(0.0, 2 * math.pi),
        river_offset=river_offset,
    )


# A fixed fallback landscape (deterministic seed) for callers that don't
# have a live game's landscape handy - keeps draw_background() always
# renderable rather than requiring a landscape argument everywhere.
_DEFAULT_LANDSCAPE = generate_landscape(seed=0)


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def celestial_state(day_phase):
    """day_phase 0..1 is one full day+night loop. The sun is up for the
    first half, the moon for the second - they're exact mirror images of
    each other, so precisely one is ever above the horizon. day_amount is
    a smooth 0 (deep night) .. 1 (high noon) blend for landscape colors;
    twilight_amount peaks for a moment at both the sunrise and sunset
    crossing, for a warm accent independent of the day/night blend."""
    theta = day_phase * 2 * math.pi
    sun_height = math.sin(theta)
    moon_height = -sun_height
    day_amount = (sun_height + 1) / 2
    twilight_amount = max(0.0, 1.0 - abs(sun_height) / 0.35)
    return sun_height, moon_height, day_amount, twilight_amount


def light_direction(day_phase):
    """Fakes directional lighting from the sun/moon's actual position,
    without real 3D geometry: shadow_dx is which way shadows point (-1
    fully left .. +1 fully right), shadow_len is how stretched they are
    (>1 = longer - near sunrise/sunset or dim moonlight - down to a
    shorter minimum near noon, when the light source is overhead)."""
    sun_height, moon_height, _, _ = celestial_state(day_phase)
    if sun_height > 0.001:
        arc_t = day_phase / 0.5
        light_height = sun_height
    elif moon_height > 0.001:
        arc_t = (day_phase - 0.5) / 0.5
        light_height = moon_height
    else:
        arc_t, light_height = 0.5, 0.5
    shadow_dx = max(-1.0, min(1.0, (0.5 - arc_t) * 2.0))
    shadow_len = max(0.7, min(2.6, 1.0 + (1.0 - max(0.05, light_height)) * 1.6))
    return shadow_dx, shadow_len


class SensorHub:
    """Best-effort microphone/camera capture. Every failure mode - missing
    library, missing system dependency (e.g. no PortAudio), no hardware,
    permission denied - is caught and just leaves that sensor permanently
    unavailable. Nothing is captured unless the corresponding *_enabled
    flag is explicitly turned on by the user."""

    def __init__(self):
        self.mic_enabled = False
        self.camera_enabled = False
        self.mic_available = None  # None = not yet attempted
        self.camera_available = None
        self.mic_level = 0.0       # smoothed 0..1
        self.motion_level = 0.0    # smoothed 0..1
        self._lock = threading.Lock()
        self._mic_stream = None
        self._camera_thread = None
        self._camera_stop = threading.Event()

    def toggle_mic(self):
        self._stop_mic() if self.mic_enabled else self._start_mic()

    def toggle_camera(self):
        self._stop_camera() if self.camera_enabled else self._start_camera()

    def _start_mic(self):
        try:
            import sounddevice as sd
        except Exception:
            self.mic_available = False
            return

        def callback(indata, frames, time_info, status):
            rms = float(np.sqrt(np.mean(np.asarray(indata, dtype=np.float64) ** 2)))
            level = min(1.0, rms * 12.0)
            with self._lock:
                self.mic_level = self.mic_level * 0.7 + level * 0.3

        try:
            stream = sd.InputStream(channels=1, samplerate=16000, blocksize=1024, callback=callback)
            stream.start()
        except Exception:
            self.mic_available = False
            return
        self._mic_stream = stream
        self.mic_available = True
        self.mic_enabled = True

    def _stop_mic(self):
        self.mic_enabled = False
        with self._lock:
            self.mic_level = 0.0
        if self._mic_stream is not None:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception:
                pass
            self._mic_stream = None

    def _start_camera(self):
        try:
            import cv2
        except Exception:
            self.camera_available = False
            return
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.camera_available = False
            cap.release()
            return
        self.camera_available = True
        self.camera_enabled = True
        self._camera_stop.clear()
        self._camera_thread = threading.Thread(target=self._camera_loop, args=(cv2, cap), daemon=True)
        self._camera_thread.start()

    def _camera_loop(self, cv2, cap):
        prev_gray = None
        while not self._camera_stop.is_set():
            ok, frame = cap.read()
            if not ok:
                break
            small = cv2.resize(frame, (160, 90))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                level = min(1.0, float(diff.mean()) / 20.0)
                with self._lock:
                    self.motion_level = self.motion_level * 0.7 + level * 0.3
            prev_gray = gray
        cap.release()

    def _stop_camera(self):
        self.camera_enabled = False
        self._camera_stop.set()
        if self._camera_thread is not None:
            self._camera_thread.join(timeout=1.0)
            self._camera_thread = None
        with self._lock:
            self.motion_level = 0.0

    def alert_level(self):
        with self._lock:
            return max(self.mic_level, self.motion_level)

    def stop(self):
        self._stop_mic()
        self._stop_camera()


class EggState:
    """The world always starts with a single unhatched creature. Nothing
    steps until enough clicks land on the egg - register_click() returns
    True the instant it hatches, so the caller can react (start ticking,
    flash the screen) exactly once."""

    def __init__(self):
        self.cracks = 0
        self.hatched = False
        self.pulse = 0.0

    def register_click(self, mx, my, zoom=1.0, pan_x=0.0):
        # Hit-test where the egg is actually drawn - the view may have
        # been panned before the first hatch, and the egg pans with it.
        if self.hatched or not egg_contains(mx, my, EGG_STAGE_X - pan_x, EGG_STAGE_Z, zoom):
            return False
        self.cracks += 1
        self.pulse = 1.0
        if self.cracks >= EGG_CLICKS_NEEDED:
            self.hatched = True
            return True
        return False

    def update(self, dt):
        self.pulse = max(0.0, self.pulse - dt * 4.0)


class BirthEggs:
    """Every creature born through reproduction (not the very first,
    initial-hatch one) starts life as an egg at its real, moving
    position - it's fully alive and simulated underneath (still eating,
    moving, able to reproduce or be eaten), but doesn't render, sound,
    or otherwise reveal itself as a creature to the player until enough
    clicks land on it, mirroring the very first hatch. One that dies
    before being hatched is simply dropped, no egg left behind."""

    def __init__(self):
        self.pending = {}   # creature id -> clicks so far
        self.known_ids = set()

    def seed_known(self, world):
        """Call once, right when the very first egg hatches, so that
        already-hatched starting creature is never treated as a new
        birth egg itself."""
        self.known_ids = {c.id for c in world.creatures}

    def sync(self, world):
        """Call once per frame after stepping the world - any creature
        id not seen before is a new birth, becoming a pending egg."""
        current_ids = {c.id for c in world.creatures if c.alive}
        for cid in current_ids - self.known_ids:
            self.pending[cid] = 0
        for cid in list(self.pending):
            if cid not in current_ids:
                del self.pending[cid]
        self.known_ids = current_ids

    def is_pending(self, creature_id):
        return creature_id in self.pending

    def add_manual(self, creature_id):
        """Immediately marks a creature (just created via the needs
        panel's egg button) as a pending egg, bypassing sync()'s normal
        diff-based detection - and records its id as already-known so a
        later sync() doesn't reset its click count back to 0."""
        self.pending[creature_id] = 0
        self.known_ids.add(creature_id)

    def try_click(self, mx, my, world, pan_x, zoom=1.0):
        """Returns True if the click landed on a pending birth egg
        (whether or not that particular click was the one that hatched
        it) - lets the caller know not to treat the click as a miss."""
        for c in world.creatures:
            if c.alive and c.id in self.pending:
                x, z = world_to_stage(c.pos)
                if egg_contains(mx, my, x - pan_x, z, zoom):
                    self.pending[c.id] += 1
                    if self.pending[c.id] >= EGG_CLICKS_NEEDED:
                        del self.pending[c.id]
                    return True
        return False


def install_solo_reproduction_guard(world):
    """The lone starting creature shouldn't be able to reproduce (bud)
    on its own - only once a second one exists (via the panel's egg
    button, or normal pairing after that) does reproduction become
    automatic. Wraps this specific World instance's private
    _reproduce() to skip it entirely while fewer than two creatures are
    alive; pairing already needs two to do anything, so this only ever
    blocks solo budding, and reproduction resumes exactly as normal the
    moment a second creature exists. A per-instance monkeypatch, not a
    change to simulation.py, so main.py/main_tui.py/main_web.py are
    unaffected. (An earlier version tried clamping energy right before
    each step instead, but step() calls _eat() - which can top energy
    back up - before _reproduce(), so that could still let a solo bud
    slip through within the same step.)"""
    original_reproduce = world._reproduce

    def guarded_reproduce():
        if len([c for c in world.creatures if c.alive]) < 2:
            return
        original_reproduce()

    world._reproduce = guarded_reproduce


def spawn_egg_near_population(world, birth_eggs):
    """Adds one new creature near the existing population's center (or
    the middle of the field if there's none left) - what the needs
    panel's egg button does. Registered immediately as a pending
    BirthEggs egg, exactly like a creature born through reproduction:
    still just an egg to the player until it's found and hatched."""
    alive = [c for c in world.creatures if c.alive]
    if alive:
        ax = sum(c.pos[0] for c in alive) / len(alive)
        ay = sum(c.pos[1] for c in alive) / len(alive)
    else:
        ax, ay = WIDTH / 2, HEIGHT / 2
    creature = world.add_creature(ax + random.uniform(-15, 15), ay + random.uniform(-15, 15))
    if creature is not None:
        birth_eggs.add_manual(creature.id)
    return creature


def find_creature_at(mx, my, world, pan_x, zoom=1.0, birth_eggs=None, t=0.0):
    """The living creature under a screen point, or None. Mirrors
    draw_critter's own geometry (projection, idle offset, body circle)
    so the clickable area is exactly what the player sees. Creatures
    still pending as birth eggs aren't targetable - those belong to
    BirthEggs.try_click. When bodies overlap, the nearest-to-camera one
    wins, matching the painter's-algorithm draw order."""
    best = None
    best_z = -1.0
    for c in world.creatures:
        if not c.alive:
            continue
        if birth_eggs is not None and birth_eggs.is_pending(c.id):
            continue
        x, z = world_to_stage(c.pos)
        sx, sy, scale = project(x - pan_x, z, zoom)
        body_r = int(24 * scale)
        if body_r < 2:
            continue
        ox, oy = idle_offset(c.id, t)
        sx += ox * scale
        sy += oy * scale
        cx, cy = sx, sy - body_r * 0.55
        r = body_r * 1.3
        if (mx - cx) ** 2 + (my - cy) ** 2 <= r * r and z > best_z:
            best, best_z = c, z
    return best


class HorrorState:
    """The game's Black Mirror dark side: the fire and knife buttons.
    Clicking one arms it (clicking again, or the other one, puts it
    away); with a weapon armed, clicking a creature applies it. Neither
    is a clean, instant death: the knife makes the creature agonize for
    AGONY_DURATION - writhing where it stands - before it dies, and fire
    sets it alight for BURN_DURATION while it screams and runs, before
    it dies. Both finish through World.kill_creature(), the same path as
    a natural death, so the family tree and stats stay honest about what
    the player did. A creature already in pain can't be hurt a second
    way at once."""

    def __init__(self):
        self.armed = None       # None, "fire" or "knife"
        self.burning = {}       # creature id -> seconds left before it dies
        self.agonizing = {}     # creature id -> seconds left before it dies
        self.decals = []        # [x_stage, z, kind, seconds left]; kind: "blood"/"scorch"

    def toggle(self, tool):
        self.armed = None if self.armed == tool else tool

    def is_burning(self, creature_id):
        return creature_id in self.burning

    def is_agonizing(self, creature_id):
        return creature_id in self.agonizing

    def in_pain(self, creature_id):
        return creature_id in self.burning or creature_id in self.agonizing

    def stab(self, creature, world):
        """Doesn't kill on the spot: the creature starts agonizing and
        bleeds where it was struck. It dies once the agony runs out (in
        update())."""
        if not creature.alive or self.in_pain(creature.id):
            return False
        self.agonizing[creature.id] = AGONY_DURATION
        x, z = world_to_stage(creature.pos)
        self.decals.append([x, z, "blood", DECAL_DURATION])
        return True

    def ignite(self, creature):
        if not creature.alive or self.in_pain(creature.id):
            return False
        self.burning[creature.id] = BURN_DURATION
        return True

    def _advance(self, world, timers, dt, decal_kind):
        """Shared countdown for burning/agonizing: tick each timer down,
        drop the ones whose creature already died some other way, and
        kill + mark the ones that reach zero."""
        by_id = {c.id: c for c in world.creatures}
        for cid in list(timers):
            c = by_id.get(cid)
            if c is None or not c.alive:
                del timers[cid]
                continue
            timers[cid] -= dt
            if timers[cid] <= 0:
                del timers[cid]
                if world.kill_creature(c):
                    x, z = world_to_stage(c.pos)
                    self.decals.append([x, z, decal_kind, DECAL_DURATION])

    def update(self, world, dt):
        """Advance burn/agony timers and age out ground marks - call once
        per unpaused frame. A creature that dies of something else
        mid-pain just stops; one whose timer runs out dies where it
        stands, leaving a scorch (fire) or blood (knife) mark there."""
        for d in self.decals:
            d[3] -= dt
        self.decals = [d for d in self.decals if d[3] > 0]
        self._advance(world, self.burning, dt, "scorch")
        self._advance(world, self.agonizing, dt, "blood")


def _dist2(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


class SentienceState:
    """Makes the population feel like living, sentient beings rather than
    dots. Each frame it works out what every hatched creature is feeling
    from its situation - and, crucially, from what's happening to the
    others around it - then that emotion drives the face it wears, the
    way it moves, and the sound the whole population makes.

    A creature on fire or under the knife feels pain (it screams; a
    burning one bolts, a knifed one writhes). A creature that can see
    another in pain nearby feels fear and flees it - empathy, the horror
    of watching it happen to someone else. Where a companion has just
    died, the survivors nearby grieve for a while. Otherwise, a creature
    that is safe and not alone is simply joyful, and a neglected or
    lonely one is sad. Nothing here touches the evolutionary simulation's
    own logic; it's a feeling, expressive layer laid over the real
    creatures."""

    def __init__(self):
        self.emotions = {}       # creature id -> emotion string (for this frame)
        self.grief_marks = []    # [x, y, seconds left]: where a companion died
        self._known = {}         # id -> last known (x, y), to catch deaths
        self.cry = None          # "scream" / "whimper" / None: the population's voice

    def _living_ids(self, world, birth_eggs):
        return {c.id for c in world.creatures if c.alive
                and not (birth_eggs is not None and birth_eggs.is_pending(c.id))}

    def update(self, world, horror, needs_low, birth_eggs, t, dt, paused):
        # 1. a creature that vanished since last frame just died - grieve
        #    the spot, so survivors nearby will feel it (skip ones still
        #    inside a birth egg, they never "appeared").
        living = self._living_ids(world, birth_eggs)
        for cid, pos in self._known.items():
            if cid not in living:
                self.grief_marks.append([pos[0], pos[1], GRIEF_DURATION])
        self._known = {c.id: (float(c.pos[0]), float(c.pos[1]))
                       for c in world.creatures if c.id in living}

        # 2. age grief out
        if not paused:
            for g in self.grief_marks:
                g[2] -= dt
        self.grief_marks = [g for g in self.grief_marks if g[2] > 0]

        # 3. how everyone feels, 4. how the population sounds
        self.emotions = self._compute(world, horror, needs_low, birth_eggs)
        self.cry = self._dominant_cry()

        # 5. pain and fear move the body, not just the face
        if not paused:
            self._apply_panic(world, horror, t, dt)
        return self.emotions

    def _compute(self, world, horror, needs_low, birth_eggs):
        alive = [c for c in world.creatures if c.alive
                 and not (birth_eggs is not None and birth_eggs.is_pending(c.id))]
        pain_pos = [c.pos for c in alive if horror is not None and horror.in_pain(c.id)]
        emotions = {}
        for c in alive:
            if horror is not None and horror.in_pain(c.id):
                emotions[c.id] = "pain"
            elif any(_dist2(c.pos, p) <= SENSE_RADIUS ** 2 for p in pain_pos if p is not c.pos):
                emotions[c.id] = "fear"
            elif any(_dist2(c.pos, (g[0], g[1])) <= GRIEF_RADIUS ** 2 for g in self.grief_marks):
                emotions[c.id] = "sad"
            elif needs_low:
                emotions[c.id] = "sad"
            elif any(o is not c and _dist2(c.pos, o.pos) <= COMPANION_RADIUS ** 2 for o in alive):
                emotions[c.id] = "joy"
            else:
                emotions[c.id] = "calm"
        return emotions

    def _dominant_cry(self):
        vals = self.emotions.values()
        if "pain" in vals:
            return "scream"
        if "fear" in vals:
            return "whimper"
        return None

    def _apply_panic(self, world, horror, t, dt):
        if horror is None:
            return
        alive = [c for c in world.creatures if c.alive]
        pain = [c for c in alive if horror.in_pain(c.id)]
        for c in alive:
            if horror.is_burning(c.id):
                # bolting in blind panic - a seeded heading that swerves
                seed = _creature_seed(c.id)
                ang = seed * 6.28318 + math.sin(t * 6.0 + seed * 6.0) * 1.4
                self._move(c, math.cos(ang), math.sin(ang), PANIC_RUN_SPEED, dt)
            elif horror.is_agonizing(c.id):
                continue  # collapses and writhes in place, doesn't travel
            elif self.emotions.get(c.id) == "fear":
                src = min((p for p in pain if p is not c),
                          key=lambda p: _dist2(c.pos, p.pos), default=None)
                if src is not None:
                    dx = float(c.pos[0] - src.pos[0])
                    dy = float(c.pos[1] - src.pos[1])
                    n = math.hypot(dx, dy) or 1.0
                    self._move(c, dx / n, dy / n, FEAR_FLEE_SPEED, dt)

    @staticmethod
    def _move(creature, ux, uy, speed, dt):
        nx = float(creature.pos[0]) + ux * speed * dt
        ny = float(creature.pos[1]) + uy * speed * dt
        creature.pos = np.clip(np.array([nx, ny]), [0, 0], [WIDTH, HEIGHT])


class NeedsState:
    """A small Tamagotchi-style care loop layered on top of the real
    creature: each need drains slowly and is topped up by clicking the
    matching item in the needs panel. Only hunger reaches back into the
    real simulation (it tops up the creature's actual energy) - the rest
    are cosmetic, specific to this file's single-companion mode."""

    def __init__(self):
        self.levels = {kind: 1.0 for kind in NEED_ITEMS}
        self.pulses = {kind: 0.0 for kind in NEED_ITEMS}

    def update(self, dt):
        for kind in NEED_ITEMS:
            self.levels[kind] = max(0.0, self.levels[kind] - NEED_DECAY_PER_SECOND * dt)
            self.pulses[kind] = max(0.0, self.pulses[kind] - dt * 4.0)

    def lowest(self):
        return min(self.levels.values())

    def feed(self, kind, world):
        if kind not in self.levels:
            return
        self.levels[kind] = 1.0
        self.pulses[kind] = 1.0
        if kind == "hunger":
            for c in world.creatures:
                if c.alive:
                    c.energy = min(MAX_ENERGY, c.energy + FEED_ENERGY_BOOST)


def need_button_rect(index):
    return pygame.Rect(NEED_PANEL_X + index * NEED_BUTTON_GAP, NEED_PANEL_Y,
                        NEED_BUTTON_SIZE, NEED_BUTTON_SIZE)


def draw_icon_pizza(screen, rect):
    cx, cy = rect.center
    r = rect.width * 0.42
    points = [(cx, cy - r), (cx - r * 0.87, cy + r * 0.5), (cx + r * 0.87, cy + r * 0.5)]
    pygame.draw.polygon(screen, (235, 195, 110), points)
    pygame.draw.polygon(screen, (200, 80, 60), points, width=2)
    for fx, fy in ((-0.15, 0.15), (0.2, 0.0), (0.0, -0.3)):
        pygame.draw.circle(screen, (190, 60, 50), (int(cx + fx * r), int(cy + fy * r)), max(1, int(r * 0.14)))


def draw_icon_water(screen, rect):
    cx, cy = rect.center
    w, h = rect.width * 0.5, rect.height * 0.6
    glass = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
             (cx + w * 0.4, cy + h / 2), (cx - w * 0.4, cy + h / 2)]
    water = [(cx - w * 0.45, cy - h * 0.05), (cx + w * 0.45, cy - h * 0.05),
             (cx + w * 0.38, cy + h / 2), (cx - w * 0.38, cy + h / 2)]
    pygame.draw.polygon(screen, (230, 245, 250), glass)
    pygame.draw.polygon(screen, (100, 175, 230), water)
    pygame.draw.polygon(screen, (150, 165, 165), glass, width=2)


def draw_icon_soap(screen, rect):
    cx, cy = rect.center
    w, h = rect.width * 0.62, rect.height * 0.4
    bar = pygame.Rect(0, 0, w, h)
    bar.center = (cx, cy)
    pygame.draw.ellipse(screen, (225, 235, 205), bar)
    pygame.draw.ellipse(screen, (175, 190, 155), bar, width=2)
    for ox, oy, r in ((-w * 0.2, -h * 1.5, 3), (w * 0.12, -h * 2.0, 4), (w * 0.3, -h * 1.2, 2)):
        pygame.draw.circle(screen, (255, 255, 255), (int(cx + ox), int(cy + oy)), r, width=1)


def draw_icon_toy(screen, rect):
    cx, cy = rect.center
    r = int(rect.width * 0.38)
    pygame.draw.circle(screen, (235, 90, 140), (cx, cy), r)
    pygame.draw.arc(screen, (255, 220, 230), (cx - r, cy - r, r * 2, r * 2), 0.3, 2.6, 2)


def draw_icon_egg(screen, rect):
    cx, cy = rect.center
    w, h = rect.width * 0.52, rect.height * 0.66
    egg = pygame.Rect(0, 0, w, h)
    egg.center = (cx, cy)
    pygame.draw.ellipse(screen, EGG_COLOR, egg)
    pygame.draw.ellipse(screen, (180, 165, 130), egg, width=1)
    for ox, oy in ((-0.16, -0.12), (0.14, 0.06), (-0.05, 0.24)):
        pygame.draw.circle(screen, EGG_SPECKLE, (int(cx + ox * w), int(cy + oy * h)), max(1, int(w * 0.08)))


def draw_icon_fire(screen, rect):
    cx, cy = rect.center
    w, h = rect.width * 0.5, rect.height * 0.62
    base_y = cy + h * 0.5
    # three nested flame tongues, hot core last
    for color, f in zip(FLAME_COLORS, (1.0, 0.68, 0.4)):
        fw, fh = w * f, h * f
        pygame.draw.polygon(screen, color, [
            (cx - fw * 0.5, base_y), (cx + fw * 0.5, base_y),
            (cx + fw * 0.18, base_y - fh * 0.62), (cx, base_y - fh),
            (cx - fw * 0.22, base_y - fh * 0.55),
        ])


def draw_icon_knife(screen, rect):
    cx, cy = rect.center
    L = rect.width * 0.36
    # blade (light gray, angled) + brown handle
    pygame.draw.polygon(screen, (205, 210, 218), [
        (cx - L, cy + L * 0.75), (cx + L * 0.15, cy - L * 0.4),
        (cx + L * 0.45, cy - L * 0.1), (cx - L * 0.65, cy + L),
    ])
    pygame.draw.line(screen, (120, 75, 40),
                     (cx + L * 0.3, cy - L * 0.25), (cx + L * 0.85, cy - L * 0.8),
                     max(3, int(rect.width * 0.12)))


NEED_ICON_DRAWERS = {
    "hunger": draw_icon_pizza,
    "thirst": draw_icon_water,
    "clean": draw_icon_soap,
    "joy": draw_icon_toy,
}

# The panel's 5th slot: not a decaying need, a one-shot action button
# that adds a brand-new creature to the world - as a birth egg the
# player still has to go find and hatch, same as any other newborn.
ADD_EGG_SLOT = len(NEED_ITEMS)

# Slots 6 and 7: the weapons. Clicking one arms it (click again to put
# it away); with a weapon armed, clicking a creature applies it.
FIRE_SLOT = ADD_EGG_SLOT + 1
KNIFE_SLOT = ADD_EGG_SLOT + 2


def add_egg_button_rect():
    return need_button_rect(ADD_EGG_SLOT)


def fire_button_rect():
    return need_button_rect(FIRE_SLOT)


def knife_button_rect():
    return need_button_rect(KNIFE_SLOT)


def draw_needs_panel(screen, needs, armed_tool=None):
    for i, kind in enumerate(NEED_ITEMS):
        rect = need_button_rect(i)
        pulse = needs.pulses[kind]
        bg_rect = rect.inflate(int(pulse * 6), int(pulse * 6))
        pygame.draw.rect(screen, (28, 32, 28), bg_rect, border_radius=8)
        pygame.draw.rect(screen, (95, 100, 90), bg_rect, width=1, border_radius=8)
        NEED_ICON_DRAWERS[kind](screen, bg_rect)
        draw_meter(screen, rect.x, rect.bottom + 4, NEED_BUTTON_SIZE, 6,
                   needs.levels[kind], NEED_COLORS[kind])

    egg_rect_ui = add_egg_button_rect()
    pygame.draw.rect(screen, (28, 32, 28), egg_rect_ui, border_radius=8)
    pygame.draw.rect(screen, (95, 100, 90), egg_rect_ui, width=1, border_radius=8)
    draw_icon_egg(screen, egg_rect_ui)

    for tool, rect, icon in (("fire", fire_button_rect(), draw_icon_fire),
                             ("knife", knife_button_rect(), draw_icon_knife)):
        pygame.draw.rect(screen, (28, 32, 28), rect, border_radius=8)
        border = ARMED_BORDER_COLOR if armed_tool == tool else (95, 100, 90)
        width = 2 if armed_tool == tool else 1
        pygame.draw.rect(screen, border, rect, width=width, border_radius=8)
        icon(screen, rect)


class AlertState:
    """Turns a sensor's alert_level() into an on-screen alert flash. This
    version of the game has no predators, so unlike earlier revisions the
    alert deliberately leaves the World untouched - it's a purely visual
    "something happened in the room" signal, still cooldown-gated so a
    sustained noise doesn't strobe the screen."""

    def __init__(self):
        self.active_timer = 0.0
        self.cooldown_timer = 0.0
        self.flash = 0.0

    def update(self, world, sensors, threshold, dt):
        self.cooldown_timer = max(0.0, self.cooldown_timer - dt)
        self.flash = max(0.0, self.flash - dt)
        if self.active_timer > 0:
            self.active_timer -= dt
        elif sensors.alert_level() > threshold and self.cooldown_timer <= 0:
            self.active_timer = ALERT_DURATION
            self.cooldown_timer = ALERT_COOLDOWN
            self.flash = 0.6


def init_sound():
    """Best-effort mixer setup - returns (tones, hover_channel,
    ambient_tones, ambient_channels, cry_sounds, cry_channel), or six
    Nones if there's no audio device at all. Never crashes the game over
    something this optional (same pattern as SensorHub).

    Several independent things share the mixer: hover_channel plays one
    tone for whichever single creature the mouse is over (Channel 0),
    ambient_channels (Channels 1-5, one per token) each play at the same
    time, quieter, for the population-chorus sound, and cry_channel
    (Channel 6) plays the population's emotional voice - a strident
    scream when any creature is in pain, a lower frightened whimper when
    others are afraid - louder than and independent of the chorus."""
    try:
        pygame.mixer.init(frequency=22050, size=-16, channels=2)
        pygame.mixer.set_num_channels(max(8, pygame.mixer.get_num_channels()))
        sample_rate = pygame.mixer.get_init()[0]
        tones = {token: _make_tone(freq, sample_rate)
                 for token, freq in enumerate(TOKEN_FREQS) if token != 0}
        ambient_tones = {token: _make_tone(freq, sample_rate, volume=0.12)
                          for token, freq in enumerate(TOKEN_FREQS) if token != 0}
        hover_channel = pygame.mixer.Channel(0)
        ambient_channels = {token: pygame.mixer.Channel(token) for token in range(1, 6)}
        cry_sounds = {
            "scream": _make_cry(sample_rate, base=720, harsh=True, volume=0.5),
            "whimper": _make_cry(sample_rate, base=300, harsh=False, volume=0.22),
        }
        cry_channel = pygame.mixer.Channel(6)
        return tones, hover_channel, ambient_tones, ambient_channels, cry_sounds, cry_channel
    except pygame.error:
        return None, None, None, None, None, None


def _make_tone(freq, sample_rate, duration=0.6, volume=0.25):
    """A short sine-wave tone with a fade in/out envelope, looped by the
    caller - the fades also soften the seam where the loop repeats."""
    n = int(sample_rate * duration)
    ts = np.linspace(0, duration, n, endpoint=False)
    wave = np.sin(2 * np.pi * freq * ts)
    fade = min(n // 20, 400)
    envelope = np.ones(n)
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    wave = (wave * envelope * volume * 32767).astype(np.int16)
    stereo = np.column_stack([wave, wave])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _make_cry(sample_rate, base=700, harsh=True, volume=0.4, duration=0.8):
    """A raw, unsettling voiced cry, deliberately *not* a clean musical
    tone like the communication signals: a fast vibrato that swoops the
    pitch up and down, and (for a scream) added dissonant overtones plus
    a bit of noise, so it reads as a living thing shrieking rather than a
    beep. Looped by the caller for as long as the pain/fear lasts."""
    n = int(sample_rate * duration)
    ts = np.linspace(0, duration, n, endpoint=False)
    vibrato = 1.0 + 0.06 * np.sin(2 * np.pi * 11.0 * ts)   # a wavering, panicked pitch
    swoop = 1.0 + 0.25 * np.sin(2 * np.pi * 1.3 * ts)      # rises and falls like a wail
    phase = 2 * np.pi * base * vibrato * swoop * ts
    wave = np.sin(phase)
    if harsh:
        wave += 0.6 * np.sin(2.76 * phase)   # inharmonic partial -> a rough, screamed timbre
        wave += 0.4 * np.sin(5.13 * phase)
        wave += 0.25 * np.random.default_rng(0).standard_normal(n)  # breathy rasp
    wave = np.clip(wave, -1.5, 1.5) / 1.5
    fade = min(n // 20, 400)
    envelope = np.ones(n)
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    wave = (wave * envelope * volume * 32767).astype(np.int16)
    stereo = np.column_stack([wave, wave])
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def update_cry(cry_channel, cry_sounds, sentience_cry, muted, current_cry):
    """Plays the population's emotional voice: whichever cry SentienceState
    settled on this frame (a scream while anyone's in pain, a whimper while
    others are afraid, or nothing). Returns what's now playing so the caller
    can track it across frames without re-hitting the mixer every time.
    Silenced by the master mute, independent of the chorus toggle."""
    if cry_channel is None:
        return None
    target = None if muted else sentience_cry
    if target != current_cry:
        if target is None:
            cry_channel.stop()
        else:
            cry_channel.play(cry_sounds[target], loops=-1)
    return target


def update_listening(channel, tones, world, mouse_pos, pan_x, muted, listening_token, zoom=1.0,
                      birth_eggs=None):
    """Plays a sustained tone for whichever living creature's *screen*
    position is closest to the mouse, within LISTEN_RADIUS_PX - the
    pseudo-3D counterpart of main.py's proximity-listening sound. Returns
    the token now playing (or None) so the caller can track it across
    frames without re-querying the mixer every time. A creature still
    pending in birth_eggs hasn't "appeared" yet, so it's skipped."""
    if channel is None:
        return None
    target = None
    if not muted:
        best_dist = LISTEN_RADIUS_PX
        for c in world.creatures:
            if not c.alive or c.token == 0:
                continue
            if birth_eggs is not None and birth_eggs.is_pending(c.id):
                continue
            x, z = world_to_stage(c.pos)
            sx, sy, _ = project(x - pan_x, z, zoom)
            dist = ((sx - mouse_pos[0]) ** 2 + (sy - mouse_pos[1]) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                target = c.token
    if target != listening_token:
        if target is None:
            channel.stop()
        else:
            channel.play(tones[target], loops=-1)
    return target


def update_ambient(ambient_channels, ambient_tones, world, muted, ambient_enabled, birth_eggs=None):
    """The population's own 'chorus': every signal (token) currently
    used by at least one living, *hatched* creature plays continuously,
    all at once, each on its own channel - not just whichever one
    creature the mouse happens to be over. Creatures still pending in
    birth_eggs don't contribute; they haven't "appeared" yet. On by
    default; turning it off (independent of the master mute) falls back
    to hearing only the hover sound."""
    if not ambient_channels:
        return
    if muted or not ambient_enabled:
        for channel in ambient_channels.values():
            channel.stop()
        return
    active_tokens = {
        c.token for c in world.creatures
        if c.alive and c.token != 0 and not (birth_eggs is not None and birth_eggs.is_pending(c.id))
    }
    for token, channel in ambient_channels.items():
        if token in active_tokens:
            if not channel.get_busy():
                channel.play(ambient_tones[token], loops=-1)
        else:
            channel.stop()


def world_to_stage(pos):
    """Reuses the World's own 2D layout as the pseudo-3D stage: its Y axis
    becomes depth (top of the field = far/near the horizon, bottom = close
    to the camera), its X axis stays lateral."""
    x_norm = (pos[0] / WIDTH) * 2.6 - 1.3
    z = max(0.02, min(1.0, pos[1] / HEIGHT))
    return x_norm, z


def project(x, z, zoom=1.0):
    """x: lateral offset (roughly -1.3..1.3), z: depth, 0 = far/near the
    horizon, 1 = close to the camera. Returns (screen_x, screen_y, scale) -
    farther things are smaller and closer to the screen's horizontal
    center, the classic converging-perspective illusion.

    zoom magnifies the whole ground-plane scene around a fixed screen
    point (the horizon, centered) rather than moving the camera - like a
    telephoto lens, not a dolly - so every distance keeps the same size
    ratio to every other distance as zoom changes, just larger overall."""
    scale = 0.1 + z * 1.05
    spread = SCREEN_W * 0.55 * (0.12 + z * 0.9)
    screen_x = SCREEN_W / 2 + x * spread
    screen_y = HORIZON_Y + z * (SCREEN_H - HORIZON_Y)
    if zoom != 1.0:
        screen_x = SCREEN_W / 2 + (screen_x - SCREEN_W / 2) * zoom
        screen_y = HORIZON_Y + (screen_y - HORIZON_Y) * zoom
        scale *= zoom
    return screen_x, screen_y, scale


def draw_background(screen, day_phase, pan_x=0.0, zoom=1.0, landscape=None, t=0.0):
    if landscape is None:
        landscape = _DEFAULT_LANDSCAPE
    sun_height, moon_height, day_amount, twilight_amount = celestial_state(day_phase)

    sky_top = lerp_color(SKY_TOP_NIGHT, SKY_TOP_DAY, day_amount)
    sky_top = lerp_color(sky_top, SKY_TOP_TWILIGHT, twilight_amount * 0.5)
    sky_horizon = lerp_color(SKY_HORIZON_NIGHT, SKY_HORIZON_DAY, day_amount)
    sky_horizon = lerp_color(sky_horizon, SKY_HORIZON_TWILIGHT, twilight_amount)
    for y in range(HORIZON_Y):
        color = lerp_color(sky_top, sky_horizon, y / HORIZON_Y)
        pygame.draw.line(screen, color, (0, y), (SCREEN_W, y))

    for frac_x, frac_y, size in STAR_POSITIONS:
        local_sky = lerp_color(sky_top, sky_horizon, frac_y)
        star_color = lerp_color(STAR_COLOR, local_sky, day_amount)
        pygame.draw.circle(screen, star_color,
                            (int(SCREEN_W * frac_x), int(HORIZON_Y * frac_y)), size)

    if sun_height > 0:
        arc_t = day_phase / 0.5
        sun_pos = (int(SCREEN_W * (0.08 + 0.84 * arc_t)), int(HORIZON_Y * (1.0 - sun_height * 0.85)))
        near_horizon = 1.0 - sun_height
        core = lerp_color(SUN_COLOR, SUN_COLOR_HORIZON, near_horizon * 0.8)
        for r, color in ((54, lerp_color(core, sky_horizon, 0.5)), (38, core)):
            pygame.draw.circle(screen, color, sun_pos, r)
    if moon_height > 0:
        arc_t = (day_phase - 0.5) / 0.5
        moon_pos = (int(SCREEN_W * (0.08 + 0.84 * arc_t)), int(HORIZON_Y * (1.0 - moon_height * 0.85)))
        pygame.draw.circle(screen, lerp_color(MOON_COLOR, sky_horizon, 0.5), moon_pos, 30)
        pygame.draw.circle(screen, MOON_COLOR, moon_pos, 26)
        for ox, oy, r in ((-8, -6, 5), (7, 3, 4), (-2, 10, 3)):
            pygame.draw.circle(screen, MOON_CRATER_COLOR, (moon_pos[0] + ox, moon_pos[1] + oy), r)

    hill_far = lerp_color(HILL_FAR_NIGHT, HILL_FAR_DAY, day_amount)
    hill_near = lerp_color(HILL_NEAR_NIGHT, HILL_NEAR_DAY, day_amount)
    hill_far = lerp_color(hill_far, TWILIGHT_WARM, twilight_amount * 0.25)
    hill_near = lerp_color(hill_near, TWILIGHT_WARM, twilight_amount * 0.3)

    # The far layer is the true back of the landscape: a jagged mountain
    # range spanning the whole horizon, not gentle rolling hills - taller,
    # sharper peaks than the near layer.
    hill_y = HORIZON_Y - int(SCREEN_H * 0.05)
    ridge_n = 12
    ridge = []
    for i in range(ridge_n + 1):
        rx = SCREEN_W * i / ridge_n
        amp1 = 55 * math.sin(i * 0.9 + landscape.hill_far_phase)
        amp2 = 28 * math.sin(i * 2.3 + landscape.hill_far_phase * 1.7)
        ridge.append((rx, hill_y - 45 - amp1 - amp2))
    far_hills = [(0, HORIZON_Y)] + ridge + [(SCREEN_W, HORIZON_Y)]
    pygame.draw.polygon(screen, hill_far, far_hills)

    near_hill_y = HORIZON_Y - int(SCREEN_H * 0.02)
    near_hills = [(0, HORIZON_Y)]
    for i in range(7):
        near_hills.append((SCREEN_W * i / 6, near_hill_y - 12 * math.sin(i * 2.1 + landscape.hill_near_phase)))
    near_hills.append((SCREEN_W, HORIZON_Y))
    pygame.draw.polygon(screen, hill_near, near_hills)

    ground_far = lerp_color(GROUND_FAR_NIGHT, GROUND_FAR_DAY, day_amount)
    ground_near = lerp_color(GROUND_NEAR_NIGHT, GROUND_NEAR_DAY, day_amount)
    ground_far = lerp_color(ground_far, TWILIGHT_WARM, twilight_amount * 0.2)
    ground_near = lerp_color(ground_near, TWILIGHT_WARM, twilight_amount * 0.2)
    for y in range(HORIZON_Y, SCREEN_H):
        frac = (y - HORIZON_Y) / (SCREEN_H - HORIZON_Y)
        pygame.draw.line(screen, lerp_color(ground_far, ground_near, frac), (0, y), (SCREEN_W, y))

    grid_color = lerp_color(GRID_COLOR_NIGHT, GRID_COLOR_DAY, day_amount)
    for i in range(1, 9):
        _, sy, _ = project(-pan_x, i / 9, zoom)
        pygame.draw.line(screen, grid_color, (0, sy), (SCREEN_W, sy), 1)
    for x in (-1.2, -0.8, -0.4, 0.0, 0.4, 0.8, 1.2):
        sx0, sy0, _ = project(x - pan_x, 0.0, zoom)
        sx1, sy1, _ = project(x - pan_x, 1.0, zoom)
        pygame.draw.line(screen, grid_color, (sx0, sy0), (sx1, sy1), 1)

    draw_grass_tufts(screen, landscape, pan_x, day_amount, zoom)
    draw_river(screen, landscape.river_offset, pan_x, day_amount, zoom, t)


def draw_ground_shadow(screen, sx, top_y, w, h, shadow_dx=0.0, shadow_len=1.0):
    """A cast shadow that stretches and leans away from the light source
    instead of always sitting as a fixed puddle directly underneath -
    shadow_dx/shadow_len come from light_direction(). Translucent, not a
    solid fill: a tree's wide shadow can overlap something small sitting
    nearby (a birth egg, another creature) in the depth-sorted draw
    order, and a solid shadow would fully erase it instead of just
    darkening it, which reads as a rendering glitch rather than shade."""
    stretched_w = max(1, int(w * shadow_len))
    rect_h = max(1, int(h))
    offset = shadow_dx * w * 0.5 * (shadow_len - 1.0)
    shadow_surf = pygame.Surface((stretched_w, rect_h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (*SHADOW_COLOR, 130), (0, 0, stretched_w, rect_h))
    screen.blit(shadow_surf, (sx + offset - stretched_w / 2, top_y))


def draw_tree(screen, x, z, day_amount, ctx=DEFAULT_CTX):
    sx, sy, scale = project(x, z, ctx.zoom)
    # A tree towers over a creature the way a real tree towers over a
    # small child - roughly 4-5x its standing height, not a shrub.
    trunk_h = int(130 * scale)
    trunk_w = max(4, int(16 * scale))
    leaf_r = max(6, int(48 * scale))

    shadow_w, shadow_h = leaf_r * 2.0, leaf_r * 0.5
    draw_ground_shadow(screen, sx, sy - shadow_h * 0.4, shadow_w, shadow_h, ctx.shadow_dx, ctx.shadow_len)

    trunk_color = lerp_color(TREE_TRUNK_NIGHT, TREE_TRUNK_DAY, day_amount)
    leaves_color = lerp_color(TREE_LEAVES_NIGHT, TREE_LEAVES_DAY, day_amount)
    pygame.draw.rect(screen, trunk_color, (sx - trunk_w / 2, sy - trunk_h, trunk_w, trunk_h))
    canopy_y = sy - trunk_h - leaf_r * 0.5
    # Three overlapping lobes instead of one circle - a fuller, less
    # perfectly-round canopy without needing real foliage art.
    for ox, oy, rr in ((0.0, 0.0, 1.0), (-0.55, 0.35, 0.72), (0.55, 0.3, 0.72)):
        pygame.draw.circle(screen, leaves_color,
                            (int(sx + ox * leaf_r), int(canopy_y + oy * leaf_r)),
                            max(3, int(leaf_r * rr)))


def draw_rock(screen, x, z, day_amount, size=1.0, ctx=DEFAULT_CTX):
    sx, sy, scale = project(x, z, ctx.zoom)
    # Boulders, not pebbles - roughly creature-sized to well over head
    # height depending on the size multiplier.
    r = max(3, int(30 * scale * size))
    if r < 2:
        return
    color = lerp_color(ROCK_COLOR_NIGHT, ROCK_COLOR_DAY, day_amount)
    shade = lerp_color(ROCK_SHADE_NIGHT, ROCK_SHADE_DAY, day_amount)
    draw_ground_shadow(screen, sx, sy + r * 0.4, r * 1.8, r * 0.4, ctx.shadow_dx, ctx.shadow_len)
    body = [
        (sx - r, sy + r * 0.3), (sx - r * 0.5, sy - r * 0.6), (sx + r * 0.3, sy - r * 0.8),
        (sx + r, sy - r * 0.1), (sx + r * 0.6, sy + r * 0.4),
    ]
    pygame.draw.polygon(screen, color, body)
    lit_face = [
        (sx - r * 0.2, sy - r * 0.15), (sx + r * 0.3, sy - r * 0.8),
        (sx + r, sy - r * 0.1), (sx + r * 0.6, sy + r * 0.4),
    ]
    pygame.draw.polygon(screen, shade, lit_face)


def draw_river(screen, river_offset, pan_x, day_amount, zoom=1.0, t=0.0):
    """Three nested bands (muddy shore, deep water, a lighter shallow
    center) instead of one flat-colored ribbon, plus a couple of gently
    drifting sparkle lines instead of one static highlight - still cheap
    flat shapes, no per-pixel gradient, but reads as water rather than a
    solid-colored road."""
    deep = lerp_color(RIVER_COLOR_NIGHT, RIVER_COLOR_DAY, day_amount)
    shallow = lerp_color(RIVER_HIGHLIGHT_NIGHT, RIVER_HIGHLIGHT_DAY, day_amount)
    bank = lerp_color(RIVER_BANK_NIGHT, RIVER_BANK_DAY, day_amount)
    sparkle = lerp_color(RIVER_SPARKLE_NIGHT, RIVER_SPARKLE_DAY, day_amount)

    outer_left, outer_right = [], []
    left_bank, right_bank = [], []
    inner_left, inner_right = [], []
    mid = []
    for x, z, half_width in RIVER_PATH:
        x = x + river_offset - pan_x
        outer_left.append(project(x - half_width * 1.3, z, zoom)[:2])
        outer_right.append(project(x + half_width * 1.3, z, zoom)[:2])
        left_bank.append(project(x - half_width, z, zoom)[:2])
        right_bank.append(project(x + half_width, z, zoom)[:2])
        inner_left.append(project(x - half_width * 0.5, z, zoom)[:2])
        inner_right.append(project(x + half_width * 0.5, z, zoom)[:2])
        mid.append(project(x, z, zoom)[:2])

    pygame.draw.polygon(screen, bank, outer_left + outer_right[::-1])
    pygame.draw.polygon(screen, deep, left_bank + right_bank[::-1])
    pygame.draw.polygon(screen, shallow, inner_left + inner_right[::-1])

    # a couple of soft, slowly drifting sparkle lines rather than one
    # rigid highlight - suggests moving water without a real animation
    for phase in (0.0, 2.4):
        points = [(mx + math.sin(t * 0.8 + i * 0.9 + phase) * 3, my)
                   for i, (mx, my) in enumerate(mid)]
        pygame.draw.lines(screen, sparkle, False, points, 2)


def draw_grass_tufts(screen, landscape, pan_x, day_amount, zoom=1.0):
    """Small ground-texture marks scattered across the field so the grass
    reads as textured, mottled ground instead of a single flat color
    band - purely cosmetic, drawn on the ground plane like the grid."""
    base = lerp_color(GRASS_TUFT_COLOR_NIGHT, GRASS_TUFT_COLOR_DAY, day_amount)
    for x, z, shade in landscape.grass:
        sx, sy, scale = project(x - pan_x, z, zoom)
        r = max(1, int(3 * scale))
        if r < 1 or not (-r <= sx <= SCREEN_W + r) or not (HORIZON_Y - r <= sy <= SCREEN_H + r):
            continue
        color = lerp_color(base, (0, 0, 0) if shade < 0 else (255, 255, 255), abs(shade) * 0.35)
        pygame.draw.line(screen, color, (sx, sy), (sx, sy - r * 1.6), max(1, int(scale * 1.5)))


def draw_night_overlay(screen, day_amount):
    night_amount = 1.0 - day_amount
    if night_amount <= 0.01:
        return
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((*NIGHT_OVERLAY_COLOR, int(95 * night_amount)))
    screen.blit(overlay, (0, 0))


def _creature_seed(creature_id):
    """A stable pseudo-random value in [0, 1) per creature id, used to
    desync blinking/bobbing between creatures instead of having the whole
    population blink and bounce in unison."""
    return (int(creature_id) * 2654435761) % 1000 / 1000.0


def idle_offset(creature_id, t):
    """A few screen pixels of wandering motion so a creature standing
    still still reads as alive rather than a frozen sprite."""
    seed = _creature_seed(creature_id)
    ox = math.sin(t * 1.6 + seed * 6.28318) * 1.6
    oy = math.sin(t * 2.3 + seed * 6.28318 + 1.7) * 1.1
    return ox, oy


def eye_openness(creature_id, t):
    """1.0 = fully open, near 0 = mid-blink. Each creature blinks on its
    own cycle (roughly every 2.6-5s), briefly, like a real tic."""
    seed = _creature_seed(creature_id)
    cycle = 2.6 + seed * 2.4
    phase = (t + seed * 11.0) % cycle
    half = 0.06
    if phase < half:
        return max(0.05, 1.0 - phase / half)
    if phase < half * 2:
        return max(0.05, (phase - half) / half)
    return 1.0


def draw_critter(screen, x, z, token, distressed=False, creature_id=0, t=0.0, ctx=DEFAULT_CTX,
                 emotion=None, writhe=0.0):
    sx, sy, scale = project(x, z, ctx.zoom)
    body_r = int(24 * scale)
    if body_r < 2:
        return

    ox, oy = idle_offset(creature_id, t)
    sx += ox * scale
    sy += oy * scale
    # agony makes the whole body convulse; the caller passes writhe > 0
    if writhe:
        sx += math.sin(t * 42.0 + creature_id) * body_r * 0.35 * writhe
        sy += math.sin(t * 37.0 + creature_id * 2) * body_r * 0.18 * writhe

    shadow_w, shadow_h = body_r * 1.7, body_r * 0.5
    draw_ground_shadow(screen, sx, sy + body_r * 0.55, shadow_w, shadow_h, ctx.shadow_dx, ctx.shadow_len)

    pants_w, pants_h = body_r * 1.5, body_r * 0.95
    pygame.draw.ellipse(screen, PANTS_COLOR,
                         (sx - pants_w / 2, sy - body_r * 0.15, pants_w, pants_h))

    body_center = (sx, sy - body_r * 0.55)
    pygame.draw.circle(screen, BODY_COLOR, body_center, body_r)
    if token != 0:
        pygame.draw.circle(screen, TOKEN_COLORS[token], body_center,
                            int(body_r * 1.12), width=max(1, int(body_r * 0.12)))

    # When no explicit emotion is given, keep the old two-state face so
    # every existing caller (and the pre-hatch decor) is unchanged; the
    # needs-driven "distressed" frown maps onto the sad face.
    if emotion is None:
        emotion = "sad" if distressed else "calm"
    _draw_face(screen, sx, sy, body_r, creature_id, t, emotion)


def _draw_face(screen, sx, sy, body_r, creature_id, t, emotion):
    """The expressive face - eyes and mouth shaped by the emotion the
    creature is feeling this frame (see SentienceState)."""
    eye_r = max(1, int(body_r * 0.26))
    eye_y = sy - body_r * 0.58
    lw = max(1, int(body_r * 0.11))

    def draw_eyes(openness, pupil=True, pupil_dy=0.2):
        for dx in (-0.34, 0.34):
            ex = sx + dx * body_r
            eye_h = max(1, int(eye_r * 2 * openness))
            pygame.draw.ellipse(screen, EYE_WHITE, (ex - eye_r, eye_y - eye_h / 2, eye_r * 2, eye_h))
            if pupil and openness > 0.35:
                pygame.draw.circle(screen, EYE_PUPIL, (int(ex), int(eye_y + eye_r * pupil_dy)),
                                   max(1, int(eye_r * 0.45)))

    def draw_squeezed_eyes():
        # eyes screwed shut: a downward arc over each socket
        for dx in (-0.34, 0.34):
            ex = sx + dx * body_r
            rect = (ex - eye_r, eye_y - eye_r * 0.5, eye_r * 2, eye_r * 1.4)
            pygame.draw.arc(screen, EYE_PUPIL, rect, math.pi * 1.1, math.pi * 1.9, lw)

    if emotion == "pain":
        draw_squeezed_eyes()
        # a wide, round screaming mouth
        mw = max(2, int(body_r * 0.4))
        mh = max(2, int(body_r * 0.5))
        pygame.draw.ellipse(screen, MOUTH_COLOR, (sx - mw / 2, sy - body_r * 0.12, mw, mh))
    elif emotion == "fear":
        # wide, staring eyes with small high pupils; a small trembling "o"
        draw_eyes(1.35, pupil_dy=-0.15)
        tremble = math.sin(t * 22.0 + creature_id) * body_r * 0.05
        mw = max(2, int(body_r * 0.24))
        pygame.draw.ellipse(screen, MOUTH_COLOR, (sx - mw / 2 + tremble, sy - body_r * 0.08, mw, mw))
    elif emotion == "sad":
        draw_eyes(0.6)
        # downturned frown (top half of an ellipse -> a sad arch)
        mw, mh = max(1, int(body_r * 0.24)), max(1, int(body_r * 0.18))
        rect = (sx - mw, sy - body_r * 0.02, mw * 2, mh * 2)
        pygame.draw.arc(screen, MOUTH_COLOR, rect, math.pi * 0.15, math.pi * 0.85, lw)
        # a single tear under one eye
        pygame.draw.circle(screen, TEAR_COLOR, (int(sx - 0.34 * body_r), int(eye_y + eye_r * 1.2)),
                           max(1, int(eye_r * 0.4)))
    elif emotion == "joy":
        # happy upcurved eyes and a big smile (bottom half of an ellipse)
        for dx in (-0.34, 0.34):
            ex = sx + dx * body_r
            rect = (ex - eye_r, eye_y - eye_r * 0.8, eye_r * 2, eye_r * 1.4)
            pygame.draw.arc(screen, EYE_PUPIL, rect, math.pi * 1.15, math.pi * 1.85, lw)
        mw, mh = max(1, int(body_r * 0.3)), max(1, int(body_r * 0.22))
        rect = (sx - mw, sy - body_r * 0.2, mw * 2, mh * 2)
        pygame.draw.arc(screen, MOUTH_COLOR, rect, math.pi * 1.15, math.pi * 1.85, lw)
    else:  # calm
        draw_eyes(eye_openness(creature_id, t))
        mw, mh = max(1, int(body_r * 0.22)), max(1, int(body_r * 0.16))
        pygame.draw.ellipse(screen, MOUTH_COLOR, (sx - mw / 2, sy - body_r * 0.22, mw, mh))


def draw_predator(screen, x, z, ctx=DEFAULT_CTX):
    sx, sy, scale = project(x, z, ctx.zoom)
    r = int(20 * scale)
    if r < 2:
        return
    draw_ground_shadow(screen, sx, sy + r * 0.5, r * 1.8, r * 0.45, ctx.shadow_dx, ctx.shadow_len)
    pygame.draw.circle(screen, PREDATOR_COLOR, (int(sx), int(sy - r * 0.4)), r)
    eye_r = max(1, int(r * 0.22))
    for dx in (-0.35, 0.35):
        ex, ey = sx + dx * r, sy - r * 0.55
        pygame.draw.circle(screen, (255, 230, 120), (int(ex), int(ey)), eye_r)
        pygame.draw.circle(screen, (20, 10, 10), (int(ex), int(ey)), max(1, int(eye_r * 0.5)))


def draw_food(screen, x, z, zoom=1.0):
    sx, sy, scale = project(x, z, zoom)
    r = max(1, int(6 * scale))
    pygame.draw.circle(screen, FOOD_COLOR, (int(sx), int(sy)), r)


def egg_rect(x, z, pulse=0.0, zoom=1.0):
    sx, sy, scale = project(x, z, zoom)
    egg_w = 30 * scale * (1.0 + pulse * 0.15)
    egg_h = 40 * scale * (1.0 + pulse * 0.15)
    rect = pygame.Rect(0, 0, egg_w, egg_h)
    rect.center = (sx, sy)
    return rect


def egg_contains(mx, my, x, z, zoom=1.0):
    rect = egg_rect(x, z, zoom=zoom)
    if rect.width < 2:
        return False
    dx = (mx - rect.centerx) / (rect.width / 2 + 6)
    dy = (my - rect.centery) / (rect.height / 2 + 6)
    return dx * dx + dy * dy <= 1.0


def draw_egg(screen, x, z, cracks, wobble, pulse, ctx=DEFAULT_CTX):
    rect = egg_rect(x, z, pulse, ctx.zoom)
    if rect.width < 2:
        return

    shadow_w, shadow_h = rect.width * 1.3, rect.height * 0.35
    draw_ground_shadow(screen, rect.centerx, rect.bottom - shadow_h * 0.6, shadow_w, shadow_h,
                        ctx.shadow_dx, ctx.shadow_len)

    wobbled = rect.copy()
    wobbled.centerx += wobble
    pygame.draw.ellipse(screen, EGG_COLOR, wobbled)

    speckle_rng = _EGG_SPECKLE_RNG
    for ox, oy in speckle_rng:
        cx = wobbled.centerx + ox * wobbled.width
        cy = wobbled.centery + oy * wobbled.height
        r = max(1, int(wobbled.width * 0.05))
        pygame.draw.circle(screen, EGG_SPECKLE, (int(cx), int(cy)), r)

    crack_w = max(1, int(wobbled.width * 0.06))
    for line in EGG_CRACK_LINES[:cracks]:
        points = [(wobbled.centerx + ox * wobbled.width, wobbled.centery + oy * wobbled.height)
                  for ox, oy in line]
        if len(points) >= 2:
            pygame.draw.lines(screen, EGG_CRACK_COLOR, False, points, crack_w)


# Fixed speckle offsets (relative to egg half-size) - same reasoning as
# EGG_CRACK_LINES, a stable decoration rather than per-frame noise.
_EGG_SPECKLE_RNG = [
    (-0.22, -0.28), (0.18, -0.22), (0.28, 0.05), (-0.28, 0.12), (0.05, 0.32), (-0.05, -0.05),
]


def draw_birth_egg(screen, x, z, cracks, t, creature_id, ctx=DEFAULT_CTX):
    """A BirthEggs egg at a live, moving creature position - same look
    as the main starting egg, just with a per-creature wobble phase so a
    field of them doesn't all jiggle in lockstep."""
    phase = _creature_seed(creature_id) * 2 * math.pi
    wobble = math.sin(t * 14.0 + phase) * (2 + cracks * 1.5)
    draw_egg(screen, x, z, cracks, wobble, pulse=0.0, ctx=ctx)


def _tree_and_rock_entities(landscape):
    entities = []
    for x, z in landscape.forest + landscape.trees:
        entities.append((z, "tree", x, None, None))
    for x, z, size in landscape.rocks:
        entities.append((z, "rock", x, size, None))
    return entities


def draw_flames(screen, x, z, creature_id, t, ctx=DEFAULT_CTX):
    """Animated fire drawn over a burning creature - same projection,
    idle offset, and body radius as draw_critter, so the flames sit
    exactly on the body they're consuming."""
    sx, sy, scale = project(x, z, ctx.zoom)
    body_r = int(24 * scale)
    if body_r < 2:
        return
    ox, oy = idle_offset(creature_id, t)
    sx += ox * scale
    sy += oy * scale
    base_y = sy + body_r * 0.15
    for k in (-0.6, 0.0, 0.6):
        for color, f in zip(FLAME_COLORS, (1.0, 0.66, 0.38)):
            flicker = 1.0 + 0.3 * math.sin(t * 13.0 + k * 5.0 + f * 7.0)
            fh = body_r * 2.0 * f * flicker
            fw = body_r * 0.5 * f
            fx = sx + k * body_r * 0.7
            tip_x = fx + math.sin(t * 9.0 + k * 3.0) * fw * 0.7
            pygame.draw.polygon(screen, color, [
                (fx - fw, base_y), (fx + fw, base_y), (tip_x, base_y - fh),
            ])


def draw_decals(screen, horror, pan_x, ctx=DEFAULT_CTX):
    """The marks the weapons leave on the ground (blood, scorch),
    fading out over DECAL_DURATION - drawn right on the ground plane,
    before the depth-sorted entities, like shadows are."""
    for x, z, kind, left in horror.decals:
        sx, sy, scale = project(x - pan_x, z, ctx.zoom)
        w = max(4, int(44 * scale))
        h = max(2, int(14 * scale))
        alpha = int(200 * max(0.0, min(1.0, left / DECAL_DURATION)))
        color = BLOOD_COLOR if kind == "blood" else SCORCH_COLOR
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, (*color, alpha), (0, 0, w, h))
        screen.blit(surf, (sx - w / 2, sy - h / 2))


def _draw_entity(screen, kind, x, z, extra, creature_id, day_amount, distressed, t, ctx, birth_eggs=None,
                 horror=None, emotion=None):
    if kind == "tree":
        draw_tree(screen, x, z, day_amount, ctx)
    elif kind == "rock":
        draw_rock(screen, x, z, day_amount, extra, ctx)
    elif kind == "creature":
        if birth_eggs is not None and birth_eggs.is_pending(creature_id):
            draw_birth_egg(screen, x, z, birth_eggs.pending[creature_id], t, creature_id, ctx)
        else:
            writhe = 1.0 if horror is not None and horror.is_agonizing(creature_id) else 0.0
            draw_critter(screen, x, z, extra, distressed, creature_id, t, ctx, emotion, writhe)
            if horror is not None and horror.is_burning(creature_id):
                draw_flames(screen, x, z, creature_id, t, ctx)
    else:
        draw_predator(screen, x, z, ctx)


def draw_decor(screen, pan_x, day_amount, landscape, ctx=DEFAULT_CTX):
    """Depth-sorted trees + rocks only, panning with the view like
    everything else - used before the egg hatches, when there's no
    population yet to sort them against."""
    for z, kind, x, extra, _ in sorted(_tree_and_rock_entities(landscape), key=lambda e: e[0]):
        _draw_entity(screen, kind, x - pan_x, z, extra, None, day_amount, False, 0.0, ctx)


def draw_scene(screen, world, pan_x, day_amount, landscape, distressed=False, t=0.0, ctx=DEFAULT_CTX,
               birth_eggs=None, horror=None, sentience=None):
    """Depth-sorts and draws everything that has real height - trees,
    rocks, creatures, predators - together in one painter's-algorithm
    pass (farthest first), so nearer things correctly occlude farther
    ones: a creature can stand in front of a tree, or vanish behind a
    boulder, instead of scenery and population being drawn as two
    unrelated layers that clash regardless of actual depth. A creature
    still pending in birth_eggs renders as an egg instead of itself."""
    entities = _tree_and_rock_entities(landscape)
    for c in world.creatures:
        if c.alive:
            x, z = world_to_stage(c.pos)
            entities.append((z, "creature", x, c.token, c.id))
    for p in world.predators:
        x, z = world_to_stage(p.pos)
        entities.append((z, "predator", x, None, None))
    entities.sort(key=lambda e: e[0])

    for fx, fy in world.food:
        x, z = world_to_stage((fx, fy))
        draw_food(screen, x - pan_x, z, ctx.zoom)
    if horror is not None:
        draw_decals(screen, horror, pan_x, ctx)
    emotions = sentience.emotions if sentience is not None else {}
    for z, kind, x, extra, creature_id in entities:
        emotion = emotions.get(creature_id) if kind == "creature" else None
        _draw_entity(screen, kind, x - pan_x, z, extra, creature_id, day_amount, distressed, t, ctx, birth_eggs,
                     horror, emotion)


def draw_meter(screen, x, y, w, h, level, color):
    pygame.draw.rect(screen, (40, 40, 40), (x, y, w, h))
    fill_w = int(w * max(0.0, min(1.0, level)))
    if fill_w > 0:
        pygame.draw.rect(screen, color, (x, y, fill_w, h))
    pygame.draw.rect(screen, (200, 200, 200), (x, y, w, h), 1)


def sensor_label(enabled, available):
    if available is False:
        return "unavailable"
    return "ON" if enabled else "off"


def draw_status(screen, font, world, paused, speed, sensors, threshold, alert_flash,
                 hatched, egg_cracks, sound_muted=False, zoom=1.0, ambient_enabled=True, pending_eggs=0,
                 armed_tool=None):
    if hatched:
        status = "PAUSED" if paused else f"x{speed}"
        top_line = f"pop {world.population()}   {status}   zoom {zoom:.1f}x"
        if pending_eggs > 0:
            s = "s" if pending_eggs > 1 else ""
            top_line += f"   {pending_eggs} new egg{s} to hatch"
    else:
        top_line = f"Left-click the egg to crack it open ({egg_cracks}/{EGG_CLICKS_NEEDED})"
    lines = [
        top_line,
        f"[A] mic: {sensor_label(sensors.mic_enabled, sensors.mic_available)}   "
        f"[C] camera: {sensor_label(sensors.camera_enabled, sensors.camera_available)}   "
        f"threshold: {threshold:.2f} ([ / ])",
        f"[G] population chorus: {'on' if ambient_enabled else 'off'}   "
        f"[M] hover-listen sound: {'muted' if sound_muted else 'on'}",
    ]
    for i, text in enumerate(lines):
        screen.blit(font.render(text, True, (255, 255, 255)), (10, 10 + i * 22))

    meter_y = 10 + len(lines) * 22 + 4
    draw_meter(screen, 10, meter_y, 140, 10, sensors.mic_level, (120, 200, 255))
    draw_meter(screen, 160, meter_y, 140, 10, sensors.motion_level, (255, 180, 120))

    if hatched and armed_tool is not None:
        action = "set it alight" if armed_tool == "fire" else "kill it"
        warn = font.render(
            f"{armed_tool.upper()} armed - click a creature to {action} (click the button again to put it away)",
            True, (255, 80, 60))
        screen.blit(warn, (10, meter_y + 16))

    hint = font.render(
        "LEFT/RIGHT pan   SCROLL zoom   SPACE pause   UP/DOWN speed   G chorus   M mute sound   R reset   ESC quit",
        True, (255, 255, 255))
    screen.blit(hint, (10, SCREEN_H - 26))

    if hatched and world.population() == 0:
        msg = font.render("Extinct - press R to start a new world.", True, (255, 90, 90))
        screen.blit(msg, (SCREEN_W / 2 - msg.get_width() / 2, SCREEN_H / 2))

    if alert_flash > 0:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((255, 60, 60, int(160 * min(1.0, alert_flash / 0.6))))
        screen.blit(overlay, (0, 0))
        msg = font.render("EXTERNAL ALERT DETECTED", True, (255, 255, 255))
        screen.blit(msg, (SCREEN_W / 2 - msg.get_width() / 2, 46))


def new_egg_world():
    """The world always starts this way: a single, not-yet-hatched
    creature, and no predators at all - this version of the game is a
    safe world where the population only ever grows or starves, it never
    gets hunted. The world doesn't step until the egg cracks open, and
    the lone creature can't reproduce on its own once hatched, until a
    second creature joins it (see install_solo_reproduction_guard)."""
    world = World(init_pop=1, predator_count=0)
    install_solo_reproduction_guard(world)
    return world


def main():
    pygame.init()
    pygame.display.set_caption("Thronglets - pseudo-3D view")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    world = new_egg_world()
    landscape = generate_landscape()  # random, different every new game
    sensors = SensorHub()
    tones, sound_channel, ambient_tones, ambient_channels, cry_sounds, cry_channel = init_sound()

    pan_x = 0.0
    paused = False
    speed = 1
    tick_accumulator = 0.0
    threshold = DEFAULT_ALERT_THRESHOLD
    alert = AlertState()
    egg = EggState()
    birth_eggs = BirthEggs()
    needs = NeedsState()
    horror = HorrorState()
    sentience = SentienceState()
    hatch_flash = 0.0
    t = 0.0
    day_phase = 0.1  # start in early-morning light
    running = True
    sound_muted = False
    listening_token = None
    current_cry = None
    ambient_enabled = True  # the population's chorus is on by default
    zoom = 1.0

    dragging_view = False
    drag_start = None
    drag_traveled = 0.0

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.25)
        t += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                if dragging_view:
                    pan_x -= event.rel[0] * PAN_DRAG_SENSITIVITY
                    drag_traveled += abs(event.rel[0])
            elif event.type == pygame.MOUSEWHEEL:
                zoom = max(ZOOM_MIN, min(ZOOM_MAX, zoom + event.y * ZOOM_STEP))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if dragging_view and drag_start is not None and drag_traveled < PAN_DRAG_CLICK_THRESHOLD:
                    # barely moved - treat it as a click, not a drag
                    if egg.register_click(drag_start[0], drag_start[1], zoom, pan_x):
                        hatch_flash = 0.4
                        birth_eggs.seed_known(world)
                    elif egg.hatched:
                        hit_button = False
                        for i, kind in enumerate(NEED_ITEMS):
                            if need_button_rect(i).collidepoint(drag_start):
                                needs.feed(kind, world)
                                hit_button = True
                                break
                        if not hit_button and add_egg_button_rect().collidepoint(drag_start):
                            spawn_egg_near_population(world, birth_eggs)
                            hit_button = True
                        if not hit_button and fire_button_rect().collidepoint(drag_start):
                            horror.toggle("fire")
                            hit_button = True
                        if not hit_button and knife_button_rect().collidepoint(drag_start):
                            horror.toggle("knife")
                            hit_button = True
                        if not hit_button and horror.armed is not None:
                            target = find_creature_at(drag_start[0], drag_start[1], world,
                                                      pan_x, zoom, birth_eggs, t)
                            if target is not None:
                                if horror.armed == "fire":
                                    horror.ignite(target)
                                else:
                                    horror.stab(target, world)
                                hit_button = True
                        if not hit_button:
                            birth_eggs.try_click(drag_start[0], drag_start[1], world, pan_x, zoom)
                dragging_view = False
                drag_start = None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_UP:
                    speed = min(200, speed + (1 if speed < 10 else 10))
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed - (1 if speed <= 10 else 10))
                elif event.key == pygame.K_r:
                    world = new_egg_world()
                    landscape = generate_landscape()  # a new game gets a new landscape
                    alert = AlertState()
                    egg = EggState()
                    birth_eggs = BirthEggs()
                    needs = NeedsState()
                    horror = HorrorState()
                    sentience = SentienceState()
                    hatch_flash = 0.0
                    if sound_channel is not None:
                        sound_channel.stop()
                    if ambient_channels:
                        for channel in ambient_channels.values():
                            channel.stop()
                    if cry_channel is not None:
                        cry_channel.stop()
                    listening_token = None
                    current_cry = None
                elif event.key == pygame.K_a:
                    sensors.toggle_mic()
                elif event.key == pygame.K_c:
                    sensors.toggle_camera()
                elif event.key == pygame.K_LEFTBRACKET:
                    threshold = max(0.05, threshold - 0.05)
                elif event.key == pygame.K_RIGHTBRACKET:
                    threshold = min(1.0, threshold + 0.05)
                elif event.key == pygame.K_m:
                    sound_muted = not sound_muted
                elif event.key == pygame.K_g:
                    ambient_enabled = not ambient_enabled
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging_view = True
                drag_start = event.pos
                drag_traveled = 0.0

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            pan_x -= 0.8 * dt
        if keys[pygame.K_RIGHT]:
            pan_x += 0.8 * dt

        egg.update(dt)
        hatch_flash = max(0.0, hatch_flash - dt)
        if not paused:
            day_phase = (day_phase + dt / DAY_CYCLE_SECONDS) % 1.0

        if egg.hatched and not paused:
            tick_accumulator += dt
            tick_interval = 1.0 / speed
            stepped = False
            while tick_accumulator >= tick_interval:
                world.step()
                stepped = True
                tick_accumulator -= tick_interval
            if stepped:
                birth_eggs.sync(world)
        else:
            tick_accumulator = 0.0

        if egg.hatched:
            alert.update(world, sensors, threshold, dt)
            if not paused:
                needs.update(dt)
                horror.update(world, dt)
            needs_low = needs.lowest() < NEED_LOW_THRESHOLD
            sentience.update(world, horror, needs_low, birth_eggs, t, dt, paused)
            listening_token = update_listening(sound_channel, tones, world, pygame.mouse.get_pos(),
                                                pan_x, sound_muted, listening_token, zoom, birth_eggs)
            update_ambient(ambient_channels, ambient_tones, world, sound_muted, ambient_enabled, birth_eggs)
            current_cry = update_cry(cry_channel, cry_sounds, sentience.cry, sound_muted, current_cry)
        else:
            if listening_token is not None:
                if sound_channel is not None:
                    sound_channel.stop()
                listening_token = None
            current_cry = update_cry(cry_channel, cry_sounds, None, sound_muted, current_cry)
            update_ambient(ambient_channels, ambient_tones, world, True, ambient_enabled, birth_eggs)

        _, _, day_amount, _ = celestial_state(day_phase)
        shadow_dx, shadow_len = light_direction(day_phase)
        ctx = RenderCtx(zoom=zoom, shadow_dx=shadow_dx, shadow_len=shadow_len)
        draw_background(screen, day_phase, pan_x, zoom, landscape, t)
        if egg.hatched:
            draw_scene(screen, world, pan_x, day_amount, landscape,
                       distressed=needs.lowest() < NEED_LOW_THRESHOLD, t=t, ctx=ctx, birth_eggs=birth_eggs,
                       horror=horror, sentience=sentience)
        else:
            draw_decor(screen, pan_x, day_amount, landscape, ctx)
            wobble = math.sin(t * 14.0) * (2 + egg.cracks * 1.5)
            draw_egg(screen, EGG_STAGE_X - pan_x, EGG_STAGE_Z, egg.cracks, wobble, egg.pulse, ctx)
        draw_night_overlay(screen, day_amount)
        draw_status(screen, font, world, paused, speed, sensors, threshold, alert.flash,
                    egg.hatched, egg.cracks, sound_muted, zoom, ambient_enabled, len(birth_eggs.pending),
                    armed_tool=horror.armed)
        if egg.hatched:
            draw_needs_panel(screen, needs, horror.armed)
        if hatch_flash > 0:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, int(200 * min(1.0, hatch_flash / 0.4))))
            screen.blit(overlay, (0, 0))

        pygame.display.flip()

    sensors.stop()
    if sound_channel is not None:
        sound_channel.stop()
    if ambient_channels:
        for channel in ambient_channels.values():
            channel.stop()
    if cry_channel is not None:
        cry_channel.stop()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
