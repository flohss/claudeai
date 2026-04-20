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
import contextlib
import io
from datetime import datetime

# --- Mode Autopilote ---
AUTOPILOT = False # True quand l'IA joue à la place du joueur
DEBUG_MODE = False # True pendant les simulations batch (supprime clear + affichage)

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
    if not DEBUG_MODE:
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
    """Affiche du texte lettre par lettre (instantané en mode autopilote/debug)."""
    if AUTOPILOT or DEBUG_MODE:
        print(text)
        return
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
        self.traits = Traits()
        self.stress = 0             # 0–100 ; >70 pénalise le travail, >90 = burn-out
        self.salary_multiplier = 1.0  # augmente avec l'expérience (+5% / 10 j travaillés)
        self.last_romance_day = 0   # dernier jour où une action romantique a eu lieu
        self.days_burned_out = 0    # nb de jours restants de burn-out forcé
        self.hour = 7   # heure courante de la journée (float, 07h00 au réveil)
        self.academic_bonus = 0     # acquis scolaire (0–30), booste les notes à l'université

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
            "energie": -2 * hours,
            "hygiene": -2 * hours,
            "fun": -3 * hours,
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
        # Modificateurs de traits
        for need, mod in self.traits.tick_mods().items():
            if need in decay:
                decay[need] += mod * hours
        # Vieillissement avancé : drain légèrement plus rapide après 40 ans
        if self.age >= 40:
            for need in ("faim", "energie", "fun"):
                if decay[need] < 0:
                    decay[need] *= 1.12
        for need, delta in decay.items():
            self.needs[need] = max(0, min(100, self.needs[need] + int(delta)))
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
        self.neglect_days = 0

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
        self.study_score = 0  # sessions d'aide aux devoirs reçues

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
    "rhume":    ("Rhume",     "🤧", {"energie": -1, "hygiene": -1},           3,  50),
    "grippe":   ("Grippe",    "🤒", {"energie": -3, "hygiene": -2, "fun": -2},5,  80),
    "burnout":  ("Burn-out",  "😵", {"energie": -4, "fun": -3, "social": -2}, 7, 120),
    "fracture": ("Fracture",  "🦴", {"energie": -2, "fun": -2},               6, 150),
    "arthrite": ("Arthrite",  "🦵", {"energie": -1},                          18, 200),
    "diabete":  ("Diabète",   "🩸", {"faim": -2},                             20, 250),
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

# --- Traits de personnalité ---
TRAIT_DEFS = {
    "ambitieux":   ("Ambitieux(se)", "🔥", "Salaire +5%, meilleure moyenne aux études."),
    "paresseux":   ("Paresseux(se)", "😴", "Énergie -50% de drain, mais nécessite plus de fun pour travailler."),
    "sociable":    ("Sociable",      "🗣", "Social se vide moins vite, rencontres plus faciles."),
    "anxieux":     ("Anxieux(se)",   "😰", "Fun se vide plus vite, stress s'accumule 50% plus vite."),
    "curieux":     ("Curieux(se)",   "🔎", "+10 pts aux sessions d'études."),
    "sportif":     ("Sportif(ve)",   "💪", "Énergie -30% de drain, adoré faire du sport."),
    "gourmand":    ("Gourmand(e)",   "🍴", "Faim se vide 50% plus vite, mange avec +10 fun."),
    "artistique":  ("Artistique",   "🎨", "Fun se vide moins vite, loisirs créatifs +10 fun."),
    "econome":     ("Économe",      "💰", "Salaire +5%, dépenses réduites."),
    "malchanceux": ("Malchanceux(se)","🪤", "Événements négatifs 2× plus fréquents."),
}

class Traits:
    def __init__(self, trait_ids=None):
        if trait_ids is None:
            # Éviter la combinaison ambitieux+paresseux (contradictoire)
            pool = list(TRAIT_DEFS.keys())
            t1 = random.choice(pool)
            pool2 = [t for t in pool if not (t1 == "ambitieux" and t == "paresseux")
                                     and not (t1 == "paresseux" and t == "ambitieux")
                                     and t != t1]
            t2 = random.choice(pool2)
            trait_ids = [t1, t2]
        self.active = set(trait_ids)

    def has(self, tid):
        return tid in self.active

    def tick_mods(self):
        """Modificateurs de decay horaire liés aux traits (en plus des bases)."""
        m = {}
        if "paresseux"  in self.active: m["energie"] = m.get("energie", 0) + 1.0
        if "anxieux"    in self.active: m["fun"]     = m.get("fun",     0) - 0.5
        if "sportif"    in self.active: m["energie"] = m.get("energie", 0) + 0.6
        if "gourmand"   in self.active: m["faim"]    = m.get("faim",    0) - 1.5
        if "artistique" in self.active: m["fun"]     = m.get("fun",     0) + 0.5
        if "sociable"   in self.active: m["social"]  = m.get("social",  0) + 1.0
        return m

    def salary_mult(self):
        mult = 1.0
        if "ambitieux" in self.active: mult += 0.05
        if "econome"   in self.active: mult += 0.05
        return mult

    def labels(self):
        return [(TRAIT_DEFS[t][0], TRAIT_DEFS[t][1]) for t in sorted(self.active) if t in TRAIT_DEFS]

# --- Éducation ---
STUDY_DOMAINS = {
    "gastronomie": ("Gastronomie", "🍳", 4, 150),
    "commerce": ("Commerce & Gestion", "💼", 4, 150),
    "arts": ("Arts & Lettres", "🎨", 6, 200),
    "informatique": ("Informatique", "💻", 6, 250),
    "sciences": ("Sciences", "🔬", 6, 250),
    "droit": ("Droit", "⚖", 8, 350),
    "medecine": ("Médecine", "🏥", 8, 400),
    "psychologie": ("Psychologie", "🧠", 6, 280),
    "architecture": ("Architecture", "🏛", 6, 280),
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
    # Nouveaux événements : vie réaliste
    (3, "🏆", "Tu reçois une prime exceptionnelle pour ton travail !", {"fun": +20, "social": +10}, +200),
    (2, "💎", "Un oncle lointain te lègue un petit héritage !", {"fun": +25}, +350),
    (4, "🚑", "Tu fais une chute et te blesses légèrement.", {"energie": -30, "fun": -20}, -50),
    (3, "🔧", "Une canalisation explose chez toi — plombier d'urgence.", {"fun": -15}, -120),
    (4, "🎲", "Tu remportes un petit tournoi local !", {"fun": +30, "social": +20}, +80),
    (3, "📉", "Ton entreprise traverse une crise — pas de prime ce mois.", {"fun": -10, "social": -5}, -80),
    (4, "💡", "Une idée de side-hustle te rapporte quelques euros !", {"fun": +15}, +60),
    (3, "🧾", "Redressement fiscal surprise — aïe !", {"fun": -20}, -150),
    (4, "🌴", "Un ami t'invite à un voyage surprise ce week-end !", {"fun": +35, "social": +25, "energie": -10}, +20),
    (5, "📱", "Ton téléphone tombe en panne — réparation urgente.", {"fun": -20, "social": -15}, -90),
    (3, "🎗", "Tu reçois une reconnaissance associative locale.", {"fun": +20, "social": +25}, +30),
    (4, "🌡", "Vague de chaleur : difficile de dormir la nuit.", {"energie": -15, "fun": -10}, 0),
    (3, "🎓", "Un ami réussit son concours — soirée de célébration !", {"fun": +25, "social": +30, "faim": -15}, +20),
    (4, "🧠", "Une période de rumination t'épuise mentalement.", {"fun": -20, "energie": -10}, 0),
    (3, "🐾", "Ton voisin te confie son chien le temps d'un week-end.", {"fun": +20, "social": +10, "energie": -5}, 0),
]

