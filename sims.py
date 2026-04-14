#!/usr/bin/env python3
"""
Les Sims - Ligne de Commande
Un simulateur de vie en mode texte.
"""

import time
import sys
import os
import random
import json

# --- Mode Autopilote ---
AUTOPILOT = False # True quand l'IA joue à la place du joueur

# --- Couleurs ANSI ---
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def _cont():
    """Pause conditionnelle : rien en autopilote, sinon attend Entrée."""
    if not AUTOPILOT:
        input(f"\n{C.GRAY}Appuie sur Entrée...{C.RESET}")

def bar(value, max_value=100, length=20):
    """Affiche une barre de progression colorée."""
    filled = int(length * value / max_value)
    empty = length - filled
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
LIFE_STAGES = [
    (0, "Enfant", "🧒", {"energie": +2, "fun": -2},
     ["travailler", "postuler", "flirter", "rendezvous", "intimite", "proposer", "marier", "rupture",
      "inscrire", "etudier"],
     ["sortir", "gastronomie", "sport", "jardiner"],
     "Tu découvres le monde !"),
    (5, "Adolescent", "🧑", {"social": -2, "fun": -1},
     ["travailler", "postuler", "intimite", "proposer", "marier",
      "inscrire", "etudier"],
     ["sortir", "rendezvous"],
     "Tu cherches ta voie dans la vie."),
    (10, "Jeune adulte", "💪", {}, [], [], "Tu es dans la fleur de l'âge !"),
    (20, "Adulte", "👔", {"energie": -1}, [], [], "L'expérience guide tes choix."),
    (35, "Senior", "🎩", {"energie": -3, "hygiene": -1}, [], [], "La sagesse et la liberté bien méritées !"),
]

def get_stage(age):
    """Retourne le stade de vie selon le nombre de jours."""
    idx = 0
    for i, (min_day, *_) in enumerate(LIFE_STAGES):
        if age >= min_day:
            idx = i
    return idx, LIFE_STAGES[idx]

def ask_parental_auth(sim, stage_name):
    """Demande l'autorisation parentale."""
    if stage_name == "Enfant":
        base_prob = 55
    else:
        base_prob = 70
    mood_bonus = int((sim.mood - 50) * 0.3)
    prob = max(20, min(90, base_prob + mood_bonus))

    slow_print(f"\n Tu demandes la permission à tes parents... 👨‍👩‍👦", 0.03)
    time.sleep(0.6)
    if random.randint(1, 100) <= prob:
        slow_print(f" {C.GREEN}Tes parents acceptent ! ✓{C.RESET}", 0.03)
        return True
    else:
        slow_print(f" {C.RED}Tes parents refusent. ✗{C.RESET}", 0.03)
        slow_print(f" {C.GRAY}Tu ravales ta déception...{C.RESET}", 0.02)
        sim.modify(fun=-10, social=-5)
        _cont()
        return False

# --- Personnage ---
class Sim:
    NEEDS = ["faim", "energie", "hygiene", "fun", "social", "vessie"]

    NEED_LABELS = {
        "faim": ("Faim", "🍔"),
        "energie": ("Énergie", "💡"),
        "hygiene": ("Hygiène", "🚿"),
        "fun": ("Fun", "🎮"),
        "social": ("Social", "💬"),
        "vessie": ("Vessie", "🚽"),
    }

    def __init__(self, name):
        self.name = name
        self.age = 10
        self.money = 500
        self.job = None
        self.job_days = 0
        self.needs = {
            "faim": 80,
            "energie": 80,
            "hygiene": 70,
            "fun": 60,
            "social": 60,
            "vessie": 80,
        }
        self.mood_history = []
        self.last_event = None
        self.weather = Weather()
        self.pet = None
        self.orientation = "Bisexuel(le)"
        self.relationship = Relationship()
        self.skills = Skills()
        self.children = []
        self.health = Health()
        self.education = Education()

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

    def tick(self, hours=1):
        decay = {
            "faim": -5 * hours,
            "energie": -3 * hours,
            "hygiene": -2 * hours,
            "fun": -4 * hours,
            "social": -3 * hours,
            "vessie": -7 * hours,
        }
        _, stage = get_stage(self.age)
        for need, mod in stage[3].items():
            if need in decay:
                decay[need] += mod * hours
        for need, mod in self.health.decay_mods().items():
            if need in decay:
                decay[need] += mod * hours
        for need, delta in decay.items():
            self.needs[need] = max(0, min(100, self.needs[need] + delta))
        if self.pet:
            self.pet.tick(hours)
        if self.needs["hygiene"] < 20 or self.needs["energie"] < 15:
            self.health.hp = max(0, self.health.hp - hours)
        mental_delta = 0
        if self.needs["fun"] < 25: mental_delta -= 2 * hours
        if self.needs["social"] < 25: mental_delta -= 2 * hours
        if self.needs["fun"] > 70: mental_delta += 1 * hours
        if self.needs["social"] > 70: mental_delta += 1 * hours
        self.health.mental = max(0, min(100, self.health.mental + mental_delta))

    def modify(self, **kwargs):
        for need, delta in kwargs.items():
            if need in self.needs:
                self.needs[need] = max(0, min(100, self.needs[need] + delta))

    def critical_needs(self):
        return [n for n, v in self.needs.items() if v <= 10]

    def is_alive(self):
        return self.needs["faim"] > 0 or self.needs["energie"] > 5

# --- Météo ---
WEATHER_TYPES = [
    ("🌞", "Ensoleillé", {"fun": +5, "energie": +3}, {"sortir": +15, "jardiner": +10}),
    ("⛅", "Nuageux", {}, {"sortir": 0, "jardiner": 0}),
    ("🌧", "Pluvieux", {"hygiene": -5}, {"sortir": -15, "jardiner": -10}),
    ("⛈", "Orageux", {"fun": -5, "energie": -5}, {"sortir": -30, "jardiner": -25}),
    ("🌨", "Enneigé", {"energie": -5}, {"sortir": +5, "jardiner": -20}),
]

class Weather:
    def __init__(self):
        self._data = random.choice(WEATHER_TYPES)

    def new_day(self):
        self._data = random.choice(WEATHER_TYPES)

    @property
    def emoji(self): return self._data[0]
    @property
    def name(self): return self._data[1]
    @property
    def daily_effects(self): return self._data[2]
    @property
    def outdoor_mods(self): return self._data[3]

# --- Animal de compagnie ---
PET_SPECIES = {
    "Chien": {"emoji": "🐶", "hunger_per_h": 4, "happy_per_h": 3},
    "Chat": {"emoji": "🐱", "hunger_per_h": 2, "happy_per_h": 2},
    "Lapin": {"emoji": "🐰", "hunger_per_h": 3, "happy_per_h": 2},
    "Poisson": {"emoji": "🐟", "hunger_per_h": 1, "happy_per_h": 1},
}

class Pet:
    def __init__(self, name, species):
        self.name = name
        self.species = species
        self.hunger = 80
        self.happiness = 80

    @property
    def emoji(self):
        return PET_SPECIES[self.species]["emoji"]

    def tick(self, hours=1):
        info = PET_SPECIES[self.species]
        self.hunger = max(0, self.hunger - info["hunger_per_h"] * hours)
        self.happiness = max(0, self.happiness - info["happy_per_h"] * hours)

    def feed(self):
        self.hunger = min(100, self.hunger + 45)

    def play(self):
        self.happiness = min(100, self.happiness + 40)

    def is_neglected(self):
        return self.hunger <= 20 or self.happiness <= 20

# --- Relations ---
PARTNER_NAMES = ["Alex", "Sam", "Jordan", "Morgan", "Taylor", "Casey", "Robin", "Jamie", "Charlie", "River", "Noa", "Lou"]

class Relationship:
    STAGES = [
        (0, "Célibataire", "💔"),
        (1, "Connaissance", "👋"),
        (2, "Ami(e) proche", "🤝"),
        (3, "Coup de coeur", "💙"),
        (4, "En couple", "💑"),
        (5, "Fiancé(e)", "💍"),
        (6, "Marié(e)", "💒"),
    ]
    THRESHOLDS = {1: 25, 2: 45, 3: 62, 4: 78, 5: 88, 6: 95}

    def __init__(self):
        self.level = 0
        self.partner_name = None
        self.affection = 0

    @property
    def label(self): return self.STAGES[self.level][1]
    @property
    def emoji(self): return self.STAGES[self.level][2]

    def is_single(self): return self.level == 0
    def has_partner(self): return self.level >= 1
    def is_couple(self): return self.level >= 4

    def gain_affection(self, amount):
        self.affection = min(100, self.affection + amount)

    def try_advance(self):
        threshold = self.THRESHOLDS.get(self.level + 1, 999)
        if self.level < 6 and self.affection >= threshold:
            self.level += 1
            self.affection = max(40, self.affection - 20)
            return self.STAGES[self.level][1]
        return None

    def breakup(self):
        self.level = 0
        self.partner_name = None
        self.affection = 0

# --- Compétences ---
SKILLS_DEF = {
    "cuisine": ("Cuisine", "🍳"),
    "sport": ("Sport", "🏃"),
    "social": ("Social", "🗣"),
    "jardinage": ("Jardinage", "🌱"),
    "jeux": ("Jeux", "🎮"),
    "travail": ("Travail", "💼"),
}

class Skills:
    XP_TO_LEVEL = 80
    MAX_LEVEL = 10

    def __init__(self):
        self.levels = {k: 0 for k in SKILLS_DEF}
        self.xp = {k: 0 for k in SKILLS_DEF}

    def gain(self, skill, xp_amount):
        if skill not in self.levels or self.levels[skill] >= self.MAX_LEVEL:
            return None
        self.xp[skill] += xp_amount
        if self.xp[skill] >= self.XP_TO_LEVEL:
            self.levels[skill] += 1
            self.xp[skill] = 0
            return self.levels[skill]
        return None

    def bonus(self, skill):
        return self.levels.get(skill, 0) * 0.1

# --- Famille ---
class Child:
    def __init__(self, name):
        self.name = name
        self.days = 0

    def tick_day(self):
        self.days += 1

    @property
    def age_label(self):
        if self.days < 3: return "Bébé 👶"
        if self.days < 8: return "Enfant 🧒"
        if self.days < 15: return "Ado 🧑"
        return "Adulte 💪"

# --- Santé ---
DISEASES = {
    "rhume": ("Rhume", "🤧", {"energie": -1, "hygiene": -1}, 3, 50),
    "grippe": ("Grippe", "🤒", {"energie": -3, "hygiene": -2, "fun": -2}, 5, 80),
    "burnout": ("Burn-out", "😵", {"energie": -4, "fun": -3, "social": -2}, 7, 120),
    "fracture": ("Fracture", "🦴", {"energie": -2, "fun": -2}, 6, 150),
}

