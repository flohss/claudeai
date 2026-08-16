"""
MODULE 8 — Reconnaitre PLUSIEURS fruits
==========================================

C'est l'extension du module 3 : au lieu de choisir entre seulement DEUX
categories (Pomme ou Orange), cette IA doit choisir entre TROIS : Pomme,
Orange ou Banane, a partir du poids (g) et de la forme du fruit (une
note de 0 = bien rond, a 10 = tres allonge).

Nouveaute par rapport au module 3 : avec seulement 2 categories, un
seul pourcentage de confiance suffisait (pres de 0% = une categorie,
pres de 100% = l'autre). Avec 3 categories ou plus, il en faut un pour
CHAQUE fruit possible, et ils doivent ensemble totaliser 100% — comme
si les fruits se partageaient un gateau selon le score qu'ils ont
obtenu. Le fruit avec la plus grosse part est la reponse de l'IA.

Chaque fruit possible a maintenant SES PROPRES boutons (un pour le
poids, un pour la forme, plus un seuil de base), et les trois jeux de
boutons "se disputent" le meilleur score a chaque exemple.

Usage :
    python -m modules.module8_fruits_multiples
    python -m modules.module8_fruits_multiples --details
"""

import argparse

import numpy as np

try:
    from .utils import arrondi_sur, barre_erreur, pas_a_pas, sauvegarder_checkpoint
except ImportError:
    # Permet aussi de lancer ce fichier tout seul (ex: bouton "Run" de
    # Pydroid3 sur Android), qui l'execute hors du package "modules".
    from utils import arrondi_sur, barre_erreur, pas_a_pas, sauvegarder_checkpoint

NOMS_CATEGORIES = ["Pomme", "Orange", "Banane"]

# poids (g), forme (0 = rond, 10 = tres allonge)
FRUITS_ENTRAINEMENT = np.array([
    [145, 1], [133, 1], [150, 1], [128, 1], [140, 0], [136, 1], [122, 1], [131, 1],
    [206, 1], [198, 1], [211, 2], [197, 1], [200, 1], [215, 2], [206, 0], [194, 1],
    [128, 8], [126, 9], [121, 8], [127, 7], [110, 8], [130, 8], [118, 9], [112, 9],
], dtype=float)

VRAIES_CATEGORIES = np.array([0] * 8 + [1] * 8 + [2] * 8)

ECHELLE_POIDS = 250.0
ECHELLE_FORME = 10.0


def normaliser(fruits):
    return np.column_stack([
        fruits[:, 0] / ECHELLE_POIDS,
        fruits[:, 1] / ECHELLE_FORME,
    ])


def repartir_les_scores(scores):
    """Transforme des scores libres en pourcentages qui totalisent 100%,
    un peu comme un partage de gateau : plus un score est grand par
    rapport aux autres, plus sa part est grosse."""
    scores_decales = scores - scores.max(axis=1, keepdims=True)
    parts = np.exp(scores_decales)
    return parts / parts.sum(axis=1, keepdims=True)


def expliquer_le_probleme():
    print("CE QUE L'IA DOIT APPRENDRE")
    print("-" * 40)
    print(f"Reconnaitre un fruit parmi {len(NOMS_CATEGORIES)} categories : {', '.join(NOMS_CATEGORIES)}.")
    print("A partir de deux indices :")
    print("   - le poids du fruit (en grammes)")
    print("   - sa forme, notee de 0 (bien rond) a 10 (tres allonge)\n")
    print("Exemples d'entrainement :")
    for (poids, forme), categorie in list(zip(FRUITS_ENTRAINEMENT, VRAIES_CATEGORIES))[:4]:
        print(f"   {poids:.0f}g, forme {forme:.0f}/10 -> {NOMS_CATEGORIES[categorie]}")
    print("   ...\n")
    print(f"Chacun des {len(NOMS_CATEGORIES)} fruits possibles a ses propres boutons. L'IA calcule")
    print("un score pour chaque fruit, puis partage 100% entre eux selon ces")
    print("scores : le fruit avec la plus grosse part est sa reponse.\n")


def construire_pensee(fruits, vraies_categories, probabilites):
    lignes = []
    for (poids, forme), vraie_categorie, probas in zip(fruits, vraies_categories, probabilites):
        vrai_nom = NOMS_CATEGORIES[vraie_categorie]
        devine_index = int(np.argmax(probas))
        devine_nom = NOMS_CATEGORIES[devine_index]
        pourcentage_principal = arrondi_sur(probas[devine_index] * 100)
        autres = ", ".join(f"{NOMS_CATEGORIES[i]} {arrondi_sur(probas[i] * 100)}%"
                            for i in range(len(NOMS_CATEGORIES)) if i != devine_index)
        bonne_reponse = devine_nom == vrai_nom
        if bonne_reponse:
            commentaire = "Bonne reponse, elle va juste renforcer un peu sa confiance."
        else:
            commentaire = "Mauvaise reponse, elle va corriger ses boutons plus fort."
        lignes.append(f"Fruit {poids:.0f}g, forme {forme:.0f}/10 (vrai: {vrai_nom}) "
                       f"-> l'IA pense '{devine_nom}' a {pourcentage_principal}% ({autres}). -> {commentaire}")
    return lignes


