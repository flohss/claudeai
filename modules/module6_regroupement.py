"""
MODULE 6 — Regrouper sans étiquettes
======================================

Jusqu'ici, chaque exemple donné à l'IA venait avec la bonne réponse
(le prix, la catégorie, la suite...). Ce module change complètement de
principe : l'IA reçoit des animaux décrits par leur taille et leur
poids, mais PERSONNE ne lui dit à quelle espèce ils appartiennent. Elle
doit elle-même repérer que certains animaux se ressemblent entre eux et
les ranger en groupes — c'est ce qu'on appelle l'apprentissage NON
SUPERVISÉ.

Petite différence importante : ce module n'a pas de "vitesse
d'apprentissage". À chaque essai, elle ne corrige pas ses groupes tout
doucement comme avant : elle recalcule directement le milieu exact de
chaque groupe. C'est une autre façon d'apprendre.

La méthode, en deux étapes répétées à chaque essai :
    1. Chaque animal rejoint le groupe dont le centre est le plus proche.
    2. Chaque centre de groupe se déplace au milieu des animaux qui
       viennent de le rejoindre.
Au bout de quelques essais, les centres arrêtent de bouger : les
groupes sont stables.

On connaît en secret la vraie espèce de chaque animal (pour pouvoir
vérifier le travail de l'IA à la fin), mais elle ne l'a JAMAIS vue.

Usage :
    python -m modules.module6_regroupement
    python -m modules.module6_regroupement --details --essais 5
"""

import argparse
from collections import Counter

import numpy as np

try:
    from .utils import pas_a_pas, sauvegarder_checkpoint
except ImportError:
    # Permet aussi de lancer ce fichier tout seul (ex: bouton "Run" de
    # Pydroid3 sur Android), qui l'execute hors du package "modules".
    from utils import pas_a_pas, sauvegarder_checkpoint

NB_GROUPES_PAR_DEFAUT = 3


def generer_exemples():
    """Fabrique des animaux avec une taille (cm) et un poids (kg), en secret
    regroupes en 3 especes. L'IA ne recevra JAMAIS la colonne "espece"."""
    rng = np.random.default_rng(7)

    def fabriquer(n, centre_taille, centre_poids, ecart_taille, ecart_poids):
        tailles = rng.normal(centre_taille, ecart_taille, n)
        poids = rng.normal(centre_poids, ecart_poids, n)
        return np.column_stack([tailles, poids])

    groupes_secrets = [
        ("petit oiseau", fabriquer(6, 15, 0.35, 2.5, 0.08)),
        ("chat ou chien", fabriquer(6, 55, 17, 7, 3)),
        ("cheval", fabriquer(6, 155, 400, 12, 40)),
    ]

    entrees, vraies_especes = [], []
    for nom_espece, points in groupes_secrets:
        for point in points:
            entrees.append(point)
            vraies_especes.append(nom_espece)

    return np.array(entrees), vraies_especes


def calculer_echelles(entrees):
    echelles = np.abs(entrees).max(axis=0) * 1.2
    echelles[echelles == 0] = 1.0
    return echelles


def calculer_distances(entrees_normalisees, centres):
    """Distance (au carre) de chaque animal a chaque centre de groupe."""
    difference = entrees_normalisees[:, None, :] - centres[None, :, :]
    return (difference ** 2).sum(axis=2)


def expliquer_le_probleme(nb_groupes):
    print("CE QUE L'IA DOIT APPRENDRE")
    print("-" * 40)
    print("Ranger des animaux en groupes, a partir de leur taille (cm) et")
    print("leur poids (kg) SEULEMENT. Personne ne lui dit leur espece.\n")
    print(f"On lui demande de trouver {nb_groupes} groupes. Elle place d'abord")
    print("ses centres de groupe au hasard, puis a chaque essai :")
    print("   1. Chaque animal rejoint le centre le plus proche")
    print("   2. Chaque centre se deplace au milieu de ses animaux\n")


def raconter_la_pensee(essai, entrees, groupes_assignes, centres, echelles, distances):
    lignes = [f"\n--- Essai {essai} : qui rejoint quel groupe ---"]
    for (taille, poids), groupe, ligne_distances in zip(entrees, groupes_assignes, distances):
        distance = float(ligne_distances[groupe]) ** 0.5
        lignes.append(f"  Animal {taille:.0f}cm, {poids:.1f}kg -> rejoint le Groupe {groupe + 1} "
                       f"(distance a son centre : {distance:.2f}).")
    lignes.append(f"--- Essai {essai} : ou se trouvent les centres maintenant ---")
    for indice_groupe, centre in enumerate(centres):
        vraie_position = centre * echelles
        nb_membres = int(np.sum(groupes_assignes == indice_groupe))
        lignes.append(f"  Centre du Groupe {indice_groupe + 1} : environ {vraie_position[0]:.0f}cm, "
                       f"{vraie_position[1]:.1f}kg ({nb_membres} animaux dedans).")
    for ligne in lignes:
        print(ligne)


