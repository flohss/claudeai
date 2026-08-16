"""
MODULE 2 — Deviner un prix
============================

Une IA qui apprend à estimer le prix d'une maison à partir de sa seule
taille (en m²). Contrairement au module 1, elle ne devine plus juste
"0 ou 1" : elle devine un NOMBRE, qui peut prendre n'importe quelle valeur.

L'IA cherche une droite qui passe le mieux possible au milieu de tous les
exemples :

    prix devine = taille x multiplicateur + valeur_de_base

"multiplicateur" et "valeur_de_base" sont les deux seuls boutons de cette
IA. Au debut ils sont au hasard, et l'entrainement consiste a les tourner
petit a petit pour que la droite colle de mieux en mieux aux exemples.

Usage :
    python -m modules.module2_prix
    python -m modules.module2_prix --details
"""

import argparse

import numpy as np

try:
    from .utils import barre_erreur, euros, pas_a_pas, sauvegarder_checkpoint
except ImportError:
    # Permet aussi de lancer ce fichier tout seul (ex: bouton "Run" de
    # Pydroid3 sur Android), qui l'execute hors du package "modules".
    from utils import barre_erreur, euros, pas_a_pas, sauvegarder_checkpoint

# Quelques maisons deja vendues, avec leur vrai prix (regle cachee que
# l'IA doit deviner : environ 2500 euros le m2, plus 15000 euros de base).
TAILLES_ENTRAINEMENT = np.array([30, 45, 60, 75, 90, 110, 130, 150, 180, 200], dtype=float)
PRIX_ENTRAINEMENT = TAILLES_ENTRAINEMENT * 2500 + 15000

# Des maisons jamais vues, pour verifier que l'IA generalise bien.
TAILLES_TEST = np.array([40, 100, 165, 190], dtype=float)
PRIX_TEST = TAILLES_TEST * 2500 + 15000

# On travaille en dizaines de m2 et en milliers d'euros pour que les
# calculs restent a une echelle confortable pour l'IA (sinon les
# corrections seraient enormes et l'entrainement partirait dans tous les sens).
ECHELLE_TAILLE = 10.0
ECHELLE_PRIX = 1000.0


def expliquer_le_probleme():
    print("CE QUE L'IA DOIT APPRENDRE")
    print("-" * 40)
    print("Deviner le prix d'une maison a partir de sa taille (en m2).")
    print("Elle ne connait pas la formule a l'avance : elle va la deviner")
    print("en regardant des maisons deja vendues.\n")
    print("Exemples d'entrainement (taille -> prix reel) :")
    for taille, prix in list(zip(TAILLES_ENTRAINEMENT, PRIX_ENTRAINEMENT))[:4]:
        print(f"   {taille:.0f} m2 -> {euros(prix)}")
    print("   ...\n")
    print("L'IA va chercher deux boutons :")
    print("   - un 'multiplicateur' : combien coute chaque m2 supplementaire")
    print("   - une 'valeur_de_base' : le prix de depart, meme pour 0 m2")
    print("Formule : prix devine = taille x multiplicateur + valeur_de_base\n")


def construire_pensee(tailles, prix_reels, prix_devines):
    lignes = []
    for taille, prix_reel, prix_devine in zip(tailles, prix_reels, prix_devines):
        ecart = prix_devine - prix_reel
        if abs(ecart) < 1000:
            commentaire = "Tres proche, elle va juste ajuster tres legerement."
        elif ecart > 0:
            commentaire = "Elle a devine trop cher, elle va baisser un peu ses boutons."
        else:
            commentaire = "Elle a devine trop bas, elle va augmenter un peu ses boutons."
        lignes.append(f"Maison de {taille:.0f} m2 (vrai prix : {euros(prix_reel)}) "
                       f"-> l'IA devine {euros(prix_devine)}. -> {commentaire}")
    return lignes


def tester(multiplicateur, valeur_de_base):
    print("\nTest sur des maisons JAMAIS VUES pendant l'entrainement :")
    ecart_total = 0.0
    for taille, prix_reel in zip(TAILLES_TEST, PRIX_TEST):
        taille_normalisee = taille / ECHELLE_TAILLE
        prix_devine = (taille_normalisee * multiplicateur + valeur_de_base) * ECHELLE_PRIX
        ecart = abs(prix_devine - prix_reel)
        ecart_total += ecart
        print(f"   {taille:.0f} m2 -> l'IA devine {euros(prix_devine)} "
              f"(vrai prix : {euros(prix_reel)}, ecart : {euros(ecart)})")
    ecart_moyen = ecart_total / len(TAILLES_TEST)
    print(f"\nEcart moyen sur les maisons jamais vues : {euros(ecart_moyen)}")
    return ecart_moyen


