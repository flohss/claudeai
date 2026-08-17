"""
MODULE 0 — LE COURS : comprendre les bases avant de commencer
==================================================================

Ce module n'entraine aucune IA : c'est un cours, pense pour quelqu'un
qui n'y connait VRAIMENT rien. Il explique, avec des mots simples et
des comparaisons de la vie de tous les jours, tout le vocabulaire et
toutes les idees utilisees par les modules 1 a 11, AVANT de vous y
lancer.

Chaque chapitre est court. Vous avancez a votre rythme (Entree pour
continuer), comme le mode "pas a pas" des autres modules.

Usage :
    python -m modules.module0_cours
    python -m modules.module0_cours --tout-dun-coup
"""

import argparse

# Chaque chapitre : un titre, une liste de paragraphes (deja mis en
# forme, pas de balisage), et eventuellement le numero du module ou
# aller voir l'idee "en vrai". Cette meme structure est reutilisee par
# l'interface web (route /cours) pour ne jamais dupliquer le texte.
CHAPITRES = [
    {
        "titre": "Bienvenue",
        "paragraphes": [
            "Ce cours est fait pour vous si vous n'y connaissez vraiment rien : "
            "pas besoin de maths, pas besoin de savoir programmer.",
            "Son but : vous donner les images mentales et le vocabulaire dont "
            "vous aurez besoin AVANT de lancer les modules 1 a 11, pour que "
            "chaque mot que vous y croiserez vous dise deja quelque chose.",
            "Comment ca marche : des chapitres courts, un a la fois. Appuyez "
            "sur Entree quand vous etes pret a passer au suivant. Vous pouvez "
            "vous arreter et revenir quand vous voulez (python -m modules.module0_cours).",
            "A la fin : un lexique complet, et un ordre conseille pour la suite.",
        ],
        "module_lie": None,
    },
    {
        "titre": "C'est quoi une \"IA\", ici ?",
        "paragraphes": [
            "Oubliez tout de suite l'idee d'une machine qui \"pense\" ou qui "
            "\"comprend\" comme un humain. Dans cette suite, une IA, c'est juste "
            "une formule de calcul (des multiplications, des additions) qui se "
            "regle TOUTE SEULE, petit a petit, en se trompant puis en se corrigeant.",
            "Analogie : reglez une douche. Trop froide -> vous tournez un peu "
            "vers le chaud. Trop chaude -> un peu vers le froid. Vous repetez "
            "jusqu'a la bonne temperature. C'est exactement ce qu'une IA \"qui "
            "apprend\" fait, sauf qu'elle a beaucoup plus de robinets a regler "
            "en meme temps, et qu'elle repete l'operation des milliers de fois.",
            "Rien de magique, donc : juste beaucoup de petits reglages, repetes "
            "beaucoup de fois. Tout le reste de ce cours consiste a detailler "
            "chaque mot de cette phrase.",
        ],
        "module_lie": None,
    },
    {
        "titre": "Le bouton (poids) et le seuil de base (biais)",
        "paragraphes": [
            "Un \"bouton\" est un simple nombre que l'IA regle elle-meme. Chaque "
            "donnee qu'on lui donne (un poids, une taille, un pixel...) est "
            "multipliee par un bouton avant d'etre additionnee aux autres.",
            "Un GRAND bouton positif veut dire : cette donnee compte beaucoup, "
            "et pousse la reponse vers \"oui\". Un grand bouton NEGATIF pousse "
            "vers \"non\". Un bouton proche de zero veut dire : cette donnee "
            "n'a presque aucune importance pour la decision.",
            "Le \"seuil de base\" (le terme technique est le biais) est un "
            "reglage a part, qui ne depend d'AUCUNE donnee : un peu comme un "
            "avis de depart, avant meme d'avoir regarde quoi que ce soit.",
            "Analogie : un jury qui note un plat. Chaque jure (un bouton) donne "
            "plus ou moins d'importance a un critere (trop sale ? trop sucre ?). "
            "Et il y a une note de depart, avant meme d'avoir goute : certains "
            "jures partent plutot indulgents, d'autres plutot severes.",
        ],
        "module_lie": None,
    },
    {
        "titre": "Tasser entre 0 et 1 : comment l'IA \"decide\"",
        "paragraphes": [
            "Une fois toutes les donnees multipliees par leurs boutons puis "
            "additionnees, on obtient un nombre libre : il pourrait valoir "
            "-50, +3, +1000... Pas tres pratique pour dire \"oui\" ou \"non\".",
            "L'astuce : on \"tasse\" ce nombre pour le forcer entre 0 et 1, avec "
            "une formule mathematique. Le resultat se lit alors comme un "
            "pourcentage de confiance : proche de 0 = \"plutot non\", proche de "
            "1 = \"plutot oui\".",
            "Analogie : une jauge d'essence qui ne peut jamais depasser \"plein\" "
            "ni descendre sous \"vide\", meme si vous continuez de forcer sur le "
            "bouton. Peu importe a quel point le calcul de depart est extreme, "
            "la reponse finale reste toujours lisible entre 0% et 100%.",
        ],
        "module_lie": 1,
    },
    {
        "titre": "La couche cachee : le petit etage de \"reflexion\"",
        "paragraphes": [
            "Parfois, un seul calcul (donnees x boutons, additionnees, tassees) "
            "ne suffit PAS a resoudre le probleme, meme en laissant l'IA "
            "s'entrainer indefiniment. Le Module 1 (le OU EXCLUSIF) est "
            "l'exemple parfait de ce cas.",
            "La solution : ajouter un etage intermediaire de petits calculs "
            "AVANT la reponse finale. Chaque \"neurone cache\" de cet etage "
            "regarde toutes les donnees a sa maniere (avec ses propres "
            "boutons), tasse son propre resultat, et c'est la reponse finale "
            "qui regarde ensuite TOUS ces resultats intermediaires.",
            "Analogie : au lieu de decider directement \"il pleut, donc je "
            "prends un parapluie\", on passe par des questions intermediaires "
            "(\"le ciel est-il gris ? y a-t-il du vent ?\"), et c'est la "
            "combinaison de ces reponses intermediaires qui fait la decision "
            "finale.",
            "Dans l'interface web, c'est ce qu'on voit dans le schema \"Ce que "
            "valent ses boutons\" : entrees -> etage cache -> sortie.",
        ],
        "module_lie": 1,
    },
    {
        "titre": "Essai, vitesse d'apprentissage, correction",
        "paragraphes": [
            "Un \"essai\" (le terme technique est epoch) est une tentative "
            "complete : l'IA regarde tous les exemples d'entrainement, calcule "
            "sa reponse pour chacun, compare a la bonne reponse, puis ajuste "
            "ses boutons en consequence. Puis elle recommence, encore et "
            "encore - souvent plusieurs milliers de fois.",
            "La \"correction\" (le terme technique est le gradient), c'est de "
            "combien et dans quel sens on tourne chaque bouton a cet essai, "
            "calcule a partir de l'erreur commise.",
            "La \"vitesse d'apprentissage\" est la taille du pas qu'on autorise "
            "a chaque correction. Trop petite : elle apprend, mais tres, tres "
            "lentement. Trop grande : elle depasse la bonne valeur a chaque "
            "fois, et peut meme partir totalement en vrille (on dit qu'elle "
            "\"diverge\").",
            "Analogie : chercher une station de radio en tournant un bouton. "
            "Petits pas = precis mais long. Grands pas = rapide, mais on peut "
            "sauter par-dessus la bonne frequence sans jamais tomber dessus. "
            "Essayez le mode \"Comparer deux vitesses d'apprentissage\" de "
            "l'interface web pour le voir de vos propres yeux.",
        ],
        "module_lie": 2,
    },
    {
        "titre": "Lire une courbe d'erreur",
        "paragraphes": [
            "A chaque essai, on mesure \"l'erreur moyenne\" : a quel point l'IA "
            "se trompe encore, en moyenne, sur l'ensemble des exemples.",
            "Sur le graphique de l'interface web, l'axe horizontal est le "
            "numero de l'essai, et l'axe vertical est cette erreur.",
            "Une IA qui apprend bien : la courbe descend, puis se stabilise "
            "pres de zero (ou pres du minimum possible pour ce probleme). Une "
            "vitesse d'apprentissage trop grande : la courbe reste haute, "
            "tremble sans arret, ou explose carrement (affiche \"instable\").",
            "C'est le tableau de bord le plus important de chaque page de "
            "suivi : un seul coup d'oeil suffit pour savoir si ca se passe bien.",
        ],
        "module_lie": 2,
    },
    {
        "titre": "Deviner un nombre libre, ou choisir une categorie",
        "paragraphes": [
            "Il y a deux grandes familles de questions qu'on peut poser a une "
            "IA de ce type :",
            "1) Deviner un NOMBRE LIBRE (le prix d'une maison, Module 2). La "
            "reponse finale n'a pas besoin d'etre tassee entre 0 et 1 : elle "
            "peut valoir n'importe quoi.",
            "2) Choisir une CATEGORIE parmi plusieurs (pomme, orange ou "
            "banane, Modules 3 et 8). Chaque categorie possible recoit son "
            "propre pourcentage de confiance, et TOUTES les categories doivent "
            "ensemble totaliser 100% - un peu comme si elles se partageaient "
            "un gateau : plus le score d'une categorie est grand par rapport "
            "aux autres, plus sa part du gateau est grosse.",
            "La facon de \"tasser\" la reponse finale depend donc entierement "
            "du type de question posee.",
        ],
        "module_lie": 3,
    },
    {
        "titre": "Voir avec ses \"yeux\" : les pixels bruts",
        "paragraphes": [
            "Dans les modules 1 a 10, quelqu'un avait deja resume, pour l'IA, "
            "les caracteristiques utiles a regarder (le poids d'un fruit, sa "
            "forme...). C'est un vrai travail de preparation, fait a l'avance.",
            "Le Module 11 change completement ca : l'IA recoit directement une "
            "petite image, pixel par pixel (16 pixels, chacun allume ou "
            "eteint), SANS aide. Chaque pixel devient une entree comme les "
            "autres, avec son propre bouton par forme possible.",
            "C'est un tout petit apercu, tres simplifie, de ce qui se passe "
            "dans une vraie reconnaissance d'image : aucune caracteristique "
            "n'est resumee a l'avance, l'IA doit tout decouvrir depuis les "
            "donnees les plus brutes possibles.",
        ],
        "module_lie": 11,
    },
    {
        "titre": "Supervise, non supervise, par renforcement : la grande carte",
        "paragraphes": [
            "Il existe trois grandes familles tres differentes pour faire "
            "apprendre une IA. Les reperer vous aidera a comprendre "
            "immediatement ce que fait chaque module.",
            "SUPERVISE (Modules 1, 2, 3, 4, 8, 10, 11) : on donne a l'IA des "
            "exemples AVEC la bonne reponse deja fournie. Elle compare sa "
            "reponse a la bonne reponse, et se corrige.",
            "NON SUPERVISE (Module 6) : on ne donne AUCUNE bonne reponse. "
            "L'IA doit decouvrir toute seule une structure cachee dans les "
            "donnees (par exemple, des groupes d'elements qui se ressemblent).",
            "PAR RENFORCEMENT (Modules 5 et 7) : on ne donne pas non plus de "
            "bonne reponse toute faite, mais l'IA recoit une recompense ou "
            "une penalite APRES chaque decision, et apprend petit a petit "
            "quelles decisions rapportent le plus, y compris a long terme.",
            "Analogies : supervise = un professeur qui corrige chaque copie. "
            "Non supervise = trier des chaussettes par paires sans etiquette "
            "de couleur, juste en regardant ce qui se ressemble. Renforcement "
            "= apprendre a faire du velo : personne ne vous donne la formule, "
            "mais vous sentez quand vous tombez (mauvais) et quand vous roulez "
            "(bon), et vous ajustez tout seul.",
        ],
        "module_lie": None,
    },
    {
        "titre": "Le vocabulaire de l'apprentissage par renforcement",
        "paragraphes": [
            "Les Modules 5 (le serpent) et 7 (le rat dans le labyrinthe) "
            "utilisent un vocabulaire particulier, a connaitre avant d'y aller :",
            "SITUATION : ce que l'IA observe a cet instant precis (les dangers "
            "autour du serpent, la position du rat sur la grille...).",
            "MEMOIRE DES CHOIX (le terme technique est la table de valeurs, ou "
            "Q-table) : pour chaque situation deja rencontree, une note pour "
            "chacune des actions possibles. Plus la note est haute, plus "
            "l'action a l'air payante depuis cette situation.",
            "CURIOSITE : la chance qu'elle tente un mouvement AU HASARD plutot "
            "que celui qu'elle croit etre le meilleur pour l'instant - "
            "indispensable pour decouvrir de nouvelles strategies, pas "
            "seulement repeter ce qu'elle connait deja. Elle est tres curieuse "
            "au debut, et de moins en moins avec l'experience.",
            "PATIENCE : a quel point elle valorise une recompense qui arrive "
            "PLUS TARD, pas seulement le tout prochain coup. Une IA impatiente "
            "fonce sur la premiere petite recompense trouvee ; une IA "
            "patiente peut sacrifier un petit gain immediat pour un plus gros "
            "gain futur.",
            "PARTIE : une tentative complete, du debut jusqu'a la fin (la mort "
            "du serpent, ou le fromage trouve par le rat).",
        ],
        "module_lie": 5,
    },
    {
        "titre": "Le regroupement sans etiquettes",
        "paragraphes": [
            "Rappel du Module 6 : aucune bonne reponse n'est fournie. L'IA "
            "doit decouvrir toute seule que certains elements se ressemblent, "
            "et les ranger en groupes.",
            "La methode, en deux etapes repetees a chaque essai : 1) chaque "
            "element rejoint le GROUPE dont le CENTRE est le plus proche ; "
            "2) chaque centre se deplace ensuite au milieu de tous les "
            "elements qui viennent de le rejoindre.",
            "Au bout de quelques essais, les centres arretent de bouger : les "
            "groupes sont stables. Notez qu'il n'y a ici aucune \"vitesse "
            "d'apprentissage\" : chaque centre saute directement a la bonne "
            "position, il n'y va pas doucement comme les autres modules.",
        ],
        "module_lie": 6,
    },
    {
        "titre": "L'algorithme genetique : evoluer au lieu de corriger",
        "paragraphes": [
            "Le Module 9 change completement de methode : il n'y a plus AUCUN "
            "bouton, et donc aucune correction du tout.",
            "A la place, une POPULATION de nombreuses solutions differentes "
            "evolue, generation apres generation, un peu comme la selection "
            "naturelle :",
            "SELECTION : seuls les meilleurs individus de la generation "
            "survivent et se reproduisent. CROISEMENT : chaque enfant herite "
            "d'un melange des deux parents. MUTATION : avec une petite chance, "
            "un changement au hasard s'ajoute - c'est ce qui permet de "
            "decouvrir des solutions qu'aucun parent n'avait. ELITE : le tout "
            "meilleur individu passe toujours tel quel a la generation "
            "suivante, pour ne jamais perdre le meilleur qu'on ait trouve.",
            "Dans ce module, la population apprend a deviner un mot secret, "
            "lettre par lettre, sans qu'aucun individu ne sache jamais "
            "quelles lettres sont justes - seule la selection des meilleurs "
            "scores fait progresser l'ensemble.",
        ],
        "module_lie": 9,
    },
    {
        "titre": "C'est vous le professeur",
        "paragraphes": [
            "Le Module 10 est different de tous les autres : rien n'est "
            "prepare a l'avance, c'est VOUS qui tapez les exemples, un par un.",
            "Il montre tres concretement une idee importante : l'IA n'a "
            "AUCUNE connaissance innee. Elle n'apprend QUE ce qu'on lui "
            "montre, ni plus, ni moins - avec toutes les qualites et tous les "
            "defauts que ca implique.",
            "C'est le meilleur endroit pour tester votre intuition : donnez-"
            "lui volontairement des exemples biaises ou contradictoires, et "
            "observez attentivement ce qu'elle \"croit\" ensuite.",
        ],
        "module_lie": 10,
    },
    {
        "titre": "Recapitulatif et par ou commencer",
        "paragraphes": [
            "Voici tout le vocabulaire simple utilise dans cette suite, avec "
            "son terme technique habituel entre parentheses :",
            "bouton (poids) - essai (epoch) - vitesse d'apprentissage "
            "(learning rate) - correction (gradient) - tasser entre 0 et 1 "
            "(sigmoide) - reflexion (activation de la couche cachee) - "
            "fenetre (fenetre de contexte) - situation (etat) - memoire des "
            "choix (table de valeurs / Q-table) - curiosite (taux "
            "d'exploration / epsilon) - patience (facteur d'actualisation / "
            "gamma) - partie (episode) - groupe (cluster) - centre du groupe "
            "(centroide) - individu (candidat) - generation (iteration de "
            "l'evolution) - selection, croisement, mutation (deja des mots "
            "francais) - elite (elitisme).",
            "Ordre conseille pour la suite, du plus simple au plus different : "
            "Module 1 (la couche cachee) -> Module 2 (deviner un nombre) -> "
            "Module 3 (choisir une categorie) -> Module 4 (une suite) -> "
            "Module 8 (plusieurs categories) -> Module 11 (des pixels bruts) "
            "-> Module 6 (non supervise) -> Module 5 puis Module 7 "
            "(renforcement) -> Module 9 (genetique) -> Module 10 (vous etes "
            "le professeur).",
            "Un dernier conseil : le mode --details (ou pas-a-pas) est "
            "disponible partout pour ralentir et tout regarder, calcul par "
            "calcul, exactement comme dans ce cours. Vous etes pret. Bon "
            "apprentissage !",
        ],
        "module_lie": None,
    },
]