class Health:
    def __init__(self):
        self.hp = 100
        self.mental = 80
        self.diseases = {}

    def get_sick(self, disease_id):
        if disease_id not in self.diseases:
            _, _, _, duration, _ = DISEASES[disease_id]
            self.diseases[disease_id] = duration

    def tick_day(self):
        recovered = [k for k, v in self.diseases.items() if v <= 1]
        for k in recovered:
            del self.diseases[k]
        for k in self.diseases:
            self.diseases[k] -= 1

    def cure_all(self):
        self.diseases.clear()

    def decay_mods(self):
        mods = {}
        for did in self.diseases:
            for need, delta in DISEASES[did][2].items():
                mods[need] = mods.get(need, 0) + delta
        return mods

    def is_sick(self):
        return bool(self.diseases)

    def hp_color(self):
        if self.hp > 60: return C.GREEN
        if self.hp > 30: return C.YELLOW
        return C.RED

    def mental_color(self):
        if self.mental > 60: return C.GREEN
        if self.mental > 30: return C.YELLOW
        return C.RED

# --- Éducation ---
STUDY_DOMAINS = {
    "gastronomie": ("Gastronomie", "🍳", 4, 150),
    "commerce": ("Commerce & Gestion", "💼", 4, 150),
    "arts": ("Arts & Lettres", "🎨", 6, 200),
    "informatique": ("Informatique", "💻", 6, 250),
    "sciences": ("Sciences", "🔬", 6, 250),
    "droit": ("Droit", "⚖", 10, 350),
    "medecine": ("Médecine", "🏥", 10, 400),
    "psychologie": ("Psychologie", "🧠", 8, 280),
    "architecture": ("Architecture", "🏛", 8, 280),
    "communication":("Communication", "📡", 4, 150),
    "finance": ("Finance & Économie", "📈", 6, 250),
    "enseignement": ("Sciences de l'éduc.", "📚", 6, 200),
    "sport_science":("Sciences du Sport", "🏅", 4, 150),
}

GRADE_ORDER = [None, "Passable", "Bien", "Très bien", "Félicitations du jury"]

def grade_from_avg(avg):
    if avg >= 80: return "Félicitations du jury"
    if avg >= 65: return "Très bien"
    if avg >= 50: return "Bien"
    if avg >= 35: return "Passable"
    return None

class Education:
    def __init__(self):
        self.enrolled_domain = None
        self.sessions_done = 0
        self.total_score = 0
        self.diploma_domain = None
        self.grade = None

    def is_enrolled(self):
        return self.enrolled_domain is not None

    def has_diploma(self, domain=None):
        if domain:
            return self.diploma_domain == domain
        return self.diploma_domain is not None

    def sessions_required(self):
        if not self.enrolled_domain:
            return 0
        return STUDY_DOMAINS[self.enrolled_domain][2]

    def grade_ok(self, min_grade):
        if min_grade is None:
            return True
        return GRADE_ORDER.index(self.grade) >= GRADE_ORDER.index(min_grade)

    @property
    def domain_label(self):
        if self.diploma_domain:
            lbl, emoji, _, _ = STUDY_DOMAINS[self.diploma_domain]
            return f"{emoji} {lbl}"
        if self.enrolled_domain:
            lbl, emoji, _, _ = STUDY_DOMAINS[self.enrolled_domain]
            return f"{emoji} {lbl} (en cours)"
        return "Aucune"

# --- Sauvegarde ---
SAVE_FILE = "savegame.json"

# --- Événements aléatoires ---
RANDOM_EVENTS = [
    (8, "💸", "Tu trouves un billet par terre !", {}, +40),
    (6, "🎰", "Tu gagnes un ticket à gratter !", {"fun": +15}, 0),
    (7, "🤝", "Un voisin t'apporte un repas cuisiné.", {"faim": +30, "social": +20}, 0),
    (6, "🎁", "Tu reçois un colis surprise d'un(e) ami(e) !", {"fun": +25, "social": +15}, 0),
    (5, "💼", "Ton patron t'accorde une prime surprise !", {"fun": +10}, +100),
    (8, "📻", "Tu tombes sur ta chanson préférée à la radio.", {"fun": +20, "energie": +5}, 0),
    (6, "🌞", "La météo est magnifique, tu te sens plein(e) d'énergie !", {"energie": +20, "fun": +10}, 0),
    (5, "👫", "Un(e) ami(e) débarque à l'improviste pour papoter.", {"social": +35, "fun": +20}, 0),
    (8, "🤒", "Tu tombes légèrement malade.", {"energie": -25, "hygiene": -20}, 0),
    (6, "🚨", "Tu reçois une facture inattendue !", {"fun": -15}, -75),
    (7, "🥴", "La nourriture était avariée... Tu te sens mal.", {"faim": -20, "energie": -15}, 0),
    (5, "😤", "Grosse dispute avec ton voisin.", {"social": -30, "fun": -15}, 0),
    (6, "⚡", "Panne de courant ! Soirée dans le noir.", {"fun": -20, "energie": -10}, 0),
    (7, "🌧", "Tu t'es fait(e) tremper sous la pluie.", {"hygiene": -25, "energie": -10}, 0),
    (5, "😱", "Un cauchemar t'a réveillé(e) en pleine nuit !", {"energie": -20, "fun": -10}, 0),
    (4, "🦟", "Nuit infernale à cause des moustiques.", {"energie": -15, "fun": -10}, 0),
    (5, "💳", "Tu t'es fait(e) arnaquer en ligne.", {"fun": -20, "social": -10}, -50),
    (5, "🌟", "Ton patron te félicite pour ton excellent travail !", {"fun": +20, "social": +15}, +50),
    (4, "🍀", "Tu trouves un bon de réduction dans ta boîte aux lettres.", {"fun": +10}, +30),
    (6, "🐶", "Un chien adorable croise ton chemin et égaie ta journée.", {"fun": +15, "social": +10}, 0),
    (5, "☕", "Ton café préféré t'offre un verre pour ta fidélité.", {"fun": +10, "energie": +10}, +10),
    (4, "🎶", "Tu composes une petite mélodie spontanée qui te rend heureux(se).", {"fun": +25, "energie": +5}, 0),
    (5, "📦", "Une livraison surprise d'un(e) ami(e) arrive à ta porte.", {"fun": +20, "social": +20}, 0),
    (6, "🚗", "Tu es bloqué(e) dans les embouteillages pendant 1h.", {"fun": -20, "energie": -10}, 0),
    (5, "📵", "Coupure internet pendant plusieurs heures.", {"fun": -25, "social": -15}, 0),
    (4, "👜", "Tu perds ton portefeuille... heureusement vide.", {"fun": -20, "social": -10}, -20),
    (5, "🤧", "Tu attrapes un petit rhume.", {"energie": -20, "hygiene": -15, "fun": -10}, 0),
    (4, "🔑", "Tu t'enfermes dehors et dois appeler un serrurier.", {"fun": -15, "social": -5}, -60),
    (5, "😬", "Tu renverses ton café sur toi au bureau... gênant.", {"hygiene": -20, "fun": -15, "social": -10}, 0),
]

def trigger_random_event(sim):
    for prob, emoji, desc, effects, money in RANDOM_EVENTS:
        if random.randint(1, 100) <= prob:
            actual_money = money
            if emoji == "🎰":
                actual_money = random.randint(10, 80)

            sim.modify(**effects)
            sim.money = max(0, sim.money + actual_money)
            
            if emoji == "🤒":
                sim.health.get_sick("grippe")
                sim.health.hp = max(0, sim.health.hp - 15)
            elif emoji == "🤧":
                sim.health.get_sick("rhume")

            lines = [f"\n {C.BOLD}━━ ÉVÉNEMENT ALÉATOIRE ━━{C.RESET}",
                     f" {emoji} {desc}"]
            if effects:
                parts = []
                for need, delta in effects.items():
                    label = Sim.NEED_LABELS[need][0]
                    sign = "+" if delta >= 0 else ""
                    color = C.GREEN if delta > 0 else C.RED
                    parts.append(f"{color}{sign}{delta} {label}{C.RESET}")
                lines.append(f" Effets : {', '.join(parts)}")
            if actual_money != 0:
                sign = "+" if actual_money >= 0 else ""
                color = C.GREEN if actual_money > 0 else C.RED
                lines.append(f" Argent : {color}{sign}${actual_money}{C.RESET}")

            return "\n".join(lines)
    return None

