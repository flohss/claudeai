# Simulateur de système solaire

Application web pour créer un système planétaire et l'observer évoluer, avec une physique gravitationnelle réaliste.

## Fonctionnalités

- **Étoile configurable** : classes spectrales O à M. La classe fixe la masse, la luminosité et la couleur de l'étoile. Les zones correspondantes s'affichent dans la vue 3D : la zone habitable (anneau vert) et la ligne des glaces (cercle pointillé).
- **Planètes et lunes** : on peut les ajouter, les modifier et les supprimer (nom, type, masse, rayon, demi-grand axe, excentricité, inclinaison, albédo, couleur). Une orbite modifiée repart de la position actuelle du corps.
- **Simulation à N corps** : toutes les attractions entre tous les corps sont calculées, avec un intégrateur symplectique Velocity Verlet. Le pas de calcul s'adapte à l'orbite la plus rapide (environ 200 pas par orbite). Si la machine ne suit pas, la simulation ralentit au lieu de perdre en précision, et la vitesse réellement atteinte s'affiche.
- **Fiche de chaque corps, en temps réel** : masse volumique, gravité de surface, vitesse de libération, orbite actuelle (a, e, i, période), température d'équilibre, position par rapport à la zone habitable et verdict d'habitabilité.
- **Événements** :
  - les collisions fusionnent les corps (la masse et la quantité de mouvement sont conservées) ;
  - une lune qui sort de la sphère de Hill de sa planète s'en échappe ;
  - un corps non lié qui dépasse 1000 UA est éjecté du système.

  Chaque événement est noté dans le journal.
- **Préréglages** : notre système solaire (8 planètes, Pluton et 6 lunes principales), un système aléatoire généré de façon plausible (planètes rocheuses à l'intérieur de la ligne des glaces, géantes au-delà, espacement stable), ou une étoile seule.
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
    nbody.ts      Accélérations, pas Verlet, collisions (détection continue), fusions
    stars.ts      Classes spectrales, zone habitable, ligne des glaces
    derived.ts    Gravité, température d'équilibre, habitabilité…
  sim/       État de la simulation et données
    Simulation.ts Store observable : pas de temps, événements, éditions
    presets.ts    Système solaire, étoile seule
    random.ts     Générateur de systèmes déterministe (graine)
    serialization.ts  Sauvegarde/chargement validés
  render/    Rendu Three.js (scène, textures procédurales)
  ui/        Composants React
```

## Choix de représentation

Les vraies proportions rendraient planètes et lunes invisibles. Les **tailles** affichées suivent donc une échelle logarithmique, et la **distance lune-planète** est exagérée à l'écran. Les **distances entre planètes**, elles, restent à l'échelle (1 UA = 10 unités de scène). Tous les calculs physiques utilisent les valeurs réelles.

La température affichée est la température d'équilibre radiatif, sans effet de serre. La Terre y est à environ −18 °C.
