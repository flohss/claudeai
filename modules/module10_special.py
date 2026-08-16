"""
MODULE 10 — SPECIAL : c'est vous le professeur
================================================

Dans tous les autres modules, les exemples etaient deja prepares a
l'avance. Ici, c'est different : VOUS donnez les exemples a l'IA, un
par un, en repondant a quelques questions. Elle n'apprend QUE ce que
vous lui montrez, sous vos yeux, avec les memes calculs transparents
que les autres modules.

Deux types de lecons possibles :
    - lui apprendre a CHOISIR entre deux categories (comme le module 3 :
      deux caracteristiques numeriques -> une categorie)
    - lui apprendre a DEVINER un nombre (comme le module 2 : une
      caracteristique numerique -> un nombre)

Usage :
    python -m modules.module10_special
    python -m modules.module10_special --details
"""

import argparse

import numpy as np

try:
    from .utils import pas_a_pas, sauvegarder_checkpoint
except ImportError:
    # Permet aussi de lancer ce fichier tout seul (ex: bouton "Run" de
    # Pydroid3 sur Android), qui l'execute hors du package "modules".
    from utils import pas_a_pas, sauvegarder_checkpoint

NB_ESSAIS_MINIMUM_EXEMPLES = 4
MOTS_POUR_TERMINER = ("fini", "fin", "termine", "terminé", "stop")


def tasser_entre_0_et_1(x):
    return 1 / (1 + np.exp(-x))


def expliquer_le_principe():
    print("CE QUE VOUS ALLEZ FAIRE")
    print("-" * 40)
    print("C'est vous qui allez enseigner quelque chose a l'IA, a partir de zero.")
    print("Elle ne sait rien au depart : elle va apprendre uniquement des")
    print(f"exemples que vous allez lui donner (au moins {NB_ESSAIS_MINIMUM_EXEMPLES}, mais plus vous")
    print("lui en donnez de varies, mieux elle comprendra la regle que vous avez")
    print("en tete.\n")


def demander_valeur_ou_fin(message):
    while True:
        texte = input(message).strip()
        if texte.lower() in MOTS_POUR_TERMINER:
            return None
        texte_normalise = texte.replace(",", ".")
        try:
            return float(texte_normalise)
        except ValueError:
            print("   Merci d'entrer un nombre valide (ex: 12 ou 3.5), ou 'fini' pour terminer.")


def demander_nombre(message):
    while True:
        texte = input(message).strip().replace(",", ".")
        try:
            return float(texte)
        except ValueError:
            print("   Merci d'entrer un nombre valide (ex: 12 ou 3.5).")


def demander_texte_non_vide(message):
    while True:
        texte = input(message).strip()
        if texte:
            return texte
        print("   Merci d'entrer une reponse non vide.")


def choisir_type_lecon():
    print("Que voulez-vous lui apprendre ?")
    print("  [1] A CHOISIR entre deux categories (ex: pomme ou orange)")
    print("  [2] A DEVINER un nombre (ex: un prix, une note, une duree...)")
    while True:
        choix = input("Votre choix (1 ou 2) : ").strip()
        if choix == "1":
            return "categories"
        if choix == "2":
            return "nombre"
        print("   Merci de repondre 1 ou 2.")


def demander_categorie(categorie_a, categorie_b):
    while True:
        reponse = input(f"   Categorie ({categorie_a}/{categorie_b}) : ").strip()
        if reponse.lower() == categorie_a.lower():
            return 0.0
        if reponse.lower() == categorie_b.lower():
            return 1.0
        print(f"   Merci de repondre '{categorie_a}' ou '{categorie_b}'.")


def collecter_exemples_categories():
    nom_car1 = demander_texte_non_vide("\nComment voulez-vous appeler la 1ere caracteristique (ex: poids) ? ")
    nom_car2 = demander_texte_non_vide("Et la 2eme caracteristique (ex: couleur) ? ")
    categorie_a = demander_texte_non_vide("Nom de la 1ere categorie (ex: Pomme) ? ")
    categorie_b = demander_texte_non_vide("Nom de la 2eme categorie (ex: Orange) ? ")

    print(f"\nDonnez-moi des exemples : pour chacun, {nom_car1}, {nom_car2}, puis la")
    print(f"bonne categorie ({categorie_a} ou {categorie_b}). Tapez 'fini' a la place")
    print(f"de {nom_car1} quand vous avez termine (minimum {NB_ESSAIS_MINIMUM_EXEMPLES} exemples, avec les deux categories).\n")

    entrees, sorties = [], []
    numero = 1
    while True:
        v1 = demander_valeur_ou_fin(f"Exemple {numero} - {nom_car1} (ou 'fini') : ")
        if v1 is None:
            if len(entrees) >= NB_ESSAIS_MINIMUM_EXEMPLES and len(set(sorties)) == 2:
                break
            print(f"   Il faut au moins {NB_ESSAIS_MINIMUM_EXEMPLES} exemples, avec les deux categories "
                  f"representees ({len(entrees)} donne(s), {len(set(sorties))} categorie(s) vue(s)).\n")
            continue
        v2 = demander_nombre(f"Exemple {numero} - {nom_car2} : ")
        categorie = demander_categorie(categorie_a, categorie_b)
        entrees.append([v1, v2])
        sorties.append(categorie)
        numero += 1

    return nom_car1, nom_car2, categorie_a, categorie_b, entrees, sorties


