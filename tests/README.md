# Suite de test

Les deux pages du dépôt sont testées dans un vrai navigateur, piloté par Playwright.
Les contrôles sont des **assertions** : la commande échoue si l'un d'eux tombe.

## Installation, une seule fois

```
npm install
npx playwright install chromium
```

## Lancer

```
npm test            # les deux suites
npm run test:jeu    # labyrinthe3d.html seul
npm run test:labo   # labo-algorithmes.html seul
```

Un petit serveur statique est démarré automatiquement sur le port 8907 : rien d'autre
à installer, et aucune connexion réseau n'est nécessaire.

Pour simplement ouvrir les pages sans tester : `npm run serve`.

## Ce qui est vérifié

**Le jeu** — chargement de three.js ; pour chacun des cinq motifs, douze tirages tous
distincts, toutes les cases atteignables et le compte d'arêtes attendu (n−1, sauf le
motif *Ouvert* qui doit dépasser ce compte) ; les 480 aller-retours possibles du code de
graine ; reproductibilité à graine égale ; construction des six décors en 3D ; joystick,
rotation du regard et absence de traversée de mur ; pause, reprise et exactitude du
chronomètre par rapport à l'horloge réelle ; carte agrandie en popup — ouverture au
clic, déplacements bloqués tant qu'elle est affichée, fermeture par clic sur le fond,
par le bouton ✕, par `Échap` ou par `M`, et mouvement qui reprend une fois refermée ;
objectif « Clés + sortie » — nombre et position des clés selon la difficulté, aucune
sur le départ ou la sortie, reproductibilité à graine égale, sortie éteinte et gain
refusé tant qu'il manque des clés, ramassage un par un avec mise à jour du compteur,
allumage de la sortie une fois complet, victoire ensuite ; fil d'Ariane, dont les cases
foulées restent un sous-ensemble des cases vues et incluent le départ ; non-régression
du mode classique (aucune clé posée, compteur masqué, sortie allumée d'emblée) ; indice
au sol et son effacement ; résolution comparée, avec le taux d'échec de la main
gauche mesuré sur 120 tirages ; sonorisation, sa cadence bridée, sa coupure et la
persistance du réglage.

**Le laboratoire** — les vingt-et-un croisements terrain × algorithme aboutissent ; n−1 arêtes
et connexité pour les trois algorithmes d'arbre sur deux terrains ; Prim et Kruskal au
même poids ; A* jamais plus coûteux que Dijkstra et toujours au même coût optimal, sur
trois terrains ; aucune configuration dégénérée sur grille à obstacles ; diamètre de
l'arbre vérifié contre une référence recalculée dans le test ; la main au mur qui sort
toujours d'un labyrinthe parfait et échoue parfois avec des boucles ; segmentation dont
le nombre de régions décroît avec le seuil ; Bellman-Ford sur un graphe orienté à coûts
positifs et négatifs — nombre de cycles négatifs détectés exactement quand il y en a,
distances et détection conformes à une référence Bellman-Ford recalculée dans le test,
forme du cycle signalé vérifiée arête par arête, et au moins un désaccord mesuré avec
Dijkstra, qui fige un sommet trop vite face à un coût négatif ; les dix fiches
explicatives, chacune avec ses sept sections, sa démonstration animée et sa
vérification chiffrée ; l'onglet Mesurer, son tableau, son histogramme et son bouton
d'invariantes.

## Limites à connaître

- Les tests s'exécutent sur **Chromium sans carte graphique** (rendu logiciel). Ni
  Safari, ni Firefox, ni un véritable appareil mobile ne sont couverts.
- Les échantillons vont de 20 à 120 tirages selon les contrôles : assez pour détecter
  une erreur systématique, pas une anomalie rare.
- Les performances réelles (images par seconde sur un téléphone modeste) ne sont pas
  mesurées.
