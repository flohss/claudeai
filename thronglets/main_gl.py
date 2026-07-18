"""A *true* 3D proof-of-concept renderer for the Thronglets world.

Every other renderer in this project is 2D: main.py / main_tui.py /
main_web.py draw flat, and main_vr.py is a *pseudo*-3D trick (2D shapes
projected onto a fake ground plane). This file is different - it is real
3D: an OpenGL scene with a perspective camera you can orbit, a lit ground
mesh, three-dimensional trees and rocks, and the creatures as lit spheres
standing on the ground. Nothing here is a 2D blit.

It is deliberately a *proof of concept*, not a port of the whole game:
there is no care menu, no seasons, no weather, no learning UI yet. The
point is to answer one question - "can this world look good in genuine
3D, and is it worth building out?" - with something you can actually
look at and orbit around. The simulation itself is the real thing: it
reuses simulation.World, so the spheres you see are real creatures at
their real positions, stepped every frame.

Rendering goes through moderngl (OpenGL 3.3 core). On a normal machine
pygame opens the window and moderngl draws into it; run it with:

    python3 main_gl.py

Controls: LEFT-drag orbits the camera, scroll wheel zooms, and the world
steps on its own. Press ESC or close the window to quit.

Because this environment has no GPU, the scene can also be rendered
off-screen into a PNG for verification (render_headless), which is how the
look was checked - Mesa's software rasterizer (llvmpipe) under a virtual
framebuffer produces the exact same image a GPU would.
"""

import math
import os
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

# --- scene palette (linear-ish RGB, 0..1) --------------------------------
GROUND_COLOR = (0.24, 0.48, 0.20)
TRUNK_COLOR = (0.38, 0.26, 0.15)
CANOPY_COLOR = (0.13, 0.36, 0.13)
CROWN_COLOR = (0.20, 0.46, 0.19)      # a lighter second tone on top
ROCK_COLOR = (0.48, 0.48, 0.53)
SKY_ZENITH = (0.24, 0.50, 0.86)
SKY_HORIZON = (0.72, 0.83, 0.94)
SUN_DIR = (0.40, 0.82, 0.32)          # direction TO the sun
SUN_COLOR = (1.05, 0.99, 0.86)
AMBIENT = (0.30, 0.36, 0.46)          # bluish sky bounce
FOG_DENSITY = 0.0030

# world (200 x 140) -> a centred patch of the ground plane
WORLD_SCALE = 0.9


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
def mesh_ground(size):
    h = size / 2.0
    n = (0.0, 1.0, 0.0)
    quad = [
        (-h, 0.0, -h, *n), (h, 0.0, -h, *n), (h, 0.0, h, *n),
        (-h, 0.0, -h, *n), (h, 0.0, h, *n), (-h, 0.0, h, *n),
    ]
    return np.array(quad, dtype="f4")


def mesh_uv_sphere(radius=1.0, stacks=16, slices=24, jitter=0.0, seed=0):
    """A unit-ish sphere. jitter>0 roughens the radius per-vertex for a
    faceted rock; seed keeps a given rock stable."""
    rng = np.random.default_rng(seed)
    grid = {}

    def vert(i, j):
        key = (i, j)
        if key not in grid:
            phi = math.pi * i / stacks           # 0..pi
            theta = 2 * math.pi * j / slices      # 0..2pi
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


