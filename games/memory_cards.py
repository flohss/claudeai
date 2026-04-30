"""Jeu de Mémoire : retournez des paires de cartes."""
import random
import time
from .utils import header, pause, prompt, success, error, info, color, clear
try:
    from colorama import Fore, Style
except ImportError:
    class _D:
        def __getattr__(self, _): return ""
    Fore = Style = _D()

SYMBOLS = ["🍎", "🍌", "🍒", "🍇", "🍓", "🥝", "🍑", "🍋",
           "🌸", "⭐", "🎯", "🎲", "🎸", "🚀", "🦋", "🐸"]

# Fallback ASCII symbols for terminals without emoji support
ASCII_SYMBOLS = ["AA", "BB", "CC", "DD", "EE", "FF", "GG", "HH",
                 "II", "JJ", "KK", "LL", "MM", "NN", "OO", "PP"]


def _make_grid(pairs):
    symbols = (SYMBOLS[:pairs] * 2)
    random.shuffle(symbols)
    return symbols


def _display_grid(grid, revealed, cols):
    rows = len(grid) // cols
    print()
    # Column numbers
    header_row = "     " + "  ".join(color(f" {c+1} ", Fore.CYAN) for c in range(cols))
    print(header_row)
    print()
    for r in range(rows):
        row_label = color(f"  {chr(65+r)}  ", Fore.YELLOW)
        cells = []
        for c in range(cols):
            idx = r * cols + c
            if revealed[idx]:
                sym = grid[idx]
                cells.append(color(f"[{sym}]", Fore.GREEN))
            else:
                cells.append(color("[ ? ]", Fore.WHITE))
        print(row_label + "  ".join(cells))
    print()


def _parse_input(raw, cols):
    """Parse 'A1' style input into grid index."""
    raw = raw.strip().upper()
    if len(raw) < 2:
        return None
    row_char = raw[0]
    try:
        col = int(raw[1:]) - 1
    except ValueError:
        return None
    row = ord(row_char) - ord('A')
    rows = 16 // cols  # max
    if row < 0 or col < 0 or col >= cols:
        return None
    return row * cols + col


def play(difficulty="normal"):
    configs = {
        "facile": (3, 4, 4),   # 6 pairs, 3 cols, 4 rows — actually 4x3=12 cards = 6 pairs
        "normal": (4, 4, 4),   # 8 pairs, 4x4
        "difficile": (4, 4, 4),
    }
    # (pairs, cols, rows)
    pair_map = {"facile": 6, "normal": 8, "difficile": 10}
    col_map  = {"facile": 4, "normal": 4, "difficile": 4}

    pairs = pair_map.get(difficulty, 8)
    cols  = col_map.get(difficulty, 4)

    grid = _make_grid(pairs)
    total = len(grid)
    revealed = [False] * total
    matched  = [False] * total
    attempts = 0
    start = time.time()

    header("JEU DE MÉMOIRE  🃏")
    info(f"Niveau : {difficulty} | {pairs} paires à trouver")
    info("Entrez deux coordonnées (ex: A1 B3) pour retourner des cartes.")
    pause("Appuyez sur Entrée pour commencer...")

    while not all(matched):
        clear()
        header("JEU DE MÉMOIRE  🃏")
        info(f"Paires trouvées : {sum(matched)//2}/{pairs}  |  Tentatives : {attempts}")
        _display_grid(grid, [revealed[i] or matched[i] for i in range(total)], cols)

        # First card
        while True:
            raw1 = prompt("  Première carte (ex: A1) : ")
            idx1 = _parse_input(raw1, cols)
            if idx1 is None or idx1 >= total:
                error("Coordonnée invalide, réessayez.")
                continue
            if matched[idx1]:
                error("Cette carte est déjà trouvée.")
                continue
            break

        # Show first card
        revealed[idx1] = True
        clear()
        header("JEU DE MÉMOIRE  🃏")
        info(f"Paires trouvées : {sum(matched)//2}/{pairs}  |  Tentatives : {attempts}")
        _display_grid(grid, [revealed[i] or matched[i] for i in range(total)], cols)

        # Second card
        while True:
            raw2 = prompt("  Deuxième carte (ex: B3) : ")
            idx2 = _parse_input(raw2, cols)
            if idx2 is None or idx2 >= total:
                error("Coordonnée invalide, réessayez.")
                continue
            if matched[idx2]:
                error("Cette carte est déjà trouvée.")
                continue
            if idx2 == idx1:
                error("Choisissez une carte différente.")
                continue
            break

        revealed[idx2] = True
        attempts += 1

        clear()
        header("JEU DE MÉMOIRE  🃏")
        info(f"Paires trouvées : {sum(matched)//2}/{pairs}  |  Tentatives : {attempts}")
        _display_grid(grid, [revealed[i] or matched[i] for i in range(total)], cols)

        if grid[idx1] == grid[idx2]:
            success("Paire trouvée !")
            matched[idx1] = matched[idx2] = True
            revealed[idx1] = revealed[idx2] = False
        else:
            error("Pas de chance, ce n'est pas une paire.")
            time.sleep(1.5)
            revealed[idx1] = revealed[idx2] = False

    elapsed = int(time.time() - start)
    score = max(0, pairs * 100 - (attempts - pairs) * 10 - elapsed)

    clear()
    header("JEU DE MÉMOIRE  🃏")
    success(f"Bravo ! Toutes les paires trouvées en {attempts} tentatives et {elapsed}s !")
    print(color(f"\n  Score final : {score}", Fore.YELLOW, bold=True))
    pause()
    return score