def entrainer(nb_essais=5000, vitesse_apprentissage=0.01, details=False,
              afficher_tous_les=1000, pas_a_pas_actif=False, sur_essai=None):
    expliquer_le_probleme()

    tailles_normalisees = TAILLES_ENTRAINEMENT / ECHELLE_TAILLE
    prix_normalises = PRIX_ENTRAINEMENT / ECHELLE_PRIX

    np.random.seed(42)
    multiplicateur = float(np.random.uniform(-1, 1))
    valeur_de_base = float(np.random.uniform(-1, 1))

    historique_erreur = []
    nb_exemples = len(tailles_normalisees)

    print(f"Debut de l'entrainement : {nb_essais} essais, vitesse d'apprentissage {vitesse_apprentissage}\n")

    for essai in range(1, nb_essais + 1):
        prix_devines_normalises = tailles_normalisees * multiplicateur + valeur_de_base
        erreur = prix_normalises - prix_devines_normalises
        erreur_moyenne_euros = float(np.mean(np.abs(erreur)) * ECHELLE_PRIX)
        historique_erreur.append(erreur_moyenne_euros)

        # Correction : de combien et dans quel sens tourner chaque bouton
        # pour que la droite se rapproche des exemples.
        correction_multiplicateur = np.mean(erreur * tailles_normalisees)
        correction_valeur_de_base = np.mean(erreur)

        multiplicateur += vitesse_apprentissage * correction_multiplicateur
        valeur_de_base += vitesse_apprentissage * correction_valeur_de_base

        prix_devines = prix_devines_normalises * ECHELLE_PRIX

        if details:
            print(f"\n--- Essai {essai} : ce que l'IA pense de chaque maison ---")
            for ligne in construire_pensee(TAILLES_ENTRAINEMENT, PRIX_ENTRAINEMENT, prix_devines):
                print(f"  {ligne}")
        elif essai == 1 or essai % afficher_tous_les == 0:
            print(f"Essai {essai:>6} | ecart moyen : {euros(erreur_moyenne_euros)} "
                  f"{barre_erreur(erreur_moyenne_euros, 50000)}")

        if sur_essai is not None:
            sur_essai({
                "essai": essai,
                "nb_essais": nb_essais,
                "erreur": erreur_moyenne_euros,
                "pensees": construire_pensee(TAILLES_ENTRAINEMENT, PRIX_ENTRAINEMENT, prix_devines),
            })

        pas_a_pas(pas_a_pas_actif)

    print(f"\nEntrainement termine ! L'IA a trouve : environ {multiplicateur * ECHELLE_PRIX / ECHELLE_TAILLE:.0f} "
          f"euros par m2, avec une base de {euros(valeur_de_base * ECHELLE_PRIX)}.")
    tester(multiplicateur, valeur_de_base)

    sauvegarder_checkpoint("module2_prix.json", {
        "multiplicateur": multiplicateur,
        "valeur_de_base": valeur_de_base,
        "echelle_taille": ECHELLE_TAILLE,
        "echelle_prix": ECHELLE_PRIX,
        "historique_erreur": historique_erreur,
    })

    return multiplicateur, valeur_de_base, historique_erreur


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 2 : une IA qui apprend a estimer un prix.")
    analyseur.add_argument("--details", action="store_true", help="Raconte la pensee de l'IA a chaque essai.")
    analyseur.add_argument("--essais", type=int, default=5000, help="Nombre d'essais (par defaut 5000).")
    analyseur.add_argument("--vitesse", type=float, default=0.01, help="Vitesse d'apprentissage (par defaut 0.01).")
    analyseur.add_argument("--afficher-tous-les", type=int, default=1000, dest="afficher_tous_les")
    analyseur.add_argument("--pas-a-pas", action="store_true", dest="pas_a_pas_actif")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    entrainer(nb_essais=args.essais, vitesse_apprentissage=args.vitesse,
              details=args.details, afficher_tous_les=args.afficher_tous_les,
              pas_a_pas_actif=args.pas_a_pas_actif)