# --- Événements partenaire ---
# Format : (prob%, emoji, desc_template, effects, money, aff_delta, min_level, condition_fn)
# {p} dans desc sera remplacé par le prénom du partenaire
PARTNER_EVENTS = [
    (13, "💌",
     "{p} t'envoie un message touchant — ça réchauffe le cœur.",
     {"fun": +15, "social": +10}, 0, +5, 1, lambda s: True),
    (10, "💬",
     "Longue conversation sincère avec {p} jusqu'à tard ce soir.",
     {"social": +25, "energie": -10}, 0, +8, 2, lambda s: True),
    (9, "🌹",
     "{p} t'a préparé une surprise romantique — quelle délicate attention !",
     {"fun": +30, "social": +20}, 0, +12, 4, lambda s: s.relationship.affection >= 55),
    (7, "🎉",
     "{p} a une excellente nouvelle — vous fêtez ça ensemble !",
     {"fun": +25, "social": +20}, +40, +8, 2, lambda s: True),
    (8, "😤",
     "{p} est de mauvaise humeur ce soir — tension palpable à la maison.",
     {"fun": -20, "social": -10}, 0, -10, 2, lambda s: s.relationship.affection < 65),
    (7, "🤒",
     "{p} est souffrant(e) — tu veilles sur lui/elle toute la nuit.",
     {"energie": -15, "fun": -10, "social": +10}, -20, -3, 1, lambda s: True),
    (8, "✈",
     "{p} part en déplacement pro — la maison est silencieuse quelques jours.",
     {"social": -20, "fun": -10}, 0, -5, 1, lambda s: True),
    (7, "😔",
     "{p} traverse une période difficile — il/elle a besoin de ton soutien.",
     {"social": +15, "energie": -10}, 0, +6, 2, lambda s: True),
    (6, "💔",
     "{p} te reproche ton manque de présence — ça ne se passe pas bien.",
     {"fun": -25, "social": -15}, 0, -18, 3, lambda s: s.relationship.affection < 45),
    (5, "🎁",
     "{p} rentre avec un cadeau surprise — tu es touché(e).",
     {"fun": +25, "social": +15}, +25, +10, 4, lambda s: s.relationship.affection >= 70),
]

def trigger_partner_event(sim):
    rel = sim.relationship
    if not rel.has_partner():
        return None
    candidates = list(PARTNER_EVENTS)
    random.shuffle(candidates)
    for prob, emoji, desc_tpl, effects, money, aff_delta, min_level, condition in candidates:
        if rel.level < min_level:
            continue
        if not condition(sim):
            continue
        if random.randint(1, 100) > prob:
            continue
        desc = desc_tpl.replace("{p}", rel.partner_name)
        sim.modify(**effects)
        sim.money = max(0, sim.money + money)
        rel.affection = max(0, min(100, rel.affection + aff_delta))
        parts = []
        for need, delta in effects.items():
            lbl = Sim.NEED_LABELS[need][0]
            sign = "+" if delta >= 0 else ""
            col = C.GREEN if delta > 0 else C.RED
            parts.append(f"{col}{sign}{delta} {lbl}{C.RESET}")
        money_str = ""
        if money != 0:
            sign = "+" if money >= 0 else ""
            col = C.GREEN if money > 0 else C.RED
            money_str = f"  {col}{sign}${money}{C.RESET}"
        aff_str = ""
        if aff_delta != 0:
            sign = "+" if aff_delta >= 0 else ""
            col = C.GREEN if aff_delta > 0 else C.RED
            aff_str = f"  {col}{sign}{aff_delta} Affection{C.RESET}"
        return (f"\n {C.BOLD}━━ PARTENAIRE 💑 {rel.partner_name.upper()} ━━{C.RESET}\n"
                f" {emoji} {desc}\n"
                f" {', '.join(parts)}{money_str}{aff_str}")
    return None

# --- Événements liés aux traits ---
# Format : (prob%, emoji, description, effects_dict, money_delta, condition_fn, consequence_key)
# consequence_key : "fracture" | "grippe" | "burnout" | "stress_up" | "mental_down" | None
TRAIT_EVENTS = {
    "ambitieux": [
        (8,  "📈", "Ton patron te remarque et te propose plus de responsabilités !",
             {"fun": +15, "social": +10}, +100, lambda s: bool(s.job), None),
        (5,  "⚡", "Tu travailles jusqu'à l'épuisement pour prouver ta valeur.",
             {"energie": -30, "fun": -10}, +80,  lambda s: bool(s.job), "stress_up"),
        (5,  "🤝", "Une offre d'emploi concurrente arrive dans ta boîte mail.",
             {"fun": +20, "social": +15}, 0,    lambda s: True, None),
    ],
    "paresseux": [
        (8,  "⏰", "Tu rates ton réveil et arrives en retard — réprimande du chef.",
             {"fun": -15, "social": -15}, -30,  lambda s: bool(s.job), None),
        (9,  "🛋", "Tu t'accordes une sieste royale non planifiée... un pur bonheur.",
             {"energie": +40, "fun": +20}, 0,   lambda s: True, None),
        (6,  "📺", "Une journée entière de série sans culpabilité aucune.",
             {"fun": +30, "energie": -5}, 0,    lambda s: True, None),
    ],
    "sociable": [
        (7,  "🌟", "Tu rencontres une personnalité influente lors d'un événement mondain.",
             {"social": +35, "fun": +25}, +60,  lambda s: True, None),
        (8,  "🎉", "Tu organises une soirée improvisée — un succès fou !",
             {"social": +40, "fun": +30, "energie": -20}, -50, lambda s: s.money >= 60, None),
        (6,  "💬", "Ton réseau te permet de décrocher un contrat en or.",
             {"social": +15}, +120, lambda s: bool(s.job), None),
    ],
    "anxieux": [
        (9,  "😰", "Crise d'anxiété soudaine — tout te semble insurmontable.",
             {"fun": -35, "energie": -20}, 0,   lambda s: True, "stress_up"),
        (7,  "🌙", "Nuit blanche à ruminer — tu te réveilles épuisé(e).",
             {"energie": -30, "fun": -15}, 0,   lambda s: True, "stress_up"),
        (5,  "💊", "L'anxiété devient trop forte, tu consultes en urgence.",
             {"fun": -10}, -80,  lambda s: s.money >= 80, "mental_down"),
    ],
    "curieux": [
        (8,  "🔬", "Une découverte fascinante dans ta lecture du soir t'inspire !",
             {"fun": +30, "energie": -5}, 0,    lambda s: True, None),
        (6,  "📚", "Tu passes la nuit à te former sur un sujet inconnu — épuisant mais enrichissant.",
             {"fun": +25, "energie": -25}, 0,   lambda s: True, None),
        (5,  "🏆", "Ta curiosité paie : tu résous un problème que personne n'avait vu.",
             {"fun": +25, "social": +15}, +80,  lambda s: bool(s.job), None),
    ],
    "sportif": [
        (9,  "🏅", "Tu bats ton record personnel — quelle fierté !",
             {"fun": +35, "energie": +10}, 0,   lambda s: True, None),
        (4,  "🦵", "En forçant trop à l'entraînement, tu te blesses sérieusement.",
             {"energie": -35, "fun": -25}, -60, lambda s: True, "fracture"),
        (7,  "🏆", "Tu es invité(e) à un événement sportif local — superbe expérience.",
             {"fun": +25, "social": +20, "energie": -10}, +40, lambda s: True, None),
    ],
    "gourmand": [
        (8,  "🍽", "Tu dénichess un restaurant gastronomique extraordinaire.",
             {"fun": +35, "faim": +20, "social": +10}, -65, lambda s: s.money >= 75, None),
        (9,  "🧁", "Un excès gourmand ce soir — tellement bon, mais les remords arrivent.",
             {"faim": -20, "fun": +20, "hygiene": -10}, -20, lambda s: s.money >= 20, None),
        (5,  "👨‍🍳", "Tu es invité(e) à un atelier cuisine — tu brilles parmi les convives !",
             {"fun": +30, "social": +25}, +20,  lambda s: True, None),
    ],
    "artistique": [
        (9,  "✨", "Une vague d'inspiration créative t'envahit — tu crées quelque chose de beau.",
             {"fun": +40, "energie": -10}, 0,   lambda s: True, None),
        (6,  "🎭", "Tu improvises une performance devant tes amis — ovation debout !",
             {"fun": +30, "social": +35}, +25,  lambda s: True, None),
        (5,  "💔", "Un critique détruit publiquement ta dernière création.",
             {"fun": -35, "social": -20}, 0,    lambda s: True, "mental_down"),
    ],
    "econome": [
        (9,  "💡", "Tu déniche une occasion incroyable — prix imbattable sur quelque chose dont tu as besoin.",
             {"fun": +20}, +70,  lambda s: True, None),
        (6,  "📊", "Ton épargne fructifie mieux que prévu ce mois-ci.",
             {"fun": +15}, +90,  lambda s: s.money >= 200, None),
        (6,  "🎯", "Tu résistes à une tentation coûteuse et tu t'en félicites.",
             {"fun": +10}, +30,  lambda s: True, None),
    ],
    "malchanceux": [
        (10, "💥", "Journée catastrophique : panne + retard + oubli — tout à la fois.",
             {"fun": -30, "energie": -15, "social": -10}, -90, lambda s: True, "stress_up"),
        (8,  "🎭", "Tu glisses dans la rue... et ta chute est filmée par un passant.",
             {"energie": -15, "fun": -25, "hygiene": -15}, -40, lambda s: True, None),
        (9,  "📉", "Une série noire sans fin — rien ne marche comme prévu aujourd'hui.",
             {"fun": -25, "social": -15}, -60, lambda s: True, "stress_up"),
    ],
}

