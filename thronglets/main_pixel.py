"""A native pixel-art renderer for the Thronglets world.

Unlike main_vr.py (which draws smooth vector shapes at full resolution),
this one is *real* pixel art: the whole scene is drawn onto a tiny
low-resolution canvas (RENDER_W x RENDER_H) with a small fixed palette and
no anti-aliasing, then blown up to the window with nearest-neighbour
scaling so every pixel stays hard and square. Because the shapes are drawn
directly on the pixel grid at that small size, the result is genuine pixel
art - not a photo passed through a blur/pixelate filter.

The scene is built the way a pixel artist layers a parallax background,
back to front - each `draw_*` function below is one layer:

    sky  ->  sun/moon  ->  mountains  ->  forest band  ->  ground  ->
    river  ->  foreground trees & rocks  ->  creatures  ->  food  ->  HUD

The population itself is the real thing: a genuine simulation.py World
(no predators - a safe world, like main_vr.py), stepped every frame, its
creatures projected into the same pseudo-3D ground plane and depth-sorted
so nearer ones cover farther ones.

Controls:
  SPACE        pause / resume
  LEFT / RIGHT pan the camera
  UP / DOWN    simulation speed
  N            drop a patch of food at a random spot
  R            reset to a fresh world + landscape
  ESC          quit

Run it with:  python main_pixel.py
"""

import math
import random
import sys

import numpy as np
import pygame

from simulation import HEIGHT, WIDTH, World

# --- the pixel canvas -------------------------------------------------------
# Everything is drawn at this tiny resolution, then scaled up by PIXEL_SCALE.
RENDER_W, RENDER_H = 320, 200
PIXEL_SCALE = 4                       # window is RENDER * PIXEL_SCALE
WINDOW_W, WINDOW_H = RENDER_W * PIXEL_SCALE, RENDER_H * PIXEL_SCALE
HORIZON_Y = int(RENDER_H * 0.42)      # where the ground meets the sky

DAY_CYCLE_SECONDS = 90.0              # a full day/night loop

# --- a small, fixed palette (the whole game is drawn from these) ------------
PALETTE = {
    "sky_day_top":    (92, 148, 208),
    "sky_day_low":    (170, 206, 232),
    "sky_night_top":  (20, 24, 52),
    "sky_night_low":  (54, 58, 96),
    "sun":            (250, 232, 150),
    "moon":           (224, 228, 236),
    "star":           (238, 240, 220),
    "mountain_far":   (96, 104, 126),
    "mountain_near":  (74, 82, 104),
    "mountain_snow":  (216, 224, 236),
    "forest_dark":    (30, 78, 52),
    "forest_mid":     (44, 104, 66),
    "ground_far":     (86, 150, 78),
    "ground_near":    (66, 128, 60),
    "grass_blade":    (110, 176, 92),
    "water_deep":     (44, 96, 150),
    "water_shallow":  (96, 164, 208),
    "water_glint":    (206, 230, 244),
    "trunk":          (86, 58, 40),
    "leaf_dark":      (36, 92, 56),
    "leaf_light":     (66, 132, 78),
    "rock":           (108, 108, 118),
    "rock_shade":     (78, 78, 90),
    "egg":            (238, 230, 202),
    "egg_shade":      (198, 184, 150),
    "critter_body":   (240, 208, 72),
    "critter_belly":  (74, 128, 196),
    "critter_dark":   (40, 40, 48),
    "hud_bg":         (16, 18, 20),
    "hud_text":       (232, 236, 226),
}

# evolved-signal (token) colours - what each creature "says", 0 = silent/grey
TOKEN_COLORS = {
    0: (150, 150, 150),
    1: (226, 92, 92),
    2: (232, 168, 64),
    3: (240, 224, 88),
    4: (96, 196, 112),
    5: (120, 148, 232),
}


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color)


