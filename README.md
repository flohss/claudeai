# Moi.AI — Double personnel artificiel

Une IA locale qui te connaît, apprend de toi en permanence et construit ton profil au fil des conversations.

## Fonctionnement

- Chaque échange est sauvegardé en local (SQLite).
- Après chaque message, Claude extrait automatiquement les informations personnelles et les mémorise.
- Le profil condensé est injecté dans chaque conversation pour que l'IA te connaisse vraiment.

## Installation

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
python main.py
```

## Commandes

| Commande   | Description                        |
|------------|------------------------------------|
| `/profil`  | Voir ton profil mémorisé           |
| `/faits`   | Lister tous les faits appris       |
| `/stats`   | Statistiques (messages, faits…)    |
| `/aide`    | Afficher l'aide                    |
| `/quitter` | Quitter                            |

## Structure

```
moiai/
  memory.py     — couche SQLite (conversations, profil, faits)
  extractor.py  — extraction automatique de faits via Claude
  chat.py       — moteur de conversation avec contexte personnel
main.py         — interface CLI (Rich)
```
