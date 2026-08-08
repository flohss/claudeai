# Labyrinthe 3D — conception en direct

Un jeu de labyrinthe à la première personne, en 3D, qui **montre d'abord l'ordinateur
réfléchir** : avant de jouer, tu regardes l'algorithme creuser le dédale case par case
sur une grille 2D, avec ses commentaires et ses statistiques. Quand c'est prêt, la vue
bascule en 3D et tu entres dedans.

Tout tient dans une page web : rien à installer, ça marche sur Android, iPhone et
ordinateur.

## Lancer le jeu

Ouvre `labyrinthe3d.html` dans un navigateur. C'est tout.

- **Sur ordinateur** : double-clic sur le fichier.
- **Sur Android / iPhone** : copie `labyrinthe3d.html` **et** `three.min.js` dans le
  même dossier du téléphone, puis ouvre le `.html`. Le moteur 3D est chargé depuis le
  fichier local ; s'il est absent, la page le récupère automatiquement sur Internet.
- **Depuis un serveur** : `npx http-server .` puis ouvre l'adresse affichée.

## Phase 1 — l'ordinateur conçoit le labyrinthe

L'écran de génération affiche en temps réel :

- la grille 2D qui se creuse, case par case ;
- la case en cours (blanche), les cases déjà visitées, la frontière (orange) ;
- un **journal de réflexion** en français (« Impasse, je remonte sur mes pas… ») ;
- les compteurs : cases visitées, murs ouverts, retours en arrière ;
- une **vitesse réglable** : 🐢 Lent, ▶ Normal, ⏩ Rapide, ⚡ Éclair — ou le bouton
  « Terminer tout de suite ».

Puis viennent deux phases bonus, tout aussi visibles :

1. **Inondation** — l'ordinateur mesure la distance de chaque case au départ (dégradé
   de couleur) et place la sortie sur la case la plus éloignée.
2. **Chemin de référence** — il trace le plus court chemin, qui te sert de score à
   battre.

## Phase 2 — le labyrinthe en 3D

Le bouton « Entrer dans le labyrinthe » bascule en vue subjective.

### Commandes

| | Ordinateur | Tactile |
|---|---|---|
| Avancer / reculer / pas de côté | `ZQSD`, `WASD` ou les flèches | joystick, moitié gauche de l'écran |
| Regarder | souris (clic pour capturer le pointeur) | glisser sur la moitié droite |
| Courir | `Maj` | pousser le joystick à fond |
| Carte | `M` ou le bouton 🗺 | bouton 🗺 |
| Pause | `Échap` ou ☰ | ☰ |

Le bouton 🗺 fait défiler trois états : carte masquée → **zone explorée uniquement** →
carte complète. La boussole 🧭 pointe vers la sortie et affiche la distance ; le bouton
🔊 coupe le son.

Le meilleur temps est retenu par navigateur pour chaque combinaison motif + difficulté.

## Réglages

**6 décors**, chacun avec ses textures générées par le code (aucune image à
télécharger), son brouillard, sa lumière et ses particules :
🏛 Ruines antiques · 🌐 Néon cyber · 🌲 Forêt enchantée · 🛰 Station spatiale ·
❄ Cavernes de glace · 🌋 Cœur du volcan.

**5 motifs**, qui sont en réalité 5 algorithmes différents — c'est ce qui rend la phase
de génération intéressante à regarder :

| Motif | Algorithme | Ce que ça donne |
|---|---|---|
| 🧵 Classique | parcours en profondeur | longs couloirs sinueux, beaucoup d'impasses |
| 🌿 Ramifié | Prim aléatoire | croissance depuis une frontière, arbre très ramifié |
| ✨ Éparpillé | Kruskal aléatoire | des îlots colorés apparaissent partout puis fusionnent |
| 🔀 Ouvert | profondeur + tressage | les impasses sont rouvertes : des boucles, plusieurs routes |
| 🏰 Salles | division récursive | on part d'une grande salle vide qu'on cloisonne |

**4 difficultés** : Facile 8×8 · Moyen 12×12 · Difficile 17×17 · Expert 23×23.

## Détails techniques

- [three.js](https://threejs.org) r128 (WebGL). `three.min.js` est fourni pour que le
  jeu fonctionne hors ligne ; sinon la page bascule sur un CDN.
- Les murs sont un seul `InstancedMesh` : un labyrinthe Expert reste fluide sur mobile.
- Les textures (briques, circuits imprimés, mousse, panneaux, glace, lave) sont peintes
  au démarrage dans un `<canvas>`, avec une carte émissive séparée pour les parties qui
  brillent.
- Le labyrinthe est stocké en bitmap `(2n+1)²` — `1` = mur, `0` = passage —, la même
  structure servant à l'affichage 2D, aux collisions et à la construction 3D.
- Les algorithmes sont écrits comme des **générateurs JavaScript** : une itération =
  une étape visible, ce qui permet de régler la vitesse ou de tout terminer d'un coup
  sans dupliquer le code.
- Sons synthétisés à la volée en WebAudio, aucun fichier audio.
