"""
MODULE 7 — Le rat dans le labyrinthe
=======================================

Comme le serpent (module 5), ce rat n'a JAMAIS reçu de bonnes réponses
à l'avance : il apprend uniquement par ESSAI-ERREUR, en explorant le
labyrinthe et en retenant ce qui l'a rapproché du fromage. C'est encore
de l'apprentissage par renforcement.

Différence avec le serpent : ici, le labyrinthe ne change JAMAIS — les
murs sont toujours aux mêmes endroits, le fromage aussi. Sa "situation"
peut donc être tout simplement SA POSITION sur la grille : pas besoin
de deviner des dangers autour de lui comme devait le faire le serpent.
Autre différence : se cogner dans un mur ne tue pas le rat, ça lui fait
juste perdre un peu de temps.

Vocabulaire (comme le module 5) :
    - "situation"  : ici, la position du rat (case x, y)
    - "mémoire des choix" : une note pour chacun des 4 mouvements
                      possibles (haut/bas/gauche/droite), pour chaque
                      case déjà visitée
    - "curiosité"  : la chance qu'il essaie un mouvement au hasard
    - "patience"   : à quel point il valorise les récompenses lointaines
    - "partie"     : une tentative, du départ jusqu'au fromage (ou
                      jusqu'à ce qu'il abandonne, faute de temps)

Usage :
    python -m modules.module7_labyrinthe
    python -m modules.module7_labyrinthe --details --parties 5
"""

import argparse
import time
from collections import defaultdict

import numpy as np

try:
    from .utils import pas_a_pas, sauvegarder_checkpoint
except ImportError:
    # Permet aussi de lancer ce fichier tout seul (ex: bouton "Run" de
    # Pydroid3 sur Android), qui l'execute hors du package "modules".
    from utils import pas_a_pas, sauvegarder_checkpoint

LABYRINTHE = [
    "S.......",
    ".####.#.",
    ".#....#.",
    ".#.##.#.",
    ".#.#..#.",
    ".#.####.",
    ".......C",
]
LARGEUR = len(LABYRINTHE[0])
HAUTEUR = len(LABYRINTHE)
MOUVEMENTS_MAX_PAR_PARTIE = 100

# 0 = haut, 1 = droite, 2 = bas, 3 = gauche — des directions ABSOLUES,
# contrairement au serpent qui tournait par rapport a sa propre direction.
VECTEURS_DIRECTION = [(0, -1), (1, 0), (0, 1), (-1, 0)]
NOMS_ACTIONS = ["haut", "droite", "bas", "gauche"]


def position_depart():
    for y in range(HAUTEUR):
        for x in range(LARGEUR):
            if LABYRINTHE[y][x] == "S":
                return (x, y)
    raise ValueError("Le labyrinthe n'a pas de depart (S).")


POSITION_DEPART = position_depart()


def nouvelle_partie():
    return {"position": POSITION_DEPART, "mouvements": 0, "recompense_totale": 0.0}


def case(position):
    x, y = position
    return LABYRINTHE[y][x]


def jouer_un_mouvement(partie, indice_action):
    dx, dy = VECTEURS_DIRECTION[indice_action]
    x, y = partie["position"]
    nouvelle_position = (x + dx, y + dy)
    nx, ny = nouvelle_position

    hors_grille = not (0 <= nx < LARGEUR and 0 <= ny < HAUTEUR)
    heurte_un_mur = hors_grille or LABYRINTHE[ny][nx] == "#"

    partie["mouvements"] += 1

    if heurte_un_mur:
        recompense, message = -1.0, "il se cogne dans un mur, il reste sur place."
    else:
        partie["position"] = nouvelle_position
        if case(nouvelle_position) == "C":
            recompense, message = 50.0, "il trouve le fromage !"
        else:
            recompense, message = -0.05, "il avance."

    partie["recompense_totale"] += recompense
    trouve = not heurte_un_mur and case(partie["position"]) == "C"
    timeout = partie["mouvements"] >= MOUVEMENTS_MAX_PAR_PARTIE
    termine = trouve or timeout

    if timeout and not trouve:
        message = "il abandonne, trop de temps passe sans trouver le fromage."

    return partie, recompense, termine, message


def choisir_action(situation, table_des_choix, curiosite, rng):
    if rng.random() < curiosite:
        return int(rng.integers(0, 4)), True
    valeurs = table_des_choix[situation]
    return int(np.argmax(valeurs)), False


