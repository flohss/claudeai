Deux logiciels dans ce dépôt :

- **`labyrinthe3d.html`** — le jeu de labyrinthe 3D à la première personne, décrit ci-dessous.
- **`labo-algorithmes.html`** — un laboratoire pour comprendre les algorithmes qui font
  tourner le jeu, décrit [à la fin](#laboratoire-dalgorithmes-de-graphe).

---

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

L'écran de génération ne montre pas seulement le résultat de chaque décision, mais la
**décision elle-même**. Chaque case se joue en deux temps : d'abord la délibération —
les possibilités envisagées apparaissent en blanc et le journal les énumère —, puis le
choix et son exécution.

Ce qui est affiché en temps réel :

- la grille 2D qui se creuse, case par case ;
- les **cases envisagées** (contour blanc) puis la **case retenue** (pleine) ;
- **le fil de la pile** en profondeur : le trait blanc qui relie la case courante au
  départ, et qui se rétracte à chaque retour en arrière ;
- **la zone en cours de découpe** (cadre cyan) pour la division récursive ;
- un **journal de réflexion** en français, qui explique le raisonnement : « 3 voisines
  vierges : le nord, le sud, l'est », « je tire le sud et je perce le mur », « oui, même
  îlot : je garde le mur, sinon je créerais une boucle » ;
- quatre compteurs, dont un qui suit **la structure propre à l'algorithme** : la pile en
  profondeur, la frontière chez Prim, les îlots restants chez Kruskal, les zones à
  traiter en division récursive ;
- une **vitesse réglable** : 🐢 Lent, ▶ Normal, ⏩ Rapide, ⚡ Éclair — ou le bouton
  « Terminer tout de suite » ;
- une **pause avec avance pas à pas**, pour examiner une décision précise aussi
  longtemps qu'on veut ;
- une **sonorisation du travail en cours** : chaque type d'étape a son timbre —
  creusement, impasse, fusion d'îlots, pose de mur, inondation, tracé du chemin.

Les notes sont calées sur une gamme pentatonique, si bien que n'importe quelle suite
reste consonante, et la cadence est bridée à environ 14 sons par seconde : aux vitesses
rapides, des milliers d'étapes passent par image et seule une poignée est sonorisée.
Les impasses sonnent grave, autour de 100 Hz, et se distinguent nettement du reste. Le
bouton 🔊 en haut du plateau coupe le son ; le réglage est retenu d'une partie à
l'autre.

Puis viennent deux phases bonus, tout aussi visibles :

1. **Inondation** — l'ordinateur mesure la distance de chaque case au départ (dégradé
   de couleur) et place la sortie sur la case la plus éloignée.
2. **Chemin de référence** — il trace le plus court chemin, qui te sert de score à
   battre.

## Graine partageable

Chaque labyrinthe porte un code court du genre `NEON-5D5PGS`, affiché pendant la
conception et sur l'écran de victoire. Il encode le décor, le motif, la difficulté et
la graine du tirage : **le même code redonne exactement le même labyrinthe**, sur
n'importe quel appareil. De quoi lancer quelqu'un sur ton tracé et comparer les temps.

Trois façons de le rejouer :

- colle le code dans le champ « Graine » du menu, puis « Charger » ;
- ouvre l'adresse `labyrinthe3d.html#NEON-5D5PGS`, la graine est chargée toute seule ;
- laisse le champ vide pour un labyrinthe tiré au hasard, comme d'habitude.

## Phase 3 — regarder l'ordinateur résoudre

Depuis la pause ou l'écran de victoire, le bouton **🤖 Voir l'ordinateur résoudre**
rejoue le labyrinthe en 2D avec deux méthodes, l'une après l'autre :

1. **Le parcours en largeur** avance sur tous les fronts à la fois — les vagues
   colorées montrent la progression. Il trouve forcément le plus court chemin, mais
   doit examiner presque tout le labyrinthe pour en être sûr.
2. **La main gauche sur le mur** applique une règle bête : longer le mur de gauche,
   sans carte ni mémoire. Le tracé se colore de plus en plus chaud là où elle repasse.
   Le plus court chemin reste affiché en filigrane bleu pour la comparaison.

Un verdict chiffré conclut. Sur le motif **Ouvert**, qui contient des boucles, la main
gauche tourne parfois indéfiniment : mesuré sur 120 tirages par cas, elle échoue 22 %
du temps en 12×12 et 28 % en 17×17, contre **0 %** sur les motifs sans boucle. C'est la
limite connue de la méthode, et le jeu l'annonce franchement plutôt que de la masquer.

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

