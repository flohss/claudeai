"""
MODULE 3 — Reconnaitre un fruit
=================================

Une IA qui apprend à distinguer une POMME d'une ORANGE à partir de deux
informations : le poids du fruit (en grammes) et sa rougeur (une note de
0 a 10 : 0 = pas rouge du tout, 10 = tres rouge).

Contrairement au module 1, cette IA n'a pas de couche cachee : un seul
etage de calcul suffit ici, car pomme et orange peuvent se separer par
une simple ligne de decision (une orange est en general plus lourde et
moins rouge qu'une pomme).

Usage :
    python -m modules.module3_fruits
    python -m modules.module3_fruits --details
"""

import argparse

import numpy as np

try:
    from .utils import barre_erreur, pas_a_pas, sauvegarder_checkpoint
except ImportError:
    # Permet aussi de lancer ce fichier tout seul (ex: bouton "Run" de
    # Pydroid3 sur Android), qui l'execute hors du package "modules".
    from utils import barre_erreur, pas_a_pas, sauvegarder_checkpoint

# poids (g), rougeur (0-10)
FRUITS_ENTRAINEMENT = np.array([
    [120, 8], [130, 7], [110, 9], [140, 6], [125, 8],
    [190, 2], [200, 1], [180, 3], [210, 2], [195, 1],
], dtype=float)

# 0 = Pomme, 1 = Orange
VRAIES_CATEGORIES = np.array([[0], [0], [0], [0], [0], [1], [1], [1], [1], [1]], dtype=float)

NOMS_CATEGORIES = ["Pomme", "Orange"]

# On ramene poids et rougeur a une echelle comparable (0..1 environ)
# pour que les deux informations pesent aussi lourd l'une que l'autre.
ECHELLE_POIDS = 250.0
ECHELLE_ROUGEUR = 10.0


def tasser_entre_0_et_1(x):
    return 1 / (1 + np.exp(-x))


def normaliser(fruits):
    return np.column_stack([
        fruits[:, 0] / ECHELLE_POIDS,
        fruits[:, 1] / ECHELLE_ROUGEUR,
    ])


def expliquer_le_probleme():
    print("CE QUE L'IA DOIT APPRENDRE")
    print("-" * 40)
    print("Reconnaitre une Pomme ou une Orange a partir de deux indices :")
    print("   - le poids du fruit (en grammes)")
    print("   - sa rougeur, notee de 0 (pas rouge) a 10 (tres rouge)\n")
    print("Exemples d'entrainement :")
    for (poids, rougeur), categorie in list(zip(FRUITS_ENTRAINEMENT, VRAIES_CATEGORIES))[:4]:
        print(f"   {poids:.0f}g, rougeur {rougeur:.0f}/10 -> {NOMS_CATEGORIES[int(categorie[0])]}")
    print("   ...\n")
    print("L'IA a deux boutons (un pour le poids, un pour la rougeur) et un")
    print("seuil de base. Elle combine les trois pour sortir un pourcentage")
    print("de confiance : pres de 0% = Pomme, pres de 100% = Orange.\n")


def construire_pensee(fruits, categories, confiances):
    lignes = []
    for (poids, rougeur), vraie_categorie, confiance in zip(fruits, categories, confiances):
        vrai_nom = NOMS_CATEGORIES[int(vraie_categorie[0])]
        devine_index = 1 if confiance[0] >= 0.5 else 0
        devine_nom = NOMS_CATEGORIES[devine_index]
        pourcentage = round(confiance[0] * 100) if devine_index == 1 else round((1 - confiance[0]) * 100)
        bonne_reponse = devine_nom == vrai_nom
        if bonne_reponse:
            commentaire = "Bonne reponse, elle va juste renforcer un peu sa confiance."
        else:
            commentaire = "Mauvaise reponse, elle va corriger ses boutons plus fort."
        lignes.append(f"Fruit {poids:.0f}g, rougeur {rougeur:.0f}/10 (vrai: {vrai_nom}) "
                       f"-> l'IA pense '{devine_nom}' a {pourcentage}%. -> {commentaire}")
    return lignes


