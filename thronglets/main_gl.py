"""A *true* 3D proof-of-concept renderer for the Thronglets world.

The other renderers in this project are 2D: main.py and main_web.py draw
flat. This file is different - it is real
3D: an OpenGL scene with a perspective camera you can orbit, a lit procedural
mountain terrain mesh, three-dimensional trees and rocks, and the creatures
as big coloured heads on two little feet - the head's colour is the signal
each creature is currently emitting (the same 6-token palette as every
other renderer). Nothing here is a 2D blit.

On top of the base scene it has a full **day/night cycle, seasons and
weather**, driven by the 3D lighting instead of flat tints:

  * Day/night: the sun (and, once it sets, the moon) travels a real arc
    across the sky. The whole scene is lit from that moving body, the sky
    gradient shifts from dawn orange through midday blue to a starry night,
    and the fog picks up the horizon colour so distance always matches the
    hour.
  * Seasons: spring / summer / autumn / winter each recolour the canopies
    and the ground - fresh green, deep green, autumn orange, and a
    snow-dusted white winter with a white ground. Seasonal ground life grows
    too: flowers bloom in spring and summer, red-capped mushrooms come up in
    autumn, and the winter terrain is shaded as drifting snow.
  * Weather: clear / rain / snow. Rain and snow are real 3D particles
    falling around the camera; both overcast the sky and dim the light,
    and snow whitens the world further.

The world starts empty: you lay the first two eggs yourself by right-
clicking the ground, and they hatch after a few seconds; every creature
born from reproduction afterwards also arrives as an egg that hatches on
its own.

The creatures learn who you are (the opt-in Mind in simulation.py): the
mouse cursor is your hand. Left-click a creature to select it; right-click
it for a menu of care acts (feed / wash / play) and the episode's dark side
(stab / burn / hit with a rock). Kind acts teach it - and the creatures
near enough to witness them - to approach; cruel ones teach fear, and kill
with an animation (a knife-stab shudder, a burning creature wreathed in
flame, a rock that squashes it flat). Each creature has an expressive little face (white
eyes with pupils, a nose, a mouth) that shifts with its emotion, and a 2D
HUD shows the flock's feeling toward you plus a panel for the selected one.
The scene has small touches of life too: the canopies sway, the creatures
bob, birds drift overhead, the lake reflects the sky, and shadows lengthen
with the low sun. The simulation itself is the real thing: it reuses
simulation.World, so the creatures you see are real, stepped every frame.

Rendering goes through moderngl (OpenGL 3.3 core). On a normal machine
pygame opens the window and moderngl draws into it; run it with:

    python3 main_gl.py

Controls: LEFT-drag orbits the camera, scroll wheel zooms, left-CLICK a
creature to select it, right-click a creature for its care/harm menu,
right-click bare ground to lay one of the first two eggs, S cycles the
season, W cycles the weather, T toggles fast time, and the day/night cycle
runs on its own. Press ESC or close the window to quit.

Because this environment has no GPU, the scene can also be rendered
off-screen into a PNG for verification (render_headless), which is how the
look was checked - Mesa's software rasterizer (llvmpipe) under a virtual
framebuffer produces the exact same image a GPU would.
"""

import math
import sys

import numpy as np

import simulation
import tuning
from i18n import disposition_label
from simulation import (ACT_APPROACH, ACT_FLEE, ACT_IGNORE, N_TOKENS,
                        WIDTH, HEIGHT, MAX_ENERGY, World,
                        MEM_ROWS, MEM_COLS, MEM_CLIP, _mem_cell_center)

# The same 6-token palette as every other renderer, as 0..1 floats so a
# creature's colour means the same thing here as in every other renderer.
TOKEN_COLORS = [
    (120, 120, 120),
    (235, 70, 70),
    (70, 140, 235),
    (245, 200, 60),
    (200, 90, 230),
    (70, 225, 210),
]
TOKEN_COLORS_F = [(r / 255.0, g / 255.0, b / 255.0) for r, g, b in TOKEN_COLORS]

TRUNK_COLOR = (0.38, 0.26, 0.15)
ROCK_COLOR = (0.48, 0.48, 0.53)
# A creature is just a big head on two little feet, coloured by the signal
# it's currently emitting (TOKEN_COLORS_F) - so its colour is its status.
EYE_COLOR = (0.08, 0.08, 0.10)

# Emergent learning (the opt-in Mind in simulation.py): the mouse cursor is
# the player's hand. Left-click selects; right-click opens a care/harm menu.
# Kind acts teach a creature (and its witnesses) to approach; cruel ones to
# flee.
LEARN_FEED_REWARD = 1.0
LEARN_CARE_REWARD = 0.3
LEARN_HARM_REWARD = -1.0
FEED_ENERGY = 40.0

# eggs: the first two are laid by the player (right-click the ground), and
# every creature born afterwards also arrives as an egg that hatches on its own
EGG_COLOR = (0.93, 0.89, 0.74)
EGG_SPOT_COLOR = (0.80, 0.72, 0.50)
HATCH_TIME = 6.0          # seconds an egg takes to hatch
MANUAL_EGGS = 2           # how many the player places by hand before it's automatic

# how long a creature takes to die from each harm, with its own animation
DYING_DUR = {"knife": 1.6, "fire": 2.0, "rock": 0.5}
FLAME_COLORS = ((1.0, 0.55, 0.12), (1.0, 0.80, 0.25))

# expressive face palette
SCLERA_COLOR = (0.97, 0.97, 0.99)
PUPIL_COLOR = (0.05, 0.05, 0.08)
NOSE_COLOR = (0.90, 0.68, 0.16)
MOUTH_COLOR = (0.40, 0.16, 0.14)

# per-emotion face parameters: pupil vertical shift, sclera scale, and the
# mouth's (width, height, forward) scale + vertical shift
EMOTION_FACE = {
    "neutral": dict(pupil_dy=0.0, sclera=1.0, mouth=(0.55, 0.18, 0.42), mouth_dy=0.0),
    "joy":     dict(pupil_dy=0.05, sclera=1.05, mouth=(0.75, 0.40, 0.45), mouth_dy=0.02),
    "sad":     dict(pupil_dy=-0.05, sclera=0.95, mouth=(0.42, 0.16, 0.40), mouth_dy=-0.10),
    "fear":    dict(pupil_dy=0.0, sclera=1.30, mouth=(0.42, 0.52, 0.42), mouth_dy=-0.06),
}

# HUD text colours for the named emotions (the selected-creature mood line)
MOOD_HUD_COLORS = {
    "joy": (150, 220, 140), "neutral": (225, 225, 215),
    "sad": (140, 170, 220), "fear": (230, 130, 120),
}



# The right-click menu: three kind acts, then three from the episode's dark
# side. (label, kind, is_danger)
MENU_ROWS = [
    ("Feed", "feed", False),
    ("Wash", "wash", False),
    ("Play", "play", False),
    ("Stab", "knife", True),
    ("Burn", "fire", True),
    ("Hit with a rock", "rock", True),
]
MENU_W, MENU_ROW_H = 210, 28


