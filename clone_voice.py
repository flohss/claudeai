#!/usr/bin/env python3
"""CLI tool to synthesize speech in a cloned voice using Coqui XTTS-v2.

Sans argument, le script pose les questions directement (utile en cas de
double-clic). Avec des arguments, il fonctionne comme avant :
    python clone_voice.py --speaker samples/my_voice.wav --text "Bonjour, ceci est ma voix clonee."
    python clone_voice.py --speaker samples/*.wav --text-file script.txt --language fr --output out.wav
    python clone_voice.py --speaker samples/ --text "..." --output out.wav
"""
import argparse
import sys
from pathlib import Path

SUPPORTED_LANGUAGES = [
    "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl",
    "cs", "ar", "zh-cn", "ja", "hu", "ko", "hi",
]
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac"}
# XTTS-v2 defaults are temperature=0.65, top_p=0.8. Raising them makes the
# delivery more expressive/emotional, at some cost to stability.
STYLE_PRESETS = {
    "normal": {},
    "expressif": {"temperature": 0.85, "top_p": 0.92},
}


def resolve_speaker_files(paths: list[Path]) -> list[Path]:
    """Expand a mix of files and directories into a flat, deduplicated list of audio files."""
    files = []
    for path in paths:
        if not path.exists():
            sys.exit(f"Erreur : chemin de reference introuvable : {path}")
        if path.is_dir():
            found = sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)
            if not found:
                sys.exit(f"Erreur : aucun fichier audio ({', '.join(AUDIO_EXTENSIONS)}) "
                          f"trouve dans {path} (ni dans ses sous-dossiers)")
            files.extend(found)
        else:
            files.append(path)
    seen = set()
    unique_files = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)
    return unique_files


def parse_args():
    parser = argparse.ArgumentParser(description="Generate speech in a cloned voice from one or more reference audio samples.")
    parser.add_argument("--speaker", type=Path, nargs="+",
                         help="One or more reference audio files, and/or a directory of them (6-30s each, wav/mp3/flac).")
    text_group = parser.add_mutually_exclusive_group()
    text_group.add_argument("--text", type=str, help="Text to synthesize.")
    text_group.add_argument("--text-file", type=Path, help="Path to a text file to synthesize.")
    parser.add_argument("--language", default=None, choices=SUPPORTED_LANGUAGES,
                         help="Language of the text (default: fr).")
    parser.add_argument("--output", type=Path, default=None, help="Output audio file path (default: output.wav).")
    parser.add_argument("--style", choices=list(STYLE_PRESETS), default=None,
                         help="Generation preset: 'normal' (default) or 'expressif' (more emotion/intonation, "
                              "slightly less stable).")
    parser.add_argument("--temperature", type=float, default=None,
                         help="Advanced: overrides --style. Higher = more expressive but less stable (XTTS default 0.65).")
    parser.add_argument("--top-p", type=float, default=None, dest="top_p",
                         help="Advanced: overrides --style (XTTS default 0.8).")
    parser.add_argument("--speed", type=float, default=None, help="Speech speed multiplier (default: 1.0).")
    parser.add_argument("--device", default=None, choices=["cpu", "cuda"],
                         help="Device to run inference on (default: auto-detect).")
    return parser.parse_args()


def ask(question, default, cast=str):
    raw = input(f"{question} [{default}] : ").strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except ValueError:
        print(f"Valeur non comprise, on garde la valeur par defaut : {default}")
        return default


def ask_speaker_files():
    raw = ask("Dossier ou fichier(s) audio de ta voix (separes par une virgule)", "samples")
    return resolve_speaker_files([Path(p.strip()) for p in raw.split(",") if p.strip()])


def ask_text():
    print("Tape ou colle le texte a faire lire, puis laisse une ligne vide pour terminer :")
    lines = []
    while True:
        line = input()
        if line == "":
            if lines:
                break
            continue
        lines.append(line)
    return "\n".join(lines)


def main():
    args = parse_args()
    interactive = len(sys.argv) == 1

    if interactive:
        print("=== Generation d'audio avec ta voix clonee ===")
        print("Reponds aux questions, ou appuie directement sur Entree pour garder la valeur par defaut.")
        print("Astuce : pointe --speaker vers un sous-dossier dedie a une emotion (ex: samples/joyeux) "
              "pour une voix plus fidele a cette emotion.\n")
        speaker_files = ask_speaker_files()
        text = ask_text()
        language = ask("Langue du texte", "fr")
        output = Path(ask("Nom du fichier audio a generer", "output.wav"))
        style = ask("Style de generation : normal ou expressif (plus d'emotion, un peu moins stable)", "normal")
        style = style.strip().lower()
        if style not in STYLE_PRESETS:
            print("Style non reconnu, utilisation de 'normal'.")
            style = "normal"
        tts_kwargs = dict(STYLE_PRESETS[style])
        device = None
        print()
    else:
        if not args.speaker:
            sys.exit("Erreur : --speaker est requis (fichier(s) ou dossier de reference).")
        if not args.text and not args.text_file:
            sys.exit("Erreur : utilise --text \"...\" ou --text-file chemin.txt.")
        speaker_files = resolve_speaker_files(args.speaker)
        text = args.text if args.text else args.text_file.read_text(encoding="utf-8")
        language = args.language or "fr"
        output = args.output or Path("output.wav")
        device = args.device
        tts_kwargs = dict(STYLE_PRESETS[args.style or "normal"])
        if args.temperature is not None:
            tts_kwargs["temperature"] = args.temperature
        if args.top_p is not None:
            tts_kwargs["top_p"] = args.top_p
        if args.speed is not None:
            tts_kwargs["speed"] = args.speed

    if not text.strip():
        sys.exit("Erreur : aucun texte a lire.")

    import torch
    from TTS.api import TTS

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Chargement du modele XTTS-v2 sur {device} (le premier lancement telecharge ~2 Go, patience)...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    print(f"Generation de {len(text)} caracteres en '{language}' a partir de {len(speaker_files)} "
          f"echantillon(s) : {', '.join(str(f) for f in speaker_files)}")
    if tts_kwargs:
        print(f"Parametres de generation : {tts_kwargs}")
    tts.tts_to_file(
        text=text,
        speaker_wav=[str(f) for f in speaker_files],
        language=language,
        file_path=str(output),
        **tts_kwargs,
    )
    print(f"Termine. Audio ecrit dans {output}")


if __name__ == "__main__":
    interactive_run = len(sys.argv) == 1
    try:
        main()
    except Exception as exc:
        print(f"\nUne erreur est survenue : {exc}")
    finally:
        if interactive_run:
            input("\nAppuie sur Entree pour fermer cette fenetre...")
