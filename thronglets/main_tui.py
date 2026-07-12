"""Terminal (curses) renderer for Thronglets.

No GUI/X11/SDL needed - handy on Termux or over plain SSH, where pygame is
painful to install. Only the Python standard library plus numpy are needed.

You pick automatic or manual mode once, at startup - not something you
toggle mid-run.

Controls: space=pause  f=drop food (auto mode only)  r=reset  +/-=speed  q=quit
  p=toggle food/predator (manual placement)
  [ / ]=remove/add a predator right now (also sets the count used on reset)
  arrow keys=move cursor, enter=place (manual mode)
  h=in-game notice/help screen
"""

import argparse
import curses
import time

from simulation import DANGER, FOOD, HEIGHT, IDLE, MATE, MAX_POPULATION, World, WIDTH, load_seed_genome

DEFAULT_INIT_POP = 70
DEFAULT_LANGUAGE_FILE = "language_model.json"

TOKEN_COLOR_PAIR = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
STATE_LABELS = {IDLE: "idle", FOOD: "food-call", MATE: "mate-call", DANGER: "alarm-call"}
HUD_H = 9
CURSOR_STEP = 4.0
ENTER_KEYS = (10, 13, curses.KEY_ENTER)

HELP_LINES = [
    ("Thronglets — notice", curses.A_BOLD),
    ("", 0),
    ("Chaque creature nait avec un genome qui decide quelle couleur", 0),
    ("elle affiche selon son etat, et comment elle reagit aux couleurs", 0),
    ("des autres. Personne ne programme le sens des couleurs : un", 0),
    ("langage commun peut emerger par selection naturelle, ou pas.", 0),
    ("", 0),
    ("Les 4 etats, par ordre de priorite :", curses.A_BOLD),
    ("  1. danger     un predateur repere -> fuite immediate", 0),
    ("  2. food-call  de la nourriture est visible tout pres", 0),
    ("  3. mate-call  prete a se reproduire + partenaire prete proche", 0),
    ("  4. idle       rien de special (etat le plus frequent, de loin)", 0),
    ("", 0),
    ("Vivre, se reproduire, mourir :", curses.A_BOLD),
    ("  L'energie baisse en permanence, manger la restaure. Emettre", 0),
    ("  une couleur (hors silence) coute un peu d'energie en plus.", 0),
    ("  Assez d'energie et d'age, un partenaire pareil a proximite :", 0),
    ("  un enfant nait. Un predateur qui attrape une creature la tue.", 0),
    ("", 0),
    ("Lire le vocabulaire affiche en haut :", curses.A_BOLD),
    ("  Pour chaque etat, la part de la population qui utilise chaque", 0),
    ("  couleur. Ca part du hasard (~17%) et grimpe si un mot fait", 0),
    ("  consensus. '..' = silence, pas une couleur en moins.", 0),
    ("", 0),
    ("A savoir :", curses.A_BOLD),
    ("  Deux etats peuvent finir sur la meme couleur par hasard (ex:", 0),
    ("  idle et alarm-call) - rien ne l'empeche ni ne garantit que ca", 0),
    ("  se resolve. Parler coute de l'energie : le silence est une", 0),
    ("  vraie strategie, pas un defaut.", 0),
]


def show_help(stdscr):
    """Paginate so this fits any terminal height, not just tall ones."""
    stdscr.nodelay(False)
    rows, _ = stdscr.getmaxyx()
    page_size = max(1, rows - 2)
    for start in range(0, len(HELP_LINES), page_size):
        page = HELP_LINES[start:start + page_size]
        stdscr.erase()
        for i, (line, attr) in enumerate(page):
            _safe_addstr(stdscr, i, 0, line, curses.color_pair(7) | attr)
        more = start + page_size < len(HELP_LINES)
        footer = "-- espace pour la suite --" if more else "-- une touche pour reprendre --"
        _safe_addstr(stdscr, min(rows - 1, len(page) + 1), 0, footer, curses.color_pair(7) | curses.A_DIM)
        stdscr.refresh()
        stdscr.getch()
    stdscr.nodelay(True)


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


