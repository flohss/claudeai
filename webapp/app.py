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

Le module 10 (SPECIAL) est different des autres : vous donnez vos
propres exemples via un formulaire dedie (/special), plutot qu'un
formulaire de parametres standard.

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

from flask import Flask, Response, abort, jsonify, redirect, render_template, request, url_for

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
from modules import module10_special as module10  # noqa: E402
from modules import module11_images as module11  # noqa: E402

app = Flask(__name__)

# session_id -> parametres du modele entraine par le module 10, pour
# pouvoir repondre aux tests interactifs (/special/predire) une fois
# l'entrainement termine.
MODELES_SPECIAL = {}


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
        # (table), pas des boutons. A la place, une petite carte du
        # labyrinthe qui montre ce qu'il a compris case par case.
        "carte_labyrinthe": True,
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
    11: {
        "titre": "Reconnaitre une petite image",
        "description": "Une IA qui regarde directement 16 pixels, sans caracteristiques deja resumees pour elle.",
        "champs": [
            {"nom": "nb_essais", "label": "Nombre d'essais", "defaut": 3000, "pas": "1"},
            {"nom": "vitesse_apprentissage", "label": "Vitesse d'apprentissage", "defaut": 0.5, "pas": "0.01"},
        ],
        # 16 entrees (un pixel chacune) : pas de nom individuel, la grille
        # de reference ci-dessous suffit a montrer ce que l'IA regarde.
        "reseau": {"entrees": [""] * module11.NB_PIXELS, "sortie": module11.NOMS_CATEGORIES},
        "grille_exemples": [f"Image {i + 1}" for i in range(module11.NB_EXEMPLES_PAR_FORME * len(module11.NOMS_CATEGORIES))],
        "formes_legende": {nom: forme.tolist() for nom, forme in module11.FORMES_REFERENCE.items()},
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
            elif num == 11:
                module11.entrainer(nb_essais=parametres["nb_essais"],
                                    vitesse_apprentissage=parametres["vitesse_apprentissage"],
                                    sur_essai=sur_essai)
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
    # Le module 10 (SPECIAL) n'a pas d'entree fixe dans MODULES (ses noms
    # de caracteristiques/categories viennent de VOS reponses au
    # formulaire) : sa configuration d'affichage est stockee directement
    # dans la session plutot que dans MODULES.
    config_module = MODULES.get(session["num"], {})
    return render_template("suivi.html", session_id=session_id, num=session["num"],
                            titre=session["titre"], parametres=session["parametres"],
                            reseau=session.get("reseau", config_module.get("reseau")),
                            nuage=config_module.get("nuage"),
                            evolution=config_module.get("evolution"),
                            grille_exemples=session.get("grille_exemples", config_module.get("grille_exemples")),
                            tester_special=session.get("tester_special"),
                            carte_labyrinthe=config_module.get("carte_labyrinthe"),
                            formes_legende=config_module.get("formes_legende"))


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
                            reseau=reseau, grille_exemples=grille_exemples,
                            carte_labyrinthe=MODULES[num].get("carte_labyrinthe"))


@app.route("/special")
def special_formulaire():
    return render_template("special_formulaire.html", erreurs=None, valeurs={})


