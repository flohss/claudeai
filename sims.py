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

# --- Stades de vie ---
# (jour_min, nom, emoji, mods_decay/h, bloquées, autorisation_parentale, description)
LIFE_STAGES = [
    (0,  "Enfant",       "🧒", {"energie": +2, "fun": -2},
     ["travailler", "postuler", "flirter", "rendezvous", "intimite", "proposer", "marier", "rupture"],
     ["sortir", "gastronomie", "sport", "jardiner"],
     "Tu découvres le monde !"),
    (5,  "Adolescent",   "🧑", {"social": -2, "fun": -1},
     ["travailler", "postuler", "intimite", "proposer", "marier"],
     ["sortir", "rendezvous"],
     "Tu cherches ta voie dans la vie."),
    (10, "Jeune adulte", "💪", {},                          [], [], "Tu es dans la fleur de l'âge !"),
    (20, "Adulte",       "👔", {"energie": -1},             [], [], "L'expérience guide tes choix."),
    (35, "Senior",       "🎩", {"energie": -3, "hygiene": -1}, [], [], "La sagesse et la liberté bien méritées !"),
]

def get_stage(age):
    """Retourne le stade de vie selon le nombre de jours."""
    idx = 0
    for i, (min_day, *_) in enumerate(LIFE_STAGES):
        if age >= min_day:
            idx = i
    return idx, LIFE_STAGES[idx]


def ask_parental_auth(sim, stage_name):
    """Demande l'autorisation parentale. Retourne True si accordée.
    La chance dépend de l'humeur du Sim (enfant sage = parents plus souples)."""
    if stage_name == "Enfant":
        base_prob = 55
    else:  # Adolescent
        base_prob = 70
    # Bonus/malus selon l'humeur : jusqu'à ±15%
    mood_bonus = int((sim.mood - 50) * 0.3)
    prob = max(20, min(90, base_prob + mood_bonus))

    slow_print(f"\n  Tu demandes la permission à tes parents... 👨‍👩‍👦", 0.03)
    time.sleep(0.6)
    if random.randint(1, 100) <= prob:
        slow_print(f"  {C.GREEN}Tes parents acceptent ! ✓{C.RESET}", 0.03)
        return True
    else:
        slow_print(f"  {C.RED}Tes parents refusent. ✗{C.RESET}", 0.03)
        slow_print(f"  {C.GRAY}Tu ravales ta déception...{C.RESET}", 0.02)
        sim.modify(fun=-10, social=-5)
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return False


