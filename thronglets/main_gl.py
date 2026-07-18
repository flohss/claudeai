"""A *true* 3D proof-of-concept renderer for the Thronglets world.

Every other renderer in this project is 2D: main.py / main_tui.py /
main_web.py draw flat, and main_vr.py is a *pseudo*-3D trick (2D shapes
projected onto a fake ground plane). This file is different - it is real
3D: an OpenGL scene with a perspective camera you can orbit, a lit procedural
mountain terrain mesh, three-dimensional trees and rocks, and the creatures
as lit spheres standing on the ground. Nothing here is a 2D blit.

On top of the base scene it now has a full **day/night cycle, seasons and
weather**, exactly like main_vr - but driven by the 3D lighting instead of
flat tints:

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

It is still deliberately a *proof of concept*, not a full port: there is
no care menu or learning UI yet. The simulation itself is the real thing:
it reuses simulation.World, so the spheres you see are real creatures at
their real positions, stepped every frame.

Rendering goes through moderngl (OpenGL 3.3 core). On a normal machine
pygame opens the window and moderngl draws into it; run it with:

    python3 main_gl.py

Controls: LEFT-drag orbits the camera, scroll wheel zooms, S cycles the
season, W cycles the weather, T toggles fast time, and the day/night
cycle runs on its own. Press ESC or close the window to quit.

Because this environment has no GPU, the scene can also be rendered
off-screen into a PNG for verification (render_headless), which is how the
look was checked - Mesa's software rasterizer (llvmpipe) under a virtual
framebuffer produces the exact same image a GPU would.
"""

import math
import sys

import numpy as np

from simulation import WIDTH, HEIGHT, World

# The same 6-token palette as every other renderer, as 0..1 floats so a
# creature's colour means the same thing here as it does in main_vr.py.
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

        self.trees, self.rocks, self.flowers, self.mushrooms = make_scene()
        self.precip = Precip()

        self.vao_ground = self._vao(self.lit, mesh_terrain())
        self.vao_trunk = self._vao(self.lit, mesh_cylinder(0.6, 4.6, 14))
        self.vao_canopy = self._vao(self.lit, mesh_uv_sphere(3.4, 12, 16))
        self.vao_creature = self._vao(self.lit, mesh_uv_sphere(2.2, 16, 24))
        self.vao_eye = self._vao(self.lit, mesh_uv_sphere(0.45, 8, 10))
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

        # a reusable dynamic buffer for the weather particles
        self.pbuf = ctx.buffer(reserve=self.precip.n_rain * 2 * 3 * 4)
        self.vao_particle = ctx.vertex_array(self.particle, [(self.pbuf, "3f", "in_pos")])

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

    def _shadow(self, x, z, r, vp, strength):
        # Keep the contact shadow at the same sampled elevation as its owner.
        m = translate(x, float(terrain_height(x, z)) + 0.06, z) @ scale(r, 1.0, r)
        self.shadow["mvp"].write(_bytes(vp @ m))
        self.shadow["u_color"].value = (0.05, 0.09, 0.05, strength)
        self.vao_disc.render()

    def _draw_water(self, vao, vp, env, eye):
        self.water["mvp"].write(_bytes(vp))
        self.water["u_time"].value = self.visual_time
        self.water["u_lightdir"].value = tuple(float(v) for v in env["light_dir"])
        self.water["u_lightcol"].value = env["light_col"]
        self.water["u_fogcol"].value = env["fog_col"]
        self.water["u_fogdensity"].value = env["fog_density"]
        self.water["u_campos"].value = tuple(float(v) for v in eye)
        vao.render()

    def render(self, world, camera, env, dt=0.0):
        ctx = self.ctx
        self.visual_time += dt
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

        # contact shadows (softer at night / under cloud)
        sh = 0.10 + 0.20 * max(env["sun_h"], 0.0)
        ctx.enable(ctx.BLEND)
        ctx.depth_mask = False
        for x, z, s, _ in self.trees:
            self._shadow(x, z, 3.6 * s, vp, sh)
        for (x, z, s, _) in self.rocks:
            self._shadow(x, z, 3.0 * s, vp, sh)
        for c in world.creatures:
            if c.alive:
                cx, cz = world_to_scene(c.pos)
                self._shadow(cx, cz, 2.6, vp, sh)
        ctx.depth_mask = True
        ctx.disable(ctx.BLEND)

        # trees: bare trunks in winter get a small snowy crown; otherwise a
        # rounded two-tone canopy in the season's colour
        for x, z, s, yaw in self.trees:
            base = translate(x, float(terrain_height(x, z)), z) @ rotate_y(yaw) @ scale(s, s, s)
            self._draw(self.vao_trunk, base, vp, TRUNK_COLOR, env)
            canopy = base @ translate(0.0, 5.4, 0.0)
            self._draw(self.vao_canopy, canopy, vp, env["canopy"], env)
            crown = base @ translate(0.0, 8.4, 0.0) @ scale(0.7, 0.7, 0.7)
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

        # creatures: lit spheres with two camera-facing eyes
        for c in world.creatures:
            if not c.alive:
                continue
            cx, cz = world_to_scene(c.pos)
            cy = float(terrain_height(cx, cz))
            # a creature that wanders onto the lake rides the water surface
            # instead of sinking into the carved lake bed
            if float(terrain_water_mask(cx, cz)) > 0.5:
                cy = WATER_LEVEL
            col = TOKEN_COLORS_F[c.token % len(TOKEN_COLORS_F)]
            self._draw(self.vao_creature, translate(cx, cy + 2.1, cz), vp, col, env)
            face = np.array([eye[0] - cx, 0.0, eye[2] - cz])
            if np.linalg.norm(face) > 1e-3:
                face /= np.linalg.norm(face)
            right = np.cross(np.array([0.0, 1.0, 0.0]), face)
            for side in (-1, 1):
                ex = cx + face[0] * 2.0 + right[0] * 0.8 * side
                ez = cz + face[2] * 2.0 + right[2] * 0.8 * side
                self._draw(self.vao_eye, translate(ex, cy + 2.7, ez), vp, (0.08, 0.08, 0.10), env)

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


