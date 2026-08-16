# Émulateur BASIC

Un émulateur/interpréteur BASIC qui tourne directement dans le navigateur, sans dépendance ni étape de build. Il est fourni avec **8 programmes preset**, déjà prêts à charger et exécuter depuis le menu déroulant.

Made with Claude

## Utilisation

Comme les presets sont chargés via `fetch()`, il faut servir les fichiers avec un petit serveur local (double-cliquer sur `index.html` ne fonctionnera pas à cause des restrictions CORS sur `file://`) :

```bash
python3 -m http.server 8080
# puis ouvrir http://localhost:8080/index.html
```

ou avec Node :

```bash
npx serve .
```

## Presets inclus (`/presets/*.bas`)

| Fichier | Description |
| --- | --- |
| `hello.bas` | Bonjour le monde + boucle FOR |
| `fizzbuzz.bas` | FizzBuzz de 1 à 30 |
| `fibonacci.bas` | Suite de Fibonacci (N termes saisis) |
| `guess.bas` | Jeu « devine le nombre » (RND + boucle) |
| `times-table.bas` | Table de multiplication |
| `primes.bas` | Nombres premiers jusqu'à N |
| `stats.bas` | Statistiques (somme/moyenne/min/max) sur un tableau `DIM` |
| `pyramid.bas` | Pyramide d'étoiles ASCII (boucles imbriquées) |

Chaque fichier `.bas` est un vrai programme BASIC classique (numéros de ligne inclus) que vous pouvez aussi ouvrir/éditer directement, ou coller dans l'éditeur.

## Dialecte supporté

- **Instructions** : `LET`, `PRINT`, `INPUT`, `IF/THEN/ELSE`, `FOR/TO/STEP/NEXT`, `GOTO`, `GOSUB/RETURN`, `DIM`, `DATA/READ/RESTORE`, `CLS`, `END/STOP`, `REM` (ou `'`)
- **Opérateurs** : `+ - * / ^ MOD`, comparaisons `= <> < > <= >=`, logiques `AND OR NOT`
- **Fonctions numériques** : `ABS INT SGN SQR SIN COS TAN ATN LOG EXP RND`
- **Fonctions chaînes** : `LEN LEFT$ RIGHT$ MID$ CHR$ ASC STR$ VAL INSTR SPACE$ STRING$ TAB()`
- Tableaux 1D/2D via `DIM`, variables texte suffixées par `$`
- Plusieurs instructions par ligne séparées par `:`

C'est un dialecte simplifié inspiré du GW-BASIC / Applesoft BASIC — pas une implémentation 100% fidèle, mais suffisant pour écrire de vrais petits programmes BASIC classiques.

## Architecture du code

- `js/basic-interpreter.js` — le moteur : lexer, parser (analyse récursive descendante) et interpréteur (exécution asynchrone, avec pause réelle sur `INPUT`)
- `js/presets.js` — la liste des programmes preset (métadonnées + chemin vers le fichier `.bas`)
- `js/app.js` — l'interface (éditeur, terminal, gestion de l'entrée utilisateur, bouton Stop pour les boucles infinies)
- `css/style.css` — thème terminal rétro
- `presets/*.bas` — les programmes preset eux-mêmes
- `index.html` — la page principale

Testé manuellement avec Playwright/Chromium : chargement de chaque preset, exécution complète avec entrées utilisateur simulées, gestion des erreurs de syntaxe et d'exécution, et arrêt d'une boucle infinie via le bouton Stop.