def collecter_exemples_nombre():
    nom_car = demander_texte_non_vide("\nComment voulez-vous appeler la caracteristique de depart (ex: taille) ? ")
    nom_sortie = demander_texte_non_vide("Et comment voulez-vous appeler ce qu'elle doit deviner (ex: prix) ? ")

    print(f"\nDonnez-moi des exemples : {nom_car} -> {nom_sortie} attendu. Tapez 'fini'")
    print(f"a la place de {nom_car} quand vous avez termine (minimum {NB_ESSAIS_MINIMUM_EXEMPLES} exemples).\n")

    entrees, sorties = [], []
    numero = 1
    while True:
        v = demander_valeur_ou_fin(f"Exemple {numero} - {nom_car} (ou 'fini') : ")
        if v is None:
            if len(entrees) >= NB_ESSAIS_MINIMUM_EXEMPLES:
                break
            print(f"   Il faut au moins {NB_ESSAIS_MINIMUM_EXEMPLES} exemples ({len(entrees)} donne(s) pour l'instant).\n")
            continue
        cible = demander_nombre(f"Exemple {numero} - {nom_sortie} attendu : ")
        entrees.append([v])
        sorties.append(cible)
        numero += 1

    return nom_car, nom_sortie, entrees, sorties


def calculer_echelles(valeurs):
    echelles = np.abs(valeurs).max(axis=0) * 1.2
    echelles[echelles == 0] = 1.0
    return echelles


def raconter_la_pensee_categories(essai, entrees, sorties, confiances, nom_car1, nom_car2, categorie_a, categorie_b):
    print(f"\n--- Essai {essai} : ce que l'IA pense de chaque exemple ---")
    for (v1, v2), vraie_categorie, confiance in zip(entrees, sorties, confiances):
        vrai_nom = categorie_b if vraie_categorie[0] == 1.0 else categorie_a
        devine_b = confiance[0] >= 0.5
        devine_nom = categorie_b if devine_b else categorie_a
        pourcentage = round((confiance[0] if devine_b else 1 - confiance[0]) * 100)
        bonne_reponse = devine_nom == vrai_nom
        commentaire = ("Bonne reponse, elle va juste renforcer un peu sa confiance." if bonne_reponse
                        else "Mauvaise reponse, elle va corriger ses boutons plus fort.")
        print(f"  {nom_car1} {v1:g}, {nom_car2} {v2:g} (vous avez dit: {vrai_nom}) "
              f"-> l'IA pense '{devine_nom}' a {pourcentage}%. -> {commentaire}")


def entrainer_categories(entrees, sorties, nom_car1, nom_car2, categorie_a, categorie_b,
                          vitesse_apprentissage, nb_essais, details, afficher_tous_les, pas_a_pas_actif):
    echelles = calculer_echelles(entrees)
    entrees_normalisees = entrees / echelles

    np.random.seed(42)
    boutons = np.random.uniform(-1, 1, (2, 1))
    seuil_de_base = float(np.random.uniform(-1, 1))

    historique_erreur = []

    print(f"\nDebut de l'entrainement sur VOS {len(entrees)} exemples : {nb_essais} essais, "
          f"vitesse d'apprentissage {vitesse_apprentissage}\n")

    for essai in range(1, nb_essais + 1):
        confiances = tasser_entre_0_et_1(entrees_normalisees @ boutons + seuil_de_base)

        erreur = sorties - confiances
        erreur_moyenne = float(np.mean(np.abs(erreur)))
        historique_erreur.append(erreur_moyenne)

        correction = erreur * confiances * (1 - confiances)
        boutons += vitesse_apprentissage * (entrees_normalisees.T @ correction)
        seuil_de_base += vitesse_apprentissage * float(np.mean(correction))

        if details:
            raconter_la_pensee_categories(essai, entrees, sorties, confiances, nom_car1, nom_car2, categorie_a, categorie_b)
        elif essai == 1 or essai % afficher_tous_les == 0:
            print(f"Essai {essai:>6} | erreur moyenne : {erreur_moyenne:.4f}")

        pas_a_pas(pas_a_pas_actif)

    return boutons, seuil_de_base, echelles, historique_erreur