# --- Affichage ---
def show_status(sim):
    clear()
    print(f"\n{C.BOLD}{C.CYAN}╔══════════════════════════════════════╗{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}║   LES SIMS - LIGNE DE COMMANDE       ║{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}╚══════════════════════════════════════╝{C.RESET}\n")

    _, stage = get_stage(sim.age)
    print(f" {C.BOLD}Sim :{C.RESET} {sim.name} | "
          f"{C.BOLD}Jour :{C.RESET} {sim.age} | "
          f"{C.BOLD}Argent :{C.RESET} {C.GREEN}${sim.money}{C.RESET} | "
          f"{C.BOLD}Humeur :{C.RESET} {sim.mood_label()}")
    print(f" {C.BOLD}Stade :{C.RESET} {stage[2]} {C.YELLOW}{stage[1]}{C.RESET} — {C.GRAY}{stage[6]}{C.RESET}")

    edu = sim.education
    if edu.has_diploma():
        print(f" {C.BOLD}Diplôme :{C.RESET} {C.GREEN}{edu.domain_label}{C.RESET} Mention : {C.YELLOW}{edu.grade}{C.RESET}")
    elif edu.is_enrolled():
        lbl, emoji, sessions, _ = STUDY_DOMAINS[edu.enrolled_domain]
        print(f" {C.BOLD}Études :{C.RESET} {emoji} {lbl} "
              f"Session {edu.sessions_done}/{sessions} "
              f"Moy. {edu.total_score // max(1, edu.sessions_done)}/100")

    if sim.job:
        print(f" {C.BOLD}Travail :{C.RESET} {sim.job} ({sim.job_days} jour(s))")
    else:
        print(f" {C.BOLD}Travail :{C.RESET} {C.GRAY}Chômeur(se){C.RESET}")

    w = sim.weather
    print(f" {C.BOLD}Météo :{C.RESET} {w.emoji} {w.name}", end="")
    if w.daily_effects:
        parts = []
        for need, delta in w.daily_effects.items():
            label = Sim.NEED_LABELS[need][0]
            sign = "+" if delta >= 0 else ""
            color = C.GREEN if delta > 0 else C.RED
            parts.append(f"{color}{sign}{delta} {label}{C.RESET}")
        print(f" ({', '.join(parts)})", end="")
    print()

    rel = sim.relationship
    if rel.is_single():
        print(f" {C.BOLD}Relation :{C.RESET} {rel.emoji} {rel.label} {C.GRAY}({sim.orientation}){C.RESET}")
    else:
        print(f" {C.BOLD}Relation :{C.RESET} {rel.emoji} {rel.label} avec {C.MAGENTA}{rel.partner_name}{C.RESET}"
              f" Affection {bar(rel.affection, length=10)}")

    if sim.pet:
        p = sim.pet
        warn = f" {C.RED}⚠ BESOIN D'ATTENTION !{C.RESET}" if p.is_neglected() else ""
        print(f" {C.BOLD}Animal :{C.RESET} {p.emoji} {p.name} ({p.species})"
              f" Faim {bar(p.hunger, length=10)} Humeur {bar(p.happiness, length=10)}{warn}")
    print()

    if sim.last_event:
        print(sim.last_event)
        print()

    h = sim.health
    hp_bar = bar(h.hp, length=12)
    men_bar = bar(h.mental, length=12)
    print(f" {C.BOLD}Santé :{C.RESET} {h.hp_color()}Physique{C.RESET} {hp_bar} "
          f"{h.mental_color()}Mentale{C.RESET} {men_bar}")
    if h.is_sick():
        sick_str = " ".join(f"{DISEASES[d][1]} {DISEASES[d][0]} ({v}j)" for d, v in h.diseases.items())
        print(f" {C.RED}{C.BOLD} Maladies actives : {sick_str}{C.RESET}")

    if sim.children:
        kids_str = " ".join(f"{c.name} ({c.age_label})" for c in sim.children)
        print(f" {C.BOLD}Famille :{C.RESET} {kids_str}")

    print(f"\n {C.BOLD}── Besoins ────────────────────────────{C.RESET}")
    for need in Sim.NEEDS:
        label, emoji = Sim.NEED_LABELS[need]
        val = sim.needs[need]
        warn = f" {C.RED}⚠ CRITIQUE{C.RESET}" if val <= 10 else ""
        print(f" {emoji} {label:<9}{bar(val)}{warn}")

    active = [(k, v) for k, v in sim.skills.levels.items() if v > 0 or sim.skills.xp[k] > 0]
    if active:
        print(f"\n {C.BOLD}── Compétences ────────────────────────{C.RESET}")
        for skill_id, lv in active:
            label, emoji = SKILLS_DEF[skill_id]
            xp = sim.skills.xp[skill_id]
            print(f" {emoji} {label:<10} Niv.{lv:2d} {bar(xp, max_value=Skills.XP_TO_LEVEL, length=12)}")
    print()

def show_menu(actions):
    current_cat = None
    for i, entry in enumerate(actions, 1):
        key, label, _, cat = entry
        if cat != current_cat:
            current_cat = cat
            print(f"\n {C.BOLD}{C.YELLOW}{cat}{C.RESET}")
        print(f" {C.CYAN}[{i:2d}]{C.RESET} {label}")
    print(f"\n {C.CYAN}[ 0]{C.RESET} Quitter\n")

# --- Actions ---
ACTIONS = [
    ("manger", "Manger (cuisiner)", None, "🍔 Besoins"),
    ("snack", "Grignoter (rapide)", None, "🍔 Besoins"),
    ("dormir", "Dormir (8h)", None, "🍔 Besoins"),
    ("sieste", "Faire une sieste (2h)", None, "🍔 Besoins"),
    ("douche", "Prendre une douche", None, "🍔 Besoins"),
    ("toilettes", "Aller aux toilettes", None, "🍔 Besoins"),
    ("tv", "Regarder la TV", None, "🎮 Loisirs"),
    ("lire", "Lire un livre", None, "🎮 Loisirs"),
    ("sport", "Faire du sport (1h)", None, "🎮 Loisirs"),
    ("mediter", "Méditer (30 min)", None, "🎮 Loisirs"),
    ("jardiner", "Jardiner (2h)", None, "🎮 Loisirs"),
    ("jeux", "Jouer aux jeux vidéo (2h)", None, "🎮 Loisirs"),
    ("gastronomie", "Cuisiner un plat spécial", None, "🎮 Loisirs"),
    ("passer", "Passer le temps (1h)", None, "🎮 Loisirs"),
    ("sortir", "Sortir avec des amis", None, "💬 Social"),
    ("appel", "Appeler quelqu'un", None, "💬 Social"),
    ("travailler", "Aller travailler", None, "💼 Travail & Carrière"),
    ("postuler", "Chercher un emploi", None, "💼 Travail & Carrière"),
    ("inscrire", "S'inscrire à l'université", None, "🎓 Études"),
    ("etudier", "Étudier (session univ.)", None, "🎓 Études"),
    ("medecin", "Consulter un médecin", None, "🏥 Santé"),
    ("medicament", "Prendre des médicaments", None, "🏥 Santé"),
    ("psy", "Voir un psy", None, "🏥 Santé"),
    ("adopter", "Adopter un animal", None, "🐾 Animal"),
    ("nourrir", "Nourrir l'animal", None, "🐾 Animal"),
    ("jouer_pet", "Jouer avec l'animal", None, "🐾 Animal"),
    ("flirter", "Flirter / Faire des rencontres", None, "💕 Vie amoureuse"),
    ("rendezvous", "Rendez-vous romantique", None, "💕 Vie amoureuse"),
    ("intimite", "Moment d'intimité", None, "💕 Vie amoureuse"),
    ("proposer", "Demander en mariage", None, "💕 Vie amoureuse"),
    ("marier", "Se marier", None, "💕 Vie amoureuse"),
    ("rupture", "Rompre", None, "💕 Vie amoureuse"),
    ("avoir_enfant", "Avoir un enfant", None, "👨‍👩‍👧 Famille"),
    ("famille", "Temps en famille", None, "👨‍👩‍👧 Famille"),
    ("sauvegarder", "Sauvegarder la partie", None, "💾 Système"),
]

def action_manger(sim):
    gain = int(40 * (1 + sim.skills.bonus('cuisine')))
    slow_print(f"\n {C.YELLOW}Tu cuisines un bon repas...{C.RESET}", 0.02)
    sim.modify(faim=gain, hygiene=-5, fun=+5)
    sim.tick(1)
    lvl = sim.skills.gain('cuisine', 8)
    if lvl: slow_print(f" {C.GREEN}Compétence Cuisine → Niv. {lvl} ! 🍳{C.RESET}", 0.02)
    _cont()

def action_snack(sim):
    slow_print(f"\n {C.YELLOW}Tu grignottes quelque chose de rapide...{C.RESET}", 0.02)
    sim.modify(faim=+15, fun=-5)
    sim.tick(0)
    _cont()

def action_dormir(sim):
    slow_print(f"\n {C.BLUE}Tu dors profondément pendant 8 heures... 💤{C.RESET}", 0.02)
    sim.modify(energie=+60, hygiene=-10, faim=-20)
    sim.tick(8)
    sim.age += 1
    sim.weather.new_day()
    slow_print(f" {C.CYAN}Nouveau jour ! Météo : {sim.weather.emoji} {sim.weather.name}{C.RESET}", 0.02)
    sim.health.tick_day()
    for child in sim.children:
        child.tick_day()
    _cont()

def action_sieste(sim):
    slow_print(f"\n {C.BLUE}Tu fais une petite sieste de 2h... 😴{C.RESET}", 0.02)
    sim.modify(energie=+20, faim=-5)
    sim.tick(2)
    _cont()

def action_douche(sim):
    slow_print(f"\n {C.CYAN}Tu prends une douche revigorante... 🚿{C.RESET}", 0.02)
    sim.modify(hygiene=+50, energie=+5, social=+5)
    sim.tick(1)
    _cont()

def action_toilettes(sim):
    slow_print(f"\n {C.MAGENTA}Tu vas aux toilettes... 🚽{C.RESET}", 0.02)
    sim.modify(vessie=+80, hygiene=-5)
    sim.tick(0)
    _cont()

def action_tv(sim):
    slow_print(f"\n {C.GREEN}Tu regardes la TV pendant 2h... 📺{C.RESET}", 0.02)
    sim.modify(fun=+25, social=+5, energie=-10, faim=-10)
    sim.tick(2)
    _cont()

def action_lire(sim):
    slow_print(f"\n {C.GREEN}Tu lis un bon livre pendant 2h... 📖{C.RESET}", 0.02)
    sim.modify(fun=+20, energie=-5, faim=-5)
    sim.tick(2)
    _cont()

def action_sortir(sim):
    cost = 30
    if sim.money < cost:
        print(f"\n {C.RED}Tu n'as pas assez d'argent pour sortir ! (${cost} nécessaires){C.RESET}")
        _cont()
        return
    meteo_mod = sim.weather.outdoor_mods.get("sortir", 0)
    soc_gain = int(50 * (1 + sim.skills.bonus('social')))
    slow_print(f"\n {C.MAGENTA}Tu passes la soirée avec des amis ! 🎉{C.RESET}", 0.02)
    if meteo_mod > 0:
        slow_print(f" {C.GREEN}La météo est parfaite pour sortir ! +{meteo_mod} Fun{C.RESET}", 0.02)
    elif meteo_mod < 0:
        slow_print(f" {C.RED}La météo n'est pas idéale... {meteo_mod} Fun{C.RESET}", 0.02)
    sim.money -= cost
    sim.modify(fun=40+meteo_mod, social=soc_gain, energie=-20, faim=-15, hygiene=-5)
    sim.tick(4)
    lvl = sim.skills.gain('social', 8)
    if lvl: slow_print(f" {C.GREEN}Compétence Social → Niv. {lvl} ! 🗣{C.RESET}", 0.02)
    _cont()

def action_appel(sim):
    soc_gain = int(25 * (1 + sim.skills.bonus('social')))
    slow_print(f"\n {C.MAGENTA}Tu appelles un(e) ami(e) pour discuter... 📞{C.RESET}", 0.02)
    sim.modify(social=soc_gain, fun=+10, energie=-5)
    sim.tick(1)
    lvl = sim.skills.gain('social', 5)
    if lvl: slow_print(f" {C.GREEN}Compétence Social → Niv. {lvl} ! 🗣{C.RESET}", 0.02)
    _cont()

