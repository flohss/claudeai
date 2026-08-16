"""
MODULE 5 — Le serpent qui apprend tout seul
==============================================

Contrairement aux modules 1 à 4, cette IA n'a JAMAIS reçu la bonne
réponse à l'avance. Personne ne lui a montré d'exemples de "bonnes
parties". Elle apprend uniquement par ESSAI-ERREUR : elle joue, elle
gagne des points quand elle mange la nourriture, elle en perd quand elle
meurt (mur ou elle-même), et petit à petit elle retient quelles décisions
ont plutôt bien tourné dans quelles situations.

C'est ce qu'on appelle l'apprentissage par renforcement.

Vocabulaire de ce module :
    - "situation"  : ce que le serpent voit autour de lui en ce moment
                      (danger devant/gauche/droite, nourriture devant/
                      gauche/droite)
    - "mémoire des choix" : pour chaque situation déjà rencontrée, une
                      note pour chacun des 3 mouvements possibles
    - "curiosité"  : la chance qu'elle essaie un mouvement au hasard
                      plutôt que celui qu'elle pense être le meilleur
                      (elle est très curieuse au début, de moins en
                      moins avec l'expérience)
    - "patience"   : à quel point elle valorise les récompenses
                      lointaines plutôt que seulement le prochain coup
    - "partie"     : l'équivalent d'un essai pour un jeu : une partie
                      commence quand le serpent nait et se termine
                      quand il meurt (ou tourne en rond trop longtemps)

Usage :
    python -m modules.module5_serpent
    python -m modules.module5_serpent --details --parties 5
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

TAILLE_GRILLE = 10
MOUVEMENTS_MAX_PAR_PARTIE = 300

# 0 = haut, 1 = droite, 2 = bas, 3 = gauche
VECTEURS_DIRECTION = [(0, -1), (1, 0), (0, 1), (-1, 0)]
NOMS_ACTIONS = ["tout droit", "tourner a gauche", "tourner a droite"]


def nouvelle_partie(rng):
    tete = (TAILLE_GRILLE // 2, TAILLE_GRILLE // 2)
    return {
        "corps": [tete],
        "direction": 1,
        "nourriture": placer_nourriture(rng, [tete]),
        "score": 0,
        "mouvements": 0,
    }


def placer_nourriture(rng, corps):
    while True:
        position = (int(rng.integers(0, TAILLE_GRILLE)), int(rng.integers(0, TAILLE_GRILLE)))
        if position not in corps:
            return position


def direction_apres_action(direction, indice_action):
    if indice_action == 1:   # tourner a gauche
        return (direction - 1) % 4
    if indice_action == 2:   # tourner a droite
        return (direction + 1) % 4
    return direction         # tout droit


def decrire_situation(partie):
    tete_x, tete_y = partie["corps"][0]
    direction = partie["direction"]

    def case_dangereuse(dir_testee):
        dx, dy = VECTEURS_DIRECTION[dir_testee]
        case = (tete_x + dx, tete_y + dy)
        hors_grille = not (0 <= case[0] < TAILLE_GRILLE and 0 <= case[1] < TAILLE_GRILLE)
        return hors_grille or case in partie["corps"][:-1]

    danger_devant = case_dangereuse(direction)
    danger_gauche = case_dangereuse((direction - 1) % 4)
    danger_droite = case_dangereuse((direction + 1) % 4)

    delta_x = partie["nourriture"][0] - tete_x
    delta_y = partie["nourriture"][1] - tete_y

    def produit(vecteur):
        return delta_x * vecteur[0] + delta_y * vecteur[1]

    nourriture_devant = produit(VECTEURS_DIRECTION[direction]) > 0
    nourriture_gauche = produit(VECTEURS_DIRECTION[(direction - 1) % 4]) > 0
    nourriture_droite = produit(VECTEURS_DIRECTION[(direction + 1) % 4]) > 0

    return (int(danger_devant), int(danger_gauche), int(danger_droite),
            int(nourriture_devant), int(nourriture_gauche), int(nourriture_droite))


def jouer_un_mouvement(partie, indice_action, rng):
    nouvelle_direction = direction_apres_action(partie["direction"], indice_action)
    dx, dy = VECTEURS_DIRECTION[nouvelle_direction]
    tete_x, tete_y = partie["corps"][0]
    nouvelle_tete = (tete_x + dx, tete_y + dy)

    hors_grille = not (0 <= nouvelle_tete[0] < TAILLE_GRILLE and 0 <= nouvelle_tete[1] < TAILLE_GRILLE)
    heurte_son_corps = nouvelle_tete in partie["corps"][:-1]

    if hors_grille or heurte_son_corps:
        return partie, -10.0, True, "elle heurte un mur ou elle-meme, la partie s'arrete."

    partie["direction"] = nouvelle_direction
    partie["corps"].insert(0, nouvelle_tete)
    partie["mouvements"] += 1

    if nouvelle_tete == partie["nourriture"]:
        partie["score"] += 1
        partie["nourriture"] = placer_nourriture(rng, partie["corps"])
        recompense, message = 10.0, "elle mange la nourriture !"
    else:
        partie["corps"].pop()
        recompense, message = -0.1, "elle avance normalement."

    if partie["mouvements"] >= MOUVEMENTS_MAX_PAR_PARTIE:
        return partie, recompense, True, "elle tourne en rond depuis trop longtemps, on arrete la partie."

    return partie, recompense, False, message


def choisir_action(situation, table_des_choix, curiosite, rng):
    if rng.random() < curiosite:
        return int(rng.integers(0, 3)), True
    valeurs = table_des_choix[situation]
    return int(np.argmax(valeurs)), False


def expliquer_le_probleme():
    print("CE QUE L'IA DOIT APPRENDRE")
    print("-" * 40)
    print("Faire grandir un serpent en mangeant de la nourriture sur une grille")
    print(f"de {TAILLE_GRILLE}x{TAILLE_GRILLE}, sans jamais heurter un mur ou son propre corps.\n")
    print("PERSONNE ne lui montre comment jouer. Elle commence en ne sachant")
    print("rien faire, et apprend uniquement des consequences de ses choix :")
    print("   +10 points quand elle mange la nourriture")
    print("   -10 points quand elle meurt (mur ou elle-meme)")
    print("   -0.1 point a chaque mouvement (pour l'inciter a ne pas tourner en rond)\n")
    print("A chaque situation rencontree, elle a 3 mouvements possibles :")
    print("   tout droit / tourner a gauche / tourner a droite")
    print("Elle garde en memoire une note pour chaque mouvement essaye dans")
    print("chaque situation, et apprend a preferer ceux qui menent a de bonnes")
    print("recompenses, y compris plus tard dans la partie (c'est le role de")
    print("la 'patience').\n")


def raconter_la_pensee(numero_partie, partie, situation, indice_action, exploration, message):
    danger_txt = []
    if situation[0]:
        danger_txt.append("danger devant")
    if situation[1]:
        danger_txt.append("danger a gauche")
    if situation[2]:
        danger_txt.append("danger a droite")
    danger_txt = ", ".join(danger_txt) if danger_txt else "aucun danger immediat"

    nourriture_txt = []
    if situation[3]:
        nourriture_txt.append("devant")
    if situation[4]:
        nourriture_txt.append("a gauche")
    if situation[5]:
        nourriture_txt.append("a droite")
    nourriture_txt = " et ".join(nourriture_txt) if nourriture_txt else "derriere elle"

    origine = "explore un mouvement au hasard" if exploration else "joue le mouvement qu'elle pense etre le meilleur"
    print(f"  Partie {numero_partie}, mouvement {partie['mouvements']}: {danger_txt}, "
          f"nourriture {nourriture_txt} -> elle {origine} : {NOMS_ACTIONS[indice_action]}. -> {message}")


def entrainer(nb_parties=400, vitesse_apprentissage=0.1, patience=0.9,
              curiosite_initiale=1.0, curiosite_minimale=0.05,
              details=False, afficher_toutes_les=50, pas_a_pas_actif=False, sur_partie=None,
              jouer_demo_finale=True):
    expliquer_le_probleme()

    rng = np.random.default_rng(42)
    table_des_choix = defaultdict(lambda: np.zeros(3))
    historique_scores = []
    curiosite = curiosite_initiale
    facteur_decroissance_curiosite = 0.98  # elle explore un peu moins a chaque partie jouee

    print(f"Debut de l'entrainement : {nb_parties} parties, vitesse d'apprentissage "
          f"{vitesse_apprentissage}, patience {patience}\n")

    for numero_partie in range(1, nb_parties + 1):
        partie = nouvelle_partie(rng)
        termine = False

        while not termine:
            situation = decrire_situation(partie)
            indice_action, exploration = choisir_action(situation, table_des_choix, curiosite, rng)

            partie, recompense, termine, message = jouer_un_mouvement(partie, indice_action, rng)
            nouvelle_situation = decrire_situation(partie)

            # Mise a jour de la note : on corrige vers la recompense recue,
            # plus ce que la meilleure suite semble valoir (ponderee par la patience).
            meilleure_valeur_future = 0.0 if termine else float(np.max(table_des_choix[nouvelle_situation]))
            valeur_actuelle = table_des_choix[situation][indice_action]
            correction = recompense + patience * meilleure_valeur_future - valeur_actuelle
            table_des_choix[situation][indice_action] = valeur_actuelle + vitesse_apprentissage * correction

            if details:
                raconter_la_pensee(numero_partie, partie, situation, indice_action, exploration, message)
                pas_a_pas(pas_a_pas_actif)

        historique_scores.append(partie["score"])
        curiosite = max(curiosite_minimale, curiosite * facteur_decroissance_curiosite)
        moyenne_recente = float(np.mean(historique_scores[-afficher_toutes_les:]))

        if not details and (numero_partie == 1 or numero_partie % afficher_toutes_les == 0):
            print(f"Partie {numero_partie:>5} | score : {partie['score']:>3} | "
                  f"moyenne des {min(afficher_toutes_les, numero_partie)} dernieres : {moyenne_recente:.1f} | "
                  f"curiosite : {curiosite:.2f}")
            pas_a_pas(pas_a_pas_actif)

        if sur_partie is not None:
            sur_partie({
                "partie": numero_partie,
                "nb_parties": nb_parties,
                "score": partie["score"],
                "moyenne_recente": moyenne_recente,
                "curiosite": curiosite,
            })

    meilleur_score = max(historique_scores)
    moyenne_finale = float(np.mean(historique_scores[-min(50, len(historique_scores)):]))
    print(f"\nEntrainement termine ! Meilleur score obtenu : {meilleur_score}. "
          f"Score moyen sur les dernieres parties : {moyenne_finale:.1f}.\n")

    if jouer_demo_finale:
        print("Regardons une partie jouee par l'IA, sans hasard, avec ce qu'elle a appris :\n")
        jouer_une_partie_demo(table_des_choix, rng)

    sauvegarder_checkpoint("module5_serpent.json", {
        "table_des_choix": {",".join(map(str, situation)): valeurs.tolist()
                             for situation, valeurs in table_des_choix.items()},
        "historique_scores": historique_scores,
    })

    return table_des_choix, historique_scores


def dessiner_grille(partie):
    lignes = []
    for y in range(TAILLE_GRILLE):
        ligne = ""
        for x in range(TAILLE_GRILLE):
            case = (x, y)
            if case == partie["corps"][0]:
                ligne += "O"
            elif case in partie["corps"]:
                ligne += "o"
            elif case == partie["nourriture"]:
                ligne += "*"
            else:
                ligne += "."
        lignes.append(ligne)
    return "\n".join(lignes)


def construire_grille_structuree(partie):
    """Meme grille que dessiner_grille, mais sous forme de tableau de
    cases nommees ('tete', 'corps', 'nourriture', 'vide') pour que
    l'interface graphique puisse la dessiner en couleur."""
    grille = []
    for y in range(TAILLE_GRILLE):
        ligne = []
        for x in range(TAILLE_GRILLE):
            case = (x, y)
            if case == partie["corps"][0]:
                ligne.append("tete")
            elif case in partie["corps"]:
                ligne.append("corps")
            elif case == partie["nourriture"]:
                ligne.append("nourriture")
            else:
                ligne.append("vide")
        grille.append(ligne)
    return grille