# --- the pseudo-3D projection ----------------------------------------------
def project(world_pos, pan_x):
    """World (x, y) -> canvas (x, y, scale). The field's Y axis is depth:
    the top of the field sits at the horizon (far, small), the bottom sits
    near the camera (close, big). Returns integer-friendly floats plus a
    0..~1 scale for sizing sprites."""
    x_norm = (world_pos[0] / WIDTH) * 2.0 - 1.0 - pan_x
    z = max(0.02, min(1.0, world_pos[1] / HEIGHT))
    spread = RENDER_W * 0.5 * (0.16 + z * 0.9)
    sx = RENDER_W / 2 + x_norm * spread
    sy = HORIZON_Y + z * (RENDER_H - HORIZON_Y)
    scale = 0.18 + z * 1.0
    return sx, sy, z, scale


# --- procedural, seeded landscape (a new one per game) ----------------------
def generate_landscape(seed=None):
    rng = random.Random(seed)
    # a jagged mountain skyline: one height per canvas column
    ridge = []
    h = rng.uniform(0.35, 0.6)
    for _ in range(RENDER_W):
        h += rng.uniform(-0.05, 0.05)
        h = max(0.2, min(0.75, h))
        ridge.append(h)
    # smooth it a touch so it reads as hills, not noise
    smooth = ridge[:]
    for i in range(1, RENDER_W - 1):
        smooth[i] = (ridge[i - 1] + ridge[i] + ridge[i + 1]) / 3.0
    # a river that meanders down the field (world x per depth band)
    river_x = rng.uniform(0.35, 0.65)
    # foreground trees & rocks, kept out of the river's path
    trees, rocks = [], []
    for _ in range(14):
        wx, wy = rng.uniform(6, WIDTH - 6), rng.uniform(HEIGHT * 0.45, HEIGHT - 6)
        if abs(wx / WIDTH - river_x) < 0.09:
            continue
        trees.append((wx, wy, rng.uniform(0.85, 1.25)))
    for _ in range(8):
        wx, wy = rng.uniform(6, WIDTH - 6), rng.uniform(HEIGHT * 0.5, HEIGHT - 4)
        if abs(wx / WIDTH - river_x) < 0.07:
            continue
        rocks.append((wx, wy, rng.uniform(0.8, 1.3)))
    return {"ridge": smooth, "river_x": river_x, "trees": trees, "rocks": rocks}


# --- day/night ---------------------------------------------------------------
def celestial(day_phase):
    theta = day_phase * 2 * math.pi
    sun_h = math.sin(theta)
    day_amount = (sun_h + 1) / 2
    return sun_h, day_amount


# =====================  LAYERS  (drawn back to front)  ======================
def draw_sky(canvas, day_amount):
    """Layer 1 - a banded vertical gradient. Posterised into a handful of
    horizontal bands on purpose, the classic pixel-art sky look."""
    top = lerp(PALETTE["sky_night_top"], PALETTE["sky_day_top"], day_amount)
    low = lerp(PALETTE["sky_night_low"], PALETTE["sky_day_low"], day_amount)
    bands = 7
    for b in range(bands):
        y0 = int(b / bands * HORIZON_Y)
        y1 = int((b + 1) / bands * HORIZON_Y)
        col = lerp(top, low, b / (bands - 1))
        pygame.draw.rect(canvas, col, (0, y0, RENDER_W, y1 - y0))


def draw_stars(canvas, day_amount, stars):
    if day_amount > 0.35:
        return
    for (sx, sy) in stars:
        canvas.set_at((sx, sy), PALETTE["star"])


def draw_celestial(canvas, day_phase):
    """Layer 2 - the sun by day, the moon by night, tracking an arc."""
    sun_h, day_amount = celestial(day_phase)
    up = sun_h if day_amount >= 0.5 else -sun_h
    if up <= -0.1:
        return
    # x tracks the phase across the sky, y rides the arc height
    x = int((day_phase % 0.5) / 0.5 * RENDER_W)
    y = int(HORIZON_Y - 8 - up * (HORIZON_Y - 14))
    color = PALETTE["sun"] if day_amount >= 0.5 else PALETTE["moon"]
    pygame.draw.circle(canvas, color, (x, y), 7)


