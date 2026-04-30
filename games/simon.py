"""Simon : mémorisez et répétez une séquence croissante."""
import random
import time
from .utils import header, pause, prompt, success, error, info, color, clear
try:
    from colorama import Fore, Style
except ImportError:
    class _D:
        def __getattr__(self, _): return ""
    Fore = Style = _D()

COLORS = {
    "R": ("ROUGE",    Fore.RED),
    "V": ("VERT",     Fore.GREEN),
    "B": ("BLEU",     Fore.BLUE),
    "J": ("JAUNE",    Fore.YELLOW),
    "M": ("MAGENTA",  Fore.MAGENTA),
    "C": ("CYAN",     Fore.CYAN),
}


def _show_pad():
    lines = []
    for key, (name, fg) in COLORS.items():
        lines.append(color(f"  [{key}]", fg, bold=True) + color(f" {name}", fg))
    return "\n".join(lines)


def _display_sequence_step(key):
    name, fg = COLORS[key]
    clear()
    header("SIMON  🎨")
    # Flash the color
    block = color(f"\n\n  ████  {name}  ████\n", fg, bold=True)
    print(block)
    time.sleep(0.7)
    clear()
    header("SIMON  🎨")
    print("\n\n  ░░░░  ...  ░░░░\n")
    time.sleep(0.3)


def play(difficulty="normal"):
    speed_map = {"facile": 0.9, "normal": 0.65, "difficile": 0.45}
    speed = speed_map.get(difficulty, 0.65)
    keys = list(COLORS.keys())

    header("SIMON  🎨")
    info(f"Niveau : {difficulty}")
    info("Mémorisez la séquence de couleurs, puis reproduisez-la.")
    info("Entrez les lettres séparées par des espaces (ex: R V B J).")
    print("\n" + _show_pad())
    pause()

    sequence = []
    score = 0

    while True:
        # Extend sequence
        sequence.append(random.choice(keys))

        # Show sequence
        clear()
        header("SIMON  🎨")
        info(f"Séquence n°{len(sequence)} — Regardez bien !")
        time.sleep(speed * 0.5 + 0.5)
        for key in sequence:
            _display_sequence_step(key)

        # Player input
        clear()
        header("SIMON  🎨")
        info(f"Reproduisez la séquence ({len(sequence)} couleur(s)) :")
        print("\n" + _show_pad() + "\n")
        raw = prompt("  Votre séquence : ").strip().upper().split()

        if raw == sequence:
            success(f"Correct ! Séquence de {len(sequence)} bien mémorisée.")
            score += len(sequence) * 10
            time.sleep(0.8)
        else:
            clear()
            header("SIMON  🎨")
            error("Mauvaise séquence !")
            expected = " ".join(color(f"[{k}]", COLORS[k][1]) for k in sequence)
            given    = " ".join(color(f"[{k}]", COLORS.get(k, ("?", Fore.WHITE))[1])
                                if k in COLORS else color(f"[{k}]", Fore.WHITE)
                                for k in raw)
            info(f"Attendu  : {expected}")
            info(f"Entré    : {given}")
            print(color(f"\n  Score final : {score}", Fore.YELLOW, bold=True))
            info(f"  Vous avez mémorisé jusqu'à {len(sequence)-1} couleurs.")
            pause()
            return score
