"""Wordle FR : devinez le mot de 5 lettres en 6 essais."""
import random
from .utils import header, pause, prompt, success, error, info, color, clear
try:
    from colorama import Fore, Style, Back
except ImportError:
    class _D:
        def __getattr__(self, _): return ""
    Fore = Style = Back = _D()

# Liste de mots français courants à 5 lettres
WORDS = [
    "ARBRE", "BALLE", "CARTE", "CHIEN", "CLAIR", "DROIT", "ECOLE", "ENFAN",
    "ETOIL", "FILLE", "FLEUR", "FORCE", "GARCO", "GRAND", "HERBE", "HIVER",
    "HOMME", "IMAGE", "JEUNE", "JOUER", "JUMEA", "LARGE", "LIVRE", "LUMIÈ",
    "MACHO", "MAGIE", "MAMAN", "MONDE", "MONTR", "MOTEU", "MUSIC", "NAGER",
    "NOIRE", "NUAGE", "OCEAN", "OISEA", "ORANG", "ORDRE", "OUVRI", "PAINS",
    "PAPIE", "PARIS", "PÈCHE", "PIANO", "PIEDR", "PLAGE", "PLUME", "POISS",
    "POMME", "PORTE", "POULE", "PREMI", "PRINC", "PROBL", "QUELL", "QUEUE",
    "RADIO", "REGAL", "REPAS", "RIVIE", "ROBER", "ROUGE", "ROUTE", "ROYAL",
    "SABLE", "SAINT", "SALON", "SAUCE", "SEIZE", "SERVI", "SINGE", "SOLEI",
    "SOUPE", "SPORT", "STERN", "SUCRE", "TABLE", "TERRE", "TIGER", "TIMON",
    "TITRE", "TOILE", "TRACE", "TRAIN", "TRÈFL", "TROIS", "TROMB", "TROUS",
    "USINE", "VAGUE", "VALSE", "VEILL", "VERRE", "VESTE", "VIEIL", "VILLE",
    "VITRE", "VOILE", "VOLCA", "MONDE", "BLANC", "BRUIT", "CALME", "DANSE",
    "FAGOT", "GÂTER", "GÉANT", "GRÈVE", "GUÈRE", "HAVRE", "HERBE", "HUILE",
    "IDÉAL", "JUGER", "LÂCHE", "LAPIN", "LIMON", "LINGE", "LOGIS", "LOURD",
    "LOYAL", "LUTTE", "LYONS", "MÂCHE", "MARIN", "MASSE", "MÉTAL", "MÈCHE",
    "MIEUX", "MITRE", "MIXTE", "MOITE", "MORUE", "MOYEN", "MURER", "MURET",
    "MUSÉE", "NAPPE", "NATTE", "NAVAL", "NŒUDS", "NOMBR", "NOTER", "NOVEL",
    "NOYAU", "OBÈSE", "OFFRE", "OLIVE", "OPÉRA", "ORAGE", "OVALE", "PAGES",
    "PAIRE", "PALME", "PANEL", "PATTE", "PAUSE", "PAVER", "PEINE", "PERCE",
    "PHASE", "PIÈCE", "PILOT", "PINOT", "PISTE", "PIXEL", "PLACE", "PLAIN",
    "PLAIT", "PLANS", "PLATS", "POIDS", "POINT", "POMPE", "PONCE", "PONTE",
    "POSES", "POSTE", "POUDR", "PREUX", "PRISE", "PROSE", "PROVE", "PUCES",
    "PULSE", "PURÉE", "RAISIN", "RAMPE", "RANGE", "RASER", "RAVIR", "RAYON",
    "REINE", "RÈGNE", "RÊVER", "RIDER", "RISEN", "ROBOT", "ROCHE", "ROMAN",
    "RONCE", "RONGE", "ROTOR", "ROTIR", "RUBAN", "RUGBY", "RUINE", "RURAL",
    "RUSER", "SALON", "SALUT", "SANTÉ", "SAUTÉ", "SAVON", "SCÈNE", "SCOUT",
    "SIÈGE", "SIGNE", "SIROP", "SŒURS", "SOLEN", "SOMME", "SONDE", "SORTE",
    "SOUDE", "SOURD", "SOUTE", "STADE", "STEAK", "STOMP", "STORE", "STYLE",
    "SUEUR", "SUITE", "SUJET", "SUPER", "SURGE", "SURGI", "TÂCHE", "TAPIS",
    "TARTE", "TAUPE", "TAXER", "TEINT", "TENTE", "TERME", "TEXTE", "THÈME",
    "TIGES", "TIMID", "TOAST", "TONTE", "TOQUE", "TORDU", "TOTAL", "TOTEM",
    "TOUPI", "TRAMP", "TRAPU", "TRIER", "TRIME", "TRÔNE", "TROPE", "TRUIE",
    "TUILE", "TULIP", "TURBO", "ULTRA", "UNDER", "UNITÉ", "USAGE", "USURP",
    "UTILE", "VALVE", "VAPEU", "VASAL", "VEINE", "VENTE", "VENUE", "VERTU",
    "VÉTÉR", "VIDER", "VIGIL", "VIGOR", "VIOLE", "VIRER", "VIRUS", "VISER",
    "VISOR", "VITAL", "VIVID", "VOCAL", "VŒUUX", "VOLET", "VOMIR", "VOTER",
    "VOÛTE", "VULVE", "YACHT", "ZONES",
    # mots courants nettoyés (5 lettres exactes, sans accents)
    "AIMER", "AUTRE", "AVOIR", "BELLE", "BONNE", "CADRE", "CAMEL", "CANAL",
    "CHOSE", "COMTE", "CORPS", "COUDE", "COUPE", "COURS", "COURT", "CRIME",
    "CRUEL", "DEBUT", "DEFER", "DELTA", "DENTS", "DEPIT", "DEPOT", "DESIR",
    "DETTE", "DIVIN", "DONNÉ", "DOUCE", "DROIT", "DUVET", "ECLAT", "EFFET",
    "EPAIS", "EPAVE", "EPOQU", "EQUIP", "ERREUR","ETAGE", "ETANG", "EVEIL",
    "EXACT", "FACON", "FAITE", "FANNY", "FARCE", "FATAL", "FAUTE", "FAVEU",
    "FIEVRE","FINAL", "FIORD", "FOLIE", "FORET", "FOULE", "FRANC", "FREIN",
    "FRONT", "FUTUR", "GAZON", "GENRE", "GILET", "GLACE", "GLISS", "GLOBE",
    "GLOIR", "GOLFE", "GORGE", "GRACE", "GRAIN", "GRAPP", "GRISE", "GROGI",
    "GUEUX", "GUIDE", "GUISE", "HALTE", "HONTE", "HOTEL", "HUMUS", "HURLE",
]