# --- Personnage ---
class Sim:
    NEEDS = ["faim", "energie", "hygiene", "fun", "social", "vessie"]

    NEED_LABELS = {
        "faim":    ("Faim",    "🍔"),
        "energie": ("Énergie", "💡"),
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
        self.last_event = None   # dernier événement aléatoire
        self.weather = Weather()
        self.pet = None
        self.orientation  = "Bisexuel(le)"  # défini dans main()
        self.relationship = Relationship()

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
        # Appliquer les modificateurs du stade de vie
        _, stage = get_stage(self.age)
        for need, mod in stage[3].items():
            if need in decay:
                decay[need] += mod * hours
        for need, delta in decay.items():
            self.needs[need] = max(0, min(100, self.needs[need] + delta))
        if self.pet:
            self.pet.tick(hours)

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


# --- Météo ---
# (emoji, nom, effets quotidiens sur besoins, modificateurs activités extérieures)
WEATHER_TYPES = [
    ("🌞", "Ensoleillé", {"fun": +5,  "energie": +3},  {"sortir": +15, "jardiner": +10}),
    ("⛅", "Nuageux",    {},                             {"sortir":  0,  "jardiner":  0}),
    ("🌧", "Pluvieux",  {"hygiene": -5},                {"sortir": -15, "jardiner": -10}),
    ("⛈", "Orageux",   {"fun": -5, "energie": -5},     {"sortir": -30, "jardiner": -25}),
    ("🌨", "Enneigé",   {"energie": -5},                {"sortir": +5,  "jardiner": -20}),
]

class Weather:
    def __init__(self):
        self._data = random.choice(WEATHER_TYPES)

    def new_day(self):
        self._data = random.choice(WEATHER_TYPES)

    @property
    def emoji(self):  return self._data[0]
    @property
    def name(self):   return self._data[1]
    @property
    def daily_effects(self): return self._data[2]
    @property
    def outdoor_mods(self):  return self._data[3]


# --- Animal de compagnie ---
PET_SPECIES = {
    "Chien":   {"emoji": "🐶", "hunger_per_h": 4, "happy_per_h": 3},
    "Chat":    {"emoji": "🐱", "hunger_per_h": 2, "happy_per_h": 2},
    "Lapin":   {"emoji": "🐰", "hunger_per_h": 3, "happy_per_h": 2},
    "Poisson": {"emoji": "🐟", "hunger_per_h": 1, "happy_per_h": 1},
}

class Pet:
    def __init__(self, name, species):
        self.name      = name
        self.species   = species
        self.hunger    = 80
        self.happiness = 80

    @property
    def emoji(self):
        return PET_SPECIES[self.species]["emoji"]

    def tick(self, hours=1):
        info = PET_SPECIES[self.species]
        self.hunger    = max(0, self.hunger    - info["hunger_per_h"] * hours)
        self.happiness = max(0, self.happiness - info["happy_per_h"]  * hours)

    def feed(self):
        self.hunger = min(100, self.hunger + 45)

    def play(self):
        self.happiness = min(100, self.happiness + 40)

    def is_neglected(self):
        return self.hunger <= 20 or self.happiness <= 20


# --- Relations & Orientation ---
PARTNER_NAMES = ["Alex", "Sam", "Jordan", "Morgan", "Taylor", "Casey", "Robin", "Jamie", "Charlie", "River", "Noa", "Lou"]

class Relationship:
    STAGES = [
        (0, "Célibataire",   "💔"),
        (1, "Connaissance",  "👋"),
        (2, "Ami(e) proche", "🤝"),
        (3, "Coup de coeur", "💙"),
        (4, "En couple",     "💑"),
        (5, "Fiancé(e)",     "💍"),
        (6, "Marié(e)",      "💒"),
    ]
    # Seuil d'affection minimum pour passer au stade suivant
    THRESHOLDS = {1: 25, 2: 45, 3: 62, 4: 78, 5: 88, 6: 95}

    def __init__(self):
        self.level        = 0
        self.partner_name = None
        self.affection    = 0

    @property
    def label(self): return self.STAGES[self.level][1]
    @property
    def emoji(self): return self.STAGES[self.level][2]

    def is_single(self): return self.level == 0
    def has_partner(self): return self.level >= 1
    def is_couple(self):   return self.level >= 4

    def gain_affection(self, amount):
        self.affection = min(100, self.affection + amount)

    def try_advance(self):
        """Tente de passer au stade suivant. Retourne le nouveau label ou None."""
        threshold = self.THRESHOLDS.get(self.level + 1, 999)
        if self.level < 6 and self.affection >= threshold:
            self.level += 1
            self.affection = max(40, self.affection - 20)
            return self.STAGES[self.level][1]
        return None

    def breakup(self):
        self.level        = 0
        self.partner_name = None
        self.affection    = 0


# --- Événements aléatoires ---
# (probabilité 0-100, emoji, description, effets sur besoins, delta argent)
RANDOM_EVENTS = [
    # Positifs
    (8,  "💸", "Tu trouves un billet par terre !",
     {},                                      +40),
    (6,  "🎰", "Tu gagnes un ticket à gratter !",
     {"fun": +15},                             +random.randint(10, 80) if False else 0),  # calculé dynamiquement
    (7,  "🤝", "Un voisin t'apporte un repas cuisiné.",
     {"faim": +30, "social": +20},             0),
    (6,  "🎁", "Tu reçois un colis surprise d'un(e) ami(e) !",
     {"fun": +25, "social": +15},              0),
    (5,  "💼", "Ton patron t'accorde une prime surprise !",
     {"fun": +10},                             +100),
    (8,  "📻", "Tu tombes sur ta chanson préférée à la radio.",
     {"fun": +20, "energie": +5},              0),
    (6,  "🌞", "La météo est magnifique, tu te sens plein(e) d'énergie !",
     {"energie": +20, "fun": +10},             0),
    (5,  "👫", "Un(e) ami(e) débarque à l'improviste pour papoter.",
     {"social": +35, "fun": +20},              0),
    # Négatifs
    (8,  "🤒", "Tu tombes légèrement malade.",
     {"energie": -25, "hygiene": -20},         0),
    (6,  "🚨", "Tu reçois une facture inattendue !",
     {"fun": -15},                             -75),
    (7,  "🥴", "La nourriture était avariée... Tu te sens mal.",
     {"faim": -20, "energie": -15},            0),
    (5,  "😤", "Grosse dispute avec ton voisin.",
     {"social": -30, "fun": -15},              0),
    (6,  "⚡", "Panne de courant ! Soirée dans le noir.",
     {"fun": -20, "energie": -10},             0),
    (7,  "🌧", "Tu t'es fait(e) tremper sous la pluie.",
     {"hygiene": -25, "energie": -10},         0),
    (5,  "😱", "Un cauchemar t'a réveillé(e) en pleine nuit !",
     {"energie": -20, "fun": -10},             0),
    (4,  "🦟", "Nuit infernale à cause des moustiques.",
     {"energie": -15, "fun": -10},             0),
    (5,  "💳", "Tu t'es fait(e) arnaquer en ligne.",
     {"fun": -20, "social": -10},              -50),
    # Nouveaux positifs
    (5,  "🌟", "Ton patron te félicite pour ton excellent travail !",
     {"fun": +20, "social": +15},              +50),
    (4,  "🍀", "Tu trouves un bon de réduction dans ta boîte aux lettres.",
     {"fun": +10},                             +30),
    (6,  "🐶", "Un chien adorable croise ton chemin et égaie ta journée.",
     {"fun": +15, "social": +10},              0),
    (5,  "☕", "Ton café préféré t'offre un verre pour ta fidélité.",
     {"fun": +10, "energie": +10},             +10),
    (4,  "🎶", "Tu composes une petite mélodie spontanée qui te rend heureux(se).",
     {"fun": +25, "energie": +5},              0),
    (5,  "📦", "Une livraison surprise d'un(e) ami(e) arrive à ta porte.",
     {"fun": +20, "social": +20},              0),
    # Nouveaux négatifs
    (6,  "🚗", "Tu es bloqué(e) dans les embouteillages pendant 1h.",
     {"fun": -20, "energie": -10},             0),
    (5,  "📵", "Coupure internet pendant plusieurs heures.",
     {"fun": -25, "social": -15},              0),
    (4,  "👜", "Tu perds ton portefeuille... heureusement vide.",
     {"fun": -20, "social": -10},              -20),
    (5,  "🤧", "Tu attrapes un petit rhume.",
     {"energie": -20, "hygiene": -15, "fun": -10}, 0),
    (4,  "🔑", "Tu t'enfermes dehors et dois appeler un serrurier.",
     {"fun": -15, "social": -5},               -60),
    (5,  "😬", "Tu renverses ton café sur toi au bureau... gênant.",
     {"hygiene": -20, "fun": -15, "social": -10}, 0),
]


def trigger_random_event(sim):
    """Lance un dé et déclenche éventuellement un événement. Retourne le message ou None."""
    for prob, emoji, desc, effects, money in RANDOM_EVENTS:
        # Chaque événement a sa propre probabilité indépendante
        if random.randint(1, 100) <= prob:
            # Argent : calcul dynamique pour le ticket à gratter
            actual_money = money
            if emoji == "🎰":
                actual_money = random.randint(10, 80)

            sim.modify(**effects)
            sim.money = max(0, sim.money + actual_money)

            lines = [f"\n  {C.BOLD}━━ ÉVÉNEMENT ALÉATOIRE ━━{C.RESET}",
                     f"  {emoji}  {desc}"]
            if effects:
                parts = []
                for need, delta in effects.items():
                    label = Sim.NEED_LABELS[need][0]
                    sign = "+" if delta >= 0 else ""
                    color = C.GREEN if delta > 0 else C.RED
                    parts.append(f"{color}{sign}{delta} {label}{C.RESET}")
                lines.append(f"  Effets : {', '.join(parts)}")
            if actual_money != 0:
                sign = "+" if actual_money >= 0 else ""
                color = C.GREEN if actual_money > 0 else C.RED
                lines.append(f"  Argent : {color}{sign}${actual_money}{C.RESET}")

            return "\n".join(lines)
    return None


# --- Affichage ---
def show_status(sim):
    clear()
    print(f"\n{C.BOLD}{C.CYAN}╔══════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}║   LES SIMS - LIGNE DE COMMANDE       ║{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}╚══════════════════════════════════════╝{C.RESET}\n")

    _, stage = get_stage(sim.age)
    print(f"  {C.BOLD}Sim :{C.RESET} {sim.name}  |  "
          f"{C.BOLD}Jour :{C.RESET} {sim.age}  |  "
          f"{C.BOLD}Argent :{C.RESET} {C.GREEN}${sim.money}{C.RESET}  |  "
          f"{C.BOLD}Humeur :{C.RESET} {sim.mood_label()}")
    print(f"  {C.BOLD}Stade   :{C.RESET} {stage[2]}  {C.YELLOW}{stage[1]}{C.RESET}  —  {C.GRAY}{stage[6]}{C.RESET}")

    if sim.job:
        print(f"  {C.BOLD}Travail :{C.RESET} {sim.job}  ({sim.job_days} jour(s))")
    else:
        print(f"  {C.BOLD}Travail :{C.RESET} {C.GRAY}Chômeur(se){C.RESET}")

    # Météo
    w = sim.weather
    print(f"  {C.BOLD}Météo   :{C.RESET} {w.emoji}  {w.name}", end="")
    if w.daily_effects:
        parts = []
        for need, delta in w.daily_effects.items():
            label = Sim.NEED_LABELS[need][0]
            sign  = "+" if delta >= 0 else ""
            color = C.GREEN if delta > 0 else C.RED
            parts.append(f"{color}{sign}{delta} {label}{C.RESET}")
        print(f"  ({', '.join(parts)})", end="")
    print()

    # Relation amoureuse
    rel = sim.relationship
    if rel.is_single():
        print(f"  {C.BOLD}Relation :{C.RESET} {rel.emoji}  {rel.label}  {C.GRAY}({sim.orientation}){C.RESET}")
    else:
        print(f"  {C.BOLD}Relation :{C.RESET} {rel.emoji}  {rel.label} avec {C.MAGENTA}{rel.partner_name}{C.RESET}"
              f"  Affection {bar(rel.affection, length=10)}")

    # Animal de compagnie
    if sim.pet:
        p = sim.pet
        warn = f" {C.RED}⚠ BESOIN D'ATTENTION !{C.RESET}" if p.is_neglected() else ""
        print(f"  {C.BOLD}Animal  :{C.RESET} {p.emoji}  {p.name} ({p.species})"
              f"  Faim {bar(p.hunger, length=10)}  Humeur {bar(p.happiness, length=10)}{warn}")
    print()

    if sim.last_event:
        print(sim.last_event)
        print()

    print(f"  {C.BOLD}── Besoins ────────────────────────────{C.RESET}")
    for need in Sim.NEEDS:
        label, emoji = Sim.NEED_LABELS[need]
        val = sim.needs[need]
        warn = f" {C.RED}⚠ CRITIQUE{C.RESET}" if val <= 10 else ""
        print(f"  {emoji} {label:<9}{bar(val)}{warn}")
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
    ("sport",     "Faire du sport (1h)",      None),
    ("mediter",   "Méditer (30 min)",         None),
    ("jardiner",  "Jardiner (2h)",            None),
    ("jeux",      "Jouer aux jeux vidéo (2h)",None),
    ("gastronomie","Cuisiner un plat spécial",None),
    ("adopter",   "Adopter un animal",        None),
    ("nourrir",   "Nourrir l'animal",         None),
    ("jouer_pet", "Jouer avec l'animal",      None),
    ("flirter",   "Flirter / Faire des rencontres", None),
    ("rendezvous","Rendez-vous romantique",   None),
    ("intimite",  "Moment d'intimité",        None),
    ("proposer",  "Demander en mariage",      None),
    ("marier",    "Se marier",                None),
    ("rupture",   "Rompre",                   None),
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
    sim.weather.new_day()
    slow_print(f"  {C.CYAN}Nouveau jour ! Météo : {sim.weather.emoji}  {sim.weather.name}{C.RESET}", 0.02)
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
    meteo_mod = sim.weather.outdoor_mods.get("sortir", 0)
    slow_print(f"\n  {C.MAGENTA}Tu passes la soirée avec des amis ! 🎉{C.RESET}", 0.02)
    if meteo_mod > 0:
        slow_print(f"  {C.GREEN}La météo est parfaite pour sortir ! +{meteo_mod} Fun{C.RESET}", 0.02)
    elif meteo_mod < 0:
        slow_print(f"  {C.RED}La météo n'est pas idéale... {meteo_mod} Fun{C.RESET}", 0.02)
    sim.money -= cost
    sim.modify(fun=40+meteo_mod, social=+50, energie=-20, faim=-15, hygiene=-5)
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
    sim.weather.new_day()
    slow_print(f"  {C.GREEN}+${salary} gagnés ! Total : ${sim.money}{C.RESET}", 0.02)
    slow_print(f"  {C.CYAN}Demain : {sim.weather.emoji}  {sim.weather.name}{C.RESET}", 0.02)
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

def action_sport(sim):
    slow_print(f"\n  {C.GREEN}Tu fais du sport pendant 1 heure... 🏃{C.RESET}", 0.02)
    sim.modify(fun=+20, energie=-25, hygiene=-20, faim=-15, social=+5)
    sim.tick(1)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_mediter(sim):
    slow_print(f"\n  {C.CYAN}Tu médites tranquillement... 🧘{C.RESET}", 0.02)
    sim.modify(energie=+15, fun=+15, social=-5)
    sim.tick(0)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_jardiner(sim):
    meteo_mod = sim.weather.outdoor_mods.get("jardiner", 0)
    slow_print(f"\n  {C.GREEN}Tu jardines pendant 2 heures... 🌱{C.RESET}", 0.02)
    if meteo_mod > 0:
        slow_print(f"  {C.GREEN}Le temps est parfait pour jardiner ! +{meteo_mod} Fun{C.RESET}", 0.02)
    elif meteo_mod < 0:
        slow_print(f"  {C.RED}La météo complique le jardinage... {meteo_mod} Fun{C.RESET}", 0.02)
    sim.modify(fun=25+meteo_mod, energie=-15, hygiene=-15, faim=-10, social=+5)
    sim.tick(2)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_jeux(sim):
    slow_print(f"\n  {C.MAGENTA}Tu joues aux jeux vidéo pendant 2h... 🎮{C.RESET}", 0.02)
    sim.modify(fun=+35, social=-10, energie=-10, faim=-10)
    sim.tick(2)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_gastronomie(sim):
    cost = 20
    if sim.money < cost:
        print(f"\n  {C.RED}Tu n'as pas assez d'argent pour les ingrédients ! (${cost} nécessaires){C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    slow_print(f"\n  {C.YELLOW}Tu prépares un plat gastronomique... 👨‍🍳{C.RESET}", 0.02)
    sim.money -= cost
    sim.modify(faim=+60, fun=+30, hygiene=-5, social=+10)
    sim.tick(2)
    slow_print(f"  {C.GREEN}Quel délice ! -${cost} pour les ingrédients.{C.RESET}", 0.02)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")


def action_adopter(sim):
    if sim.pet:
        print(f"\n  {C.YELLOW}Tu as déjà un animal : {sim.pet.emoji}  {sim.pet.name} !{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    print(f"\n  {C.BOLD}Choisir un animal à adopter :{C.RESET}")
    species_list = list(PET_SPECIES.keys())
    for i, (sp, info) in enumerate(PET_SPECIES.items(), 1):
        print(f"  {C.CYAN}[{i}]{C.RESET} {info['emoji']}  {sp}")
    print(f"  {C.CYAN}[0]{C.RESET} Annuler")
    try:
        choice = int(input("\n  Choix : ").strip())
        if 1 <= choice <= len(species_list):
            sp = species_list[choice - 1]
            pet_name = input(f"  Quel prénom pour ton {sp} ? ").strip()
            if not pet_name:
                pet_name = sp
            sim.pet = Pet(pet_name, sp)
            slow_print(f"\n  {C.GREEN}Félicitations ! {sim.pet.emoji}  {pet_name} rejoint ta famille ! 🎊{C.RESET}", 0.02)
    except ValueError:
        pass
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_nourrir(sim):
    if not sim.pet:
        print(f"\n  {C.YELLOW}Tu n'as pas d'animal. Adoptes-en un d'abord !{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    slow_print(f"\n  {C.YELLOW}Tu nourris {sim.pet.name}... {sim.pet.emoji}{C.RESET}", 0.02)
    sim.pet.feed()
    sim.modify(fun=+5, social=+5)
    slow_print(f"  {C.GREEN}{sim.pet.name} est rassasié(e) ! (Faim : {sim.pet.hunger}%){C.RESET}", 0.02)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_jouer_pet(sim):
    if not sim.pet:
        print(f"\n  {C.YELLOW}Tu n'as pas d'animal. Adoptes-en un d'abord !{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    slow_print(f"\n  {C.MAGENTA}Tu joues avec {sim.pet.name}... {sim.pet.emoji}{C.RESET}", 0.02)
    sim.pet.play()
    sim.modify(fun=+20, social=+10, energie=-5)
    sim.tick(1)
    slow_print(f"  {C.GREEN}{sim.pet.name} est ravi(e) ! (Humeur : {sim.pet.happiness}%){C.RESET}", 0.02)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_flirter(sim):
    rel = sim.relationship
    if rel.is_couple():
        print(f"\n  {C.RED}Tu es déjà en couple avec {rel.partner_name} !{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    slow_print(f"\n  {C.MAGENTA}Tu flirtes et cherches une connexion... 😏{C.RESET}", 0.02)
    sim.modify(social=+20, fun=+15, energie=-5)
    if rel.is_single():
        if random.randint(1, 100) <= 60:
            name = random.choice(PARTNER_NAMES)
            rel.partner_name = name
            rel.level = 1
            rel.affection = 25
            slow_print(f"  {C.GREEN}Tu fais la connaissance de {name} ! 👋{C.RESET}", 0.02)
        else:
            slow_print(f"  {C.YELLOW}Pas de coup de foudre cette fois...{C.RESET}", 0.02)
    else:
        rel.gain_affection(15)
        new_stage = rel.try_advance()
        if new_stage:
            slow_print(f"  {C.GREEN}Ta relation avec {rel.partner_name} évolue : {new_stage} ! 💫{C.RESET}", 0.02)
        else:
            slow_print(f"  {C.CYAN}Bonne ambiance avec {rel.partner_name} ! (Affection {rel.affection}%){C.RESET}", 0.02)
    sim.tick(1)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_rendezvous(sim):
    rel = sim.relationship
    if not rel.has_partner():
        print(f"\n  {C.RED}Tu n'as personne à inviter ! Flirte d'abord.{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    cost = 35
    if sim.money < cost:
        print(f"\n  {C.RED}Pas assez d'argent pour le rendez-vous (${cost} nécessaires).{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    slow_print(f"\n  {C.MAGENTA}Tu passes une soirée romantique avec {rel.partner_name}... 🌹{C.RESET}", 0.02)
    sim.money -= cost
    sim.modify(fun=+35, social=+35, energie=-15, faim=-10)
    rel.gain_affection(25)
    new_stage = rel.try_advance()
    if new_stage:
        slow_print(f"  {C.GREEN}Ta relation évolue : {new_stage} ! 💫{C.RESET}", 0.02)
    else:
        slow_print(f"  {C.CYAN}Belle soirée ! (Affection {rel.affection}%){C.RESET}", 0.02)
    sim.tick(3)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_intimite(sim):
    rel = sim.relationship
    if not rel.is_couple():
        print(f"\n  {C.RED}Tu dois être en couple pour partager ce moment.{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    slow_print(f"\n  {C.MAGENTA}Tu partages un moment d'intimité avec {rel.partner_name}... 💕{C.RESET}", 0.02)
    sim.modify(fun=+25, social=+20, energie=-15, faim=-5)
    rel.gain_affection(12)
    sim.tick(2)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_proposer(sim):
    rel = sim.relationship
    if rel.level != 4:
        print(f"\n  {C.RED}Tu dois être en couple avant de te fiancer !{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    if rel.affection < 75:
        print(f"\n  {C.YELLOW}Votre relation n'est pas encore assez solide... (Affection {rel.affection}% — 75% requise){C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    slow_print(f"\n  {C.MAGENTA}Tu demandes {rel.partner_name} en mariage... 💍{C.RESET}", 0.02)
    if random.randint(1, 100) <= 85:
        rel.level = 5
        rel.affection = 80
        slow_print(f"  {C.GREEN}{rel.partner_name} accepte ! Vous êtes fiancé(e)s ! 💍{C.RESET}", 0.02)
        sim.modify(fun=+40, social=+30)
    else:
        slow_print(f"  {C.RED}{rel.partner_name} hésite encore... Pas encore prêt(e). 😔{C.RESET}", 0.02)
        sim.modify(fun=-10, social=-5)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_marier(sim):
    rel = sim.relationship
    if rel.level != 5:
        print(f"\n  {C.RED}Tu dois être fiancé(e) avant de te marier !{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    cost = 200
    slow_print(f"\n  {C.MAGENTA}La cérémonie de mariage avec {rel.partner_name}... 💒{C.RESET}", 0.02)
    sim.money -= min(cost, sim.money)
    rel.level = 6
    rel.affection = 90
    sim.modify(fun=+50, social=+40, energie=-10)
    slow_print(f"  {C.GREEN}Félicitations ! Vous êtes marié(e)s avec {rel.partner_name} ! 🎊{C.RESET}", 0.02)
    slow_print(f"  {C.GRAY}Coût de la cérémonie : ${cost}{C.RESET}", 0.02)
    input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")

def action_rupture(sim):
    rel = sim.relationship
    if rel.is_single():
        print(f"\n  {C.YELLOW}Tu es déjà célibataire.{C.RESET}")
        input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
        return
    partner = rel.partner_name
    slow_print(f"\n  {C.RED}Tu mets fin à ta relation avec {partner}... 💔{C.RESET}", 0.02)
    rel.breakup()
    sim.modify(fun=-25, social=-20, energie=-10)
    slow_print(f"  {C.GRAY}C'est douloureux, mais la vie continue.{C.RESET}", 0.02)
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
    "travailler":  action_travailler,
    "postuler":    action_postuler,
    "passer":      action_passer,
    "sport":       action_sport,
    "mediter":     action_mediter,
    "jardiner":    action_jardiner,
    "jeux":        action_jeux,
    "gastronomie": action_gastronomie,
    "adopter":     action_adopter,
    "nourrir":     action_nourrir,
    "jouer_pet":   action_jouer_pet,
    "flirter":     action_flirter,
    "rendezvous":  action_rendezvous,
    "intimite":    action_intimite,
    "proposer":    action_proposer,
    "marier":      action_marier,
    "rupture":     action_rupture,
}


# --- Boucle principale ---
def game_loop(sim):
    prev_stage_idx, _ = get_stage(sim.age)

    while True:
        # Détecter un changement de stade de vie
        cur_stage_idx, cur_stage = get_stage(sim.age)
        if cur_stage_idx != prev_stage_idx:
            clear()
            print(f"\n  {C.BOLD}{C.YELLOW}{'═' * 40}{C.RESET}")
            slow_print(f"  {cur_stage[2]}  Nouveau stade de vie : {C.BOLD}{cur_stage[1]}{C.RESET} !", 0.03)
            slow_print(f"  {C.GRAY}{cur_stage[6]}{C.RESET}", 0.03)
            if cur_stage[4]:
                blocked = ", ".join(cur_stage[4])
                slow_print(f"  {C.RED}Interdit : {blocked}{C.RESET}", 0.02)
            if cur_stage[5]:
                auth = ", ".join(cur_stage[5])
                slow_print(f"  {C.YELLOW}Autorisation parentale requise : {auth}{C.RESET}", 0.02)
            print(f"  {C.BOLD}{C.YELLOW}{'═' * 40}{C.RESET}\n")
            input(f"  {C.GRAY}[Entrée pour continuer]{C.RESET}")
            prev_stage_idx = cur_stage_idx

        show_status(sim)

        # Avertissements critiques
        crit = sim.critical_needs()
        if crit:
            labels = [Sim.NEED_LABELS[n][0] for n in crit]
            print(f"  {C.RED}{C.BOLD}⚠  ATTENTION : {', '.join(labels)} en état critique !{C.RESET}")
        if sim.pet and sim.pet.is_neglected():
            print(f"  {C.RED}{C.BOLD}⚠  {sim.pet.name} a besoin de toi ! Faim:{sim.pet.hunger}% Humeur:{sim.pet.happiness}%{C.RESET}")
        if crit or (sim.pet and sim.pet.is_neglected()):
            print()

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
                _, stage = get_stage(sim.age)
                if action_key in stage[4]:
                    # Action complètement bloquée par le stade de vie
                    print(f"\n  {C.RED}Cette action n'est pas disponible à ton stade de vie ({stage[1]}).{C.RESET}")
                    time.sleep(1.5)
                elif action_key in stage[5]:
                    # Action nécessitant une autorisation parentale
                    if ask_parental_auth(sim, stage[1]):
                        ACTION_FNS[action_key](sim)
                        sim.last_event = trigger_random_event(sim)
                    else:
                        sim.last_event = None
                else:
                    ACTION_FNS[action_key](sim)
                    sim.last_event = trigger_random_event(sim)
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

    # Orientation sexuelle
    orientations = ["Hétérosexuel(le)", "Homosexuel(le)", "Bisexuel(le)", "Je préfère ne pas préciser"]
    print(f"\n  {C.BOLD}Quelle est l'orientation sexuelle de {name} ?{C.RESET}")
    for i, o in enumerate(orientations, 1):
        print(f"  {C.CYAN}[{i}]{C.RESET} {o}")
    try:
        o_choice = int(input("\n  Choix : ").strip())
        if 1 <= o_choice <= len(orientations):
            sim.orientation = orientations[o_choice - 1]
    except ValueError:
        pass

    slow_print(f"\n  {C.GREEN}Bienvenue {sim.name} ! Ta vie commence maintenant...{C.RESET}\n", 0.03)
    time.sleep(1)

    game_loop(sim)

    # Score final
    _, final_stage = get_stage(sim.age)
    print(f"\n  {C.BOLD}── Résultats ──────────────────────────{C.RESET}")
    print(f"  Nom     : {sim.name}")
    print(f"  Stade   : {final_stage[2]}  {final_stage[1]}")
    print(f"  Jours   : {sim.age}")
    print(f"  Argent  : ${sim.money}")
    print(f"  Métier  : {sim.job or 'Jamais travaillé'}")
    if sim.pet:
        print(f"  Animal  : {sim.pet.emoji}  {sim.pet.name} ({sim.pet.species})")
    rel = sim.relationship
    if rel.is_single():
        print(f"  Relation : {rel.emoji}  Célibataire")
    else:
        print(f"  Relation : {rel.emoji}  {rel.label} avec {rel.partner_name}")
    print(f"  Humeur  : {sim.mood_label()}\n")


if __name__ == "__main__":
    main()
