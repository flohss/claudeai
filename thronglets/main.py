"""Watch a Thronglets world live in a window.

You pick automatic or manual mode once, at startup - not something you
toggle mid-run.

Controls:
  SPACE        pause / resume
  UP / DOWN    simulation speed (ticks per rendered frame)
  R            reset to a fresh world
  LEFT CLICK   place food (auto mode) or whatever's selected (manual mode)
  P            toggle what manual clicks place (food / predator)
  [ / ]        remove/add a predator right now
  H            in-game notice/help screen
  ESC          quit
"""

import argparse
import sys

import pygame

from simulation import DANGER, FOOD, HEIGHT, IDLE, MATE, MAX_POPULATION, World, WIDTH, load_seed_genome

DEFAULT_INIT_POP = 70
DEFAULT_LANGUAGE_FILE = "language_model.json"

SCALE = 5
HUD_H = 200
SCREEN_W, SCREEN_H = int(WIDTH * SCALE), int(HEIGHT * SCALE) + HUD_H

BG = (18, 22, 16)
GROUND = (30, 38, 24)
HUD_BG = (10, 12, 9)
TEXT_COLOR = (220, 220, 210)
FOOD_COLOR = (110, 220, 90)
BODY_COLOR = (222, 208, 150)
PREDATOR_COLOR = (220, 30, 30)
TOKEN_COLORS = [
    (120, 120, 120),  # 0: silence, not drawn as a ring
    (235, 70, 70),
    (70, 140, 235),
    (245, 200, 60),
    (200, 90, 230),
    (70, 225, 210),
]
STATE_LABELS = {IDLE: "idle-chatter", FOOD: "food-call", MATE: "mate-call", DANGER: "alarm-call"}

HELP_LINES = [
    ("Thronglets - notice", True),
    ("", False),
    ("Each creature is born with a genome deciding which color it shows for", False),
    ("its current state, and how it reacts to colors it hears from others.", False),
    ("Nobody programs what a color means - a shared language can emerge", False),
    ("through natural selection, or it might not.", False),
    ("", False),
    ("The 4 states, in priority order:", True),
    ("  1. danger     a predator was spotted -> flee immediately", False),
    ("  2. food-call  food is visible nearby", False),
    ("  3. mate-call  ready to mate, and a ready partner is nearby", False),
    ("  4. idle       nothing special (by far the most common state)", False),
    ("", False),
    ("Living, mating, dying:", True),
    ("  Energy drains constantly; eating restores it. Emitting a color", False),
    ("  (other than silence) costs a bit of extra energy. Enough energy", False),
    ("  and age, plus a matching partner nearby: a child is born. A", False),
    ("  predator that catches a creature kills it outright.", False),
    ("", False),
    ("Reading the vocabulary rows at the top:", True),
    ("  For each state, the share of the population using each color.", False),
    ("  It starts near chance (~17%) and climbs if a token wins out.", False),
    ("  A '..' swatch means silence, not a missing color.", False),
    ("", False),
    ("Worth knowing:", True),
    ("  Two states can end up sharing the same color purely by chance", False),
    ("  (e.g. idle and alarm-call) - nothing prevents it or guarantees", False),
    ("  it resolves. Signaling costs energy, so silence is a real", False),
    ("  strategy, not a default.", False),
]