def draw_mountains(canvas, ridge, day_amount):
    """Layer 3 - the jagged skyline filling the whole horizon, back to front."""
    far = shade(PALETTE["mountain_far"], 0.5 + 0.5 * day_amount)
    near = shade(PALETTE["mountain_near"], 0.5 + 0.5 * day_amount)
    snow = PALETTE["mountain_snow"]
    # a far, flatter range first
    for x in range(RENDER_W):
        top = HORIZON_Y - int(ridge[x] * 0.55 * HORIZON_Y)
        pygame.draw.line(canvas, far, (x, top + 6), (x, HORIZON_Y))
    # then a nearer, taller range with snow caps
    for x in range(RENDER_W):
        top = HORIZON_Y - int(ridge[x] * HORIZON_Y)
        pygame.draw.line(canvas, near, (x, top), (x, HORIZON_Y))
        if ridge[x] > 0.6:
            canvas.set_at((x, top), snow)
            if x % 2 == 0:
                canvas.set_at((x, top + 1), snow)


def draw_forest_band(canvas, day_amount):
    """Layer 4 - a dense band of little trees along the mid-distance, edge
    to edge, sitting just below the horizon."""
    base = HORIZON_Y
    band_h = 16
    dark = shade(PALETTE["forest_dark"], 0.6 + 0.4 * day_amount)
    mid = shade(PALETTE["forest_mid"], 0.6 + 0.4 * day_amount)
    pygame.draw.rect(canvas, dark, (0, base, RENDER_W, band_h))
    for x in range(0, RENDER_W, 4):
        h = 4 + (x * 7 % 5)
        pygame.draw.rect(canvas, mid, (x, base - h + 2, 3, h))
        canvas.set_at((x + 1, base - h + 1), mid)


def draw_ground(canvas, day_amount, t):
    """Layer 5 - the open plain, a few posterised green bands from the
    forest's foot down to the camera, speckled with grass pixels."""
    far = shade(PALETTE["ground_far"], 0.55 + 0.45 * day_amount)
    near = shade(PALETTE["ground_near"], 0.55 + 0.45 * day_amount)
    top = HORIZON_Y + 14
    for y in range(top, RENDER_H):
        col = lerp(far, near, (y - top) / (RENDER_H - top))
        pygame.draw.line(canvas, col, (0, y), (RENDER_W, y))
    # scattered grass blades (deterministic, so they don't crawl)
    blade = shade(PALETTE["grass_blade"], 0.55 + 0.45 * day_amount)
    for i in range(140):
        gx = (i * 53) % RENDER_W
        gy = top + (i * 31) % (RENDER_H - top)
        if gy > top + 2:
            canvas.set_at((gx, gy), blade)


def draw_river(canvas, river_x, day_amount, t):
    """Layer 6 - the river, widening as it nears the camera, with a lighter
    core and a couple of drifting glints."""
    deep = shade(PALETTE["water_deep"], 0.55 + 0.45 * day_amount)
    shallow = shade(PALETTE["water_shallow"], 0.55 + 0.45 * day_amount)
    top = HORIZON_Y + 12
    for y in range(top, RENDER_H):
        z = (y - top) / (RENDER_H - top)
        meander = math.sin(z * 3.0 + 0.4) * 0.03
        cx = int((river_x + meander) * RENDER_W)
        half = int(1 + z * 12)
        pygame.draw.line(canvas, deep, (cx - half, y), (cx + half, y))
        core = max(0, half - 3)
        if core:
            pygame.draw.line(canvas, shallow, (cx - core, y), (cx + core, y))
        # a drifting glint
        if (y + int(t * 6)) % 9 == 0 and core > 1:
            canvas.set_at((cx + (y % 3) - 1, y), PALETTE["water_glint"])


