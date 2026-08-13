# NEURA-SET

Un co-producteur musical IA pour Ableton Live : il écoute ce que vous jouez
via un routing audio interne, en extrait le tempo/la tonalité/l'accord/la
structure, propose des continuations MIDI cohérentes, et les dépose comme
clips dans une piste dédiée — vous les acceptez ou rejetez d'un clic dans une
interface web, rien n'atterrit dans le mix sans validation humaine.

## Architecture

Le système est organisé en 4 couches (perception → décision → génération →
action), détaillées avec un diagramme de flux dans
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). En résumé :

1. **Perception** (`neura_set/perception/`) — capture audio temps réel,
   tempo/tonalité/accord/structure via `librosa` + template matching.
2. **Génération** (`neura_set/generation/`) — chaîne de Markov entraînée en
   ligne sur ce que vous jouez, avec un point d'extension documenté pour un
   vrai modèle Transformer/MusicGen.
3. **Décision** (`neura_set/decision/`) — un agent à règles décide quand
   proposer et filtre les doublons ; scaffold RL (Gymnasium + PPO) prêt à
   entraîner une fois des logs de session disponibles.
4. **Action** (`neura_set/action/`) — écrit les propositions dans Ableton via
   [AbletonOSC](https://github.com/ideoforms/AbletonOSC), ou exporte un
   `.mid` autonome.

Une interface web (FastAPI + WebSocket) affiche les propositions en direct
avec des boutons Accepter/Rejeter.

## État actuel

Tout ce qui est listé ci-dessus **fonctionne** (12 tests passent, voir
`tests/`) : capture audio, extraction de features, détection d'accord,
segmentation de structure, génération Markov, agent de décision, export MIDI,
client OSC, serveur web. Ce qui **ne l'est pas encore**, volontairement :

- Le modèle génératif type Music Transformer / MusicGen fine-tuné —
  demande un GPU et un corpus MIDI d'entraînement. `transformer_generator.py`
  documente les deux voies d'intégration possibles.
- L'agent de décision par renforcement — l'environnement Gymnasium existe et
  fonctionne, mais l'entraîner avant d'avoir de vraies sessions loggées
  reviendrait à apprendre du bruit.
- Le CNN de reconnaissance d'accords — remplacé par du template matching sur
  chromagramme, suffisant pour des triades sur un mix propre.

Voir la section "Écarts avec le brief initial" de `docs/ARCHITECTURE.md` pour
le détail des compromis.

## Stack technique

| Composant | Outil |
|---|---|
| Communication Ableton | AbletonOSC + `python-osc` |
| Analyse audio | `librosa` |
| Génération musicale | Chaîne de Markov (par défaut) ; point d'extension PyTorch/Transformer |
| Agent de décision | Règles (par défaut) ; scaffold `stable-baselines3` |
| Interface de contrôle | FastAPI + WebSocket |
| Export MIDI | `mido` |

## Installation

macOS / Linux :

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Windows (PowerShell ou l'invite de commandes) :

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

Sur Windows, la commande s'appelle `python` (pas `python3`), et l'activation du
venv passe par `.venv\Scripts\activate` plutôt que `source .venv/bin/activate`.
Si vous préférez ne pas utiliser de venv, `pip install -e ".[dev]"` seul
fonctionne aussi directement avec votre Python global.

## Utilisation

Lancer la commande seule (`python -m neura_set`) ne suffit pas à obtenir des
propositions : NEURA-SET écoute un périphérique d'entrée audio, pas
directement Ableton. Tant que ce périphérique ne reçoit aucun son (micro
silencieux, rien routé dessus), l'interface affichera "En attente…" — c'est
le comportement normal, pas un bug.

### Étape 1 — router le son d'Ableton vers NEURA-SET

Il faut un câble audio virtuel qui fait sortir le son d'Ableton d'un côté et
rentrer comme "micro" de l'autre :

- **Windows** : installez [VB-CABLE](https://vb-audio.com/Cable/) (gratuit).
  Dans Ableton, Préférences → Audio → réglez la sortie sur "CABLE Input". Ça
  coupe le monitoring normal ; pour garder le son sur vos enceintes *et*
  l'envoyer à NEURA-SET, utilisez [VoiceMeeter](https://vb-audio.com/Voicemeeter/)
  à la place, qui permet de dupliquer la sortie.
- **macOS** : [BlackHole](https://github.com/ExistentialAudio/BlackHole)
  (gratuit), même principe, combinable avec un périphérique agrégé pour
  garder le monitoring.
- **Linux** : créez un sink PipeWire/PulseAudio virtuel (`pactl load-module
  module-null-sink`) et routez la sortie d'Ableton dessus.

### Étape 2 — dire à NEURA-SET quel périphérique écouter

```bash
python -m neura_set --list-audio-devices
```

Repérez le nom ou l'index du câble virtuel (ex. `CABLE Output` sur Windows
avec VB-CABLE) dans la liste, puis :

```bash
python -m neura_set --input-device "CABLE Output"
```

Sans cet argument, NEURA-SET écoute le périphérique d'entrée par défaut du
système (généralement votre micro) — ce qui explique une interface qui reste
vide même en jouant, si Ableton ne sort pas sur ce device.

### Étape 3 — avec Ableton, pour écrire les propositions dans un clip

1. Installez [AbletonOSC](https://github.com/ideoforms/AbletonOSC) comme
   Control Surface.
2. Créez une piste MIDI dédiée (ex. "NEURA-SET Proposals") et notez son index.
3. Lancez :

```bash
python -m neura_set --input-device "CABLE Output" --track-id 2 --style techno
```

4. Ouvrez `http://localhost:8000` pour accepter/rejeter les propositions en
   direct. Sans `--track-id`, NEURA-SET tourne en mode UI seule (pas d'écriture
   dans Ableton) — pratique pour tester juste la boucle écoute → proposition.

## Utilisation depuis un téléphone Android

L'interface tourne côté serveur : le téléphone n'est qu'un écran de
validation, aucune install requise dessus. Le serveur écoute déjà sur
`0.0.0.0` par défaut, donc :

1. Assurez-vous que l'ordinateur et le téléphone sont sur le même réseau WiFi.
2. Trouvez l'adresse IP locale de l'ordinateur (`ip a` sur Linux, `ipconfig`
   sur Windows, `ifconfig` sur macOS — cherchez quelque chose comme
   `192.168.1.x`).
3. Sur le téléphone, ouvrez Chrome et allez sur `http://<cette-ip>:8000`.
4. Menu Chrome (⋮) → **Ajouter à l'écran d'accueil** : la page s'installe
   avec sa propre icône et se lance en plein écran, sans barre d'adresse.

L'interface est pensée pour Android dès le départ : cibles tactiles ≥ 48px,
retour visuel au toucher (pas de survol nécessaire), reconnexion automatique
du WebSocket si Android met l'onglet en veille (écran éteint, changement
d'appli), et couleur de la barre de statut Chrome assortie au thème
clair/sombre du téléphone. Limite connue : si vous exposez le serveur sur
internet (au lieu du LAN) derrière HTTPS, utilisez un reverse-proxy qui gère
le TLS — le navigateur bascule automatiquement en `wss://` dans ce cas, mais
un simple tunnel HTTP ne suffira pas.

## Roadmap

- [ ] Fine-tuner un Music Transformer sur un corpus MIDI par genre
- [ ] Entraîner l'agent RL une fois des sessions réelles loggées
- [ ] CNN de reco d'accords (remplacer le template matching)
- [ ] Auto-ducking / EQ dynamique réactifs à l'analyse spectrale
- [ ] Contrôle des paramètres de mix via AbletonOSC