def trigger_trait_event(sim):
    """Déclenche AU PLUS UN événement lié aux traits par nuit.

    Les conséquences graves (fracture, burnout) ne s'appliquent que si le sim
    est assez en forme (hp > 60, energie > 30, âge > 15) pour les encaisser.
    """
    # Construire la liste candidate en mêlant tous les traits
    candidates = []
    for trait in sim.traits.active:
        for ev in TRAIT_EVENTS.get(trait, []):
            candidates.append((trait, ev))
    random.shuffle(candidates)

    for trait, (prob, emoji, desc, effects, money, condition, consequence) in candidates:
        if not condition(sim):
            continue
        if random.randint(1, 100) > prob:
            continue

        # Garder les conséquences graves hors de portée des sims déjà fragiles
        severe = consequence in ("fracture", "burnout")
        if severe and (sim.health.hp < 65 or sim.needs["energie"] < 35 or sim.age < 18):
            continue

        # Appliquer effets
        sim.modify(**effects)
        sim.money = max(0, sim.money + money)

        # Conséquences spéciales
        if consequence == "fracture":
            sim.health.get_sick("fracture")
            sim.health.hp = max(0, sim.health.hp - 12)
        elif consequence == "grippe":
            sim.health.get_sick("grippe")
        elif consequence == "burnout":
            sim.health.get_sick("burnout")
            sim.days_burned_out = max(sim.days_burned_out, 2)
        elif consequence == "stress_up":
            sim.stress = min(100, sim.stress + 15)
        elif consequence == "mental_down":
            sim.health.mental = max(0, sim.health.mental - 20)

        # Message affiché
        trait_lbl, trait_emoji, _ = TRAIT_DEFS[trait]
        parts = []
        for need, delta in effects.items():
            lbl = Sim.NEED_LABELS[need][0]
            sign = "+" if delta >= 0 else ""
            col = C.GREEN if delta > 0 else C.RED
            parts.append(f"{col}{sign}{delta} {lbl}{C.RESET}")
        money_str = ""
        if money != 0:
            sign = "+" if money >= 0 else ""
            col = C.GREEN if money > 0 else C.RED
            money_str = f"  {col}{sign}${money}{C.RESET}"
        cons_str = ""
        if consequence == "fracture":   cons_str = f"  {C.RED}→ Fracture !{C.RESET}"
        elif consequence == "stress_up":cons_str = f"  {C.YELLOW}→ +15 Stress{C.RESET}"
        elif consequence == "mental_down":cons_str = f"  {C.RED}→ Santé mentale −20{C.RESET}"

        return (f"\n {C.BOLD}━━ TRAIT {trait_emoji} {trait_lbl.upper()} ━━{C.RESET}\n"
                f" {emoji} {desc}\n"
                f" {', '.join(parts)}{money_str}{cons_str}")
    return None

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
            elif emoji == "🚑":
                sim.health.hp = max(0, sim.health.hp - 20)
                if random.random() < 0.3:
                    sim.health.get_sick("fracture")
            elif emoji == "🧠":
                sim.health.mental = max(0, sim.health.mental - 15)
                sim.stress = min(100, sim.stress + 10)
            # Événements doublés pour les malchanceux
            if hasattr(sim, 'traits') and sim.traits.has("malchanceux") and actual_money < 0:
                sim.money = max(0, sim.money + actual_money)  # double la perte
                effects_str_extra = f" {C.RED}(×2 — malchanceux){C.RESET}"
            else:
                effects_str_extra = ""

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
                lines.append(f" Argent : {color}{sign}${actual_money}{C.RESET}{effects_str_extra}")

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
          f"{C.BOLD}Argent :{C.RESET} {C.GREEN}${sim.money}{C.RESET} | "
          f"{C.BOLD}Humeur :{C.RESET} {sim.mood_label()}")
    print(f" {C.BOLD}Stade :{C.RESET} {stage[2]} {C.YELLOW}{stage[1]}{C.RESET} — {C.GRAY}{stage[6]}{C.RESET}")

    _h = int(sim.hour)
    _m = int((sim.hour % 1) * 60)
    _day = JOURS_SEMAINE[sim.age % 7]
    _we = (sim.age % 7) >= 5
    _we_str = f"  {C.YELLOW}[Week-end]{C.RESET}" if _we else ""
    _hcol = C.YELLOW if _we else C.CYAN
    print(f" {C.BOLD}Heure :{C.RESET} {_hcol}🕐 {_h:02d}h{_m:02d}{C.RESET}  "
          f"{C.BOLD}Jour :{C.RESET} {_day}  {C.BOLD}·{C.RESET}  Jour {sim.age}{_we_str}")

    # Acquis scolaire (affiché en âge scolaire, ou si > 0 en adulte)
    ab = getattr(sim, 'academic_bonus', 0)
    if stage[1] in ("Enfant", "Adolescent"):
        ab_col = C.GREEN if ab >= 20 else (C.YELLOW if ab >= 10 else C.GRAY)
        print(f" {C.BOLD}Scolarité :{C.RESET} {ab_col}Acquis {ab}/30{C.RESET}  {bar(ab, max_value=30, length=12)}")
    elif ab > 0 and not sim.education.has_diploma():
        print(f" {C.BOLD}Scolarité :{C.RESET} {C.CYAN}Acquis scolaire +{ab} pts (bonus universitaire){C.RESET}")

    edu = sim.education
    if edu.has_diploma():
        print(f" {C.BOLD}Diplôme :{C.RESET} {C.GREEN}{edu.domain_label}{C.RESET} Mention : {C.YELLOW}{edu.grade}{C.RESET}")
    elif edu.is_enrolled():
        lbl, emoji, sessions, _ = STUDY_DOMAINS[edu.enrolled_domain]
        print(f" {C.BOLD}Études :{C.RESET} {emoji} {lbl} "
              f"Session {edu.sessions_done}/{sessions} "
              f"Moy. {edu.total_score // max(1, edu.sessions_done)}/100")

    # Traits de personnalité
    if hasattr(sim, 'traits'):
        t_str = "  ".join(f"{e} {n}" for n, e in sim.traits.labels())
        print(f" {C.BOLD}Traits :{C.RESET} {t_str}")

    if sim.job:
        sal_str = f"  ×{sim.salary_multiplier:.2f}" if sim.salary_multiplier != 1.0 else ""
        bo_str  = f"  {C.RED}[BURN-OUT {sim.days_burned_out}j]{C.RESET}" if sim.days_burned_out > 0 else ""
        print(f" {C.BOLD}Travail :{C.RESET} {sim.job} ({sim.job_days} jour(s)){sal_str}{bo_str}")
    else:
        print(f" {C.BOLD}Travail :{C.RESET} {C.GRAY}Chômeur(se){C.RESET}")
    # Stress
    if hasattr(sim, 'stress'):
        sc = C.RED if sim.stress > 70 else (C.YELLOW if sim.stress > 40 else C.GREEN)
        print(f" {C.BOLD}Stress  :{C.RESET} {sc}{sim.stress}%{C.RESET} {bar(sim.stress, length=12)}")

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
        if p.neglect_days > 0:
            warn = f" {C.RED}⚠ NÉGLIGÉ {p.neglect_days}/3j — {3 - p.neglect_days} jour(s) restant(s) !{C.RESET}"
        elif p.is_neglected():
            warn = f" {C.YELLOW}⚠ BESOIN D'ATTENTION{C.RESET}"
        else:
            warn = ""
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
        dur = ACTION_DURATIONS.get(key, 0)
        if dur >= 1:
            dur_str = f"{int(dur)}h"
        elif dur > 0:
            dur_str = f"{int(dur * 60)}min"
        else:
            dur_str = ""
        suffix = f"  {C.GRAY}({dur_str}){C.RESET}" if dur_str else ""
        print(f" {C.CYAN}[{i:2d}]{C.RESET} {label}{suffix}")
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
    ("devoirs", "Aide aux devoirs", None, "👨‍👩‍👧 Famille"),
    ("sauvegarder", "Sauvegarder la partie", None, "💾 Système"),
]

# Durées de chaque action en heures (0 = instantané, ne consume pas de temps)
ACTION_DURATIONS = {
    "toilettes": 0.25, "snack": 0.25, "nourrir": 0.25, "medicament": 0.25,
    "douche": 0.5,     "mediter": 0.5,  "rupture": 0.5,
    "manger": 1.0,     "appel": 1.0,    "sport": 1.0,   "postuler": 1.0,
    "passer": 1.0,     "flirter": 1.0,  "proposer": 1.0,"adopter": 1.0,
    "jouer_pet": 1.0,  "medecin": 1.0,  "psy": 1.0,
    "sieste": 2.0,     "tv": 2.0,       "lire": 2.0,    "jardiner": 2.0,
    "jeux": 2.0,       "gastronomie": 2.0, "famille": 2.0, "intimite": 2.0,
    "rendezvous": 3.0, "marier": 3.0,
    "inscrire": 4.0,   "sortir": 4.0,
    "etudier": 6.0,
    "dormir": 8.0,     "travailler": 8.0,
    "avoir_enfant": 0.0, "devoirs": 1.0, "sauvegarder": 0.0,
}

