# Un réseau de neurones dans la page : ce que mesure le prototype

`proto-reseau.js` entraîne un perceptron multicouche — propagation avant,
rétropropagation et Adam écrits à la main, aucune bibliothèque — sur les motifs
d'un studio, et le compare à une chaîne de Markov d'ordre variable sur les mêmes
motifs mis de côté. À lancer avec `node recherche/proto-reseau.js`.

## Ce qui marche

**Le réseau prédit nettement mieux que Markov**, une fois trois choses en place.
Les chiffres sont des −log P par pas, donc directement comparables : plus bas
vaut mieux.

| Studio | Réseau | Markov d'ordre variable |
| --- | --- | --- |
| Trance | **0,55** | 1,03 |
| 8-bit | **1,49** | 1,89 |

Sans ces trois correctifs, le réseau *perdait* contre Markov sur le 8-bit :

- **Les intervalles en entrée.** Donner explicitement l'écart avec la note
  précédente, plutôt que d'espérer que le réseau le retrouve depuis cent motifs.
- **La décroissance des poids** et **l'arrêt précoce**. Sans frein, la perte sur
  les motifs mis de côté remontait dès la dixième époque pendant que celle
  d'apprentissage continuait de descendre.
- **Les douze transpositions.** Cent motifs deviennent mille deux cents, et le
  réseau cesse de mémoriser des hauteurs absolues.

L'entraînement tient en 21 s pour la trance, 6 s pour le 8-bit, après avoir
stocké les entrées comme listes de cases actives plutôt que comme vecteurs
pleins — elles sont creuses, une trentaine de valeurs sur cent soixante-douze.

## Ce qui ne marche pas

**Un bon prédicteur n'est pas un bon générateur.** Laissé à lui-même, le modèle
écrit une note puis se tait pour le reste du motif.

La raison est mécanique : les trois quarts des pas du corpus sont des silences.
Prédire « silence » suffit donc à obtenir une bonne perte, et une fois le
contexte rempli de silences, le modèle n'en sort plus. C'est un état absorbant.

Un régulateur de densité — imposer le nombre de notes du motif — corrige le
compte mais pas la place : les notes s'entassent en fin de motif, parce que le
régulateur les retient tant qu'il peut puis les lâche toutes d'un coup.

## Ce qu'il faudrait

Échantillonner pas à pas est le mauvais cadre. Il faut **chercher le motif
entier** : recuit simulé ou échantillonnage de Gibbs sur les 32 pas, en notant
chaque motif complet avec le réseau, sous contraintes dures — la gamme, la
densité, l'accord en cours, la chute sur la tonique.

Le réseau ne déciderait plus *si* une note tombe, seulement **quelle proposition
est la plus dans le style**. C'est là qu'il est bon, et les contraintes se
chargent de ce qu'il fait mal.