def choose_mode(stdscr):
    stdscr.nodelay(False)
    stdscr.erase()
    lines = [
        ("Thronglets", curses.A_BOLD),
        ("", 0),
        ("Choisis le mode de depart :", curses.A_BOLD),
        ("  A = automatique - nourriture et predateurs apparaissent seuls", 0),
        ("  M = manuel - tu places tout toi-meme, rien ne spawn seul", 0),
        ("", 0),
        ("Appuie sur A ou M pour commencer.", curses.A_DIM),
    ]
    for i, (line, attr) in enumerate(lines):
        _safe_addstr(stdscr, i, 0, line, curses.color_pair(7) | attr)
    stdscr.refresh()

    mode = None
    while mode is None:
        key = stdscr.getch()
        if key in (ord("a"), ord("A")):
            mode = "auto"
        elif key in (ord("m"), ord("M")):
            mode = "manual"
    stdscr.nodelay(True)
    return mode


def choose_population(stdscr):
    stdscr.nodelay(False)
    stdscr.erase()
    lines = [
        ("Thronglets", curses.A_BOLD),
        ("", 0),
        (f"Combien de creatures au depart ? (1-{MAX_POPULATION}, entree = {DEFAULT_INIT_POP})", curses.A_BOLD),
    ]
    for i, (line, attr) in enumerate(lines):
        _safe_addstr(stdscr, i, 0, line, curses.color_pair(7) | attr)
    _safe_addstr(stdscr, 4, 0, "> ", curses.color_pair(7))
    stdscr.refresh()

    curses.echo()
    curses.curs_set(1)
    text = stdscr.getstr(4, 2, 4).decode(errors="ignore").strip()
    curses.noecho()
    curses.curs_set(0)
    stdscr.nodelay(True)

    try:
        n = int(text)
    except ValueError:
        return DEFAULT_INIT_POP
    return max(1, min(MAX_POPULATION, n))


def choose_ai(stdscr):
    stdscr.nodelay(False)
    stdscr.erase()
    lines = [
        ("Thronglets", curses.A_BOLD),
        ("", 0),
        ("Activer le langage pre-entraine par IA ?", curses.A_BOLD),
        (f"  (relit '{DEFAULT_LANGUAGE_FILE}', genere par train_language.py)", 0),
        ("", 0),
        ("  O = oui - les creatures parlent deja un langage sans confusion", 0),
        ("  N = non - le langage doit emerger tout seul en jouant (defaut)", 0),
        ("", 0),
        ("Appuie sur O ou N pour commencer.", curses.A_DIM),
    ]
    for i, (line, attr) in enumerate(lines):
        _safe_addstr(stdscr, i, 0, line, curses.color_pair(7) | attr)
    stdscr.refresh()

    choice = None
    while choice is None:
        key = stdscr.getch()
        if key in (ord("o"), ord("O")):
            choice = True
        elif key in (ord("n"), ord("N")):
            choice = False
    stdscr.nodelay(True)
    return choice


def _flash_message(stdscr, text):
    stdscr.nodelay(False)
    stdscr.erase()
    _safe_addstr(stdscr, 0, 0, text, curses.color_pair(1) | curses.A_BOLD)
    _safe_addstr(stdscr, 2, 0, "-- une touche pour continuer --", curses.color_pair(7) | curses.A_DIM)
    stdscr.refresh()
    stdscr.getch()
    stdscr.nodelay(True)