JOBS = [
    ("Caissier(ère)", 100, None, None),
    ("Livreur", 150, None, None),
    ("Serveur(se)", 130, None, None),
    ("Plombier", 180, None, None),
    ("Artiste", 120, None, None),
    ("Cuisinier", 220, "gastronomie", "Passable"),
    ("Chef de cuisine", 320, "gastronomie", "Bien"),
    ("Chef étoilé", 500, "gastronomie", "Très bien"),
    ("Comptable", 240, "commerce", "Bien"),
    ("Manager", 280, "commerce", "Passable"),
    ("Dir. commercial", 400, "commerce", "Très bien"),
    ("Graphiste", 190, "arts", "Passable"),
    ("Illustrateur", 250, "arts", "Bien"),
    ("Réalisateur", 420, "arts", "Très bien"),
    ("Développeur", 300, "informatique", "Bien"),
    ("Ingénieur", 430, "informatique", "Très bien"),
    ("Data Scientist", 480, "informatique", "Très bien"),
    ("CTO", 700, "informatique", "Félicitations du jury"),
    ("Technicien labo", 250, "sciences", "Passable"),
    ("Chercheur", 360, "sciences", "Bien"),
    ("Biologiste", 420, "sciences", "Très bien"),
    ("Juriste", 310, "droit", "Bien"),
    ("Avocat", 430, "droit", "Très bien"),
    ("Notaire", 480, "droit", "Très bien"),
    ("Juge", 560, "droit", "Félicitations du jury"),
    ("Infirmier(ère)", 220, "medecine", "Passable"),
    ("Médecin", 450, "medecine", "Bien"),
    ("Chirurgien", 620, "medecine", "Félicitations du jury"),
    ("Conseiller(ère)", 250, "psychologie", "Passable"),
    ("Psychologue", 370, "psychologie", "Bien"),
    ("Psychiatre", 540, "psychologie", "Félicitations du jury"),
    ("Dessinateur", 240, "architecture", "Passable"),
    ("Architecte", 440, "architecture", "Bien"),
    ("Architecte en chef",590, "architecture", "Très bien"),
    ("Chargé(e) commu", 180, "communication", "Passable"),
    ("Journaliste", 260, "communication", "Bien"),
    ("Chef de presse", 380, "communication", "Très bien"),
    ("Conseiller financ.",270, "finance", "Passable"),
    ("Analyste financier",380, "finance", "Bien"),
    ("Banquier", 490, "finance", "Très bien"),
    ("Dir. financier", 680, "finance", "Félicitations du jury"),
    ("Assistant(e) péda.",180, "enseignement", "Passable"),
    ("Enseignant(e)", 230, "enseignement", "Bien"),
    ("Proviseur", 380, "enseignement", "Très bien"),
    ("Animateur sportif",170, "sport_science", "Passable"),
    ("Coach sportif", 240, "sport_science", "Bien"),
    ("Préparateur physique",360,"sport_science", "Très bien"),
]

def jobs_available(edu):
    return [
        (lbl, sal) for lbl, sal, dom, grade in JOBS
        if (dom is None) or (edu.has_diploma(dom) and edu.grade_ok(grade))
    ]

def action_travailler(sim):
    if not sim.job:
        print(f"\n {C.RED}Tu n'as pas de travail ! Postule d'abord.{C.RESET}")
        _cont()
        return
    base_salary = next(sal for lbl, sal, *_ in JOBS if lbl == sim.job)
    salary = int(base_salary * (1 + sim.skills.bonus('travail')))
    slow_print(f"\n {C.YELLOW}Tu travailles toute la journée comme {sim.job}... 💼{C.RESET}", 0.02)
    sim.money += salary
    sim.job_days += 1
    sim.modify(energie=-30, faim=-25, social=+10, hygiene=-10, fun=-15)
    sim.tick(8)
    sim.age += 1
    sim.weather.new_day()
    slow_print(f" {C.GREEN}+${salary} gagnés ! Total : ${sim.money}{C.RESET}", 0.02)
    slow_print(f" {C.CYAN}Demain : {sim.weather.emoji} {sim.weather.name}{C.RESET}", 0.02)
    lvl = sim.skills.gain('travail', 10)
    if lvl: slow_print(f" {C.GREEN}Compétence Travail → Niv. {lvl} ! 💼{C.RESET}", 0.02)
    if sim.needs["energie"] < 15 and sim.needs["fun"] < 15:
        sim.health.get_sick("burnout")
        slow_print(f" {C.RED}Tu fais un burn-out... 😵 Repose-toi !{C.RESET}", 0.02)
    sim.health.tick_day()
    for child in sim.children:
        child.tick_day()
    _cont()

def action_postuler(sim):
    if sim.job:
        print(f"\n {C.YELLOW}Tu as déjà un travail : {sim.job}.{C.RESET}")
        print(f" Veux-tu en changer ? (o/n) ", end="")
        if input().strip().lower() != "o":
            return
    available = jobs_available(sim.education)
    print(f"\n {C.BOLD}Offres d'emploi disponibles :{C.RESET}")
    for i, (name, salary) in enumerate(available, 1):
        print(f" {C.CYAN}[{i}]{C.RESET} {name} — ${salary}/jour")
    locked = [(lbl, sal, dom, grade) for lbl, sal, dom, grade in JOBS
              if dom is not None and not (sim.education.has_diploma(dom) and sim.education.grade_ok(grade))]
    if locked:
        print(f"\n {C.GRAY}Emplois nécessitant un diplôme :{C.RESET}")
        for lbl, sal, dom, grade in locked:
            d_lbl, d_emoji, _, _ = STUDY_DOMAINS[dom]
            print(f" {C.GRAY} {d_emoji} {lbl} (${sal}/j) — {d_lbl}, mention {grade}{C.RESET}")
    print(f"\n {C.CYAN}[0]{C.RESET} Annuler")
    try:
        choice = int(input("\n Choix : ").strip())
        if 1 <= choice <= len(available):
            sim.job = available[choice - 1][0]
            sim.job_days = 0
            slow_print(f"\n {C.GREEN}Félicitations ! Tu es maintenant {sim.job} ! 🎊{C.RESET}", 0.02)
    except ValueError:
        pass
    _cont()

def action_passer(sim):
    slow_print(f"\n {C.GRAY}Une heure passe tranquillement...{C.RESET}", 0.02)
    sim.tick(1)
    _cont()

def action_sport(sim):
    fun_gain = int(20 * (1 + sim.skills.bonus('sport')))
    energie_cost = max(10, int(25 * (1 - sim.skills.bonus('sport') * 0.5)))
    slow_print(f"\n {C.GREEN}Tu fais du sport pendant 1 heure... 🏃{C.RESET}", 0.02)
    sim.modify(fun=fun_gain, energie=-energie_cost, hygiene=-20, faim=-15, social=+5)
    sim.tick(1)
    lvl = sim.skills.gain('sport', 10)
    if lvl: slow_print(f" {C.GREEN}Compétence Sport → Niv. {lvl} ! 🏃{C.RESET}", 0.02)
    _, stage = get_stage(sim.age)
    fracture_risk = 20 if stage[1] == "Senior" else (10 if sim.needs["energie"] < 20 else 0)
    if fracture_risk and random.randint(1, 100) <= fracture_risk:
        sim.health.get_sick("fracture")
        slow_print(f" {C.RED}Aïe ! Tu t'es blessé(e)... 🦴 Fracture !{C.RESET}", 0.02)
    _cont()

def action_mediter(sim):
    slow_print(f"\n {C.CYAN}Tu médites tranquillement... 🧘{C.RESET}", 0.02)
    sim.modify(energie=+15, fun=+15, social=-5)
    sim.tick(0)
    _cont()

def action_jardiner(sim):
    meteo_mod = sim.weather.outdoor_mods.get("jardiner", 0)
    fun_gain = int(25 * (1 + sim.skills.bonus('jardinage')))
    slow_print(f"\n {C.GREEN}Tu jardines pendant 2 heures... 🌱{C.RESET}", 0.02)
    if meteo_mod > 0:
        slow_print(f" {C.GREEN}Le temps est parfait pour jardiner ! +{meteo_mod} Fun{C.RESET}", 0.02)
    elif meteo_mod < 0:
        slow_print(f" {C.RED}La météo complique le jardinage... {meteo_mod} Fun{C.RESET}", 0.02)
    sim.modify(fun=fun_gain+meteo_mod, energie=-15, hygiene=-15, faim=-10, social=+5)
    sim.tick(2)
    lvl = sim.skills.gain('jardinage', 8)
    if lvl: slow_print(f" {C.GREEN}Compétence Jardinage → Niv. {lvl} ! 🌱{C.RESET}", 0.02)
    _cont()

def action_jeux(sim):
    fun_gain = int(35 * (1 + sim.skills.bonus('jeux')))
    slow_print(f"\n {C.MAGENTA}Tu joues aux jeux vidéo pendant 2h... 🎮{C.RESET}", 0.02)
    sim.modify(fun=fun_gain, social=-10, energie=-10, faim=-10)
    sim.tick(2)
    lvl = sim.skills.gain('jeux', 8)
    if lvl: slow_print(f" {C.GREEN}Compétence Jeux → Niv. {lvl} ! 🎮{C.RESET}", 0.02)
    _cont()

def action_gastronomie(sim):
    cost = 20
    if sim.money < cost:
        print(f"\n {C.RED}Tu n'as pas assez d'argent pour les ingrédients ! (${cost} nécessaires){C.RESET}")
        _cont()
        return
    faim_gain = int(60 * (1 + sim.skills.bonus('cuisine')))
    fun_gain = int(30 * (1 + sim.skills.bonus('cuisine')))
    slow_print(f"\n {C.YELLOW}Tu prépares un plat gastronomique... 👨‍🍳{C.RESET}", 0.02)
    sim.money -= cost
    sim.modify(faim=faim_gain, fun=fun_gain, hygiene=-5, social=+10)
    sim.tick(2)
    slow_print(f" {C.GREEN}Quel délice ! -${cost} pour les ingrédients.{C.RESET}", 0.02)
    lvl = sim.skills.gain('cuisine', 12)
    if lvl: slow_print(f" {C.GREEN}Compétence Cuisine → Niv. {lvl} ! 🍳{C.RESET}", 0.02)
    _cont()

def action_adopter(sim):
    if sim.pet:
        print(f"\n {C.YELLOW}Tu as déjà un animal : {sim.pet.emoji} {sim.pet.name} !{C.RESET}")
        _cont()
        return
    print(f"\n {C.BOLD}Choisir un animal à adopter :{C.RESET}")
    species_list = list(PET_SPECIES.keys())
    for i, (sp, info) in enumerate(PET_SPECIES.items(), 1):
        print(f" {C.CYAN}[{i}]{C.RESET} {info['emoji']} {sp}")
    print(f" {C.CYAN}[0]{C.RESET} Annuler")
    try:
        choice = int(input("\n Choix : ").strip())
        if 1 <= choice <= len(species_list):
            sp = species_list[choice - 1]
            pet_name = input(f" Quel prénom pour ton {sp} ? ").strip()
            if not pet_name:
                pet_name = sp
            sim.pet = Pet(pet_name, sp)
            slow_print(f"\n {C.GREEN}Félicitations ! {sim.pet.emoji} {pet_name} rejoint ta famille ! 🎊{C.RESET}", 0.02)
    except ValueError:
        pass
    _cont()

