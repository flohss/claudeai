"""Sudoku 4x4 : jeu de logique classique en taille réduite."""
import random
import copy
from .utils import header, pause, prompt, success, error, info, color, clear
try:
    from colorama import Fore, Style
except ImportError:
    class _D:
        def __getattr__(self, _): return ""
    Fore = Style = _D()

# ─── Solver / Generator ──────────────────────────────────────────────────────

def _is_valid(board, row, col, num, size=4):
    box = int(size ** 0.5)
    if num in board[row]:
        return False
    if num in [board[r][col] for r in range(size)]:
        return False
    br, bc = (row // box) * box, (col // box) * box
    for r in range(br, br + box):
        for c in range(bc, bc + box):
            if board[r][c] == num:
                return False
    return True


def _solve(board, size=4):
    for r in range(size):
        for c in range(size):
            if board[r][c] == 0:
                nums = list(range(1, size + 1))
                random.shuffle(nums)
                for n in nums:
                    if _is_valid(board, r, c, n, size):
                        board[r][c] = n
                        if _solve(board, size):
                            return True
                        board[r][c] = 0
                return False
    return True


def _generate(size=4, blanks=8):
    board = [[0] * size for _ in range(size)]
    _solve(board, size)
    solution = copy.deepcopy(board)
    cells = [(r, c) for r in range(size) for c in range(size)]
    random.shuffle(cells)
    for r, c in cells[:blanks]:
        board[r][c] = 0
    return board, solution


# ─── Display ─────────────────────────────────────────────────────────────────

def _display(board, fixed, size=4):
    box = int(size ** 0.5)
    sep = color("  +" + "+".join(["───"] * box) * box + "+", Fore.CYAN)
    print()
    for r in range(size):
        if r % box == 0:
            print(sep)
        row_str = color("  |", Fore.CYAN)
        for c in range(size):
            val = board[r][c]
            if c % box == 0 and c > 0:
                row_str += color("|", Fore.CYAN)
            if val == 0:
                row_str += color(" · ", Fore.WHITE)
            elif fixed[r][c]:
                row_str += color(f" {val} ", Fore.YELLOW, bold=True)
            else:
                row_str += color(f" {val} ", Fore.GREEN)
        row_str += color("|", Fore.CYAN)
        row_label = color(f" {r+1} ", Fore.MAGENTA)
        print(row_label + row_str)
    print(sep)
    col_labels = "     " + "  ".join(color(str(c+1), Fore.MAGENTA) for c in range(size))
    print(col_labels)
    print()


def _is_complete(board, size=4):
    return all(board[r][c] != 0 for r in range(size) for c in range(size))


def _is_correct(board, solution, size=4):
    return board == solution


# ─── Main ─────────────────────────────────────────────────────────────────────

BLANK_MAP = {"facile": 5, "normal": 8, "difficile": 11}


def play(difficulty="normal"):
    size = 4
    blanks = BLANK_MAP.get(difficulty, 8)
    board, solution = _generate(size, blanks)
    fixed = [[board[r][c] != 0 for c in range(size)] for r in range(size)]
    import time
    start = time.time()
    errors = 0

    header("SUDOKU 4×4  🧩")
    info(f"Niveau : {difficulty} | {blanks} cases vides")
    info("Remplissez la grille : chaque ligne, colonne et bloc 2×2 contient 1-4.")
    info("Commande : 'ligne colonne valeur' (ex: 1 3 4) | 'aide' | 'quitter'")
    pause()

    while True:
        clear()
        header("SUDOKU 4×4  🧩")
        info(f"Niveau : {difficulty}  |  Erreurs : {errors}  |  {blanks} vides au départ")
        _display(board, fixed, size)

        if _is_complete(board, size):
            if _is_correct(board, solution, size):
                elapsed = int(time.time() - start)
                score = max(0, 500 - errors * 30 - elapsed)
                success(f"Sudoku résolu en {elapsed}s avec {errors} erreur(s) !")
                print(color(f"\n  Score : {score}", Fore.YELLOW, bold=True))
                pause()
                return score
            else:
                error("La grille est complète mais incorrecte. Vérifiez !")
                continue

        raw = prompt("  Votre coup (ligne col val) ou 'aide'/'quitter' : ").strip().lower()

        if raw in ("quitter", "q"):
            info("Partie abandonnée.")
            pause()
            return 0

        if raw in ("aide", "a", "hint"):
            # Reveal one cell
            empties = [(r, c) for r in range(size) for c in range(size) if board[r][c] == 0]
            if empties:
                r, c = random.choice(empties)
                board[r][c] = solution[r][c]
                errors += 1
                info(f"Aide : case ({r+1},{c+1}) = {solution[r][c]}")
            continue

        parts = raw.split()
        if len(parts) != 3:
            error("Format attendu : ligne colonne valeur (ex: 2 3 4)")
            continue
        try:
            r, c, val = int(parts[0]) - 1, int(parts[1]) - 1, int(parts[2])
        except ValueError:
            error("Entrez des nombres entiers.")
            continue

        if not (0 <= r < size and 0 <= c < size):
            error(f"Ligne et colonne doivent être entre 1 et {size}.")
            continue
        if not (1 <= val <= size):
            error(f"La valeur doit être entre 1 et {size}.")
            continue
        if fixed[r][c]:
            error("Cette case est fixe, vous ne pouvez pas la modifier.")
            continue

        if val == solution[r][c]:
            board[r][c] = val
            success(f"Correct !")
        else:
            errors += 1
            error(f"Incorrect ! ({errors} erreur(s) au total)")