def draw(stdscr, world, paused, speed, mode, placing, cursor, trained=False):
    stdscr.erase()
    rows, cols = stdscr.getmaxyx()
    field_h = max(1, rows - HUD_H)
    field_w = max(1, cols)
    sx, sy = (field_w - 1) / WIDTH, (field_h - 1) / HEIGHT

    pop = world.population()
    status = "PAUSED" if paused else f"x{speed}"
    tag = "  [trained vocabulary]" if trained else ""
    header = f"tick {world.tick}  pop {pop}  births {world.births}  deaths {world.deaths}  {status}{tag}"
    _safe_addstr(stdscr, 0, 0, header, curses.color_pair(7) | curses.A_BOLD)

    if mode == "manual":
        settings = f"mode: manuel   pose: {placing} (p)   fleches+entree pour placer"
    else:
        settings = f"mode: auto   predateurs: {len(world.predators)} ([ ] agit tout de suite)"
    _safe_addstr(stdscr, 1, 0, settings, curses.color_pair(7) | curses.A_DIM)

    breakdown = world.vocabulary_breakdown()
    for row, state in enumerate((DANGER, FOOD, MATE, IDLE), start=2):
        _draw_vocab_row(stdscr, row, STATE_LABELS[state], breakdown[state])

    _safe_addstr(stdscr, HUD_H - 3, 0, "o colore = signale   o blanc = silencieuse   . = nourriture   X = predateur",
                 curses.color_pair(7) | curses.A_DIM)
    food_hint = "f=food" if mode == "auto" else "f=food (auto mode only)"
    _safe_addstr(stdscr, HUD_H - 2, 0, f"space=pause  {food_hint}  r=reset  +/-=speed  q=quit",
                 curses.color_pair(7) | curses.A_DIM)
    _safe_addstr(stdscr, HUD_H - 1, 0, "p=placer  [ ]=nb predateurs  fleches/entree=placer  h=aide",
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


def _new_world(mode, predator_count, init_pop=DEFAULT_INIT_POP, seed_genome=None):
    if mode == "manual":
        return World(init_pop=init_pop, manual_food=True, manual_predators=True, seed_genome=seed_genome)
    return World(init_pop=init_pop, predator_count=predator_count, seed_genome=seed_genome)


def run(stdscr, language_path=None):
    curses.curs_set(0)
    setup_colors()

    mode = choose_mode(stdscr)
    init_pop = choose_population(stdscr)

    if language_path:
        seed_genome = load_seed_genome(language_path)
    elif choose_ai(stdscr):
        try:
            seed_genome = load_seed_genome(DEFAULT_LANGUAGE_FILE)
        except OSError:
            seed_genome = None
            _flash_message(stdscr, f"'{DEFAULT_LANGUAGE_FILE}' introuvable - lancement sans IA.")
    else:
        seed_genome = None

    placing = "food"
    cursor = [WIDTH / 2, HEIGHT / 2]

    world = _new_world(mode, 6, init_pop, seed_genome)
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
            world = _new_world(mode, len(world.predators), init_pop, seed_genome)
        elif key in (ord("+"), ord("=")):
            speed = min(200, speed + (1 if speed < 10 else 10))
        elif key in (ord("-"), ord("_")):
            speed = max(1, speed - (1 if speed <= 10 else 10))
        elif key == ord("f") and mode == "auto":
            world.add_food(*world.rng.uniform([10, 10], [WIDTH - 10, HEIGHT - 10]))
        elif key == ord("p"):
            placing = "predator" if placing == "food" else "food"
        elif key == ord("["):
            world.remove_predator()
        elif key == ord("]"):
            world.add_random_predator()
        elif key == ord("h"):
            show_help(stdscr)
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

        draw(stdscr, world, paused, speed, mode, placing, cursor, trained=seed_genome is not None)
        time.sleep(frame_time)


def main():
    parser = argparse.ArgumentParser(description="Thronglets - terminal renderer")
    parser.add_argument("--language", type=str, default=None,
                         help="seed the population with a train_language.py --export vocabulary "
                              "instead of starting from scratch")
    args = parser.parse_args()

    curses.wrapper(run, args.language)


if __name__ == "__main__":
    main()