JOURS_SEMAINE = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

def get_available_actions(sim):
    """Retourne la liste des actions disponibles selon l'heure et le jour."""
    _, stage = get_stage(sim.age)
    blocked = set(stage[4])
    hour = sim.hour
    is_weekend = (sim.age % 7) >= 5

    available = []
    for entry in ACTIONS:
        key, label, fn, cat = entry
        if key in blocked:
            continue
        dur = ACTION_DURATIONS.get(key, 0)
        # Après 22h, seul dormir est disponible
        if hour >= 22 and key != "dormir":
            continue
        # Filtrer les actions qui dépasseraient 24h
        if dur > 0 and hour + dur > 24 and key != "dormir":
            continue
        # Week-end : pas de travail
        if is_weekend and key == "travailler":
            continue
        # Label dynamique pour devoirs : "Faire ses devoirs" quand on est jeune
        if key == "devoirs" and stage[1] in ("Enfant", "Adolescent"):
            entry = (key, "Faire ses devoirs (aide parentale)", fn, "📚 Études")
        available.append(entry)
    return available

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
    sim.hour = 7    # réveil à 07h00
    sim.weather.new_day()
    slow_print(f" {C.CYAN}Nouveau jour ! Météo : {sim.weather.emoji} {sim.weather.name}{C.RESET}", 0.02)
    sim.health.tick_day()
    for child in sim.children:
        child.tick_day()

    # ── Animal : négligence prolongée ─────────────────────────────
    if sim.pet:
        if sim.pet.is_neglected():
            sim.pet.neglect_days += 1
            sim.modify(fun=-8, social=-5)
            if sim.pet.neglect_days >= 3:
                slow_print(f"\n {C.RED}💔 {sim.pet.name} est parti(e) faute de soins... tu te sens terriblement coupable.{C.RESET}", 0.02)
                sim.modify(fun=-30, social=-20)
                sim.stress = min(100, sim.stress + 20)
                sim.pet = None
            else:
                slow_print(f" {C.YELLOW}⚠ {sim.pet.name} souffre de négligence — encore {3 - sim.pet.neglect_days} jour(s) avant l'irréparable.{C.RESET}", 0.02)
        else:
            sim.pet.neglect_days = 0

    # ── Événements nocturnes : trait > partenaire > aléatoire (40%) ──
    trait_msg = trigger_trait_event(sim)
    if trait_msg:
        sim.last_event = trait_msg
    else:
        partner_msg = trigger_partner_event(sim)
        if partner_msg:
            sim.last_event = partner_msg
        elif random.randint(1, 100) <= 40:
            sim.last_event = trigger_random_event(sim)
        else:
            sim.last_event = None

    # ── Récupération du stress au repos ────────────────────────────
    stress_rec = 15
    if "paresseux" in sim.traits.active: stress_rec = 20
    sim.stress = max(0, sim.stress - stress_rec)
    if sim.days_burned_out > 0:
        sim.days_burned_out -= 1
        if sim.days_burned_out == 0:
            slow_print(f" {C.GREEN}✅ Tu te sens enfin reposé(e). Le burn-out est derrière toi.{C.RESET}", 0.02)

    # ── Coûts journaliers des enfants ──────────────────────────────
    if sim.children:
        daily_kid_cost = 15 * len(sim.children)
        if sim.money >= daily_kid_cost:
            sim.money -= daily_kid_cost
        else:
            sim.money = 0
            sim.modify(fun=-8, social=-5)

    # ── Dégradation naturelle de la relation ──────────────────────
    rel = sim.relationship
    if rel.has_partner():
        days_since_romance = sim.age - sim.last_romance_day
        if days_since_romance >= 3:
            decay_aff = 3 if rel.level >= 4 else 1
            rel.affection = max(0, rel.affection - decay_aff)
        # Risque de rupture spontanée si affection trop basse
        if rel.affection < 20 and rel.level in (1, 2, 3) and random.randint(1, 100) <= 10:
            slow_print(f"\n {C.RED}💔 {rel.partner_name} s'éloigne... La relation prend fin.{C.RESET}", 0.02)
            rel.breakup()
        elif rel.affection < 15 and rel.level == 4 and random.randint(1, 100) <= 5:
            slow_print(f"\n {C.RED}💔 Votre couple ne tient plus... Rupture avec {rel.partner_name}.{C.RESET}", 0.02)
            rel.breakup()

    # ── Licenciement aléatoire (rare : ~1 fois en 5 ans) ─────────
    if sim.job and sim.job_days >= 10:
        layoff_risk = 1 if sim.education.has_diploma() else 2   # 1-2% / jour
        if random.randint(1, 1000) <= layoff_risk * 5:           # 0.5-1% effectif
            if not AUTOPILOT:
                slow_print(f"\n {C.RED}📋 Mauvaise nouvelle : tu as été licencié(e) de ton poste de {sim.job}.{C.RESET}", 0.02)
                slow_print(f" {C.GRAY}Des réductions d'effectifs ont touché ton entreprise.{C.RESET}", 0.02)
            prev_job = sim.job
            sim.job = None
            # On garde job_days pour ne pas perdre les acquis d'ancienneté
            sim.modify(fun=-15, social=-10)

    # ── Maladies chroniques liées à l'âge ────────────────────────
    if sim.age >= 32 and "arthrite" not in sim.health.diseases:
        if random.randint(1, 1000) <= 5:   # 0.5%/jour
            sim.health.get_sick("arthrite")
            slow_print(f" {C.YELLOW}🦵 Tu ressens des douleurs articulaires persistantes (arthrite).{C.RESET}", 0.02)
    if sim.age >= 38 and "diabete" not in sim.health.diseases:
        if random.randint(1, 1000) <= 4:   # 0.4%/jour
            sim.health.get_sick("diabete")
            slow_print(f" {C.YELLOW}🩸 Un bilan sanguin révèle un diabète de type 2.{C.RESET}", 0.02)

    _cont()

def action_sieste(sim):
    slow_print(f"\n {C.BLUE}Tu fais une petite sieste de 2h... 😴{C.RESET}", 0.02)
    sim.stress = max(0, sim.stress - 5)
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
    _, stage = get_stage(sim.age)
    if stage[1] in ("Enfant", "Adolescent"):
        slow_print(f"\n {C.GREEN}Tu lis et tu apprends par toi-même... 📖{C.RESET}", 0.02)
        sim.modify(fun=+15, energie=-5, faim=-5)
        sim.tick(2)
        sim.academic_bonus = min(30, sim.academic_bonus + 1)
        slow_print(f" {C.CYAN}Acquis scolaire : {sim.academic_bonus}/30{C.RESET}", 0.02)
    else:
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
    # Burn-out forcé : impossible de travailler
    if sim.days_burned_out > 0:
        slow_print(f"\n {C.RED}Tu es en burn-out total... Tu ne peux pas travailler. Repose-toi. 😵{C.RESET}", 0.02)
        _cont()
        return
    # Stress élevé → travail plus épuisant
    stress_penalty = 10 if sim.stress > 70 else 0
    base_salary = next(sal for lbl, sal, *_ in JOBS if lbl == sim.job)
    salary = int(base_salary * (1 + sim.skills.bonus('travail')) * sim.salary_multiplier * sim.traits.salary_mult())
    slow_print(f"\n {C.YELLOW}Tu travailles toute la journée comme {sim.job}... 💼{C.RESET}", 0.02)
    sim.money += salary
    sim.job_days += 1
    sim.modify(energie=-(25 + stress_penalty), faim=-20, social=+15, hygiene=-10, fun=+5)
    sim.tick(8)
    # Stress cumulé par la journée de travail
    stress_gain = 8
    if "anxieux" in sim.traits.active: stress_gain = 12
    if "paresseux" in sim.traits.active: stress_gain = 5
    sim.stress = min(100, sim.stress + stress_gain)
    slow_print(f" {C.GREEN}+${salary} gagnés ! Total : ${sim.money}{C.RESET}", 0.02)
    if sim.stress > 70:
        slow_print(f" {C.YELLOW}⚠ Stress élevé ({sim.stress}%) — tu ressens la pression...{C.RESET}", 0.02)
    # Augmentation de salaire tous les 10 jours travaillés (max ×1.5)
    if sim.job_days % 10 == 0 and sim.salary_multiplier < 1.50:
        sim.salary_multiplier = round(min(1.50, sim.salary_multiplier + 0.05), 2)
        slow_print(f" {C.GREEN}⬆ Augmentation ! Ton salaire est maintenant ×{sim.salary_multiplier:.2f}{C.RESET}", 0.02)
    lvl = sim.skills.gain('travail', 10)
    if lvl: slow_print(f" {C.GREEN}Compétence Travail → Niv. {lvl} ! 💼{C.RESET}", 0.02)
    if sim.needs["energie"] < 15 and sim.needs["fun"] < 15:
        sim.health.get_sick("burnout")
        sim.days_burned_out = 3
        slow_print(f" {C.RED}💥 Tu fais un burn-out ! Tu dois te reposer 3 jours...{C.RESET}", 0.02)
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
    sim.stress = max(0, sim.stress - 8)
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
    sim.stress = max(0, sim.stress - 25)
    sim.modify(fun=+15, social=+10)
    slow_print(f" {C.GREEN}Santé mentale +35. Stress −25. Tu te sens mieux. (-${cost}){C.RESET}", 0.02)
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
    # La famille aide aussi à décompresser
    sim.stress = max(0, sim.stress - 6)
    sim.tick(2)
    _cont()

