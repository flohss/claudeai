"""
OUTILS PARTAGES — utilisés par tous les modules
=================================================

Ce fichier ne contient aucune IA : juste des petites fonctions pratiques
(formatage des nombres, sauvegarde des checkpoints, pause "pas à pas")
réutilisées par les modules 1 à 4 pour éviter de répéter le même code
partout.
"""

import json
import math
import os

DOSSIER_CHECKPOINTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "checkpoints")


def arrondi_sur(valeur):
    """Arrondit un nombre, ou renvoie "instable" s'il est devenu NaN ou
    infini — en general le signe d'une vitesse d'apprentissage beaucoup
    trop grande, qui fait "exploser" les boutons au lieu de les affiner.
    """
    if not math.isfinite(valeur):
        return "instable"
    return round(valeur)


def euros(montant):
    """Formate un montant en euros avec un espace comme séparateur de milliers.

    Exemple : euros(215000) -> "215 000 €"
    """
    if not math.isfinite(montant):
        return "montant instable (vitesse d'apprentissage trop grande)"
    entier = int(round(montant))
    signe = "-" if entier < 0 else ""
    entier = abs(entier)
    texte = str(entier)
    groupes = []
    while texte:
        groupes.insert(0, texte[-3:])
        texte = texte[:-3]
    return f"{signe}{' '.join(groupes)} €"


def sauvegarder_checkpoint(nom_fichier, donnees):
    """Sauvegarde un dictionnaire (boutons appris + historique d'erreur) en JSON.

    Le fichier est écrit dans le dossier checkpoints/ à la racine du projet.
    """
    os.makedirs(DOSSIER_CHECKPOINTS, exist_ok=True)
    chemin = os.path.join(DOSSIER_CHECKPOINTS, nom_fichier)
    with open(chemin, "w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, indent=2, ensure_ascii=False)
    print(f"Checkpoint sauvegarde : {chemin}")
    return chemin


def charger_checkpoint(nom_fichier):
    """Recharge un checkpoint JSON. Renvoie None s'il n'existe pas encore."""
    chemin = os.path.join(DOSSIER_CHECKPOINTS, nom_fichier)
    if not os.path.exists(chemin):
        return None
    with open(chemin, "r", encoding="utf-8") as fichier:
        return json.load(fichier)


def pas_a_pas(actif):
    """Si le mode pas-à-pas est actif, attend que l'utilisateur appuie sur Entrée."""
    if actif:
        input("   [Appuyez sur Entree pour avancer d'un essai...]")


def barre_erreur(valeur, valeur_max, largeur=30):
    """Petite barre ASCII toute simple pour visualiser une erreur qui descend.

    Exemple : barre_erreur(0.25, 1.0) -> "[#######.......................]"
    """
    if valeur_max <= 0:
        proportion = 0.0
    else:
        proportion = max(0.0, min(1.0, valeur / valeur_max))
    nb_pleins = int(round(proportion * largeur))
    return "[" + "#" * nb_pleins + "." * (largeur - nb_pleins) + "]"