def action_nourrir(sim):
    if not sim.pet:
        print(f"\n {C.YELLOW}Tu n'as pas d'animal. Adoptes-en un d'abord !{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.YELLOW}Tu nourris {sim.pet.name}... {sim.pet.emoji}{C.RESET}", 0.02)
    sim.pet.feed()
    sim.modify(fun=+5, social=+5)
    slow_print(f" {C.GREEN}{sim.pet.name} est rassasié(e) ! (Faim : {sim.pet.hunger}%){C.RESET}", 0.02)
    _cont()

def action_jouer_pet(sim):
    if not sim.pet:
        print(f"\n {C.YELLOW}Tu n'as pas d'animal. Adoptes-en un d'abord !{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.MAGENTA}Tu joues avec {sim.pet.name}... {sim.pet.emoji}{C.RESET}", 0.02)
    sim.pet.play()
    sim.modify(fun=+20, social=+10, energie=-5)
    sim.tick(1)
    slow_print(f" {C.GREEN}{sim.pet.name} est ravi(e) ! (Humeur : {sim.pet.happiness}%){C.RESET}", 0.02)
    _cont()

def action_medecin(sim):
    cost = 80
    if sim.money < cost:
        print(f"\n {C.RED}Pas assez d'argent pour le médecin (${cost}).{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.CYAN}Tu consultes un médecin... 👨‍⚕️{C.RESET}", 0.02)
    sim.money -= cost
    sim.health.hp = min(100, sim.health.hp + 30)
    sim.health.cure_all()
    sim.modify(energie=+10)
    slow_print(f" {C.GREEN}Toutes tes maladies sont soignées ! Santé +30. (-${cost}){C.RESET}", 0.02)
    sim.tick(1)
    _cont()

def action_medicament(sim):
    cost = 20
    if sim.money < cost:
        print(f"\n {C.RED}Pas assez d'argent pour les médicaments (${cost}).{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.YELLOW}Tu prends des médicaments... 💊{C.RESET}", 0.02)
    sim.money -= cost
    sim.health.hp = min(100, sim.health.hp + 10)
    for d in sim.health.diseases:
        sim.health.diseases[d] = max(1, sim.health.diseases[d] - 1)
    slow_print(f" {C.GREEN}Santé +10, maladies accélérées. (-${cost}){C.RESET}", 0.02)
    _cont()

def action_psy(sim):
    cost = 60
    if sim.money < cost:
        print(f"\n {C.RED}Pas assez d'argent pour la séance (${cost}).{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.MAGENTA}Tu parles avec ton psy... 🛋{C.RESET}", 0.02)
    sim.money -= cost
    sim.health.mental = min(100, sim.health.mental + 35)
    sim.modify(fun=+15, social=+10)
    slow_print(f" {C.GREEN}Santé mentale +35. Tu te sens mieux. (-${cost}){C.RESET}", 0.02)
    sim.tick(1)
    _cont()

CHILD_NAMES = ["Emma", "Léo", "Jade", "Noah", "Inès", "Lucas", "Chloé", "Tom", "Manon", "Hugo"]

def action_avoir_enfant(sim):
    if sim.relationship.level < 6:
        print(f"\n {C.RED}Tu dois être marié(e) pour avoir un enfant.{C.RESET}")
        _cont()
        return
    if len(sim.children) >= 4:
        print(f"\n {C.YELLOW}Vous avez déjà une grande famille ({len(sim.children)} enfants) !{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.MAGENTA}Vous attendez un heureux événement... 🍼{C.RESET}", 0.02)
    name = random.choice([n for n in CHILD_NAMES if not any(c.name == n for c in sim.children)])
    child = Child(name)
    sim.children.append(child)
    sim.modify(fun=+30, social=+20, energie=-20)
    slow_print(f" {C.GREEN}Bienvenue petit(e) {name} ! 👶{C.RESET}", 0.02)
    _cont()

def action_famille(sim):
    if not sim.children:
        print(f"\n {C.YELLOW}Tu n'as pas encore d'enfants.{C.RESET}")
        _cont()
        return
    kids = ", ".join(c.name for c in sim.children)
    slow_print(f"\n {C.GREEN}Tu passes du temps en famille avec {kids}... 👨‍👩‍👧‍👦{C.RESET}", 0.02)
    sim.modify(fun=+25, social=+30, energie=-10)
    sim.tick(2)
    _cont()

def action_sauvegarder(sim):
    data = {
        "name": sim.name, "age": sim.age, "money": sim.money,
        "job": sim.job, "job_days": sim.job_days, "needs": sim.needs,
        "orientation": sim.orientation,
        "relationship": {
            "level": sim.relationship.level,
            "partner_name": sim.relationship.partner_name,
            "affection": sim.relationship.affection,
        },
        "pet": {"name": sim.pet.name, "species": sim.pet.species,
                "hunger": sim.pet.hunger, "happiness": sim.pet.happiness
                } if sim.pet else None,
        "weather_idx": WEATHER_TYPES.index(sim.weather._data),
        "skills": {"levels": sim.skills.levels, "xp": sim.skills.xp},
        "children": [{"name": c.name, "days": c.days} for c in sim.children],
        "health": {"hp": sim.health.hp, "mental": sim.health.mental, "diseases": sim.health.diseases},
        "education": {
            "enrolled_domain": sim.education.enrolled_domain,
            "sessions_done": sim.education.sessions_done,
            "total_score": sim.education.total_score,
            "diploma_domain": sim.education.diploma_domain,
            "grade": sim.education.grade,
        },
    }
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    slow_print(f"\n {C.GREEN}Partie sauvegardée dans {SAVE_FILE} ! 💾{C.RESET}", 0.02)
    _cont()

def action_flirter(sim):
    rel = sim.relationship
    if rel.is_couple():
        print(f"\n {C.RED}Tu es déjà en couple avec {rel.partner_name} !{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.MAGENTA}Tu flirtes et cherches une connexion... 😏{C.RESET}", 0.02)
    sim.modify(social=+20, fun=+15, energie=-5)
    if rel.is_single():
        if random.randint(1, 100) <= 60:
            name = random.choice(PARTNER_NAMES)
            rel.partner_name = name
            rel.level = 1
            rel.affection = 25
            slow_print(f" {C.GREEN}Tu fais la connaissance de {name} ! 👋{C.RESET}", 0.02)
        else:
            slow_print(f" {C.YELLOW}Pas de coup de foudre cette fois...{C.RESET}", 0.02)
    else:
        rel.gain_affection(15)
        new_stage = rel.try_advance()
        if new_stage:
            slow_print(f" {C.GREEN}Ta relation avec {rel.partner_name} évolue : {new_stage} ! 💫{C.RESET}", 0.02)
        else:
            slow_print(f" {C.CYAN}Bonne ambiance avec {rel.partner_name} ! (Affection {rel.affection}%){C.RESET}", 0.02)
    sim.tick(1)
    _cont()

def action_rendezvous(sim):
    rel = sim.relationship
    if not rel.has_partner():
        print(f"\n {C.RED}Tu n'as personne à inviter ! Flirte d'abord.{C.RESET}")
        _cont()
        return
    cost = 35
    if sim.money < cost:
        print(f"\n {C.RED}Pas assez d'argent pour le rendez-vous (${cost} nécessaires).{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.MAGENTA}Tu passes une soirée romantique avec {rel.partner_name}... 🌹{C.RESET}", 0.02)
    sim.money -= cost
    sim.modify(fun=+35, social=+35, energie=-15, faim=-10)
    rel.gain_affection(25)
    new_stage = rel.try_advance()
    if new_stage:
        slow_print(f" {C.GREEN}Ta relation évolue : {new_stage} ! 💫{C.RESET}", 0.02)
    else:
        slow_print(f" {C.CYAN}Belle soirée ! (Affection {rel.affection}%){C.RESET}", 0.02)
    sim.tick(3)
    _cont()

def action_intimite(sim):
    rel = sim.relationship
    if not rel.is_couple():
        print(f"\n {C.RED}Tu dois être en couple pour partager ce moment.{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.MAGENTA}Tu partages un moment d'intimité avec {rel.partner_name}... 💕{C.RESET}", 0.02)
    sim.modify(fun=+25, social=+20, energie=-15, faim=-5)
    rel.gain_affection(12)
    sim.tick(2)
    _cont()

def action_proposer(sim):
    rel = sim.relationship
    if rel.level != 4:
        print(f"\n {C.RED}Tu dois être en couple avant de te fiancer !{C.RESET}")
        _cont()
        return
    if rel.affection < 75:
        print(f"\n {C.YELLOW}Votre relation n'est pas encore assez solide... (Affection {rel.affection}% — 75% requise){C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.MAGENTA}Tu demandes {rel.partner_name} en mariage... 💍{C.RESET}", 0.02)
    if random.randint(1, 100) <= 85:
        rel.level = 5
        rel.affection = 80
        slow_print(f" {C.GREEN}{rel.partner_name} accepte ! Vous êtes fiancé(e)s ! 💍{C.RESET}", 0.02)
        sim.modify(fun=+40, social=+30)
    else:
        slow_print(f" {C.RED}{rel.partner_name} hésite encore... Pas encore prêt(e). 😔{C.RESET}", 0.02)
        sim.modify(fun=-10, social=-5)
    _cont()

def action_marier(sim):
    rel = sim.relationship
    if rel.level != 5:
        print(f"\n {C.RED}Tu dois être fiancé(e) avant de te marier !{C.RESET}")
        _cont()
        return
    cost = 200
    slow_print(f"\n {C.MAGENTA}La cérémonie de mariage avec {rel.partner_name}... 💒{C.RESET}", 0.02)
    sim.money -= min(cost, sim.money)
    rel.level = 6
    rel.affection = 90
    sim.modify(fun=+50, social=+40, energie=-10)
    slow_print(f" {C.GREEN}Félicitations ! Vous êtes marié(e)s avec {rel.partner_name} ! 🎊{C.RESET}", 0.02)
    slow_print(f" {C.GRAY}Coût de la cérémonie : ${cost}{C.RESET}", 0.02)
    _cont()

