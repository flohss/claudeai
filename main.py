#!/usr/bin/env python3
"""
╔══════════════════════════════════════╗
║     JEUX DE LOGIQUE & MÉMOIRE       ║
║         CLI Game Collection         ║
╚══════════════════════════════════════╝
"""
import sys
import json
import os
from pathlib import Path

# Ensure the package is importable when running as a script
sys.path.insert(0, str(Path(__file__).parent))

from games.utils import header, pause, prompt, success, error, info, color, clear
try:
    from colorama import Fore, Style
except ImportError:
    class _D:
        def __getattr__(self, _): return ""
    Fore = Style = _D()

SCORES_FILE = Path(__file__).parent / ".scores.json"

GAMES = [
    ("Mémoire de cartes  🃏",  "memory_cards",   "Retournez des paires de cartes cachées"),
    ("Simon              🎨",  "simon",           "Mémorisez et répétez une séquence de couleurs"),
    ("Mastermind         🔐",  "mastermind",      "Déchiffrez le code secret en peu d'essais"),
    ("Mémoire de chiffres🔢", "number_memory",   "Mémorisez des séquences de chiffres croissantes"),
    ("Sudoku 4×4         🧩",  "sudoku",          "Remplissez la grille de logique"),
    ("Wordle FR          🟩",  "wordle",          "Devinez le mot de 5 lettres en 6 essais"),
]

DIFFICULTIES = ["facile", "normal", "difficile"]


def load_scores():
    if SCORES_FILE.exists():
        try:
            return json.loads(SCORES_FILE.read_text())
        except Exception:
            pass
    return {}


def save_score(game_key, difficulty, score, name):
    scores = load_scores()
    key = f"{game_key}_{difficulty}"
    entry = scores.get(key, {"best": 0, "player": "", "history": []})
    entry["history"].append({"score": score, "player": name})
    entry["history"] = sorted(entry["history"], key=lambda x: x["score"], reverse=True)[:5]
    if score > entry["best"]:
        entry["best"] = score
        entry["player"] = name
    scores[key] = entry
    SCORES_FILE.write_text(json.dumps(scores, indent=2, ensure_ascii=False))


def show_scores():
    scores = load_scores()
    header("TABLEAU DES SCORES  🏆")
    if not scores:
        info("Aucun score enregistré pour l'instant.")
        pause()
        return
    for title, key, _ in GAMES:
        for diff in DIFFICULTIES:
            entry = scores.get(f"{key}_{diff}")
            if entry and entry["best"] > 0:
                line = (
                    color(f"  {title[:20]:<22}", Fore.CYAN) +
                    color(f"[{diff:<10}]", Fore.MAGENTA) +
                    color(f"  {entry['best']:>6} pts", Fore.YELLOW, bold=True) +
                    color(f"  par {entry['player']}", Fore.WHITE)
                )
                print(line)
    print()
    pause()


def select_difficulty():
    header("CHOISIR LA DIFFICULTÉ")
    for i, d in enumerate(DIFFICULTIES, 1):
        icons = {"facile": "🟢", "normal": "🟡", "difficile": "🔴"}
        print(color(f"  {i}. ", Fore.WHITE) + color(f"{icons[d]} {d.capitalize()}", Fore.CYAN))
    print()
    while True:
        raw = prompt("  Votre choix (1-3) : ").strip()
        if raw in ("1", "2", "3"):
            return DIFFICULTIES[int(raw) - 1]
        error("Entrez 1, 2 ou 3.")


def ask_player_name():
    raw = prompt("  Votre pseudo (Entrée = Anonyme) : ").strip()
    return raw if raw else "Anonyme"


def main_menu():
    header("JEUX DE LOGIQUE & MÉMOIRE")
    print(color("  Choisissez un jeu :\n", Fore.WHITE))
    for i, (title, _, desc) in enumerate(GAMES, 1):
        print(color(f"  {i}. ", Fore.YELLOW, bold=True) +
              color(f"{title}", Fore.CYAN, bold=True))
        print(color(f"     {desc}", Fore.WHITE))
        print()
    print(color("  S. ", Fore.YELLOW, bold=True) + color("Tableau des scores  🏆", Fore.CYAN))
    print(color("  Q. ", Fore.YELLOW, bold=True) + color("Quitter", Fore.WHITE))
    print()
    while True:
        raw = prompt("  Votre choix : ").strip().upper()
        if raw == "Q":
            return None
        if raw == "S":
            return "scores"
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(GAMES):
                return idx
        except ValueError:
            pass
        error(f"Entrez un chiffre entre 1 et {len(GAMES)}, S ou Q.")


def run():
    # Check Python version
    if sys.version_info < (3, 7):
        print("Python 3.7+ requis.")
        sys.exit(1)

    player_name = None

    while True:
        choice = main_menu()

        if choice is None:
            clear()
            print(color("\n  À bientôt ! 👋\n", Fore.CYAN, bold=True))
            break

        if choice == "scores":
            show_scores()
            continue

        title, module_name, _ = GAMES[choice]
        difficulty = select_difficulty()

        if player_name is None:
            header("BIENVENUE !")
            player_name = ask_player_name()

        # Import and run the selected game
        try:
            import importlib
            module = importlib.import_module(f"games.{module_name}")
            score = module.play(difficulty=difficulty)
        except KeyboardInterrupt:
            clear()
            info("\n  Partie interrompue.")
            pause("Appuyez sur Entrée pour revenir au menu...")
            continue
        except Exception as e:
            error(f"Erreur inattendue : {e}")
            import traceback
            traceback.print_exc()
            pause()
            continue

        if score > 0:
            save_score(module_name, difficulty, score, player_name)
            info(f"Score de {score} pts enregistré pour {player_name} !")

        clear()
        header("JEUX DE LOGIQUE & MÉMOIRE")
        print(color(f"\n  Rejouer ou changer de jeu ?\n", Fore.CYAN))
        raw = prompt("  [R]ejouer le même | [M]enu principal | [Q]uitter : ").strip().upper()
        if raw == "R":
            try:
                score = module.play(difficulty=difficulty)
                if score > 0:
                    save_score(module_name, difficulty, score, player_name)
            except KeyboardInterrupt:
                pass
        elif raw == "Q":
            clear()
            print(color("\n  À bientôt ! 👋\n", Fore.CYAN, bold=True))
            break
        # else: back to main menu


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        clear()
        print(color("\n  À bientôt ! 👋\n", Fore.CYAN, bold=True))
