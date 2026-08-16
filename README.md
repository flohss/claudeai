# claudeai

Outil en ligne de commande pour cloner ta propre voix et generer de la parole
(text-to-speech) a partir de texte ecrit, en utilisant le modele open-source
[Coqui XTTS-v2](https://github.com/coqui-ai/TTS).

Le clonage est "zero-shot" : un seul echantillon audio de ta voix (10-30
secondes) suffit, pas besoin d'entrainer un modele. Fournir **plusieurs**
echantillons (phrases, tons et rythmes differents) ameliore nettement la
qualite et la fidelite de la voix generee.

## ⚠️ Usage responsable

- N'utilise ce projet que pour cloner **ta propre voix**, avec ton propre
  consentement.
- Ne clone jamais la voix de quelqu'un d'autre sans son autorisation
  explicite.
- Le modele XTTS-v2 est distribue sous la
  [Coqui Public Model License](https://coqui.ai/cpml) (usage non commercial).

## Installation

Necessite Python 3.10 ou plus recent.

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

Le paquet `coqui-tts` (fork communautaire maintenu de Coqui TTS, module
Python `TTS`) est utilise a la place du paquet historique `TTS`, qui ne
supportait pas Python 3.12+.

Le premier lancement telecharge le modele XTTS-v2 (~2 Go).

## Mode facile (double-clic, Windows)

Pas a l'aise avec la ligne de commande ? Une fois l'installation ci-dessus
faite une premiere fois, tu peux double-cliquer directement sur :

- **`1_enregistrer_voix.bat`** pour enregistrer ta voix : le programme te
  pose les questions une par une (dossier, nombre de clips, duree...) dans
  la fenetre qui s'ouvre.
- **`2_generer_audio.bat`** pour generer un audio avec ta voix clonee : il
  te demande le dossier des echantillons, le texte a lire, la langue et le
  nom du fichier de sortie.

La fenetre reste ouverte a la fin (ou en cas d'erreur) pour que tu puisses
lire ce qui s'est passe.

## 1. Enregistrer plusieurs echantillons de ta voix

Utilise ton micro pour enregistrer plusieurs clips de 15-25 secondes, dans
un endroit calme et sans bruit de fond. Le script te guide clip par clip
avec des phrases suggerees assez longues pour bien remplir la duree (varie
le ton, le rythme, les emotions pour enrichir la voix clonee).

Lance-le sans argument pour repondre aux questions (ou double-clique sur
`1_enregistrer_voix.bat`) :

```bash
python record_sample.py
```

Ou passe directement les options si tu preferes :

```bash
python record_sample.py --output-dir samples --count 5 --duration 20
```

Cela cree `samples/my_voice_01.wav` a `samples/my_voice_05.wav`. Tu peux
relancer le script plus tard pour ajouter davantage de clips : la
numerotation reprend automatiquement apres le dernier fichier existant
(les clips precedents ne sont jamais ecrases).

Chaque clip est automatiquement nettoye apres l'enregistrement (silence de
debut/fin coupe, volume normalise) pour ameliorer la fidelite du clonage. Si
un clip contient moins de 3 secondes de parole detectee (silence, micro trop
bas...), le script te previent pour que tu puisses le refaire.

Tu peux aussi utiliser directement des fichiers audio existants (wav/mp3/flac)
de ta voix a la place.

### Ameliorer le rendu des emotions

XTTS-v2 reproduit ton timbre de voix, mais capte moins bien l'intonation
emotionnelle a partir d'echantillons neutres. Pour ameliorer ca, tu peux
enregistrer une serie de clips dediee a une emotion, avec des phrases
adaptees (joie, tristesse, colere, calme) :

```bash
python record_sample.py --output-dir samples --emotion joyeux --count 4 --duration 20
```

Cela cree les clips dans `samples/joyeux/`, avec des phrases suggerees
adaptees a cette emotion. Emotions disponibles avec phrases dediees :
`joyeux`, `triste`, `colere`, `calme` (toute autre etiquette utilise les
phrases generiques, dans son propre sous-dossier).

## 2. Generer de la parole avec ta voix clonee

Lance sans argument pour repondre aux questions (ou double-clique sur
`2_generer_audio.bat`) :

```bash
python clone_voice.py
```

Ou passe directement les options, en donnant tout le dossier d'echantillons
(recommande, meilleure qualite) :

```bash
python clone_voice.py \
  --speaker samples/ \
  --text "Bonjour, ceci est un test de clonage de ma propre voix." \
  --language fr \
  --output output.wav
```

Le dossier par defaut est `samples/` : si tu pointes vers ce dossier racine,
**tous** les fichiers audio de ses sous-dossiers (`samples/joyeux/`,
`samples/triste/`, etc.) sont inclus automatiquement, en plus de ceux a la
racine. Pour cibler une seule emotion, pointe directement vers son
sous-dossier, par exemple `--speaker samples/joyeux/`.

Ou liste des fichiers precis, ou un seul :

```bash
python clone_voice.py --speaker samples/my_voice_01.wav samples/my_voice_02.wav --text-file script.txt --output output.wav
python clone_voice.py --speaker samples/my_voice.wav --text "..." --output output.wav
```

Langues supportees : `en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn,
ja, hu, ko, hi`.

### Ajuster l'expressivite

`--style expressif` (au lieu du `normal` par defaut) augmente l'intonation
et l'emotion dans la voix generee, au prix d'un resultat un peu moins
stable :

```bash
python clone_voice.py --speaker samples/joyeux/ --text "..." --style expressif
```

Pour un reglage plus fin : `--temperature` (plus haut = plus expressif),
`--top-p` et `--speed` (vitesse de la voix). Ces options sont aussi
proposees comme question lors de l'utilisation sans argument.

### Verification automatique de la fidelite du texte

XTTS peut parfois sauter, repeter ou deformer un mot, surtout sur des
textes longs. Par defaut, `clone_voice.py` reecoute l'audio genere avec un
modele de reconnaissance vocale local ([faster-whisper](https://github.com/SYSTRAN/faster-whisper)),
le compare au texte demande, et **relance automatiquement la generation**
(jusqu'a `--max-retries`, 2 par defaut) si la correspondance est insuffisante,
en gardant la meilleure tentative. Le script affiche le score de fidelite
obtenu et, si le seuil n'est pas atteint, un resume des mots qui different.

Cette verification ralentit la generation (chargement d'un modele
supplementaire + une transcription par tentative). Pour la desactiver :

```bash
python clone_voice.py --speaker samples/ --text "..." --no-verify
```

Options associees : `--similarity-threshold` (seuil requis, 0.92 par
defaut), `--max-retries`, `--whisper-model` (taille du modele de
verification : `tiny`, `base`, `small` par defaut, `medium`, `large-v3` —
plus grand = plus precis mais plus lent). Le premier lancement telecharge
ce modele de verification separement (quelques centaines de Mo selon la
taille choisie).

## Notes

- Un GPU (CUDA) accelere fortement la generation, mais le CPU fonctionne
  aussi (plus lent).
- Les fichiers audio (`samples/*.wav`, `output*.wav`) ne sont pas versionnes
  dans git (voir `.gitignore`) car ce sont des donnees personnelles.
