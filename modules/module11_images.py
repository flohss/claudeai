"""
MODULE 11 — Reconnaitre une petite image
============================================

Jusqu'ici, chaque IA recevait quelques caracteristiques deja resumees
pour elle (un poids, une couleur, une forme...). Ce module change ca :
l'IA regarde directement une petite IMAGE, pixel par pixel, sans que
personne lui ait deja explique ce qu'elle represente.

L'image est une grille de 4x4 = 16 pixels, chacun soit allume (1) soit
eteint (0). L'IA doit reconnaitre laquelle de 3 formes est dessinee :
Carre, Croix ou Ligne. Chaque pixel devient une entree, exactement
comme le poids ou la forme l'etaient dans le module 8 — sauf qu'ici il
y en a 16 au lieu de 2, et chacun a son propre bouton par forme
possible.

Meme methode que le module 8 (plusieurs categories, un score par forme
qui se transforme en pourcentages qui totalisent 100%) : ce module est
surtout nouveau par ce qu'il montre a l'IA, pas par comment elle apprend.

Usage :
    python -m modules.module11_images
    python -m modules.module11_images --details
"""

import argparse

import numpy as np

try:
    from .utils import arrondi_sur, barre_erreur, pas_a_pas, sauvegarder_checkpoint
except ImportError:
    # Permet aussi de lancer ce fichier tout seul (ex: bouton "Run" de
    # Pydroid3 sur Android), qui l'execute hors du package "modules".
    from utils import arrondi_sur, barre_erreur, pas_a_pas, sauvegarder_checkpoint

TAILLE_GRILLE = 4
NB_PIXELS = TAILLE_GRILLE * TAILLE_GRILLE
NB_EXEMPLES_PAR_FORME = 18
NB_PIXELS_BRUITES_MAX = 2

# Les 3 formes "de reference". 1 = pixel allume (noir), 0 = pixel eteint.
FORMES_REFERENCE = {
    "Carre": np.array([
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
    ]),
    "Croix": np.array([
        [1, 0, 0, 1],
        [0, 1, 1, 0],
        [0, 1, 1, 0],
        [1, 0, 0, 1],
    ]),
    "Ligne": np.array([
        [0, 0, 0, 0],
        [1, 1, 1, 1],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]),
}

NOMS_CATEGORIES = list(FORMES_REFERENCE.keys())


def dessiner_image(image_plate):
    """Transforme les 16 pixels (0/1) en petit dessin ASCII pour le terminal."""
    grille = image_plate.reshape(TAILLE_GRILLE, TAILLE_GRILLE)
    return "\n".join("".join("#" if pixel else "." for pixel in ligne) for ligne in grille)


def generer_exemples():
    """Fabrique des images d'entrainement en partant de chaque forme de
    reference et en "salissant" au hasard quelques pixels (0, 1 ou 2) —
    pour que l'IA apprenne a reconnaitre la forme meme un peu imparfaite,
    pas seulement le dessin parfait."""
    rng = np.random.default_rng(3)
    images, categories = [], []

    for indice_categorie, nom in enumerate(NOMS_CATEGORIES):
        base = FORMES_REFERENCE[nom].flatten()
        for _ in range(NB_EXEMPLES_PAR_FORME):
            image = base.copy()
            nb_bruit = int(rng.integers(0, NB_PIXELS_BRUITES_MAX + 1))
            if nb_bruit:
                positions = rng.choice(NB_PIXELS, size=nb_bruit, replace=False)
                image[positions] = 1 - image[positions]
            images.append(image)
            categories.append(indice_categorie)

    images = np.array(images, dtype=float)
    categories = np.array(categories)

    ordre = rng.permutation(len(images))
    return images[ordre], categories[ordre]


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
    print(f"Reconnaitre une petite image de {TAILLE_GRILLE}x{TAILLE_GRILLE} pixels parmi")
    print(f"{len(NOMS_CATEGORIES)} formes possibles : {', '.join(NOMS_CATEGORIES)}.\n")
    print("Nouveaute par rapport aux modules precedents : personne ne resume")
    print("l'image en 'caracteristiques' pour elle (comme un poids ou une")
    print(f"couleur). Elle regarde directement les {NB_PIXELS} pixels, un par un —")
    print("chaque pixel devient une entree, avec son propre bouton par forme.\n")
    print("Les 3 formes de reference :\n")
    for nom, forme in FORMES_REFERENCE.items():
        print(f"  {nom} :")
        for ligne in dessiner_image(forme.flatten()).split("\n"):
            print(f"    {ligne}")
        print()
    print("Chaque image d'entrainement part d'une de ces formes, avec parfois")
    print("1 ou 2 pixels 'salis' au hasard, pour que l'IA apprenne a reconnaitre")
    print("la forme meme un peu imparfaite.\n")


def construire_pensee(images, vraies_categories, probabilites):
    lignes = []
    for indice, (vraie_categorie, probas) in enumerate(zip(vraies_categories, probabilites)):
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
        lignes.append(f"Image {indice + 1} (vraie forme: {vrai_nom}) "
                       f"-> l'IA pense '{devine_nom}' a {pourcentage_principal}% ({autres}). -> {commentaire}")
    return lignes


