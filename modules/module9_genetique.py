"""
MODULE 9 — Algorithme génétique : faire évoluer une population
==================================================================

Tous les modules precedents apprenaient en corrigeant petit a petit
UNE SEULE IA (ses boutons, ou sa memoire des choix). Celui-ci change
completement de methode : il n'y a pas de correction du tout. A la
place, une POPULATION de nombreuses solutions differentes evolue au
fil des generations, un peu comme la selection naturelle :

    1. On note chaque individu de la population (son "score")
    2. Seuls les meilleurs survivent et se reproduisent
    3. Leurs enfants heritent d'un melange de leurs deux parents
       (le "croisement"), avec parfois un petit changement au hasard
       (la "mutation")
    4. On recommence avec cette nouvelle generation

Le probleme choisi ici : deviner un mot secret, lettre par lettre.
Chaque individu est un mot au hasard (des lettres de A a Z), et son
score est le nombre de lettres a la bonne place. Aucun individu ne
"sait" quelles lettres sont justes : seule la selection des meilleurs
scores, generation apres generation, fait converger la population vers
le mot secret.

Usage :
    python -m modules.module9_genetique
    python -m modules.module9_genetique --details --generations 5
    python -m modules.module9_genetique --mot PYTHON
"""

import argparse
import string

import numpy as np

try:
    from .utils import pas_a_pas, sauvegarder_checkpoint
except ImportError:
    # Permet aussi de lancer ce fichier tout seul (ex: bouton "Run" de
    # Pydroid3 sur Android), qui l'execute hors du package "modules".
    from utils import pas_a_pas, sauvegarder_checkpoint

ALPHABET = string.ascii_uppercase
MOT_CIBLE_PAR_DEFAUT = "ALGORITHME"


def nouvel_individu(rng, n_lettres):
    return rng.integers(0, 26, n_lettres)


def mot_depuis_individu(individu):
    return "".join(ALPHABET[lettre] for lettre in individu)


def calculer_score(individu, cible_indices):
    return int(np.sum(individu == cible_indices))


def croiser(parent_a, parent_b, rng):
    """Fabrique un enfant en prenant, lettre par lettre, celle d'un
    parent ou de l'autre au hasard."""
    masque = rng.random(len(parent_a)) < 0.5
    return np.where(masque, parent_a, parent_b)


def muter(individu, rng, taux_mutation):
    """Avec une petite chance par lettre, la remplace par une lettre
    au hasard — c'est ce qui permet a la population de decouvrir des
    lettres qu'aucun parent n'avait."""
    enfant = individu.copy()
    masque = rng.random(len(individu)) < taux_mutation
    enfant[masque] = rng.integers(0, 26, int(masque.sum()))
    return enfant


def expliquer_le_probleme(mot_cible, taille_population, nb_survivants, taux_mutation):
    print("CE QUE LA POPULATION DOIT DECOUVRIR")
    print("-" * 40)
    print(f"Le mot secret a deviner est : {mot_cible} ({len(mot_cible)} lettres).")
    print("Attention : c'est nous qui le savons, pas la population ! Chaque")
    print("individu est un mot au hasard, et ne connait que son SCORE : le")
    print("nombre de lettres qu'il a placees au bon endroit.\n")
    print(f"Population de {taille_population} individus. A chaque generation :")
    print(f"   1. On calcule le score de chacun")
    print(f"   2. Les {nb_survivants} meilleurs survivent, les autres disparaissent")
    print("   3. On cree de nouveaux individus en croisant deux survivants")
    print(f"      au hasard, avec {taux_mutation * 100:.0f}% de chance par lettre qu'une mutation")
    print("      la change au hasard\n")
    print("(Le tout meilleur individu passe toujours tel quel a la generation")
    print("suivante, pour ne jamais perdre le meilleur qu'on ait trouve.)\n")


def construire_pensee(mots, scores, n_lettres):
    lignes = []
    moyenne = sum(scores) / len(scores)
    lignes.append(f"Meilleur individu : '{mots[0]}' -> score {scores[0]}/{n_lettres}.")
    lignes.append(f"Score moyen de toute la population : {moyenne:.1f}/{n_lettres}.")
    top5 = ", ".join(f"'{mot}' ({score})" for mot, score in zip(mots[:5], scores[:5]))
    lignes.append(f"Les 5 meilleurs de cette generation : {top5}.")
    return lignes


