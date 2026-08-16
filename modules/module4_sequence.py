"""
MODULE 4 — Deviner la suite
=============================

Une IA qui regarde les 3 derniers nombres d'une suite et doit deviner le
nombre suivant. C'est une introduction en douceur à ce qui se passe
derrière les IA qui écrivent du texte : elles ne "lisent" pas toute une
phrase d'un coup, elles regardent une petite "fenêtre" des derniers mots
(ici, des derniers nombres) pour deviner ce qui vient après.

On choisit une famille de suites (avec --famille) :

    - "addition"       : on ajoute toujours le meme nombre (2, 4, 6, 8, ...)
    - "multiplication"  : on double toujours le nombre precedent (1, 2, 4, 8, ...)
    - "fibonacci"       : chaque nombre est la somme des deux precedents (1, 1, 2, 3, 5, ...)

La regle n'est jamais donnee a l'IA : elle voit seulement une douzaine de
suites qui la suivent, avec des points de depart differents a chaque
fois, et doit la retrouver toute seule.

Elle a une "couche cachee" comme le module 1 (un étage de réflexion
intermédiaire), et une réponse finale libre comme le module 2 (un
nombre, pas juste 0 ou 1).

On peut aussi lui donner des LETTRES : elles sont converties en nombres
(A=1, B=2, ... Z=26) avant d'être montrées à l'IA, puis reconverties en
lettres pour l'affichage (voir --famille addition).

Usage :
    python -m modules.module4_sequence
    python -m modules.module4_sequence --famille multiplication --details
    python -m modules.module4_sequence --famille fibonacci
"""

import argparse

import numpy as np

from .utils import barre_erreur, pas_a_pas, sauvegarder_checkpoint

FENETRE = 3          # combien de nombres precedents l'IA regarde
NB_NEURONES_CACHES = 6

NOMS_FAMILLES = {
    "addition": "on ajoute toujours le meme nombre",
    "multiplication": "on double toujours le nombre precedent",
    "fibonacci": "chaque nombre est la somme des deux precedents",
}


def tasser_entre_0_et_1(x):
    return 1 / (1 + np.exp(-x))


def derivee_tassage(valeur_deja_tassee):
    return valeur_deja_tassee * (1 - valeur_deja_tassee)


def lettre_vers_nombre(lettre):
    return ord(lettre.upper()) - ord("A") + 1


def nombre_vers_lettre(nombre):
    n = int(round(nombre))
    n = max(1, min(26, n))
    return chr(n - 1 + ord("A"))


def generer_suites_entrainement(famille, nb_suites=12):
    """Fabrique une douzaine de petites suites qui suivent toutes la meme regle,
    mais avec des points de depart differents a chaque fois."""
    rng = np.random.default_rng(42)
    suites = []

    if famille == "addition":
        for _ in range(nb_suites):
            depart = int(rng.integers(1, 10))
            pas = int(rng.choice([-4, -3, -2, -1, 1, 2, 3, 4]))
            suites.append([depart + i * pas for i in range(5)])

    elif famille == "multiplication":
        for _ in range(nb_suites):
            depart = int(rng.integers(1, 6))
            suites.append([depart * (2 ** i) for i in range(5)])

    elif famille == "fibonacci":
        for _ in range(nb_suites):
            a, b = int(rng.integers(1, 8)), int(rng.integers(1, 8))
            suite = [a, b]
            for _ in range(3):
                suite.append(suite[-1] + suite[-2])
            suites.append(suite)

    else:
        raise ValueError(f"Famille inconnue : {famille}")

    return suites


def fabriquer_fenetres(suites):
    """Decoupe chaque suite en petites fenetres de 3 nombres -> le 4e nombre."""
    entrees, cibles = [], []
    for suite in suites:
        for i in range(len(suite) - FENETRE):
            entrees.append(suite[i:i + FENETRE])
            cibles.append(suite[i + FENETRE])
    return np.array(entrees, dtype=float), np.array(cibles, dtype=float).reshape(-1, 1)


