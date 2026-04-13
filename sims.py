#!/usr/bin/env python3
"""
Les Sims - Ligne de Commande
Un simulateur de vie en mode texte.
"""

import time
import sys
import os
import random

# --- Couleurs ANSI ---
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"
    GRAY    = "\033[90m"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def bar(value, max_value=100, length=20):
    """Affiche une barre de progression colorée."""
    filled = int(length * value / max_value)
    empty  = length - filled
    if value > 60:
        color = C.GREEN
    elif value > 30:
        color = C.YELLOW
    else:
        color = C.RED
    return f"{color}{'█' * filled}{'░' * empty}{C.RESET} {value:3d}%"

def slow_print(text, delay=0.03):
    """Affiche du texte lettre par lettre."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()

# --- Personnage ---
class Sim:
    NEEDS = ["faim", "energie", "hygiene", "fun", "social", "vessie"]

    NEED_LABELS = {
        "faim":    ("Faim",    "🍔"),
        "energie": ("Énergie", "⚡"),
        "hygiene": ("Hygiène", "🚿"),
        "fun":     ("Fun",     "🎮"),
        "social":  ("Social",  "💬"),
        "vessie":  ("Vessie",  "🚽"),
    }

    def __init__(self, name):
        self.name = name
        self.age  = 0          # jours écoulés
        self.money = 500
        self.job   = None
        self.job_days = 0

        # Besoins (0 = critique, 100 = plein)
        self.needs = {
            "faim":    80,
            "energie": 80,
            "hygiene": 70,
            "fun":     60,
            "social":  60,
            "vessie":  80,
        }
        self.mood_history = []

    # ---- Humeur globale ----
    @property
    def mood(self):
        avg = sum(self.needs.values()) / len(self.needs)
        return int(avg)

    def mood_label(self):
        m = self.mood
        if m >= 80: return f"{C.GREEN}Heureux(se) 😄{C.RESET}"
        if m >= 60: return f"{C.YELLOW}Bien 🙂{C.RESET}"
        if m >= 40: return f"{C.YELLOW}Moyen 😐{C.RESET}"
        if m >= 20: return f"{C.RED}Triste 😟{C.RESET}"
        return f"{C.RED}Miserable 😭{C.RESET}"

    # ---- Passage du temps ----
    def tick(self, hours=1):
        """Diminue les besoins avec le temps."""
        decay = {
            "faim":    -5  * hours,
            "energie": -3  * hours,
            "hygiene": -2  * hours,
            "fun":     -4  * hours,
            "social":  -3  * hours,
            "vessie":  -7  * hours,
        }
        for need, delta in decay.items():
            self.needs[need] = max(0, min(100, self.needs[need] + delta))

    def modify(self, **kwargs):
        for need, delta in kwargs.items():
            if need in self.needs:
                self.needs[need] = max(0, min(100, self.needs[need] + delta))

    # ---- Statut critique ----
    def critical_needs(self):
        return [n for n, v in self.needs.items() if v <= 10]

    def is_alive(self):
        # Mort si faim ou énergie à 0 trop longtemps → simplifié ici
        return self.needs["faim"] > 0 or self.needs["energie"] > 5


# --- Affichage ---
def show_status(sim):
    clear()
    print(f"\n{C.BOLD}{C.CYAN}╔══════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}║   LES SIMS - LIGNE DE COMMANDE       ║{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}╚══════════════════════════════════════╝{C.RESET}\n")

    print(f"  {C.BOLD}Sim :{C.RESET} {sim.name}  |  "
          f"{C.BOLD}Jour :{C.RESET} {sim.age}  |  "
          f"{C.BOLD}Argent :{C.RESET} {C.GREEN}${sim.money}{C.RESET}  |  "
          f"{C.BOLD}Humeur :{C.RESET} {sim.mood_label()}")

    if sim.job:
        print(f"  {C.BOLD}Travail :{C.RESET} {sim.job}  ({sim.job_days} jour(s))\n")
    else:
        print(f"  {C.BOLD}Travail :{C.RESET} {C.GRAY}Chômeur(se){C.RESET}\n")

    print(f"  {C.BOLD}── Besoins ────────────────────────────{C.RESET}")
    for need in Sim.NEEDS:
        label, emoji = Sim.NEED_LABELS[need]
        val = sim.needs[need]
        warn = f" {C.RED}⚠ CRITIQUE{C.RESET}" if val <= 10 else ""
        print(f"  {emoji} {label:<9} {bar(val)}{warn}")
    print()


def show_menu(actions):
    print(f"  {C.BOLD}── Actions disponibles ────────────────{C.RESET}")
    for i, (key, label, _) in enumerate(actions, 1):
        print(f"  {C.CYAN}[{i}]{C.RESET} {label}")
    print(f"  {C.CYAN}[0]{C.RESET} Quitter\n")


# --- Actions ---
ACTIONS = [
    # (id, label, fonction)
    ("manger",    "Manger (cuisiner)",        None),
    ("snack",     "Grignoter (rapide)",       None),
    ("dormir",    "Dormir (8h)",              None),
    ("sieste",    "Faire une sieste (2h)",    None),
    ("douche",    "Prendre une douche",       None),
    ("toilettes", "Aller aux toilettes",      None),
    ("tv",        "Regarder la TV",           None),
    ("lire",      "Lire un livre",            None),
    ("sortir",    "Sortir avec des amis",     None),
    ("appel",     "Appeler quelqu'un",        None),
    ("travailler","Aller travailler",         None),
    ("postuler",  "Chercher un emploi",       None),
    ("passer",    "Passer le temps (1h)",     None),
]


def action_manger(sim):
    slow_print(f"\n  {C.YELLOW}Tu cuisines un bon repas...{C.RESET}", 0.02)
    sim.modify(faim=+40, hygiene=-5, fun=+5)
    sim.tick(1)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_snack(sim):
    slow_print(f"\n  {C.YELLOW}Tu grignottes quelque chose de rapide...{C.RESET}", 0.02)
    sim.modify(faim=+15, fun=-5)
    sim.tick(0)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_dormir(sim):
    slow_print(f"\n  {C.BLUE}Tu dors profondément pendant 8 heures... 💤{C.RESET}", 0.02)
    sim.modify(energie=+60, hygiene=-10, faim=-20)
    sim.tick(8)
    sim.age += 1
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_sieste(sim):
    slow_print(f"\n  {C.BLUE}Tu fais une petite sieste de 2h... 😴{C.RESET}", 0.02)
    sim.modify(energie=+20, faim=-5)
    sim.tick(2)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_douche(sim):
    slow_print(f"\n  {C.CYAN}Tu prends une douche revigorante... 🚿{C.RESET}", 0.02)
    sim.modify(hygiene=+50, energie=+5, social=+5)
    sim.tick(1)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_toilettes(sim):
    slow_print(f"\n  {C.MAGENTA}Tu vas aux toilettes... 🚽{C.RESET}", 0.02)
    sim.modify(vessie=+80, hygiene=-5)
    sim.tick(0)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_tv(sim):
    slow_print(f"\n  {C.GREEN}Tu regardes la TV pendant 2h... 📺{C.RESET}", 0.02)
    sim.modify(fun=+25, social=+5, energie=-10, faim=-10)
    sim.tick(2)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_lire(sim):
    slow_print(f"\n  {C.GREEN}Tu lis un bon livre pendant 2h... 📖{C.RESET}", 0.02)
    sim.modify(fun=+20, energie=-5, faim=-5)
    sim.tick(2)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_sortir(sim):
    cost = 30
    if sim.money < cost:
        print(f"\n  {C.RED}Tu n'as pas assez d'argent pour sortir ! (${cost} nécessaires){C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    slow_print(f"\n  {C.MAGENTA}Tu passes la soirée avec des amis ! 🎉{C.RESET}", 0.02)
    sim.money -= cost
    sim.modify(fun=+40, social=+50, energie=-20, faim=-15, hygiene=-5)
    sim.tick(4)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_appel(sim):
    slow_print(f"\n  {C.MAGENTA}Tu appelles un(e) ami(e) pour discuter... 📞{C.RESET}", 0.02)
    sim.modify(social=+25, fun=+10, energie=-5)
    sim.tick(1)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

JOBS = [
    ("Livreur",      150),
    ("Cuisinier",    200),
    ("Développeur",  300),
    ("Médecin",      400),
    ("Artiste",      120),
]

def action_travailler(sim):
    if not sim.job:
        print(f"\n  {C.RED}Tu n'as pas de travail ! Postule d'abord.{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    salary = next(s for j, s in JOBS if j == sim.job)
    slow_print(f"\n  {C.YELLOW}Tu travailles toute la journée comme {sim.job}... 💼{C.RESET}", 0.02)
    sim.money += salary
    sim.job_days += 1
    sim.modify(energie=-30, faim=-25, social=+10, hygiene=-10, fun=-15)
    sim.tick(8)
    sim.age += 1
    slow_print(f"  {C.GREEN}+${salary} gagnés ! Total : ${sim.money}{C.RESET}", 0.02)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_postuler(sim):
    if sim.job:
        print(f"\n  {C.YELLOW}Tu as déjà un travail : {sim.job}.{C.RESET}")
        print(f"  Veux-tu en changer ? (o/n) ", end="")
        if input().strip().lower() != "o":
            return
    print(f"\n  {C.BOLD}Offres d'emploi disponibles :{C.RESET}")
    for i, (name, salary) in enumerate(JOBS, 1):
        print(f"  {C.CYAN}[{i}]{C.RESET} {name} — ${salary}/jour")
    print(f"  {C.CYAN}[0]{C.RESET} Annuler")
    try:
        choice = int(input("\n  Choix : ").strip())
        if 1 <= choice <= len(JOBS):
            sim.job = JOBS[choice - 1][0]
            sim.job_days = 0
            slow_print(f"\n  {C.GREEN}Félicitations ! Tu es maintenant {sim.job} ! 🎊{C.RESET}", 0.02)
    except ValueError:
        pass
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_passer(sim):
    slow_print(f"\n  {C.GRAY}Une heure passe tranquillement...{C.RESET}", 0.02)
    sim.tick(1)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")


ACTION_FNS = {
    "manger":    action_manger,
    "snack":     action_snack,
    "dormir":    action_dormir,
    "sieste":    action_sieste,
    "douche":    action_douche,
    "toilettes": action_toilettes,
    "tv":        action_tv,
    "lire":      action_lire,
    "sortir":    action_sortir,
    "appel":     action_appel,
    "travailler":action_travailler,
    "postuler":  action_postuler,
    "passer":    action_passer,
}


# --- Boucle principale ---
def game_loop(sim):
    while True:
        show_status(sim)

        # Avertissements critiques
        crit = sim.critical_needs()
        if crit:
            labels = [Sim.NEED_LABELS[n][0] for n in crit]
            print(f"  {C.RED}{C.BOLD}⚠  ATTENTION : {', '.join(labels)} en état critique !{C.RESET}\n")

        # Mort par famine / épuisement
        if sim.needs["faim"] == 0 and sim.needs["energie"] == 0:
            slow_print(f"\n  {C.RED}💀 {sim.name} est épuisé(e) et mort(e) de faim après {sim.age} jour(s)...{C.RESET}")
            slow_print(f"  {C.GRAY}Prends soin de tes Sims la prochaine fois !{C.RESET}")
            break

        show_menu(ACTIONS)

        try:
            choice = input("  Ton choix : ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "0"

        if choice == "0":
            slow_print(f"\n  {C.CYAN}Au revoir {sim.name} ! Merci d'avoir joué. 👋{C.RESET}")
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ACTIONS):
                action_key = ACTIONS[idx][0]
                ACTION_FNS[action_key](sim)
            else:
                print(f"  {C.RED}Choix invalide.{C.RESET}")
                time.sleep(1)
        except ValueError:
            print(f"  {C.RED}Choix invalide.{C.RESET}")
            time.sleep(1)


# --- Démarrage ---
def main():
    clear()
    print(f"\n{C.BOLD}{C.CYAN}")
    print("  ██████╗  ██████╗ ██████╗")
    print("  ██╔══██╗██╔═══██╗██╔══██╗")
    print("  ██████╔╝██║   ██║██████╔╝")
    print("  ██╔══██╗██║   ██║██╔══██╗")
    print("  ██████╔╝╚██████╔╝██████╔╝")
    print("  ╚═════╝  ╚═════╝ ╚═════╝")
    print(f"  LES SIMS — LIGNE DE COMMANDE{C.RESET}\n")

    slow_print("  Bienvenue dans Les Sims en mode terminal !", 0.03)
    slow_print("  Prends soin de ton Sim et gère ses besoins.\n", 0.03)

    name = input(f"  {C.BOLD}Quel est le prénom de ton Sim ? {C.RESET}").strip()
    if not name:
        name = "Alex"

    sim = Sim(name)
    slow_print(f"\n  {C.GREEN}Bienvenue {sim.name} ! Ta vie commence maintenant...{C.RESET}\n", 0.03)
    time.sleep(1)

    game_loop(sim)

    # Score final
    print(f"\n  {C.BOLD}── Résultats ──────────────────────────{C.RESET}")
    print(f"  Nom     : {sim.name}")
    print(f"  Jours   : {sim.age}")
    print(f"  Argent  : ${sim.money}")
    print(f"  Métier  : {sim.job or 'Jamais travaillé'}")
    print(f"  Humeur  : {sim.mood_label()}\n")


if __name__ == "__main__":
    main()
