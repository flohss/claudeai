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
```

Le mode `--details` fait "raconter sa pensée" à l'IA en vraies phrases
françaises, pour chaque exemple, à chaque essai — utile pour vraiment
suivre son raisonnement (pensez à réduire `--essais` dans ce mode, sinon
ça défile très vite).

## Les modules

| # | Module | Ce que l'IA apprend | Nouveauté pédagogique |
|---|--------|----------------------|------------------------|
| 1 | `module1_xor_simple` | Le OU EXCLUSIF (XOR), à partir de 4 exemples | Une couche cachée (étage de réflexion intermédiaire) |
| 2 | `module2_prix` | Estimer le prix d'une maison à partir de sa taille | Deviner un nombre libre, pas juste 0 ou 1 |
| 3 | `module3_fruits` | Distinguer une pomme d'une orange (poids + couleur) | Choisir entre plusieurs catégories |
| 4 | `module4_sequence` | Deviner le nombre (ou la lettre) suivant d'une suite | La "fenêtre" de contexte, comme dans les IA de texte |
| 5 | `module5_serpent` | Jouer au serpent sans jamais recevoir de bonnes réponses à l'avance | L'apprentissage par renforcement (essai-erreur + récompenses) |

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
checkpoints/                  -> checkpoints JSON sauvegardés après chaque entrainement
requirements.txt
```

Chaque module sauvegarde un checkpoint JSON (`checkpoints/moduleX_*.json`)
avec ses boutons finaux (ou sa mémoire des choix pour le module 5) et
l'historique de l'erreur (ou des scores) au fil des essais.

## Suite envisagée (à prioriser ensemble)

- Une vraie courbe d'erreur ASCII dans le terminal (plotext / asciichart)
- Un mode "rejouer" pour recharger un checkpoint et reprendre l'entrainement,
  ou revoir le film d'un apprentissage passé
- Un mode "comparer les vitesses" : lancer un module avec 2-3 vitesses
  d'apprentissage différentes côte à côte, pour voir concrètement
  pourquoi une vitesse trop grande fait diverger et une trop petite
  apprend trop lentement

Déjà fait : le mode "pas à pas" (branché dans le menu) et le module 5
(jeu appris par essai-erreur, sans exemples fournis à l'avance).
