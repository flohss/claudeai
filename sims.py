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
        self.retired = False        # True après action prendre_retraite
        self.pension = 0            # montant quotidien de la pension ($/jour)
        self.housing = None         # None ou dict {property_id, purchase_price, loan_total, loan_remaining, daily_payment, days_missed}

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

    def new_day(self, season_weights=None):
        if season_weights:
            self._data = random.choices(WEATHER_TYPES, weights=season_weights)[0]
        else:
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

# --- Prénoms ---
_PRENOMS_MASC = [
    # Contemporains français
    "Théo", "Hugo", "Lucas", "Léo", "Nathan", "Tom", "Mathis", "Ethan", "Louis", "Arthur",
    "Raphaël", "Clément", "Baptiste", "Julien", "Pierre", "Antoine", "Nicolas", "Guillaume",
    "Thomas", "Alexandre", "Maxime", "Valentin", "Romain", "Simon", "Adrien", "Victor",
    "Florian", "Axel", "Quentin", "Kevin", "Enzo", "Luca", "Matteo", "Gabin", "Paul",
    "Rémi", "Tristan", "Alexis", "Robin", "Jordan", "Nolan", "Kylian", "Yanis", "Adam",
    "Mehdi", "Sacha", "Félix", "Oscar", "Émile", "Gabriel", "Marius", "Jules", "Charles",
    "Henri", "Timothée", "Théodore", "Thibaut", "Gaspard", "Armand", "Florent", "Cédric",
    "Dorian", "Aymeric", "Anthony", "Samuel", "Kilian", "Gaétan", "Maxence", "Aurélien",
    "Thibault", "Sandro", "Ilian", "Darius", "Boris", "Basile", "Brice", "Amaury",
    "Antonin", "Ariel", "Aristide", "Arsène", "Noé", "Achille", "Étienne", "Jérémy",
    # Classiques français
    "Jean", "Jacques", "François", "Philippe", "Maurice", "André", "Marcel", "Roger",
    "Fernand", "Gaston", "Gérard", "Bernard", "Robert", "Michel", "Alain", "Daniel",
    "Éric", "Patrick", "Christophe", "Stéphane", "Frédéric", "Olivier", "Laurent",
    "Sébastien", "Jérôme", "Xavier", "Arnaud", "Gilles", "Cyril", "Pascal", "Thierry",
    "Denis", "Yves", "Luc", "Bruno", "Serge", "Claude", "Emmanuel", "Fabrice", "Hubert",
    "Joël", "Lionel", "Benoît", "René", "Lucien", "Patrice", "Norbert", "Fabien",
    "Damien", "Vincent", "Grégoire", "Gautier", "Geoffroy", "Godefroy", "Lambert",
    "Lancelot", "Stanislas", "Sylvestre", "Théophile", "Ulysse", "Renaud", "Raoul",
    "Gonzague", "Hippolyte", "Isidore", "Prosper", "Casimir", "Anastase", "Aubin",
    # Régionaux (breton, basque…)
    "Maël", "Ronan", "Yann", "Corentin", "Malo", "Gaël", "Loïc", "Erwan", "Titouan",
    "Brendan", "Gwénolé", "Tugdual", "Efflan", "Gurvan", "Jakez", "Tangi", "Gwendal",
    "Iker", "Aitor", "Mikel", "Eneko", "Gaizka", "Gorka", "Iñigo", "Unai", "Xabi",
    # Internationaux
    "Logan", "Mason", "Elijah", "Oliver", "James", "Benjamin", "Henry", "Sebastian",
    "Jonah", "Ezra", "Aaron", "Eli", "William", "Wyatt", "Cameron", "Aiden", "Hunter",
    "Tyler", "Cole", "Bryce", "Chase", "Connor", "Finn", "Gavin", "Hayden", "Jasper",
    "Kai", "Kyle", "Lance", "Maxwell", "Miles", "Nash", "Orlando", "Parker", "Quinn",
    "Reed", "Rowan", "Scott", "Seth", "Shane", "Blake", "Owen", "Liam", "Noah",
    "Edward", "Edwin", "Curtis", "Craig", "Colin", "Colby", "Clay", "Clark",
    "Austin", "Archer", "Aldo", "Alden", "Albert", "Bruno", "Brett",
    # Espagnols / latinos
    "Carlos", "Diego", "Miguel", "Pablo", "Luis", "Juan", "Eduardo", "Roberto",
    "Fernando", "Sergio", "Rafael", "Alejandro", "Marcos", "Rodrigo", "Alvaro",
    "Jaime", "Pedro", "Vicente", "Salvador", "Emilio", "Felipe", "Gonzalo",
    "Enrique", "Ignacio", "Jorge", "Julio", "Lorenzo", "Manuel", "Santiago",
    # Italiens
    "Alessandro", "Francesco", "Andrea", "Davide", "Emanuele", "Nicola",
    "Angelo", "Dario", "Domenico", "Fabio", "Giacomo", "Giovanni", "Giuseppe",
    "Leonardo", "Mauro", "Paolo", "Stefano", "Valentino", "Marco",
    # Nordiques / germaniques
    "Björn", "Lars", "Erik", "Sven", "Magnus", "Olaf", "Gunnar", "Leif",
    "Rasmus", "Casper", "Mads", "Mikkel", "Hans", "Klaus", "Karl", "Otto",
    # Arabes / nord-africains
    "Mohammed", "Youssef", "Amine", "Karim", "Hakim", "Hassan", "Omar", "Ali",
    "Rachid", "Nabil", "Tarek", "Walid", "Yacine", "Zakaria", "Bilal", "Farid",
    "Hicham", "Marwan", "Nassim", "Sofiane", "Ayoub", "Aziz", "Badr", "Anass",
    "Rayan", "Samy", "Imad", "Ismail", "Hamza", "Ghali", "Fares", "Djamal",
    "Brahim", "Adil", "Akram", "Amar", "Wissam", "Yazid", "Ziad", "Ramzi",
    "Othman", "Abdel", "Idriss", "Nadir", "Mourad", "Samir", "Hichem", "Anas",
    # Africains subsahariens
    "Mamadou", "Ibrahima", "Abdoulaye", "Moussa", "Seydou", "Ousmane", "Modou",
    "Lamine", "Cheikh", "Daouda", "Aliou", "Malick", "Souleymane", "Pape",
    "Babacar", "Kofi", "Kwame", "Amadou", "Boubacar", "Ismaël", "Oumar",
    "Thierno", "Alpha", "Demba", "Samba", "Sékou", "Assane", "Alassane",
]

_PRENOMS_FEM = [
    # Contemporaines françaises
    "Emma", "Jade", "Manon", "Léa", "Inès", "Chloé", "Louise", "Alice", "Camille",
    "Lucie", "Eva", "Clara", "Sophie", "Julie", "Laura", "Sarah", "Charlotte",
    "Mathilde", "Zoé", "Lola", "Pauline", "Elisa", "Anaïs", "Marine", "Justine",
    "Clémence", "Amandine", "Émilie", "Mélanie", "Audrey", "Amélie", "Céline",
    "Diane", "Elise", "Fanny", "Gaëlle", "Isabelle", "Julia", "Karine", "Lisa",
    "Margaux", "Margot", "Nathalie", "Océane", "Yasmine", "Fleur", "Flore",
    "Estelle", "Agathe", "Victoire", "Adèle", "Héloïse", "Noémie", "Perrine",
    "Violette", "Rose", "Iris", "Lily", "Luna", "Nina", "Mia", "Maëlle",
    "Nolwenn", "Morgane", "Rozenn", "Lou", "Louisa", "Lucile", "Lilas", "Loan",
    "Maëva", "Marion", "Maud", "Mélodie", "Milena", "Mona", "Nadège", "Naomi",
    "Natacha", "Nawel", "Ophélie", "Oriane", "Paola", "Pénélope", "Perle",
    "Prune", "Romane", "Rosalie", "Roxane", "Sabrina", "Salomé", "Sandra",
    "Sirine", "Solène", "Tiphaine", "Valentine", "Vanessa", "Axelle", "Coralie",
    "Daphnée", "Éléonore", "Floriane", "Livia", "Maëlis", "Mahault",
    "Joséphine", "Juliette", "Laetitia", "Laure", "Lise", "Lorraine",
    "Magnolia", "Malorie", "Manuela", "Marielle", "Marilyne", "Maureen",
    "Mélissa", "Nelly", "Pascaline", "Prescillia", "Prudence", "Séraphine",
    "Stéphanie", "Tamara", "Valéria", "Wendeline", "Yara", "Ysabeau",
    "Junia", "Céleste", "Colombe", "Blanche", "Capucine", "Cassandre",
    "Guillemette", "Harmonie", "Ingrid", "Orianne", "Roseline", "Thalia",
    # Classiques françaises
    "Marie", "Anne", "Jeanne", "Françoise", "Hélène", "Suzanne", "Marguerite",
    "Madeleine", "Simone", "Odette", "Denise", "Nicole", "Monique", "Jacqueline",
    "Martine", "Michèle", "Christine", "Sylvie", "Véronique", "Laurence",
    "Virginie", "Delphine", "Aurélie", "Patricia", "Florence", "Geneviève",
    "Colette", "Brigitte", "Cécile", "Danielle", "Edith", "Germaine", "Huguette",
    "Irène", "Joëlle", "Lydie", "Nadine", "Noëlle", "Pascale", "Renée",
    "Séverine", "Tatiana", "Viviane", "Yvonne", "Corinne", "Valérie", "Sandrine",
    "Geneviève", "Andrée", "Bernadette", "Fernande", "Odile", "Régine",
    "Rosine", "Thérèse", "Ursule", "Wanda", "Xavière", "Zelda",
    # Régionales (bretonnes…)
    "Gwenaëlle", "Sterenn", "Maïwenn", "Gaëllane", "Soizic", "Gwenola",
    "Naïg", "Rozenn", "Nolwenn", "Enora", "Armelle", "Aziliz",
    # Internationales
    "Olivia", "Sophia", "Isabella", "Amelia", "Harper", "Evelyn", "Abigail",
    "Emily", "Victoria", "Scarlett", "Grace", "Penelope", "Riley", "Hazel",
    "Violet", "Aurora", "Savannah", "Brooklyn", "Bella", "Skylar", "Lucy",
    "Anna", "Caroline", "Nova", "Kennedy", "Samantha", "Maya", "Willow",
    "Aaliyah", "Elena", "Ariana", "Gabrielle", "Brianna", "Hailey", "Autumn",
    "Alyssa", "Lilly", "Madison", "Morgan", "Taylor", "Casey", "Blake",
    "Avery", "Dakota", "Quinn", "Peyton", "Sydney", "Bailey", "Jamie",
    "Reese", "Sage", "Sloane", "Skye", "Nadia", "Vera", "Mila", "Natasha",
    "Alicia", "Bianca", "Carmen", "Diana", "Elena", "Francesca", "Gloria",
    "Hannah", "Ingrid", "Jessica", "Kate", "Linda", "Monica", "Nancy",
    "Patricia", "Rebecca", "Stella", "Uma", "Valentina", "Wendy", "Xenia",
    # Espagnoles / latines
    "Lucia", "Sofia", "Valeria", "Camila", "Isabel", "Daniela", "Fernanda",
    "Catalina", "Alejandra", "Mariana", "Beatriz", "Claudia", "Esperanza",
    "Jimena", "Lola", "Pilar", "Rosario", "Silvia", "Teresa", "Ximena",
    # Arabes / nord-africaines
    "Amina", "Leila", "Sonia", "Nora", "Sara", "Lina", "Fatima", "Zayneb",
    "Maryam", "Kenza", "Imane", "Hafsa", "Houda", "Samira", "Karima",
    "Naima", "Aicha", "Malika", "Meriem", "Nadia", "Nabila", "Nawal",
    "Nour", "Rima", "Safia", "Salima", "Selma", "Siham", "Yamina",
    "Zineb", "Zorah", "Djamila", "Farida", "Fadela", "Fatiha", "Hakima",
    "Halima", "Hassiba", "Hayat", "Loubna", "Manel", "Nassima", "Nesrine",
    "Nissa", "Nourhen", "Radia", "Rahima", "Rym", "Wahiba", "Yousra",
    # Africaines subsahariennes
    "Aminata", "Fatoumata", "Mariama", "Kadiatou", "Mariam", "Aissatou",
    "Coumba", "Khady", "Penda", "Awa", "Binta", "Djeneba", "Fatouma",
    "Hawa", "Maimouna", "Nafissatou", "Oumou", "Ramata", "Fanta",
    "Halima", "Hadja", "Khadija", "Koumba", "Mariatou", "Mireille",
    "Miriam", "Zeinab", "Adja", "Astou", "Fatou", "Ndéye", "Rokhaya",
]

