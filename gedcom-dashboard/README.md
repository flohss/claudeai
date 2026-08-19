# Analyse généalogique GEDCOM → Dashboard HTML

Outil qui parse un fichier GEDCOM (`.ged`) et génère un dashboard HTML
interactif et **autonome** (aucune dépendance externe : CSS, JS et données
sont tous embarqués dans un unique fichier `.html`, consultable hors ligne
dans n'importe quel navigateur). Le dashboard permet aussi de **charger un
autre fichier GEDCOM**, d'**éditer l'arbre** (ajout/modification/suppression
de personnes et d'unions) et de **réexporter en GEDCOM**, entièrement côté
navigateur.

## Utilisation

```bash
python3 build_dashboard.py mon_arbre.ged -o dashboard.html
```

Le script ne dépend que de la bibliothèque standard Python (3.8+). Ouvrez
ensuite `dashboard.html` dans n'importe quel navigateur — aucun serveur,
aucune connexion internet requise.

## Contenu généré

Le dashboard présente 11 onglets :

1. **Démographie** — effectifs, répartition par sexe/génération, pyramide
   des âges, âge au décès (moyenne/médiane/distribution par siècle),
   doyen(ne) actuel(le), records de longévité.
2. **Chronologie** — naissances/mariages/décès par décennie, profondeur de
   l'arbre, frise des générations, écart générationnel moyen, saisonnalité
   (naissances/mariages/décès par mois, toutes années confondues, avec le
   mois le plus fréquent pour chacun).
3. **Géographie** — lieux de naissance/mariage/décès les plus fréquents,
   détection de migrations (naissance/décès dans des régions différentes),
   zones de concentration familiale.
4. **Familles** — taille des fratries, familles nombreuses, âge moyen au
   mariage, écart d'âge entre conjoints, remariages, fécondité (répartition
   du nombre d'enfants par famille, évolution du nombre moyen d'enfants par
   décennie de mariage, intervalle moyen entre naissances au sein d'une
   fratrie), table de toutes les familles avec recherche, et actions
   Modifier/Supprimer par union.
5. **Patronymes** — fréquence des noms de famille, évolution par période de
   50 ans.
6. **Qualité des données** — taux de complétude des fiches, anomalies de
   dates (incohérences parent/enfant, âges invraisemblables, décès non
   renseignés probables), doublons potentiels.
7. **Fiches individuelles** — recherche/filtre par nom, sexe, statut,
   génération et lien de parenté (famille par le sang vs par alliance) ;
   fiche détaillée par personne (dates, lieux, parents, conjoint(s),
   enfants, fratrie) avec navigation cliquable entre fiches, et boutons
   Modifier/Supprimer.
8. **Arbre** — arbre ascendant (pedigree) centré sur une personne choisie,
   2 à 8 générations, zoom, cases cliquables ouvrant la fiche ; navigation
   directe depuis n'importe quelle fiche (« Voir dans l'arbre »). Deux vues
   au choix : rectangulaire (éventail binaire classique) ou demi-cercle
   (éventail circulaire, avec la personne racine au centre en bas et les
   générations d'ascendants en anneaux concentriques au-dessus ; le texte
   suit la courbure de chaque case et, dans les générations profondes où
   les cases deviennent trop étroites pour du texte courbé, passe
   automatiquement à l'écriture radiale). Export papier en A4 ou A3 via
   l'impression native du navigateur (« Enregistrer au format PDF »),
   orientation choisie automatiquement pour remplir au mieux la page.
9. **Calendrier perpétuel** — naissances, mariages et décès classés par
   jour de l'année (toutes années confondues), filtrables par mois/type/nom,
   avec un rappel « dans l'histoire familiale » pour la date du jour.
10. **Questions** — pose des questions en français sur l'arbre (parents,
    naissance/décès d'une personne, lien de parenté exact entre deux
    personnes — cousin germain, grand-oncle, etc. —, records, listes par
    année…) via un moteur de reconnaissance de motifs entièrement local
    (aucune IA, aucune connexion réseau).
11. **Édition** — charger un autre fichier `.ged` (remplace les données
    affichées), exporter l'état actuel en GEDCOM, ajouter une nouvelle
    personne (avec lien vers père/mère existants), créer une union entre
    deux personnes.

Les modifications ne vivent qu'en mémoire dans la page (aucun serveur,
aucune sauvegarde automatique) : pensez à **exporter en GEDCOM** pour
conserver votre travail. L'export préserve aussi tout ce que l'outil ne
modélise pas explicitement (notes, citations de sources, `RIN`, `_UID`,
tags personnalisés…) : ces données sont conservées verbatim tant que la
fiche ou l'événement auquel elles sont rattachées n'est pas édité.

## Architecture

- `gedcom_parser.py` — parseur GEDCOM 5.5.x (INDI/FAM) côté Python, gère les
  formats de date variés (jour/mois/année, année seule, préfixes ABT/BEF/
  AFT/EST/CAL/BET…AND/FROM…TO). Sert à générer l'état initial embarqué dans
  le dashboard (`to_raw_json`).
- `gedcom_analyze.py` — CLI/bibliothèque Python autonome pour calculer les
  statistiques (démographie, chronologie, géographie, structure familiale,
  patronymes, qualité des données) hors du dashboard, si besoin. Calcule
  aussi, pour chaque personne, le lien avec la racine de l'arbre : famille
  par le sang (ascendant·e, descendant·e, collatéral·e) ou par alliance
  (conjoint·e ou lié·e uniquement via un mariage).
- `templates/gedcom_engine.js` — portage JavaScript complet du parsing, du
  calcul de statistiques (fidèle à `gedcom_analyze.py`, vérifié par
  comparaison directe des sorties) et de la sérialisation GEDCOM, plus la
  gestion d'état (ajout/modification/suppression d'individus et de
  familles). C'est ce moteur qui tourne dans le navigateur pour permettre le
  chargement de fichiers et l'édition en direct. Le parsing capture aussi,
  pour chaque fiche/événement, les blocs GEDCOM non modélisés (NOTE, SOUR,
  RIN, tags personnalisés…) sous forme de lignes brutes rattachées
  (`extra_lines`), et les enregistrements de niveau 0 non gérés (SOUR,
  OBJE, REPO…) verbatim (`otherRecords`), réémis tels quels à l'export.
- `templates/dashboard.html.tpl` + `templates/app.js` — gabarit HTML/CSS et
  logique de rendu (graphiques SVG faits main, formulaires d'édition, sans
  bibliothèque externe).
- `build_dashboard.py` — assemble le tout : parse le `.ged` → sérialise
  l'état brut en JSON → injecte ce JSON et les scripts dans le gabarit →
  écrit le fichier HTML final autonome.

## Exemple

`famille_hess.ged` → `dashboard.html` : arbre de 702 individus et 302
familles, généré à partir d'un export MyHeritage.