def tester_categories(entrees, sorties, boutons, seuil_de_base, echelles, nom_car1, nom_car2, categorie_a, categorie_b):
    print("\nCe que l'IA a retenu de vos exemples :\n")
    entrees_normalisees = entrees / echelles
    confiances = tasser_entre_0_et_1(entrees_normalisees @ boutons + seuil_de_base)

    nb_corrects = 0
    for (v1, v2), vraie_categorie, confiance in zip(entrees, sorties, confiances):
        vrai_nom = categorie_b if vraie_categorie[0] == 1.0 else categorie_a
        devine_nom = categorie_b if confiance[0] >= 0.5 else categorie_a
        correct = devine_nom == vrai_nom
        nb_corrects += int(correct)
        symbole = "OK" if correct else "X "
        print(f"  [{symbole}] {nom_car1} {v1:g}, {nom_car2} {v2:g} -> IA: {devine_nom} | vous: {vrai_nom}")

    print(f"\nScore final : {nb_corrects}/{len(entrees)} de VOS exemples bien appris.")


def essayer_interactif_categories(boutons, seuil_de_base, echelles, nom_car1, nom_car2, categorie_a, categorie_b):
    print(f"\nA vous de tester l'IA avec de nouveaux cas (tapez 'fini' a la place de {nom_car1} pour arreter) :")
    while True:
        v1 = demander_valeur_ou_fin(f"\n{nom_car1} (ou 'fini') : ")
        if v1 is None:
            break
        v2 = demander_nombre(f"{nom_car2} : ")
        entree = np.array([[v1, v2]]) / echelles
        confiance = float(tasser_entre_0_et_1(entree @ boutons + seuil_de_base)[0, 0])
        devine_nom = categorie_b if confiance >= 0.5 else categorie_a
        pourcentage = (confiance if confiance >= 0.5 else 1 - confiance) * 100
        print(f"   -> l'IA pense '{devine_nom}' a {pourcentage:.0f}% de confiance.")


def raconter_la_pensee_nombre(essai, entrees, sorties, devines, nom_car, nom_sortie):
    print(f"\n--- Essai {essai} : ce que l'IA pense de chaque exemple ---")
    for (v,), sortie_reelle, devine in zip(entrees, sorties.flatten(), devines.flatten()):
        ecart = abs(devine - sortie_reelle)
        seuil = max(0.5, abs(sortie_reelle) * 0.05)
        if ecart < seuil:
            commentaire = "Tres proche, elle va juste ajuster tres legerement."
        elif devine > sortie_reelle:
            commentaire = "Elle a devine trop haut, elle va baisser un peu ses boutons."
        else:
            commentaire = "Elle a devine trop bas, elle va augmenter un peu ses boutons."
        print(f"  {nom_car} {v:g} (vous avez dit {nom_sortie}: {sortie_reelle:g}) "
              f"-> l'IA devine {devine:.2f}. -> {commentaire}")


def entrainer_nombre(entrees, sorties, nom_car, nom_sortie,
                      vitesse_apprentissage, nb_essais, details, afficher_tous_les, pas_a_pas_actif):
    echelle_car = calculer_echelles(entrees)[0]
    echelle_sortie = float(max(np.abs(sorties).max(), 1) * 1.2)

    entrees_normalisees = entrees / echelle_car
    sorties_normalisees = sorties / echelle_sortie

    np.random.seed(42)
    multiplicateur = float(np.random.uniform(-1, 1))
    valeur_de_base = float(np.random.uniform(-1, 1))

    historique_erreur = []

    print(f"\nDebut de l'entrainement sur VOS {len(entrees)} exemples : {nb_essais} essais, "
          f"vitesse d'apprentissage {vitesse_apprentissage}\n")

    for essai in range(1, nb_essais + 1):
        devines_normalisees = entrees_normalisees.flatten() * multiplicateur + valeur_de_base
        erreur = sorties_normalisees.flatten() - devines_normalisees
        erreur_moyenne = float(np.mean(np.abs(erreur)) * echelle_sortie)
        historique_erreur.append(erreur_moyenne)

        correction_multiplicateur = np.mean(erreur * entrees_normalisees.flatten())
        correction_valeur_de_base = np.mean(erreur)

        multiplicateur += vitesse_apprentissage * correction_multiplicateur
        valeur_de_base += vitesse_apprentissage * correction_valeur_de_base

        if details:
            devines = (devines_normalisees * echelle_sortie).reshape(-1, 1)
            raconter_la_pensee_nombre(essai, entrees, sorties, devines, nom_car, nom_sortie)
        elif essai == 1 or essai % afficher_tous_les == 0:
            print(f"Essai {essai:>6} | ecart moyen : {erreur_moyenne:.2f}")

        pas_a_pas(pas_a_pas_actif)

    return multiplicateur, valeur_de_base, echelle_car, echelle_sortie, historique_erreur