_PRENOMS_ANIMAUX = [
    # Chiens classiques
    "Fido", "Rex", "Max", "Buddy", "Rocky", "Duke", "Cooper", "Bear", "Tucker", "Milo",
    "Zeus", "Buster", "Winston", "Leo", "Oliver", "Oscar", "Jasper", "Bentley", "Toby",
    # Noms français / gourmands
    "Minou", "Noisette", "Caramel", "Bulle", "Grizou", "Luna", "Pixel", "Câlin", "Doudou",
    "Pépite", "Cannelle", "Chocolat", "Vanille", "Praline", "Fraise", "Myrtille", "Cacao",
    "Nougat", "Cerise", "Amande", "Pistache", "Abricot", "Figue", "Olive", "Papaye",
    # Nature / fleurs
    "Coquelicot", "Pâquerette", "Lilas", "Jasmin", "Mimosa", "Bouton", "Étoile", "Comète",
    "Soleil", "Lune", "Brume", "Tornade", "Tempête", "Orage", "Sirocco", "Mistral",
    # Références culturelles
    "Einstein", "Picasso", "Mozart", "Darwin", "Newton", "Tesla", "Voltaire", "Socrate",
    "Platon", "Archimède", "Galilée", "Copernic", "Descartes", "Pascal", "Rousseau",
    # Fantaisie / superhéros
    "Zorro", "Tornado", "Flash", "Turbo", "Rocket", "Comet", "Nova", "Star", "Galaxy",
    "Cosmos", "Nebula", "Aurora", "Eclipse", "Phoenix", "Titan", "Atlas", "Orion",
    # Mignons
    "Bobine", "Toupie", "Pirouette", "Frimousse", "Chamallow", "Guimauve", "Bonbon",
    "Câlinette", "Fluffie", "Patapouf", "Ronron", "Minette", "Rouquin", "Bibi",
    "Boubou", "Coco", "Lulu", "Mimi", "Nono", "Pacha", "Riri", "Titi", "Zozo",
]

# --- Relations ---
PARTNER_NAMES = _PRENOMS_MASC + _PRENOMS_FEM

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
# Format : (nom, emoji, decay_mods, durée_ou_None, coût, catégorie)
# catégorie : "inf"=infection  "trau"=trauma  "chr"=chronique
#             "fat"=fatal/progressif  "neuro"=neurodégénératif  "ment"=mental
DISEASES = {
    # ── Infections ──────────────────────────────────────────────────
    "rhume":        ("Rhume",                "🤧", {"energie": -1, "hygiene": -1},                  3,   40, "inf"),
    "gastro":       ("Gastro-entérite",      "🤢", {"energie": -2, "faim": -3},                     4,   60, "inf"),
    "grippe":       ("Grippe",               "🤒", {"energie": -3, "hygiene": -2, "fun": -2},        6,   80, "inf"),
    "bronchite":    ("Bronchite",            "😮", {"energie": -2, "hygiene": -1, "fun": -1},        9,  110, "inf"),
    "pneumonie":    ("Pneumonie",            "🫁", {"energie": -5, "hygiene": -3, "fun": -3},       14,  200, "inf"),
    # ── Traumatismes ────────────────────────────────────────────────
    "entorse":      ("Entorse",              "🦶", {"energie": -1, "fun": -2},                       5,   80, "trau"),
    "fracture":     ("Fracture",             "🦴", {"energie": -2, "fun": -2},                       8,  150, "trau"),
    "commotion":    ("Commotion cérébrale",  "🤕", {"energie": -3, "social": -2},                    6,  180, "trau"),
    # ── Maladies chroniques (permanentes, gérables) ──────────────
    "hypertension": ("Hypertension",         "💗", {"energie": -1, "fun": -1},                    None,  120, "chr"),
    "asthme":       ("Asthme",               "💨", {"energie": -2},                               None,  100, "chr"),
    "arthrite":     ("Arthrite",             "🦵", {"energie": -1},                               None,  180, "chr"),
    "diabete":      ("Diabète",              "🩸", {"faim": -2, "energie": -1},                   None,  250, "chr"),
    "insuff_card":  ("Insuf. cardiaque",     "❤", {"energie": -3, "fun": -2, "social": -2},       None,  400, "chr"),
    # ── Maladies progressives/fatales (stades 1→2→3) ─────────────
    "cancer_poumon":("Cancer du poumon",     "🫁", {"energie": -3, "fun": -2, "hygiene": -1},     None,  600, "fat"),
    "cancer_colon": ("Cancer colorectal",    "🏥", {"energie": -2, "faim": -2, "fun": -1},        None,  500, "fat"),
    "cancer_peau":  ("Mélanome",             "🌑", {"energie": -1, "fun": -1},                    None,  350, "fat"),
    "leucemie":     ("Leucémie",             "🩸", {"energie": -4, "hygiene": -2, "fun": -3},     None,  600, "fat"),
    # ── Neurodégénératives (seniors, incurables) ──────────────────
    "alzheimer":    ("Maladie d'Alzheimer",  "🧠", {"social": -3, "fun": -2, "energie": -1},      None,  250, "neuro"),
    "parkinson":    ("Maladie de Parkinson", "🤲", {"energie": -2, "fun": -2, "social": -1},      None,  220, "neuro"),
    # ── Mental ───────────────────────────────────────────────────
    "burnout":      ("Burn-out",             "😵", {"energie": -4, "fun": -3, "social": -2},        7,  120, "ment"),
}

class Health:
    def __init__(self):
        self.hp = 100
        self.mental = 80
        self.diseases = {}          # id → jours restants ou None (chronique/progressif)
        self.disease_stage = {}     # id → stade 1–3 (fat/neuro uniquement)

    def get_sick(self, disease_id):
        if disease_id not in self.diseases and disease_id in DISEASES:
            cat = DISEASES[disease_id][5]
            dur = DISEASES[disease_id][3]
            if cat in ("chr", "fat", "neuro"):
                self.diseases[disease_id] = None
                if cat in ("fat", "neuro"):
                    self.disease_stage[disease_id] = 1
            else:
                self.diseases[disease_id] = dur

    def tick_day(self):
        # Guérison des maladies à durée finie
        recovered = [k for k, v in self.diseases.items() if v is not None and v <= 1]
        for k in recovered:
            del self.diseases[k]
            self.disease_stage.pop(k, None)
        for k in list(self.diseases):
            if self.diseases.get(k) is not None:
                self.diseases[k] -= 1
        # Progression et HP drain des maladies évolutives
        for did in list(self.diseases):
            if did not in self.diseases or did not in DISEASES:
                continue
            cat = DISEASES[did][5]
            stage = self.disease_stage.get(did, 1)
            if cat == "fat":
                if stage < 3 and random.randint(1, 100) <= 6:  # ~16j/stade
                    self.disease_stage[did] = stage + 1
                self.hp = max(0, self.hp - {1: 0, 2: 1, 3: 3}.get(stage, 0))
            elif cat == "neuro":
                if stage < 3 and random.randint(1, 100) <= 4:  # ~25j/stade
                    self.disease_stage[did] = stage + 1
                self.hp = max(0, self.hp - max(0, stage - 1))
            elif did == "pneumonie":
                self.hp = max(0, self.hp - 2)
            elif did == "insuff_card":
                self.hp = max(0, self.hp - 1)

    def cure_all(self):
        """Supprime uniquement les maladies guérissables (infections, traumas, mental)."""
        to_remove = [k for k in self.diseases
                     if k in DISEASES and DISEASES[k][5] not in ("chr", "fat", "neuro")]
        for k in to_remove:
            del self.diseases[k]
            self.disease_stage.pop(k, None)

    def decay_mods(self):
        mods = {}
        for did in self.diseases:
            if did not in DISEASES:
                continue
            base = DISEASES[did][2]
            stage = self.disease_stage.get(did, 1)
            if DISEASES[did][5] in ("fat", "neuro") and stage > 1:
                base = {k: v * stage for k, v in base.items()}
            for need, delta in base.items():
                mods[need] = mods.get(need, 0) + delta
        return mods

    def has_fatal(self):
        return any(DISEASES.get(d, ('','','',0,0,'inf'))[5] in ("fat", "neuro")
                   for d in self.diseases)

    def fatal_max_stage(self):
        stages = [self.disease_stage.get(d, 1) for d in self.diseases
                  if DISEASES.get(d, ('','','',0,0,'inf'))[5] in ("fat", "neuro")]
        return max(stages, default=0)

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