class ContextMenu:
    """A tiny 2D right-click menu drawn into the HUD overlay."""

    def __init__(self):
        self.open = False
        self.pos = (0, 0)
        self.cid = None

    def show(self, pos, cid, screen):
        x = max(0, min(pos[0], screen[0] - MENU_W))
        y = max(0, min(pos[1], screen[1] - MENU_ROW_H * len(MENU_ROWS)))
        self.pos, self.cid, self.open = (x, y), cid, True

    def close(self):
        self.open = False
        self.cid = None

    def row_at(self, mx, my):
        if not self.open:
            return None
        x, y = self.pos
        if x <= mx <= x + MENU_W and y <= my <= y + MENU_ROW_H * len(MENU_ROWS):
            return int((my - y) // MENU_ROW_H)
        return None

    def draw(self, surf, font):
        import pygame
        if not self.open:
            return
        x, y = self.pos
        h = MENU_ROW_H * len(MENU_ROWS)
        panel = pygame.Surface((MENU_W, h), pygame.SRCALPHA)
        panel.fill((12, 16, 22, 225))
        pygame.draw.rect(panel, (110, 210, 130), panel.get_rect(), 1)
        for i, (label, _kind, danger) in enumerate(MENU_ROWS):
            col = (235, 120, 110) if danger else (215, 235, 220)
            panel.blit(font.render(label, True, col), (12, i * MENU_ROW_H + 6))
            if i:
                pygame.draw.line(panel, (60, 70, 66), (6, i * MENU_ROW_H),
                                 (MENU_W - 6, i * MENU_ROW_H), 1)
        surf.blit(panel, (x, y))


def apply_action(world, renderer, cid, kind):
    """Run a care/harm menu action on the creature with id cid."""
    c = next((c for c in world.creatures if c.id == cid and c.alive), None)
    if c is None:
        return
    if kind == "feed":
        c.energy = min(MAX_ENERGY, c.energy + FEED_ENERGY)
        world.deliver_experience(c, LEARN_FEED_REWARD)
        renderer.set_emotion(cid, "joy")
    elif kind in ("wash", "play"):
        world.deliver_experience(c, LEARN_CARE_REWARD)
        renderer.set_emotion(cid, "joy")
    else:  # knife / fire / rock - the dark side: teach fear, then die (animated)
        world.deliver_experience(c, LEARN_HARM_REWARD)
        renderer.set_emotion(cid, "fear", DYING_DUR[kind] + 0.3)
        renderer.start_dying(cid, kind)


class EggState:
    """Tracks which creatures are still unhatched eggs. A laid egg is set
    dormant in the World (it doesn't move, eat or reproduce) and hatches -
    waking up - after HATCH_TIME."""

    def __init__(self):
        self.eggs = {}       # cid -> seconds left before hatching
        self.manual = 0      # how many the player has laid by hand

    def lay(self, world, cid, manual):
        world.set_dormant(cid, True)
        self.eggs[cid] = HATCH_TIME
        if manual:
            self.manual += 1

    def update(self, dt, world):
        for cid in list(self.eggs):
            self.eggs[cid] -= dt
            if self.eggs[cid] <= 0.0:
                world.set_dormant(cid, False)   # hatch
                del self.eggs[cid]

    def is_egg(self, cid):
        return cid in self.eggs

    def progress(self, cid):
        return 1.0 - max(0.0, self.eggs.get(cid, 0.0)) / HATCH_TIME
FLOWER_COLORS = ((0.96, 0.34, 0.52), (0.98, 0.82, 0.24), (0.72, 0.46, 0.95))
FLOWER_STEM_COLOR = (0.16, 0.42, 0.12)
FLOWER_CENTER_COLOR = (0.99, 0.86, 0.30)   # sunny disc floret at the heart
MUSHROOM_CAP_COLOR = (0.72, 0.13, 0.06)
MUSHROOM_STEM_COLOR = (0.82, 0.74, 0.56)
MUSHROOM_SPOT_COLOR = (0.97, 0.96, 0.92)   # the classic white cap dots
FOG_DENSITY = 0.0030

# world (200 x 140) -> a centred patch of the terrain
WORLD_SCALE = 0.9

# The terrain covers more than the visible simulation world so the horizon
# remains mountainous while the camera orbits.  Keeping the simulation's
# centre comparatively gentle makes it a useful playable valley.
TERRAIN_SIZE = 600.0
TERRAIN_CELLS = 144

# A sheltered lake is carved directly into the height field, so its water
# never looks like a flat sheet laid across hills.
WATER_LEVEL = 0.35
# Keep the terrain floor below the animated water surface.  Without this
# clearance, wave vertices intermittently cross the terrain depth buffer.
WATER_BED_LEVEL = WATER_LEVEL - 0.65
LAKE_CENTER = (48.0, -38.0)
LAKE_RADII = (38.0, 25.0)

# --- seasons: canopy + ground colours -----------------------------------
SEASONS = ["spring", "summer", "autumn", "winter"]
SEASON_CANOPY = {
    "spring": (0.32, 0.58, 0.22),
    "summer": (0.14, 0.38, 0.14),
    "autumn": (0.80, 0.44, 0.12),
    "winter": (0.82, 0.86, 0.90),
}
SEASON_CROWN = {
    "spring": (0.42, 0.66, 0.30),
    "summer": (0.20, 0.46, 0.19),
    "autumn": (0.90, 0.60, 0.22),
    "winter": (0.92, 0.95, 0.98),
}
SEASON_GROUND = {
    "spring": (0.30, 0.55, 0.24),
    "summer": (0.24, 0.48, 0.20),
    "autumn": (0.44, 0.45, 0.20),
    "winter": (0.86, 0.90, 0.95),
}

# --- weather: how much it dims and fogs the world -----------------------
WEATHERS = ["clear", "rain", "snow"]
WEATHER = {
    #            light   fog x   overcast(0..1)   precip
    "clear": dict(light=1.00, fog=1.0, overcast=0.0, precip=None),
    "rain":  dict(light=0.55, fog=2.1, overcast=0.85, precip="rain"),
    "snow":  dict(light=0.78, fog=1.7, overcast=0.65, precip="snow"),
}

# --- day/night keyframes (by sun height, -1..1) -------------------------
SKY_DAY_ZEN = (0.20, 0.48, 0.86)
SKY_DAY_HOR = (0.72, 0.83, 0.94)
SKY_DUSK_ZEN = (0.22, 0.20, 0.42)
SKY_DUSK_HOR = (0.96, 0.55, 0.26)
SKY_NIGHT_ZEN = (0.02, 0.03, 0.10)
SKY_NIGHT_HOR = (0.05, 0.07, 0.18)
LIGHT_DAY = (1.05, 0.99, 0.86)
LIGHT_DUSK = (1.02, 0.60, 0.34)
LIGHT_MOON = (0.42, 0.50, 0.72)
AMBIENT_DAY = (0.32, 0.38, 0.48)
AMBIENT_NIGHT = (0.09, 0.11, 0.19)


def _mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def environment(phase, season, weather):
    """Turn (phase 0..1, season, weather) into every colour/vector the
    scene needs. phase: 0=midnight, .25=sunrise, .5=noon, .75=sunset."""
    wx = WEATHER[weather]
    # sun arc: elevation sin peaks at noon; azimuth sweeps east->west by day
    sun_h = math.sin(2 * math.pi * (phase - 0.25))        # -1..1
    az = math.pi * ((phase - 0.25) % 1.0)                 # 0..pi across the sky
    ce = max(math.cos(2 * math.pi * (phase - 0.25)), 0.0)
    horiz = math.sqrt(max(1.0 - sun_h * sun_h, 1e-4))
    sun_dir = (math.cos(az) * horiz, sun_h, math.sin(az) * horiz)
    # the moon is the sun's antipode - it rises as the sun sets
    moon_dir = (-sun_dir[0], -sun_dir[1], -sun_dir[2])

    day = max(sun_h, 0.0)                                  # 0 at/below horizon
    dusk = 1.0 - min(abs(sun_h) / 0.35, 1.0)              # 1 near the horizon
    night = max(-sun_h, 0.0)

    if sun_h >= 0.0:
        zen = _mix(SKY_DUSK_ZEN, SKY_DAY_ZEN, day)
        hor = _mix(SKY_DUSK_HOR, SKY_DAY_HOR, day)
    else:
        # Keep only a short blue-hour transition.  The previous mix used the
        # raw night value, leaving the orange sunset palette visible long
        # after the moon had risen.
        night_mix = min(max((night + 0.06) / 0.12, 0.0), 1.0)
        zen = _mix(SKY_DUSK_ZEN, SKY_NIGHT_ZEN, night_mix)
        hor = _mix(SKY_DUSK_HOR, SKY_NIGHT_HOR, night_mix)

    # overcast greys the sky out
    grey = (0.55, 0.57, 0.60)
    oc = wx["overcast"]
    zen = _mix(zen, grey, oc)
    hor = _mix(hor, grey, oc)

    # light: sun colour by day (warm at the horizon), moonlight by night
    if sun_h >= 0.0:
        lcol = _mix(LIGHT_DUSK, LIGHT_DAY, day)
        intensity = (0.15 + 0.85 * day) * wx["light"]
        body_dir, body_up = sun_dir, sun_h > -0.04
        body_col = (1.0, 0.95, 0.80)
    else:
        lcol = LIGHT_MOON
        intensity = (0.12 + 0.10 * night) * wx["light"]
        body_dir, body_up = moon_dir, True
        body_col = (0.85, 0.90, 1.0)
    light_col = tuple(c * intensity for c in lcol)
    ambient = _mix(AMBIENT_NIGHT, AMBIENT_DAY, day)
    ambient = tuple(c * (0.6 + 0.4 * wx["light"]) for c in ambient)

    return dict(
        sun_h=sun_h, sun_dir=sun_dir, moon_dir=moon_dir,
        light_dir=(sun_dir if sun_h >= 0.0 else moon_dir),
        light_col=light_col, ambient=ambient,
        zenith=zen, horizon=hor, fog_col=hor,
        fog_density=FOG_DENSITY * wx["fog"],
        night=night, dusk=dusk,
        body_dir=body_dir, body_up=body_up, body_col=body_col,
        canopy=SEASON_CANOPY[season], crown=SEASON_CROWN[season],
        ground=SEASON_GROUND[season], precip=wx["precip"],
        season=season,
        bare=(season == "winter"),
    )


# =========================================================================
# tiny column-vector matrix maths (numpy, row-major; transposed on upload)
# =========================================================================
def _identity():
    return np.identity(4, dtype=np.float32)


def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2.0)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def look_at(eye, center, up):
    eye = np.asarray(eye, dtype=np.float64)
    center = np.asarray(center, dtype=np.float64)
    up = np.asarray(up, dtype=np.float64)
    f = center - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.identity(4, dtype=np.float32)
    m[0, :3] = s
    m[1, :3] = u
    m[2, :3] = -f
    m[0, 3] = -np.dot(s, eye)
    m[1, 3] = -np.dot(u, eye)
    m[2, 3] = np.dot(f, eye)
    return m


def translate(x, y, z):
    m = _identity()
    m[0, 3] = x
    m[1, 3] = y
    m[2, 3] = z
    return m


def scale(sx, sy, sz):
    m = _identity()
    m[0, 0] = sx
    m[1, 1] = sy
    m[2, 2] = sz
    return m


def rotate_y(rad):
    c, s = math.cos(rad), math.sin(rad)
    m = _identity()
    m[0, 0] = c
    m[0, 2] = s
    m[2, 0] = -s
    m[2, 2] = c
    return m


def _bytes(m):
    """moderngl mat4 uniforms are column-major; our matrices are the usual
    row-major v' = M v, so upload the transpose."""
    return m.T.astype("f4").tobytes()