def entrainer(nb_generations=150, taille_population=40, nb_survivants=10, taux_mutation=0.05,
              mot_cible=MOT_CIBLE_PAR_DEFAUT, details=False, afficher_toutes_les=10,
              pas_a_pas_actif=False, sur_generation=None):
    mot_cible = mot_cible.upper()
    cible_indices = np.array([ALPHABET.index(lettre) for lettre in mot_cible])
    n_lettres = len(mot_cible)

    expliquer_le_probleme(mot_cible, taille_population, nb_survivants, taux_mutation)

    rng = np.random.default_rng(42)
    population = [nouvel_individu(rng, n_lettres) for _ in range(taille_population)]
    historique_scores = []
    mots, scores = [], []

    print(f"Debut de l'evolution : jusqu'a {nb_generations} generations\n")

    for generation in range(1, nb_generations + 1):
        scores = [calculer_score(individu, cible_indices) for individu in population]
        ordre = sorted(range(len(population)), key=lambda i: -scores[i])
        population = [population[i] for i in ordre]
        scores = [scores[i] for i in ordre]
        mots = [mot_depuis_individu(individu) for individu in population]

        historique_scores.append(scores[0])

        if details:
            print(f"\n--- Generation {generation} ---")
            for ligne in construire_pensee(mots, scores, n_lettres):
                print(f"  {ligne}")
        elif generation == 1 or generation % afficher_toutes_les == 0:
            moyenne = sum(scores) / len(scores)
            print(f"Generation {generation:>4} | meilleur : '{mots[0]}' ({scores[0]}/{n_lettres}) "
                  f"| moyenne : {moyenne:.1f}/{n_lettres}")

        if sur_generation is not None:
            sur_generation({
                "generation": generation,
                "nb_generations": nb_generations,
                "meilleur_mot": mots[0],
                "meilleur_score": scores[0],
                "n_lettres": n_lettres,
                "lettres_correctes": [lettre == vraie for lettre, vraie in zip(mots[0], mot_cible)],
                "moyenne_score": sum(scores) / len(scores),
                "population": [{"mot": mot, "score": score} for mot, score in zip(mots[:8], scores[:8])],
                "taille_population": len(population),
                "nb_survivants": nb_survivants,
            })

        pas_a_pas(pas_a_pas_actif)

        if scores[0] == n_lettres:
            print(f"\nLe mot secret a ete trouve a la generation {generation} : '{mots[0]}' !")
            break

        survivants = population[:nb_survivants]
        nouvelle_population = [population[0]]  # elitisme : le meilleur est toujours garde
        while len(nouvelle_population) < taille_population:
            parent_a = survivants[rng.integers(0, nb_survivants)]
            parent_b = survivants[rng.integers(0, nb_survivants)]
            enfant = croiser(parent_a, parent_b, rng)
            enfant = muter(enfant, rng, taux_mutation)
            nouvelle_population.append(enfant)
        population = nouvelle_population

    print(f"\nEvolution terminee ! Meilleur mot trouve : '{mots[0]}' ({scores[0]}/{n_lettres}).")

    sauvegarder_checkpoint("module9_genetique.json", {
        "mot_cible": mot_cible,
        "meilleur_mot_trouve": mots[0],
        "meilleur_score": scores[0],
        "historique_scores": historique_scores,
    })

    return mots[0], historique_scores


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 9 : une population qui evolue pour deviner un mot secret.")
    analyseur.add_argument("--details", action="store_true", help="Raconte ce qui se passe a chaque generation.")
    analyseur.add_argument("--generations", type=int, default=150, dest="nb_generations",
                            help="Nombre de generations maximum (par defaut 150).")
    analyseur.add_argument("--population", type=int, default=40, dest="taille_population",
                            help="Taille de la population (par defaut 40).")
    analyseur.add_argument("--survivants", type=int, default=10, dest="nb_survivants",
                            help="Combien d'individus survivent a chaque generation (par defaut 10).")
    analyseur.add_argument("--mutation", type=float, default=0.05, dest="taux_mutation",
                            help="Chance qu'une lettre mute, entre 0 et 1 (par defaut 0.05).")
    analyseur.add_argument("--mot", type=str, default=MOT_CIBLE_PAR_DEFAUT, dest="mot_cible",
                            help="Le mot secret a faire deviner (lettres A-Z uniquement).")
    analyseur.add_argument("--afficher-toutes-les", type=int, default=10, dest="afficher_toutes_les")
    analyseur.add_argument("--pas-a-pas", action="store_true", dest="pas_a_pas_actif")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    entrainer(nb_generations=args.nb_generations, taille_population=args.taille_population,
              nb_survivants=args.nb_survivants, taux_mutation=args.taux_mutation,
              mot_cible=args.mot_cible, details=args.details,
              afficher_toutes_les=args.afficher_toutes_les, pas_a_pas_actif=args.pas_a_pas_actif)