def action_devoirs(sim):
    _, stage = get_stage(sim.age)
    # ── Enfant : devoirs avec aide des parents ─────────────────────────
    if stage[1] == "Enfant":
        slow_print(f"\n {C.CYAN}Tes parents t'aident à faire tes devoirs... 📚{C.RESET}", 0.02)
        sim.modify(energie=-15, fun=-5, social=+10)
        sim.tick(1)
        sim.academic_bonus = min(30, sim.academic_bonus + 3)
        lvl = sim.skills.gain('travail', 6)
        if lvl: slow_print(f" {C.GREEN}Compétence Travail → Niv. {lvl} ! 💼{C.RESET}", 0.02)
        slow_print(f" {C.GREEN}Bien guidé(e) ! Acquis scolaire : {sim.academic_bonus}/30 📈{C.RESET}", 0.02)
        _cont()
        return
    # ── Adolescent : révisions en autonomie ───────────────────────────
    if stage[1] == "Adolescent":
        slow_print(f"\n {C.CYAN}Tu travailles seul(e) sur tes cours et révisions... 📖{C.RESET}", 0.02)
        sim.modify(energie=-20, fun=-10, social=+5)
        sim.tick(1)
        sim.academic_bonus = min(30, sim.academic_bonus + 4)
        lvl = sim.skills.gain('travail', 10)
        if lvl: slow_print(f" {C.GREEN}Compétence Travail → Niv. {lvl} ! 💼{C.RESET}", 0.02)
        slow_print(f" {C.GREEN}Discipline et rigueur — acquis scolaire : {sim.academic_bonus}/30 📈{C.RESET}", 0.02)
        _cont()
        return
    # ── Adulte sans enfants ────────────────────────────────────────────
    if not sim.children:
        print(f"\n {C.YELLOW}Tu n'as pas d'enfants à aider.{C.RESET}")
        _cont()
        return
    # ── Adulte avec enfants ────────────────────────────────────────────
    kids = ", ".join(c.name for c in sim.children)
    slow_print(f"\n {C.CYAN}Tu aides {kids} à faire leurs devoirs... 📚{C.RESET}", 0.02)
    sim.modify(social=+15, fun=+10, energie=-10)
    sim.tick(1)
    for child in sim.children:
        if child.age_label != "Adulte 💪":
            child.study_score += 1
            slow_print(f" {C.GREEN}{child.name} progresse (+1 session d'aide){C.RESET}", 0.02)
    lvl = sim.skills.gain('travail', 4)
    if lvl: slow_print(f" {C.GREEN}Compétence Travail → Niv. {lvl} ! 💼{C.RESET}", 0.02)
    slow_print(f" {C.GREEN}Tu te sens utile et proche de ta famille. 🌟{C.RESET}", 0.02)
    _cont()