def action_rupture(sim):
    rel = sim.relationship
    if rel.is_single():
        print(f"\n {C.YELLOW}Tu es déjà célibataire.{C.RESET}")
        _cont()
        return
    partner = rel.partner_name
    slow_print(f"\n {C.RED}Tu mets fin à ta relation avec {partner}... 💔{C.RESET}", 0.02)
    rel.breakup()
    sim.modify(fun=-25, social=-20, energie=-10)
    slow_print(f" {C.GRAY}C'est douloureux, mais la vie continue.{C.RESET}", 0.02)
    _cont()

def _study_session_score(sim):
    base = 50
    base += (sim.needs["fun"] - 50) * 0.2
    base += (sim.needs["energie"] - 50) * 0.3
    base += sim.skills.levels.get("travail", 0) * 2
    base += sim.skills.levels.get("social", 0) * 1
    base += random.randint(-15, 15)
    return max(0, min(100, int(base)))

def action_inscrire(sim):
    edu = sim.education
    if edu.is_enrolled():
        lbl, emoji, sessions, cost = STUDY_DOMAINS[edu.enrolled_domain]
        print(f"\n {C.YELLOW}Tu es déjà inscrit(e) en {lbl} ({edu.sessions_done}/{sessions} sessions).{C.RESET}")
        _cont()
        return
    if edu.has_diploma():
        print(f"\n {C.GREEN}Tu as déjà un diplôme : {edu.domain_label} (Mention : {edu.grade}){C.RESET}")
        print(f" Veux-tu faire un autre cursus ? (o/n) ", end="")
        if input().strip().lower() != "o":
            return

    print(f"\n {C.BOLD}Choisir un domaine d'études :{C.RESET}")
    domains = list(STUDY_DOMAINS.items())
    for i, (key, (lbl, emoji, sessions, cost)) in enumerate(domains, 1):
        print(f" {C.CYAN}[{i}]{C.RESET} {emoji} {lbl:<22} {sessions} sessions ${cost}/session")
    print(f" {C.CYAN}[0]{C.RESET} Annuler")
    try:
        choice = int(input("\n Choix : ").strip())
        if 1 <= choice <= len(domains):
            key, (lbl, emoji, sessions, cost) = domains[choice - 1]
            if sim.money < cost:
                print(f"\n {C.RED}Pas assez d'argent pour la première session ! (${cost} nécessaires){C.RESET}")
                _cont()
                return
            sim.money -= cost
            edu.enrolled_domain = key
            edu.sessions_done = 1
            edu.total_score = _study_session_score(sim)
            slow_print(f"\n {C.GREEN}Tu t'inscris en {lbl} ! Première session effectuée. {emoji}{C.RESET}", 0.02)
            slow_print(f" {C.GRAY}{sessions} sessions au total, ${cost}/session{C.RESET}", 0.02)
            slow_print(f" {C.CYAN}Progression : {edu.sessions_done}/{sessions}{C.RESET}", 0.02)
            sim.tick(4)
    except ValueError:
        pass
    _cont()

def action_etudier(sim):
    edu = sim.education
    if not edu.is_enrolled():
        print(f"\n {C.YELLOW}Tu n'es pas inscrit(e) à l'université. Inscris-toi d'abord !{C.RESET}")
        _cont()
        return
    lbl, emoji, sessions, cost = STUDY_DOMAINS[edu.enrolled_domain]
    if sim.money < cost:
        print(f"\n {C.RED}Pas assez d'argent pour cette session (${cost} nécessaires).{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.CYAN}Tu étudies en {lbl}... {emoji}{C.RESET}", 0.02)
    sim.money -= cost
    score = _study_session_score(sim)
    edu.sessions_done += 1
    edu.total_score += score
    sim.modify(energie=-20, fun=-10, faim=-15, social=-5)
    sim.tick(6)
    slow_print(f" Session {edu.sessions_done}/{sessions} terminée ! Score : {score}/100 "
               f"(Moy. courante : {edu.total_score // edu.sessions_done}/100)", 0.02)
    lvl = sim.skills.gain('travail', 5)
    if lvl:
        slow_print(f" {C.GREEN}Compétence Travail → Niv. {lvl} ! 💼{C.RESET}", 0.02)

    if edu.sessions_done >= sessions:
        avg = edu.total_score / sessions
        grade = grade_from_avg(avg)
        print()
        if grade:
            edu.diploma_domain = edu.enrolled_domain
            edu.grade = grade
            edu.enrolled_domain = None
            slow_print(f" {C.BOLD}{C.YELLOW}🎓 Félicitations ! Tu obtiens ton diplôme en {lbl} !{C.RESET}", 0.03)
            slow_print(f" {C.GREEN}Mention : {grade} (Moyenne : {avg:.0f}/100){C.RESET}", 0.03)
            slow_print(f" {C.CYAN}De nouveaux emplois s'ouvrent à toi !{C.RESET}", 0.02)
            sim.modify(fun=+20, social=+10)
        else:
            edu.enrolled_domain = None
            edu.sessions_done = 0
            edu.total_score = 0
            slow_print(f" {C.RED}Tu n'as pas obtenu le diplôme en {lbl}. (Moyenne : {avg:.0f}/100 — minimum 35){C.RESET}", 0.03)
            slow_print(f" {C.YELLOW}Tu peux te réinscrire et réessayer.{C.RESET}", 0.02)
            sim.modify(fun=-15)
    _cont()

ACTION_FNS = {
    "manger": action_manger,
    "snack": action_snack,
    "dormir": action_dormir,
    "sieste": action_sieste,
    "douche": action_douche,
    "toilettes": action_toilettes,
    "tv": action_tv,
    "lire": action_lire,
    "sortir": action_sortir,
    "appel": action_appel,
    "travailler": action_travailler,
    "postuler": action_postuler,
    "passer": action_passer,
    "sport": action_sport,
    "mediter": action_mediter,
    "jardiner": action_jardiner,
    "jeux": action_jeux,
    "gastronomie": action_gastronomie,
    "adopter": action_adopter,
    "nourrir": action_nourrir,
    "jouer_pet": action_jouer_pet,
    "flirter": action_flirter,
    "rendezvous": action_rendezvous,
    "intimite": action_intimite,
    "proposer": action_proposer,
    "marier": action_marier,
    "rupture": action_rupture,
    "avoir_enfant": action_avoir_enfant,
    "famille": action_famille,
    "sauvegarder": action_sauvegarder,
    "medecin": action_medecin,
    "medicament": action_medicament,
    "psy": action_psy,
    "inscrire": action_inscrire,
    "etudier": action_etudier,
}

# --- IA Autopilote ---
_AUTO_NAMES = ["Camille", "Alex", "Jordan", "Morgan", "Sam", "Robin",
               "Léa", "Noah", "Inès", "Lucas", "Jade", "Tom"]

def ai_choose_action(sim):
    """CORRIGÉ - Retourne la clé d'action que l'IA choisit selon les priorités du Sim."""
    _, stage = get_stage(sim.age)
    blocked = set(stage[4])
    n = sim.needs

    # — Priorité 1 : besoins critiques —
    if n["vessie"] < 20: 
        return "toilettes"
    if n["faim"] < 25 and "manger" not in blocked:
        return "snack" if sim.money < 20 else "manger"
    # CORRECTION: Seuil augmenté à 30% (était 20%) pour dormir avant le crash
    if n["energie"] < 30: 
        return "dormir"
    if n["hygiene"] < 25: 
        return "douche"

    # — Priorité 2 : santé (préventive et curative) —
    h = sim.health
    if h.hp < 30 and sim.money >= 80:                                 return "medecin"
    if h.hp < 55 and sim.money >= 20:                                 return "medicament"
    if h.mental < 50 and sim.money >= 60 and random.random() < 0.35: return "psy"
    if h.is_sick() and sim.money >= 20:                               return "medicament"

    # — Priorité 3 : animal —
    if sim.pet and sim.pet.hunger    < 30:                            return "nourrir"
    if sim.pet and sim.pet.happiness < 30:                            return "jouer_pet"
    if (not sim.pet and "adopter" not in blocked
            and sim.money > 200 and random.random() < 0.05):          return "adopter"

    # — Priorité 4 : PRÉVENTION DU BURN-OUT —
    # Si énergie faible mais pas critique, sieste rapide
    if 30 <= n["energie"] < 50 and "sieste" not in blocked:
        return "sieste"
    
    # Si fun très bas, récupération obligatoire avant toute activité stressante
    if n["fun"] < 35:
        if "mediter" not in blocked:
            return "mediter"
        if "tv" not in blocked:
            return "tv"
        if "jeux" not in blocked:
            return "jeux"

    # — Priorité 5 : carrière / études —
    if "travailler" not in blocked:
        edu = sim.education

        # Postuler / inscrire ne coûtent pas d'énergie → toujours autorisés
        if sim.job and random.random() < 0.10:
            best = max(jobs_available(edu), key=lambda x: x[1], default=None)
            if best:
                cur_sal = next((s for lb, s, *_ in JOBS if lb == sim.job), 0)
                if best[1] > cur_sal:
                    return "postuler"
        if not sim.job and jobs_available(edu):
            return "postuler"
        if (not edu.is_enrolled() and not edu.has_diploma()
                and sim.money > 600 and random.random() < 0.30):
            return "inscrire"
        if (not edu.is_enrolled() and edu.has_diploma()
                and sim.money > 800 and random.random() < 0.15):
            return "inscrire"

        # Travailler / étudier nécessitent un minimum d'énergie et de fun
        # Seuils réalistes : énergie ≥ 45, fun ≥ 25
        peut_bosser = n["energie"] >= 45 and n["fun"] >= 25
        if peut_bosser:
            if edu.is_enrolled():
                cost = STUDY_DOMAINS[edu.enrolled_domain][3]
                if sim.money >= cost:
                    return "etudier"
                elif sim.job:
                    return "travailler"
            if sim.job:
                return "travailler"
        else:
            # Récupération prioritaire avant de travailler
            if n["energie"] < 45:
                return "sieste" if n["energie"] > 25 else "dormir"
            if n["fun"] < 25:
                return "mediter" if "mediter" not in blocked else "tv"

    # — Priorité 6 : vie amoureuse —
    if "flirter" not in blocked:
        rel = sim.relationship
        if rel.is_single() and random.random() < 0.25:
            return "flirter"
        if rel.has_partner() and not rel.is_couple():
            if sim.money >= 35 and random.random() < 0.40:
                return "rendezvous"
            return "flirter"
        if rel.is_couple() and rel.affection < 90 and random.random() < 0.30:
            return "intimite"
        if rel.level == 4 and rel.affection >= 75 and random.random() < 0.50:
            return "proposer"
        if rel.level == 5 and sim.money >= 200 and random.random() < 0.50:
            return "marier"

    # — Priorité 7 : famille —
    if ("avoir_enfant" not in blocked
        and sim.relationship.level == 6
        and len(sim.children) < 3
        and random.random() < 0.15):
        return "avoir_enfant"
    if sim.children and random.random() < 0.20:
        return "famille"

    # — Priorité 8 : loisirs selon besoins (équilibrage quotidien) —
    pool = []
    if n["energie"] > 50:  # CORRECTION: Seuil augmenté pour garder réserve d'énergie
        pool += ["sport", "jardiner"]
    if n["fun"] < 60:
        pool += ["jeux", "tv", "lire", "mediter"]
        if sim.money >= 20 and sim.skills.levels.get("cuisine", 0) > 0:
            pool += ["gastronomie"]
    if n["social"] < 50:
        pool += ["appel"]
    if sim.money >= 30 and n["fun"] < 70:  # Sortir seulement si besoin de fun
        pool += ["sortir"]
    if not pool:
        pool = ["mediter", "passer", "lire"]  # Activités douces par défaut
    pool = [a for a in pool if a not in blocked]
    return random.choice(pool) if pool else "passer"

