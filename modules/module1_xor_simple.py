"""
MODULE 1 — Le OU EXCLUSIF (XOR)
================================

La toute première IA de la suite. Elle doit apprendre une règle logique
toute simple à partir de seulement 4 exemples : le "OU EXCLUSIF" (XOR).

La règle à deviner :
    - Si les deux entrées sont PAREILLES  -> la réponse est 0 (faux)
    - Si les deux entrées sont DIFFERENTES -> la réponse est 1 (vrai)

Ce problème est célèbre en pédagogie de l'IA car une IA "à un seul étage"
(sans couche cachée) ne peut PAS l'apprendre, quel que soit le temps
qu'on lui laisse. Il lui faut un étage de réflexion intermédiaire :
c'est ce que ce module montre, calcul par calcul.

Usage :
    python -m modules.module1_xor_simple
    python -m modules.module1_xor_simple --details
"""

import argparse

import numpy as np

try:
    from .utils import arrondi_sur, barre_erreur, pas_a_pas, sauvegarder_checkpoint
except ImportError:
    # Permet aussi de lancer ce fichier tout seul (ex: bouton "Run" de
    # Pydroid3 sur Android), qui l'execute hors du package "modules".
    from utils import arrondi_sur, barre_erreur, pas_a_pas, sauvegarder_checkpoint

EXEMPLES_ENTREE = np.array([
    [0, 0],
    [0, 1],
    [1, 0],
    [1, 1],
], dtype=float)

EXEMPLES_VRAIE_REPONSE = np.array([[0], [1], [1], [0]], dtype=float)

NB_NEURONES_CACHES = 4


def tasser_entre_0_et_1(x):
    """Ecrase n'importe quel nombre pour le ramener entre 0 et 1.

    Un grand nombre positif donne quelque chose proche de 1, un grand
    nombre negatif donne quelque chose proche de 0. C'est ce qui permet
    a l'IA d'exprimer sa reponse comme un pourcentage de confiance.
    """
    return 1 / (1 + np.exp(-x))


def derivee_tassage(valeur_deja_tassee):
    """A quel point une petite correction change la valeur tassee."""
    return valeur_deja_tassee * (1 - valeur_deja_tassee)


def expliquer_le_probleme():
    print("CE QUE L'IA DOIT APPRENDRE")
    print("-" * 40)
    print("La regle du OU EXCLUSIF (XOR) : la reponse est VRAIE seulement")
    print("si les deux entrees sont DIFFERENTES l'une de l'autre.\n")
    print("   0 et 0  ->  0   (pareil      -> faux)")
    print("   0 et 1  ->  1   (different   -> vrai)")
    print("   1 et 0  ->  1   (different   -> vrai)")
    print("   1 et 1  ->  0   (pareil      -> faux)\n")
    print("Au debut, l'IA ne connait rien : ses 'boutons' (les nombres qui")
    print("controlent ses calculs) sont regles au hasard. A chaque essai,")
    print("elle va regarder les 4 exemples, comparer sa reponse a la bonne")
    print("reponse, et tourner ses boutons un tout petit peu dans la bonne")
    print(f"direction. Elle a ici {NB_NEURONES_CACHES} 'neurones caches' : un petit")
    print("etage de reflexion intermediaire, indispensable pour ce probleme.\n")


def construire_pensee(reponse):
    """Construit les phrases qui racontent ce que l'IA pense de chaque exemple.

    Utilise a la fois par l'affichage CLI (--details) et par l'interface
    graphique, pour ne pas repeter deux fois la meme mise en phrase.
    """
    noms_entrees = ["0 et 0", "0 et 1", "1 et 0", "1 et 1"]
    lignes = []
    for i in range(len(EXEMPLES_ENTREE)):
        vrai = int(EXEMPLES_VRAIE_REPONSE[i, 0])
        pense = float(reponse[i, 0])
        pourcentage = arrondi_sur(pense * 100)
        verdict = "vrai (1)" if pense >= 0.5 else "faux (0)"
        bon = (pense >= 0.5) == (vrai == 1)
        commentaire = "Bonne reponse" if bon else "Mauvaise reponse, elle va corriger ses boutons"
        lignes.append(f"{noms_entrees[i]} (vraie reponse : {vrai}) -> l'IA pense '{verdict}' a {pourcentage}%. -> {commentaire}.")
    return lignes


