# claudeai
Made with Claude

## Culture Générale — quiz en Python

Application en ligne de commande, entièrement en Python (bibliothèque standard uniquement).
Choisissez une thématique (Histoire, Géographie, Sciences, Nature, Littérature & Arts, Sport,
Société & Monde — 62 sujets, 310 questions au total, inspirés de la collection encyclopédique
« Tout l'Univers »), puis un mode :

- **Quiz** : un sujet est ouvert au hasard dans la thématique, avec une série de questions à
  choix multiples mélangées aléatoirement.
- **Article surprise (Wikipédia)** : un vrai article Wikipédia lié à la thématique est tiré au
  hasard et son résumé (titre, extrait, lien) est affiché. Ce mode nécessite une connexion
  internet.

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

### Lancer les tests

```bash
pip install -r requirements-dev.txt
python3 -m pytest
```