def expliquer_le_probleme():
    print("CE QUE LE RAT DOIT APPRENDRE")
    print("-" * 40)
    print(f"Trouver le fromage (C) dans ce labyrinthe de {LARGEUR}x{HAUTEUR}, en partant de S :\n")
    for ligne in LABYRINTHE:
        print("   " + ligne)
    print("\nPERSONNE ne lui montre le chemin. Il commence en ne sachant rien,")
    print("et apprend uniquement des consequences de ses choix :")
    print("   +50 points quand il trouve le fromage")
    print("   -1 point s'il se cogne dans un mur (il reste sur place, ce n'est pas mortel)")
    print("   -0.05 point a chaque mouvement (pour l'inciter a ne pas trainer)\n")
    print("Sa situation est juste sa position sur la grille. A chaque case deja")
    print("visitee, il garde une note pour chacun des 4 mouvements possibles :")
    print("   haut / droite / bas / gauche\n")


def construire_carte_valeurs(table_des_choix):
    """Pour chaque case du labyrinthe (sauf les murs), la meilleure valeur
    connue et la direction qu'il pense etre la meilleure pour l'instant.
    Utilise par l'interface graphique pour montrer ce que le rat a compris
    du labyrinthe AU FIL de l'entrainement, pas seulement a la toute fin."""
    carte = []
    for y in range(HAUTEUR):
        ligne = []
        for x in range(LARGEUR):
            if LABYRINTHE[y][x] == "#":
                ligne.append("mur")
                continue
            valeurs = table_des_choix.get((x, y))
            if valeurs is None:
                ligne.append(None)  # case jamais visitee pour l'instant
            else:
                ligne.append({"valeur": float(np.max(valeurs)), "action": int(np.argmax(valeurs))})
        carte.append(ligne)
    return carte


def raconter_la_pensee(numero_partie, partie, position_avant, indice_action, exploration, message):
    origine = "explore un mouvement au hasard" if exploration else "joue le mouvement qu'il pense etre le meilleur"
    print(f"  Partie {numero_partie}, mouvement {partie['mouvements']}: en {position_avant} "
          f"-> il {origine} : {NOMS_ACTIONS[indice_action]}. -> {message}")


def entrainer(nb_parties=300, vitesse_apprentissage=0.1, patience=0.9,
              curiosite_initiale=1.0, curiosite_minimale=0.05,
              details=False, afficher_toutes_les=50, pas_a_pas_actif=False, sur_partie=None,
              jouer_demo_finale=True):
    expliquer_le_probleme()

    rng = np.random.default_rng(42)
    table_des_choix = defaultdict(lambda: np.zeros(4))
    historique_recompenses = []
    historique_reussites = []
    curiosite = curiosite_initiale
    facteur_decroissance_curiosite = 0.98

    print(f"Debut de l'entrainement : {nb_parties} parties, vitesse d'apprentissage "
          f"{vitesse_apprentissage}, patience {patience}\n")

    for numero_partie in range(1, nb_parties + 1):
        partie = nouvelle_partie()
        termine = False
        trouve = False

        while not termine:
            situation = partie["position"]
            indice_action, exploration = choisir_action(situation, table_des_choix, curiosite, rng)

            position_avant = partie["position"]
            partie, recompense, termine, message = jouer_un_mouvement(partie, indice_action)
            nouvelle_situation = partie["position"]
            trouve = message == "il trouve le fromage !"

            meilleure_valeur_future = 0.0 if termine else float(np.max(table_des_choix[nouvelle_situation]))
            valeur_actuelle = table_des_choix[situation][indice_action]
            correction = recompense + patience * meilleure_valeur_future - valeur_actuelle
            table_des_choix[situation][indice_action] = valeur_actuelle + vitesse_apprentissage * correction

            if details:
                raconter_la_pensee(numero_partie, partie, position_avant, indice_action, exploration, message)
                pas_a_pas(pas_a_pas_actif)

        historique_recompenses.append(partie["recompense_totale"])
        historique_reussites.append(trouve)
        curiosite = max(curiosite_minimale, curiosite * facteur_decroissance_curiosite)
        moyenne_recente = float(np.mean(historique_recompenses[-afficher_toutes_les:]))
        taux_reussite_recent = float(np.mean(historique_reussites[-afficher_toutes_les:])) * 100

        if not details and (numero_partie == 1 or numero_partie % afficher_toutes_les == 0):
            print(f"Partie {numero_partie:>5} | recompense : {partie['recompense_totale']:>6.2f} | "
                  f"moyenne des {min(afficher_toutes_les, numero_partie)} dernieres : {moyenne_recente:.2f} | "
                  f"reussite recente : {taux_reussite_recent:.0f}% | curiosite : {curiosite:.2f}")
            pas_a_pas(pas_a_pas_actif)

        if sur_partie is not None:
            sur_partie({
                "partie": numero_partie,
                "nb_parties": nb_parties,
                "recompense": partie["recompense_totale"],
                "moyenne_recente": moyenne_recente,
                "taux_reussite_recent": taux_reussite_recent,
                "curiosite": curiosite,
                "trouve": trouve,
                "carte_valeurs": construire_carte_valeurs(table_des_choix),
            })

    meilleure_recompense = max(historique_recompenses)
    taux_reussite_final = float(np.mean(historique_reussites[-min(50, len(historique_reussites)):])) * 100
    print(f"\nEntrainement termine ! Meilleure recompense obtenue : {meilleure_recompense:.2f}. "
          f"Taux de reussite sur les dernieres parties : {taux_reussite_final:.0f}%.\n")

    if jouer_demo_finale:
        print("Regardons une partie jouee par le rat, sans hasard, avec ce qu'il a appris :\n")
        jouer_une_partie_demo(table_des_choix)

    sauvegarder_checkpoint("module7_labyrinthe.json", {
        "table_des_choix": {",".join(map(str, situation)): valeurs.tolist()
                             for situation, valeurs in table_des_choix.items()},
        "historique_recompenses": historique_recompenses,
        "historique_reussites": historique_reussites,
    })

    return table_des_choix, historique_recompenses