def jouer_une_partie_demo(table_des_choix, rng, vitesse_affichage=0.15, sur_mouvement=None):
    partie = nouvelle_partie(rng)
    termine = False

    print(dessiner_grille(partie))
    print(f"Score : {partie['score']}\n")

    if sur_mouvement is not None:
        sur_mouvement({"grille": construire_grille_structuree(partie), "score": partie["score"],
                       "message": "debut de la partie.", "termine": False})

    while not termine:
        situation = decrire_situation(partie)
        indice_action, _ = choisir_action(situation, table_des_choix, curiosite=0.0, rng=rng)
        partie, _, termine, message = jouer_un_mouvement(partie, indice_action, rng)

        try:
            time.sleep(vitesse_affichage)
        except KeyboardInterrupt:
            print("\n(demonstration interrompue)")
            break

        print(dessiner_grille(partie))
        print(f"Score : {partie['score']} | {message}\n")

        if sur_mouvement is not None:
            sur_mouvement({"grille": construire_grille_structuree(partie), "score": partie["score"],
                           "message": message, "termine": termine})

    print(f"Partie de demonstration terminee. Score final : {partie['score']}.")


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 5 : un serpent qui apprend a jouer par essai-erreur.")
    analyseur.add_argument("--details", action="store_true", help="Raconte la pensee de l'IA a chaque mouvement.")
    analyseur.add_argument("--parties", type=int, default=400, help="Nombre de parties jouees (par defaut 400).")
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