# --- Événements saisonniers ---
# Format : (prob%, emoji, desc, effects, money, condition_fn, special)
# special : "grippe" | "rhume" | "fracture" | None
SEASON_EVENTS = {
    "printemps": [
        (18, "🌸", "Les cerisiers sont en fleur — une promenade magique s'impose.",
         {"fun": +20, "social": +10}, 0, None, None),
        (14, "🤧", "Les pollens du printemps t'assaillent — allergies en pleine forme.",
         {"energie": -15, "fun": -10}, 0, None, "rhume"),
        (15, "🌱", "Tu passes l'après-midi à préparer ton potager.",
         {"fun": +15, "energie": -10}, 0, None, None),
        (12, "🎪", "Une fête de village bat son plein dans le quartier !",
         {"fun": +30, "social": +25}, -20, None, None),
        (14, "🌧", "Un orage de printemps t'attrape en pleine sortie.",
         {"hygiene": -25, "fun": -10, "energie": -5}, 0, None, None),
        (10, "🍓", "Les premières fraises du marché — tu craques pour un kilo.",
         {"faim": +20, "fun": +15}, -15, None, None),
        (12, "🚴", "Sortie vélo sous le soleil printanier avec des amis.",
         {"fun": +25, "energie": -15, "social": +15}, 0, None, None),
        (8,  "🐛", "Tu tombes nez-à-nez avec une chenille processionnaire — bonne frayeur.",
         {"fun": -10}, 0, None, None),
    ],
    "ete": [
        (18, "🏖", "Journée plage avec des amis — soleil, rires et vagues !",
         {"fun": +35, "social": +25, "energie": -10}, 0, None, None),
        (14, "🌡", "Canicule nocturne — la nuit est étouffante, impossible de dormir.",
         {"energie": -20, "fun": -10}, 0, None, None),
        (12, "🎆", "Feu d'artifice du 14 juillet — le ciel explose de couleurs !",
         {"fun": +30, "social": +20}, 0, None, None),
        (13, "🍦", "Glace artisanale sous le soleil — petit plaisir de l'été.",
         {"fun": +15, "faim": +10}, -12, None, None),
        (12, "🏊", "Après-midi à la piscine municipale — rafraîchissant !",
         {"fun": +25, "energie": -10, "hygiene": -5}, -15, None, None),
        (10, "🍖", "Barbecue improvisé avec les voisins — ambiance festive !",
         {"fun": +30, "social": +30, "faim": +20}, -25, None, None),
        (10, "⚡", "Orage violent en pleine nuit — le tonnerre te réveille en sursaut.",
         {"energie": -15, "fun": -10}, 0, None, None),
        (8,  "🌻", "Champ de tournesols au détour d'une route — le bonheur simple.",
         {"fun": +20}, 0, None, None),
    ],
    "automne": [
        (16, "🍄", "Cueillette de champignons en forêt — le panier est plein !",
         {"fun": +20, "energie": -10, "faim": +10}, +20, None, None),
        (14, "🎃", "Halloween — décoration, costumes et friandises pour les enfants.",
         {"fun": +25, "social": +20}, -20,
         lambda s: bool(s.children) or s.relationship.level >= 4, None),
        (12, "🍷", "Vendanges chez un ami viticulteur — tu mets la main à la pâte.",
         {"fun": +20, "social": +25, "energie": -15}, +30, None, None),
        (13, "🌧", "Pluie grise et froide — une mélancolie automnale t'envahit.",
         {"fun": -15, "social": -10}, 0, None, None),
        (12, "🌰", "Tu ramasses des châtaignes et les fais griller au feu de bois.",
         {"fun": +20, "faim": +15}, 0, None, None),
        (10, "🦔", "Un hérisson déambule dans ton jardin ce soir — craquant !",
         {"fun": +15, "social": +5}, 0, None, None),
        (10, "📚", "Rentrée culturelle : conférence passionnante au théâtre local.",
         {"fun": +15, "social": +15}, -20, None, None),
        (9,  "💨", "Tempête automnale — une branche casse sur ta voiture.",
         {"fun": -20}, -80, None, None),
    ],
    "hiver": [
        (18, "🎄", "Décorations de Noël partout dans le quartier — ambiance féerique.",
         {"fun": +25, "social": +15}, -30, None, None),
        (16, "🎁", "Tu reçois un cadeau surprise d'un proche pour les fêtes !",
         {"fun": +30, "social": +20}, +50,
         lambda s: s.relationship.level >= 2, None),
        (13, "⛷", "Sortie ski avec des amis — pistes enneigées et vin chaud !",
         {"fun": +35, "social": +25, "energie": -20}, -60,
         lambda s: s.money >= 100, "entorse"),
        (12, "🌨", "Tempête de neige — tu restes blotti(e) chez toi toute la journée.",
         {"fun": +10, "social": -15, "energie": +5}, 0, None, None),
        (14, "🎆", "Réveillon du Nouvel An — champagne, musique et bonne humeur !",
         {"fun": +40, "social": +35, "energie": -15}, -30, None, None),
        (14, "🤒", "Le froid t'a fragilisé(e) — tu couve quelque chose.",
         {"energie": -20, "fun": -10}, 0, None, "grippe"),
        (12, "☕", "Soirée cocooning au coin du feu — plaid, thé et bonne lecture.",
         {"fun": +20, "energie": +10, "social": -5}, 0, None, None),
        (8,  "🧊", "Verglas sur le trottoir — tu glisses et te blesses.",
         {"energie": -15, "fun": -20}, -30, None, "fracture"),
    ],
}

def trigger_season_event(sim):
    sid, sdata = get_season(sim.age)
    events = list(SEASON_EVENTS.get(sid, []))
    random.shuffle(events)
    for prob, emoji, desc, effects, money, condition, special in events:
        if condition and not condition(sim):
            continue
        if random.randint(1, 100) > prob:
            continue
        sim.modify(**effects)
        sim.money = max(0, sim.money + money)
        if special == "grippe":
            sim.health.get_sick("grippe")
        elif special == "rhume":
            sim.health.get_sick("rhume")
        elif special == "fracture":
            if random.randint(1, 100) <= 40:
                sim.health.get_sick("fracture")
                sim.health.hp = max(0, sim.health.hp - 8)
        elif special == "entorse":
            if random.randint(1, 100) <= 30:
                sim.health.get_sick("entorse")
        lines = [
            f"\n {C.BOLD}━━ ÉVÉNEMENT {sdata[1]} {sdata[0].upper()} ━━{C.RESET}",
            f" {emoji} {desc}",
        ]
        if effects:
            parts = []
            for need, delta in effects.items():
                label = Sim.NEED_LABELS[need][0]
                sign = "+" if delta >= 0 else ""
                col = C.GREEN if delta > 0 else C.RED
                parts.append(f"{col}{sign}{delta} {label}{C.RESET}")
            lines.append(f" Effets : {', '.join(parts)}")
        if money != 0:
            sign = "+" if money >= 0 else ""
            col = C.GREEN if money > 0 else C.RED
            lines.append(f" Argent : {col}{sign}${money}{C.RESET}")
        return "\n".join(lines)
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
    _ssid, _ssdata = get_season(sim.age)
    _season_cols = {"printemps": C.GREEN, "ete": C.YELLOW, "automne": C.YELLOW, "hiver": C.CYAN}
    _scol = _season_cols[_ssid]
    print(f" {C.BOLD}Heure :{C.RESET} {_hcol}🕐 {_h:02d}h{_m:02d}{C.RESET}  "
          f"{C.BOLD}Jour :{C.RESET} {_day}  {C.BOLD}·{C.RESET}  Jour {sim.age}  "
          f"{_ssdata[1]} {_scol}{_ssdata[0]}{C.RESET}{_we_str}")

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

    if getattr(sim, 'retired', False):
        pension_col = C.GREEN if sim.pension >= 300 else (C.CYAN if sim.pension >= 150 else C.YELLOW)
        print(f" {C.BOLD}Retraite :{C.RESET} {C.GREEN}🎉 Retraité(e){C.RESET}  "
              f"{pension_col}Pension ${sim.pension}/jour{C.RESET}  "
              f"{C.GRAY}({sim.job_days} j. cotisés){C.RESET}")
    elif sim.job:
        sal_str = f"  ×{sim.salary_multiplier:.2f}" if sim.salary_multiplier != 1.0 else ""
        bo_str  = f"  {C.RED}[BURN-OUT {sim.days_burned_out}j]{C.RESET}" if sim.days_burned_out > 0 else ""
        print(f" {C.BOLD}Travail :{C.RESET} {sim.job} ({sim.job_days} jour(s)){sal_str}{bo_str}")
    else:
        print(f" {C.BOLD}Travail :{C.RESET} {C.GRAY}Chômeur(se){C.RESET}")
    # Stress
    if hasattr(sim, 'stress'):
        sc = C.RED if sim.stress > 70 else (C.YELLOW if sim.stress > 40 else C.GREEN)
        print(f" {C.BOLD}Stress  :{C.RESET} {sc}{sim.stress}%{C.RESET} {bar(sim.stress, length=12)}")

    if sim.housing:
        _hw = sim.housing
        _hpdata = get_property_data(_hw["property_id"])
        if _hpdata:
            _hnom, _hemoji = _hpdata[1], _hpdata[2]
            if _hw["loan_remaining"] > 0:
                _paid = _hw["loan_total"] - _hw["loan_remaining"]
                _pct  = int(_paid * 100 / max(1, _hw["loan_total"]))
                _miss = (f"  {C.RED}⚠ {_hw['days_missed']} impayé(s){C.RESET}"
                         if _hw["days_missed"] > 0 else "")
                _pcol = C.RED if _hw["days_missed"] > 0 else C.YELLOW
                print(f" {C.BOLD}Logement :{C.RESET} {_hemoji} {_hnom}  "
                      f"Crédit {_pcol}${_hw['daily_payment']}/j{C.RESET}  "
                      f"Restant ${_hw['loan_remaining']:,}/{_hw['loan_total']:,}  "
                      f"{bar(_pct, length=10)}{_miss}")
            else:
                print(f" {C.BOLD}Logement :{C.RESET} {_hemoji} {_hnom}  {C.GREEN}✅ Propriétaire !{C.RESET}")

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
        parts = []
        for d, v in h.diseases.items():
            if d not in DISEASES: continue
            name, emoji, _, _, _, cat = DISEASES[d]
            stage = h.disease_stage.get(d, 0)
            if cat in ("fat", "neuro"):
                sc = C.RED if stage >= 3 else (C.YELLOW if stage >= 2 else C.CYAN)
                parts.append(f"{emoji} {name} {sc}stade {stage}{C.RESET}")
            elif cat == "chr":
                parts.append(f"{emoji} {name} {C.GRAY}(chronique){C.RESET}")
            elif v is not None:
                parts.append(f"{emoji} {name} ({v}j)")
            else:
                parts.append(f"{emoji} {name}")
        if parts:
            print(f" {C.RED}{C.BOLD}Maladies :{C.RESET} {' | '.join(parts)}")

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
    ("travailler_partiel", "Travailler à mi-temps (4h)", None, "💼 Travail & Carrière"),
    ("postuler", "Chercher un emploi", None, "💼 Travail & Carrière"),
    ("prendre_retraite", "Prendre sa retraite 🎉", None, "💼 Travail & Carrière"),
    ("benevole", "Faire du bénévolat", None, "🎮 Loisirs"),
    ("voyage", "Partir en voyage", None, "🎮 Loisirs"),
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
    ("acheter_maison", "Acheter un bien immobilier", None, "🏠 Immobilier"),
    ("vendre_maison",  "Vendre son bien immobilier",  None, "🏠 Immobilier"),
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
    "prendre_retraite": 0.5, "benevole": 4.0, "voyage": 4.0,
    "acheter_maison": 2.0, "vendre_maison": 1.0,
    "travailler_partiel": 4.0,
}