def show_help(screen, font):
    line_h = 24
    top = 20
    page_size = max(1, (SCREEN_H - top - 50) // line_h)
    for start in range(0, len(HELP_LINES), page_size):
        page = HELP_LINES[start:start + page_size]
        more = start + page_size < len(HELP_LINES)
        footer = "-- space for more --" if more else "-- press any key to resume --"
        waiting = True
        while waiting:
            screen.fill(BG)
            for i, (line, bold) in enumerate(page):
                color = TEXT_COLOR if not bold else (255, 255, 255)
                screen.blit(font.render(line, True, color), (20, top + i * line_h))
            screen.blit(font.render(footer, True, (150, 155, 145)), (20, top + len(page) * line_h + 14))
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    waiting = False


def draw(screen, font, world, paused, speed, mode, placing, trained=False):
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

    for p in world.predators:
        x, y = int(p.pos[0] * SCALE), int(p.pos[1] * SCALE) + HUD_H
        pygame.draw.circle(screen, PREDATOR_COLOR, (x, y), 6)

    draw_hud(screen, font, world, paused, speed, mode, placing, trained)


def draw_vocab_row(screen, font, y, label, pairs):
    x = 10
    lbl = font.render(f"{label}:", True, TEXT_COLOR)
    screen.blit(lbl, (x, y))
    x += lbl.get_width() + 10
    for token, frac in pairs:
        if token == 0:
            pygame.draw.circle(screen, (110, 110, 110), (x + 6, y + 8), 6, width=1)
        else:
            pygame.draw.circle(screen, TOKEN_COLORS[token], (x + 6, y + 8), 6)
        txt = font.render(f"{frac * 100:3.0f}%", True, TEXT_COLOR)
        screen.blit(txt, (x + 16, y))
        x += 16 + txt.get_width() + 14


def draw_hud(screen, font, world, paused, speed, mode, placing, trained=False):
    pygame.draw.rect(screen, HUD_BG, (0, 0, SCREEN_W, HUD_H))
    pop = world.population()
    status = "PAUSED" if paused else f"x{speed}"
    tag = "   [trained vocabulary]" if trained else ""
    header = (f"tick {world.tick:>6}   pop {pop:>4}   births {world.births:>5}   "
              f"deaths {world.deaths:>5}   {status}   (space=pause  up/down=speed  r=reset  h=help){tag}")
    screen.blit(font.render(header, True, TEXT_COLOR), (10, 8))

    if mode == "manual":
        settings = f"mode: manual   click places: {placing} (P)"
    else:
        settings = f"mode: automatic   predators: {len(world.predators)} ([ / ] act immediately)"
    screen.blit(font.render(settings, True, TEXT_COLOR), (10, 28))

    screen.blit(font.render("vocabulary — every color in use per state, population share:",
                             True, TEXT_COLOR), (10, 48))

    y = 70
    breakdown = world.vocabulary_breakdown()
    for state in (DANGER, FOOD, MATE, IDLE):
        draw_vocab_row(screen, font, y, STATE_LABELS[state], breakdown[state])
        y += 22

    legend_y = y
    lx = 10
    pygame.draw.circle(screen, BODY_COLOR, (lx + 6, legend_y + 8), 4)
    pygame.draw.circle(screen, (150, 150, 150), (lx + 6, legend_y + 8), 7, width=2)
    txt = font.render("creature (ring = its current signal)", True, TEXT_COLOR)
    screen.blit(txt, (lx + 18, legend_y))
    lx += 18 + txt.get_width() + 20

    pygame.draw.circle(screen, FOOD_COLOR, (lx + 6, legend_y + 8), 3)
    txt = font.render("food", True, TEXT_COLOR)
    screen.blit(txt, (lx + 18, legend_y))
    lx += 18 + txt.get_width() + 20

    pygame.draw.circle(screen, PREDATOR_COLOR, (lx + 6, legend_y + 8), 6)
    txt = font.render("predator", True, TEXT_COLOR)
    screen.blit(txt, (lx + 18, legend_y))

    if pop == 0:
        msg = font.render("Extinct. Press R to start a new world.", True, (235, 90, 90))
        screen.blit(msg, (10, legend_y + 22))


def _new_world(mode, predator_count, init_pop=DEFAULT_INIT_POP, seed_genome=None):
    if mode == "manual":
        return World(init_pop=init_pop, manual_food=True, manual_predators=True, seed_genome=seed_genome)
    return World(init_pop=init_pop, predator_count=predator_count, seed_genome=seed_genome)


def choose_mode(screen, font):
    lines = [
        "Thronglets",
        "",
        "Choose the starting mode:",
        "  A = automatic - food and predators spawn on their own",
        "  M = manual - you place everything yourself, nothing spawns alone",
        "",
        "Press A or M to start.",
    ]
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:
                    return "auto"
                if event.key == pygame.K_m:
                    return "manual"


def choose_population(screen, font):
    text = ""
    while True:
        screen.fill(BG)
        lines = [
            "Thronglets",
            "",
            f"How many creatures to start with? (1-{MAX_POPULATION}, default {DEFAULT_INIT_POP})",
            "",
            f"> {text}",
            "",
            "Press ENTER to confirm.",
        ]
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if not text:
                        return DEFAULT_INIT_POP
                    return max(1, min(MAX_POPULATION, int(text)))
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                elif event.unicode.isdigit() and len(text) < 3:
                    text += event.unicode


def choose_ai(screen, font):
    lines = [
        "Thronglets",
        "",
        "Activer le langage pre-entraine par IA ?",
        f"  (relit '{DEFAULT_LANGUAGE_FILE}', genere par train_language.py)",
        "",
        "  O = oui - les creatures parlent deja un langage sans confusion",
        "  N = non - le langage doit emerger tout seul en jouant (defaut)",
        "",
        "Press O or N to start.",
    ]
    while True:
        screen.fill(BG)
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_COLOR), (20, 20 + i * 26))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_o:
                    return True
                if event.key == pygame.K_n:
                    return False


def flash_message(screen, font, text):
    waiting = True
    while waiting:
        screen.fill(BG)
        screen.blit(font.render(text, True, (235, 90, 90)), (20, 20))
        screen.blit(font.render("-- press any key to continue --", True, TEXT_COLOR), (20, 60))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                waiting = False


def main():
    parser = argparse.ArgumentParser(description="Thronglets - pygame renderer")
    parser.add_argument("--language", type=str, default=None,
                         help="seed the population with a train_language.py --export vocabulary "
                              "instead of starting from scratch")
    args = parser.parse_args()

    pygame.init()
    pygame.display.set_caption("Thronglets - a tiny language is being born")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    mode = choose_mode(screen, font)
    init_pop = choose_population(screen, font)

    if args.language:
        seed_genome = load_seed_genome(args.language)
    elif choose_ai(screen, font):
        try:
            seed_genome = load_seed_genome(DEFAULT_LANGUAGE_FILE)
        except OSError:
            seed_genome = None
            flash_message(screen, font, f"'{DEFAULT_LANGUAGE_FILE}' introuvable - lancement sans IA.")
    else:
        seed_genome = None

    placing = "food"

    world = _new_world(mode, 6, init_pop, seed_genome)
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
                    world = _new_world(mode, len(world.predators), init_pop, seed_genome)
                elif event.key == pygame.K_UP:
                    speed = min(200, speed + (1 if speed < 10 else 10))
                elif event.key == pygame.K_DOWN:
                    speed = max(1, speed - (1 if speed <= 10 else 10))
                elif event.key == pygame.K_p:
                    placing = "predator" if placing == "food" else "food"
                elif event.key == pygame.K_LEFTBRACKET:
                    world.remove_predator()
                elif event.key == pygame.K_RIGHTBRACKET:
                    world.add_random_predator()
                elif event.key == pygame.K_h:
                    show_help(screen, font)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if my > HUD_H:
                    wx, wy = mx / SCALE, (my - HUD_H) / SCALE
                    if mode == "manual" and placing == "predator":
                        world.add_predator(wx, wy)
                    else:
                        world.add_food(wx, wy)

        if not paused:
            for _ in range(speed):
                world.step()

        draw(screen, font, world, paused, speed, mode, placing, trained=seed_genome is not None)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
