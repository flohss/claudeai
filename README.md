# Mon IA, module par module

Une suite d'outils pédagogiques en ligne de commande pour **apprendre le
fonctionnement d'une IA de A à Z**, en français simple et sans jargon
technique. Chaque module est une petite IA entraînée sous vos yeux, avec
tous ses calculs affichés en toute transparence.

Écrit en numpy pur (pas de PyTorch/TensorFlow) : chaque calcul reste
visible et compréhensible.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

Lancer le menu interactif :

```bash
python menu.py
```

Ou lancer un module directement en ligne de commande :

```bash
python -m modules.module1_xor_simple --details
python -m modules.module2_prix --essais 8000 --vitesse 0.02
python -m modules.module3_fruits --details --afficher-tous-les 200
python -m modules.module4_sequence --details
python -m modules.module5_serpent --details --parties 5
python -m modules.module6_regroupement --details --essais 5
python -m modules.module7_labyrinthe --details --parties 5
python -m modules.module8_fruits_multiples --details --essais 5
python -m modules.module9_special --details
```

Le mode `--details` fait "raconter sa pensée" à l'IA en vraies phrases
françaises, pour chaque exemple, à chaque essai — utile pour vraiment
suivre son raisonnement (pensez à réduire `--essais` dans ce mode, sinon
ça défile très vite).

Chaque fichier de module peut aussi être ouvert et lancé tout seul (par
exemple avec le bouton "Run" de Pydroid3 sur Android) : il détecte
automatiquement s'il est lancé comme un simple script ou comme partie
du package `modules` et s'adapte, sans erreur d'import.

## Interface graphique (navigateur)

En plus de la ligne de commande, une petite interface web locale permet
de choisir les paramètres, lancer l'entraînement, et le suivre EN DIRECT
dans le navigateur : la courbe d'erreur qui descend, un schéma des
boutons qui s'anime (entrées → couche cachée → sortie, coloré selon la
valeur de chaque bouton), un nuage de points pour le module 6 (les
animaux qui changent de couleur de groupe au fil des essais), une
grille animée pour le module 7 (le rat qui explore le labyrinthe), et
le fil de pensée de l'IA qui défile — pour les modules 1 à 8 (le
module 9 reste pour l'instant réservé à la ligne de commande, car il
vous demande de taper vos exemples un par un). Le module 8 (plusieurs
catégories) affiche même un schéma à PLUSIEURS sorties : un nœud par
fruit possible, chacun avec ses propres boutons.

Un bouton "Arrêter" permet d'interrompre un entraînement en cours. Et
un mode comparaison (lien "Comparer deux vitesses d'apprentissage" sur
chaque page de module) lance deux entraînements identiques sauf sur la
vitesse d'apprentissage, affichés côte à côte, pour voir concrètement
pourquoi une vitesse trop grande fait diverger l'IA.

```bash
pip install -r requirements-web.txt
python -m webapp.app
```

Sous Windows, double-cliquez simplement sur `lancer_interface_web.bat` :
il crée l'environnement virtuel si besoin, installe les dépendances, et
ouvre votre navigateur tout seul.

Puis ouvrez `http://localhost:5000` dans votre navigateur (ou l'adresse
IP affichée au démarrage, pour y accéder depuis un autre appareil du
même réseau, par exemple votre téléphone). Elle ne refait aucun calcul
elle-même : elle appelle exactement les mêmes fonctions `entrainer()`
que la ligne de commande, avec juste un rappel qui pousse chaque essai
vers la page au fur et à mesure.

C'est un serveur de développement local, pas destiné à être exposé sur
internet.

## Les modules