# --- Immobilier ---
# Format : (id, nom, emoji, prix, acompte_pct, standing, effets_quotidiens)
PROPERTIES = [
    ("studio",    "Studio",             "🏠",  2_000, 0.20, 1, {"fun": +1, "energie": +1}),
    ("appt_t2",   "Appartement T2",     "🏢",  4_500, 0.20, 2, {"fun": +1, "energie": +1, "social": +1}),
    ("appt_t3",   "Appartement T3",     "🏢",  8_000, 0.20, 3, {"fun": +2, "energie": +1, "social": +1}),
    ("maison_tv", "Maison de ville",    "🏡", 14_000, 0.25, 4, {"fun": +2, "energie": +2, "social": +2}),
    ("maison_c",  "Maison de campagne", "🌿", 20_000, 0.25, 5, {"fun": +3, "energie": +2, "social": +1}),
    ("villa",     "Villa",              "🏰", 32_000, 0.25, 6, {"fun": +4, "energie": +3, "social": +3}),
    ("manoir",    "Manoir",             "🏯", 50_000, 0.30, 7, {"fun": +6, "energie": +4, "social": +5}),
]

# Format : (label, durée_jours, taux_intérêt)
LOAN_TERMS = [
    ("Court terme  (30j)",  30, 0.03),
    ("Moyen terme  (60j)",  60, 0.05),
    ("Long terme   (90j)",  90, 0.08),
    ("Très long   (120j)", 120, 0.10),
]

def get_property_data(pid):
    for p in PROPERTIES:
        if p[0] == pid:
            return p
    return None

JOURS_SEMAINE = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

YEAR_LENGTH = 28   # 4 saisons × 7 jours

# Format : (nom, emoji, effets_quotidiens, poids_météos[soleil/nuag/pluie/orage/neige])
SEASONS = {
    "printemps": ("Printemps", "🌸", {"fun": +3},                  [35, 35, 20, 10,  0]),
    "ete":       ("Été",       "☀",  {"fun": +5, "energie": -2},   [50, 25, 15, 10,  0]),
    "automne":   ("Automne",   "🍂", {"fun": -2, "social": -1},    [15, 35, 40, 10,  0]),
    "hiver":     ("Hiver",     "❄",  {"fun": -3, "energie": -3},   [10, 30, 20,  5, 35]),
}
_SEASON_ORDER = ["printemps", "ete", "automne", "hiver"]