# Filter to exactly 5-letter words (ASCII only for reliability)
def _clean_words():
    cleaned = []
    for w in WORDS:
        w = w.upper().strip()
        # Keep only ASCII alpha words of exactly 5 chars
        if len(w) == 5 and w.isalpha() and w.isascii():
            cleaned.append(w)
    return list(set(cleaned))

CLEAN_WORDS = _clean_words()
if len(CLEAN_WORDS) < 20:
    # Fallback: minimal hardcoded list
    CLEAN_WORDS = [
        "ARBRE", "BALLE", "CARTE", "CHIEN", "CLAIR", "DROIT", "LARGE",
        "MONDE", "POMME", "PORTE", "ROUGE", "SABLE", "TABLE", "TRAIN",
        "VILLE", "BLANC", "BRUIT", "CALME", "DANSE", "FILLE", "FLEUR",
        "FORET", "GRACE", "HOMME", "IMAGE", "JEUNE", "JOUER", "LIVRE",
        "MAMAN", "NUAGE", "OCEAN", "PIANO", "PLACE", "POINT", "REPAS",
        "REINE", "ROBOT", "ROCHE", "ROMAN", "SALON", "SAUCE", "SPORT",
        "SUCRE", "TERRE", "TITRE", "TOILE", "VAGUE", "VALSE", "VERRE",
        "AIMER", "AUTRE", "AVOIR", "BELLE", "BONNE", "CADRE", "CANAL",
        "CHOSE", "CORPS", "COUPE", "COURS", "CRIME", "DEBUT", "DELTA",
        "DEPOT", "DETTE", "DIVIN", "FAUTE", "FINAL", "FOLIE", "FRANC",
        "FREIN", "FRONT", "FUTUR", "GAZON", "GENRE", "GILET", "GLACE",
        "GLOBE", "GOLFE", "GORGE", "GRAIN", "GUIDE", "HALTE", "HONTE",
        "HOTEL", "HURLE",
    ]