| # | Module | Ce que l'IA apprend | Nouveauté pédagogique |
|---|--------|----------------------|------------------------|
| 1 | `module1_xor_simple` | Le OU EXCLUSIF (XOR), à partir de 4 exemples | Une couche cachée (étage de réflexion intermédiaire) |
| 2 | `module2_prix` | Estimer le prix d'une maison à partir de sa taille | Deviner un nombre libre, pas juste 0 ou 1 |
| 3 | `module3_fruits` | Distinguer une pomme d'une orange (poids + couleur) | Choisir entre plusieurs catégories |
| 4 | `module4_sequence` | Deviner le nombre (ou la lettre) suivant d'une suite | La "fenêtre" de contexte, comme dans les IA de texte |
| 5 | `module5_serpent` | Jouer au serpent sans jamais recevoir de bonnes réponses à l'avance | L'apprentissage par renforcement (essai-erreur + récompenses) |
| 6 | `module6_regroupement` | Ranger des animaux en groupes à partir de leur taille et poids, sans jamais connaître leur espèce | L'apprentissage NON supervisé (aucune bonne réponse fournie) |
| 7 | `module7_labyrinthe` | Trouver le fromage dans un labyrinthe fixe, par essai-erreur | Une situation = juste une position sur une grille (pas de dangers à deviner comme le serpent) |
| 8 | `module8_fruits_multiples` | Reconnaître Pomme, Orange ou Banane (extension du module 3 à 3+ catégories) | Partager 100% de confiance entre plusieurs réponses possibles |
| 9 | `module9_special` | Ce que VOUS lui enseignez, en direct (deux catégories, ou un nombre) | C'est vous le professeur, pas un jeu d'exemples préparé à l'avance |

## Vocabulaire (aucun jargon technique)

| Mot simple utilisé ici | Terme technique habituel |
|---|---|
| bouton | poids (weight) |
| essai | epoch |
| vitesse d'apprentissage | learning rate |
| correction | gradient |
| tasser entre 0 et 1 | sigmoïde |
| réflexion | activation de la couche cachée |
| fenêtre | fenêtre de contexte |
| situation | état (module 5) |
| mémoire des choix | table de valeurs / Q-table (module 5) |
| curiosité | taux d'exploration / epsilon (module 5) |
| patience | facteur d'actualisation / gamma (module 5) |
| partie | épisode (module 5) |
| groupe | cluster (module 6) |
| centre du groupe | centroïde (module 6) |
| regrouper | clustering (module 6) |

## Structure du projet

```
menu.py                       -> écran d'accueil, menu interactif
modules/
    utils.py                  -> outils partagés (formatage, checkpoints, pas-à-pas)
    module1_xor_simple.py
    module2_prix.py
    module3_fruits.py
    module4_sequence.py
    module5_serpent.py
    module6_regroupement.py
    module7_labyrinthe.py
    module8_fruits_multiples.py
    module9_special.py
checkpoints/                  -> checkpoints JSON sauvegardés après chaque entrainement
webapp/                       -> interface graphique (Flask), optionnelle
    app.py
    templates/
    static/
requirements.txt               -> dépendance pour la ligne de commande (numpy)
requirements-web.txt           -> dépendance en plus pour l'interface graphique (flask)
lancer_interface_web.bat       -> double-clic Windows pour lancer l'interface graphique
```

Chaque module sauvegarde un checkpoint JSON (`checkpoints/moduleX_*.json`)
avec ses boutons finaux (ou sa mémoire des choix pour les modules 5 et 7,
ses centres de groupes pour le module 6, ou ce que vous lui avez enseigné
pour le module 9) et l'historique de l'erreur (ou des scores/récompenses)
au fil des essais.

## Suite envisagée (à prioriser ensemble)

- Amener le module 9 (SPECIAL) dans l'interface graphique, avec un
  formulaire pour taper les exemples au lieu du terminal
- Un mode "rejouer" pour recharger un checkpoint et reprendre l'entrainement,
  ou revoir le film d'un apprentissage passé
- Comparer plus de deux vitesses à la fois (3-4 côte à côte)
- D'autres modules avant le SPECIAL : reconnaissance d'image simplifiée
  (petite grille de pixels), ou un module sur le sur-apprentissage/
  sous-apprentissage

Déjà fait : le mode "pas à pas" (branché dans le menu), le module 5
(serpent, essai-erreur sans exemples fournis à l'avance), le module 6
(regroupement sans étiquettes, apprentissage non supervisé), le module 7
(le rat dans le labyrinthe, essai-erreur avec une situation = position
sur une grille fixe), le module 8 (plusieurs catégories à la fois,
extension du module 3), le module 9 (c'est vous qui enseignez l'IA à
partir de zéro), l'interface graphique dans le navigateur pour les
modules 1 à 8 (avec un schéma à plusieurs sorties pour le module 8), le
nuage de points animé, le bouton "Arrêter", et le mode comparaison.