def calculer_corrects(vraies_categories, probabilites):
    """Pour chaque fruit, l'IA a-t-elle actuellement la bonne reponse ?
    Utilise par l'interface graphique pour dessiner une petite grille
    qui se colore en vert au fil de l'entrainement."""
    return [bool(int(np.argmax(probas)) == vraie) for vraie, probas in zip(vraies_categories, probabilites)]


def tester(boutons, seuils_de_base):
    fruits_normalises = normaliser(FRUITS_ENTRAINEMENT)
    probabilites = repartir_les_scores(fruits_normalises @ boutons + seuils_de_base)

    nb_corrects = 0
    for (poids, forme), vraie_categorie, probas in zip(FRUITS_ENTRAINEMENT, VRAIES_CATEGORIES, probabilites):
        vrai_nom = NOMS_CATEGORIES[vraie_categorie]
        devine_nom = NOMS_CATEGORIES[int(np.argmax(probas))]
        correct = devine_nom == vrai_nom
        nb_corrects += int(correct)
        symbole = "OK" if correct else "X "
        print(f"  [{symbole}] {poids:.0f}g, forme {forme:.0f}/10 -> IA: {devine_nom} | vrai: {vrai_nom}")

    print(f"\nScore final : {nb_corrects}/{len(FRUITS_ENTRAINEMENT)} fruits bien reconnus.")
    return nb_corrects


def entrainer(nb_essais=2000, vitesse_apprentissage=0.5, details=False,
              afficher_tous_les=400, pas_a_pas_actif=False, sur_essai=None):
    expliquer_le_probleme()

    fruits_normalises = normaliser(FRUITS_ENTRAINEMENT)
    cibles = np.eye(len(NOMS_CATEGORIES))[VRAIES_CATEGORIES]

    np.random.seed(0)
    boutons = np.random.uniform(-1, 1, (2, len(NOMS_CATEGORIES)))
    seuils_de_base = np.random.uniform(-1, 1, len(NOMS_CATEGORIES))

    historique_erreur = []

    print(f"Debut de l'entrainement : {nb_essais} essais, vitesse d'apprentissage {vitesse_apprentissage}\n")

    for essai in range(1, nb_essais + 1):
        probabilites = repartir_les_scores(fruits_normalises @ boutons + seuils_de_base)

        erreur = probabilites - cibles
        erreur_moyenne = float(np.mean(np.abs(erreur)))
        historique_erreur.append(erreur_moyenne)

        boutons -= vitesse_apprentissage * (fruits_normalises.T @ erreur) / len(FRUITS_ENTRAINEMENT)
        seuils_de_base -= vitesse_apprentissage * erreur.mean(axis=0)

        if details:
            print(f"\n--- Essai {essai} : ce que l'IA pense de chaque fruit ---")
            for ligne in construire_pensee(FRUITS_ENTRAINEMENT, VRAIES_CATEGORIES, probabilites):
                print(f"  {ligne}")
        elif essai == 1 or essai % afficher_tous_les == 0:
            print(f"Essai {essai:>6} | erreur moyenne : {erreur_moyenne:.4f} {barre_erreur(erreur_moyenne, 0.5)}")

        if sur_essai is not None:
            sur_essai({
                "essai": essai,
                "nb_essais": nb_essais,
                "erreur": erreur_moyenne,
                "pensees": construire_pensee(FRUITS_ENTRAINEMENT, VRAIES_CATEGORIES, probabilites),
                "corrects": calculer_corrects(VRAIES_CATEGORIES, probabilites),
                "poids1": boutons.tolist(),
                "poids2": None,
                "biais_sortie": seuils_de_base.tolist(),
            })

        pas_a_pas(pas_a_pas_actif)

    print("\nEntrainement termine ! Verifions ce que l'IA a retenu :\n")
    tester(boutons, seuils_de_base)

    sauvegarder_checkpoint("module8_fruits_multiples.json", {
        "noms_categories": NOMS_CATEGORIES,
        "boutons": boutons.tolist(),
        "seuils_de_base": seuils_de_base.tolist(),
        "historique_erreur": historique_erreur,
    })

    return boutons, seuils_de_base, historique_erreur


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 8 : une IA qui apprend a reconnaitre plusieurs fruits.")
    analyseur.add_argument("--details", action="store_true", help="Raconte la pensee de l'IA a chaque essai.")
    analyseur.add_argument("--essais", type=int, default=2000, help="Nombre d'essais (par defaut 2000).")
    analyseur.add_argument("--vitesse", type=float, default=0.5, help="Vitesse d'apprentissage (par defaut 0.5).")
    analyseur.add_argument("--afficher-tous-les", type=int, default=400, dest="afficher_tous_les")
    analyseur.add_argument("--pas-a-pas", action="store_true", dest="pas_a_pas_actif")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    entrainer(nb_essais=args.essais, vitesse_apprentissage=args.vitesse,
              details=args.details, afficher_tous_les=args.afficher_tous_les,
              pas_a_pas_actif=args.pas_a_pas_actif)
