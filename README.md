# claudeai
Made with Claude

## Culture Générale — quiz en Python

Application en ligne de commande, entièrement en Python (bibliothèque standard uniquement).
Choisissez une thématique (Histoire, Géographie, Sciences, Littérature & Arts, Sport) : un
sujet est alors ouvert au hasard dans cette thématique, avec une série de questions à choix
multiples mélangées aléatoirement.

### Lancer l'application

```bash
python3 app.py
```

### Structure

- `app.py` : point d'entrée.
- `culture_generale/data.py` : banque de questions, organisée par thématique puis par sujet.
- `culture_generale/quiz.py` : logique de tirage aléatoire du sujet et déroulement du quiz.
- `culture_generale/cli.py` : interface en ligne de commande (menus, questions, score).