def _evaluate(secret, guess):
    """Return list of ('green'|'yellow'|'grey', letter) per position."""
    result = []
    from collections import Counter
    # Count remaining letters after removing greens
    remaining = Counter(s for s, g in zip(secret, guess) if s != g)
    # First pass: greens
    greens = [s == g for s, g in zip(secret, guess)]
    # Second pass: yellows
    yellows = [False] * 5
    for i, (s, g) in enumerate(zip(secret, guess)):
        if not greens[i] and remaining[g] > 0:
            yellows[i] = True
            remaining[g] -= 1

    for i in range(5):
        letter = guess[i]
        if greens[i]:
            result.append(("green", letter))
        elif yellows[i]:
            result.append(("yellow", letter))
        else:
            result.append(("grey", letter))
    return result


def _render_result(evaluation):
    parts = []
    for status, letter in evaluation:
        if status == "green":
            parts.append(color(f" {letter} ", Fore.BLACK if HAS_BACK else Fore.GREEN,
                               Back.GREEN if HAS_BACK else "", bold=True))
        elif status == "yellow":
            parts.append(color(f" {letter} ", Fore.BLACK if HAS_BACK else Fore.YELLOW,
                               Back.YELLOW if HAS_BACK else "", bold=True))
        else:
            parts.append(color(f" {letter} ", Fore.WHITE))
    return "  ".join(parts)

try:
    from colorama import Back
    HAS_BACK = True
except ImportError:
    HAS_BACK = False


def _keyboard_state(history):
    """Return dict letter -> best status."""
    state = {}
    for guess_eval in history:
        for status, letter in guess_eval:
            current = state.get(letter, "unused")
            if current == "green":
                continue
            if status == "green":
                state[letter] = "green"
            elif status == "yellow" and current != "green":
                state[letter] = "yellow"
            elif status == "grey" and current == "unused":
                state[letter] = "grey"
    return state


def _render_keyboard(state):
    rows = ["AZERTYUIOP", "QSDFGHJKLM", "WXCVBN"]
    lines = []
    for row in rows:
        parts = []
        for l in row:
            s = state.get(l, "unused")
            if s == "green":
                parts.append(color(f"[{l}]", Fore.GREEN, bold=True))
            elif s == "yellow":
                parts.append(color(f"[{l}]", Fore.YELLOW, bold=True))
            elif s == "grey":
                parts.append(color(f"[{l}]", Fore.WHITE))
            else:
                parts.append(f"[{l}]")
        lines.append("  " + " ".join(parts))
    return "\n".join(lines)


MAX_TRIES = 6


def play(difficulty="normal"):
    word_list = CLEAN_WORDS[:]
    random.shuffle(word_list)
    secret = word_list[0]

    history_eval = []
    history_guesses = []

    header("WORDLE FR  🟩")
    info("Devinez le mot de 5 lettres en 6 essais.")
    info("🟩 = bonne lettre, bonne position")
    info("🟨 = bonne lettre, mauvaise position")
    info("⬜ = lettre absente du mot")
    pause()

    won = False
    for attempt in range(1, MAX_TRIES + 1):
        clear()
        header("WORDLE FR  🟩")
        info(f"Essai {attempt}/{MAX_TRIES}")
        print()

        for ev in history_eval:
            print("  " + _render_result(ev))
        # Blank rows
        for _ in range(MAX_TRIES - len(history_eval)):
            print("  " + "  ".join(color(" _ ", Fore.WHITE) for _ in range(5)))
        print()
        kb_state = _keyboard_state(history_eval)
        print(_render_keyboard(kb_state))
        print()

        while True:
            raw = prompt("  Entrez un mot de 5 lettres : ").strip().upper()
            if len(raw) != 5 or not raw.isalpha():
                error("Entrez exactement 5 lettres alphabétiques.")
                continue
            break

        ev = _evaluate(secret, raw)
        history_eval.append(ev)
        history_guesses.append(raw)

        if raw == secret:
            won = True
            break

    score = 0
    clear()
    header("WORDLE FR  🟩")
    for ev in history_eval:
        print("  " + _render_result(ev))
    print()
    if won:
        turns = len(history_guesses)
        score = (MAX_TRIES - turns + 1) * 100
        success(f"Bravo ! Mot trouvé en {turns} essai(s) : {color(secret, Fore.GREEN, bold=True)}")
    else:
        error(f"Perdu ! Le mot était : {color(secret, Fore.YELLOW, bold=True)}")
    print(color(f"\n  Score : {score}", Fore.YELLOW, bold=True))
    pause()
    return score
