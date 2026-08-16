"""
INTERFACE WEB — voir l'IA reflechir dans le navigateur
=========================================================

Petite application web locale (Flask) qui permet de choisir les
parametres d'un module, de lancer son entrainement, et de le suivre EN
DIRECT dans le navigateur : la courbe d'erreur qui descend, le schema
des boutons qui bougent, et le fil de pensee de l'IA (les memes
phrases que le mode --details du terminal). On peut aussi arreter un
entrainement en cours, ou comparer deux vitesses d'apprentissage cote
a cote sur le meme module.

Elle ne refait AUCUN calcul elle-meme : elle appelle exactement les
memes fonctions entrainer() que la ligne de commande, avec juste des
rappels (callbacks) qui poussent chaque essai vers le navigateur au
fur et a mesure, via un flux "Server-Sent Events".

Le module 10 (SPECIAL) n'est pas encore disponible ici, car il vous
demande de taper vos exemples un par un : pour l'instant, utilisez-le
en ligne de commande (python -m modules.module10_special).

Usage :
    pip install -r requirements-web.txt
    python -m webapp.app
Puis ouvrez http://localhost:5000 dans votre navigateur.
"""

import json
import math
import queue
import sys
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, Response, abort, redirect, render_template, request, url_for

# Permet de lancer ce fichier de plusieurs facons (python -m webapp.app,
# ou python webapp/app.py) en trouvant toujours le package "modules" a
# la racine du projet.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules import module1_xor_simple as module1  # noqa: E402
from modules import module2_prix as module2  # noqa: E402
from modules import module3_fruits as module3  # noqa: E402
from modules import module4_sequence as module4  # noqa: E402
from modules import module5_serpent as module5  # noqa: E402
from modules import module6_regroupement as module6  # noqa: E402
from modules import module7_labyrinthe as module7  # noqa: E402
from modules import module8_fruits_multiples as module8  # noqa: E402
from modules import module9_genetique as module9  # noqa: E402

app = Flask(__name__)


class EntrainementInterrompu(Exception):
    """Levee depuis un rappel (sur_essai/sur_partie/sur_mouvement) quand
    l'utilisateur a clique sur "Arreter" dans le navigateur."""


# session_id -> {"file": queue.Queue, "arret": threading.Event, "num": int,
#                "titre": str, "parametres": dict}
SESSIONS = {}

