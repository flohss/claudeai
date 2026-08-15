#!/usr/bin/env python3
"""CLI tool to synthesize speech in a cloned voice using Coqui XTTS-v2.

Usage:
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


def resolve_speaker_files(paths: list[Path]) -> list[Path]:
    """Expand a mix of files and directories into a flat, deduplicated list of audio files."""
    files = []
    for path in paths:
        if not path.exists():
            sys.exit(f"Error: speaker reference path not found: {path}")
        if path.is_dir():
            found = sorted(p for p in path.iterdir() if p.suffix.lower() in AUDIO_EXTENSIONS)
            if not found:
                sys.exit(f"Error: no audio files ({', '.join(AUDIO_EXTENSIONS)}) found in {path}")
            files.extend(found)
        else:
            files.append(path)
    # Deduplicate while preserving order.
    seen = set()
    unique_files = []
    for f in files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)
    return unique_files


def parse_args():
    parser = argparse.ArgumentParser(description="Generate speech in a cloned voice from one or more reference audio samples.")
    parser.add_argument("--speaker", required=True, type=Path, nargs="+",
                         help="One or more reference audio files, and/or a directory of them (6-30s each, wav/mp3/flac). "
                              "Providing several clips (different sentences/tones) improves cloning quality.")
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument("--text", type=str, help="Text to synthesize.")
    text_group.add_argument("--text-file", type=Path, help="Path to a text file to synthesize.")
    parser.add_argument("--language", default="fr", choices=SUPPORTED_LANGUAGES,
                         help="Language of the text (default: fr).")
    parser.add_argument("--output", type=Path, default=Path("output.wav"), help="Output audio file path.")
    parser.add_argument("--device", default=None, choices=["cpu", "cuda"],
                         help="Device to run inference on (default: auto-detect).")
    return parser.parse_args()


def main():
    args = parse_args()

    speaker_files = resolve_speaker_files(args.speaker)

    text = args.text if args.text else args.text_file.read_text(encoding="utf-8")
    if not text.strip():
        sys.exit("Error: no text to synthesize.")

    import torch
    from TTS.api import TTS

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading XTTS-v2 model on {device} (first run downloads ~2GB, be patient)...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    print(f"Synthesizing {len(text)} characters in '{args.language}' using {len(speaker_files)} "
          f"voice sample(s): {', '.join(str(f) for f in speaker_files)}")
    tts.tts_to_file(
        text=text,
        speaker_wav=[str(f) for f in speaker_files],
        language=args.language,
        file_path=str(args.output),
    )
    print(f"Done. Audio written to {args.output}")


if __name__ == "__main__":
    main()
