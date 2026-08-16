# Atelier — studio de dessin assisté par IA

Studio de dessin vectoriel dans le navigateur : dessinez à main levée et un
classifieur géométrique détecte les formes simples (ligne, rectangle, carré,
losange, triangle, pentagone à octogone, cercle/ellipse, étoile) pour
proposer une version nette du trait. À côté, des outils de tracé direct
(ligne, flèche, rectangle, ellipse) pour un résultat propre du premier coup.

## Fonctionnalités

- **Crayon** avec correction de traits, ou outils de forme directs (ligne,
  flèche, rectangle, ellipse).
- **Sélection** : multi-sélection au lasso ou Maj+clic, déplacement,
  redimensionnement par poignées, suppression.
- **Calques** : ajout, renommage, visibilité, réordonnancement.
- **Zoom & pan** : molette pour zoomer (centré sur le curseur), outil Main
  pour se déplacer.
- **Historique** annuler/rétablir complet (Ctrl+Z / Ctrl+Maj+Z), y compris
  les déplacements et redimensionnements.
- **Mode sombre** (auto ou manuel), palette d'encre adaptée par thème,
  couleur personnalisée.
- **Export** PNG ou SVG (rognés au contenu), **sauvegarde/ouverture** du
  projet en fichier `.json`, sauvegarde automatique locale.

## Raccourcis clavier

`P` crayon · `V` sélection · `L` ligne · `A` flèche · `R` rectangle ·
`O` ellipse · `H` main · `Ctrl+Z` / `Ctrl+Maj+Z` annuler/rétablir ·
`Suppr` supprimer la sélection.

## Développement

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Structure

- `src/geometry.js` — géométrie pure (classification de formes, RDP, bbox…).
- `src/canvasElements.jsx` — sous-composants SVG (tracés, poignées, papier).
- `src/theme.js` — palettes clair/sombre.
- `src/App.jsx` — état, interactions, mise en page.