MODULES = {
    1: {
        "titre": "Le OU EXCLUSIF (XOR)",
        "description": "Une IA qui apprend une regle logique a partir de 4 exemples.",
        "champs": [
            {"nom": "nb_essais", "label": "Nombre d'essais", "defaut": 10000, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.5, "pas": "0.01"},
        ],
        "reseau": {"entrees": ["entree A", "entree B"], "sortie": "OU EXCLUSIF"},
        # Grille de suivi : un carre par exemple, colore selon si l'IA le
        # reussit actuellement, pour voir la progression exemple par exemple.
        "grille_exemples": ["0 et 0", "0 et 1", "1 et 0", "1 et 1"],
    },
    2: {
        "titre": "Deviner un prix",
        "description": "Une IA qui apprend a estimer le prix d'une maison a partir de sa taille.",
        "champs": [
            {"nom": "nb_essais", "label": "Nombre d'essais", "defaut": 5000, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.01, "pas": "0.001"},
        ],
        "reseau": {"entrees": ["taille"], "sortie": "prix"},
    },
    3: {
        "titre": "Reconnaitre un fruit",
        "description": "Une IA qui apprend a distinguer une pomme d'une orange (poids + couleur).",
        "champs": [
            {"nom": "nb_essais", "label": "Nombre d'essais", "defaut": 3000, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.1, "pas": "0.01"},
        ],
        "reseau": {"entrees": ["poids", "rougeur"], "sortie": "categorie"},
        "grille_exemples": [f"Fruit {i + 1}" for i in range(10)],
    },
    4: {
        "titre": "Deviner la suite",
        "description": "Une IA qui regarde les 3 derniers nombres d'une suite pour deviner le suivant.",
        "champs": [
            {"nom": "nb_essais", "label": "Nombre d'essais", "defaut": 9000, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.05, "pas": "0.01"},
            {"nom": "famille", "label": "Famille de suite", "type": "select",
             "options": ["addition", "multiplication", "fibonacci"], "defaut": "addition"},
        ],
        "reseau": {"entrees": ["t-3", "t-2", "t-1"], "sortie": "suivant"},
    },
    5: {
        "titre": "Le serpent qui apprend tout seul",
        "description": "Une IA qui apprend a jouer par essai-erreur, sans bonnes reponses fournies a l'avance.",
        "champs": [
            {"nom": "nb_parties", "label": "Nombre de parties", "defaut": 400, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.1, "pas": "0.01"},
            {"nom": "patience", "label": "Patience (importance du futur)", "defaut": 0.9, "pas": "0.01"},
        ],
        # Pas de "reseau" : le module 5 n'a pas de boutons, mais une
        # memoire des choix (table), qui ne se dessine pas comme un reseau.
    },
    6: {
        "titre": "Regrouper sans étiquettes",
        "description": "Une IA qui range des animaux en groupes a partir de leur taille et leur poids, sans jamais qu'on lui dise leur espece.",
        "champs": [
            {"nom": "nb_essais", "label": "Nombre d'essais maximum", "defaut": 10, "pas": "1"},
            {"nom": "nb_groupes", "label": "Nombre de groupes a chercher", "defaut": 3, "pas": "1"},
        ],
        # Pas de "reseau" (pas de boutons) ni de "vitesse_apprentissage"
        # (elle recalcule directement le milieu de chaque groupe, elle
        # n'y va pas doucement) : affichage en nuage de points a la place.
        "nuage": True,
    },
    7: {
        "titre": "Le rat dans le labyrinthe",
        "description": "Une IA qui apprend par essai-erreur a trouver le fromage dans un labyrinthe fixe.",
        "champs": [
            {"nom": "nb_parties", "label": "Nombre de parties", "defaut": 300, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.1, "pas": "0.01"},
            {"nom": "patience", "label": "Patience (importance du futur)", "defaut": 0.9, "pas": "0.01"},
        ],
        # Pas de "reseau" : comme le module 5, il a une memoire des choix
        # (table), pas des boutons.
    },
    8: {
        "titre": "Reconnaitre PLUSIEURS fruits",
        "description": "L'extension du module 3 : choisir entre Pomme, Orange ou Banane, pas seulement deux categories.",
        "champs": [
            {"nom": "nb_essais", "label": "Nombre d'essais", "defaut": 2000, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.5, "pas": "0.01"},
        ],
        "reseau": {"entrees": ["poids", "forme"], "sortie": ["Pomme", "Orange", "Banane"]},
        "grille_exemples": [f"Fruit {i + 1}" for i in range(24)],
    },
    9: {
        "titre": "Algorithme génétique",
        "description": "Pas de correction : une population de mots evolue par selection, croisement et mutation pour deviner un mot secret.",
        "champs": [
            {"nom": "mot_cible", "label": "Mot secret a deviner (lettres A-Z)", "type": "texte", "defaut": "ALGORITHME"},
            {"nom": "nb_generations", "label": "Nombre de generations maximum", "defaut": 150, "pas": "1"},
            {"nom": "taille_population", "label": "Taille de la population", "defaut": 40, "pas": "1"},
            {"nom": "nb_survivants", "label": "Nombre de survivants par generation", "defaut": 10, "pas": "1"},
            {"nom": "taux_mutation", "label": "Taux de mutation (0 a 1)", "defaut": 0.05, "pas": "0.01"},
        ],
        # Pas de "reseau" (aucun bouton, aucune vitesse d'apprentissage) :
        # affichage du mot qui evolue, lettre par lettre, a la place.
        "evolution": True,
    },
}