def mesh_cone(radius=1.0, height=1.0, slices=20):
    tris = []
    apex = (0.0, height, 0.0)
    for j in range(slices):
        t0 = 2 * math.pi * j / slices
        t1 = 2 * math.pi * (j + 1) / slices
        x0, z0 = math.cos(t0), math.sin(t0)
        x1, z1 = math.cos(t1), math.sin(t1)
        p0 = (x0 * radius, 0.0, z0 * radius)
        p1 = (x1 * radius, 0.0, z1 * radius)
        # a smooth-ish side normal
        n0 = (x0, radius / height, z0)
        n1 = (x1, radius / height, z1)
        tris += [(*p0, *n0), (*p1, *n1), (*apex, *n0)]
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
in vec3 v_world;
in vec3 v_norm;
out vec4 f_color;
void main() {
    vec3 n = normalize(v_norm);
    float diff = max(dot(n, normalize(u_lightdir)), 0.0);
    vec3 base = u_color;
    if (u_grid == 1) {
        vec2 c = v_world.xz / 9.0;
        vec2 g = abs(fract(c - 0.5) - 0.5) / fwidth(c);
        float line = 1.0 - min(min(g.x, g.y), 1.0);
        base = mix(base, base * 0.80, line * 0.55);
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
in vec3 in_norm;
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
uniform vec2 u_sun;
in vec2 v_uv;
out vec4 f_color;
void main() {
    float t = pow(clamp(v_uv.y, 0.0, 1.0), 0.8);
    vec3 col = mix(u_horizon, u_zenith, t);
    float d = distance(v_uv, u_sun);
    float glow = exp(-d * d * 55.0);
    col += vec3(1.0, 0.95, 0.8) * glow * 0.9;
    f_color = vec4(col, 1.0);
}
"""


# =========================================================================
# scene generation
# =========================================================================
def make_scene(seed=7):
    """Scatter trees and rocks across the plane (deterministic per seed).
    Returns (trees, rocks) lists of (x, z, scale, yaw)."""
    rng = np.random.default_rng(seed)
    trees, rocks = [], []
    for _ in range(46):
        x = (rng.random() - 0.5) * 170
        z = (rng.random() - 0.5) * 120
        if abs(x) < 14 and abs(z) < 14:
            continue
        trees.append((x, z, 0.8 + rng.random() * 0.7, rng.random() * 6.28))
    for _ in range(9):
        x = (rng.random() - 0.5) * 160
        z = (rng.random() - 0.5) * 110
        rocks.append((x, z, 0.7 + rng.random() * 0.8, rng.random() * 6.28))
    return trees, rocks


def world_to_scene(pos):
    """simulation.World (0..WIDTH, 0..HEIGHT) -> centred ground coords."""
    x = (float(pos[0]) - WIDTH / 2.0) * WORLD_SCALE
    z = (float(pos[1]) - HEIGHT / 2.0) * WORLD_SCALE
    return x, z


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

        self.trees, self.rocks = make_scene()

        # geometry
        self.vao_ground = self._vao(self.lit, mesh_ground(600.0))
        self.vao_trunk = self._vao(self.lit, mesh_cylinder(0.6, 4.6, 14))
        self.vao_canopy = self._vao(self.lit, mesh_uv_sphere(3.4, 12, 16))
        self.vao_cone = self._vao(self.lit, mesh_cone(3.2, 6.0, 18))
        self.vao_creature = self._vao(self.lit, mesh_uv_sphere(2.2, 16, 24))
        self.vao_eye = self._vao(self.lit, mesh_uv_sphere(0.45, 8, 10))
        # the shadow shader only reads position, so skip the normal (3x4)
        disc_vbo = ctx.buffer(mesh_disc(1.0).tobytes())
        self.vao_disc = ctx.vertex_array(self.shadow, [(disc_vbo, "3f 3x4", "in_pos")])
        # rocks get individual faceted meshes so they don't all look alike
        self.vao_rocks = [
            self._vao(self.lit, mesh_uv_sphere(2.6, 6, 8, jitter=0.55, seed=i))
            for i in range(len(self.rocks))
        ]

        sky_quad = np.array([-1, -1, 3, -1, -1, 3], dtype="f4")
        self.vbo_sky = ctx.buffer(sky_quad.tobytes())
        self.vao_sky = ctx.vertex_array(self.sky, [(self.vbo_sky, "2f", "in_pos")])

        # constant lighting uniforms
        self.lit["u_lightdir"].value = tuple(np.array(SUN_DIR) / np.linalg.norm(SUN_DIR))
        self.lit["u_lightcol"].value = SUN_COLOR
        self.lit["u_ambient"].value = AMBIENT
        self.lit["u_fogcol"].value = SKY_HORIZON
        self.lit["u_fogdensity"].value = FOG_DENSITY
        self.sky["u_zenith"].value = SKY_ZENITH
        self.sky["u_horizon"].value = SKY_HORIZON
        self.sky["u_sun"].value = (0.5, 0.86)

    def _vao(self, prog, verts, attribs=("in_pos", "in_norm")):
        vbo = self.ctx.buffer(verts.tobytes())
        return self.ctx.vertex_array(prog, [(vbo, "3f 3f", *attribs)])

    def _draw(self, vao, model, view_proj, color, grid=0):
        self.lit["mvp"].write(_bytes(view_proj @ model))
        self.lit["model"].write(_bytes(model))
        self.lit["u_color"].value = color
        self.lit["u_grid"].value = grid
        vao.render()

    def _shadow(self, x, z, r, view_proj):
        m = translate(x, 0.04, z) @ scale(r, 1.0, r)
        self.shadow["mvp"].write(_bytes(view_proj @ m))
        self.shadow["u_color"].value = (0.05, 0.10, 0.05, 0.28)
        self.vao_disc.render()

    def render(self, world, camera):
        ctx = self.ctx
        eye, target = camera.eye_target()
        view = look_at(eye, target, (0, 1, 0))
        proj = perspective(52.0, self.size[0] / self.size[1], 1.0, 900.0)
        vp = proj @ view
        self.lit["u_campos"].value = tuple(float(v) for v in eye)

        ctx.clear(depth=1.0)
        # sky first, no depth
        ctx.disable(ctx.DEPTH_TEST)
        self.vao_sky.render()
        ctx.enable(ctx.DEPTH_TEST)

        # ground
        self._draw(self.vao_ground, _identity(), vp, GROUND_COLOR, grid=1)

        # contact shadows (blended, no depth write)
        ctx.enable(ctx.BLEND)
        ctx.depth_mask = False
        for x, z, s, _yaw in self.trees:
            self._shadow(x, z, 3.6 * s, vp)
        for (x, z, s, _yaw) in self.rocks:
            self._shadow(x, z, 3.0 * s, vp)
        for c in world.creatures:
            if c.alive:
                cx, cz = world_to_scene(c.pos)
                self._shadow(cx, cz, 2.6, vp)
        ctx.depth_mask = True
        ctx.disable(ctx.BLEND)

        # trees: trunk + rounded canopy
        for x, z, s, yaw in self.trees:
            base = translate(x, 0.0, z) @ rotate_y(yaw) @ scale(s, s, s)
            self._draw(self.vao_trunk, base, vp, TRUNK_COLOR)
            canopy = base @ translate(0.0, 5.4, 0.0)
            self._draw(self.vao_canopy, canopy, vp, CANOPY_COLOR)
            crown = base @ translate(0.0, 8.4, 0.0) @ scale(0.7, 0.7, 0.7)
            self._draw(self.vao_canopy, crown, vp, CROWN_COLOR)

        # rocks
        for (x, z, s, yaw), vao in zip(self.rocks, self.vao_rocks):
            m = translate(x, 1.0 * s, z) @ rotate_y(yaw) @ scale(s, s * 0.7, s)
            self._draw(vao, m, vp, ROCK_COLOR)

        # creatures as lit spheres with two camera-facing eyes
        fwd = np.array([eye[0], 0.0, eye[2]])
        for c in world.creatures:
            if not c.alive:
                continue
            cx, cz = world_to_scene(c.pos)
            col = TOKEN_COLORS_F[c.token % len(TOKEN_COLORS_F)]
            body = translate(cx, 2.1, cz)
            self._draw(self.vao_creature, body, vp, col)
            face = np.array([eye[0] - cx, 0.0, eye[2] - cz])
            if np.linalg.norm(face) > 1e-3:
                face /= np.linalg.norm(face)
            right = np.cross(np.array([0.0, 1.0, 0.0]), face)
            for side in (-1, 1):
                ex = cx + face[0] * 2.0 + right[0] * 0.8 * side
                ez = cz + face[2] * 2.0 + right[2] * 0.8 * side
                eye_m = translate(ex, 2.7, ez)
                self._draw(self.vao_eye, eye_m, vp, (0.08, 0.08, 0.10))


class Camera:
    """Orbit camera: azimuth/elevation around a ground target, at a
    distance you can zoom."""

    def __init__(self):
        self.azimuth = 0.7
        self.elevation = 0.42
        self.distance = 150.0
        self.target = np.array([0.0, 4.0, 0.0])

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
def render_headless(path, size=(1000, 700), seed=7, steps=40):
    import moderngl
    ctx = moderngl.create_standalone_context()
    fbo = ctx.simple_framebuffer(size)
    fbo.use()
    world = World(init_pop=8, predator_count=0)
    world.seed = seed
    for _ in range(steps):
        world.step()
    renderer = Renderer(ctx, size)
    cam = Camera()
    renderer.render(world, cam)
    data = fbo.read(components=3)
    try:
        from PIL import Image
        img = Image.frombytes("RGB", size, data).transpose(Image.FLIP_TOP_BOTTOM)
        img.save(path)
    except ImportError:
        import pygame
        surf = pygame.image.fromstring(data, size, "RGB")
        surf = pygame.transform.flip(surf, False, True)
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
    pygame.display.set_caption("Thronglets - true 3D (proof of concept)")
    ctx = moderngl.create_context()
    renderer = Renderer(ctx, size)
    cam = Camera()
    world = World(init_pop=8, predator_count=0)

    clock = pygame.time.Clock()
    dragging = False
    running = True
    accum = 0.0
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                cam.orbit(event.rel[0], -event.rel[1])
            elif event.type == pygame.MOUSEWHEEL:
                cam.zoom(event.y)
        accum += dt
        if accum >= 0.12:          # step the sim a few times a second
            world.step()
            accum = 0.0
        renderer.render(world, cam)
        pygame.display.flip()
    pygame.quit()


if __name__ == "__main__":
    if "--headless" in sys.argv:
        out = "gl_poc.png"
        for a in sys.argv:
            if a.startswith("--out="):
                out = a.split("=", 1)[1]
        render_headless(out)
    else:
        main()
