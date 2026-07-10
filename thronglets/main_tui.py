"""Terminal (curses) renderer for Thronglets.

No GUI/X11/SDL needed - handy on Termux or over plain SSH, where pygame is
painful to install. Only the Python standard library plus numpy are needed.

Controls: space=pause  f=drop food (auto mode only)  r=reset  +/-=speed  q=quit
  m=toggle auto/manual  p=toggle food/predator (manual placement)
  [ / ]=remove/add a predator right now (also sets the count used on reset)
  arrow keys=move cursor, enter=place (manual mode)
"""

import curses
import time

from simulation import DANGER, FOOD, HEIGHT, IDLE, MATE, World, WIDTH

TOKEN_COLOR_PAIR = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
STATE_LABELS = {IDLE: "idle", FOOD: "food-call", MATE: "mate-call", DANGER: "alarm-call"}
HUD_H = 9
CURSOR_STEP = 4.0
ENTER_KEYS = (10, 13, curses.KEY_ENTER)


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


def _draw_vocab_row(stdscr, y, label, pairs):
    x = 0
    _safe_addstr(stdscr, y, x, f"{label}:", curses.color_pair(7) | curses.A_BOLD)
    x += len(label) + 2
    for token, frac in pairs:
        if token == 0:
            _safe_addstr(stdscr, y, x, "..", curses.color_pair(7) | curses.A_DIM)
        else:
            _safe_addstr(stdscr, y, x, "##", curses.color_pair(TOKEN_COLOR_PAIR[token]) | curses.A_BOLD)
        seg = f"{frac * 100:3.0f}% "
        _safe_addstr(stdscr, y, x + 2, seg, curses.color_pair(7))
        x += 2 + len(seg)


def draw(stdscr, world, paused, speed, mode, placing, cursor):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()
    field_h = max(1, rows - HUD_H)
    field_w = max(1, cols)
    sx, sy = (field_w - 1) / WIDTH, (field_h - 1) / HEIGHT

    pop = world.population()
    status = "PAUSED" if paused else f"x{speed}"
    header = f"tick {world.tick}  pop {pop}  births {world.births}  deaths {world.deaths}  {status}"
    _safe_addstr(stdscr, 0, 0, header, curses.color_pair(7) | curses.A_BOLD)

    if mode == "manual":
        settings = f"mode: manuel (m)   pose: {placing} (p)   fleches+entree pour placer"
    else:
        settings = f"mode: auto (m)   predateurs: {len(world.predators)} ([ ] agit tout de suite)"
    _safe_addstr(stdscr, 1, 0, settings, curses.color_pair(7) | curses.A_DIM)

    breakdown = world.vocabulary_breakdown()
    for row, state in enumerate((DANGER, FOOD, MATE, IDLE), start=2):
        _draw_vocab_row(stdscr, row, STATE_LABELS[state], breakdown[state])

    _safe_addstr(stdscr, HUD_H - 3, 0, "o colore = signale   o blanc = silencieuse   . = nourriture   X = predateur",
                 curses.color_pair(7) | curses.A_DIM)
    food_hint = "f=food" if mode == "auto" else "f=food (auto mode only)"
    _safe_addstr(stdscr, HUD_H - 2, 0, f"space=pause  {food_hint}  r=reset  +/-=speed  q=quit",
                 curses.color_pair(7) | curses.A_DIM)
    _safe_addstr(stdscr, HUD_H - 1, 0, "m=mode  p=placer  [ ]=nb predateurs  fleches/entree=placer",
                 curses.color_pair(7) | curses.A_DIM)

    for fx, fy in world.food:
        y, x = HUD_H + int(fy * sy), int(fx * sx)
        _safe_addstr(stdscr, y, x, ".", curses.color_pair(6))

    for c in world.creatures:
        if not c.alive:
            continue
        y, x = HUD_H + int(c.pos[1] * sy), int(c.pos[0] * sx)
        pair = TOKEN_COLOR_PAIR.get(c.token, 7)
        _safe_addstr(stdscr, y, x, "o", curses.color_pair(pair) | curses.A_BOLD)

    for p in world.predators:
        y, x = HUD_H + int(p.pos[1] * sy), int(p.pos[0] * sx)
        _safe_addstr(stdscr, y, x, "X", curses.color_pair(1) | curses.A_BOLD)

    if mode == "manual":
        cy, cx = HUD_H + int(cursor[1] * sy), int(cursor[0] * sx)
        pair = 6 if placing == "food" else 1
        _safe_addstr(stdscr, cy, cx, "+", curses.color_pair(pair) | curses.A_BOLD | curses.A_REVERSE)

    if pop == 0:
        _safe_addstr(stdscr, HUD_H + field_h // 2, max(0, cols // 2 - 12),
                     "Extinct. Press r to reset.", curses.color_pair(1) | curses.A_BOLD)

    stdscr.refresh()


def _new_world(mode, predator_count):
    if mode == "manual":
        return World(init_pop=70, manual_food=True, manual_predators=True)
    return World(init_pop=70, predator_count=predator_count)


def run(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    setup_colors()

    mode = "auto"
    placing = "food"
    cursor = [WIDTH / 2, HEIGHT / 2]

    world = _new_world(mode, 6)
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
            world = _new_world(mode, len(world.predators))
        elif key in (ord("+"), ord("=")):
            speed = min(200, speed + (1 if speed < 10 else 10))
        elif key in (ord("-"), ord("_")):
            speed = max(1, speed - (1 if speed <= 10 else 10))
        elif key == ord("f") and mode == "auto":
            world.add_food(*world.rng.uniform([10, 10], [WIDTH - 10, HEIGHT - 10]))
        elif key == ord("m"):
            mode = "manual" if mode == "auto" else "auto"
        elif key == ord("p"):
            placing = "predator" if placing == "food" else "food"
        elif key == ord("["):
            world.remove_predator()
        elif key == ord("]"):
            world.add_random_predator()
        elif key == curses.KEY_UP:
            cursor[1] = max(0.0, cursor[1] - CURSOR_STEP)
        elif key == curses.KEY_DOWN:
            cursor[1] = min(HEIGHT, cursor[1] + CURSOR_STEP)
        elif key == curses.KEY_LEFT:
            cursor[0] = max(0.0, cursor[0] - CURSOR_STEP)
        elif key == curses.KEY_RIGHT:
            cursor[0] = min(WIDTH, cursor[0] + CURSOR_STEP)
        elif key in ENTER_KEYS and mode == "manual":
            if placing == "food":
                world.add_food(cursor[0], cursor[1])
            else:
                world.add_predator(cursor[0], cursor[1])

        if not paused:
            for _ in range(speed):
                world.step()

        draw(stdscr, world, paused, speed, mode, placing, cursor)
        time.sleep(frame_time)


def main():
    curses.wrapper(run)


if __name__ == "__main__":
    main()