def get_season(age):
    sid = _SEASON_ORDER[(age % YEAR_LENGTH) // (YEAR_LENGTH // 4)]
    return sid, SEASONS[sid]

def get_available_actions(sim):
    """Retourne la liste des actions disponibles selon l'heure et le jour."""
    _, stage = get_stage(sim.age)
    blocked = set(stage[4])
    hour = sim.hour
    is_weekend = (sim.age % 7) >= 5

    is_retired = getattr(sim, 'retired', False)

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
        # Retraité : bloquer travail et candidature
        if is_retired and key in ("travailler", "postuler", "travailler_partiel"):
            continue
        # Mi-temps : uniquement si inscrit à l'université et a un emploi
        if key == "travailler_partiel":
            if not sim.education.is_enrolled() or not sim.job:
                continue
            if stage[1] in ("Enfant", "Adolescent"):
                continue
        # prendre_retraite : uniquement Senior non encore retraité
        if key == "prendre_retraite":
            if is_retired or stage[1] not in ("Senior",):
                continue
        # bénévolat : uniquement retraité
        if key == "benevole" and not is_retired:
            continue
        # voyage : adultes seulement (pas Enfant/Adolescent)
        if key == "voyage" and stage[1] in ("Enfant", "Adolescent"):
            continue
        # Achat immobilier : pas déjà propriétaire, pas Enfant/Adolescent
        if key == "acheter_maison":
            if getattr(sim, 'housing', None) or stage[1] in ("Enfant", "Adolescent"):
                continue
        # Vente : uniquement si propriétaire
        if key == "vendre_maison" and not getattr(sim, 'housing', None):
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

def maybe_contract_disease(sim):
    """Déclenchement quotidien des maladies selon l'âge, le style de vie et le hasard."""
    h = sim.health
    age = sim.age
    stress = getattr(sim, 'stress', 0)
    sport_level = sim.skills.levels.get('sport', 0)
    season_id, _ = get_season(age)

    # Multiplicateurs saisonniers
    _grippe_m = 3 if season_id == "hiver" else (1.5 if season_id == "automne" else 0.5)
    _gastro_m = 2 if season_id == "ete"   else 1.0

    # ── Infections (tous âges) ──────────────────────────────────────
    if "grippe" not in h.diseases and "rhume" not in h.diseases:
        if random.randint(1, 200) <= max(1, int(2 * _grippe_m)):
            h.get_sick("grippe")
            if not AUTOPILOT:
                slow_print(f" {C.YELLOW}🤒 Tu commences à avoir de la fièvre... c'est la grippe.{C.RESET}", 0.02)
    if "rhume" not in h.diseases and "grippe" not in h.diseases:
        if random.randint(1, 100) <= max(1, int(3 * _grippe_m)):
            h.get_sick("rhume")
    if "gastro" not in h.diseases and sim.needs["hygiene"] < 30:
        if random.randint(1, 100) <= max(1, int(4 * _gastro_m)):
            h.get_sick("gastro")
            if not AUTOPILOT:
                slow_print(f" {C.YELLOW}🤢 Gastro-entérite... malaise garanti.{C.RESET}", 0.02)
    # Bronchite (grippe qui traîne)
    if ("grippe" in h.diseases and h.diseases["grippe"] is not None
            and h.diseases["grippe"] <= 2 and "bronchite" not in h.diseases
            and random.randint(1, 100) <= 20):
        h.get_sick("bronchite")
        if not AUTOPILOT:
            slow_print(f" {C.RED}😮 La grippe a évolué en bronchite...{C.RESET}", 0.02)
    # Pneumonie (bronchite grave ou HP très bas + grippe)
    if ("bronchite" in h.diseases and h.diseases.get("bronchite") is not None
            and h.diseases["bronchite"] <= 2 and "pneumonie" not in h.diseases
            and random.randint(1, 100) <= 15):
        h.get_sick("pneumonie")
        if not AUTOPILOT:
            slow_print(f" {C.RED}🫁 Pneumonie déclarée — consultation d'urgence recommandée !{C.RESET}", 0.03)

    # ── Maladies chroniques (âge-dépendant) ─────────────────────
    if age >= 25 and "hypertension" not in h.diseases:
        prob = max(0, int((age - 22) * 0.3 + (stress > 60) * 3 + (sport_level < 2) * 2))
        if random.randint(1, 1000) <= prob:
            h.get_sick("hypertension")
            if not AUTOPILOT:
                slow_print(f" {C.YELLOW}💗 Ton médecin détecte une hypertension artérielle.{C.RESET}", 0.02)
    if age >= 20 and "asthme" not in h.diseases:
        if random.randint(1, 2000) <= 2:
            h.get_sick("asthme")
            if not AUTOPILOT:
                slow_print(f" {C.YELLOW}💨 On diagnostique un asthme. Évite les efforts intenses.{C.RESET}", 0.02)
    if age >= 32 and "arthrite" not in h.diseases:
        if random.randint(1, 1000) <= max(1, age - 30):
            h.get_sick("arthrite")
            if not AUTOPILOT:
                slow_print(f" {C.YELLOW}🦵 Douleurs articulaires persistantes — c'est de l'arthrite.{C.RESET}", 0.02)
    if age >= 35 and "diabete" not in h.diseases:
        prob = max(0, int((age - 32) * 0.5 + (sport_level < 2) * 2))
        if random.randint(1, 1000) <= prob:
            h.get_sick("diabete")
            if not AUTOPILOT:
                slow_print(f" {C.YELLOW}🩸 Bilan sanguin : diabète de type 2 diagnostiqué.{C.RESET}", 0.02)
    if age >= 40 and "insuff_card" not in h.diseases:
        prob = max(0, int((age - 38) * 0.4 + ("hypertension" in h.diseases) * 5 + (stress > 70) * 3))
        if random.randint(1, 1000) <= prob:
            h.get_sick("insuff_card")
            if not AUTOPILOT:
                slow_print(f" {C.RED}❤ Diagnostic : insuffisance cardiaque. Prenez soin de vous.{C.RESET}", 0.02)

    # ── Cancers et maladies fatales (seniors) ───────────────────
    if age >= 35 and not h.has_fatal():
        prob = max(0, int((age - 32) * 0.3 + (stress > 70) * 2 + ("hypertension" in h.diseases) * 1))
        if random.randint(1, 1000) <= prob:
            cancer_type = random.choices(
                ["cancer_poumon", "cancer_colon", "cancer_peau", "leucemie"],
                weights=[30, 30, 30, 10]
            )[0]
            h.get_sick(cancer_type)
            _names = {"cancer_poumon": "cancer du poumon", "cancer_colon": "cancer colorectal",
                      "cancer_peau": "mélanome", "leucemie": "leucémie"}
            if not AUTOPILOT:
                slow_print(f"\n {C.RED}⚕ Les examens révèlent : {_names[cancer_type]} (stade 1).{C.RESET}", 0.03)
                slow_print(f" {C.YELLOW}Consulte régulièrement ton médecin pour ralentir la progression.{C.RESET}", 0.02)

    # ── Neurodégénératives (très seniors) ─────────────────────
    if age >= 42 and not any(d in h.diseases for d in ("alzheimer", "parkinson")):
        prob = max(0, int((age - 40) * 0.6))
        if random.randint(1, 1000) <= prob:
            disease_id = random.choice(["alzheimer", "parkinson"])
            h.get_sick(disease_id)
            if not AUTOPILOT:
                slow_print(f"\n {C.RED}🧠 Diagnostic : {DISEASES[disease_id][0]} (stade 1).{C.RESET}", 0.03)

def action_dormir(sim):
    slow_print(f"\n {C.BLUE}Tu dors profondément pendant 8 heures... 💤{C.RESET}", 0.02)
    sim.modify(energie=+60, hygiene=-10, faim=-20)
    sim.tick(8)
    _prev_sid = get_season(sim.age)[0]
    sim.age += 1
    sim.hour = 7    # réveil à 07h00
    _sid, _sdata = get_season(sim.age)
    sim.weather.new_day(_sdata[3])
    if _sid != _prev_sid:
        _msgs = {
            "printemps": f"🌸 La nature se réveille — {C.GREEN}Printemps{C.RESET} !",
            "ete":       f"☀  Le soleil est au zénith — {C.YELLOW}Été{C.RESET} !",
            "automne":   f"🍂 Les feuilles tombent — {C.YELLOW}Automne{C.RESET} !",
            "hiver":     f"❄  Un froid glacial s'installe — {C.CYAN}Hiver{C.RESET} !",
        }
        slow_print(f"\n {_msgs[_sid]}", 0.03)
    slow_print(f" {C.CYAN}Nouveau jour ! {_sdata[1]} {_sdata[0]} — Météo : {sim.weather.emoji} {sim.weather.name}{C.RESET}", 0.02)
    # Effets saisonniers quotidiens
    sim.modify(**_sdata[2])
    _prev_stages = {k: sim.health.disease_stage.get(k, 1)
                    for k in sim.health.diseases
                    if DISEASES.get(k, ('','','',0,0,'inf'))[5] in ("fat", "neuro")}
    sim.health.tick_day()
    for _did, _old in _prev_stages.items():
        if _did in sim.health.diseases:
            _new = sim.health.disease_stage.get(_did, 1)
            if _new > _old:
                _sc = C.RED if _new >= 3 else C.YELLOW
                slow_print(f" {_sc}⚠ {DISEASES[_did][1]} {DISEASES[_did][0]} a progressé au stade {_new} !{C.RESET}", 0.02)
                if _new == 3:
                    slow_print(f" {C.RED}Stade terminal — consultation médicale d'urgence !{C.RESET}", 0.02)
    for child in sim.children:
        child.tick_day()

    # ── Pension de retraite ───────────────────────────────────────
    if getattr(sim, 'retired', False) and sim.pension > 0:
        sim.money += sim.pension
        slow_print(f" {C.GREEN}💰 Pension du jour : +${sim.pension}  (Total : ${sim.money}){C.RESET}", 0.02)

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
        else:
            season_msg = trigger_season_event(sim) if random.randint(1, 100) <= 35 else None
            if season_msg:
                sim.last_event = season_msg
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

    # ── Remboursement immobilier ──────────────────────────────────
    if sim.housing:
        _mh = sim.housing
        if _mh["loan_remaining"] > 0:
            _payment = min(_mh["daily_payment"], _mh["loan_remaining"])
            if sim.money >= _payment:
                sim.money -= _payment
                _mh["loan_remaining"] = max(0, _mh["loan_remaining"] - _payment)
                _mh["days_missed"] = 0
                if _mh["loan_remaining"] == 0:
                    _pd = get_property_data(_mh["property_id"])
                    slow_print(f" {C.GREEN}🏠 Crédit remboursé ! Tu es pleinement propriétaire de "
                               f"{_pd[2]} {_pd[1]} !{C.RESET}", 0.02)
            else:
                _mh["days_missed"] += 1
                slow_print(f" {C.RED}⚠ Échéance immobilière non payée (${_payment}) ! "
                           f"Impayés : {_mh['days_missed']}/3{C.RESET}", 0.02)
                sim.modify(fun=-10, social=-5)
                sim.stress = min(100, getattr(sim, 'stress', 0) + 15)
                if _mh["days_missed"] >= 3:
                    _pd = get_property_data(_mh["property_id"])
                    slow_print(f" {C.RED}💔 Saisie ! {_pd[2]} {_pd[1]} t'est retirée "
                               f"faute de paiements.{C.RESET}", 0.02)
                    sim.modify(fun=-30, social=-20)
                    sim.stress = min(100, sim.stress + 30)
                    sim.housing = None
        # Effets quotidiens du bien immobilier (confort du logement)
        if sim.housing:
            _pd2 = get_property_data(sim.housing["property_id"])
            if _pd2:
                sim.modify(**_pd2[6])

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

    maybe_contract_disease(sim)

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
    sim.tick(4)   # matinée (4h)
    # ── Pause déjeuner ─────────────────────────────────────────
    lunch_cost = 15
    if sim.money >= lunch_cost:
        sim.money -= lunch_cost
        sim.modify(faim=+35)
        slow_print(f" {C.GRAY}⌚ Pause déjeuner — repas à la cantine (+35 faim, -${lunch_cost}){C.RESET}", 0.02)
    else:
        sim.modify(faim=+15)
        slow_print(f" {C.GRAY}⌚ Pause déjeuner — sandwich rapide (+15 faim){C.RESET}", 0.02)
    sim.tick(4)   # après-midi (4h)
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

def action_travailler_partiel(sim):
    """Demi-journée de travail — idéal pour financer les études sans s'épuiser."""
    if not sim.job:
        slow_print(f"\n {C.RED}Tu n'as pas de travail ! Postule d'abord.{C.RESET}", 0.02)
        _cont()
        return
    if sim.days_burned_out > 0:
        slow_print(f"\n {C.RED}Tu es en burn-out... Repose-toi.{C.RESET}", 0.02)
        _cont()
        return
    stress_penalty = 5 if sim.stress > 70 else 0
    base_salary = next(sal for lbl, sal, *_ in JOBS if lbl == sim.job)
    salary = int(base_salary * 0.5 * (1 + sim.skills.bonus('travail')) * sim.salary_multiplier * sim.traits.salary_mult())
    slow_print(f"\n {C.YELLOW}Tu travailles une demi-journée comme {sim.job}... ⏰{C.RESET}", 0.02)
    sim.money += salary
    sim.job_days += 1
    sim.modify(energie=-(12 + stress_penalty), faim=-10, social=+8, hygiene=-5, fun=+3)
    sim.tick(4)
    stress_gain = 4
    if "anxieux" in sim.traits.active:   stress_gain = 6
    if "paresseux" in sim.traits.active: stress_gain = 2
    sim.stress = min(100, sim.stress + stress_gain)
    slow_print(f" {C.GREEN}+${salary} gagnés ! Total : ${sim.money}{C.RESET}", 0.02)
    lvl = sim.skills.gain('travail', 5)
    if lvl: slow_print(f" {C.GREEN}Compétence Travail → Niv. {lvl} ! 💼{C.RESET}", 0.02)
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
    sim.modify(energie=+15, fun=+15)
    sim.stress = max(0, sim.stress - 8)
    sim.health.mental = min(100, sim.health.mental + 5)
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
    h = sim.health
    has_fat = h.has_fatal()
    max_stage = h.fatal_max_stage()
    has_chr = any(DISEASES.get(d, ('','','',0,0,'inf'))[5] == "chr" for d in h.diseases)
    if has_fat and max_stage >= 2:
        cost, visit = 400, "traitement oncologique"
    elif has_fat:
        cost, visit = 250, "suivi oncologique"
    elif has_chr:
        cost, visit = 150, "suivi maladie chronique"
    else:
        cost, visit = 80, "consultation"
    if sim.money < cost:
        print(f"\n {C.RED}Pas assez d'argent pour la {visit} (${cost}).{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.CYAN}Tu consultes un médecin... 👨‍⚕️  ({visit}){C.RESET}", 0.02)
    sim.money -= cost
    h.hp = min(100, h.hp + 20)
    cured, managed = [], []
    for did in list(h.diseases):
        if did not in DISEASES: continue
        cat = DISEASES[did][5]
        if cat in ("inf", "trau", "ment"):
            del h.diseases[did]
            h.disease_stage.pop(did, None)
            cured.append(DISEASES[did][0])
        elif cat == "chr":
            h.hp = min(100, h.hp + 8)
            managed.append(f"{DISEASES[did][0]} (chronique)")
        elif cat in ("fat", "neuro"):
            stage = h.disease_stage.get(did, 1)
            if stage > 1 and random.randint(1, 100) <= 30:
                h.disease_stage[did] = stage - 1
                slow_print(f" {C.GREEN}✨ Le traitement a fait régresser {DISEASES[did][0]} au stade {stage-1} !{C.RESET}", 0.02)
            managed.append(f"{DISEASES[did][0]} stade {h.disease_stage.get(did, 1)}")
    if cured:
        slow_print(f" {C.GREEN}Guéri(e) : {', '.join(cured)}{C.RESET}", 0.02)
    if managed:
        slow_print(f" {C.CYAN}Suivi : {', '.join(managed)}{C.RESET}", 0.02)
    slow_print(f" {C.GREEN}Santé +20. (-${cost}){C.RESET}", 0.02)
    sim.modify(energie=+5)
    sim.tick(1)
    _cont()

def action_medicament(sim):
    cost = 20
    h = sim.health
    treatable = {k for k in h.diseases
                 if k in DISEASES and DISEASES[k][5] in ("inf", "trau", "ment")}
    if not treatable:
        msg = ("Les médicaments n'ont pas d'effet sur les maladies chroniques ou graves."
               if h.is_sick() else "Tu n'as pas de maladie aiguë à traiter.")
        print(f"\n {C.YELLOW}{msg}{C.RESET}")
        _cont()
        return
    if sim.money < cost:
        print(f"\n {C.RED}Pas assez d'argent (${cost}).{C.RESET}")
        _cont()
        return
    slow_print(f"\n {C.YELLOW}Tu prends tes médicaments... 💊{C.RESET}", 0.02)
    sim.money -= cost
    h.hp = min(100, h.hp + 8)
    for d in treatable:
        if h.diseases.get(d) is not None:
            h.diseases[d] = max(1, h.diseases[d] - 1)
    slow_print(f" {C.GREEN}Santé +8, maladies aiguës accélérées. (-${cost}){C.RESET}", 0.02)
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

CHILD_NAMES = _PRENOMS_MASC + _PRENOMS_FEM

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
        "retired": sim.retired,
        "pension": sim.pension,
        "housing": sim.housing,
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
        "health": {"hp": sim.health.hp, "mental": sim.health.mental,
                   "diseases": sim.health.diseases, "disease_stage": sim.health.disease_stage},
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

# --- Retraite ---

def calculate_pension(sim):
    if sim.job:
        base = next((sal for lbl, sal, *_ in JOBS if lbl == sim.job), 80)
    else:
        base = 80
    cotisation = min(1.0, sim.job_days / 30)
    pension = int(base * 0.60 * cotisation * sim.salary_multiplier)
    if sim.age >= 45:
        pension = int(pension * 1.15)   # bonus retraite tardive
    if sim.education.has_diploma():
        pension = int(pension * 1.05)   # bonus diplômé
    return max(60, pension)

def action_prendre_retraite(sim):
    clear()
    pension = calculate_pension(sim)
    sim.retired = True
    sim.pension = pension

    slow_print(f"\n {C.BOLD}{C.YELLOW}🎉 Tu prends ta retraite bien méritée !{C.RESET}", 0.03)
    slow_print(f"\n {C.BOLD}── Bilan de carrière ──────────────────{C.RESET}", 0.02)
    job_label = sim.job or "Sans emploi"
    if sim.job:
        base_sal = next((sal for lbl, sal, *_ in JOBS if lbl == sim.job), 80)
    else:
        base_sal = 80
    cotisation_pct = min(100, int(sim.job_days / 30 * 100))
    bonus_str = "tardive +15%" if sim.age >= 45 else "normale"
    slow_print(f"   Dernier poste      : {job_label}", 0.02)
    slow_print(f"   Jours travaillés   : {sim.job_days}  ({cotisation_pct}% de carrière complète)", 0.02)
    slow_print(f"   Salaire de pointe  : ${int(base_sal * sim.salary_multiplier)}/j  (×{sim.salary_multiplier:.2f})", 0.02)
    slow_print(f"   Type de retraite   : {bonus_str}", 0.02)
    slow_print(f"\n {C.GREEN}💰 Pension accordée : ${pension}/jour — versée chaque matin.{C.RESET}", 0.03)
    if pension >= 400:
        slow_print(f" {C.GREEN}✨ Retraite dorée — profite pleinement !{C.RESET}", 0.02)
    elif pension >= 200:
        slow_print(f" {C.CYAN}Bonne retraite — tu as de quoi vivre confortablement.{C.RESET}", 0.02)
    else:
        slow_print(f" {C.YELLOW}Retraite modeste — gère ton budget avec soin.{C.RESET}", 0.02)

    sim.stress = max(0, sim.stress - 30)
    sim.modify(fun=+15, social=+10)
    slow_print(f" {C.GREEN}Le stress fond... Bienvenue dans la liberté ! 🌅{C.RESET}", 0.02)
    _cont()

def action_benevole(sim):
    slow_print(f"\n {C.GREEN}Tu consacres ta matinée au bénévolat... 🤝{C.RESET}", 0.02)
    sim.modify(social=+25, fun=+20, energie=-15, faim=-10)
    sim.tick(4)
    sim.stress = max(0, sim.stress - 10)
    lvl = sim.skills.gain('social', 8)
    if lvl: slow_print(f" {C.GREEN}Compétence Social → Niv. {lvl} !{C.RESET}", 0.02)
    slow_print(f" {C.CYAN}Tu te sens utile et pleinement épanoui(e). 💚{C.RESET}", 0.02)
    _cont()

def action_voyage(sim):
    if sim.money < 200:
        slow_print(f"\n {C.RED}Il te faut au moins $200 pour partir en voyage.{C.RESET}", 0.02)
        _cont()
        return
    cost = min(random.randint(150, 300), sim.money - 50)
    destinations = [
        ("Paris", "🗼"), ("Rome", "🏛"), ("Lisbonne", "🌊"), ("Barcelone", "🌞"),
        ("Prague", "🏰"), ("Amsterdam", "🚲"), ("Vienne", "🎶"),
        ("Tokyo", "🗾"), ("New York", "🗽"), ("Marrakech", "🕌"),
    ]
    dest, emoji = random.choice(destinations)
    slow_print(f"\n {C.CYAN}✈ Tu pars en voyage à {dest} {emoji}...{C.RESET}", 0.02)
    sim.money -= cost
    sim.modify(fun=+40, social=+20, energie=-10, faim=-15)
    sim.tick(4)
    slow_print(f" {C.YELLOW}-${cost} — Dépenses de voyage{C.RESET}", 0.02)
    slow_print(f" {C.GREEN}Quel dépaysement ! Ces souvenirs resteront gravés... 🌍{C.RESET}", 0.02)
    _cont()

def action_acheter_maison(sim):
    if sim.housing:
        _pd = get_property_data(sim.housing["property_id"])
        slow_print(f"\n {C.RED}Tu possèdes déjà {_pd[2]} {_pd[1]}. Vends-la d'abord.{C.RESET}", 0.02)
        _cont()
        return

    slow_print(f"\n {C.YELLOW}🏘 Marché immobilier — Propriétés disponibles :{C.RESET}", 0.02)
    print()
    for i, (pid, nom, emoji, prix, acompte_pct, standing, effets) in enumerate(PROPERTIES, 1):
        acompte = int(prix * acompte_pct)
        eff_str = "  ".join(f"{'+'if v>0 else ''}{v} {k}" for k, v in effets.items())
        ok = "✅" if sim.money >= acompte else f"{C.RED}❌ manque ${acompte - sim.money:,}{C.RESET}"
        print(f" {C.CYAN}[{i}]{C.RESET} {emoji} {nom:22s}  "
              f"{C.BOLD}${prix:,}{C.RESET}  Acompte {C.YELLOW}${acompte:,}{C.RESET} {ok}"
              f"  {C.GRAY}({eff_str}){C.RESET}")
    print(f"\n {C.CYAN}[ 0]{C.RESET} Annuler\n")

    try:
        choice = input(f" {C.BOLD}Propriété : {C.RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "0"

    if not choice.isdigit() or int(choice) == 0 or int(choice) > len(PROPERTIES):
        slow_print(f" {C.GRAY}Transaction annulée.{C.RESET}", 0.02)
        _cont()
        return

    pid, nom, emoji, prix, acompte_pct, standing, effets = PROPERTIES[int(choice) - 1]
    acompte = int(prix * acompte_pct)

    if sim.money < acompte:
        slow_print(f"\n {C.RED}Fonds insuffisants (${acompte:,} requis, tu as ${sim.money}).{C.RESET}", 0.02)
        _cont()
        return

    loan_principal = prix - acompte
    slow_print(f"\n {C.YELLOW}💳 Choisir la durée du crédit (emprunt : ${loan_principal:,}) :{C.RESET}", 0.02)
    print()
    for i, (lbl, days, rate) in enumerate(LOAN_TERMS, 1):
        total = int(loan_principal * (1 + rate))
        daily = max(1, round(total / days))
        print(f" {C.CYAN}[{i}]{C.RESET} {lbl:22s}  {C.BOLD}${daily}/jour{C.RESET}  "
              f"Total remboursé ${total:,}  Taux {int(rate*100)}%")
    print(f"\n {C.CYAN}[ 0]{C.RESET} Annuler\n")

    try:
        tc = input(f" {C.BOLD}Durée : {C.RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        tc = "0"

    if not tc.isdigit() or int(tc) == 0 or int(tc) > len(LOAN_TERMS):
        slow_print(f" {C.GRAY}Transaction annulée.{C.RESET}", 0.02)
        _cont()
        return

    _, term_days, interest_rate = LOAN_TERMS[int(tc) - 1]
    loan_total = int(loan_principal * (1 + interest_rate))
    daily_payment = max(1, round(loan_total / term_days))

    sim.money -= acompte
    sim.housing = {
        "property_id": pid,
        "purchase_price": prix,
        "loan_total": loan_total,
        "loan_remaining": loan_total,
        "daily_payment": daily_payment,
        "days_missed": 0,
    }
    slow_print(f"\n {C.GREEN}🎉 Félicitations ! Tu es propriétaire d'un(e) {emoji} {nom} !{C.RESET}", 0.02)
    slow_print(f" Acompte versé : {C.YELLOW}-${acompte:,}{C.RESET}  "
               f"Crédit : ${daily_payment}/jour pendant {term_days} jours.", 0.02)
    sim.modify(fun=+15, social=+10)
    sim.tick(2)
    _cont()


def action_vendre_maison(sim):
    if not sim.housing:
        slow_print(f"\n {C.RED}Tu ne possèdes aucun bien immobilier.{C.RESET}", 0.02)
        _cont()
        return

    _mh = sim.housing
    _pd = get_property_data(_mh["property_id"])
    pid, nom, emoji, prix, *_ = _pd
    equity = max(0, _mh["purchase_price"] - _mh["loan_remaining"])

    slow_print(f"\n {C.YELLOW}🏘 Vente de {emoji} {nom}{C.RESET}", 0.02)
    slow_print(f" Prix d'estimation : ${_mh['purchase_price']:,}", 0.02)
    slow_print(f" Capital restant dû : ${_mh['loan_remaining']:,}", 0.02)
    slow_print(f" Gain net : {C.GREEN}${equity:,}{C.RESET}", 0.02)

    try:
        confirm = input(f"\n {C.BOLD}Confirmer la vente ? (o/n) : {C.RESET}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        confirm = "n"

    if confirm != "o":
        slow_print(f" {C.GRAY}Vente annulée.{C.RESET}", 0.02)
        _cont()
        return

    sim.money += equity
    sim.housing = None
    slow_print(f"\n {C.GREEN}Vente effectuée ! +${equity:,} récupérés.{C.RESET}", 0.02)
    sim.modify(fun=-5)
    sim.tick(1)
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
    "travailler_partiel": action_travailler_partiel,
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
    "prendre_retraite": action_prendre_retraite,
    "benevole": action_benevole,
    "voyage": action_voyage,
    "acheter_maison": action_acheter_maison,
    "vendre_maison": action_vendre_maison,
}

# --- IA Autopilote ---
_AUTO_NAMES = _PRENOMS_MASC + _PRENOMS_FEM

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

    # ── Retraite ─────────────────────────────────────────────────
    if getattr(sim, 'retired', False):
        # Pré-sleep : même logique que pour les actifs après 22h
        if sim.hour >= 22:
            if n["faim"]    < _faim_safe:    return "snack" if sim.money < 5 else "manger"
            if n["hygiene"] < _hygiene_safe: return "douche"
            if n["social"] < 65 and sim.hour < 23:                         return "appel"
            if n["fun"]     < 50 and sim.hour < 23 and "mediter" not in blocked: return "mediter"
            return "dormir"
        # Seuils calés sur le coût bénévolat/voyage (4h, Senior : énergie ~-9/h, faim ~-6/h)
        # Urgence HP : hygiene critique → douche AVANT dormir (sinon HP drain pendant le sleep)
        if n["hygiene"] < 25 and n["energie"] > 20: return "douche"
        if n["faim"] < 70:    return "snack" if sim.money < 5 else "manger"
        # Hygiene faible AVANT de dormir : se laver en priorité pour éviter HP drain nocturne
        if n["energie"] < 60 and n["hygiene"] < 50 and n["energie"] > 20: return "douche"
        if n["energie"] < 60: return "sieste" if n["energie"] >= 35 else "dormir"
        if n["hygiene"] < 65: return "douche"
        if n["vessie"] < 50:  return "toilettes"
        # Seuils alignés sur le chemin actif (44/42) pour éviter drain mental en retraite
        if n["fun"] < 44 and "mediter" not in blocked:  return "mediter"
        if n["social"] < 42:  return "appel"
        if h.is_sick():
            if sim.money >= 20: return "medicament"
            return "lire"
        # Adoption en retraite (chemin actif ne s'applique pas aux retraités)
        if (not sim.pet and "adopter" not in blocked
                and sim.money > 250 and random.random() < 0.25):          return "adopter"
        # Garde prédictive avant bénévolat : vérifier les réserves post-4h
        _benv_ok = (
            n["energie"]          > 75 and    # energie après bénév. : ~75-35=40 > seuil
            n["faim"]             > 75 and    # faim après bénév.    : ~75-32=43 > seuil
            n["hygiene"] - 12     > 55 and    # hygiene après bénév.  : marge sécurité HP
            n["vessie"]           > 60        # vessie après 4h (-28) : >32 OK
        )
        # Voyage ponctuel si finances et formes le permettent
        if (sim.money >= 250 and n["fun"] < 65 and _benv_ok and random.random() < 0.25):
            return "voyage"
        # Bénévolat : activité sociale principale en retraite
        if _benv_ok and (n["social"] < 70 or n["fun"] < 70):
            return "benevole"
        pool_r = ["lire", "jardiner", "mediter", "tv", "jeux", "appel"]
        if sim.children:              pool_r += ["famille", "devoirs"]
        if sim.relationship.level >= 4: pool_r += ["intimite"]
        if sim.money >= 20 and sim.skills.levels.get("cuisine", 0) > 0:
            pool_r += ["gastronomie"]
        pool_r = [a for a in pool_r if a not in blocked]
        return random.choice(pool_r) if pool_r else "lire"

    # Décision de prendre la retraite : IA attend le jour 45 (retraite tardive + 15%)
    # job_days >= 25 garantit une pension décente ET empêche une retraite prématurée
    # d'un sim qui n'a jamais travaillé (résout le bug "sans emploi" seed 29).
    if stage[1] == "Senior" and sim.age >= 45:
        if sim.education.is_enrolled():
            pass   # finir les études d'abord
        elif not h.is_sick() and sim.money >= 200 and sim.job_days >= 18 and sim.job:
            return "prendre_retraite"

    # Urgence absolue : faim=0 → manger avant tout (sinon danger_turns → famine)
    if n["faim"] == 0:
        return "snack" if sim.money < 5 else "manger"

    if sim.hour >= 22:
        # Préparation pré-sleep : éviter famine/HP drain pendant le sleep
        if n["faim"]    < _faim_safe:    return "snack" if sim.money < 5 else "manger"
        if n["hygiene"] < _hygiene_safe: return "douche"
        if n["vessie"]  < 30:            return "toilettes"
        # Garde social pré-sleep (8h tick -24 → social < 42 passerait sous 25 → mental -16)
        if n["social"] < 65 and sim.hour < 23:                             return "appel"
        if n["fun"]     < 50 and sim.hour < 23 and "mediter" not in blocked:
            return "mediter"   # dormir avec plus de fun → réveiller avec moins de drain
        return "dormir"

    # ═══════════════════════════════════════════════════════════════
    # MODE MALADIE : GUÉRIR en priorité (médicament réduit durée de 1j/prise).
    # ═══════════════════════════════════════════════════════════════
    if h.is_sick():
        sleep_faim_cost = 60
        sleep_hyg_cost  = 10 + 8 * (2 + extra_h)
        faim_safe    = 15 + sleep_faim_cost
        hygiene_safe = 22 + sleep_hyg_cost

        # Maladies fatales : consulter quand le stade progresse, pas en urgence permanente
        if h.has_fatal():
            max_stage = h.fatal_max_stage()
            fat_cost = 400 if max_stage >= 2 else 250
            # Tente le médecin tous les ~3 jours si budget (pas chaque tour)
            if (sim.money >= fat_cost * 1.5 and n["faim"] > 40 and n["energie"] > 25
                    and sim.age % 3 == 0):
                return "medecin"

        about_to_sleep = n["energie"] < 15

        if about_to_sleep:
            if n["energie"] < 10 and sim.money >= 80:    return "medecin"
            needs_meds_now = any(v is not None and v > 1 for v in h.diseases.values())
            if n["energie"] < 10 and needs_meds_now and sim.money >= 20: return "medicament"
            if n["faim"]    < faim_safe:             return "snack" if sim.money < 5 else "manger"
            if n["hygiene"] < hygiene_safe:          return "douche"
            return "dormir"

        # Éveillé et malade → GUÉRIR
        if n["faim"]    < 45:                        return "snack" if sim.money < 5 else "manger"
        if n["hygiene"] < 45:                        return "douche"
        if sim.money >= 80 and not h.has_fatal():    return "medecin"
        has_treatable = any(
            h.diseases.get(k) is not None and h.diseases[k] > 1
            and DISEASES.get(k, ('','','',0,0,'inf'))[5] in ("inf", "trau", "ment")
            for k in h.diseases
        )
        if has_treatable and sim.money >= 20:        return "medicament"
        if n["energie"] < 60 and "sieste" not in blocked: return "sieste"
        if n["faim"]    < 60:                        return "manger"
        if n["fun"] < 60 and "mediter" not in blocked: return "mediter"
        return "lire"

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
        # Garde social pré-sleep urgence (même logique que 22h : 8h tick -24 social)
        if n["social"] < 65 and n["energie"] > 20:                         return "appel"
        if n["fun"] < 50 and "mediter" not in blocked and n["energie"] > 15: return "mediter"
        return "dormir"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 2 : urgence santé (HP très bas ou mental effondré)
    # Seuil bas (65) : seule une détresse réelle bloque le travail/études.
    # La santé préventive (hp < 85) reste en priorité 3, après la carrière.
    # ═══════════════════════════════════════════════════════════════
    if h.hp < 65 and sim.money >= 80:                                     return "medecin"
    if h.mental < 30:
        if n["fun"] < 80 and "mediter" not in blocked:                    return "mediter"
        return "appel"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 2b : garde proactive fun/social — prévenir effondrement mental
    # fun < 44 ou social < 42 → récupération AVANT de travailler/étudier.
    # Sans ce garde, 8h de travail avec fun=20 → mental -16 pts/jour.
    # Seuils identiques à PRIORITÉ 5 : la différence clé est que ces checks
    # se font AVANT la carrière (lun-ven inclus), pas seulement le week-end.
    # Effet secondaire : l'énergie consommée par appel/mediter empêche naturellement
    # le double-shift (2e journée de travail dans la même journée).
    # ═══════════════════════════════════════════════════════════════
    if n["fun"] < fun_thresh and "mediter" not in blocked:                return "mediter"
    if n["social"] < 42:                                                   return "appel"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 3 : carrière & études — engagements fermes
    # Études : 7j/7. Travail : lun-ven.
    # Seule l'urgence physique (énergie/faim sous seuil minimal) peut différer.
    # ═══════════════════════════════════════════════════════════════
    if "travailler" not in blocked:
        edu = sim.education

        # A) Pas de job → postuler immédiatement
        if not sim.job and jobs_available(edu):
            return "postuler"

        # B) Diplôme → re-postuler si poste plus payant disponible
        if edu.has_diploma():
            best = max(jobs_available(edu), key=lambda x: x[1], default=None)
            if best:
                cur_sal = next((s for lb, s, *_ in JOBS if lb == sim.job), 0)
                if best[1] > cur_sal:
                    return "postuler"

        # Seuils minimaux : juste assez pour tenir une journée de cours ou de travail
        _can_work  = n["energie"] > 25 and n["faim"] > 20 and n["hygiene"] > 20
        _can_study = n["energie"] > 20 and n["faim"] > 15

        # C) Études en cours → 7j/7, toutes priorités secondaires cèdent
        if edu.is_enrolled():
            session_cost = STUDY_DOMAINS[edu.enrolled_domain][3]
            _time_ok_study = sim.hour + 6 <= 23   # session 6h doit finir avant minuit
            if sim.money >= session_cost and _can_study and _time_ok_study:
                # Gardes pré-étude : etudier = modify(-10,-5) + tick(6) → fun-28, social-23
                # seuil 72 : fun post-étude = 72-28 = 44 >= fun_thresh
                if n["fun"] < 72 and "mediter" not in blocked:              return "mediter"
                if n["social"] < 65:                                        return "appel"
                return "etudier"
            # Pas de job → postuler d'abord pour financer les études
            if not sim.job and jobs_available(edu):
                return "postuler"
            # Argent insuffisant → mi-temps pour financer (7j/7, moins épuisant)
            if sim.job and _can_work and sim.hour + 4 <= 23:
                return "travailler_partiel"
            # Récupération minimale si physiquement incapable
            if not _can_study:
                if n["faim"] <= 15:    return "snack" if sim.money < 5 else "manger"
                return "sieste" if n["energie"] >= 20 else "dormir"

        # D) Pas de diplôme → s'inscrire dès que les fonds permettent
        elif not edu.has_diploma() and sim.money >= 350 and "inscrire" not in blocked:
            return "inscrire"

        # E) Travailler lun-ven — présence systématique sauf urgence physique
        # La pause déjeuner dans action_travailler couvre la faim, pas besoin de pré-manger.
        elif not is_weekend and sim.job:
            if _can_work:
                return "travailler"
            # Récupération rapide si incapable physiquement
            if n["faim"] <= 20:    return "snack" if sim.money < 5 else "manger"
            return "sieste" if n["energie"] >= 20 else "dormir"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 4 : animal de compagnie
    # Avant la santé proactive : le check hp<85 → medecin bloquerait sinon
    # quasi-systématiquement (HP moy ~77), empêchant toute adoption.
    # ═══════════════════════════════════════════════════════════════
    if sim.pet and sim.pet.hunger    < 35:                                return "nourrir"
    if sim.pet and sim.pet.happiness < 30:                                return "jouer_pet"
    if (not sim.pet and "adopter" not in blocked
            and sim.money > 250 and random.random() < 0.25):              return "adopter"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 4b : santé proactive (hp modérément bas, mental fragile)
    # S'exécute uniquement quand il n'y a pas de travail/études imminent
    # (week-end, après les cours, ou sim sans emploi).
    # ═══════════════════════════════════════════════════════════════
    if h.hp < 85 and sim.money >= 80:                                     return "medecin"
    if h.mental < 45 and sim.money >= 60:                                 return "psy"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 5 : récupération préventive (loisirs / social / sieste)
    # Ces actions n'ont lieu que si aucun travail ni étude n'est imminent.
    # ═══════════════════════════════════════════════════════════════
    energie_work_min = 25 + 8 * (2 + extra_e) + 3
    if n["energie"] < min(55, energie_work_min) and n["faim"] >= 20 and "sieste" not in blocked:
        return "sieste"

    if n["social"] < 42:                                                   return "appel"

    if n["fun"] < fun_thresh and "mediter" not in blocked:                return "mediter"
    if n["fun"] < fun_thresh - 10 and n["energie"] > 55 and n["faim"] > 45:
        if "tv" not in blocked:                                            return "tv"

    # ═══════════════════════════════════════════════════════════════
    # PRIORITÉ 5b : immobilier — acheter dès que les finances le permettent
    # ═══════════════════════════════════════════════════════════════
    if not getattr(sim, 'housing', None) and "acheter_maison" not in blocked:
        salary = next((sal for lbl, sal, *_ in JOBS if lbl == sim.job), 0)
        if getattr(sim, 'retired', False):
            salary = sim.pension
        if salary > 0:
            # Vérifie s'il y a une propriété abordable (même logique que ai_auto_acheter_maison)
            money_buffer = 240 + 10 * (15 * len(sim.children) if sim.children else 0)
            for prop in reversed(PROPERTIES):
                pid, nom, emoji, prix, acompte_pct, standing, effets = prop
                acompte = int(prix * acompte_pct)
                if sim.money < acompte + money_buffer:
                    continue
                for term in reversed(LOAN_TERMS):
                    _, days, rate = term
                    daily = max(1, round(int((prix - acompte) * (1 + rate)) / days))
                    if daily <= salary * 0.45:
                        return "acheter_maison"

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

_AUTO_PET_NAMES = _PRENOMS_ANIMAUX

def ai_auto_postuler(sim):
    """Choisit automatiquement un job disponible.
    Avec diplôme : meilleur salaire. Sans diplôme : choix aléatoire (variété)."""
    available = jobs_available(sim.education)
    if not available:
        return
    if sim.education.has_diploma():
        best = max(available, key=lambda x: x[1])
    else:
        # Sans diplôme : choix aléatoire parmi tous les postes accessibles
        best = random.choice(available)
    if sim.job == best[0]:
        return
    sim.job = best[0]
    # job_days n'est PAS remis à zéro : les cotisations retraite s'accumulent
    # sur toute la carrière, pas seulement sur le dernier poste.
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

def ai_auto_acheter_maison(sim):
    """Choisit automatiquement la propriété et le crédit optimaux pour l'IA."""
    if sim.housing:
        return
    salary = next((sal for lbl, sal, *_ in JOBS if lbl == sim.job), 0)
    if getattr(sim, 'retired', False):
        salary = sim.pension
    if salary == 0:
        return
    # Réserve de sécurité : 3 médecins + 10 jours de besoins quotidiens (~80$/j)
    money_buffer = 240 + 10 * (15 * len(sim.children) if sim.children else 0)
    # Cherche la meilleure propriété dont le paiement quotidien ≤ 40% du revenu
    chosen_prop = None
    chosen_term = None
    for prop in reversed(PROPERTIES):  # du plus cher au moins cher
        pid, nom, emoji, prix, acompte_pct, standing, effets = prop
        acompte = int(prix * acompte_pct)
        if sim.money < acompte + money_buffer:
            continue
        # Cherche le terme le plus long (paiement le plus faible)
        for term in reversed(LOAN_TERMS):
            lbl, days, rate = term
            loan_total = int((prix - acompte) * (1 + rate))
            daily = max(1, round(loan_total / days))
            if daily <= salary * 0.45:
                chosen_prop = prop
                chosen_term = term
                break
        if chosen_prop:
            break
    if not chosen_prop or not chosen_term:
        return  # pas encore les moyens
    pid, nom, emoji, prix, acompte_pct, standing, effets = chosen_prop
    acompte = int(prix * acompte_pct)
    _, term_days, interest_rate = chosen_term
    loan_total = int((prix - acompte) * (1 + interest_rate))
    daily_payment = max(1, round(loan_total / term_days))
    sim.money -= acompte
    sim.housing = {
        "property_id": pid,
        "purchase_price": prix,
        "loan_total": loan_total,
        "loan_remaining": loan_total,
        "daily_payment": daily_payment,
        "days_missed": 0,
    }
    slow_print(f"  {C.GREEN}[IA] 🏠 Achat : {emoji} {nom} — Acompte ${acompte:,} — "
               f"Crédit ${daily_payment}/j × {term_days}j{C.RESET}", 0.02)
    sim.modify(fun=+15, social=+10)
    sim.tick(2)


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
                _death_cause = next(
                    (DISEASES[d][0] for d in sim.health.diseases
                     if DISEASES.get(d,('','','',0,0,'inf'))[5] in ("fat","neuro")),
                    None)
                if _death_cause:
                    slow_print(f"\n {C.RED}💀 {sim.name} est décédé(e) des suites de {_death_cause}...{C.RESET}", 0.02)
                else:
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
            if action_key == "acheter_maison":
                ai_auto_acheter_maison(sim)
                sim.hour += ACTION_DURATIONS.get("acheter_maison", 0)
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
            _fatal = next(
                (DISEASES[d][0] for d in sim.health.diseases
                 if DISEASES.get(d,('','','',0,0,'inf'))[5] in ("fat","neuro")),
                None)
            if _fatal:
                slow_print(f"\n {C.RED}💀 {sim.name} est décédé(e) des suites de {_fatal}...{C.RESET}")
            else:
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
    sim.health.disease_stage = hd.get("disease_stage", {})

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
    sim.retired           = d.get("retired", False)
    sim.pension           = d.get("pension", 0)
    sim.housing           = d.get("housing", None)
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