def tester(entrees, vraies_especes, groupes_assignes, nb_groupes):
    print("\nOn devoile maintenant les vraies especes (jamais montrees a l'IA) :\n")

    majorite_par_groupe = {}
    for indice_groupe in range(nb_groupes):
        especes_du_groupe = [vraies_especes[i] for i in range(len(vraies_especes)) if groupes_assignes[i] == indice_groupe]
        if especes_du_groupe:
            majorite_par_groupe[indice_groupe] = Counter(especes_du_groupe).most_common(1)[0][0]
        else:
            majorite_par_groupe[indice_groupe] = "(groupe vide)"

    nb_corrects = 0
    for (taille, poids), vraie_espece, groupe in zip(entrees, vraies_especes, groupes_assignes):
        devine = majorite_par_groupe[groupe]
        correct = devine == vraie_espece
        nb_corrects += int(correct)
        symbole = "OK" if correct else "X "
        print(f"  [{symbole}] {taille:.0f}cm, {poids:.1f}kg -> Groupe {groupe + 1} "
              f"(surtout des '{devine}') | vraie espece : {vraie_espece}")

    print(f"\nScore final : {nb_corrects}/{len(entrees)} animaux bien regroupes "
          f"(verification possible seulement parce qu'on connaissait la vraie reponse en secret).")
    return nb_corrects


def entrainer(nb_essais=10, nb_groupes=NB_GROUPES_PAR_DEFAUT, details=False,
              afficher_tous_les=2, pas_a_pas_actif=False, sur_essai=None):
    expliquer_le_probleme(nb_groupes)

    entrees, vraies_especes = generer_exemples()
    echelles = calculer_echelles(entrees)
    entrees_normalisees = entrees / echelles

    rng = np.random.default_rng(42)
    indices_initiaux = rng.choice(len(entrees), size=nb_groupes, replace=False)
    centres = entrees_normalisees[indices_initiaux].copy()

    historique_erreur = []
    groupes_assignes = np.zeros(len(entrees), dtype=int)

    print(f"Debut de l'entrainement : {nb_essais} essais, {nb_groupes} groupes recherches\n")

    for essai in range(1, nb_essais + 1):
        distances = calculer_distances(entrees_normalisees, centres)
        groupes_assignes = np.argmin(distances, axis=1)
        erreur = float(np.mean(np.min(distances, axis=1)))
        historique_erreur.append(erreur)

        nouveaux_centres = centres.copy()
        for indice_groupe in range(nb_groupes):
            membres = entrees_normalisees[groupes_assignes == indice_groupe]
            if len(membres) > 0:
                nouveaux_centres[indice_groupe] = membres.mean(axis=0)
        deplacement = float(np.mean(np.linalg.norm(nouveaux_centres - centres, axis=1)))
        centres = nouveaux_centres

        if details:
            raconter_la_pensee(essai, entrees, groupes_assignes, centres, echelles, distances)
        elif essai == 1 or essai % afficher_tous_les == 0:
            print(f"Essai {essai:>4} | distance moyenne au centre : {erreur:.4f} | "
                  f"deplacement des centres : {deplacement:.4f}")

        if sur_essai is not None:
            sur_essai({
                "essai": essai,
                "nb_essais": nb_essais,
                "erreur": erreur,
                "deplacement": deplacement,
                "points": [[float(t), float(p)] for t, p in entrees],
                "groupes": [int(g) for g in groupes_assignes],
                "centres": [[float(c) for c in (centre * echelles)] for centre in centres],
            })

        pas_a_pas(pas_a_pas_actif)

        if deplacement < 1e-6 and essai > 1:
            print(f"\nLes centres ne bougent plus depuis l'essai {essai} : on peut s'arreter la.")
            break

    print("\nEntrainement termine !")
    tester(entrees, vraies_especes, groupes_assignes, nb_groupes)

    sauvegarder_checkpoint("module6_regroupement.json", {
        "centres": (centres * echelles).tolist(),
        "nb_groupes": nb_groupes,
        "historique_erreur": historique_erreur,
    })

    return centres, groupes_assignes, historique_erreur


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 6 : une IA qui regroupe des animaux sans etiquettes.")
    analyseur.add_argument("--details", action="store_true", help="Raconte la pensee de l'IA a chaque essai.")
    analyseur.add_argument("--essais", type=int, default=10, help="Nombre d'essais maximum (par defaut 10).")
    analyseur.add_argument("--groupes", type=int, default=NB_GROUPES_PAR_DEFAUT, dest="nb_groupes",
                            help="Combien de groupes chercher (par defaut 3).")
    analyseur.add_argument("--afficher-tous-les", type=int, default=2, dest="afficher_tous_les")
    analyseur.add_argument("--pas-a-pas", action="store_true", dest="pas_a_pas_actif")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    entrainer(nb_essais=args.essais, nb_groupes=args.nb_groupes, details=args.details,
              afficher_tous_les=args.afficher_tous_les, pas_a_pas_actif=args.pas_a_pas_actif)
