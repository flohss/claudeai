"""
ÉCRAN D'ACCUEIL — Mon IA, module par module
==============================================

Ce script rassemble tous les modules d'apprentissage dans un seul endroit.
Lancez-le, choisissez un module, et regardez l'IA apprendre en direct,
avec tous les calculs expliqués en français simple.

Usage :
    python menu.py
"""

import sys

from modules import module1_xor_simple as module1
from modules import module2_prix as module2
from modules import module3_fruits as module3
from modules import module4_sequence as module4


BANNIERE = r"""
============================================================
||                                                        ||
||     M O N   I A   -   A P P R E N T I S S A G E        ||
||         pas a pas, calcul par calcul                   ||
||                                                        ||
============================================================
"""


def afficher_accueil():
    print(BANNIERE)
    print("Voici les modules disponibles. Chacun est une petite IA")
    print("differente, entrainee sous vos yeux, avec tous ses calculs")
    print("expliques en francais simple.\n")
    print("  [1] Le OU EXCLUSIF (XOR)")
    print("      Une IA qui apprend une regle logique a partir de 4 exemples.")
    print("      Premiere IA, la plus simple pour comprendre le principe.\n")
    print("  [2] Deviner un prix")
    print("      Une IA qui apprend a estimer le prix d'une maison")
    print("      a partir de sa taille. Elle devine un NOMBRE, pas juste 0 ou 1.\n")
    print("  [3] Reconnaitre un fruit")
    print("      Une IA qui apprend a distinguer une pomme d'une orange")
    print("      a partir du poids et de la couleur. Premier pas vers le choix")
    print("      entre plusieurs categories.\n")
    print("  [4] Deviner la suite")
    print("      Une IA qui regarde les derniers nombres d'une suite pour")
    print("      deviner le suivant. Introduction a ce qui se passe derriere")
    print("      les IA qui ecrivent du texte.\n")
    print("  [5] Quitter\n")


def demander_details():
    reponse = input("Voulez-vous voir TOUS les calculs a chaque essai ? (o/n, defaut n) : ").strip().lower()
    return reponse == "o"


def pause_avant_retour():
    input("\nAppuyez sur Entree pour revenir a l'ecran d'accueil...")


def lancer_module_1():
    print("\n--- MODULE 1 : Le OU EXCLUSIF (XOR) ---\n")
    details = demander_details()
    module1.entrainer(nb_essais=10000, vitesse_apprentissage=0.5,
                       details=details, afficher_tous_les=1000)
    pause_avant_retour()


def lancer_module_2():
    print("\n--- MODULE 2 : Deviner un prix ---\n")
    details = demander_details()
    module2.entrainer(nb_essais=5000, vitesse_apprentissage=0.01,
                       details=details, afficher_tous_les=1000)
    pause_avant_retour()


def lancer_module_3():
    print("\n--- MODULE 3 : Reconnaitre un fruit ---\n")
    details = demander_details()
    module3.entrainer(nb_essais=3000, vitesse_apprentissage=0.1,
                       details=details, afficher_tous_les=500)
    pause_avant_retour()


def demander_famille():
    print("\nQuelle famille de suite l'IA doit-elle deviner ?")
    print("  [1] addition       (2, 4, 6, 8, ...)")
    print("  [2] multiplication (1, 2, 4, 8, ...)")
    print("  [3] fibonacci      (1, 1, 2, 3, 5, ...)")
    choix = input("Votre choix (1-3, defaut 1) : ").strip()
    return {"2": "multiplication", "3": "fibonacci"}.get(choix, "addition")


def lancer_module_4():
    print("\n--- MODULE 4 : Deviner la suite ---\n")
    famille = demander_famille()
    details = demander_details()
    module4.entrainer(nb_essais=9000, vitesse_apprentissage=0.05,
                       details=details, afficher_tous_les=1000, famille=famille)
    pause_avant_retour()


def boucle_principale():
    while True:
        afficher_accueil()
        choix = input("Votre choix (1-5) : ").strip()

        if choix == "1":
            lancer_module_1()
        elif choix == "2":
            lancer_module_2()
        elif choix == "3":
            lancer_module_3()
        elif choix == "4":
            lancer_module_4()
        elif choix == "5":
            print("\nA bientot !")
            sys.exit(0)
        else:
            print("\nChoix non reconnu, merci de taper un chiffre entre 1 et 5.\n")


if __name__ == "__main__":
    boucle_principale()
