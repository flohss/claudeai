"""Mémoire de chiffres : mémorisez une séquence de plus en plus longue."""
import random
import time
from .utils import header, pause, prompt, success, error, info, color, clear
try:
    from colorama import Fore, Style
except ImportError:
    class _D:
        def __getattr__(self, _): return ""
    Fore = Style = _D()

DIFF = {
    "facile":    {"start": 3, "show_time": 2.5, "mode": "repeat"},
    "normal":    {"start": 4, "show_time": 2.0, "mode": "repeat"},
    "difficile": {"start": 5, "show_time": 1.5, "mode": "reverse"},
}


def _show_sequence(seq, duration):
    clear()
    header("MÉMOIRE DE CHIFFRES  🔢")
    info("Mémorisez cette séquence :\n")
    display = "  ".join(color(str(n), Fore.YELLOW, bold=True) for n in seq)
    print(f"\n   {display}\n")

    bar_len = 30
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed >= duration:
            break
        filled = int(bar_len * elapsed / duration)
        bar = color("█" * filled, Fore.GREEN) + color("░" * (bar_len - filled), Fore.WHITE)
        print(f"   [{bar}]  {duration - elapsed:.1f}s", end="\r", flush=True)
        time.sleep(0.05)
    print()


def play(difficulty="normal"):
    cfg = DIFF.get(difficulty, DIFF["normal"])
    start_len  = cfg["start"]
    show_time  = cfg["show_time"]
    mode       = cfg["mode"]
    score      = 0
    cur_len    = start_len

    header("MÉMOIRE DE CHIFFRES  🔢")
    info(f"Niveau : {difficulty}")
    if mode == "reverse":
        info("Mémorisez la séquence et entrez-la À L'ENVERS !")
    else:
        info("Mémorisez la séquence et reproduisez-la.")
    info("La séquence s'allonge à chaque bonne réponse.")
    pause()

    lives = 3
    while lives > 0:
        seq = [random.randint(0, 9) for _ in range(cur_len)]
        _show_sequence(seq, show_time)

        clear()
        header("MÉMOIRE DE CHIFFRES  🔢")
        info(f"Vies : {'❤️ ' * lives}  |  Longueur : {cur_len}  |  Score : {score}")

        if mode == "reverse":
            info("Entrez la séquence À L'ENVERS (chiffres collés, ex: 4 2 7 → 724) :")
            target = list(reversed(seq))
        else:
            info("Entrez la séquence (chiffres séparés par des espaces) :")
            target = seq

        raw = prompt("  Votre réponse : ").strip().replace(" ", "")
        try:
            given = [int(c) for c in raw]
        except ValueError:
            error("Entrez uniquement des chiffres.")
            lives -= 1
            continue

        if given == target:
            success(f"Parfait ! Séquence de {cur_len} correcte.")
            score += cur_len * 15
            cur_len += 1
            show_time = max(0.8, show_time - 0.1)
        else:
            lives -= 1
            error(f"Incorrect ! Il restait {lives} vie(s).")
            info(f"  Attendu  : {' '.join(str(n) for n in target)}")
            info(f"  Vous avez: {' '.join(str(n) for n in given)}")
            if lives > 0:
                cur_len = max(start_len, cur_len - 1)
            time.sleep(1.5)

    clear()
    header("MÉMOIRE DE CHIFFRES  🔢")
    error("Plus de vies !")
    info(f"  Meilleure longueur atteinte : {cur_len} chiffres")
    print(color(f"\n  Score final : {score}", Fore.YELLOW, bold=True))
    pause()
    return score
