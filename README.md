# claudeai

Outil en ligne de commande pour cloner ta propre voix et generer de la parole
(text-to-speech) a partir de texte ecrit, en utilisant le modele open-source
[Coqui XTTS-v2](https://github.com/coqui-ai/TTS).

Le clonage est "zero-shot" : un seul echantillon audio de ta voix (10-30
secondes) suffit, pas besoin d'entrainer un modele.

## ⚠️ Usage responsable

- N'utilise ce projet que pour cloner **ta propre voix**, avec ton propre
  consentement.
- Ne clone jamais la voix de quelqu'un d'autre sans son autorisation
  explicite.
- Le modele XTTS-v2 est distribue sous la
  [Coqui Public Model License](https://coqui.ai/cpml) (usage non commercial).

## Installation

Necessite Python 3.9-3.11.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Le premier lancement telecharge le modele XTTS-v2 (~2 Go).

## 1. Enregistrer un echantillon de ta voix

Utilise ton micro pour enregistrer 15-20 secondes de toi en train de parler
naturellement (lis un paragraphe a voix haute, dans un endroit calme, sans
bruit de fond) :

```bash
python record_sample.py --output samples/my_voice.wav --duration 20
```

Tu peux aussi fournir directement un fichier audio existant (wav/mp3/flac)
de ta voix a la place.

## 2. Generer de la parole avec ta voix clonee

```bash
python clone_voice.py \
  --speaker samples/my_voice.wav \
  --text "Bonjour, ceci est un test de clonage de ma propre voix." \
  --language fr \
  --output output.wav
```

Ou a partir d'un fichier texte :

```bash
python clone_voice.py --speaker samples/my_voice.wav --text-file script.txt --output output.wav
```

Langues supportees : `en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn,
ja, hu, ko, hi`.

## Notes

- Un GPU (CUDA) accelere fortement la generation, mais le CPU fonctionne
  aussi (plus lent).
- Les fichiers audio (`samples/*.wav`, `output*.wav`) ne sont pas versionnes
  dans git (voir `.gitignore`) car ce sont des donnees personnelles.