_AUTO_PET_NAMES = ["Fido", "Minou", "Noisette", "Caramel", "Bulle", "Pixel", "Grizou", "Luna"]

def ai_auto_postuler(sim):
    """Choisit automatiquement le meilleur job disponible (ou change si mieux payé)."""
    available = jobs_available(sim.education)
    if not available:
        return
    best = max(available, key=lambda x: x[1])
    if sim.job == best[0]:
        return
    sim.job = best[0]
    sim.job_days = 0
    slow_print(f"  {C.GREEN}[IA] Embauché(e) comme {sim.job} (${best[1]}/j) 💼{C.RESET}", 0.02)


def ai_auto_adopter(sim):
    """Adopte automatiquement un animal aléatoire."""
    if sim.pet:
        return
    species  = random.choice(list(PET_SPECIES.keys()))
    pet_name = random.choice(_AUTO_PET_NAMES)
    sim.pet  = Pet(pet_name, species)
    slow_print(f"  {C.GREEN}[IA] {sim.pet.emoji} {pet_name} le {species} rejoint la famille !{C.RESET}", 0.02)

def ai_auto_inscrire(sim):
    """Choisit automatiquement le domaine d'études le plus rentable accessible."""
    best_domain = None
    best_salary = 0
    for key, (lbl, emoji, sessions, cost) in STUDY_DOMAINS.items():
        if sim.money < cost:
            continue
        for jlbl, jsal, dom, grade in JOBS:
            if dom == key and grade in (None, "Passable", "Bien"):
                if jsal > best_salary:
                    best_salary = jsal
                    best_domain = key
    if best_domain is None:
        affordable = [(k, v) for k, v in STUDY_DOMAINS.items() if sim.money >= v[3]]
        if not affordable:
            return
        best_domain = min(affordable, key=lambda x: x[1][3])[0]
    lbl, emoji, sessions, cost = STUDY_DOMAINS[best_domain]
    sim.money -= cost
    sim.education.enrolled_domain = best_domain
    sim.education.sessions_done = 1
    sim.education.total_score = _study_session_score(sim)
    slow_print(f" {C.GREEN}[IA] Inscrit(e) en {lbl} {emoji} ({sessions} sessions){C.RESET}", 0.02)
    sim.tick(4)

def autopilot_loop(sim, speed=0.8):
    """Boucle de jeu autonome — l'IA prend toutes les décisions."""
    global AUTOPILOT
    AUTOPILOT = True

    prev_stage_idx, _ = get_stage(sim.age)
    last_age_checked = sim.age - 1

    try:
        while True:
            # — Mort naturelle —
            if sim.age > last_age_checked and sim.age >= 45:
                last_age_checked = sim.age
                death_prob = min(35, (sim.age - 43) * 3)
                if random.randint(1, 100) <= death_prob:
                    clear()
                    slow_print(f"\n 🕯 {sim.name} s'est endormi(e) paisiblement à {sim.age} jours...", 0.03)
                    return "vieillesse"

            # — Changement de stade —
            cur_stage_idx, cur_stage = get_stage(sim.age)
            if cur_stage_idx != prev_stage_idx:
                clear()
                slow_print(f"\n {cur_stage[2]} {sim.name} entre dans le stade : {C.BOLD}{cur_stage[1]}{C.RESET}", 0.03)
                prev_stage_idx = cur_stage_idx
                time.sleep(speed)

            show_status(sim)

            # — Morts par besoins / santé —
            if sim.needs["faim"] == 0 and sim.needs["energie"] == 0:
                slow_print(f"\n {C.RED}💀 {sim.name} est mort(e) d'épuisement après {sim.age} jour(s).{C.RESET}", 0.02)
                return "famine"
            if sim.health.hp <= 0:
                slow_print(f"\n {C.RED}💀 {sim.name} est décédé(e) des suites de sa santé.{C.RESET}", 0.02)
                return "santé"

            # — Décision IA —
            action_key = ai_choose_action(sim)
            _, stage = get_stage(sim.age)

            # Actions bloquées → dormir par défaut
            if action_key in stage[4]:
                action_key = "dormir"

            # Remplacer les actions interactives par leurs variantes IA
            if action_key == "postuler":
                ai_auto_postuler(sim)
                sim.last_event = trigger_random_event(sim)
                time.sleep(speed)
                continue
            if action_key == "inscrire":
                ai_auto_inscrire(sim)
                sim.last_event = trigger_random_event(sim)
                time.sleep(speed)
                continue
            if action_key == "adopter":
                ai_auto_adopter(sim)
                sim.last_event = trigger_random_event(sim)
                time.sleep(speed)
                continue

            # Afficher la décision
            label = next((lb for k, lb, *_ in ACTIONS if k == action_key), action_key)
            print(f"\n {C.CYAN}[IA]{C.RESET} → {label}")

            ACTION_FNS[action_key](sim)
            sim.last_event = trigger_random_event(sim)
            time.sleep(speed)

    finally:
        AUTOPILOT = False

def ai_offer_legacy(sim):
    """Choisit l'héritier adulte le plus âgé (le plus expérimenté)."""
    adult_children = [c for c in sim.children if c.days >= 15]
    if not adult_children:
        return None
    chosen = max(adult_children, key=lambda c: c.days)
    heir = Sim(chosen.name)
    heir.age = 10
    heir.money = sim.money // 2
    heir.orientation = sim.orientation
    for sk in heir.skills.levels:
        heir.skills.levels[sk] = sim.skills.levels[sk] // 2
    heir.children = [c for c in sim.children if c.name != chosen.name]
    slow_print(f"\n {C.YELLOW}[IA] La vie continue avec {chosen.name} — génération suivante !{C.RESET}", 0.03)
    slow_print(f" {C.GRAY}Héritage : ${heir.money} | Compétences héritées à 50 %{C.RESET}", 0.02)
    time.sleep(1)
    return heir

# --- Résultats ---
def show_results(sim, cause=""):
    _, final_stage = get_stage(sim.age)
    print(f"\n {C.BOLD}── Résultats ──────────────────────────{C.RESET}")
    if cause:
        print(f" {C.RED}{cause}{C.RESET}")
    print(f" Nom : {sim.name}")
    print(f" Stade : {final_stage[2]} {final_stage[1]}")
    print(f" Jours : {sim.age}")
    print(f" Argent : ${sim.money}")
    print(f" Métier : {sim.job or 'Jamais travaillé'}")
    if sim.education.has_diploma():
        print(f" Diplôme : {sim.education.domain_label} Mention : {sim.education.grade}")
    if sim.children:
        kids = ", ".join(f"{c.name} ({c.age_label})" for c in sim.children)
        print(f" Famille : {kids}")
    if sim.pet:
        print(f" Animal : {sim.pet.emoji} {sim.pet.name} ({sim.pet.species})")
    rel = sim.relationship
    if not rel.is_single():
        print(f" Relation : {rel.emoji} {rel.label} avec {rel.partner_name}")
    print(f" Humeur : {sim.mood_label()}\n")

# --- Lignée ---
def offer_legacy(sim):
    """Propose de continuer avec un enfant adulte. Retourne un nouveau Sim ou None."""
    adult_children = [c for c in sim.children if c.days >= 15]
    if not adult_children:
        return None

    print(f" {C.BOLD}{C.YELLOW}{'═' * 42}{C.RESET}")
    slow_print(f" {sim.name} laisse derrière lui/elle une famille.", 0.03)
    slow_print(f" Veux-tu continuer l'aventure avec un(e) de ses enfants ?", 0.03)
    print()
    for i, child in enumerate(adult_children, 1):
        print(f" {C.CYAN}[{i}]{C.RESET} {child.name}")
    print(f" {C.CYAN}[0]{C.RESET} Non, terminer la partie")
    print(f" {C.BOLD}{C.YELLOW}{'═' * 42}{C.RESET}\n")

    try:
        choice = int(input(" Choix : ").strip())
        if 1 <= choice <= len(adult_children):
            chosen = adult_children[choice - 1]
            heir = Sim(chosen.name)
            heir.age = 10
            heir.money = sim.money // 2
            heir.orientation = sim.orientation
            for sk in heir.skills.levels:
                heir.skills.levels[sk] = sim.skills.levels[sk] // 2
            heir.children = [c for c in sim.children if c.name != chosen.name]
            slow_print(f"\n {C.GREEN}Bienvenue {chosen.name} ! Tu prends le relais de {sim.name}.{C.RESET}", 0.03)
            slow_print(f" {C.GRAY}Héritage : ${heir.money} | Compétences héritées à 50 %{C.RESET}", 0.02)
            time.sleep(1)
            return heir
    except (ValueError, EOFError, KeyboardInterrupt):
        pass
    return None

