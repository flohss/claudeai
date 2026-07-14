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
that actually evolved their own colors and genuinely react to danger. The
sensors don't touch the genome or the evolutionary mechanics at all - they
just occasionally add a transient predator (like a real predator sighting)
when the room gets loud or something moves in front of the camera, and let
the population's already-evolved alarm response do the rest.

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

The creature design is an original, simplified, geometric interpretation
of the look (round yellow body, two hair-tufts, big eyes, blue lower
half) - not a reproduction of the show's or the licensed game's actual
pixel art.

Controls:
  LEFT CLICK     crack the egg (before it hatches)
  LEFT / RIGHT   pan the view
  SPACE          pause / resume
  UP / DOWN      simulation speed
  R              reset to a fresh egg
  A              toggle the microphone sensor
  C              toggle the camera sensor
  [ / ]          lower / raise the alert sensitivity threshold
  ESC            quit
"""

import math
import sys
import threading

import numpy as np
import pygame

from simulation import HEIGHT, WIDTH, World

SCREEN_W, SCREEN_H = 1000, 700
HORIZON_Y = int(SCREEN_H * 0.42)

SKY_TOP = (40, 70, 130)
SKY_HORIZON = (178, 212, 235)
SUN_COLOR = (255, 236, 180)
HILL_FAR = (100, 140, 120)
HILL_NEAR = (80, 125, 95)
GROUND_FAR = (95, 165, 100)
GROUND_NEAR = (55, 130, 65)
GRID_COLOR = (70, 150, 80)
TREE_TRUNK = (90, 65, 45)
TREE_LEAVES = (55, 115, 60)

BODY_COLOR = (245, 210, 70)
HAIR_COLOR = (225, 90, 60)
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

ALERT_DURATION = 2.5    # seconds the phantom predator sighting lasts
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


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


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

    def register_click(self, mx, my):
        if self.hatched or not egg_contains(mx, my, EGG_STAGE_X, EGG_STAGE_Z):
            return False
        self.cracks += 1
        self.pulse = 1.0
        if self.cracks >= EGG_CLICKS_NEEDED:
            self.hatched = True
            return True
        return False

    def update(self, dt):
        self.pulse = max(0.0, self.pulse - dt * 4.0)


class AlertState:
    """Turns a sensor's alert_level() into a transient predator sighting:
    reused via World.add_random_predator()/remove_predator() rather than
    touching genomes or danger-state directly, so the population's
    already-evolved alarm response does all the actual reacting."""

    def __init__(self):
        self.active_timer = 0.0
        self.cooldown_timer = 0.0
        self.flash = 0.0

    def update(self, world, sensors, threshold, dt):
        self.cooldown_timer = max(0.0, self.cooldown_timer - dt)
        self.flash = max(0.0, self.flash - dt)
        if self.active_timer > 0:
            self.active_timer -= dt
            if self.active_timer <= 0:
                world.remove_predator()
        elif sensors.alert_level() > threshold and self.cooldown_timer <= 0:
            world.add_random_predator()
            self.active_timer = ALERT_DURATION
            self.cooldown_timer = ALERT_COOLDOWN
            self.flash = 0.6


def world_to_stage(pos):
    """Reuses the World's own 2D layout as the pseudo-3D stage: its Y axis
    becomes depth (top of the field = far/near the horizon, bottom = close
    to the camera), its X axis stays lateral."""
    x_norm = (pos[0] / WIDTH) * 2.6 - 1.3
    z = max(0.02, min(1.0, pos[1] / HEIGHT))
    return x_norm, z


def project(x, z):
    """x: lateral offset (roughly -1.3..1.3), z: depth, 0 = far/near the
    horizon, 1 = close to the camera. Returns (screen_x, screen_y, scale) -
    farther things are smaller and closer to the screen's horizontal
    center, the classic converging-perspective illusion."""
    scale = 0.1 + z * 1.05
    spread = SCREEN_W * 0.55 * (0.12 + z * 0.9)
    screen_x = SCREEN_W / 2 + x * spread
    screen_y = HORIZON_Y + z * (SCREEN_H - HORIZON_Y)
    return screen_x, screen_y, scale


def draw_background(screen):
    for y in range(HORIZON_Y):
        color = lerp_color(SKY_TOP, SKY_HORIZON, y / HORIZON_Y)
        pygame.draw.line(screen, color, (0, y), (SCREEN_W, y))

    sun_pos = (int(SCREEN_W * 0.78), int(HORIZON_Y * 0.32))
    for r, color in ((54, lerp_color(SUN_COLOR, SKY_HORIZON, 0.55)), (38, SUN_COLOR)):
        pygame.draw.circle(screen, color, sun_pos, r)

    hill_y = HORIZON_Y - int(SCREEN_H * 0.05)
    far_hills = [(0, HORIZON_Y)]
    for i in range(9):
        far_hills.append((SCREEN_W * i / 8, hill_y - 18 * math.sin(i * 1.3 + 0.5)))
    far_hills.append((SCREEN_W, HORIZON_Y))
    pygame.draw.polygon(screen, HILL_FAR, far_hills)

    near_hill_y = HORIZON_Y - int(SCREEN_H * 0.02)
    near_hills = [(0, HORIZON_Y)]
    for i in range(7):
        near_hills.append((SCREEN_W * i / 6, near_hill_y - 12 * math.sin(i * 2.1 + 2.0)))
    near_hills.append((SCREEN_W, HORIZON_Y))
    pygame.draw.polygon(screen, HILL_NEAR, near_hills)

    for y in range(HORIZON_Y, SCREEN_H):
        t = (y - HORIZON_Y) / (SCREEN_H - HORIZON_Y)
        pygame.draw.line(screen, lerp_color(GROUND_FAR, GROUND_NEAR, t), (0, y), (SCREEN_W, y))

    for i in range(1, 9):
        _, sy, _ = project(0, i / 9)
        pygame.draw.line(screen, GRID_COLOR, (0, sy), (SCREEN_W, sy), 1)
    for x in (-1.2, -0.8, -0.4, 0.0, 0.4, 0.8, 1.2):
        sx0, sy0, _ = project(x, 0.0)
        sx1, sy1, _ = project(x, 1.0)
        pygame.draw.line(screen, GRID_COLOR, (sx0, sy0), (sx1, sy1), 1)

    for x, z in ((-1.1, 0.28), (1.15, 0.22), (-0.75, 0.55), (0.95, 0.62)):
        draw_tree(screen, x, z)


def draw_tree(screen, x, z):
    sx, sy, scale = project(x, z)
    trunk_h = int(30 * scale)
    trunk_w = max(2, int(6 * scale))
    pygame.draw.rect(screen, TREE_TRUNK, (sx - trunk_w / 2, sy - trunk_h, trunk_w, trunk_h))
    leaf_r = max(3, int(22 * scale))
    pygame.draw.circle(screen, TREE_LEAVES, (int(sx), int(sy - trunk_h - leaf_r * 0.6)), leaf_r)


def draw_critter(screen, x, z, token):
    sx, sy, scale = project(x, z)
    body_r = int(24 * scale)
    if body_r < 2:
        return

    shadow_w, shadow_h = body_r * 1.7, body_r * 0.5
    pygame.draw.ellipse(screen, SHADOW_COLOR,
                         (sx - shadow_w / 2, sy + body_r * 0.55, shadow_w, shadow_h))

    pants_w, pants_h = body_r * 1.5, body_r * 0.95
    pygame.draw.ellipse(screen, PANTS_COLOR,
                         (sx - pants_w / 2, sy - body_r * 0.15, pants_w, pants_h))

    body_center = (sx, sy - body_r * 0.55)
    pygame.draw.circle(screen, BODY_COLOR, body_center, body_r)
    if token != 0:
        pygame.draw.circle(screen, TOKEN_COLORS[token], body_center,
                            int(body_r * 1.12), width=max(1, int(body_r * 0.12)))

    tuft_r = max(2, int(body_r * 0.36))
    for dx in (-0.42, 0.42):
        pygame.draw.circle(screen, HAIR_COLOR,
                            (int(sx + dx * body_r), int(sy - body_r * 1.05)), tuft_r)

    eye_r = max(1, int(body_r * 0.26))
    eye_y = sy - body_r * 0.58
    for dx in (-0.34, 0.34):
        ex = sx + dx * body_r
        pygame.draw.circle(screen, EYE_WHITE, (int(ex), int(eye_y)), eye_r)
        pygame.draw.circle(screen, EYE_PUPIL, (int(ex), int(eye_y + eye_r * 0.2)),
                            max(1, int(eye_r * 0.45)))

    mouth_w, mouth_h = max(1, int(body_r * 0.22)), max(1, int(body_r * 0.16))
    pygame.draw.ellipse(screen, MOUTH_COLOR,
                         (sx - mouth_w / 2, sy - body_r * 0.22, mouth_w, mouth_h))


def draw_predator(screen, x, z):
    sx, sy, scale = project(x, z)
    r = int(20 * scale)
    if r < 2:
        return
    pygame.draw.ellipse(screen, SHADOW_COLOR, (sx - r * 0.9, sy + r * 0.5, r * 1.8, r * 0.45))
    pygame.draw.circle(screen, PREDATOR_COLOR, (int(sx), int(sy - r * 0.4)), r)
    eye_r = max(1, int(r * 0.22))
    for dx in (-0.35, 0.35):
        ex, ey = sx + dx * r, sy - r * 0.55
        pygame.draw.circle(screen, (255, 230, 120), (int(ex), int(ey)), eye_r)
        pygame.draw.circle(screen, (20, 10, 10), (int(ex), int(ey)), max(1, int(eye_r * 0.5)))


def draw_food(screen, x, z):
    sx, sy, scale = project(x, z)
    r = max(1, int(6 * scale))
    pygame.draw.circle(screen, FOOD_COLOR, (int(sx), int(sy)), r)


def egg_rect(x, z, pulse=0.0):
    sx, sy, scale = project(x, z)
    egg_w = 30 * scale * (1.0 + pulse * 0.15)
    egg_h = 40 * scale * (1.0 + pulse * 0.15)
    rect = pygame.Rect(0, 0, egg_w, egg_h)
    rect.center = (sx, sy)
    return rect


def egg_contains(mx, my, x, z):
    rect = egg_rect(x, z)
    if rect.width < 2:
        return False
    dx = (mx - rect.centerx) / (rect.width / 2 + 6)
    dy = (my - rect.centery) / (rect.height / 2 + 6)
    return dx * dx + dy * dy <= 1.0


def draw_egg(screen, x, z, cracks, wobble, pulse):
    rect = egg_rect(x, z, pulse)
    if rect.width < 2:
        return

    shadow_w, shadow_h = rect.width * 1.3, rect.height * 0.35
    pygame.draw.ellipse(screen, SHADOW_COLOR,
                         (rect.centerx - shadow_w / 2, rect.bottom - shadow_h * 0.6, shadow_w, shadow_h))

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


def draw_population(screen, world, pan_x):
    entities = []
    for c in world.creatures:
        if c.alive:
            x, z = world_to_stage(c.pos)
            entities.append((z, "creature", x, c.token))
    for p in world.predators:
        x, z = world_to_stage(p.pos)
        entities.append((z, "predator", x, None))
    entities.sort(key=lambda e: e[0])

    for fx, fy in world.food:
        x, z = world_to_stage((fx, fy))
        draw_food(screen, x - pan_x, z)
    for z, kind, x, token in entities:
        if kind == "creature":
            draw_critter(screen, x - pan_x, z, token)
        else:
            draw_predator(screen, x - pan_x, z)


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
                 hatched, egg_cracks):
    if hatched:
        status = "PAUSED" if paused else f"x{speed}"
        top_line = f"pop {world.population()}   {status}"
    else:
        top_line = f"Left-click the egg to crack it open ({egg_cracks}/{EGG_CLICKS_NEEDED})"
    lines = [
        top_line,
        f"[A] mic: {sensor_label(sensors.mic_enabled, sensors.mic_available)}   "
        f"[C] camera: {sensor_label(sensors.camera_enabled, sensors.camera_available)}   "
        f"threshold: {threshold:.2f} ([ / ])",
    ]
    for i, text in enumerate(lines):
        screen.blit(font.render(text, True, (255, 255, 255)), (10, 10 + i * 22))

    meter_y = 10 + len(lines) * 22 + 4
    draw_meter(screen, 10, meter_y, 140, 10, sensors.mic_level, (120, 200, 255))
    draw_meter(screen, 160, meter_y, 140, 10, sensors.motion_level, (255, 180, 120))

    hint = font.render("LEFT/RIGHT pan   SPACE pause   UP/DOWN speed   R reset   ESC quit",
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
    creature. It doesn't step until the egg cracks open, so nothing else
    in the world (predators included) can do anything to it first."""
    return World(init_pop=1, predator_count=6)