def tester(boutons_couche_1, boutons_couche_2):
    reflexion = tasser_entre_0_et_1(EXEMPLES_ENTREE @ boutons_couche_1)
    reponse = tasser_entre_0_et_1(reflexion @ boutons_couche_2)

    noms_entrees = ["0 et 0", "0 et 1", "1 et 0", "1 et 1"]
    nb_corrects = 0
    for i in range(len(EXEMPLES_ENTREE)):
        vrai = int(EXEMPLES_VRAIE_REPONSE[i, 0])
        pense = float(reponse[i, 0])
        verdict = 1 if pense >= 0.5 else 0
        correct = verdict == vrai
        nb_corrects += int(correct)
        symbole = "OK" if correct else "X "
        print(f"  [{symbole}] {noms_entrees[i]} -> IA: {verdict} (confiance {pense * 100:.1f}%) | vrai: {vrai}")

    print(f"\nScore final : {nb_corrects}/{len(EXEMPLES_ENTREE)} exemples bien appris.")
    return nb_corrects


def entrainer(nb_essais=10000, vitesse_apprentissage=0.5, details=False,
              afficher_tous_les=1000, pas_a_pas_actif=False, sur_essai=None):
    """sur_essai(dict) est un rappel optionnel, appele a chaque essai avec
    un resume structure (utilise par l'interface graphique pour suivre
    l'entrainement en direct sans dupliquer les calculs)."""
    expliquer_le_probleme()

    np.random.seed(42)
    boutons_couche_1 = np.random.uniform(-1, 1, (2, NB_NEURONES_CACHES))
    boutons_couche_2 = np.random.uniform(-1, 1, (NB_NEURONES_CACHES, 1))

    historique_erreur = []

    print(f"Debut de l'entrainement : {nb_essais} essais, vitesse d'apprentissage {vitesse_apprentissage}\n")

    for essai in range(1, nb_essais + 1):
        # Etape 1 : l'IA reflechit (couche cachee)
        reflexion = tasser_entre_0_et_1(EXEMPLES_ENTREE @ boutons_couche_1)
        # Etape 2 : l'IA donne sa reponse finale
        reponse = tasser_entre_0_et_1(reflexion @ boutons_couche_2)

        erreur = EXEMPLES_VRAIE_REPONSE - reponse
        erreur_moyenne = float(np.mean(np.abs(erreur)))
        historique_erreur.append(erreur_moyenne)

        # Correction : on regarde de combien on s'est trompe, et on tourne
        # les boutons un peu dans la bonne direction (des sorties vers l'entree)
        correction_reponse = erreur * derivee_tassage(reponse)
        correction_reflexion = (correction_reponse @ boutons_couche_2.T) * derivee_tassage(reflexion)

        boutons_couche_2 += vitesse_apprentissage * (reflexion.T @ correction_reponse)
        boutons_couche_1 += vitesse_apprentissage * (EXEMPLES_ENTREE.T @ correction_reflexion)

        if details:
            print(f"\n--- Essai {essai} : ce que l'IA pense de chaque exemple ---")
            for ligne in construire_pensee(reponse):
                print(f"  {ligne}")
        elif essai == 1 or essai % afficher_tous_les == 0:
            print(f"Essai {essai:>6} | erreur moyenne : {erreur_moyenne:.4f} {barre_erreur(erreur_moyenne, 0.5)}")

        if sur_essai is not None:
            sur_essai({
                "essai": essai,
                "nb_essais": nb_essais,
                "erreur": erreur_moyenne,
                "pensees": construire_pensee(reponse),
                "poids1": boutons_couche_1.tolist(),
                "poids2": boutons_couche_2.tolist(),
                "biais_sortie": None,
            })

        pas_a_pas(pas_a_pas_actif)

    print("\nEntrainement termine ! Verifions ce que l'IA a retenu :\n")
    tester(boutons_couche_1, boutons_couche_2)

    sauvegarder_checkpoint("module1_xor.json", {
        "boutons_couche_1": boutons_couche_1.tolist(),
        "boutons_couche_2": boutons_couche_2.tolist(),
        "historique_erreur": historique_erreur,
    })

    return boutons_couche_1, boutons_couche_2, historique_erreur


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 1 : une IA qui apprend le OU EXCLUSIF (XOR).")
    analyseur.add_argument("--details", action="store_true", help="Raconte la pensee de l'IA a chaque essai.")
    analyseur.add_argument("--essais", type=int, default=10000, help="Nombre d'essais (par defaut 10000).")
    analyseur.add_argument("--vitesse", type=float, default=0.5, help="Vitesse d'apprentissage (par defaut 0.5).")
    analyseur.add_argument("--afficher-tous-les", type=int, default=1000, dest="afficher_tous_les")
    analyseur.add_argument("--pas-a-pas", action="store_true", dest="pas_a_pas_actif")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    entrainer(nb_essais=args.essais, vitesse_apprentissage=args.vitesse,
              details=args.details, afficher_tous_les=args.afficher_tous_les,
              pas_a_pas_actif=args.pas_a_pas_actif)