def tester_nombre(entrees, sorties, multiplicateur, valeur_de_base, echelle_car, echelle_sortie, nom_car, nom_sortie):
    print("\nCe que l'IA a retenu de vos exemples :\n")
    for (v,), sortie_reelle in zip(entrees, sorties.flatten()):
        devine = (v / echelle_car * multiplicateur + valeur_de_base) * echelle_sortie
        print(f"   {nom_car} {v:g} -> IA devine {nom_sortie} : {devine:.2f} | vous aviez dit : {sortie_reelle:g}")


def essayer_interactif_nombre(multiplicateur, valeur_de_base, echelle_car, echelle_sortie, nom_car, nom_sortie):
    print(f"\nA vous de tester l'IA avec de nouveaux cas (tapez 'fini' pour arreter) :")
    while True:
        v = demander_valeur_ou_fin(f"\n{nom_car} (ou 'fini') : ")
        if v is None:
            break
        devine = (v / echelle_car * multiplicateur + valeur_de_base) * echelle_sortie
        print(f"   -> l'IA devine {nom_sortie} : {devine:.2f}")


def entrainer(vitesse_apprentissage=0.1, nb_essais=4000, details=False,
              afficher_tous_les=400, pas_a_pas_actif=False):
    expliquer_le_principe()
    type_lecon = choisir_type_lecon()

    if type_lecon == "categories":
        nom_car1, nom_car2, categorie_a, categorie_b, entrees_brutes, sorties_brutes = collecter_exemples_categories()
        entrees = np.array(entrees_brutes, dtype=float)
        sorties = np.array(sorties_brutes, dtype=float).reshape(-1, 1)

        boutons, seuil_de_base, echelles, historique_erreur = entrainer_categories(
            entrees, sorties, nom_car1, nom_car2, categorie_a, categorie_b,
            vitesse_apprentissage, nb_essais, details, afficher_tous_les, pas_a_pas_actif)

        tester_categories(entrees, sorties, boutons, seuil_de_base, echelles, nom_car1, nom_car2, categorie_a, categorie_b)

        sauvegarder_checkpoint("module10_special_categories.json", {
            "type_lecon": "categories",
            "noms_caracteristiques": [nom_car1, nom_car2],
            "categories": [categorie_a, categorie_b],
            "boutons": boutons.tolist(),
            "seuil_de_base": seuil_de_base,
            "echelles": echelles.tolist(),
            "historique_erreur": historique_erreur,
        })

        essayer_interactif_categories(boutons, seuil_de_base, echelles, nom_car1, nom_car2, categorie_a, categorie_b)
        return boutons, seuil_de_base, historique_erreur

    nom_car, nom_sortie, entrees_brutes, sorties_brutes = collecter_exemples_nombre()
    entrees = np.array(entrees_brutes, dtype=float).reshape(-1, 1)
    sorties = np.array(sorties_brutes, dtype=float).reshape(-1, 1)

    multiplicateur, valeur_de_base, echelle_car, echelle_sortie, historique_erreur = entrainer_nombre(
        entrees, sorties, nom_car, nom_sortie, vitesse_apprentissage, nb_essais, details, afficher_tous_les, pas_a_pas_actif)

    tester_nombre(entrees, sorties, multiplicateur, valeur_de_base, echelle_car, echelle_sortie, nom_car, nom_sortie)

    sauvegarder_checkpoint("module10_special_nombre.json", {
        "type_lecon": "nombre",
        "nom_caracteristique": nom_car,
        "nom_sortie": nom_sortie,
        "multiplicateur": multiplicateur,
        "valeur_de_base": valeur_de_base,
        "echelle_caracteristique": echelle_car,
        "echelle_sortie": echelle_sortie,
        "historique_erreur": historique_erreur,
    })

    essayer_interactif_nombre(multiplicateur, valeur_de_base, echelle_car, echelle_sortie, nom_car, nom_sortie)
    return multiplicateur, valeur_de_base, historique_erreur


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Module 10 : vous enseignez quelque chose a l'IA a partir de zero.")
    analyseur.add_argument("--details", action="store_true", help="Raconte la pensee de l'IA a chaque essai.")
    analyseur.add_argument("--essais", type=int, default=2000, help="Nombre d'essais (par defaut 2000).")
    analyseur.add_argument("--vitesse", type=float, default=0.1, help="Vitesse d'apprentissage (par defaut 0.1).")
    analyseur.add_argument("--afficher-tous-les", type=int, default=200, dest="afficher_tous_les")
    analyseur.add_argument("--pas-a-pas", action="store_true", dest="pas_a_pas_actif")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    entrainer(nb_essais=args.essais, vitesse_apprentissage=args.vitesse,
              details=args.details, afficher_tous_les=args.afficher_tous_les,
              pas_a_pas_actif=args.pas_a_pas_actif)