Le bouton 💡, en bas à droite, allume au sol le chemin vers la sortie pendant sept
secondes. Un temps obtenu avec au moins un indice n'est pas enregistré comme record.

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
| 🧵 Classique | parcours en profondeur | longs couloirs sinueux, chemin de sortie très long |
| 🌿 Ramifié | Prim aléatoire | croissance depuis une frontière, arbre très ramifié |
| ✨ Éparpillé | Kruskal aléatoire | des îlots colorés apparaissent partout puis fusionnent |
| 🔀 Ouvert | profondeur + tressage | les impasses sont rouvertes : des boucles, plusieurs routes |
| 🏰 Salles | division récursive | on part d'une grande salle vide qu'on cloisonne |

**4 difficultés** : Facile 8×8 · Moyen 12×12 · Difficile 17×17 · Expert 23×23.

### Une invariante à observer

Quel que soit l'algorithme, le compteur « murs ouverts » finit toujours à **cases − 1**
— 143 sur un 12×12. Ce n'est pas un hasard du tirage : un labyrinthe où toute case est
atteignable par un chemin unique est un *arbre couvrant*, et un arbre sur N sommets a
exactement N−1 arêtes. Seul le motif **Ouvert** dépasse ce compte, parce que le tressage
ajoute des passages en trop — et ce sont précisément ces passages qui créent les boucles.

En revanche la longueur du chemin de sortie varie du simple au quadruple : environ 90
cases en Classique contre 23 en Ramifié, à taille et à nombre de murs identiques. Toute
la différence tient à *quel* arbre est tiré parmi les milliards possibles, c'est-à-dire
au biais de l'algorithme.

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
  sans dupliquer le code. Les solveurs suivent le même principe.
- Le tirage passe par un générateur pseudo-aléatoire à graine (mulberry32) plutôt que
  par `Math.random`, ce qui rend chaque labyrinthe reproductible à partir de son code.
  Seules les textures et les particules gardent un hasard libre.
- Le chronomètre est lu sur l'horloge réelle, pas sur le delta d'image : ce dernier est
  plafonné à 50 ms pour protéger les collisions, et s'en servir pour compter le temps
  ferait retarder la montre sur tout appareil qui descend sous 20 images par seconde.
- Sons synthétisés à la volée en WebAudio, aucun fichier audio.

---

# Laboratoire d'algorithmes de graphe

`labo-algorithmes.html` — un second logiciel, sans jeu, pour comprendre les algorithmes
du labyrinthe dans leurs autres usages. Ouvrable hors ligne, aucune dépendance.

Le logiciel est bâti sur une idée simple : un terrain produit un **graphe**, et les
algorithmes sont écrits une seule fois, de façon générique. C'est donc littéralement le
**même code** qui creuse un labyrinthe sur une grille, dessine un réseau de câblage
minimal sur un nuage de points, et segmente une image. Changer de terrain suffit à
révéler un autre usage du même raisonnement.

## La matrice terrain × algorithme

| | Grille | Nuage de points | Image | Plan |
|---|---|---|---|---|
| **Profondeur** | labyrinthe à longs couloirs | arbre d'exploration | | |
| **Prim** | labyrinthe ramifié | réseau de câblage minimal | | |
| **Kruskal** | labyrinthe par îlots | réseau de câblage minimal | segmentation | |
| **Largeur** | plus court chemin | plus court chemin | remplissage par diffusion | |
| **Dijkstra / A\*** | chemin pondéré | chemin pondéré | | |
| **Main au mur** | navigation sans mémoire | | | |
| **Division récursive** | labyrinthe en salles | | | découpage en pièces (BSP) |

Sur une grille aux poids tirés au hasard, l'arbre couvrant minimal **est** un labyrinthe
parfait : c'est le pont entre les deux mondes.

## Quatre modes

**Observer** — un algorithme, pas à pas, avec la délibération visible (les arêtes
envisagées avant le choix), le journal de raisonnement, les compteurs, une
**sonorisation du parcours**, et surtout **la structure de données dessinée en direct** : la pile qui monte et descend, la file qui
défile, le tas dont la racine est toujours le minimum, la forêt union-find dont les
îlots fusionnent. C'est elle, et elle seule, qui distingue ces algorithmes — ils font
sinon tous la même chose.

**Course** — deux à quatre algorithmes côte à côte, même terrain, même graine,
synchronisés, avec les compteurs en vis-à-vis et un verdict chiffré.

