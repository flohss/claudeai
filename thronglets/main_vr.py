"""A pseudo-3D visual demo of the Thronglets' look - round, big-eyed
creatures with red hair-tufts and blue overalls, wandering over a simple
perspective landscape (sky, sun, hills, grass fading to a horizon).

This is NOT true VR: no headset, no stereoscopic/OpenXR/WebXR output,
nothing this environment could test even if it existed. It's the classic
"pseudo-3D driving game" trick - a ground plane projected onto a normal 2D
screen so things shrink and converge toward a horizon line - viewed on a
regular monitor. It's also a standalone demo, independent of
simulation.py: no language evolution here, the creatures are just cosmetic
wanderers, not an evolving population.

The creature design is an original, simplified, geometric interpretation
of the look (round yellow body, two hair-tufts, big eyes, blue lower
half) - not a reproduction of the show's or the licensed game's actual
pixel art.

Controls:
  LEFT / RIGHT   pan the camera
  R              scatter a fresh set of creatures
  ESC            quit
"""

import argparse
import math
import random
import sys

import pygame

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

DEFAULT_N_CREATURES = 45


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def shift_color(color, delta):
    return tuple(max(0, min(255, c + delta)) for c in color)


class Critter:
    """A purely decorative wanderer - position and a little idle motion,
    no genome, no signaling, no relation to simulation.py's World."""

    def __init__(self, rng):
        self.rng = rng
        self.x = rng.uniform(-1.3, 1.3)
        self.z = rng.uniform(0.03, 1.0)
        self.phase = rng.uniform(0, math.tau)
        self.drift_speed = rng.uniform(0.15, 0.35)
        self.approach_speed = rng.uniform(0.01, 0.05)
        self.tint = rng.randint(-14, 14)

    def update(self, dt, t):
        self.x += math.sin(t * self.drift_speed + self.phase) * 0.15 * dt
        self.z += self.approach_speed * dt
        if self.z > 1.05:
            self.z = 0.03
            self.x = self.rng.uniform(-1.3, 1.3)


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
    for r, alpha_color in ((54, lerp_color(SUN_COLOR, SKY_HORIZON, 0.55)), (38, SUN_COLOR)):
        pygame.draw.circle(screen, alpha_color, sun_pos, r)

    hill_y = HORIZON_Y - int(SCREEN_H * 0.05)
    far_hills = [(0, HORIZON_Y)]
    for i in range(9):
        fx = SCREEN_W * i / 8
        fy = hill_y - 18 * math.sin(i * 1.3 + 0.5)
        far_hills.append((fx, fy))
    far_hills.append((SCREEN_W, HORIZON_Y))
    pygame.draw.polygon(screen, HILL_FAR, far_hills)

    near_hill_y = HORIZON_Y - int(SCREEN_H * 0.02)
    near_hills = [(0, HORIZON_Y)]
    for i in range(7):
        fx = SCREEN_W * i / 6
        fy = near_hill_y - 12 * math.sin(i * 2.1 + 2.0)
        near_hills.append((fx, fy))
    near_hills.append((SCREEN_W, HORIZON_Y))
    pygame.draw.polygon(screen, HILL_NEAR, near_hills)

    for y in range(HORIZON_Y, SCREEN_H):
        t = (y - HORIZON_Y) / (SCREEN_H - HORIZON_Y)
        color = lerp_color(GROUND_FAR, GROUND_NEAR, t)
        pygame.draw.line(screen, color, (0, y), (SCREEN_W, y))

    # A faint perspective grid reinforces the ground-plane illusion: rows
    # get farther apart near the camera, columns converge on the horizon.
    for i in range(1, 9):
        z = i / 9
        _, sy, _ = project(0, z)
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


def draw_critter(screen, x, z, tint=0):
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
    pygame.draw.circle(screen, shift_color(BODY_COLOR, tint), body_center, body_r)

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


def scatter(rng, n):
    return [Critter(rng) for _ in range(n)]


def main():
    parser = argparse.ArgumentParser(description="Thronglets - pseudo-3D visual demo")
    parser.add_argument("--creatures", type=int, default=DEFAULT_N_CREATURES,
                         help="how many creatures to scatter across the landscape")
    args = parser.parse_args()

    pygame.init()
    pygame.display.set_caption("Thronglets - pseudo-3D demo")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    rng = random.Random()
    critters = scatter(rng, args.creatures)
    camera_x = 0.0
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
                elif event.key == pygame.K_r:
                    critters = scatter(rng, args.creatures)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            camera_x -= 0.8 * dt
        if keys[pygame.K_RIGHT]:
            camera_x += 0.8 * dt

        for c in critters:
            c.update(dt, t)

        draw_background(screen)
        for c in sorted(critters, key=lambda c: c.z):
            draw_critter(screen, c.x - camera_x, c.z, tint=c.tint)

        hint = font.render("LEFT/RIGHT pan   R scatter   ESC quit", True, (255, 255, 255))
        screen.blit(hint, (10, 10))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