def suites_test(famille):
    """Quelques suites jamais vues, pour verifier que l'IA a bien generalise."""
    if famille == "addition":
        return [([5, 10, 15], 20), ([9, 7, 5], 3), ([1, 4, 7], 10)]
    if famille == "multiplication":
        return [([3, 6, 12], 24), ([5, 10, 20], 40)]
    return [([2, 3, 5], 8), ([1, 4, 5], 9)]


def expliquer_le_probleme(famille, suites):
    print("CE QUE L'IA DOIT APPRENDRE")
    print("-" * 40)
    print(f"Regarder les {FENETRE} derniers nombres d'une suite, et deviner le suivant.")
    print("C'est le meme principe qui se cache derriere les IA qui ecrivent du")
    print("texte : elles regardent une 'fenetre' des derniers mots pour deviner")
    print("le mot suivant. Ici, la fenetre porte sur des nombres.\n")
    print(f"Famille de suites choisie : {famille}")
    print("(la regle n'est jamais donnee a l'IA, elle doit la retrouver seule)\n")
    print("Quelques suites d'entrainement, toutes avec un depart different :")
    for suite in suites[:4]:
        print(f"   {', '.join(str(n) for n in suite)}")
    print("   ...\n")
    print(f"L'IA a une couche cachee de {NB_NEURONES_CACHES} neurones (comme le module 1)")
    print("et une reponse finale libre, un nombre quelconque (comme le module 2).\n")


def raconter_la_pensee(essai, entrees, cibles, reponses):
    print(f"\n--- Essai {essai} : ce que l'IA pense de chaque suite ---")
    for fenetre, cible, reponse in zip(entrees, cibles, reponses):
        texte_fenetre = ", ".join(str(int(n)) for n in fenetre)
        vrai = float(cible[0])
        devine = float(reponse[0])
        ecart = abs(devine - vrai)
        if ecart < 0.5:
            commentaire = "Bonne reponse, elle va juste affiner sa confiance."
        elif ecart < max(2.0, abs(vrai) * 0.1):
            commentaire = "Presque bon, elle va corriger un peu ses boutons."
        else:
            commentaire = "Loin du compte, elle va corriger ses boutons plus fort."
        print(f"  Suite: {texte_fenetre} (vrai suivant: {vrai:.0f}) "
              f"-> l'IA devine {devine:.1f} (arrondi: {round(devine)}). -> {commentaire}")


def predire(entrees, boutons_couche_1, boutons_couche_2, valeur_de_base, echelle):
    entrees_normalisees = entrees / echelle
    reflexion = tasser_entre_0_et_1(entrees_normalisees @ boutons_couche_1)
    reponse_normalisee = reflexion @ boutons_couche_2 + valeur_de_base
    return reponse_normalisee * echelle


def tester(famille, boutons_couche_1, boutons_couche_2, valeur_de_base, echelle):
    print("\nTest sur des suites JAMAIS VUES pendant l'entrainement :")
    exemples = suites_test(famille)
    entrees = np.array([fenetre for fenetre, _ in exemples], dtype=float)
    reponses = predire(entrees, boutons_couche_1, boutons_couche_2, valeur_de_base, echelle)

    nb_corrects = 0
    for (fenetre, vrai), reponse in zip(exemples, reponses):
        texte_fenetre = ", ".join(str(n) for n in fenetre)
        devine = round(float(reponse[0]))
        correct = devine == vrai
        nb_corrects += int(correct)
        symbole = "OK" if correct else "X "
        print(f"   [{symbole}] {texte_fenetre}, ... -> IA devine {devine} | vrai : {vrai}")
    print(f"\nScore final : {nb_corrects}/{len(exemples)} suites jamais vues bien devinees.")

    if famille == "addition":
        print("\nEt avec des LETTRES (A=1, B=2, ... Z=26) :")
        exemple_lettres = ["A", "C", "E"]
        entree_nombres = np.array([[lettre_vers_nombre(l) for l in exemple_lettres]], dtype=float)
        reponse = predire(entree_nombres, boutons_couche_1, boutons_couche_2, valeur_de_base, echelle)
        lettre_devinee = nombre_vers_lettre(reponse[0, 0])
        print(f"   {', '.join(exemple_lettres)}, ... -> IA devine '{lettre_devinee}' (vrai : 'G')")

    return nb_corrects


