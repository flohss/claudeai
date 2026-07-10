"""Watch a Thronglets world live in a window.

Controls:
  SPACE        pause / resume
  UP / DOWN    simulation speed (ticks per rendered frame)
  R            reset to a fresh world
  LEFT CLICK   drop a food patch where you click
  ESC          quit
"""

import sys

import numpy as np
import pygame

from simulation import FOOD, HEIGHT, IDLE, MATE, World, WIDTH

SCALE = 5
HUD_H = 90
SCREEN_W, SCREEN_H = int(WIDTH * SCALE), int(HEIGHT * SCALE) + HUD_H

BG = (18, 22, 16)
GROUND = (30, 38, 24)
HUD_BG = (10, 12, 9)
TEXT_COLOR = (220, 220, 210)
FOOD_COLOR = (110, 220, 90)
BODY_COLOR = (222, 208, 150)
TOKEN_COLORS = [
    (120, 120, 120),  # 0: silence, not drawn as a ring
    (235, 70, 70),
    (70, 140, 235),
    (245, 200, 60),
    (200, 90, 230),
    (70, 225, 210),
]
STATE_LABELS = {IDLE: "idle-chatter", FOOD: "food-call", MATE: "mate-call"}


def draw(screen, font, world, paused, speed):
    screen.fill(BG)
    pygame.draw.rect(screen, GROUND, (0, HUD_H, SCREEN_W, SCREEN_H - HUD_H))

    for fx, fy in world.food:
        pygame.draw.circle(screen, FOOD_COLOR, (int(fx * SCALE), int(fy * SCALE) + HUD_H), 3)

    for c in world.creatures:
        if not c.alive:
            continue
        x, y = int(c.pos[0] * SCALE), int(c.pos[1] * SCALE) + HUD_H
        pygame.draw.circle(screen, BODY_COLOR, (x, y), 4)
        if c.token != 0:
            pygame.draw.circle(screen, TOKEN_COLORS[c.token], (x, y), 7, width=2)

    draw_hud(screen, font, world, paused, speed)


def draw_hud(screen, font, world, paused, speed):
    pygame.draw.rect(screen, HUD_BG, (0, 0, SCREEN_W, HUD_H))
    pop = world.population()
    status = "PAUSED" if paused else f"x{speed}"
    header = (f"tick {world.tick:>6}   pop {pop:>4}   births {world.births:>5}   "
              f"deaths {world.deaths:>5}   {status}   (space=pause  up/down=speed  r=reset  click=food)")
    screen.blit(font.render(header, True, TEXT_COLOR), (10, 8))
    screen.blit(font.render("vocabulary — state to dominant token, population agreement:",
                             True, TEXT_COLOR), (10, 28))

    x, y = 10, 50
    vocab = world.vocabulary()
    for state, label in STATE_LABELS.items():
        token, agreement = vocab[state]
        color = TOKEN_COLORS[token]
        pygame.draw.circle(screen, color, (x + 6, y + 8), 6)
        txt = font.render(f"{label}: {agreement * 100:4.0f}% agree", True, TEXT_COLOR)
        screen.blit(txt, (x + 18, y))
        x += 220

    if pop == 0:
        msg = font.render("Extinct. Press R to start a new world.", True, (235, 90, 90))
        screen.blit(msg, (10, y + 22))


def main():
    pygame.init()
    pygame.display.set_caption("Thronglets - a tiny language is being born")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    world = World(init_pop=70)
    paused = False
    speed = 1
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    world = World(init_pop=70)
                elif event.key == pygame.K_UP:
                    speed = min(10, speed + 1)
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed - 1)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if my > HUD_H:
                    wx, wy = mx / SCALE, (my - HUD_H) / SCALE
                    for _ in range(5):
                        jitter = world.rng.normal(0, 4, 2)
                        world.food.append(np.clip(np.array([wx, wy]) + jitter, [0, 0], [WIDTH, HEIGHT]))

        if not paused:
            for _ in range(speed):
                world.step()

        draw(screen, font, world, paused, speed)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