def action_sauvegarder(sim):
    data = {
        "name": sim.name, "age": sim.age, "money": sim.money,
        "hour": sim.hour,
        "job": sim.job, "job_days": sim.job_days, "needs": sim.needs,
        "orientation": sim.orientation,
        "stress": sim.stress,
        "salary_multiplier": sim.salary_multiplier,
        "last_romance_day": sim.last_romance_day,
        "days_burned_out": sim.days_burned_out,
        "academic_bonus": sim.academic_bonus,
        "traits": list(sim.traits.active),
        "relationship": {
            "level": sim.relationship.level,
            "partner_name": sim.relationship.partner_name,
            "affection": sim.relationship.affection,
        },
        "pet": {"name": sim.pet.name, "species": sim.pet.species,
                "hunger": sim.pet.hunger, "happiness": sim.pet.happiness,
                "neglect_days": sim.pet.neglect_days,
                } if sim.pet else None,
        "weather_idx": WEATHER_TYPES.index(sim.weather._data),
        "skills": {"levels": sim.skills.levels, "xp": sim.skills.xp},
        "children": [{"name": c.name, "days": c.days, "study_score": c.study_score} for c in sim.children],
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
    sim.last_romance_day = sim.age
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
    sim.last_romance_day = sim.age
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
    sim.last_romance_day = sim.age
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
    base += getattr(sim, 'academic_bonus', 0)   # acquis scolaire de l'enfance
    base += random.randint(-15, 15)
    if hasattr(sim, 'traits') and sim.traits.has("curieux"):
        base += 10
    if hasattr(sim, 'traits') and sim.traits.has("ambitieux"):
        base += 5
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
    "devoirs": action_devoirs,
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
    """IA survie optimisée — seuils dynamiques tenant compte des maladies actives."""
    _, stage = get_stage(sim.age)
    blocked = set(stage[4])
    n = sim.needs
    h = sim.health

    is_weekend = (sim.age % 7) >= 5

    # ── Taux de decay extra causés par les maladies actives ──────────
    # IMPORTANT : les valeurs dans DISEASES sont NÉGATIVES (ex: grippe hygiene=-2/h).
    # On prend la valeur absolue pour obtenir le taux de decay supplémentaire.
    extra_e = -sum(DISEASES[d][2].get("energie", 0) for d in h.diseases if d in DISEASES)
    extra_h = -sum(DISEASES[d][2].get("hygiene", 0) for d in h.diseases if d in DISEASES)
    extra_f = -sum(DISEASES[d][2].get("fun",     0) for d in h.diseases if d in DISEASES)

    # Seuils dynamiques (tick énergie=-2/h, fun=-3/h depuis refonte)
    hygiene_thresh = 22 + 10 + 8 * (2 + extra_h)  # 48 sain | 72 grippe+rhume
    energie_thresh = 36 + extra_e * 5              # 36 sain | 61 grippe+rhume
    fun_thresh     = 44 + extra_f * 3              # 44 sain | 50 grippe+rhume

    # Coûts d'un sleep (pour la préparation pré-bedtime)
    _sleep_hyg_cost = 10 + 8 * (2 + extra_h)       # 26 sain | 50 grippe+rhume
    _faim_safe      = 15 + 60                       # 75 — survive sleep
    _hygiene_safe   = 22 + _sleep_hyg_cost          # 48 sain | 72 grippe+rhume

    # Burn-out forcé : pas de travail, récupération prioritaire
    if getattr(sim, 'days_burned_out', 0) > 0:
        if n["faim"] < 60:  return "snack" if sim.money < 5 else "manger"
        if n["energie"] < 60: return "sieste" if n["energie"] >= 30 else "dormir"
        if n["fun"] < 50 and "mediter" not in blocked: return "mediter"
        if h.mental < 50 and sim.money >= 60: return "psy"
        return "lire"

    # Stress > 90 → ne peut pas travailler, décompresser en priorité
    if getattr(sim, 'stress', 0) >= 90:
        if sim.money >= 60 and h.mental < 80: return "psy"
        if n["fun"] < 70 and "mediter" not in blocked: return "mediter"
        return "lire"

    # Urgence absolue : faim=0 → manger avant tout (sinon danger_turns → famine)
    if n["faim"] == 0:
        return "snack" if sim.money < 5 else "manger"

    if sim.hour >= 22:
        # Préparation pré-sleep : éviter famine/HP drain pendant le sleep
        if n["faim"]    < _faim_safe:    return "snack" if sim.money < 5 else "manger"
        if n["hygiene"] < _hygiene_safe: return "douche"
        if n["fun"]     < 50 and sim.hour < 23 and "mediter" not in blocked:
            return "mediter"   # dormir avec plus de fun → réveiller avec moins de drain
        return "dormir"

    # ═══════════════════════════════════════════════════════════════
    # MODE MALADIE : GUÉRIR en priorité (médicament réduit durée de 1j/prise).
    # 4 médicaments + 1 sleep cure grippe (5→1→tick_day=0) pour $80.
    # COÛTS SLEEP : faim −60, hygiene −(10+8×(2+extra_h)), énergie net +4 (grippe+rhume)
    # PIÈGE : douche coûte tick(1) → énergie −7 avec maladies.
    #   → Séparer "pré-sleep" (préparer les reserves) de "éveillé" (médicaments).
    # ═══════════════════════════════════════════════════════════════
    if h.is_sick():
        sleep_faim_cost = 60                          # modify -20 + tick 8×5
        sleep_hyg_cost  = 10 + 8 * (2 + extra_h)     # 26 sain | 50 grippe+rhume
        faim_safe    = 15 + sleep_faim_cost           # 75 — survive sleep
        hygiene_safe = 22 + sleep_hyg_cost            # 48 sain | 72 grippe+rhume

        about_to_sleep = n["energie"] < 15

        if about_to_sleep:
            # Urgence : energie ≈ 0 + maladies multiples → sleep ne restaure PAS l'énergie.
            # ex: grippe+rhume: gain=60, coût=8×(2+3+1)×8=48, net=+12 (nouveau tick -2/h).
            # Médecin SEULEMENT si energie < 10 pour limiter les ticks de faim (1 appel max).
            if n["energie"] < 10 and sim.money >= 80:    return "medecin"
            needs_meds_now = any(v > 1 for v in h.diseases.values())
            if n["energie"] < 10 and needs_meds_now and sim.money >= 20: return "medicament"
            # Préparer le sleep AVANT de dormir (ordre : faim → hygiene → sleep)
            if n["faim"]    < faim_safe:             return "snack" if sim.money < 5 else "manger"
            if n["hygiene"] < hygiene_safe:          return "douche"
            return "dormir"

        # Éveillé et malade → GUÉRIR
        if n["faim"]    < 45:                        return "snack" if sim.money < 5 else "manger"
        if n["hygiene"] < 45:                        return "douche"
        # Médecin : cure_all() + HP+30 pour $80
        if sim.money >= 80:                          return "medecin"
        # Médicament pour réduire durée de maladie si durée > 1
        needs_meds = any(v > 1 for v in h.diseases.values())
        if needs_meds and sim.money >= 20:           return "medicament"
        # Maladies toutes à 1j → attendre le prochain sleep pour guérir ; récupérer
        if n["energie"] < 60 and "sieste" not in blocked: return "sieste"
        if n["faim"]    < 60:                        return "manger"
        return "mediter" if "mediter" not in blocked else "lire"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 1 : besoins critiques (sim sain — seuils dynamiques)
    # HYGIENE AVANT ENERGIE : douche doit précéder le sleep pour éviter hygiene < 20
    # après tick(8). Sans ce guard, energie < 20 force le sleep avec hygiene trop basse.
    # Douche saine : energie +5 (modify) puis tick -3 = net +2 → ne nuit pas à l'énergie.
    # ═══════════════════════════════════════════════════════════════
    if n["vessie"]  < 30:                                                 return "toilettes"
    if n["faim"]    < 50 and "manger" not in blocked:
        return "snack" if sim.money < 5 else "manger"
    if n["hygiene"] < hygiene_thresh:                                     return "douche"
    if n["energie"] < energie_thresh:
        # Vérifier faim avant de dormir (sleep coûte 60 faim; dormir avec faim<75 → réveil à ~15)
        if n["faim"] < _faim_safe:   return "snack" if sim.money < 5 else "manger"
        return "dormir"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 2 : santé proactive
    # ═══════════════════════════════════════════════════════════════
    if h.hp < 85 and sim.money >= 80:                                     return "medecin"
    if h.mental < 45 and sim.money >= 60:                                 return "psy"
    # Mental critique sans argent → fun/social
    if h.mental < 30:
        if n["fun"] < 80 and "mediter" not in blocked:                    return "mediter"
        return "appel"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 3 : animal de compagnie
    # ═══════════════════════════════════════════════════════════════
    if sim.pet and sim.pet.hunger    < 35:                                return "nourrir"
    if sim.pet and sim.pet.happiness < 30:                                return "jouer_pet"
    if (not sim.pet and "adopter" not in blocked
            and sim.money > 400 and random.random() < 0.03):              return "adopter"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 4 : récupération préventive
    # Sieste (2h): +30 énergie (modify) + tick(2) → net ~+22 énergie, coûte -15 faim
    # Méditer (0.5h): +15 fun +15 energie GRATUITEMENT (quasi nul)
    # ═══════════════════════════════════════════════════════════════
    # Sieste proactive — recharger avant seuil de travail
    energie_work_min = 25 + 8 * (2 + extra_e) + 3   # 44 sain | 68 grippe+rhume
    if n["energie"] < min(55, energie_work_min) and n["faim"] >= 20 and "sieste" not in blocked:
        return "sieste"

    # Social préventif : si social bas, mental drain imminent (fun<25 ET social<25 → -4/h)
    if n["social"] < 42:                                                   return "appel"

    # Fun préventif
    if n["fun"] < fun_thresh and "mediter" not in blocked:                return "mediter"
    if n["fun"] < fun_thresh - 10 and n["energie"] > 55 and n["faim"] > 45:
        if "tv" not in blocked:                                            return "tv"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 5 : carrière & études
    # ═══════════════════════════════════════════════════════════════
    if "travailler" not in blocked:
        edu = sim.education

        # A) Pas de job → postuler immédiatement (y compris après licenciement)
        if not sim.job and jobs_available(edu):
            return "postuler"

        # B) Diplôme obtenu → changer de poste sans délai
        if edu.has_diploma():
            best = max(jobs_available(edu), key=lambda x: x[1], default=None)
            if best:
                cur_sal = next((s for lb, s, *_ in JOBS if lb == sim.job), 0)
                if best[1] > cur_sal:
                    return "postuler"

        # Calcul prédictif (tick énergie=-2/h, fun=-3/h)
        e_cost_t    = 25 + 8 * (2 + extra_e)   # 41 sain | 65 grippe
        f_cost_t    = -5 + 8 * (3 + extra_f)   # 19 sain | 35 grippe
        hyg_cost_t  = 10 + 8 * (2 + extra_h)
        faim_cost_t = 20 + 8 * 5               # 60
        peut_travailler = (
            n["energie"] - e_cost_t  > 3   and
            n["faim"]    - faim_cost_t > 5  and
            n["fun"]     - f_cost_t  > -20  and
            n["hygiene"] - hyg_cost_t > 20
        )
        e_cost_e = 8 + 6 * (2 + extra_e)
        f_cost_e = 0 + 6 * (3 + extra_f)
        peut_etudier = (
            n["energie"] - e_cost_e > 12 and
            n["faim"]    - 45       > 10 and
            n["fun"]     - f_cost_e > -10
        )

        # C) Études en cours → étudier 7j/7 en priorité sur le travail
        if edu.is_enrolled():
            session_cost = STUDY_DOMAINS[edu.enrolled_domain][3]
            sessions_left = edu.sessions_required() - edu.sessions_done
            # Buffer réduit quand on approche de la fin : plus besoin de garder autant de réserve
            study_buffer = max(0, (sessions_left - 1)) * 80   # 0$ sur la dernière session, 80$/session sinon
            if sim.money >= session_cost + study_buffer and peut_etudier:
                return "etudier"
            # Pas de session possible → travailler pour financer les études
            if not is_weekend and sim.job and peut_travailler:
                return "travailler"

        # D) Pas encore inscrit → s'inscrire dès que le buffer le permet (session + 200$ médecin)
        elif (not edu.has_diploma() and sim.money >= 350
                and "inscrire" not in blocked):
            return "inscrire"

        # E) Travailler (semaine seulement)
        elif not is_weekend and sim.job and peut_travailler:
            return "travailler"

        # Récupération ciblée si conditions de travail non réunies
        if not peut_travailler and not is_weekend:
            if n["energie"] < energie_work_min:
                return "sieste" if n["energie"] >= 30 else "dormir"
            if n["faim"] < 65:
                return "manger"
            if n["fun"] < 25 and "mediter" not in blocked:
                return "mediter"
            if n["hygiene"] < hygiene_thresh:
                return "douche"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 6 : vie amoureuse — progression déterministe
    # ═══════════════════════════════════════════════════════════════
    if "flirter" not in blocked:
        rel = sim.relationship

        # Célibataire → chercher une rencontre (avec garde sur les stats)
        if rel.is_single() and n["energie"] > 50 and n["faim"] > 45:
            return "flirter"

        # Lvl 1-3 : faire avancer la relation (rendezvous +25 aff/$35, flirt +15 aff/gratuit)
        if rel.has_partner() and not rel.is_couple():
            if sim.money >= 115 and n["energie"] > 55 and n["faim"] > 50 and random.random() < 0.75:
                return "rendezvous"  # 115 = 35 coût + 80 buffer médecin
            elif n["energie"] > 45 and random.random() < 0.75:
                return "flirter"

        # Lvl 4 (couple) : monter l'affection puis demander en mariage
        if rel.level == 4:
            if rel.affection >= 75 and "proposer" not in blocked:
                return "proposer"
            if "intimite" not in blocked:
                return "intimite"

    # Lvl 5 (fiancé(e)) : se marier quand finances et santé le permettent
    if ("marier" not in blocked and sim.relationship.level == 5
            and sim.money >= 360 and h.hp >= 70 and not h.is_sick()):
        return "marier"

    # Lvl 6 (marié(e)) : entretenir l'affection
    if (sim.relationship.level == 6
            and "intimite" not in blocked
            and sim.relationship.affection < 88):
        return "intimite"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 7 : famille
    # ═══════════════════════════════════════════════════════════════
    # Jeune sim : faire ses propres devoirs (booste travail skill)
    if (stage[1] in ("Enfant", "Adolescent")
            and "devoirs" not in blocked
            and n["energie"] > 40 and random.random() < 0.25):
        return "devoirs"
    if ("avoir_enfant" not in blocked
        and sim.relationship.level == 6
        and len(sim.children) < 3
        and random.random() < 0.35):
        return "avoir_enfant"
    if sim.children and random.random() < 0.40:
        return "famille"
    if sim.children and random.random() < 0.20 and "devoirs" not in blocked:
        return "devoirs"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 8 : loisirs sécurisés
    # ═══════════════════════════════════════════════════════════════
    pool = []
    if n["energie"] > 75 and n["faim"] > 60 and not h.is_sick():
        pool += ["sport"]
    if n["energie"] > 65 and n["faim"] > 55 and not h.is_sick():
        pool += ["jardiner"]
    if n["fun"] < 75:
        pool += ["lire", "mediter"]
        if n["energie"] > 55 and n["faim"] > 45:
            pool += ["tv", "jeux"]
        if sim.money >= 20 and sim.skills.levels.get("cuisine", 0) > 0:
            pool += ["gastronomie"]
    if sim.money >= 100 and n["fun"] < 68 and n["energie"] > 65 and n["faim"] > 55 and not h.is_sick():
        pool += ["sortir"]
    if n["social"] < 60:
        pool += ["appel"]
    if not pool:
        pool = ["mediter", "lire", "appel"]
    pool = [a for a in pool if a not in blocked]
    return random.choice(pool) if pool else "mediter"

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
    """Choisit automatiquement le domaine d'études le plus rentable accessible.
    Garde un buffer financier (400$) pour les soins médicaux et dépenses courantes."""
    MONEY_BUFFER = 200   # réserve santé minimale (2-3 médecins)
    scored = {}  # domain → score
    for key, (lbl, emoji, sessions, cost) in STUDY_DOMAINS.items():
        if sim.money < cost + MONEY_BUFFER:
            continue
        best_sal = max(
            (jsal for jlbl, jsal, dom, grade in JOBS
             if dom == key and grade in (None, "Passable", "Bien")),
            default=0,
        )
        if best_sal > 0:
            # Score = salaire / sessions (efficacité par session) avec plancher à 1
            scored[key] = best_sal / max(sessions, 1)

    if not scored:
        return
    # Sélection pondérée parmi les filières dont le score est ≥ 70 % du meilleur
    best_score = max(scored.values())
    candidates = {k: s for k, s in scored.items() if s >= 0.70 * best_score}
    keys = list(candidates.keys())
    weights = [candidates[k] for k in keys]
    best_domain = random.choices(keys, weights=weights, k=1)[0]
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
    danger_turns = 0   # compteur de tours en état critique

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

            # — Morts par besoins / santé (avec période de grâce de 2 tours) —
            if sim.needs["faim"] == 0 and sim.needs["energie"] == 0:
                danger_turns += 1
                if danger_turns >= 2:
                    slow_print(f"\n {C.RED}💀 {sim.name} est mort(e) d'épuisement après {sim.age} jour(s).{C.RESET}", 0.02)
                    return "famine"
            else:
                danger_turns = 0
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
                sim.hour += ACTION_DURATIONS.get("postuler", 0)
                time.sleep(speed)
                continue
            if action_key == "inscrire":
                ai_auto_inscrire(sim)
                sim.hour += ACTION_DURATIONS.get("inscrire", 0)
                time.sleep(speed)
                continue
            if action_key == "adopter":
                ai_auto_adopter(sim)
                sim.hour += ACTION_DURATIONS.get("adopter", 0)
                time.sleep(speed)
                continue

            # Afficher la décision
            label = next((lb for k, lb, *_ in ACTIONS if k == action_key), action_key)
            print(f"\n {C.CYAN}[IA]{C.RESET} → {label}")

            ACTION_FNS[action_key](sim)
            if action_key != "dormir":
                sim.hour += ACTION_DURATIONS.get(action_key, 0)
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
    study_bonus = chosen.study_score * 20   # 20$ par session d'aide reçue
    heir.money = sim.money // 2 + study_bonus
    heir.orientation = sim.orientation
    for sk in heir.skills.levels:
        heir.skills.levels[sk] = sim.skills.levels[sk] // 2
    heir.children = [c for c in sim.children if c.name != chosen.name]
    slow_print(f"\n {C.YELLOW}[IA] La vie continue avec {chosen.name} — génération suivante !{C.RESET}", 0.03)
    if study_bonus > 0:
        slow_print(f" {C.GREEN}Grâce aux devoirs partagés : +${study_bonus} d'avance au départ{C.RESET}", 0.02)
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

# --- Mode Débogage / Batch ---
DEBUG_REPORT_FILE = "debug_report.txt"

def _format_debug_report(results):
    """Formate les résultats de simulation en rapport texte lisible."""
    lines = []
    sep = "=" * 62
    lines += [sep,
              "  RAPPORT DÉBOGAGE — MODE AUTOPILOTE",
              f"  Date       : {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}",
              f"  Simulations: {len(results)}",
              sep]

    for r in results:
        lines.append(f"\n── Simulation #{r['sim']} : {r['name']} ──────────────────────")
        cause_str = {"famine": "💀 Famine", "santé": "💀 Santé",
                     "vieillesse": "🕯 Vieillesse", "timeout": "⏱ Limite atteinte",
                     None: "✅ En vie"}.get(r['cause'], r['cause'])
        lines.append(f"  Survie     : {r['age']} jours  |  Fin : {cause_str}  |  {r['generations']} génération(s)")
        lines.append(f"  Travail    : {r['job'] or 'Aucun'} ({r['job_days']} j)  |  Diplôme : {r['diploma'] or 'Aucun'}")
        lines.append(f"  Argent     : ${r['money']}  |  HP : {r['hp']}  |  Mental : {r['mental']}")
        rel_str = r['relationship']
        if r['partner']:
            rel_str += f" avec {r['partner']}"
        lines.append(f"  Relation   : {rel_str}  |  Enfants : {r['children']}  |  Animal : {r['pet'] or 'Aucun'}")
        if r['diseases']:
            lines.append(f"  ⚠ Maladies : {', '.join(r['diseases'])}")
        n = r['needs']
        lines.append(f"  Besoins    : faim={n['faim']:3d}  énergie={n['energie']:3d}  "
                     f"hygiene={n['hygiene']:3d}  fun={n['fun']:3d}  "
                     f"social={n['social']:3d}  vessie={n['vessie']:3d}")

    # ── Statistiques globales ──────────────────────────────────
    lines += ["", sep, "  STATISTIQUES GLOBALES", sep]
    ages = [r['age'] for r in results]
    lines.append(f"  Survie moyenne : {sum(ages)/len(ages):.1f} jours")
    lines.append(f"  Survie max     : {max(ages)} jours  (sim #{results[ages.index(max(ages))]['sim']})")
    lines.append(f"  Survie min     : {min(ages)} jours  (sim #{results[ages.index(min(ages))]['sim']})")

    from collections import Counter
    causes = Counter(r['cause'] for r in results)
    causes_str = "  ".join(f"{k or 'en vie'} ×{v}" for k, v in causes.most_common())
    lines.append(f"  Causes de fin  : {causes_str}")

    jobs = [r['job'] for r in results if r['job']]
    if jobs:
        top = Counter(jobs).most_common(5)
        lines.append(f"  Top jobs       : " + "  |  ".join(f"{j} ×{c}" for j, c in top))

    dips = [r['diploma'].split(' (')[0] for r in results if r['diploma']]
    if dips:
        top = Counter(dips).most_common(5)
        lines.append(f"  Top diplômes   : " + "  |  ".join(f"{d} ×{c}" for d, c in top))
    else:
        lines.append(f"  Diplômes       : aucun obtenu")

    avg_money = sum(r['money'] for r in results) / len(results)
    lines.append(f"  Argent moyen   : ${avg_money:.0f}")

    married = sum(1 for r in results if "Marié" in r['relationship'])
    burnout_count = sum(1 for r in results if 'burnout' in r['diseases'])
    lines.append(f"  Mariés à fin   : {married}/{len(results)}")
    lines.append(f"  Burnout actif  : {burnout_count}/{len(results)}")

    all_diseases = []
    for r in results:
        all_diseases.extend(r['diseases'])
    if all_diseases:
        top_d = Counter(all_diseases).most_common()
        lines.append(f"  Maladies finales: " + "  ".join(f"{d} ×{c}" for d, c in top_d))

    lines.append(sep)
    return "\n".join(lines)

def debug_batch_run(n_sims=10, max_gen=5):
    """Lance n_sims simulations autopilote en batch et sauvegarde le rapport."""
    global DEBUG_MODE
    DEBUG_MODE = True

    results = []
    orientations = ["Hétérosexuel(le)", "Homosexuel(le)", "Bisexuel(le)"]

    for sim_num in range(1, n_sims + 1):
        print(f"\r  ▶ Simulation {sim_num:3d}/{n_sims}...", end="", flush=True)

        name   = random.choice(_AUTO_NAMES)
        orient = random.choice(orientations)
        sim    = Sim(name)
        sim.orientation = orient

        gen         = 1
        final_cause = None

        # Rediriger stdout pour supprimer tout affichage pendant la simulation
        with contextlib.redirect_stdout(io.StringIO()):
            while gen <= max_gen:
                cause = autopilot_loop(sim, speed=0)
                final_cause = cause
                if cause is None:
                    break
                heir = ai_offer_legacy(sim)
                if heir is None:
                    break
                sim = heir
                gen += 1

        results.append({
            "sim":          sim_num,
            "name":         name,
            "age":          sim.age,
            "generations":  gen,
            "cause":        final_cause,
            "job":          sim.job,
            "job_days":     sim.job_days,
            "diploma":      (f"{sim.education.diploma_domain} ({sim.education.grade})"
                             if sim.education.has_diploma() else None),
            "money":        sim.money,
            "hp":           sim.health.hp,
            "mental":       sim.health.mental,
            "relationship": sim.relationship.label,
            "partner":      sim.relationship.partner_name,
            "children":     len(sim.children),
            "pet":          (f"{sim.pet.name} ({sim.pet.species})" if sim.pet else None),
            "diseases":     list(sim.health.diseases.keys()),
            "needs":        dict(sim.needs),
        })

    DEBUG_MODE = False
    print(f"\r  ✓ {n_sims} simulations terminées.{' ' * 20}")

    report = _format_debug_report(results)

    with open(DEBUG_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    print(f"\n {C.GREEN}Rapport sauvegardé → {DEBUG_REPORT_FILE}{C.RESET}")
    input(f"\n{C.GRAY}Appuie sur Entrée pour revenir au menu...{C.RESET}")

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
            study_bonus = chosen.study_score * 20
            heir.money = sim.money // 2 + study_bonus
            heir.orientation = sim.orientation
            for sk in heir.skills.levels:
                heir.skills.levels[sk] = sim.skills.levels[sk] // 2
            heir.children = [c for c in sim.children if c.name != chosen.name]
            slow_print(f"\n {C.GREEN}Bienvenue {chosen.name} ! Tu prends le relais de {sim.name}.{C.RESET}", 0.03)
            bonus_str = f" + ${study_bonus} (devoirs)" if study_bonus > 0 else ""
            slow_print(f" {C.GRAY}Héritage : ${heir.money}{bonus_str} | Compétences héritées à 50 %{C.RESET}", 0.02)
            time.sleep(1)
            return heir
    except (ValueError, EOFError, KeyboardInterrupt):
        pass
    return None

# --- Boucle principale ---
def game_loop(sim):
    prev_stage_idx, _ = get_stage(sim.age)
    last_age_checked = sim.age - 1
    danger_turns = 0   # compteur de tours en état critique

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

        # Mort par famine / épuisement (période de grâce : 2 tours consécutifs à 0)
        if sim.needs["faim"] == 0 and sim.needs["energie"] == 0:
            danger_turns += 1
            if danger_turns >= 2:
                slow_print(f"\n {C.RED}💀 {sim.name} est épuisé(e) et mort(e) de faim après {sim.age} jour(s)...{C.RESET}")
                slow_print(f" {C.GRAY}Prends soin de tes Sims la prochaine fois !{C.RESET}")
                return "famine"
        else:
            danger_turns = 0
        # Mort par mauvaise santé
        if sim.health.hp <= 0:
            slow_print(f"\n {C.RED}💀 {sim.name} est décédé(e) des suites de problèmes de santé...{C.RESET}")
            slow_print(f" {C.GRAY}Pense à consulter un médecin régulièrement !{C.RESET}")
            return "santé"

        if sim.hour >= 22:
            print(f"\n {C.YELLOW}🌙 Il est {int(sim.hour):02d}h — il est temps de dormir !{C.RESET}\n")
        avail = get_available_actions(sim)
        show_menu(avail)

        try:
            choice = input(" Ton choix : ").strip()
        except (EOFError, KeyboardInterrupt):
            choice = "0"

        if choice == "0":
            slow_print(f"\n {C.CYAN}Au revoir {sim.name} ! Merci d'avoir joué. 👋{C.RESET}")
            return None

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(avail):
                action_key = avail[idx][0]
                _, stage = get_stage(sim.age)
                if action_key in stage[5]:
                    if ask_parental_auth(sim, stage[1]):
                        ACTION_FNS[action_key](sim)
                        if action_key != "dormir":
                            sim.hour += ACTION_DURATIONS.get(action_key, 0)
                    else:
                        sim.last_event = None
                else:
                    ACTION_FNS[action_key](sim)
                    if action_key != "dormir":
                        sim.hour += ACTION_DURATIONS.get(action_key, 0)
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
    sim.hour = d.get("hour", 7)
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
        sim.pet.neglect_days = p.get("neglect_days", 0)

    widx = d.get("weather_idx", 0)
    sim.weather._data = WEATHER_TYPES[min(widx, len(WEATHER_TYPES) - 1)]

    sk = d.get("skills", {})
    sim.skills.levels = sk.get("levels", sim.skills.levels)
    sim.skills.xp = sk.get("xp", sim.skills.xp)

    for cd in d.get("children", []):
        c = Child(cd["name"])
        c.days = cd["days"]
        c.study_score = cd.get("study_score", 0)
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

    sim.stress           = d.get("stress", 0)
    sim.salary_multiplier = d.get("salary_multiplier", 1.0)
    sim.last_romance_day  = d.get("last_romance_day", 0)
    sim.days_burned_out   = d.get("days_burned_out", 0)
    sim.academic_bonus    = d.get("academic_bonus", 0)
    trait_ids = d.get("traits")
    if trait_ids:
        sim.traits = Traits(trait_ids)

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
    print(f" {C.CYAN}[4]{C.RESET} 🔧 Mode Débogage — Simuler plusieurs parties en batch")
    try:
        start = input(f"\n {C.BOLD}Choix : {C.RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        start = "1"

    # ── Mode Débogage / Batch ────────────────────────────────────────
    if start == "4":
        clear()
        print(f"\n {C.BOLD}{C.YELLOW}🔧 MODE DÉBOGAGE — SIMULATIONS EN BATCH{C.RESET}\n")
        slow_print(" Ce mode lance plusieurs parties autopilote en silence,", 0.03)
        slow_print(" condense les résultats et les sauvegarde dans un fichier.", 0.03)
        slow_print(f" {C.GRAY}(Le fichier {DEBUG_REPORT_FILE} peut être partagé pour analyse){C.RESET}\n", 0.02)
        try:
            n_input = input(f" {C.BOLD}Nombre de simulations (défaut 10) : {C.RESET}").strip()
            n_sims = int(n_input) if n_input.isdigit() and int(n_input) > 0 else 10
        except (EOFError, KeyboardInterrupt):
            n_sims = 10
        try:
            g_input = input(f" {C.BOLD}Générations max par simulation (défaut 5) : {C.RESET}").strip()
            max_gen = int(g_input) if g_input.isdigit() and int(g_input) > 0 else 5
        except (EOFError, KeyboardInterrupt):
            max_gen = 5
        print()
        debug_batch_run(n_sims=n_sims, max_gen=max_gen)
        return

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