**Mesurer** — rejoue jusqu'à 1000 fois sans affichage, produit un tableau de moyennes et
d'étendues, et trace les distributions. C'est ce qui fait passer de « je sens la
différence » à « je la mesure ».

**Comprendre** — une fiche par algorithme : l'idée en une phrase, une démonstration
animée en boucle sur le terrain qui lui va le mieux, le pseudo-code, la structure de
données et pourquoi c'est elle qui décide du comportement, ce qu'il garantit **et ce
qu'il ne garantit pas**, le coût en temps et en mémoire, ses usages réels, et des liens
vers les algorithmes à lui comparer.

Chaque fiche se termine par une affirmation et un bouton qui la **vérifie en la
mesurant** sur-le-champ. Aucun chiffre n'est écrit en dur : ils sont tous calculés au
moment où tu cliques.

### Le son du parcours

Chaque type d'étape a son timbre : l'examen d'un candidat, l'arête retenue, le
dépilement, l'arête écartée, la fusion de deux îlots, le mur posé. Deux hauteurs
portent une information plutôt qu'une simple couleur : dans le parcours en largeur la
note monte avec la distance au départ, puis recommence — on **entend** le front
s'éloigner ; chez la main sur le mur, la note dépend de la direction suivie, si bien
qu'on entend le promeneur tourner aux angles.

Comme dans le jeu, les hauteurs sont calées sur une gamme pentatonique et la cadence est
bridée à une quinzaine de sons par seconde. Le bouton 🔊 de la barre de commandes coupe
le son, et le réglage est retenu. En mode Course, seul le premier concurrent est
sonorisé : quatre pistes simultanées seraient inaudibles.

## Quelques résultats à retrouver soi-même

- **Prim et Kruskal donnent toujours exactement le même poids total.** Deux démarches
  opposées — croissance locale contre tri global — qui convergent vers le même optimum.
- **La profondeur produit des chemins bien plus longs que Prim**, à nombre d'arêtes
  identique : sur une grille 12×12, un diamètre d'arbre d'environ 91 contre 44. Le biais
  de l'algorithme, et rien d'autre, décide de la difficulté. Le diamètre est mesuré par
  double balayage — partir d'un sommet quelconque mène à une extrémité du diamètre, et
  repartir de là donne le maximum réel. Mesurer depuis le coin de départ le
  sous-estimerait d'environ 15 % chez Prim.
- **Le gain d'A\* sur Dijkstra dépend entièrement du terrain** : environ 4× sur un nuage
  de points, 1,8× sur une grille à obstacles, mais à peine mieux que Dijkstra dans un
  labyrinthe. Un labyrinthe est un arbre : il n'existe qu'un chemin, donc l'heuristique
  n'a presque rien à guider. Une bonne heuristique ne sert que là où il y a un choix.
- **Sur l'image synthétique, qui contient 7 régions, Kruskal en retrouve exactement 7**
  au seuil par défaut.

## Vérification automatique

Le bouton « Vérifier les invariantes » contrôle sur une douzaine de graines que :

- tout arbre couvrant a exactement n−1 arêtes et laisse tous les sommets atteignables ;
- Prim et Kruskal donnent le même poids total ;
- A\* n'examine jamais plus de sommets que Dijkstra, pour un chemin de même coût ;
- la main sur le mur échoue bel et bien sur un domaine à boucles — comportement attendu
  et annoncé, pas un défaut masqué.

## Notes de conception

- Chaque algorithme est un **générateur** (`function*`) : une itération = une étape
  observable. Le réglage de vitesse, la pause, l'avance pas à pas et l'exécution
  instantanée en découlent sans dupliquer une ligne de logique.
- Le hasard passe par un générateur à graine, jamais par `Math.random` directement.
  Chaque configuration porte un code court qui rejoue exactement la même scène.
- Sur le terrain image, la photo est une **entrée** et non un tirage : la graine ne la
  change pas. Une image peut être chargée depuis l'appareil, elle ne quitte jamais le
  navigateur.
- L'heuristique d'A\* utilise la distance de Manhattan sur une grille et la distance
  euclidienne sur un nuage, toujours multipliée par le coût minimal d'un pas : c'est la
  condition d'admissibilité, sans laquelle A\* cesserait de garantir le plus court chemin.

---

# Tests

Les deux pages sont couvertes par une suite exécutée dans un vrai navigateur.

```
npm install
npx playwright install chromium
npm test
```

110 contrôles, dont les propriétés mathématiques vérifiées contre des références
recalculées dans le test lui-même. Le détail de ce qui est couvert — et surtout **ce qui
ne l'est pas** — se trouve dans [`tests/README.md`](tests/README.md).