def calculer_corrects(vraies_categories, probabilites):
    """Pour chaque image, l'IA a-t-elle actuellement la bonne reponse ?
    Utilise par l'interface graphique pour dessiner une petite grille
    qui se colore en vert au fil de l'entrainement."""
    return [bool(int(np.argmax(probas)) == vraie) for vraie, probas in zip(vraies_categories, probabilites)]


def tester(images, vraies_categories, boutons, seuils_de_base, details=False):
    probabilites = repartir_les_scores(images @ boutons + seuils_de_base)

    nb_corrects = 0
    for indice, (vraie_categorie, probas) in enumerate(zip(vraies_categories, probabilites)):
        vrai_nom = NOMS_CATEGORIES[vraie_categorie]
        devine_nom = NOMS_CATEGORIES[int(np.argmax(probas))]
        correct = devine_nom == vrai_nom
        nb_corrects += int(correct)
        symbole = "OK" if correct else "X "
        print(f"  [{symbole}] Image {indice + 1} -> IA: {devine_nom} | vraie forme: {vrai_nom}")
        if details:
            for ligne in dessiner_image(images[indice]).split("\n"):
                print(f"       {ligne}")

    print(f"\nScore final : {nb_corrects}/{len(images)} images bien reconnues.")
    return nb_corrects


def entrainer(nb_essais=3000, vitesse_apprentissage=0.5, details=False,
              afficher_tous_les=400, pas_a_pas_actif=False, sur_essai=None):
    expliquer_le_probleme()

    images, vraies_categories = generer_exemples()
    cibles = np.eye(len(NOMS_CATEGORIES))[vraies_categories]

    np.random.seed(0)
    boutons = np.random.uniform(-1, 1, (NB_PIXELS, len(NOMS_CATEGORIES)))
    seuils_de_base = np.random.uniform(-1, 1, len(NOMS_CATEGORIES))

    historique_erreur = []

    print(f"Debut de l'entrainement : {nb_essais} essais, vitesse d'apprentissage {vitesse_apprentissage}, "
          f"{len(images)} images d'entrainement\n")

    for essai in range(1, nb_essais + 1):
        probabilites = repartir_les_scores(images @ boutons + seuils_de_base)

        erreur = probabilites - cibles
        erreur_moyenne = float(np.mean(np.abs(erreur)))
        historique_erreur.append(erreur_moyenne)

        boutons -= vitesse_apprentissage * (images.T @ erreur) / len(images)
        seuils_de_base -= vitesse_apprentissage * erreur.mean(axis=0)

        if details:
            print(f"\n--- Essai {essai} : ce que l'IA pense de chaque image ---")
            for ligne in construire_pensee(images, vraies_categories, probabilites):
                print(f"  {ligne}")
        elif essai == 1 or essai % afficher_tous_les == 0:
            print(f"Essai {essai:>6} | erreur moyenne : {erreur_moyenne:.4f} {barre_erreur(erreur_moyenne, 0.5)}")

        if sur_essai is not None:
            sur_essai({
                "essai": essai,
                "nb_essais": nb_essais,
                "erreur": erreur_moyenne,
                "pensees": construire_pensee(images, vraies_categories, probabilites),
                "corrects": calculer_corrects(vraies_categories, probabilites),
                "poids1": boutons.tolist(),
                "poids2": None,
                "biais_sortie": seuils_de_base.tolist(),
            })

        pas_a_pas(pas_a_pas_actif)

    print("\nEntrainement termine ! Verifions ce que l'IA a retenu :\n")
    tester(images, vraies_categories, boutons, seuils_de_base, details=details)

    sauvegarder_checkpoint("module11_images.json", {
        "noms_categories": NOMS_CATEGORIES,
        "taille_grille": TAILLE_GRILLE,
        "boutons": boutons.tolist(),
        "seuils_de_base": seuils_de_base.tolist(),
        "historique_erreur": historique_erreur,
    })

    return boutons, seuils_de_base, historique_erreur


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 11 : une IA qui apprend a reconnaitre une petite image.")
    analyseur.add_argument("--details", action="store_true", help="Raconte la pensee de l'IA a chaque essai.")
    analyseur.add_argument("--essais", type=int, default=3000, help="Nombre d'essais (par defaut 3000).")
    analyseur.add_argument("--vitesse", type=float, default=0.5, help="Vitesse d'apprentissage (par defaut 0.5).")
    analyseur.add_argument("--afficher-tous-les", type=int, default=400, dest="afficher_tous_les")
    analyseur.add_argument("--pas-a-pas", action="store_true", dest="pas_a_pas_actif")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    entrainer(nb_essais=args.essais, vitesse_apprentissage=args.vitesse,
              details=args.details, afficher_tous_les=args.afficher_tous_les,
              pas_a_pas_actif=args.pas_a_pas_actif)