def tester(boutons, seuil_de_base):
    fruits_normalises = normaliser(FRUITS_ENTRAINEMENT)
    confiances = tasser_entre_0_et_1(fruits_normalises @ boutons + seuil_de_base)

    nb_corrects = 0
    for (poids, rougeur), vraie_categorie, confiance in zip(FRUITS_ENTRAINEMENT, VRAIES_CATEGORIES, confiances):
        vrai_nom = NOMS_CATEGORIES[int(vraie_categorie[0])]
        devine_index = 1 if confiance[0] >= 0.5 else 0
        devine_nom = NOMS_CATEGORIES[devine_index]
        correct = devine_nom == vrai_nom
        nb_corrects += int(correct)
        symbole = "OK" if correct else "X "
        print(f"  [{symbole}] {poids:.0f}g, rougeur {rougeur:.0f}/10 -> IA: {devine_nom} | vrai: {vrai_nom}")

    print(f"\nScore final : {nb_corrects}/{len(FRUITS_ENTRAINEMENT)} fruits bien reconnus.")
    return nb_corrects


def entrainer(nb_essais=3000, vitesse_apprentissage=0.1, details=False,
              afficher_tous_les=500, pas_a_pas_actif=False, sur_essai=None):
    expliquer_le_probleme()

    fruits_normalises = normaliser(FRUITS_ENTRAINEMENT)

    np.random.seed(42)
    boutons = np.random.uniform(-1, 1, (2, 1))
    seuil_de_base = float(np.random.uniform(-1, 1))

    historique_erreur = []

    print(f"Debut de l'entrainement : {nb_essais} essais, vitesse d'apprentissage {vitesse_apprentissage}\n")

    for essai in range(1, nb_essais + 1):
        confiances = tasser_entre_0_et_1(fruits_normalises @ boutons + seuil_de_base)

        erreur = VRAIES_CATEGORIES - confiances
        erreur_moyenne = float(np.mean(np.abs(erreur)))
        historique_erreur.append(erreur_moyenne)

        correction = erreur * confiances * (1 - confiances)
        boutons += vitesse_apprentissage * (fruits_normalises.T @ correction)
        seuil_de_base += vitesse_apprentissage * float(np.mean(correction))

        if details:
            print(f"\n--- Essai {essai} : ce que l'IA pense de chaque fruit ---")
            for ligne in construire_pensee(FRUITS_ENTRAINEMENT, VRAIES_CATEGORIES, confiances):
                print(f"  {ligne}")
        elif essai == 1 or essai % afficher_tous_les == 0:
            print(f"Essai {essai:>6} | erreur moyenne : {erreur_moyenne:.4f} {barre_erreur(erreur_moyenne, 0.5)}")

        if sur_essai is not None:
            sur_essai({
                "essai": essai,
                "nb_essais": nb_essais,
                "erreur": erreur_moyenne,
                "pensees": construire_pensee(FRUITS_ENTRAINEMENT, VRAIES_CATEGORIES, confiances),
            })

        pas_a_pas(pas_a_pas_actif)

    print("\nEntrainement termine ! Verifions ce que l'IA a retenu :\n")
    tester(boutons, seuil_de_base)

    sauvegarder_checkpoint("module3_fruits.json", {
        "boutons": boutons.tolist(),
        "seuil_de_base": seuil_de_base,
        "historique_erreur": historique_erreur,
    })

    return boutons, seuil_de_base, historique_erreur


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 3 : une IA qui apprend a reconnaitre un fruit.")
    analyseur.add_argument("--details", action="store_true", help="Raconte la pensee de l'IA a chaque essai.")
    analyseur.add_argument("--essais", type=int, default=3000, help="Nombre d'essais (par defaut 3000).")
    analyseur.add_argument("--vitesse", type=float, default=0.1, help="Vitesse d'apprentissage (par defaut 0.1).")
    analyseur.add_argument("--afficher-tous-les", type=int, default=500, dest="afficher_tous_les")
    analyseur.add_argument("--pas-a-pas", action="store_true", dest="pas_a_pas_actif")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    entrainer(nb_essais=args.essais, vitesse_apprentissage=args.vitesse,
              details=args.details, afficher_tous_les=args.afficher_tous_les,
              pas_a_pas_actif=args.pas_a_pas_actif)
