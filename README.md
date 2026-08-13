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

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Utilisation

Sans Ableton, pour tester la boucle perception → génération → UI :

```bash
python -m neura_set
```

Avec Ableton :

1. Installez [AbletonOSC](https://github.com/ideoforms/AbletonOSC) comme
   Control Surface.
2. Créez une piste MIDI dédiée (ex. "NEURA-SET Proposals") et notez son index.
3. Routez la sortie d'Ableton (ou une cue) vers un device de loopback virtuel
   (BlackHole/VB-Cable/PipeWire sink) — voir `docs/ARCHITECTURE.md`.
4. Lancez :

```bash
python -m neura_set --track-id 2 --style techno
```

5. Ouvrez `http://localhost:8000` pour accepter/rejeter les propositions en
   direct.

## Roadmap

- [ ] Fine-tuner un Music Transformer sur un corpus MIDI par genre
- [ ] Entraîner l'agent RL une fois des sessions réelles loggées
- [ ] CNN de reco d'accords (remplacer le template matching)
- [ ] Auto-ducking / EQ dynamique réactifs à l'analyse spectrale
- [ ] Contrôle des paramètres de mix via AbletonOSC