@app.route("/special/lancer", methods=["POST"])
def special_lancer():
    type_lecon = request.form.get("type_lecon", "categories")
    try:
        nb_essais = max(1, int(float(request.form.get("nb_essais", 2000))))
    except ValueError:
        nb_essais = 2000
    try:
        vitesse_apprentissage = float(request.form.get("vitesse_apprentissage", 0.1))
    except ValueError:
        vitesse_apprentissage = 0.1
    afficher_tous_les = max(1, nb_essais // 10)

    import numpy as np

    if type_lecon == "categories":
        nom_car1 = (request.form.get("nom_car1") or "caracteristique 1").strip()
        nom_car2 = (request.form.get("nom_car2") or "caracteristique 2").strip()
        categorie_a = (request.form.get("categorie_a") or "A").strip()
        categorie_b = (request.form.get("categorie_b") or "B").strip()

        entrees, sorties, labels = [], [], []
        for v1, v2, cat in zip(request.form.getlist("v1[]"), request.form.getlist("v2[]"),
                                request.form.getlist("categorie[]")):
            try:
                entrees.append([float(v1), float(v2)])
            except ValueError:
                continue
            sorties.append(0.0 if cat == categorie_a else 1.0)
            labels.append(f"{v1} / {v2}")

        if len(entrees) < module10.NB_ESSAIS_MINIMUM_EXEMPLES or len(set(sorties)) < 2:
            erreur = (f"Il faut au moins {module10.NB_ESSAIS_MINIMUM_EXEMPLES} exemples valides, "
                      f"avec les deux categories representees ({len(entrees)} donne(s) pour l'instant).")
            return render_template("special_formulaire.html", erreurs=[erreur], valeurs=request.form), 400

        entrees_np = np.array(entrees, dtype=float)
        sorties_np = np.array(sorties, dtype=float).reshape(-1, 1)

        session_id = uuid.uuid4().hex
        file_evenements = queue.Queue()
        arret_event = threading.Event()
        SESSIONS[session_id] = {
            "file": file_evenements, "arret": arret_event, "num": 10,
            "titre": "SPECIAL : c'est vous le professeur",
            "parametres": {"nb_essais": nb_essais, "vitesse_apprentissage": vitesse_apprentissage,
                           "type_lecon": "categories", "nom_car1": nom_car1, "nom_car2": nom_car2},
            "reseau": {"entrees": [nom_car1, nom_car2], "sortie": f"{categorie_a} / {categorie_b}"},
            "grille_exemples": labels,
            "tester_special": {"type_lecon": "categories", "nom_car1": nom_car1, "nom_car2": nom_car2},
        }

        intervalle = max(1, nb_essais // NB_POINTS_CIBLE)

        def sur_essai(info):
            if arret_event.is_set():
                raise EntrainementInterrompu()
            if (info["essai"] <= NB_POINTS_CIBLE or info["essai"] % intervalle == 0
                    or info["essai"] == nb_essais):
                file_evenements.put({"type": "essai", **info})
                time.sleep(0.03)

        def travail():
            try:
                boutons, seuil_de_base, echelles, _ = module10.entrainer_categories(
                    entrees_np, sorties_np, nom_car1, nom_car2, categorie_a, categorie_b,
                    vitesse_apprentissage, nb_essais, False, afficher_tous_les, False,
                    sur_essai=sur_essai)
                MODELES_SPECIAL[session_id] = {
                    "type_lecon": "categories", "boutons": boutons, "seuil_de_base": seuil_de_base,
                    "echelles": echelles, "categorie_a": categorie_a, "categorie_b": categorie_b,
                }
                file_evenements.put({"type": "fin"})
            except EntrainementInterrompu:
                file_evenements.put({"type": "arrete"})
            except Exception as exc:  # pylint: disable=broad-except
                file_evenements.put({"type": "erreur", "message": str(exc)})

        threading.Thread(target=travail, daemon=True).start()
        return redirect(url_for("suivi", session_id=session_id))

    # type_lecon == "nombre"
    nom_car = (request.form.get("nom_car") or "caracteristique").strip()
    nom_sortie = (request.form.get("nom_sortie") or "resultat").strip()

    entrees, sorties, labels = [], [], []
    for v, cible in zip(request.form.getlist("v[]"), request.form.getlist("cible[]")):
        try:
            entrees.append([float(v)])
            sorties.append(float(cible))
            labels.append(v)
        except ValueError:
            continue

    if len(entrees) < module10.NB_ESSAIS_MINIMUM_EXEMPLES:
        erreur = (f"Il faut au moins {module10.NB_ESSAIS_MINIMUM_EXEMPLES} exemples valides "
                  f"({len(entrees)} donne(s) pour l'instant).")
        return render_template("special_formulaire.html", erreurs=[erreur], valeurs=request.form), 400

    entrees_np = np.array(entrees, dtype=float)
    sorties_np = np.array(sorties, dtype=float).reshape(-1, 1)

    session_id = uuid.uuid4().hex
    file_evenements = queue.Queue()
    arret_event = threading.Event()
    SESSIONS[session_id] = {
        "file": file_evenements, "arret": arret_event, "num": 10,
        "titre": "SPECIAL : c'est vous le professeur",
        "parametres": {"nb_essais": nb_essais, "vitesse_apprentissage": vitesse_apprentissage,
                       "type_lecon": "nombre", "nom_car": nom_car, "nom_sortie": nom_sortie},
        "reseau": {"entrees": [nom_car], "sortie": nom_sortie},
        "grille_exemples": labels,
        "tester_special": {"type_lecon": "nombre", "nom_car": nom_car, "nom_sortie": nom_sortie},
    }

    intervalle = max(1, nb_essais // NB_POINTS_CIBLE)

    def sur_essai(info):
        if arret_event.is_set():
            raise EntrainementInterrompu()
        if (info["essai"] <= NB_POINTS_CIBLE or info["essai"] % intervalle == 0
                or info["essai"] == nb_essais):
            file_evenements.put({"type": "essai", **info})
            time.sleep(0.03)

    def travail():
        try:
            multiplicateur, valeur_de_base, echelle_car, echelle_sortie, _ = module10.entrainer_nombre(
                entrees_np, sorties_np, nom_car, nom_sortie,
                vitesse_apprentissage, nb_essais, False, afficher_tous_les, False,
                sur_essai=sur_essai)
            MODELES_SPECIAL[session_id] = {
                "type_lecon": "nombre", "multiplicateur": multiplicateur, "valeur_de_base": valeur_de_base,
                "echelle_car": echelle_car, "echelle_sortie": echelle_sortie, "nom_sortie": nom_sortie,
            }
            file_evenements.put({"type": "fin"})
        except EntrainementInterrompu:
            file_evenements.put({"type": "arrete"})
        except Exception as exc:  # pylint: disable=broad-except
            file_evenements.put({"type": "erreur", "message": str(exc)})

    threading.Thread(target=travail, daemon=True).start()
    return redirect(url_for("suivi", session_id=session_id))


@app.route("/special/predire/<session_id>", methods=["POST"])
def special_predire(session_id):
    import numpy as np

    modele = MODELES_SPECIAL.get(session_id)
    if modele is None:
        return jsonify({"texte": "Modele introuvable : l'entrainement n'est peut-etre pas encore termine."}), 404

    if modele["type_lecon"] == "categories":
        try:
            v1 = float(request.form.get("v1", ""))
            v2 = float(request.form.get("v2", ""))
        except ValueError:
            return jsonify({"texte": "Merci d'entrer deux nombres valides."}), 400
        devine_nom, pourcentage = module10.predire_categorie(
            v1, v2, modele["boutons"], modele["seuil_de_base"], modele["echelles"],
            modele["categorie_a"], modele["categorie_b"])
        return jsonify({"texte": f"L'IA pense '{devine_nom}' à {pourcentage:.0f}% de confiance."})

    try:
        v = float(request.form.get("v", ""))
    except ValueError:
        return jsonify({"texte": "Merci d'entrer un nombre valide."}), 400
    devine = module10.predire_nombre(v, modele["multiplicateur"], modele["valeur_de_base"],
                                      modele["echelle_car"], modele["echelle_sortie"])
    return jsonify({"texte": f"L'IA devine {modele['nom_sortie']} : {devine:.2f}"})


if __name__ == "__main__":
    print("Interface graphique disponible sur http://localhost:5000")
    print("(accessible aussi depuis un autre appareil du meme reseau via votre adresse IP)")
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
