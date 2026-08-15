#!/usr/bin/env python3
"""CLI tool to synthesize speech in a cloned voice using Coqui XTTS-v2.

Usage:
    python clone_voice.py --speaker samples/my_voice.wav --text "Bonjour, ceci est ma voix clonee."
    python clone_voice.py --speaker samples/my_voice.wav --text-file script.txt --language fr --output out.wav
"""
import argparse
import sys
from pathlib import Path

SUPPORTED_LANGUAGES = [
    "en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl",
    "cs", "ar", "zh-cn", "ja", "hu", "ko", "hi",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate speech in a cloned voice from a reference audio sample.")
    parser.add_argument("--speaker", required=True, type=Path,
                         help="Path to a reference audio file of the target voice (6-30s, wav/mp3/flac).")
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

    if not args.speaker.exists():
        sys.exit(f"Error: speaker reference file not found: {args.speaker}")

    text = args.text if args.text else args.text_file.read_text(encoding="utf-8")
    if not text.strip():
        sys.exit("Error: no text to synthesize.")

    import torch
    from TTS.api import TTS

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Loading XTTS-v2 model on {device} (first run downloads ~2GB, be patient)...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    print(f"Synthesizing {len(text)} characters in '{args.language}' using voice from {args.speaker}...")
    tts.tts_to_file(
        text=text,
        speaker_wav=str(args.speaker),
        language=args.language,
        file_path=str(args.output),
    )
    print(f"Done. Audio written to {args.output}")


if __name__ == "__main__":
    main()
