# claudeai
Made with Claude

## Culture Générale — quiz en Python

[![Tests](https://github.com/flohss/claudeai/actions/workflows/tests.yml/badge.svg)](https://github.com/flohss/claudeai/actions/workflows/tests.yml)

Application en ligne de commande, entièrement en Python (bibliothèque standard uniquement),
avec trois modes au choix :

- **Quiz de culture générale** : choisissez une thématique (Histoire, Géographie, Sciences,
  Nature, Littérature & Arts, Sport, Société & Monde — 16 sujets et 5 questions par sujet dans
  chacune, soit 112 sujets et 560 questions au total), un sujet est ouvert au hasard dans cette
  thématique (sans repasser deux fois par le même avant d'avoir fait le tour), avec une série
  de questions à choix multiples mélangées aléatoirement. À la fin, l'appli propose de lire
  l'article Wikipédia du sujet tiré au sort pour en savoir plus.
- **Article surprise (Wikipédia)** : une thématique puis un sujet sont tirés au hasard, puis un
  vrai article Wikipédia correspondant à ce sujet précis est recherché et son résumé (titre,
  extrait, lien) est affiché.
- **Recherche par mot-clé (Wikipédia)** : tapez un mot-clé ou un sujet de votre choix pour
  lister les articles Wikipédia correspondants, puis choisissez-en un pour en lire le résumé.

Les modes Wikipédia nécessitent une connexion internet.

### Lancer l'application

```bash
python3 app.py
```

### Structure

- `app.py` : point d'entrée.
- `culture_generale/data.py` : banque de questions, organisée par thématique puis par sujet.
- `culture_generale/quiz.py` : logique de tirage aléatoire du sujet et déroulement du quiz.
- `culture_generale/wikipedia.py` : recherche et récupération d'un article Wikipédia aléatoire
  (API MediaWiki, sans dépendance externe).
- `culture_generale/cli.py` : interface en ligne de commande (menus, questions, score).
- `tests/` : tests unitaires (pytest).
- `.github/workflows/tests.yml` : intégration continue, lance la suite de tests à chaque push
  et pull request.

### Lancer les tests

```bash
pip install -r requirements-dev.txt
python3 -m pytest
```