def afficher_chapitre(numero, chapitre, total):
    print("=" * 70)
    print(f"CHAPITRE {numero}/{total} - {chapitre['titre']}")
    print("=" * 70)
    print()
    for paragraphe in chapitre["paragraphes"]:
        print(paragraphe)
        print()
    if chapitre.get("module_lie") is not None:
        print(f"   -> Pour le voir en pratique : Module {chapitre['module_lie']}")
        print()


def donner_cours(pas_a_pas_actif=True):
    total = len(CHAPITRES)
    for numero, chapitre in enumerate(CHAPITRES, start=1):
        afficher_chapitre(numero, chapitre, total)
        if pas_a_pas_actif and numero < total:
            input("   [Appuyez sur Entree pour lire le chapitre suivant...]\n")

    print("Fin du cours ! Retournez au menu pour choisir un module.\n")


def construire_analyseur():
    analyseur = argparse.ArgumentParser(
        description="Module 0 : le cours qui explique toutes les notions utilisees par la suite.")
    analyseur.add_argument("--tout-dun-coup", action="store_true", dest="tout_dun_coup",
                            help="Affiche tous les chapitres sans pause (pratique pour lire ou imprimer d'un coup).")
    return analyseur


if __name__ == "__main__":
    args = construire_analyseur().parse_args()
    donner_cours(pas_a_pas_actif=not args.tout_dun_coup)