# =========================================================================
# meshes  (interleaved position(3) + normal(3), float32)
# =========================================================================
def terrain_water_mask(x, z):
    """Return 0 on dry land and 1 across the lake bed."""
    x = np.asarray(x, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    lake_x = (x - LAKE_CENTER[0]) / LAKE_RADII[0]
    lake_z = (z - LAKE_CENTER[1]) / LAKE_RADII[1]
    lake_distance = lake_x * lake_x + lake_z * lake_z
    lake_mask = np.clip((1.0 - lake_distance) * 12.0, 0.0, 1.0)
    return lake_mask


def terrain_height(x, z):
    """Return the procedural terrain elevation at a scene-space position.

    Broad Gaussian massifs give the landscape recognisable mountain ranges;
    layered waves add ridges and rolling ground without needing an external
    heightmap.  The central valley stays low enough for the simulation.
    """
    x = np.asarray(x, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    rolling = (
        3.5 * np.sin(x * 0.055 + z * 0.021)
        + 2.2 * np.cos(z * 0.081 - x * 0.017)
        + 1.1 * np.sin((x + z) * 0.19)
    )
    massifs = (
        68.0 * np.exp(-(((x + 165.0) / 76.0) ** 2 + ((z + 125.0) / 62.0) ** 2))
        + 60.0 * np.exp(-(((x - 145.0) / 70.0) ** 2 + ((z - 105.0) / 78.0) ** 2))
        + 48.0 * np.exp(-(((x + 120.0) / 64.0) ** 2 + ((z - 155.0) / 70.0) ** 2))
        + 42.0 * np.exp(-(((x - 20.0) / 125.0) ** 2 + ((z + 245.0) / 60.0) ** 2))
    )
    height = rolling + massifs

    # Smoothly flatten the basin into a lake and cut a narrow, winding outlet
    # towards the east.  The high exponent keeps a readable shoreline.
    water_mask = terrain_water_mask(x, z)
    return height * (1.0 - water_mask) + WATER_BED_LEVEL * water_mask


def terrain_normal(x, z, step=0.5):
    """Sample an upward-facing normal from the same height field."""
    dx = (terrain_height(x + step, z) - terrain_height(x - step, z)) / (2.0 * step)
    dz = (terrain_height(x, z + step) - terrain_height(x, z - step)) / (2.0 * step)
    normal = np.array([-dx, 1.0, -dz], dtype=np.float64)
    return normal / np.linalg.norm(normal)


def mesh_terrain(size=TERRAIN_SIZE, cells=TERRAIN_CELLS):
    """Build a triangle terrain mesh with smooth normals per grid vertex."""
    axis = np.linspace(-size / 2.0, size / 2.0, cells + 1, dtype=np.float64)
    xx, zz = np.meshgrid(axis, axis, indexing="ij")
    yy = terrain_height(xx, zz)
    spacing = axis[1] - axis[0]
    d_height_dx, d_height_dz = np.gradient(yy, spacing, spacing)
    normals = np.stack((-d_height_dx, np.ones_like(yy), -d_height_dz), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    vertices = np.dstack((xx, yy, zz, normals)).astype("f4")

    # Counter-clockwise triangles viewed from above: OpenGL can cull these
    # safely later without changing the generated terrain.
    a = vertices[:-1, :-1]
    b = vertices[1:, :-1]
    c = vertices[1:, 1:]
    d = vertices[:-1, 1:]
    tris = np.empty((cells, cells, 6, 6), dtype="f4")
    tris[:, :, 0], tris[:, :, 1], tris[:, :, 2] = a, c, b
    tris[:, :, 3], tris[:, :, 4], tris[:, :, 5] = a, d, c
    return tris.reshape(-1, 6)


def mesh_uv_sphere(radius=1.0, stacks=16, slices=24, jitter=0.0, seed=0):
    """A unit-ish sphere. jitter>0 roughens the radius per-vertex for a
    faceted rock; seed keeps a given rock stable."""
    rng = np.random.default_rng(seed)
    grid = {}

    def vert(i, j):
        key = (i, j)
        if key not in grid:
            phi = math.pi * i / stacks
            theta = 2 * math.pi * j / slices
            nx = math.sin(phi) * math.cos(theta)
            ny = math.cos(phi)
            nz = math.sin(phi) * math.sin(theta)
            r = radius
            if jitter:
                r *= 1.0 + jitter * (rng.random() - 0.5)
            grid[key] = ((nx * r, ny * r, nz * r), (nx, ny, nz))
        return grid[key]

    tris = []
    for i in range(stacks):
        for j in range(slices):
            a = vert(i, j)
            b = vert(i + 1, j)
            c = vert(i + 1, j + 1)
            d = vert(i, j + 1)
            for (p, nn) in (a, b, c, a, c, d):
                tris.append((*p, *nn))
    return np.array(tris, dtype="f4")


def mesh_cylinder(radius=1.0, height=1.0, slices=18):
    tris = []
    for j in range(slices):
        t0 = 2 * math.pi * j / slices
        t1 = 2 * math.pi * (j + 1) / slices
        x0, z0 = math.cos(t0), math.sin(t0)
        x1, z1 = math.cos(t1), math.sin(t1)
        p00 = (x0 * radius, 0.0, z0 * radius)
        p01 = (x0 * radius, height, z0 * radius)
        p10 = (x1 * radius, 0.0, z1 * radius)
        p11 = (x1 * radius, height, z1 * radius)
        n0 = (x0, 0.0, z0)
        n1 = (x1, 0.0, z1)
        tris += [(*p00, *n0), (*p10, *n1), (*p11, *n1),
                 (*p00, *n0), (*p11, *n1), (*p01, *n0)]
    return np.array(tris, dtype="f4")


def mesh_disc(radius=1.0, slices=28):
    """A flat circle in the XZ plane, normal up - used for contact shadows."""
    tris = []
    n = (0.0, 1.0, 0.0)
    for j in range(slices):
        t0 = 2 * math.pi * j / slices
        t1 = 2 * math.pi * (j + 1) / slices
        p0 = (math.cos(t0) * radius, 0.0, math.sin(t0) * radius)
        p1 = (math.cos(t1) * radius, 0.0, math.sin(t1) * radius)
        tris += [(0.0, 0.0, 0.0, *n), (*p0, *n), (*p1, *n)]
    return np.array(tris, dtype="f4")


def mesh_lake(slices=72):
    """Triangle fan for the calm lake surface."""
    verts = []
    cx, cz = LAKE_CENTER
    rx, rz = LAKE_RADII
    for i in range(slices):
        a0 = math.tau * i / slices
        a1 = math.tau * (i + 1) / slices
        verts.extend(((cx, WATER_LEVEL, cz),
                      (cx + math.cos(a0) * rx, WATER_LEVEL, cz + math.sin(a0) * rz),
                      (cx + math.cos(a1) * rx, WATER_LEVEL, cz + math.sin(a1) * rz)))
    return np.asarray(verts, dtype="f4")


def mesh_flower_petals(petals=6, ring=0.46, petal_r=0.30):
    """A ring of flattened little spheres - the petals of one flower, baked
    into a single mesh so a whole blossom is just one draw call."""
    base = mesh_uv_sphere(petal_r, 5, 7)
    out = []
    for k in range(petals):
        a = 2 * math.pi * k / petals
        ox, oz = math.cos(a) * ring, math.sin(a) * ring
        for v in base:
            out.append((v[0] + ox, v[1] * 0.45, v[2] + oz, v[3], v[4], v[5]))
    return np.array(out, dtype="f4")


# =========================================================================
# shaders
# =========================================================================
LIT_VERT = """
#version 330
uniform mat4 mvp;
uniform mat4 model;
in vec3 in_pos;
in vec3 in_norm;
out vec3 v_world;
out vec3 v_norm;
void main() {
    vec4 wp = model * vec4(in_pos, 1.0);
    v_world = wp.xyz;
    v_norm = mat3(model) * in_norm;
    gl_Position = mvp * vec4(in_pos, 1.0);
}
"""

LIT_FRAG = """
#version 330
uniform vec3 u_color;
uniform vec3 u_lightdir;
uniform vec3 u_lightcol;
uniform vec3 u_ambient;
uniform vec3 u_fogcol;
uniform vec3 u_campos;
uniform float u_fogdensity;
uniform int u_grid;
uniform float u_snowcover;
in vec3 v_world;
in vec3 v_norm;
out vec4 f_color;
void main() {
    vec3 n = normalize(v_norm);
    float diff = max(dot(n, normalize(u_lightdir)), 0.0);
    vec3 base = u_color;
    if (u_grid == 1) {
        if (u_snowcover > 0.5) {
            // Fine powder, shallow wind drifts, and a cool tint in the
            // hollows make the winter terrain read as accumulated snow.
            float grain = fract(sin(dot(floor(v_world.xz * 5.0), vec2(127.1, 311.7))) * 43758.5453);
            float drift = sin(v_world.x * 0.055) * cos(v_world.z * 0.047) * 0.5 + 0.5;
            vec3 powder = mix(vec3(0.72, 0.80, 0.91), vec3(0.98, 0.99, 1.0), drift);
            base = mix(powder, vec3(1.0), smoothstep(0.94, 1.0, grain) * 0.14);
        } else {
            // gentle tonal variation instead of a hard grid, so the ground
            // reads as textured turf rather than wireframe
            float grain = fract(sin(dot(floor(v_world.xz * 2.5), vec2(127.1, 311.7))) * 43758.5453);
            float mott = sin(v_world.x * 0.11) * cos(v_world.z * 0.09) * 0.5 + 0.5;
            base *= 0.93 + 0.10 * mix(grain, mott, 0.5);
        }
    }
    vec3 col = base * (u_ambient + u_lightcol * diff);
    float dist = length(v_world - u_campos);
    float fog = clamp(1.0 - exp(-u_fogdensity * dist), 0.0, 1.0);
    col = mix(col, u_fogcol, fog);
    f_color = vec4(col, 1.0);
}
"""

SHADOW_VERT = """
#version 330
uniform mat4 mvp;
in vec3 in_pos;
void main() { gl_Position = mvp * vec4(in_pos, 1.0); }
"""

SHADOW_FRAG = """
#version 330
uniform vec4 u_color;
out vec4 f_color;
void main() { f_color = u_color; }
"""

SKY_VERT = """
#version 330
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

SKY_FRAG = """
#version 330
uniform vec3 u_zenith;
uniform vec3 u_horizon;
uniform vec2 u_body;
uniform vec3 u_bodycol;
uniform float u_night;
in vec2 v_uv;
out vec4 f_color;
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void main() {
    float t = pow(clamp(v_uv.y, 0.0, 1.0), 0.8);
    vec3 col = mix(u_horizon, u_zenith, t);
    // sun / moon: a bright disc plus a soft glow
    float d = distance(v_uv, u_body);
    col += u_bodycol * exp(-d * d * 700.0);          // the disc
    col += u_bodycol * exp(-d * d * 45.0) * 0.7;     // the glow
    // stars come out at night, only in the upper sky
    if (u_night > 0.02 && v_uv.y > 0.35) {
        vec2 g = floor(v_uv * vec2(240.0, 150.0));
        float s = step(0.9965, hash(g));
        col += vec3(s) * u_night * (v_uv.y - 0.35) * 1.6;
    }
    f_color = vec4(col, 1.0);
}
"""

PARTICLE_VERT = """
#version 330
uniform mat4 mvp;
uniform float u_size;
in vec3 in_pos;
void main() {
    gl_Position = mvp * vec4(in_pos, 1.0);
    gl_PointSize = u_size;
}
"""

PARTICLE_FRAG = """
#version 330
uniform vec4 u_color;
out vec4 f_color;
void main() { f_color = u_color; }
"""

OVERLAY_VERT = """
#version 330
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

OVERLAY_FRAG = """
#version 330
uniform sampler2D u_tex;
in vec2 v_uv;
out vec4 f_color;
void main() { f_color = texture(u_tex, v_uv); }
"""

WATER_VERT = """
#version 330
uniform mat4 mvp;
uniform float u_time;
in vec3 in_pos;
out vec3 v_world;
void main() {
    vec3 p = in_pos;
    p.y += sin(p.x * 0.22 + u_time * 1.8) * 0.16;
    p.y += cos(p.z * 0.31 - u_time * 1.25) * 0.10;
    v_world = p;
    gl_Position = mvp * vec4(p, 1.0);
}
"""

WATER_FRAG = """
#version 330
uniform vec3 u_lightdir;
uniform vec3 u_lightcol;
uniform vec3 u_fogcol;
uniform vec3 u_campos;
uniform vec3 u_zenith;
uniform vec3 u_horizon;
uniform float u_fogdensity;
uniform float u_time;
in vec3 v_world;
out vec4 f_color;
void main() {
    vec3 n = normalize(vec3(
        -0.035 * cos(v_world.x * 0.22 + u_time * 1.8), 1.0,
         0.031 * sin(v_world.z * 0.31 - u_time * 1.25)));
    vec3 view_dir = normalize(u_campos - v_world);
    vec3 half_dir = normalize(view_dir + normalize(u_lightdir));
    float sparkle = pow(max(dot(n, half_dir), 0.0), 58.0);
    // Fake depth from the lake footprint: pale shallows at the bank, then a
    // dense blue centre that reads as genuinely deep water.
    vec2 lake_pos = (v_world.xz - vec2(48.0, -38.0)) / vec2(38.0, 25.0);
    float depth = clamp(1.0 - length(lake_pos), 0.0, 1.0);
    float ripple = sin(v_world.x * 0.45 + v_world.z * 0.23 + u_time * 2.2) * 0.025;
    vec3 water = mix(vec3(0.06, 0.34, 0.42), vec3(0.008, 0.055, 0.14), depth);
    water += ripple;
    // reflect the sky: more mirror-like at grazing angles (Fresnel), so the
    // lake picks up the zenith/horizon colours of the current hour
    float fres = pow(1.0 - clamp(view_dir.y, 0.0, 1.0), 3.0);
    vec3 sky_refl = mix(u_horizon, u_zenith, clamp(view_dir.y * 1.3, 0.0, 1.0));
    water = mix(water, sky_refl, fres * 0.65);
    water += u_lightcol * (0.16 + sparkle * 1.8);
    float dist = length(v_world - u_campos);
    float fog = clamp(1.0 - exp(-u_fogdensity * dist), 0.0, 1.0);
    f_color = vec4(mix(water, u_fogcol, fog), 0.90);
}
"""


# =========================================================================
# weather particles
# =========================================================================
class Precip:
    """A box of falling particles that follows the camera target. Rain is
    drawn as short slanted line segments, snow as drifting points."""

    BOX = (200.0, 130.0, 200.0)

    def __init__(self, n_rain=900, n_snow=520):
        self.n_rain = n_rain
        self.n_snow = n_snow
        rng = np.random.default_rng(1)
        bw, bh, bd = self.BOX
        self.rain = rng.random((n_rain, 3)) * (bw, bh, bd) - (bw / 2, 0, bd / 2)
        self.snow = rng.random((n_snow, 3)) * (bw, bh, bd) - (bw / 2, 0, bd / 2)
        self.snow_phase = rng.random(n_snow) * 6.28

    def update(self, dt):
        bh = self.BOX[1]
        self.rain[:, 1] -= 210.0 * dt
        self.rain[:, 0] += 14.0 * dt          # a little wind slant
        self.snow[:, 1] -= 26.0 * dt
        self.snow_phase += dt * 1.5
        self.snow[:, 0] += np.cos(self.snow_phase) * 6.0 * dt
        for arr in (self.rain, self.snow):
            below = arr[:, 1] < 0.0
            arr[below, 1] += bh

    def rain_lines(self, target):
        """Return 2*n vertices (world space) for GL_LINES rain streaks."""
        base = self.rain + (target[0], 0.0, target[2])
        tips = base + (1.6, 7.0, 0.0)
        out = np.empty((self.n_rain * 2, 3), dtype="f4")
        out[0::2] = base
        out[1::2] = tips
        return out

    def snow_points(self, target):
        return (self.snow + (target[0], 0.0, target[2])).astype("f4")


# =========================================================================
# scene generation
# =========================================================================
def make_scene(seed=7):
    rng = np.random.default_rng(seed)
    trees, rocks, flowers, mushrooms = [], [], [], []
    # Retry positions so the scene keeps its density while reserving a dry
    # shoreline around the procedurally carved lake and river.
    for _ in range(320):
        if len(trees) >= 46:
            break
        x = (rng.random() - 0.5) * 170
        z = (rng.random() - 0.5) * 120
        if abs(x) < 14 and abs(z) < 14 or float(terrain_water_mask(x, z)) > 0.02:
            continue
        trees.append((x, z, 0.8 + rng.random() * 0.7, rng.random() * 6.28))
    for _ in range(160):
        if len(rocks) >= 9:
            break
        x = (rng.random() - 0.5) * 160
        z = (rng.random() - 0.5) * 110
        if float(terrain_water_mask(x, z)) > 0.02:
            continue
        rocks.append((x, z, 0.7 + rng.random() * 0.8, rng.random() * 6.28))

    # Small seasonal props use their own random positions.  They are always
    # generated, but only drawn in their matching season below.
    for _ in range(720):
        if len(flowers) >= 72:
            break
        x = (rng.random() - 0.5) * 165
        z = (rng.random() - 0.5) * 115
        if float(terrain_water_mask(x, z)) > 0.02:
            continue
        flowers.append((x, z, 1.1 + rng.random() * 0.9,
                        int(rng.integers(len(FLOWER_COLORS)))))
    for _ in range(420):
        if len(mushrooms) >= 34:
            break
        x = (rng.random() - 0.5) * 165
        z = (rng.random() - 0.5) * 115
        if float(terrain_water_mask(x, z)) > 0.02:
            continue
        mushrooms.append((x, z, 1.2 + rng.random() * 0.9))
    return trees, rocks, flowers, mushrooms


def world_to_scene(pos):
    x = (float(pos[0]) - WIDTH / 2.0) * WORLD_SCALE
    z = (float(pos[1]) - HEIGHT / 2.0) * WORLD_SCALE
    return x, z


def project_to_uv(vp, world_point):
    v = vp @ np.array([world_point[0], world_point[1], world_point[2], 1.0], dtype=np.float64)
    if v[3] <= 1e-5:
        return (-5.0, -5.0)
    return (float(v[0] / v[3] * 0.5 + 0.5), float(v[1] / v[3] * 0.5 + 0.5))


# =========================================================================
# renderer
# =========================================================================
class Renderer:
    def __init__(self, ctx, size):
        self.ctx = ctx
        self.size = size
        ctx.enable(ctx.DEPTH_TEST)

        self.lit = ctx.program(vertex_shader=LIT_VERT, fragment_shader=LIT_FRAG)
        self.shadow = ctx.program(vertex_shader=SHADOW_VERT, fragment_shader=SHADOW_FRAG)
        self.sky = ctx.program(vertex_shader=SKY_VERT, fragment_shader=SKY_FRAG)
        self.particle = ctx.program(vertex_shader=PARTICLE_VERT, fragment_shader=PARTICLE_FRAG)
        self.water = ctx.program(vertex_shader=WATER_VERT, fragment_shader=WATER_FRAG)
        self.overlay = ctx.program(vertex_shader=OVERLAY_VERT, fragment_shader=OVERLAY_FRAG)

        self.trees, self.rocks, self.flowers, self.mushrooms = make_scene()
        self.precip = Precip()
        self.selected_id = None            # creature the player clicked, or None
        # per-creature gait state, so the feet step in time with real movement
        self.prev_scene = {}   # id -> last (cx, cz), to measure how far it moved
        self.walk_speed = {}   # id -> smoothed scene-units/frame (flicker-free)
        self.walk_phase = {}   # id -> stride phase, advanced while moving
        self.facing = {}       # id -> unit (fx, fz) heading it last walked toward
        # a small flock of birds drifting through the sky (world-space points)
        rng = np.random.default_rng(3)
        self.birds = rng.random((14, 3)) * (260.0, 40.0, 260.0) - (130.0, -70.0, 130.0)

        self.vao_ground = self._vao(self.lit, mesh_terrain())
        self.vao_trunk = self._vao(self.lit, mesh_cylinder(0.6, 4.6, 14))
        self.vao_canopy = self._vao(self.lit, mesh_uv_sphere(3.4, 12, 16))
        # a small sphere reused for the mouth and the selection marker
        self.vao_eye = self._vao(self.lit, mesh_uv_sphere(0.45, 8, 10))
        # the unit-ish sphere every creature body part is scaled from
        self.vao_hand = self._vao(self.lit, mesh_uv_sphere(0.42, 7, 9))
        # face parts: white eyeball, black pupil, nose, mouth
        self.vao_sclera = self._vao(self.lit, mesh_uv_sphere(0.27, 8, 10))
        self.vao_pupil = self._vao(self.lit, mesh_uv_sphere(0.15, 6, 8))
        self.vao_nose = self._vao(self.lit, mesh_uv_sphere(0.16, 6, 8))
        self.vao_egg = self._vao(self.lit, mesh_uv_sphere(1.0, 12, 14))
        self.emotion_fx = {}   # cid -> (emotion, expire_time) for transient moods
        self.dying = {}        # cid -> [kind, elapsed, duration] mid-death animation
        self.vao_flower_stem = self._vao(self.lit, mesh_cylinder(0.09, 1.05, 7))
        self.vao_flower_petals = self._vao(self.lit, mesh_flower_petals())
        self.vao_flower_center = self._vao(self.lit, mesh_uv_sphere(0.22, 6, 8))
        self.vao_mushroom_stem = self._vao(self.lit, mesh_cylinder(0.22, 0.95, 9))
        self.vao_mushroom_cap = self._vao(self.lit, mesh_uv_sphere(0.82, 8, 12))
        self.vao_mushroom_spot = self._vao(self.lit, mesh_uv_sphere(0.13, 5, 6))
        self.vbo_lake = ctx.buffer(mesh_lake().tobytes())
        self.vao_lake = ctx.vertex_array(self.water, [(self.vbo_lake, "3f", "in_pos")])
        self.visual_time = 0.0

        disc_vbo = ctx.buffer(mesh_disc(1.0).tobytes())
        self.vao_disc = ctx.vertex_array(self.shadow, [(disc_vbo, "3f 3x4", "in_pos")])

        self.vao_rocks = [
            self._vao(self.lit, mesh_uv_sphere(2.6, 6, 8, jitter=0.55, seed=i))
            for i in range(len(self.rocks))
        ]

        sky_quad = np.array([-1, -1, 3, -1, -1, 3], dtype="f4")
        self.vao_sky = ctx.vertex_array(
            self.sky, [(ctx.buffer(sky_quad.tobytes()), "2f", "in_pos")])

        # a reusable dynamic buffer for the weather particles + birds
        self.pbuf = ctx.buffer(reserve=self.precip.n_rain * 2 * 3 * 4)
        self.vao_particle = ctx.vertex_array(self.particle, [(self.pbuf, "3f", "in_pos")])
        self.bird_buf = ctx.buffer(reserve=len(self.birds) * 3 * 4)
        self.vao_birds = ctx.vertex_array(self.particle, [(self.bird_buf, "3f", "in_pos")])

        # a full-screen quad + RGBA texture for the 2D text overlay (HUD)
        quad = np.array([-1, -1, 1, -1, -1, 1, 1, -1, 1, 1, -1, 1], dtype="f4")
        self.vao_overlay = ctx.vertex_array(self.overlay, [(ctx.buffer(quad.tobytes()), "2f", "in_pos")])
        self.overlay_tex = ctx.texture(size, 4)
        self.overlay_tex.filter = (self.ctx.NEAREST, self.ctx.NEAREST)

    def _vao(self, prog, verts):
        vbo = self.ctx.buffer(verts.tobytes())
        return self.ctx.vertex_array(prog, [(vbo, "3f 3f", "in_pos", "in_norm")])

    def _draw(self, vao, model, vp, color, env, grid=0):
        self.lit["mvp"].write(_bytes(vp @ model))
        self.lit["model"].write(_bytes(model))
        self.lit["u_color"].value = color
        self.lit["u_grid"].value = grid
        self.lit["u_snowcover"].value = 1.0 if env["season"] == "winter" else 0.0
        vao.render()

    # a scaled unit sphere at a point (built from the r0.42 sphere mesh)
    def _sph(self, vp, env, x, y, z, r, color, sx=None, sy=None, sz=None):
        sx = r if sx is None else sx
        sy = r if sy is None else sy
        sz = r if sz is None else sz
        self._draw(self.vao_hand, translate(x, y, z) @ scale(sx / 0.42, sy / 0.42, sz / 0.42),
                   vp, color, env)

    def _draw_face(self, vp, env, cx, cz, hy, hr, eye, emo):
        """White eyes + pupils, nose and an emotion-shaped mouth on a head of
        radius hr, all turned to face the camera."""
        fp = EMOTION_FACE[emo]
        sc = hr / 0.96
        face = np.array([eye[0] - cx, 0.0, eye[2] - cz])
        if np.linalg.norm(face) > 1e-3:
            face /= np.linalg.norm(face)
        right = np.cross(np.array([0.0, 1.0, 0.0]), face)
        for side in (-1, 1):
            ex = cx + face[0] * hr * 0.72 + right[0] * hr * 0.34 * side
            ez = cz + face[2] * hr * 0.72 + right[2] * hr * 0.34 * side
            ey = hy + hr * 0.16
            self._draw(self.vao_sclera, translate(ex, ey, ez) @ scale(sc * fp["sclera"], sc * fp["sclera"], sc * fp["sclera"]),
                       vp, SCLERA_COLOR, env)
            # sit the pupil on the front surface of the white so it stays visible
            pr = 0.27 * sc * fp["sclera"] * 0.85
            self._draw(self.vao_pupil, translate(ex + face[0] * pr, ey + fp["pupil_dy"], ez + face[2] * pr) @ scale(sc, sc, sc),
                       vp, PUPIL_COLOR, env)
        self._draw(self.vao_nose, translate(cx + face[0] * hr * 0.9, hy - hr * 0.05, cz + face[2] * hr * 0.9) @ scale(sc, sc, sc),
                   vp, NOSE_COLOR, env)
        mw, mh, mf = fp["mouth"]
        self._draw(self.vao_eye, translate(cx + face[0] * hr * 0.84, hy - hr * 0.42 + fp["mouth_dy"], cz + face[2] * hr * 0.84)
                   @ scale(mw * sc, mh * sc, mf * sc), vp, MOUTH_COLOR, env)

    def _shadow(self, x, z, r, vp, strength, sun):
        # A directional shadow: offset away from the sun and stretched when the
        # sun is low, so shadows lengthen at dawn/dusk like real ones. sun is
        # the (normalised) direction TO the sun.
        sx, sy, sz = sun
        lift = max(sy, 0.08)
        ox, oz = -sx / lift * r * 0.9, -sz / lift * r * 0.9
        stretch = 1.0 + (1.0 - min(lift, 1.0)) * 1.6
        m = (translate(x + ox, float(terrain_height(x, z)) + 0.06, z + oz)
             @ scale(r * stretch, 1.0, r * stretch))
        self.shadow["mvp"].write(_bytes(vp @ m))
        self.shadow["u_color"].value = (0.05, 0.09, 0.05, strength)
        self.vao_disc.render()

    def _draw_memory(self, vp, mind):
        """Lay the selected creature's mental map on the ground: a green tile
        over ground it remembers as good, a red one over ground it learned to
        fear, brighter the stronger the memory. Its consciousness, made
        visible. Call inside a blend / depth-write-off block."""
        mem = mind.memory
        for cy in range(MEM_ROWS):
            for cx in range(MEM_COLS):
                v = float(mem[cy, cx])
                if abs(v) < 0.06:
                    continue
                wx, wy = _mem_cell_center(cy, cx)
                sx, sz = world_to_scene((wx, wy))
                ty = float(terrain_height(sx, sz))
                if float(terrain_water_mask(sx, sz)) > 0.5:
                    ty = WATER_LEVEL
                mag = min(1.0, abs(v) / MEM_CLIP)
                col = (0.30, 1.0, 0.55) if v > 0 else (1.0, 0.18, 0.12)
                r = 7.5 * (0.55 + 0.45 * mag)
                m = translate(sx, ty + 0.08, sz) @ scale(r, 1.0, r)
                self.shadow["mvp"].write(_bytes(vp @ m))
                self.shadow["u_color"].value = (col[0], col[1], col[2], 0.28 + 0.42 * mag)
                self.vao_disc.render()

    def _draw_water(self, vao, vp, env, eye):
        self.water["mvp"].write(_bytes(vp))
        self.water["u_time"].value = self.visual_time
        self.water["u_lightdir"].value = tuple(float(v) for v in env["light_dir"])
        self.water["u_lightcol"].value = env["light_col"]
        self.water["u_fogcol"].value = env["fog_col"]
        self.water["u_fogdensity"].value = env["fog_density"]
        self.water["u_campos"].value = tuple(float(v) for v in eye)
        self.water["u_zenith"].value = env["zenith"]
        self.water["u_horizon"].value = env["horizon"]
        vao.render()

    # -- emotion + dying ----------------------------------------------------
    def set_emotion(self, cid, emotion, duration=2.0):
        self.emotion_fx[cid] = (emotion, self.visual_time + duration)

    def start_dying(self, cid, kind):
        self.dying[cid] = [kind, 0.0, DYING_DUR[kind]]

    def _advance_dying(self, world, dt):
        for cid in list(self.dying):
            self.dying[cid][1] += dt
            if self.dying[cid][1] >= self.dying[cid][2]:
                c = next((c for c in world.creatures if c.id == cid), None)
                if c is not None:
                    world.kill_creature(c)
                del self.dying[cid]
                if self.selected_id == cid:
                    self.selected_id = None

    def emotion_of(self, c):
        """A transient mood set by a recent action; otherwise the creature's
        own persistent inner mood (valence/arousal) when it has a mind, or a
        rough guess from energy + disposition when learning is off."""
        fx = self.emotion_fx.get(c.id)
        if fx is not None and self.visual_time < fx[1]:
            return fx[0]
        if c.mind is not None:
            return c.mind.emotion()   # the lasting inner feeling drives the face
        if c.energy / MAX_ENERGY < 0.28:
            return "sad"
        return "neutral"

    def arousal_of(self, c):
        """How agitated the creature is right now, 0 (calm) .. 1 (frantic) -
        drives how much its body fidgets. Falls back to a mild default when
        learning is off so standing creatures still breathe."""
        if c.mind is not None:
            return float(c.mind.arousal)
        return 0.3

    # -- interaction helpers ------------------------------------------------
    def _camera_vp(self, camera):
        eye, target = camera.eye_target()
        view = look_at(eye, target, (0, 1, 0))
        proj = perspective(52.0, self.size[0] / self.size[1], 1.0, 900.0)
        return proj @ view, eye

    def _mouse_ray(self, camera, mx, my):
        """A world-space ray (origin, direction) through the pixel (mx, my)."""
        vp, eye = self._camera_vp(camera)
        inv = np.linalg.inv(vp.astype(np.float64))
        ndc_x = 2.0 * mx / self.size[0] - 1.0
        ndc_y = 1.0 - 2.0 * my / self.size[1]

        def unproj(ndc_z):
            p = inv @ np.array([ndc_x, ndc_y, ndc_z, 1.0])
            return p[:3] / p[3]

        near, far = unproj(-1.0), unproj(1.0)
        d = far - near
        return near, d / (np.linalg.norm(d) + 1e-9)

    def creature_at(self, world, camera, mx, my, eggs=None):
        """Return the creature whose body sphere the pixel ray hits first.
        Unhatched eggs and creatures mid-death are not selectable."""
        o, d = self._mouse_ray(camera, mx, my)
        best, best_t = None, 1e9
        for c in world.creatures:
            if not c.alive or c.id in self.dying or (eggs is not None and eggs.is_egg(c.id)):
                continue
            cx, cz = world_to_scene(c.pos)
            cy = float(terrain_height(cx, cz))
            if float(terrain_water_mask(cx, cz)) > 0.5:
                cy = WATER_LEVEL
            centre = np.array([cx, cy + 1.4, cz])
            oc = o - centre
            b = np.dot(oc, d)
            disc = b * b - (np.dot(oc, oc) - 1.8 * 1.8)
            if disc < 0:
                continue
            t = -b - math.sqrt(disc)
            if 0 < t < best_t:
                best, best_t = c, t
        return best

    def hand_world(self, camera, mx, my):
        """Where the mouse ray meets the ground - in simulation coordinates,
        for World.hand_pos. None if it points at the sky."""
        o, d = self._mouse_ray(camera, mx, my)
        if abs(d[1]) < 1e-6:
            return None
        t = -o[1] / d[1]
        if t <= 0:
            return None
        p = o + d * t
        return (p[0] / WORLD_SCALE + WIDTH / 2.0, p[2] / WORLD_SCALE + HEIGHT / 2.0)

    def draw_overlay(self, surface):
        """Blit a pygame RGBA Surface over the finished 3D frame (the HUD)."""
        import pygame
        data = pygame.image.tostring(surface, "RGBA", True)
        self.overlay_tex.write(data)
        self.ctx.disable(self.ctx.DEPTH_TEST)
        self.ctx.enable(self.ctx.BLEND)
        self.overlay_tex.use(0)
        self.overlay["u_tex"].value = 0
        self.vao_overlay.render()
        self.ctx.disable(self.ctx.BLEND)
        self.ctx.enable(self.ctx.DEPTH_TEST)

    def render(self, world, camera, env, dt=0.0, eggs=None):
        ctx = self.ctx
        self.visual_time += dt
        self._advance_dying(world, dt)
        eye, target = camera.eye_target()
        view = look_at(eye, target, (0, 1, 0))
        proj = perspective(52.0, self.size[0] / self.size[1], 1.0, 900.0)
        vp = proj @ view

        # feed the lit shader this hour's lighting
        ld = np.array(env["light_dir"]); ld = ld / (np.linalg.norm(ld) + 1e-6)
        self.lit["u_lightdir"].value = tuple(float(v) for v in ld)
        self.lit["u_lightcol"].value = env["light_col"]
        self.lit["u_ambient"].value = env["ambient"]
        self.lit["u_fogcol"].value = env["fog_col"]
        self.lit["u_fogdensity"].value = env["fog_density"]
        self.lit["u_campos"].value = tuple(float(v) for v in eye)

        ctx.clear(depth=1.0)

        # sky (no depth): gradient + sun/moon + stars
        ctx.disable(ctx.DEPTH_TEST)
        self.sky["u_zenith"].value = env["zenith"]
        self.sky["u_horizon"].value = env["horizon"]
        self.sky["u_night"].value = float(env["night"])
        body_pt = (target[0] + env["body_dir"][0] * 400,
                   env["body_dir"][1] * 400,
                   target[2] + env["body_dir"][2] * 400)
        self.sky["u_body"].value = project_to_uv(vp, body_pt) if env["body_up"] else (-5.0, -5.0)
        self.sky["u_bodycol"].value = env["body_col"]
        self.vao_sky.render()
        ctx.enable(ctx.DEPTH_TEST)

        # terrain
        self._draw(self.vao_ground, _identity(), vp, env["ground"], env, grid=1)

        # Animated, translucent lake. Depth writes are disabled so the shimmer
        # blends with the terrain while still respecting objects.
        ctx.enable(ctx.BLEND)
        ctx.depth_mask = False
        self._draw_water(self.vao_lake, vp, env, eye)
        ctx.depth_mask = True
        ctx.disable(ctx.BLEND)

        # contact shadows, cast directionally from the sun (softer at night)
        sun = tuple(float(v) for v in ld)
        sh = 0.10 + 0.20 * max(env["sun_h"], 0.0)
        ctx.enable(ctx.BLEND)
        ctx.depth_mask = False
        for x, z, s, _ in self.trees:
            self._shadow(x, z, 3.6 * s, vp, sh, sun)
        for (x, z, s, _) in self.rocks:
            self._shadow(x, z, 3.0 * s, vp, sh, sun)
        for c in world.creatures:
            if c.alive:
                cx, cz = world_to_scene(c.pos)
                self._shadow(cx, cz, 2.6, vp, sh, sun)
        # the selected creature's spatial memory, painted on the ground
        if self.selected_id is not None:
            sel = next((c for c in world.creatures
                        if c.id == self.selected_id and c.alive and c.mind is not None), None)
            if sel is not None:
                self._draw_memory(vp, sel.mind)
        ctx.depth_mask = True
        ctx.disable(ctx.BLEND)

        # trees: bare trunks in winter get a small snowy crown; otherwise a
        # rounded two-tone canopy in the season's colour
        for x, z, s, yaw in self.trees:
            base = translate(x, float(terrain_height(x, z)), z) @ rotate_y(yaw) @ scale(s, s, s)
            self._draw(self.vao_trunk, base, vp, TRUNK_COLOR, env)
            # the canopy leans a little in the wind, more the higher it sits
            sway = math.sin(self.visual_time * 1.3 + (x + z) * 0.1) * 0.6
            canopy = base @ translate(sway, 5.4, sway * 0.5)
            self._draw(self.vao_canopy, canopy, vp, env["canopy"], env)
            crown = base @ translate(sway * 1.5, 8.4, sway * 0.8) @ scale(0.7, 0.7, 0.7)
            self._draw(self.vao_canopy, crown, vp, env["crown"], env)

        for (x, z, s, yaw), vao in zip(self.rocks, self.vao_rocks):
            m = (translate(x, float(terrain_height(x, z)) + 1.8 * s, z)
                 @ rotate_y(yaw) @ scale(s, s * 0.7, s))
            self._draw(vao, m, vp, ROCK_COLOR, env)

        # Seasonal ground life: flowers bloom in spring and summer, mushrooms
        # come up in autumn; each disappears completely outside its season
        # while the base world stays intact.
        if env["season"] in ("spring", "summer"):
            for x, z, s, color_i in self.flowers:
                y = float(terrain_height(x, z))
                self._draw(self.vao_flower_stem, translate(x, y, z) @ scale(s, s, s),
                           vp, FLOWER_STEM_COLOR, env)
                head = translate(x, y + 1.05 * s, z) @ scale(s, s, s)
                self._draw(self.vao_flower_petals, head, vp, FLOWER_COLORS[color_i], env)
                self._draw(self.vao_flower_center, head, vp, FLOWER_CENTER_COLOR, env)
        elif env["season"] == "autumn":
            for x, z, s in self.mushrooms:
                y = float(terrain_height(x, z))
                self._draw(self.vao_mushroom_stem, translate(x, y, z) @ scale(s, s, s),
                           vp, MUSHROOM_STEM_COLOR, env)
                cap = translate(x, y + 0.9 * s, z) @ scale(s, s * 0.5, s)
                self._draw(self.vao_mushroom_cap, cap, vp, MUSHROOM_CAP_COLOR, env)
                # a few white dots dusted over the top of the cap
                for dx, dz in ((0.0, 0.0), (0.34, 0.12), (-0.28, 0.24), (0.14, -0.32)):
                    spot = translate(x + dx * s, y + 1.16 * s, z + dz * s) @ scale(s, s, s)
                    self._draw(self.vao_mushroom_spot, spot, vp, MUSHROOM_SPOT_COLOR, env)

        # creatures: eggs while unhatched, otherwise a big coloured head on
        # two little feet - the colour is the creature's current signal.
        flames = []   # (cx, cy, cz) burning creatures, drawn after the bodies
        for c in world.creatures:
            if not c.alive:
                continue
            cx, cz = world_to_scene(c.pos)
            cy = float(terrain_height(cx, cz))
            if float(terrain_water_mask(cx, cz)) > 0.5:
                cy = WATER_LEVEL

            # --- unhatched egg: a wobbling speckled ovoid on the ground ------
            if eggs is not None and eggs.is_egg(c.id):
                p = eggs.progress(c.id)
                wob = math.sin(self.visual_time * (3.0 + 6.0 * p) + c.id) * (0.05 + 0.18 * p)
                base = translate(cx, cy + 1.15, cz) @ rotate_y(wob) @ scale(0.62, 0.82, 0.62)
                self._draw(self.vao_egg, base, vp, EGG_COLOR, env)
                for dx, dy, dz in ((0.3, 0.2, 0.2), (-0.25, -0.1, 0.3), (0.15, 0.5, -0.28)):
                    self._draw(self.vao_pupil, translate(cx + dx, cy + 1.15 + dy, cz + dz) @ scale(0.9, 0.9, 0.9),
                               vp, EGG_SPOT_COLOR, env)
                continue

            # --- dying animation: shudder (knife), squash (rock), burn (fire) -
            dstate = self.dying.get(c.id)
            jx = jz = 0.0
            sq = 1.0
            if dstate is not None:
                kind, el, dur = dstate
                frac = min(el / dur, 1.0)
                if kind == "knife":
                    jx = math.sin(self.visual_time * 46.0) * 0.35
                    jz = math.cos(self.visual_time * 39.0) * 0.30
                elif kind == "fire":
                    jx = math.sin(self.visual_time * 30.0) * 0.12
                    flames.append((cx, cy, cz))
                elif kind == "rock":
                    sq = max(0.12, 1.0 - frac * 0.9)
            cxj, czj = cx + jx, cz + jz

            # --- gait: measure real movement, step the feet in time with it ---
            pc = self.prev_scene.get(c.id)
            self.prev_scene[c.id] = (cx, cz)
            mvx = mvz = 0.0
            dist = 0.0
            if pc is not None:
                mvx, mvz = cx - pc[0], cz - pc[1]
                dist = math.hypot(mvx, mvz)
            # smoothed speed so a single jittery frame can't start/stop the walk
            sp = self.walk_speed.get(c.id, 0.0)
            sp += (dist - sp) * (min(1.0, dt * 8.0) if dt > 0 else 1.0)
            self.walk_speed[c.id] = sp
            moving = sp > 0.01 and dstate is None
            if moving and dist > 1e-5:
                self.facing[c.id] = (mvx / dist, mvz / dist)
            fx, fz = self.facing.get(c.id, (0.0, 1.0))
            rx, rz = -fz, fx  # sideways ("right") vector, for foot spacing + waddle
            ph = self.walk_phase.get(c.id, 0.0)
            if moving:
                ph += dt * 9.0    # cadence while walking
            self.walk_phase[c.id] = ph
            swing = math.sin(ph) if moving else 0.0
            step_bob = abs(math.sin(ph)) * 0.14 if moving else 0.0   # rise on each step
            roll = math.cos(ph) * 0.14 if moving else 0.0            # side-to-side waddle

            # the persistent inner mood shows even when standing still: an
            # agitated creature (high arousal) breathes faster and trembles,
            # a calm one is almost still.
            arous = self.arousal_of(c)
            idle_bob = math.sin(self.visual_time * (1.8 + arous * 3.2) + c.id * 1.7) * (0.08 + arous * 0.16)
            bob = 0.0 if (dstate or moving) else idle_bob
            if arous > 0.5 and not dstate and not moving:
                tr = (arous - 0.5) * 0.34   # a nervous tremor
                cxj += math.sin(self.visual_time * 34.0 + c.id) * tr
                czj += math.cos(self.visual_time * 29.0 + c.id * 1.3) * tr
            foot = cy + bob
            # colour by the creature's current signal (its "status")
            col = TOKEN_COLORS_F[c.token % len(TOKEN_COLORS_F)]
            foot_col = tuple(v * 0.45 for v in col)   # darker version, for the feet
            # two little feet: opposite phase, swinging fore/aft and lifting per step
            for side in (-1.0, 1.0):
                s = swing * side
                lift = max(0.0, s) * 0.35
                fxp = cxj + rx * 0.45 * side + fx * (0.25 + s * 0.45)
                fzp = czj + rz * 0.45 * side + fz * (0.25 + s * 0.45)
                self._sph(vp, env, fxp, foot + 0.15 + lift, fzp, 0.34, foot_col, 0.42, 0.28, 0.55)
            # big coloured head with a face; waddles sideways + bobs when walking
            head_x = cxj + rx * roll
            head_z = czj + rz * roll
            head_y = foot + 1.35 * sq + step_bob
            self._sph(vp, env, head_x, head_y, head_z, 1.25, col, 1.25, 1.25 * sq, 1.25)
            self._draw_face(vp, env, head_x, head_z, head_y, 1.25, eye,
                            "fear" if dstate else self.emotion_of(c))
            if c.id == self.selected_id and dstate is None:
                mk = 3.4 + math.sin(self.visual_time * 4.0) * 0.35
                self._draw(self.vao_eye, translate(cx, foot + mk, cz), vp, (1.0, 0.95, 0.35), env)

        # flames over burning creatures: several flickering tongues
        for cx, cy, cz in flames:
            for k in range(6):
                fh = 1.1 + 0.6 * math.sin(self.visual_time * 12.0 + k * 1.7)
                fx = cx + math.sin(self.visual_time * 9.0 + k * 2.1) * 0.7
                fz = cz + math.cos(self.visual_time * 8.0 + k * 1.3) * 0.7
                col = FLAME_COLORS[k % 2]
                self._draw(self.vao_hand, translate(fx, cy + 1.3 + k * 0.55, fz) @ scale(1.5, 2.0 * fh, 1.5),
                           vp, col, env)

        # a small flock of birds drifting across the sky
        self.birds[:, 0] += dt * 9.0
        self.birds[:, 2] += dt * 3.0
        wrap = self.birds[:, 0] > 150.0
        self.birds[wrap, 0] -= 300.0
        wrapz = self.birds[:, 2] > 150.0
        self.birds[wrapz, 2] -= 300.0
        bird_world = self.birds + (target[0], 0.0, target[2] * 0.0)
        ctx.enable(ctx.BLEND)
        ctx.depth_mask = False
        ctx.enable(ctx.PROGRAM_POINT_SIZE)
        self.bird_buf.write(bird_world.astype("f4").tobytes())
        self.particle["mvp"].write(_bytes(vp))
        self.particle["u_size"].value = 4.0
        self.particle["u_color"].value = (0.10, 0.10, 0.13, 0.9)
        self.vao_birds.render(mode=ctx.POINTS, vertices=len(self.birds))
        ctx.depth_mask = True
        ctx.disable(ctx.BLEND)

        # weather particles
        if env["precip"]:
            self.precip.update(dt)
            ctx.enable(ctx.BLEND)
            ctx.depth_mask = False
            self.particle["mvp"].write(_bytes(vp))
            if env["precip"] == "rain":
                verts = self.precip.rain_lines(target)
                self.pbuf.write(verts.tobytes())
                self.particle["u_size"].value = 1.0
                self.particle["u_color"].value = (0.70, 0.80, 0.95, 0.45)
                self.vao_particle.render(mode=self.ctx.LINES, vertices=len(verts))
            else:
                verts = self.precip.snow_points(target)
                self.pbuf.write(verts.tobytes())
                ctx.enable(ctx.PROGRAM_POINT_SIZE)
                self.particle["u_size"].value = 3.5
                self.particle["u_color"].value = (0.98, 0.99, 1.0, 0.9)
                self.vao_particle.render(mode=self.ctx.POINTS, vertices=len(verts))
            ctx.depth_mask = True
            ctx.disable(ctx.BLEND)


class Camera:
    def __init__(self):
        self.azimuth = 0.7
        self.elevation = 0.42
        self.distance = 150.0
        self.target = np.array([0.0, float(terrain_height(0.0, 0.0)) + 7.0, 0.0])

    def eye_target(self):
        ce = math.cos(self.elevation)
        eye = self.target + np.array([
            math.cos(self.azimuth) * ce * self.distance,
            math.sin(self.elevation) * self.distance,
            math.sin(self.azimuth) * ce * self.distance,
        ])
        return eye, self.target

    def orbit(self, dx, dy):
        self.azimuth += dx * 0.006
        self.elevation = max(0.08, min(1.35, self.elevation + dy * 0.006))

    def zoom(self, amount):
        self.distance = max(40.0, min(320.0, self.distance * (0.9 ** amount)))


TOKEN_NAMES = ["silent", "red", "blue", "yellow", "purple", "teal"]


def build_hud(size, world, env, phase, selected_id, font, small, menu=None):
    """Draw the 2D HUD onto a transparent pygame Surface: the season/weather/
    clock/population line, the flock's learned feeling toward you, a panel for
    the selected creature, and a one-line controls hint."""
    import pygame
    surf = pygame.Surface(size, pygame.SRCALPHA)

    def text(s, x, y, col=(240, 244, 250), fnt=None):
        fnt = fnt or font
        surf.blit(fnt.render(s, True, (0, 0, 0)), (x + 1, y + 1))
        surf.blit(fnt.render(s, True, col), (x, y))

    hh, mm = int(phase * 24) % 24, int(phase * 24 * 60) % 60
    text("%s   |   %s   |   %02d:%02d   |   pop %d" % (
        env["season"], env["precip"] or "clear", hh, mm, world.population()), 12, 10)
    disp = world.disposition_summary()
    if disp is not None:
        col = (150, 220, 140) if disp > 0.05 else (225, 110, 110) if disp < -0.05 else (230, 230, 220)
        text("the flock %s (%+.0f%%)" % (disposition_label(disp), disp * 100), 12, 36, col)

        # the arc of how it got here, saved with the world - a flock that fell
        # from trust reads nothing like one that was never liked
        arc = list(getattr(world, "disposition_history", []))
        if len(arc) > 1:
            ax, ay, aw, ah = 12, 58, 150, 20
            pygame.draw.rect(surf, (40, 48, 38), (ax, ay, aw, ah))
            pygame.draw.line(surf, (90, 98, 86), (ax, ay + ah // 2), (ax + aw, ay + ah // 2))
            pts = [(ax + i * aw / (len(arc) - 1),
                    ay + ah / 2 - max(-1.0, min(1.0, v)) * ah / 2) for i, v in enumerate(arc)]
            pygame.draw.lines(surf, (150, 200, 230), False, pts)

        # what the flock has DECIDED about you, which the average cannot show:
        # split down the middle looks identical to uniformly indifferent
        choices = world.choice_summary()
        if choices:
            bx, by, bw, bh = 176, 62, 150, 10
            left = bx
            for act, colr in ((ACT_APPROACH, (120, 200, 110)), (ACT_FLEE, (220, 95, 90)),
                              (ACT_IGNORE, (120, 126, 112))):
                span = int(round(choices.get(act, 0.0) * bw))
                if span:
                    pygame.draw.rect(surf, colr, (left, by, span, bh))
                left += span
            pygame.draw.rect(surf, (70, 78, 62), (bx, by, bw, bh), 1)
            text("%d%% come  %d%% flee  %d%% ignore"
                 % (choices.get(ACT_APPROACH, 0) * 100, choices.get(ACT_FLEE, 0) * 100,
                    choices.get(ACT_IGNORE, 0) * 100), bx + bw + 10, by - 3, (200, 200, 190), small)

    if selected_id is not None:
        c = next((c for c in world.creatures if c.id == selected_id and c.alive), None)
        if c is not None:
            has_mind = c.mind is not None
            ph = 172 if has_mind else 78
            # One line per fact, rather than two facts sharing a line. The
            # feeling line used to sit beside energy and ran clean off the
            # panel as soon as the wording gained its neutral band ("doesn't
            # know you yet" is half again as long as "is wary of you").
            px, py, pw = 12, size[1] - ph - 40, (300 if has_mind else 250)
            panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
            panel.fill((12, 16, 22, 190))
            pygame.draw.rect(panel, (110, 210, 130), panel.get_rect(), 1)
            surf.blit(panel, (px, py))
            text("creature #%d" % c.id, px + 10, py + 8, (170, 240, 175))
            text("colour: %s   gen %d" % (TOKEN_NAMES[c.token % 6], getattr(c, "generation", 0)),
                 px + 10, py + 30, fnt=small)
            text("energy: %3.0f%%" % (100.0 * c.energy / MAX_ENERGY), px + 10, py + 48, fnt=small)
            if has_mind:
                d = c.mind.disposition()
                text("feeling: %s (%+.0f%%)" % (disposition_label(d), d * 100),
                     px + 10, py + 66, fnt=small)
                emo = c.mind.emotion()
                ecol = MOOD_HUD_COLORS.get(emo, (230, 230, 220))
                text("mood: %-8s val %+.0f%%  aro %2.0f%%"
                     % (emo, c.mind.valence * 100, c.mind.arousal * 100),
                     px + 10, py + 84, ecol, small)
                # what THIS creature has learned each colour foretells - more
                # telling here than a flock average, because you picked it
                text("what calls mean to it:", px + 10, py + 104, (150, 200, 130), small)
                cx = px + 10
                for token in range(1, N_TOKENS):
                    m = c.mind.signal_meaning(token)
                    pygame.draw.circle(surf, TOKEN_COLORS[token], (cx + 5, py + 126), 5)
                    mc = ((225, 110, 110) if m < -0.02 else
                          (150, 220, 140) if m > 0.02 else (140, 146, 132))
                    text("%+.2f" % m, cx + 13, py + 119, mc, small)
                    cx += 46
                # the only learning that reaches the body: how much harder this
                # one runs because it worked out what a hunter costs it
                if c.mind.dread > 0.0:
                    grasp = min(1.0, c.mind.dread / max(1e-9, simulation.KNOWLEDGE_FLEE_FULL))
                    text("dread %.3f -> runs %+.0f%% harder"
                         % (c.mind.dread, simulation.KNOWLEDGE_FLEE_GAIN * grasp * 100),
                         px + 10, py + 146, (225, 110, 110), small)
                else:
                    text("hunters mean nothing to it yet", px + 10, py + 146,
                         (140, 146, 132), small)

    text("L-drag orbit   scroll zoom   click: select   right-click creature: care/harm   "
         "right-click ground: lay an egg   S/W season/weather   T fast-time",
         12, size[1] - 24, (206, 212, 220), small)
    if menu is not None:
        menu.draw(surf, small)
    return surf


# =========================================================================
# headless render (for verification in a GPU-less environment)
# =========================================================================
def render_headless(path, size=(1000, 700), phase=0.5, season="summer",
                    weather="clear", seed=7, steps=40):
    import moderngl
    import pygame
    pygame.init()
    ctx = moderngl.create_standalone_context()
    fbo = ctx.simple_framebuffer(size)
    fbo.use()
    world = World(init_pop=8, predator_count=0, learning=True)
    for _ in range(steps):
        world.step()
    renderer = Renderer(ctx, size)
    sel = next((c.id for c in world.creatures if c.alive), None)
    renderer.selected_id = sel
    env = environment(phase, season, weather)
    renderer.render(world, Camera(), env, dt=0.05)
    font = pygame.font.SysFont("consolas", 18)
    small = pygame.font.SysFont("consolas", 14)
    renderer.draw_overlay(build_hud(size, world, env, phase, sel, font, small))
    data = fbo.read(components=3)
    try:
        from PIL import Image
        Image.frombytes("RGB", size, data).transpose(Image.FLIP_TOP_BOTTOM).save(path)
    except ImportError:
        surf = pygame.transform.flip(pygame.image.fromstring(data, size, "RGB"), False, True)
        pygame.image.save(surf, path)
    print("saved", path)


# =========================================================================
# interactive main (needs a real display + OpenGL)
# =========================================================================
def main():
    import moderngl
    import pygame
    pygame.init()
    size = (1000, 700)
    pygame.display.set_mode(size, pygame.OPENGL | pygame.DOUBLEBUF)
    pygame.display.set_caption("Thronglets - true 3D")
    # values pinned in the pygame P screen are the player's defaults for the
    # WHOLE project, not for one renderer - this view read the built-ins and
    # quietly ignored them
    tuning.load_and_apply()
    ctx = moderngl.create_context()
    renderer = Renderer(ctx, size)
    cam = Camera()
    # the world starts empty: the player lays the first eggs by hand
    world = World(init_pop=0, predator_count=0, learning=True)
    font = pygame.font.SysFont("consolas", 18)
    small = pygame.font.SysFont("consolas", 14)
    menu = ContextMenu()
    eggs = EggState()
    known_ids = set()       # every creature id we've already turned into an egg

    phase = 0.35            # early morning
    season_i, weather_i = 1, 0
    fast_time = False
    clock = pygame.time.Clock()
    dragging = False
    drag_moved = False
    running = True
    accum = 0.0

    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_s:
                    season_i = (season_i + 1) % len(SEASONS)
                elif event.key == pygame.K_w:
                    weather_i = (weather_i + 1) % len(WEATHERS)
                elif event.key == pygame.K_t:
                    fast_time = not fast_time
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if menu.open:               # a click while the menu is up
                    row = menu.row_at(*event.pos)
                    if row is not None:
                        apply_action(world, renderer, menu.cid, MENU_ROWS[row][1])
                    menu.close()
                else:
                    dragging, drag_moved = True, False
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if dragging and not drag_moved:   # a click, not an orbit drag: select
                    c = renderer.creature_at(world, cam, *event.pos, eggs)
                    renderer.selected_id = c.id if c is not None else None
                dragging = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                c = renderer.creature_at(world, cam, *event.pos, eggs)
                if c is not None:                 # a creature: open the care/harm menu
                    renderer.selected_id = c.id
                    menu.show(event.pos, c.id, size)
                elif eggs.manual < MANUAL_EGGS:   # bare ground: lay one of the first eggs
                    menu.close()
                    hp = renderer.hand_world(cam, *event.pos)
                    if hp is not None:
                        nc = world.add_creature(hp[0], hp[1])
                        if nc is not None:
                            known_ids.add(nc.id)
                            eggs.lay(world, nc.id, manual=True)
                else:
                    menu.close()
            elif event.type == pygame.MOUSEMOTION and dragging:
                if abs(event.rel[0]) + abs(event.rel[1]) > 2:
                    drag_moved = True
                cam.orbit(event.rel[0], -event.rel[1])
            elif event.type == pygame.MOUSEWHEEL:
                cam.zoom(event.y)

        # the mouse cursor is the player's hand the creatures feel and learn
        world.hand_pos = renderer.hand_world(cam, *pygame.mouse.get_pos())

        # advance the day: a full cycle in ~2 min (or ~12 s in fast mode)
        phase = (phase + dt / (12.0 if fast_time else 120.0)) % 1.0
        accum += dt
        if accum >= 0.12:
            world.step()
            accum = 0.0

        # every creature born from reproduction also arrives as an egg
        for c in world.creatures:
            if c.id not in known_ids:
                known_ids.add(c.id)
                eggs.lay(world, c.id, manual=False)
        eggs.update(dt, world)

        env = environment(phase, SEASONS[season_i], WEATHERS[weather_i])
        renderer.render(world, cam, env, dt=dt, eggs=eggs)
        renderer.draw_overlay(build_hud(size, world, env, phase, renderer.selected_id, font, small, menu))
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    if "--headless" in sys.argv:
        out, phase, season, weather = "gl_poc.png", 0.5, "summer", "clear"
        for a in sys.argv:
            if a.startswith("--out="):
                out = a.split("=", 1)[1]
            elif a.startswith("--phase="):
                phase = float(a.split("=", 1)[1])
            elif a.startswith("--season="):
                season = a.split("=", 1)[1]
            elif a.startswith("--weather="):
                weather = a.split("=", 1)[1]
        render_headless(out, phase=phase, season=season, weather=weather)
    else:
        main()