# =========================================================================
# headless render (for verification in a GPU-less environment)
# =========================================================================
def render_headless(path, size=(1000, 700), phase=0.5, season="summer",
                    weather="clear", seed=7, steps=40):
    import moderngl
    ctx = moderngl.create_standalone_context()
    fbo = ctx.simple_framebuffer(size)
    fbo.use()
    world = World(init_pop=8, predator_count=0)
    for _ in range(steps):
        world.step()
    renderer = Renderer(ctx, size)
    renderer.render(world, Camera(), environment(phase, season, weather), dt=0.05)
    data = fbo.read(components=3)
    try:
        from PIL import Image
        Image.frombytes("RGB", size, data).transpose(Image.FLIP_TOP_BOTTOM).save(path)
    except ImportError:
        import pygame
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
    ctx = moderngl.create_context()
    renderer = Renderer(ctx, size)
    cam = Camera()
    world = World(init_pop=8, predator_count=0)

    phase = 0.35            # early morning
    season_i, weather_i = 1, 0
    fast_time = False
    clock = pygame.time.Clock()
    dragging = False
    running = True
    accum = 0.0

    def caption():
        pygame.display.set_caption(
            "Thronglets true-3D  |  %s  |  %s  |  %02d:%02d" % (
                SEASONS[season_i], WEATHERS[weather_i],
                int(phase * 24) % 24, int(phase * 24 * 60) % 60))

    caption()
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_s:
                    season_i = (season_i + 1) % len(SEASONS); caption()
                elif event.key == pygame.K_w:
                    weather_i = (weather_i + 1) % len(WEATHERS); caption()
                elif event.key == pygame.K_t:
                    fast_time = not fast_time
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                cam.orbit(event.rel[0], -event.rel[1])
            elif event.type == pygame.MOUSEWHEEL:
                cam.zoom(event.y)

        # advance the day: a full cycle in ~2 min (or ~12 s in fast mode)
        phase = (phase + dt / (12.0 if fast_time else 120.0)) % 1.0
        accum += dt
        if accum >= 0.12:
            world.step()
            accum = 0.0
        if int(phase * 24 * 60) % 5 == 0:
            caption()

        env = environment(phase, SEASONS[season_i], WEATHERS[weather_i])
        renderer.render(world, cam, env, dt=dt)
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