# Au dela de ce nombre d'essais/parties, on n'envoie pas un evenement a
# CHAQUE essai (ca inonderait le navigateur pour rien) : on en saute
# certains pour garder environ ce nombre de points sur la courbe.
NB_POINTS_CIBLE = 250


def nettoyer_pour_json(valeur):
    """Remplace les NaN/infinis (numeriquement valides en Python, mais
    invalides en JSON strict) par None, pour qu'une vitesse d'apprentissage
    trop grande qui fait "exploser" les boutons ne casse jamais le flux
    envoye au navigateur."""
    if isinstance(valeur, float):
        return valeur if math.isfinite(valeur) else None
    if isinstance(valeur, list):
        return [nettoyer_pour_json(v) for v in valeur]
    if isinstance(valeur, dict):
        return {cle: nettoyer_pour_json(v) for cle, v in valeur.items()}
    return valeur


def convertir_valeur(champ, valeur_brute):
    if champ.get("type") == "select":
        return valeur_brute
    if champ.get("type") == "texte":
        valeur = str(valeur_brute).strip().upper()
        return valeur if valeur.isalpha() else champ["defaut"]
    if champ["nom"] in ("nb_essais", "nb_parties", "nb_groupes",
                         "nb_generations", "taille_population", "nb_survivants"):
        return int(float(valeur_brute))
    return float(valeur_brute)


def lire_parametres(num, formulaire):
    parametres = {}
    for champ in MODULES[num]["champs"]:
        valeur_brute = formulaire.get(champ["nom"], champ["defaut"])
        parametres[champ["nom"]] = convertir_valeur(champ, valeur_brute)
    return parametres


def lire_parametres_comparaison(num, formulaire):
    """Comme lire_parametres, mais separe la vitesse d'apprentissage en
    deux valeurs (vitesse_a / vitesse_b) : tout le reste est partage,
    pour isoler son effet."""
    partages = {}
    for champ in MODULES[num]["champs"]:
        if champ["nom"] == "vitesse_apprentissage":
            continue
        valeur_brute = formulaire.get(champ["nom"], champ["defaut"])
        partages[champ["nom"]] = convertir_valeur(champ, valeur_brute)

    champ_vitesse = next(c for c in MODULES[num]["champs"] if c["nom"] == "vitesse_apprentissage")
    vitesse_a = float(formulaire.get("vitesse_a", champ_vitesse["defaut"]))
    vitesse_b = float(formulaire.get("vitesse_b", champ_vitesse["defaut"]))

    return dict(partages, vitesse_apprentissage=vitesse_a), dict(partages, vitesse_apprentissage=vitesse_b)