def dessiner_grille(partie):
    lignes = []
    for y in range(HAUTEUR):
        ligne = ""
        for x in range(LARGEUR):
            if (x, y) == partie["position"]:
                ligne += "R"
            else:
                ligne += LABYRINTHE[y][x]
        lignes.append(ligne)
    return "\n".join(lignes)


def construire_grille_structuree(partie):
    """Meme grille que dessiner_grille, mais sous forme de tableau de
    cases nommees, pour que l'interface graphique puisse la dessiner en
    couleur."""
    NOMS_CASES = {"#": "mur", "C": "fromage", "S": "vide", ".": "vide"}
    grille = []
    for y in range(HAUTEUR):
        ligne = []
        for x in range(LARGEUR):
            if (x, y) == partie["position"]:
                ligne.append("rat")
            else:
                ligne.append(NOMS_CASES.get(LABYRINTHE[y][x], "vide"))
        grille.append(ligne)
    return grille


def jouer_une_partie_demo(table_des_choix, vitesse_affichage=0.3, sur_mouvement=None):
    rng = np.random.default_rng()
    partie = nouvelle_partie()
    termine = False

    print(dessiner_grille(partie))
    print(f"Recompense cumulee : {partie['recompense_totale']:.2f}\n")

    if sur_mouvement is not None:
        sur_mouvement({"grille": construire_grille_structuree(partie), "recompense": partie["recompense_totale"],
                       "message": "debut de la partie.", "termine": False})

    while not termine:
        situation = partie["position"]
        indice_action, _ = choisir_action(situation, table_des_choix, curiosite=0.0, rng=rng)
        partie, _, termine, message = jouer_un_mouvement(partie, indice_action)

        try:
            time.sleep(vitesse_affichage)
        except KeyboardInterrupt:
            print("\n(demonstration interrompue)")
            break

        print(dessiner_grille(partie))
        print(f"Recompense cumulee : {partie['recompense_totale']:.2f} | {message}\n")

        if sur_mouvement is not None:
            sur_mouvement({"grille": construire_grille_structuree(partie), "recompense": partie["recompense_totale"],
                           "message": message, "termine": termine})

    print(f"Partie de demonstration terminee. Recompense finale : {partie['recompense_totale']:.2f}.")


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 7 : un rat qui apprend a trouver le fromage par essai-erreur.")
    analyseur.add_argument("--details", action="store_true", help="Raconte la pensee du rat a chaque mouvement.")
    analyseur.add_argument("--parties", type=int, default=300, help="Nombre de parties jouees (par defaut 300).")
    analyseur.add_argument("--vitesse", type=float, default=0.1, help="Vitesse d'apprentissage (par defaut 0.1).")
    analyseur.add_argument("--patience", type=float, default=0.9,
                            help="Importance donnee aux recompenses futures, entre 0 et 1 (par defaut 0.9).")
    analyseur.add_argument("--curiosite", type=float, default=1.0, dest="curiosite_initiale",
                            help="Chance de depart de tester un mouvement au hasard (par defaut 1.0).")
    analyseur.add_argument("--afficher-toutes-les", type=int, default=50, dest="afficher_toutes_les")
    analyseur.add_argument("--pas-a-pas", action="store_true", dest="pas_a_pas_actif")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    entrainer(nb_parties=args.parties, vitesse_apprentissage=args.vitesse, patience=args.patience,
              curiosite_initiale=args.curiosite_initiale, details=args.details,
              afficher_toutes_les=args.afficher_toutes_les, pas_a_pas_actif=args.pas_a_pas_actif)