def _draw_tree(canvas, sx, sy, scale, day_amount):
    trunk = shade(PALETTE["trunk"], 0.6 + 0.4 * day_amount)
    dark = shade(PALETTE["leaf_dark"], 0.6 + 0.4 * day_amount)
    light = shade(PALETTE["leaf_light"], 0.6 + 0.4 * day_amount)
    th = max(4, int(16 * scale))
    tw = max(1, int(2 * scale))
    cw = max(4, int(14 * scale))
    ch = max(4, int(16 * scale))
    x, y = int(sx), int(sy)
    pygame.draw.rect(canvas, trunk, (x - tw // 2, y - th, tw, th))
    canopy = pygame.Rect(x - cw // 2, y - th - ch + 2, cw, ch)
    pygame.draw.ellipse(canvas, dark, canopy)
    inner = canopy.inflate(-max(2, cw // 3), -max(2, ch // 3))
    inner.move_ip(-1, -1)
    pygame.draw.ellipse(canvas, light, inner)


def _draw_rock(canvas, sx, sy, scale, day_amount):
    rock = shade(PALETTE["rock"], 0.6 + 0.4 * day_amount)
    dark = shade(PALETTE["rock_shade"], 0.6 + 0.4 * day_amount)
    w = max(3, int(10 * scale))
    h = max(2, int(7 * scale))
    x, y = int(sx), int(sy)
    pygame.draw.ellipse(canvas, dark, (x - w // 2, y - h, w, h))
    pygame.draw.ellipse(canvas, rock, (x - w // 2, y - h - 1, w, h))


def _draw_critter(canvas, sx, sy, scale, token, distressed=False):
    """A little pixel critter, built entirely from squares (no curves): a
    square yellow head (its skin), a blue square torso, and blue arms and
    legs whose tips are bare yellow skin - the hands and the feet. A 1px
    rim of its evolved-signal colour frames the head."""
    skin = PALETTE["critter_body"]      # yellow: head, hands, feet
    cloth = PALETTE["critter_belly"]    # blue: torso, arms, legs
    dark = PALETTE["critter_dark"]
    ring = TOKEN_COLORS.get(token, TOKEN_COLORS[0])

    cx = int(sx)
    foot = int(sy)                      # the feet rest on the projected ground point
    hw = max(3, int(9 * scale))         # head side (square)
    tw = max(3, int(8 * scale))         # torso width
    th = max(2, int(5 * scale))         # torso height
    legl = max(2, int(4 * scale))       # leg length
    legt = max(1, hw // 4)              # leg thickness
    footh = max(1, legt)                # yellow foot height
    armw = max(1, hw // 4)              # arm thickness (runs down the side)
    handh = max(1, armw)                # yellow hand height at the arm's end

    torso_bottom = foot - legl
    torso_top = torso_bottom - th
    head_bottom = torso_top
    head_top = head_bottom - hw

    # --- legs: blue stubs standing on bare yellow feet ---
    for lx in (cx - tw // 2, cx + tw // 2 - legt):
        pygame.draw.rect(canvas, cloth, (lx, torso_bottom, legt, legl - footh))
        pygame.draw.rect(canvas, skin, (lx, torso_bottom + legl - footh, legt, footh))

    # --- torso (blue square) ---
    pygame.draw.rect(canvas, cloth, (cx - tw // 2, torso_top, tw, th))

    # --- arms: blue, hanging straight down each side of the torso, ending
    #     in bare yellow hands ---
    for ax in (cx - tw // 2 - armw, cx + tw // 2):
        pygame.draw.rect(canvas, cloth, (ax, torso_top, armw, th - handh))
        pygame.draw.rect(canvas, skin, (ax, torso_top + th - handh, armw, handh))

    # --- head: a yellow square, framed by the token colour ---
    head = pygame.Rect(cx - hw // 2, head_top, hw, hw)
    pygame.draw.rect(canvas, ring, head.inflate(2, 2))   # 1px coloured frame
    pygame.draw.rect(canvas, skin, head)

    # --- face ---
    if hw >= 5:
        eye = max(1, hw // 5)
        ey = head_top + hw // 3
        pygame.draw.rect(canvas, dark, (cx - hw // 4, ey, eye, eye))
        pygame.draw.rect(canvas, dark, (cx + hw // 4 - eye + 1, ey, eye, eye))
        my = head_top + (hw * 2) // 3
        mw = max(2, hw // 3)
        if distressed:
            pygame.draw.rect(canvas, dark, (cx - mw // 2, my, mw, max(1, hw // 5)))  # open, worried
        else:
            pygame.draw.rect(canvas, dark, (cx - mw // 2, my, mw, 1))                 # a small flat mouth
    else:
        canvas.set_at((cx, head_top + hw // 2), dark)


def draw_entities(canvas, world, pan_x, day_amount, landscape):
    """Layers 7-8 - foreground trees, rocks and the live creatures, all
    depth-sorted together so nearer things correctly cover farther ones."""
    ents = []
    for (wx, wy, s) in landscape["trees"]:
        sx, sy, z, sc = project((wx, wy), pan_x)
        ents.append((z, "tree", sx, sy, sc * s))
    for (wx, wy, s) in landscape["rocks"]:
        sx, sy, z, sc = project((wx, wy), pan_x)
        ents.append((z, "rock", sx, sy, sc * s))
    for c in world.creatures:
        if not c.alive:
            continue
        sx, sy, z, sc = project(c.pos, pan_x)
        ents.append((z, "critter", sx, sy, sc, c.token, c.energy))
    ents.sort(key=lambda e: e[0])   # far (small z) first
    for e in ents:
        kind = e[1]
        if kind == "tree":
            _draw_tree(canvas, e[2], e[3], e[4], day_amount)
        elif kind == "rock":
            _draw_rock(canvas, e[2], e[3], e[4], day_amount)
        else:
            distressed = e[6] < 20.0
            _draw_critter(canvas, e[2], e[3], e[4], e[5], distressed)


def draw_food(canvas, world, pan_x):
    """Layer 9 - the food pellets on the ground."""
    for f in world.food:
        sx, sy, z, sc = project(f, pan_x)
        canvas.set_at((int(sx), int(sy)), (120, 210, 90))
        if sc > 0.6:
            canvas.set_at((int(sx) + 1, int(sy)), (150, 230, 110))


# --- HUD (drawn on the upscaled window, so text stays readable) -------------
def draw_hud(window, font, world, paused, speed):
    status = "PAUSED" if paused else f"x{speed}"
    line = f"pop {world.population()}   {status}"
    window.blit(font.render(line, True, PALETTE["hud_text"]), (10, 8))
    hint = font.render("SPACE pause   LEFT/RIGHT pan   UP/DOWN speed   N food   R reset   ESC quit",
                       True, PALETTE["hud_text"])
    window.blit(hint, (10, WINDOW_H - 22))


def new_world():
    return World(init_pop=18, predator_count=0, learning=True)


def main():
    pygame.init()
    pygame.display.set_caption("Thronglets - pixel art")
    window = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    canvas = pygame.Surface((RENDER_W, RENDER_H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    world = new_world()
    landscape = generate_landscape()
    stars = [(random.randint(0, RENDER_W - 1), random.randint(0, HORIZON_Y - 4)) for _ in range(50)]

    pan_x = 0.0
    paused = False
    speed = 4
    day_phase = 0.15
    t = 0.0
    tick_accumulator = 0.0

    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.25)
        t += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_UP:
                    speed = min(60, speed + 2)
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed - 2)
                elif event.key == pygame.K_n:
                    world.add_food(random.uniform(0, WIDTH), random.uniform(0, HEIGHT))
                elif event.key == pygame.K_r:
                    world = new_world()
                    landscape = generate_landscape()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            pan_x -= 0.7 * dt
        if keys[pygame.K_RIGHT]:
            pan_x += 0.7 * dt

        if not paused:
            day_phase = (day_phase + dt / DAY_CYCLE_SECONDS) % 1.0
            tick_accumulator += dt
            step_interval = 1.0 / speed
            while tick_accumulator >= step_interval:
                world.step()
                tick_accumulator -= step_interval

        _, day_amount = celestial(day_phase)

        # ---- compose the scene, layer by layer, on the low-res canvas ----
        draw_sky(canvas, day_amount)
        draw_stars(canvas, day_amount, stars)
        draw_celestial(canvas, day_phase)
        draw_mountains(canvas, landscape["ridge"], day_amount)
        draw_forest_band(canvas, day_amount)
        draw_ground(canvas, day_amount, t)
        draw_river(canvas, landscape["river_x"], day_amount, t)
        draw_food(canvas, world, pan_x)
        draw_entities(canvas, world, pan_x, day_amount, landscape)

        # ---- blow the canvas up to the window with hard pixels ----
        pygame.transform.scale(canvas, (WINDOW_W, WINDOW_H), window)
        draw_hud(window, font, world, paused, speed)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
