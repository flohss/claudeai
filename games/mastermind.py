"""Mastermind : devinez le code secret en 10 essais maximum."""
import random
from .utils import header, pause, prompt, success, error, info, color, clear
try:
    from colorama import Fore, Style
except ImportError:
    class _D:
        def __getattr__(self, _): return ""
    Fore = Style = _D()

COLORS = {
    "R": ("Rouge",   Fore.RED),
    "V": ("Vert",    Fore.GREEN),
    "B": ("Bleu",    Fore.BLUE),
    "J": ("Jaune",   Fore.YELLOW),
    "M": ("Magenta", Fore.MAGENTA),
    "C": ("Cyan",    Fore.CYAN),
    "O": ("Orange",  Fore.RED),    # approximation
    "W": ("Blanc",   Fore.WHITE),
}

DIFF = {
    "facile":    (4, 6, 12),   # code_len, nb_colors, max_tries
    "normal":    (4, 6, 10),
    "difficile": (5, 8, 10),
}


def _make_secret(length, nb_colors):
    pool = list(COLORS.keys())[:nb_colors]
    return [random.choice(pool) for _ in range(length)]


def _evaluate(secret, guess):
    """Return (blacks, whites) — blacks=right place, whites=right color wrong place."""
    blacks = sum(s == g for s, g in zip(secret, guess))
    # whites: count color matches ignoring exact positions
    from collections import Counter
    s_count = Counter(s for s, g in zip(secret, guess) if s != g)
    g_count = Counter(g for s, g in zip(secret, guess) if s != g)
    whites = sum((s_count & g_count).values())
    return blacks, whites


def _color_cell(key):
    name, fg = COLORS.get(key, ("?", Fore.WHITE))
    return color(f"[{key}]", fg, bold=True)


def _display_history(history, code_len):
    if not history:
        return
    print()
    print(color(f"  {'#':>2}  {'Code':<{code_len*4}}  ⬛ Exact  ⬜ Couleur", Fore.CYAN))
    print(color("  " + "─" * 40, Fore.CYAN))
    for i, (guess, b, w) in enumerate(history, 1):
        cells = "  ".join(_color_cell(k) for k in guess)
        blacks = color("⬛" * b, Fore.WHITE)
        whites = color("⬜" * w, Fore.YELLOW)
        print(f"  {i:>2}  {cells}   {blacks}{whites}")
    print()


def _parse_guess(raw, length, nb_colors):
    pool = set(list(COLORS.keys())[:nb_colors])
    tokens = raw.strip().upper().split()
    if len(tokens) != length:
        return None, f"Entrez exactement {length} couleurs."
    invalid = [t for t in tokens if t not in pool]
    if invalid:
        return None, f"Couleurs invalides : {', '.join(invalid)}"
    return tokens, None


def play(difficulty="normal"):
    code_len, nb_colors, max_tries = DIFF.get(difficulty, DIFF["normal"])
    pool = list(COLORS.keys())[:nb_colors]
    secret = _make_secret(code_len, nb_colors)
    history = []

    header("MASTERMIND  🔐")
    info(f"Niveau : {difficulty} | Code de {code_len} couleurs | {max_tries} essais max")
    info(f"Couleurs disponibles : " + "  ".join(_color_cell(k) for k in pool))
    info("Entrez les couleurs séparées par des espaces (ex: R V B J).")
    info("⬛ = bonne couleur bonne position  |  ⬜ = bonne couleur mauvaise position")
    pause()

    won = False
    for attempt in range(1, max_tries + 1):
        clear()
        header("MASTERMIND  🔐")
        info(f"Essai {attempt}/{max_tries} | Couleurs : " + "  ".join(_color_cell(k) for k in pool))
        _display_history(history, code_len)

        while True:
            raw = prompt(f"  Essai {attempt} : ")
            guess, err = _parse_guess(raw, code_len, nb_colors)
            if err:
                error(err)
            else:
                break

        blacks, whites = _evaluate(secret, guess)
        history.append((guess, blacks, whites))

        if blacks == code_len:
            won = True
            break

    score = 0
    clear()
    header("MASTERMIND  🔐")
    _display_history(history, code_len)
    secret_str = "  ".join(_color_cell(k) for k in secret)

    if won:
        turns = len(history)
        score = max(0, (max_tries - turns + 1) * code_len * 20)
        success(f"Bravo ! Code trouvé en {turns} essai(s) !")
        print(color(f"\n  Code secret : {secret_str}", Fore.GREEN))
    else:
        error("Perdu ! Vous n'avez plus d'essais.")
        print(color(f"\n  Code secret était : {secret_str}", Fore.YELLOW))

    print(color(f"\n  Score : {score}", Fore.YELLOW, bold=True))
    pause()
    return score
