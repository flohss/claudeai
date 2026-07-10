"""Terminal (curses) renderer for Thronglets.

No GUI/X11/SDL needed - handy on Termux or over plain SSH, where pygame is
painful to install. Only the Python standard library plus numpy are needed.

Controls: space=pause  f=drop food  r=reset  +/-=speed  q=quit
"""

import curses
import time

import numpy as np

from simulation import FOOD, HEIGHT, IDLE, MATE, World, WIDTH

TOKEN_COLOR_PAIR = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
STATE_LABELS = {IDLE: "idle", FOOD: "food-call", MATE: "mate-call"}
HUD_H = 4


def setup_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_BLUE, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_MAGENTA, -1)
    curses.init_pair(5, curses.COLOR_CYAN, -1)
    curses.init_pair(6, curses.COLOR_GREEN, -1)   # food
    curses.init_pair(7, curses.COLOR_WHITE, -1)   # hud / body


def _safe_addstr(stdscr, y, x, text, attr):
    rows, cols = stdscr.getmaxyx()
    if 0 <= y < rows and 0 <= x < cols:
        try:
            stdscr.addstr(y, x, text[: cols - x], attr)
        except curses.error:
            pass


def draw(stdscr, world, paused, speed):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()
    field_h = max(1, rows - HUD_H)
    field_w = max(1, cols)
    sx, sy = (field_w - 1) / WIDTH, (field_h - 1) / HEIGHT

    pop = world.population()
    status = "PAUSED" if paused else f"x{speed}"
    header = f"tick {world.tick}  pop {pop}  births {world.births}  deaths {world.deaths}  {status}"
    _safe_addstr(stdscr, 0, 0, header, curses.color_pair(7) | curses.A_BOLD)

    x = 0
    vocab = world.vocabulary()
    for state in (FOOD, MATE, IDLE):
        token, agreement = vocab[state]
        pair = TOKEN_COLOR_PAIR.get(token, 7)
        _safe_addstr(stdscr, 1, x, "##", curses.color_pair(pair) | curses.A_BOLD)
        label = f" {STATE_LABELS[state]} {agreement * 100:.0f}%   "
        _safe_addstr(stdscr, 1, x + 2, label, curses.color_pair(7))
        x += 2 + len(label)

    _safe_addstr(stdscr, 2, 0, "@ = signale   o = silencieuse   . = nourriture",
                 curses.color_pair(7) | curses.A_DIM)
    _safe_addstr(stdscr, 3, 0, "space=pause  f=food  r=reset  +/-=speed  q=quit",
                 curses.color_pair(7) | curses.A_DIM)

    for fx, fy in world.food:
        y, x = HUD_H + int(fy * sy), int(fx * sx)
        _safe_addstr(stdscr, y, x, ".", curses.color_pair(6))

    for c in world.creatures:
        if not c.alive:
            continue
        y, x = HUD_H + int(c.pos[1] * sy), int(c.pos[0] * sx)
        pair = TOKEN_COLOR_PAIR.get(c.token, 7)
        ch = "@" if c.token else "o"
        _safe_addstr(stdscr, y, x, ch, curses.color_pair(pair) | curses.A_BOLD)

    if pop == 0:
        _safe_addstr(stdscr, HUD_H + field_h // 2, max(0, cols // 2 - 12),
                     "Extinct. Press r to reset.", curses.color_pair(1) | curses.A_BOLD)

    stdscr.refresh()


def run(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    setup_colors()

    world = World(init_pop=70)
    paused = False
    speed = 1
    frame_time = 1 / 20

    while True:
        key = stdscr.getch()
        if key in (ord("q"), 27):
            break
        elif key == ord(" "):
            paused = not paused
        elif key == ord("r"):
            world = World(init_pop=70)
        elif key in (ord("+"), ord("=")):
            speed = min(10, speed + 1)
        elif key in (ord("-"), ord("_")):
            speed = max(1, speed - 1)
        elif key == ord("f"):
            center = world.rng.uniform([10, 10], [WIDTH - 10, HEIGHT - 10])
            for _ in range(6):
                world.food.append(np.clip(center + world.rng.normal(0, 5, 2), [0, 0], [WIDTH, HEIGHT]))

        if not paused:
            for _ in range(speed):
                world.step()

        draw(stdscr, world, paused, speed)
        time.sleep(frame_time)


def main():
    curses.wrapper(run)


if __name__ == "__main__":
    main()
