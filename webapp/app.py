"""
INTERFACE WEB — voir l'IA reflechir dans le navigateur
=========================================================

Petite application web locale (Flask) qui permet de choisir les
parametres d'un module, de lancer son entrainement, et de le suivre EN
DIRECT dans le navigateur : la courbe d'erreur qui descend, et le fil
de pensee de l'IA (les memes phrases que le mode --details du terminal).

Elle ne refait AUCUN calcul elle-meme : elle appelle exactement les
memes fonctions entrainer() que la ligne de commande, avec juste un
rappel (callback) qui pousse chaque essai vers le navigateur au fur et
a mesure, via un flux "Server-Sent Events".

Le module 6 (SPECIAL) n'est pas encore disponible ici, car il vous
demande de taper vos exemples un par un : pour l'instant, utilisez-le
en ligne de commande (python -m modules.module6_special).

Usage :
    pip install -r requirements-web.txt
    python -m webapp.app
Puis ouvrez http://localhost:5000 dans votre navigateur.
"""

import json
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

app = Flask(__name__)

# session_id -> {"file": queue.Queue, "num": int, "titre": str, "parametres": dict}
SESSIONS = {}

MODULES = {
    1: {
        "titre": "Le OU EXCLUSIF (XOR)",
        "description": "Une IA qui apprend une regle logique a partir de 4 exemples.",
        "champs": [
            {"nom": "nb_essais", "label": "Nombre d'essais", "defaut": 10000, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.5, "pas": "0.01"},
        ],
    },
    2: {
        "titre": "Deviner un prix",
        "description": "Une IA qui apprend a estimer le prix d'une maison a partir de sa taille.",
        "champs": [
            {"nom": "nb_essais", "label": "Nombre d'essais", "defaut": 5000, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.01, "pas": "0.001"},
        ],
    },
    3: {
        "titre": "Reconnaitre un fruit",
        "description": "Une IA qui apprend a distinguer une pomme d'une orange (poids + couleur).",
        "champs": [
            {"nom": "nb_essais", "label": "Nombre d'essais", "defaut": 3000, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.1, "pas": "0.01"},
        ],
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
    },
    5: {
        "titre": "Le serpent qui apprend tout seul",
        "description": "Une IA qui apprend a jouer par essai-erreur, sans bonnes reponses fournies a l'avance.",
        "champs": [
            {"nom": "nb_parties", "label": "Nombre de parties", "defaut": 400, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.1, "pas": "0.01"},
            {"nom": "patience", "label": "Patience (importance du futur)", "defaut": 0.9, "pas": "0.01"},
        ],
    },
}

# Au dela de ce nombre d'essais/parties, on n'envoie pas un evenement a
# CHAQUE essai (ca inonderait le navigateur pour rien) : on en saute
# certains pour garder environ ce nombre de points sur la courbe.
NB_POINTS_CIBLE = 250


def lire_parametres(num, formulaire):
    parametres = {}
    for champ in MODULES[num]["champs"]:
        valeur_brute = formulaire.get(champ["nom"], champ["defaut"])
        if champ.get("type") == "select":
            parametres[champ["nom"]] = valeur_brute
        elif champ["nom"] in ("nb_essais", "nb_parties"):
            parametres[champ["nom"]] = int(float(valeur_brute))
        else:
            parametres[champ["nom"]] = float(valeur_brute)
    return parametres


def lancer_entrainement(num, parametres):
    session_id = uuid.uuid4().hex
    file_evenements = queue.Queue()
    SESSIONS[session_id] = {
        "file": file_evenements,
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
        if info["essai"] % intervalle == 0 or info["essai"] == info["nb_essais"]:
            file_evenements.put({"type": "essai", **info})
            time.sleep(0.03)

    def sur_partie(info):
        file_evenements.put({"type": "partie", **info})
        time.sleep(0.02)

    def sur_mouvement(info):
        file_evenements.put({"type": "mouvement", **info})

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
            file_evenements.put({"type": "fin"})
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
    return render_template("suivi.html", session_id=session_id, num=session["num"],
                            titre=session["titre"], parametres=session["parametres"])


@app.route("/flux/<session_id>")
def flux(session_id):
    session = SESSIONS.get(session_id)
    if session is None:
        abort(404)

    def generer():
        file_evenements = session["file"]
        while True:
            evenement = file_evenements.get()
            yield f"data: {json.dumps(evenement)}\n\n"
            if evenement.get("type") in ("fin", "erreur"):
                break
        SESSIONS.pop(session_id, None)

    return Response(generer(), mimetype="text/event-stream")


if __name__ == "__main__":
    print("Interface graphique disponible sur http://localhost:5000")
    print("(accessible aussi depuis un autre appareil du meme reseau via votre adresse IP)")
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
