# Simulateur de système solaire

Application web pour créer un système planétaire et l'observer évoluer, avec une physique gravitationnelle réaliste.

## Fonctionnalités

- **Étoile configurable** : classes spectrales O à M. La classe fixe la masse, la luminosité et la couleur de l'étoile. Les zones correspondantes s'affichent dans la vue 3D : la zone habitable (anneau vert) et la ligne des glaces (cercle pointillé).
- **Systèmes doubles** : on peut ajouter une étoile compagne (classe, séparation, excentricité). Les planètes peuvent tourner autour d'une seule étoile (type S) ou des deux (circumbinaires, type P). Le panneau indique les limites de stabilité selon le critère de Holman et Wiegert (1999), et chaque fiche dit si l'orbite est stable. La température et la zone habitable tiennent compte de la lumière des deux étoiles. Une planète arrachée à son étoile devient circumbinaire.
- **Formation planétaire** : un disque protoplanétaire de planétésimaux autour d'une jeune étoile. En se percutant, ils fusionnent en protoplanètes puis en planètes. Au-delà de la ligne des glaces, les noyaux d'au moins 3 M⊕ capturent le gaz du disque et deviennent des géantes, jusqu'à ce que ce gaz se dissipe. Le modèle est accéléré (rayons de capture agrandis, gaz dissipé en 300 ans) pour voir le résultat en quelques minutes.
- **Anneaux** : Saturne et Uranus en ont, comme certaines géantes des systèmes aléatoires, et on peut en ajouter à toute planète (bords, opacité, couleur). Ils sont orientés selon l'axe de rotation. Une lune qui franchit la limite de Roche de sa planète est disloquée par les marées et forme un anneau.
- **Graphiques en temps réel** : la dérive de l'énergie totale (elle mesure la précision du calcul ; les collisions apparaissent en pointillés), l'excentricité et le demi-grand axe des planètes. Chaque graphique a un réticule et une infobulle, une légende cliquable qui sélectionne le corps, et un tableau de valeurs.
- **Planètes et lunes** : on peut les ajouter, les modifier et les supprimer (nom, type, masse, rayon, demi-grand axe, excentricité, inclinaison, albédo, couleur). Une orbite modifiée repart de la position actuelle du corps.
- **Simulation à N corps** : toutes les attractions entre tous les corps sont calculées, avec un intégrateur symplectique Velocity Verlet. Le pas de calcul s'adapte à l'orbite la plus rapide (environ 200 pas par orbite). Si la machine ne suit pas, la simulation ralentit au lieu de perdre en précision, et la vitesse réellement atteinte s'affiche.
- **Fiche de chaque corps, en temps réel** : masse volumique, gravité de surface, vitesse de libération, orbite actuelle (a, e, i, période), température d'équilibre, position par rapport à la zone habitable et verdict d'habitabilité.
- **Événements** :
  - les collisions fusionnent les corps (la masse et la quantité de mouvement sont conservées) ;
  - une lune qui sort de la sphère de Hill de sa planète s'en échappe ;
  - un corps non lié qui dépasse 1000 UA est éjecté du système.

  Chaque événement est noté dans le journal.
- **Préréglages** :
  - notre système solaire (8 planètes, Pluton et 6 lunes principales, anneaux de Saturne et d'Uranus) ;
  - Kepler-16, une binaire serrée avec sa planète circumbinaire ;
  - Alpha du Centaure, une binaire large avec des planètes hypothétiques ;
  - un système aléatoire plausible (planètes rocheuses à l'intérieur de la ligne des glaces, géantes au-delà, espacement stable) ;
  - un disque protoplanétaire paramétrable ;
  - une étoile seule.
- **Sauvegarde et chargement** au format JSON, qui reprend l'état exact du système.
- **Vue 3D** : caméra orbitale, trajectoires, noms, suivi du corps sélectionné, contrôle du temps de 1 jour à environ 27 ans par seconde (la touche Espace met en pause).

## Démarrer

```bash
npm install
npm run dev      # serveur de développement
npm test         # tests du moteur physique et de la simulation
npm run build    # vérification des types + build de production dans dist/
```

## Architecture

```
src/
  physics/   Moteur physique pur, sans dépendance au rendu
    units.ts      Unités internes : UA, masse solaire, année (G = 4π²)
    orbits.ts     Éléments orbitaux ⇄ position/vitesse, période, rayon de Hill
    binary.ts     Limites de stabilité des systèmes doubles (Holman & Wiegert)
    nbody.ts      Accélérations, pas Verlet, collisions (détection continue), fusions
    stars.ts      Classes spectrales, zone habitable, ligne des glaces
    derived.ts    Gravité, flux reçu, température d'équilibre, limite de Roche, habitabilité…
  sim/       État de la simulation et données
    Simulation.ts Store observable : pas de temps, événements (collisions, Roche,
                  évasions, capture de gaz), éditions, étoiles multiples
    disk.ts       Disque protoplanétaire et paramètres de formation
    telemetry.ts  Historique énergie / orbites pour les graphiques
    stability.ts  Verdict de stabilité d'une orbite dans un système double
    presets.ts    Système solaire, Kepler-16, Alpha du Centaure, étoile seule
    random.ts     Générateur de systèmes déterministe (graine)
    serialization.ts  Sauvegarde/chargement validés
  render/    Rendu Three.js (scène, textures procédurales)
  ui/        Composants React (dont LineChart, graphiques SVG sans dépendance)
```

## Choix de représentation

Les vraies proportions rendraient planètes et lunes invisibles. Les **tailles** affichées suivent donc une échelle logarithmique, et la **distance lune-planète** est exagérée à l'écran. Les **distances entre planètes**, elles, restent à l'échelle (1 UA = 10 unités de scène). Tous les calculs physiques utilisent les valeurs réelles.

La température affichée est la température d'équilibre radiatif, sans effet de serre. La Terre y est à environ −18 °C.