def lancer_entrainement(num, parametres):
    session_id = uuid.uuid4().hex
    file_evenements = queue.Queue()
    arret_event = threading.Event()
    SESSIONS[session_id] = {
        "file": file_evenements,
        "arret": arret_event,
        "num": num,
        "titre": MODULES[num]["titre"],
        "parametres": parametres,
    }

    nb_total = parametres.get("nb_essais") or parametres.get("nb_parties") or 1
    intervalle = max(1, nb_total // NB_POINTS_CIBLE)

    # Les calculs eux-memes sont quasi instantanes (numpy sur de petits
    # tableaux) : sans petite pause ici, tous les evenements arriveraient
    # d'un coup et la page ne "verrait" rien defiler. Cette pause ne
    # ralentit que l'affichage, jamais l'entrainement lui-meme.
    def sur_essai(info):
        if arret_event.is_set():
            raise EntrainementInterrompu()
        # Le module 6 (regroupement) s'arrete souvent bien avant nb_essais
        # (des que les groupes ne bougent plus) : l'intervalle calcule sur
        # le nb_essais demande le sauterait alors completement. On envoie
        # donc toujours les tout premiers essais, quoi qu'il arrive.
        if (info["essai"] <= NB_POINTS_CIBLE or info["essai"] % intervalle == 0
                or info["essai"] == info["nb_essais"]):
            file_evenements.put({"type": "essai", **info})
            time.sleep(0.03)

    def sur_partie(info):
        if arret_event.is_set():
            raise EntrainementInterrompu()
        file_evenements.put({"type": "partie", **info})
        time.sleep(0.02)

    def sur_mouvement(info):
        if arret_event.is_set():
            raise EntrainementInterrompu()
        file_evenements.put({"type": "mouvement", **info})

    def sur_generation(info):
        if arret_event.is_set():
            raise EntrainementInterrompu()
        file_evenements.put({"type": "generation", **info})
        time.sleep(0.03)

    def travail():
        try:
            if num == 1:
                module1.entrainer(nb_essais=parametres["nb_essais"],
                                   vitesse_apprentissage=parametres["vitesse_apprentissage"],
                                   sur_essai=sur_essai)
            elif num == 2:
                module2.entrainer(nb_essais=parametres["nb_essais"],
                                   vitesse_apprentissage=parametres["vitesse_apprentissage"],
                                   sur_essai=sur_essai)
            elif num == 3:
                module3.entrainer(nb_essais=parametres["nb_essais"],
                                   vitesse_apprentissage=parametres["vitesse_apprentissage"],
                                   sur_essai=sur_essai)
            elif num == 4:
                module4.entrainer(nb_essais=parametres["nb_essais"],
                                   vitesse_apprentissage=parametres["vitesse_apprentissage"],
                                   famille=parametres["famille"], sur_essai=sur_essai)
            elif num == 5:
                import numpy as np
                table_des_choix, _ = module5.entrainer(
                    nb_parties=parametres["nb_parties"],
                    vitesse_apprentissage=parametres["vitesse_apprentissage"],
                    patience=parametres["patience"],
                    sur_partie=sur_partie, jouer_demo_finale=False)
                file_evenements.put({"type": "fin_entrainement"})
                rng_demo = np.random.default_rng()
                module5.jouer_une_partie_demo(table_des_choix, rng_demo, vitesse_affichage=0.2,
                                               sur_mouvement=sur_mouvement)
            elif num == 6:
                module6.entrainer(nb_essais=parametres["nb_essais"],
                                   nb_groupes=parametres["nb_groupes"],
                                   sur_essai=sur_essai)
            elif num == 7:
                table_des_choix, _ = module7.entrainer(
                    nb_parties=parametres["nb_parties"],
                    vitesse_apprentissage=parametres["vitesse_apprentissage"],
                    patience=parametres["patience"],
                    sur_partie=sur_partie, jouer_demo_finale=False)
                file_evenements.put({"type": "fin_entrainement"})
                module7.jouer_une_partie_demo(table_des_choix, vitesse_affichage=0.3,
                                               sur_mouvement=sur_mouvement)
            elif num == 8:
                module8.entrainer(nb_essais=parametres["nb_essais"],
                                   vitesse_apprentissage=parametres["vitesse_apprentissage"],
                                   sur_essai=sur_essai)
            elif num == 9:
                module9.entrainer(nb_generations=parametres["nb_generations"],
                                   taille_population=parametres["taille_population"],
                                   nb_survivants=parametres["nb_survivants"],
                                   taux_mutation=parametres["taux_mutation"],
                                   mot_cible=parametres["mot_cible"],
                                   sur_generation=sur_generation)
            file_evenements.put({"type": "fin"})
        except EntrainementInterrompu:
            file_evenements.put({"type": "arrete"})
        except Exception as exc:  # pylint: disable=broad-except
            file_evenements.put({"type": "erreur", "message": str(exc)})

    threading.Thread(target=travail, daemon=True).start()
    return session_id


@app.route("/")
def accueil():
    return render_template("accueil.html", modules=MODULES)


@app.route("/module/<int:num>")
def formulaire(num):
    if num not in MODULES:
        abort(404)
    return render_template("formulaire.html", num=num, m=MODULES[num])


@app.route("/lancer/<int:num>", methods=["POST"])
def lancer(num):
    if num not in MODULES:
        abort(404)
    parametres = lire_parametres(num, request.form)
    session_id = lancer_entrainement(num, parametres)
    return redirect(url_for("suivi", session_id=session_id))


@app.route("/suivi/<session_id>")
def suivi(session_id):
    session = SESSIONS.get(session_id)
    if session is None:
        abort(404)
    config_module = MODULES[session["num"]]
    return render_template("suivi.html", session_id=session_id, num=session["num"],
                            titre=session["titre"], parametres=session["parametres"],
                            reseau=config_module.get("reseau"), nuage=config_module.get("nuage"),
                            evolution=config_module.get("evolution"),
                            grille_exemples=config_module.get("grille_exemples"))


@app.route("/arreter/<session_id>", methods=["POST"])
def arreter(session_id):
    session = SESSIONS.get(session_id)
    if session is not None:
        session["arret"].set()
    return ("", 204)


@app.route("/flux/<session_id>")
def flux(session_id):
    session = SESSIONS.get(session_id)
    if session is None:
        abort(404)

    def generer():
        file_evenements = session["file"]
        while True:
            evenement = file_evenements.get()
            yield f"data: {json.dumps(nettoyer_pour_json(evenement))}\n\n"
            if evenement.get("type") in ("fin", "erreur", "arrete"):
                break
        SESSIONS.pop(session_id, None)

    return Response(generer(), mimetype="text/event-stream")


def champ_vitesse_de(num):
    """Renvoie la description du champ vitesse_apprentissage d'un module,
    ou None s'il n'en a pas (ex: le module 6, qui n'a pas de vitesse)."""
    return next((c for c in MODULES[num]["champs"] if c["nom"] == "vitesse_apprentissage"), None)


@app.route("/comparer/<int:num>")
def comparer_formulaire(num):
    if num not in MODULES:
        abort(404)
    champ_vitesse = champ_vitesse_de(num)
    if champ_vitesse is None:
        abort(404)
    autres_champs = [c for c in MODULES[num]["champs"] if c["nom"] != "vitesse_apprentissage"]
    return render_template("comparer_formulaire.html", num=num, m=MODULES[num],
                            champ_vitesse=champ_vitesse, autres_champs=autres_champs)


@app.route("/comparer/<int:num>/lancer", methods=["POST"])
def comparer_lancer(num):
    if num not in MODULES or champ_vitesse_de(num) is None:
        abort(404)
    params_a, params_b = lire_parametres_comparaison(num, request.form)
    id_a = lancer_entrainement(num, params_a)
    id_b = lancer_entrainement(num, params_b)
    return redirect(url_for("comparer_suivi", num=num, id_a=id_a, id_b=id_b))


@app.route("/comparer-suivi/<int:num>/<id_a>/<id_b>")
def comparer_suivi(num, id_a, id_b):
    session_a = SESSIONS.get(id_a)
    session_b = SESSIONS.get(id_b)
    if session_a is None or session_b is None:
        abort(404)
    reseau = MODULES[num].get("reseau")
    grille_exemples = MODULES[num].get("grille_exemples")
    return render_template("comparaison.html", num=num, titre=MODULES[num]["titre"],
                            id_a=id_a, id_b=id_b,
                            parametres_a=session_a["parametres"], parametres_b=session_b["parametres"],
                            reseau=reseau, grille_exemples=grille_exemples)


if __name__ == "__main__":
    print("Interface graphique disponible sur http://localhost:5000")
    print("(accessible aussi depuis un autre appareil du meme reseau via votre adresse IP)")
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
