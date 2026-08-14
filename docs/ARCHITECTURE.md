# Architecture de NEURA-SET

NEURA-SET est structuré en 4 couches, chacune un package sous `src/neura_set/`,
communiquant via deux types de données partagés (`neura_set/types.py`) :

- `MusicalContext` — ce que le système entend *maintenant* (tempo, tonalité,
  accord, énergie, section du morceau).
- `Proposal` — une idée générée (liste de `NoteEvent`) en attente de
  validation humaine.

```
 micro/loopback           écran / navigateur            Ableton Live
      │                          ▲                            ▲
      ▼                          │                            │
┌───────────┐   MusicalContext ┌────────────┐  Proposal  ┌───────────┐
│ perception │ ───────────────▶│  decision  │───────────▶│  action   │
│ (écoute)   │                 │ (filtre)   │             │ (écrit)   │
└───────────┘                  └─────┬──────┘             └───────────┘
                                      │ generate()               ▲
                                      ▼                          │
                                ┌────────────┐                   │
                                │ generation │───────────────────┘
                                │ (compose)  │   Proposal.notes
                                └────────────┘
                                      ▲
                          accept/reject via WebSocket
                                      │
                                ┌────────────┐
                                │ interface  │  (FastAPI + WS, UI web)
                                └────────────┘
```

`orchestrator.py` est le point de jonction : une boucle asyncio interroge la
perception à intervalle régulier, consulte la couche décision, déclenche la
génération, pousse le résultat vers l'UI et (si configuré) écrit le clip dans
Ableton via OSC. Les retours accept/reject repartent de l'UI vers la décision
(apprentissage des préférences) et le générateur (entraînement en ligne).

## 1. Perception — `neura_set/perception/`

| Fichier | Rôle | État |
|---|---|---|
| `audio_capture.py` | Capture temps réel via `sounddevice` (PortAudio) dans un ring buffer, thread-safe | Fonctionnel, nécessite un device de loopback configuré dans l'OS/Ableton |
| `audio_features.py` | Tempo (`librosa.feature.tempo`), chroma, tonalité (corrélation avec les profils de Krumhansl-Kessler), RMS, centroïde spectral, densité d'onsets | Fonctionnel |
| `chord_detection.py` | Détection d'accord par *template matching* sur le chromagramme (triades maj/min) | Fonctionnel, mais volontairement simple — voir "Écarts avec le brief" |
| `structure_segmentation.py` | Segmentation par matrice d'auto-similarité + noyau damier (Foote 2000), étiquetage grossier par énergie relative | Fonctionnel, heuristique |
| `analyzer.py` | Combine tout ça en un `MusicalContext`, verrouille la tonalité globale une fois détectée avec confiance, lisse le tempo (moyenne mobile exponentielle) et la section (confirmation sur plusieurs mesures consécutives avant de changer) pour éviter le flicker d'une fenêtre de 4s à l'autre | Fonctionnel |

## 2. Génération — `neura_set/generation/`

| Fichier | Rôle | État |
|---|---|---|
| `base.py` | Interface `Generator` (`generate()`, `train()`) | — |
| `markov_generator.py` | Chaîne de Markov à ordre variable sur les degrés de la gamme, entraînée en ligne sur ce que joue l'humain, avec repli sur une règle de voix (temps forts → notes de l'accord, temps faibles → mouvement par degré) | **Fonctionnel de bout en bout**, c'est le générateur par défaut |
| `style.py` | Presets de style (densité, registre, vélocité, swing, legato) appliqués en post-traitement | Fonctionnel |
| `transformer_generator.py` | Point d'extension pour un vrai modèle (Music Transformer / MusicGen fine-tuné) | **Non implémenté intentionnellement** — voir docstring du fichier |

## 3. Décision — `neura_set/decision/`

| Fichier | Rôle | État |
|---|---|---|
| `agent.py` | `DecisionAgent` à règles : silence gate (pas de proposition sous `min_rms_energy`, donc rien au démarrage tant que personne ne joue), cooldown, limite de propositions en attente, évitement des sections denses (drop/chorus), recul si le taux d'acceptation chute sur une section, filtrage de nouveauté (similarité de hauteurs vs. propositions récemment acceptées) | **Fonctionnel**, c'est l'agent par défaut |
| `rl_agent.py` | Environnement Gymnasium + entraînement PPO (stable-baselines3) rejouant des transitions (contexte, proposer/pas, accepté/rejeté) loggées | Fonctionnel *si des logs existent* — non branché sur le pipeline par défaut, car il n'y a pas encore de données de session réelles pour entraîner sur autre chose que du bruit |

## 4. Action — `neura_set/action/`

| Fichier | Rôle | État |
|---|---|---|
| `osc_client.py` | Client OSC vers AbletonOSC (envoi + écoute des réponses) | Fonctionnel, adresses à revérifier contre la version d'AbletonOSC installée |
| `midi_writer.py` | `NoteEvent` → tuples OSC AbletonOSC, ou export `.mid` autonome (via `mido`) | Fonctionnel |
| `ableton_controller.py` | Dépose chaque proposition dans un clip libre de la piste "NEURA-SET Proposals" ; accepter = fire le clip, rejeter = stop + vide le clip | Fonctionnel |

## 5. Interface — `neura_set/interface/`

FastAPI + WebSocket (`app.py`, `websocket_manager.py`) + une page HTML/JS
autonome (`static/index.html`, pas de build step) qui liste les propositions
en direct avec des boutons Accepter/Rejeter.

## Écarts avec le brief initial (et pourquoi)

Le brief envisage un CNN pour la reco d'accords, un Transformer fine-tuné
(Magenta / MusicGen) et un agent RL entraîné en production. Ces trois pièces
demandent soit un GPU + corpus MIDI d'entraînement, soit des sessions réelles
enregistrées pour avoir un signal de récompense qui ne soit pas du bruit —
aucun des deux n'existe à ce stade. Plutôt que de livrer des stubs qui
prétendent marcher, chaque couche a une implémentation *réelle et utilisable
aujourd'hui* (template matching, Markov, règles) et un point d'extension
clairement documenté pour la version "brief complet" (voir
`transformer_generator.py` et `rl_agent.py`).

## Lancer le système

```bash
pip install -e ".[dev]"

# Sans Ableton, juste l'UI + le générateur Markov, pour tester la boucle :
python -m neura_set

# Avec Ableton : créez d'abord une piste MIDI "NEURA-SET Proposals" et
# notez son index (0 = première piste), lancez AbletonOSC, puis :
python -m neura_set --track-id 2 --style techno
```

Ouvrez `http://localhost:8000` pour voir arriver les propositions.

## Configuration audio (loopback)

`AudioCapture` lit un device d'entrée standard — il n'écoute pas Ableton
directement. Routez la sortie (ou une piste cue) d'Ableton vers un device de
loopback virtuel (BlackHole sur macOS, VB-Cable sur Windows, un sink
PulseAudio/PipeWire sur Linux), puis pointez `AudioConfig.input_device`
dessus.