# --- Boucle principale ---
def game_loop(sim):
    prev_stage_idx, _ = get_stage(sim.age)
    last_age_checked = sim.age - 1

    while True:
        # Mort naturelle (vieillesse)
        if sim.age > last_age_checked and sim.age >= 45:
            last_age_checked = sim.age
            death_prob = min(35, (sim.age - 43) * 3)
            if random.randint(1, 100) <= death_prob:
                clear()
                print(f"\n {C.GRAY}{'─' * 42}{C.RESET}")
                slow_print(f"\n 🕯 {sim.name} s'est endormi(e) paisiblement...", 0.03)
                slow_print(f" Une belle vie de {sim.age} jours s'achève.", 0.03)
                print(f" {C.GRAY}{'─' * 42}{C.RESET}\n")
                return "vieillesse"

        # Détecter un changement de stade de vie
        cur_stage_idx, cur_stage = get_stage(sim.age)
        if cur_stage_idx != prev_stage_idx:
            clear()
            print(f"\n {C.BOLD}{C.YELLOW}{'═' * 40}{C.RESET}")
            slow_print(f" {cur_stage[2]} Nouveau stade de vie : {C.BOLD}{cur_stage[1]}{C.RESET} !", 0.03)
            slow_print(f" {C.GRAY}{cur_stage[6]}{C.RESET}", 0.03)
            if cur_stage[4]:
                blocked = ", ".join(cur_stage[4])
                slow_print(f" {C.RED}Interdit : {blocked}{C.RESET}", 0.02)
            if cur_stage[5]:
                auth = ", ".join(cur_stage[5])
                slow_print(f" {C.YELLOW}Autorisation parentale requise : {auth}{C.RESET}", 0.02)
            print(f" {C.BOLD}{C.YELLOW}{'═' * 40}{C.RESET}\n")
            _cont()
            prev_stage_idx = cur_stage_idx

        show_status(sim)

        # Avertissements critiques
        crit = sim.critical_needs()
        if crit:
            labels = [Sim.NEED_LABELS[n][0] for n in crit]
            print(f" {C.RED}{C.BOLD}⚠ ATTENTION : {', '.join(labels)} en état critique !{C.RESET}")
        if sim.pet and sim.pet.is_neglected():
            print(f" {C.RED}{C.BOLD}⚠ {sim.pet.name} a besoin de toi ! Faim:{sim.pet.hunger}% Humeur:{sim.pet.happiness}%{C.RESET}")
        if sim.health.hp <= 30:
            print(f" {C.RED}{C.BOLD}⚠ Santé physique critique ({sim.health.hp}%) — consulte un médecin !{C.RESET}")
        if sim.health.mental <= 25:
            print(f" {C.RED}{C.BOLD}⚠ Santé mentale critique ({sim.health.mental}%) — vois un psy !{C.RESET}")
        if crit or sim.health.hp <= 30 or sim.health.mental <= 25 or (sim.pet and sim.pet.is_neglected()):
            print()

        # Mort par famine / épuisement
        if sim.needs["faim"] == 0 and sim.needs["energie"] == 0:
            slow_print(f"\n {C.RED}💀 {sim.name} est épuisé(e) et mort(e) de faim après {sim.age} jour(s)...{C.RESET}")
            slow_print(f" {C.GRAY}Prends soin de tes Sims la prochaine fois !{C.RESET}")
            return "famine"
        # Mort par mauvaise santé
        if sim.health.hp <= 0:
            slow_print(f"\n {C.RED}💀 {sim.name} est décédé(e) des suites de problèmes de santé...{C.RESET}")
            slow_print(f" {C.GRAY}Pense à consulter un médecin régulièrement !{C.RESET}")
            return "santé"

        show_menu(ACTIONS)

        try:
            choice = input(" Ton choix : ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "0"

        if choice == "0":
            slow_print(f"\n {C.CYAN}Au revoir {sim.name} ! Merci d'avoir joué. 👋{C.RESET}")
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ACTIONS):
                action_key = ACTIONS[idx][0]
                _, stage = get_stage(sim.age)
                if action_key in stage[4]:
                    print(f"\n {C.RED}Cette action n'est pas disponible à ton stade de vie ({stage[1]}).{C.RESET}")
                    time.sleep(1.5)
                elif action_key in stage[5]:
                    if ask_parental_auth(sim, stage[1]):
                        ACTION_FNS[action_key](sim)
                        sim.last_event = trigger_random_event(sim)
                    else:
                        sim.last_event = None
                else:
                    ACTION_FNS[action_key](sim)
                    sim.last_event = trigger_random_event(sim)
            else:
                print(f" {C.RED}Choix invalide.{C.RESET}")
                time.sleep(1)
        except ValueError:
            print(f" {C.RED}Choix invalide.{C.RESET}")
            time.sleep(1)

# --- Chargement ---
def load_game():
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        d = json.load(f)
    sim = Sim(d["name"])
    sim.age = d["age"]
    sim.money = d["money"]
    sim.job = d["job"]
    sim.job_days = d["job_days"]
    sim.needs = d["needs"]
    sim.orientation = d.get("orientation", "Bisexuel(le)")

    rel = d.get("relationship", {})
    sim.relationship.level = rel.get("level", 0)
    sim.relationship.partner_name = rel.get("partner_name")
    sim.relationship.affection = rel.get("affection", 0)

    if d.get("pet"):
        p = d["pet"]
        sim.pet = Pet(p["name"], p["species"])
        sim.pet.hunger = p["hunger"]
        sim.pet.happiness = p["happiness"]

    widx = d.get("weather_idx", 0)
    sim.weather._data = WEATHER_TYPES[min(widx, len(WEATHER_TYPES) - 1)]

    sk = d.get("skills", {})
    sim.skills.levels = sk.get("levels", sim.skills.levels)
    sim.skills.xp = sk.get("xp", sim.skills.xp)

    for cd in d.get("children", []):
        c = Child(cd["name"])
        c.days = cd["days"]
        sim.children.append(c)

    hd = d.get("health", {})
    sim.health.hp = hd.get("hp", 100)
    sim.health.mental = hd.get("mental", 80)
    sim.health.diseases = hd.get("diseases", {})

    ed = d.get("education", {})
    sim.education.enrolled_domain = ed.get("enrolled_domain")
    sim.education.sessions_done = ed.get("sessions_done", 0)
    sim.education.total_score = ed.get("total_score", 0)
    sim.education.diploma_domain = ed.get("diploma_domain")
    sim.education.grade = ed.get("grade")

    return sim

# --- Démarrage ---
def main():
    clear()
    print(f"\n{C.BOLD}{C.CYAN}")
    print(" ███████╗██╗███╗   ███╗███████╗")
    print(" ██╔════╝██║████╗ ████║██╔════╝")
    print(" ███████╗██║██╔████╔██║███████╗")
    print(" ╚════██║██║██║╚██╔╝██║╚════██║")
    print(" ███████║██║██║ ╚═╝ ██║███████║")
    print(" ╚══════╝╚═╝╚═╝     ╚═╝╚══════╝")
    print(f" LES SIMS — LIGNE DE COMMANDE{C.RESET}\n")

    slow_print(" Bienvenue dans Les Sims en mode terminal !", 0.03)
    slow_print(" Prends soin de ton Sim et gère ses besoins.\n", 0.03)

    print(f" {C.CYAN}[1]{C.RESET} Nouvelle partie")
    if os.path.exists(SAVE_FILE):
        print(f" {C.CYAN}[2]{C.RESET} Charger la partie sauvegardée")
    print(f" {C.CYAN}[3]{C.RESET} 🤖 Mode Autopilote — l'IA joue à ta place")
    try:
        start = input(f"\n {C.BOLD}Choix : {C.RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        start = "1"

    # ── Mode Autopilote ──────────────────────────────────────────────
    if start == "3":
        clear()
        print(f"\n {C.BOLD}{C.YELLOW}🤖 MODE AUTOPILOTE{C.RESET}\n")
        slow_print(" L'IA va simuler une vie entière à ta place.", 0.03)
        slow_print(" Elle gèrera les besoins, la carrière, les relations et la lignée.\n", 0.03)

        print(f" Vitesse de simulation :")
        print(f" {C.CYAN}[1]{C.RESET} Rapide (0.3 s/action)")
        print(f" {C.CYAN}[2]{C.RESET} Normale (0.8 s/action)")
        print(f" {C.CYAN}[3]{C.RESET} Lente (1.5 s/action)")
        try:
            spd_choice = input(f"\n {C.BOLD}Vitesse : {C.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            spd_choice = "2"
        speed_map = {"1": 0.3, "2": 0.8, "3": 1.5}
        speed = speed_map.get(spd_choice, 0.8)

        auto_name = random.choice(_AUTO_NAMES)
        auto_orient = random.choice(["Hétérosexuel(le)", "Homosexuel(le)", "Bisexuel(le)"])
        sim = Sim(auto_name)
        sim.orientation = auto_orient
        slow_print(f"\n {C.GREEN}Simulation de la vie de {auto_name} ({auto_orient})...{C.RESET}\n", 0.03)
        time.sleep(1)

        current = sim
        generation = 1
        max_gen = 5
        while current is not None and generation <= max_gen:
            if generation > 1:
                slow_print(f"\n {C.BOLD}{C.YELLOW}🤖 Génération {generation} — {current.name}{C.RESET}\n", 0.03)
                time.sleep(speed)
            cause = autopilot_loop(current, speed=speed)
            show_results(current, cause or "")
            time.sleep(speed * 2)
            current = ai_offer_legacy(current)
            generation += 1

        slow_print(f"\n {C.GRAY}🤖 Simulation terminée après {generation - 1} génération(s). Merci !{C.RESET}\n")
        return

    # ── Charger une partie ────────────────────────────────────────────
    if start == "2" and os.path.exists(SAVE_FILE):
        sim = load_game()
        slow_print(f"\n {C.GREEN}Partie chargée ! Bon retour {sim.name} ! 💾{C.RESET}\n", 0.03)
        time.sleep(1)
        current = sim
        generation = 1
        while current is not None:
            cause = game_loop(current)
            show_results(current, cause or "")
            current = offer_legacy(current)
            generation += 1
        slow_print(f" {C.GRAY}Fin de la lignée. Merci d'avoir joué !{C.RESET}\n")
        return

    # ── Nouvelle partie ───────────────────────────────────────────────
    name = input(f"\n {C.BOLD}Quel est le prénom de ton Sim ? {C.RESET}").strip()
    if not name:
        name = "Alex"

    sim = Sim(name)

    orientations = ["Hétérosexuel(le)", "Homosexuel(le)", "Bisexuel(le)", "Je préfère ne pas préciser"]
    print(f"\n {C.BOLD}Quelle est l'orientation sexuelle de {name} ?{C.RESET}")
    for i, o in enumerate(orientations, 1):
        print(f" {C.CYAN}[{i}]{C.RESET} {o}")
    try:
        o_choice = int(input("\n Choix : ").strip())
        if 1 <= o_choice <= len(orientations):
            sim.orientation = orientations[o_choice - 1]
    except ValueError:
        pass

    slow_print(f"\n {C.GREEN}Bienvenue {sim.name} ! Ta vie commence maintenant...{C.RESET}\n", 0.03)
    time.sleep(1)

    current = sim
    generation = 1
    while current is not None:
        if generation > 1:
            slow_print(f"\n {C.BOLD}{C.YELLOW}Génération {generation} — {current.name}{C.RESET}\n", 0.03)
            time.sleep(1)
        cause = game_loop(current)
        show_results(current, cause or "")
        current = offer_legacy(current)
        generation += 1

    slow_print(f" {C.GRAY}Fin de la lignée. Merci d'avoir joué !{C.RESET}\n")

if __name__ == "__main__":
    main()