def main():
    pygame.init()
    pygame.display.set_caption("Thronglets - pseudo-3D view")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    world = new_egg_world()
    sensors = SensorHub()

    pan_x = 0.0
    paused = False
    speed = 1
    tick_accumulator = 0.0
    threshold = DEFAULT_ALERT_THRESHOLD
    alert = AlertState()
    egg = EggState()
    hatch_flash = 0.0
    t = 0.0
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
                    speed = min(200, speed + (1 if speed < 10 else 10))
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed - (1 if speed <= 10 else 10))
                elif event.key == pygame.K_r:
                    world = new_egg_world()
                    alert = AlertState()
                    egg = EggState()
                    hatch_flash = 0.0
                elif event.key == pygame.K_a:
                    sensors.toggle_mic()
                elif event.key == pygame.K_c:
                    sensors.toggle_camera()
                elif event.key == pygame.K_LEFTBRACKET:
                    threshold = max(0.05, threshold - 0.05)
                elif event.key == pygame.K_RIGHTBRACKET:
                    threshold = min(1.0, threshold + 0.05)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if egg.register_click(event.pos[0], event.pos[1]):
                    hatch_flash = 0.4

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            pan_x -= 0.8 * dt
        if keys[pygame.K_RIGHT]:
            pan_x += 0.8 * dt

        egg.update(dt)
        hatch_flash = max(0.0, hatch_flash - dt)

        if egg.hatched and not paused:
            tick_accumulator += dt
            tick_interval = 1.0 / speed
            while tick_accumulator >= tick_interval:
                world.step()
                tick_accumulator -= tick_interval
        else:
            tick_accumulator = 0.0

        if egg.hatched:
            alert.update(world, sensors, threshold, dt)

        draw_background(screen)
        if egg.hatched:
            draw_population(screen, world, pan_x)
        else:
            wobble = math.sin(t * 14.0) * (2 + egg.cracks * 1.5)
            draw_egg(screen, EGG_STAGE_X - pan_x, EGG_STAGE_Z, egg.cracks, wobble, egg.pulse)
        draw_status(screen, font, world, paused, speed, sensors, threshold, alert.flash,
                    egg.hatched, egg.cracks)
        if hatch_flash > 0:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, int(200 * min(1.0, hatch_flash / 0.4))))
            screen.blit(overlay, (0, 0))

        pygame.display.flip()

    sensors.stop()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