def entrainer(nb_essais=9000, vitesse_apprentissage=0.05, details=False,
              afficher_tous_les=1000, pas_a_pas_actif=False, famille="addition"):
    suites = generer_suites_entrainement(famille)
    expliquer_le_probleme(famille, suites)

    entrees, cibles = fabriquer_fenetres(suites)
    # On ramene tout a une echelle confortable pour l'IA (entre -1 et 1 environ),
    # calculee a partir des plus grands nombres rencontres dans cette famille.
    echelle = float(max(np.abs(entrees).max(), np.abs(cibles).max(), 1) * 1.2)
    entrees_normalisees = entrees / echelle
    cibles_normalisees = cibles / echelle

    np.random.seed(42)
    boutons_couche_1 = np.random.uniform(-0.5, 0.5, (FENETRE, NB_NEURONES_CACHES))
    boutons_couche_2 = np.random.uniform(-0.5, 0.5, (NB_NEURONES_CACHES, 1))
    valeur_de_base = 0.0

    historique_erreur = []

    print(f"Debut de l'entrainement : {nb_essais} essais sur {len(entrees)} fenetres, "
          f"vitesse d'apprentissage {vitesse_apprentissage}\n")

    for essai in range(1, nb_essais + 1):
        reflexion = tasser_entre_0_et_1(entrees_normalisees @ boutons_couche_1)
        reponse_normalisee = reflexion @ boutons_couche_2 + valeur_de_base

        erreur = cibles_normalisees - reponse_normalisee
        erreur_moyenne = float(np.mean(np.abs(erreur)) * echelle)
        historique_erreur.append(erreur_moyenne)

        correction_reponse = erreur
        correction_reflexion = (correction_reponse @ boutons_couche_2.T) * derivee_tassage(reflexion)

        boutons_couche_2 += vitesse_apprentissage * (reflexion.T @ correction_reponse)
        valeur_de_base += vitesse_apprentissage * float(np.mean(correction_reponse))
        boutons_couche_1 += vitesse_apprentissage * (entrees_normalisees.T @ correction_reflexion)

        if details:
            raconter_la_pensee(essai, entrees, cibles, reponse_normalisee * echelle)
        elif essai == 1 or essai % afficher_tous_les == 0:
            print(f"Essai {essai:>6} | erreur moyenne : {erreur_moyenne:.2f} {barre_erreur(erreur_moyenne, echelle / 10)}")

        pas_a_pas(pas_a_pas_actif)

    print("\nEntrainement termine ! Verifions ce que l'IA a retenu :")
    tester(famille, boutons_couche_1, boutons_couche_2, valeur_de_base, echelle)

    sauvegarder_checkpoint(f"module4_sequence_{famille}.json", {
        "famille": famille,
        "boutons_couche_1": boutons_couche_1.tolist(),
        "boutons_couche_2": boutons_couche_2.tolist(),
        "valeur_de_base": valeur_de_base,
        "echelle": echelle,
        "historique_erreur": historique_erreur,
    })

    return boutons_couche_1, boutons_couche_2, valeur_de_base, historique_erreur


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 4 : une IA qui apprend a deviner la suite d'une sequence.")
    analyseur.add_argument("--details", action="store_true", help="Raconte la pensee de l'IA a chaque essai.")
    analyseur.add_argument("--essais", type=int, default=9000, help="Nombre d'essais (par defaut 9000).")
    analyseur.add_argument("--vitesse", type=float, default=0.05, help="Vitesse d'apprentissage (par defaut 0.05).")
    analyseur.add_argument("--afficher-tous-les", type=int, default=1000, dest="afficher_tous_les")
    analyseur.add_argument("--pas-a-pas", action="store_true", dest="pas_a_pas_actif")
    analyseur.add_argument("--famille", choices=list(NOMS_FAMILLES), default="addition",
                            help="Quelle regle de suite l'IA doit deviner (par defaut addition).")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    entrainer(nb_essais=args.essais, vitesse_apprentissage=args.vitesse,
              details=args.details, afficher_tous_les=args.afficher_tous_les,
              pas_a_pas_actif=args.pas_a_pas_actif, famille=args.famille)
