#!/usr/bin/env python3
"""Record one or more reference voice samples from the microphone for clone_voice.py.

Recording several clips (different sentences, tones, paces) gives XTTS-v2 a
richer voice embedding and noticeably improves cloning quality compared to a
single sample.

Usage:
    python record_sample.py --output-dir samples --count 5 --duration 15
    python record_sample.py --output samples/my_voice.wav --duration 20   # single clip
"""
import argparse
from pathlib import Path

SUGGESTED_SENTENCES = [
    "Bonjour, je m'appelle... et voici un echantillon de ma voix.",
    "Le temps aujourd'hui est plutot agreable, avec un ciel degage.",
    "Pourrais-tu me dire quelle heure il est, s'il te plait ?",
    "J'aime beaucoup ecouter de la musique le soir en rentrant chez moi.",
    "C'est incroyable a quel point la technologie a evolue ces dernieres annees.",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Record microphone sample(s) to use as voice-cloning references.")
    parser.add_argument("--output", type=Path, default=None,
                         help="Output wav file path for a single recording (overrides --output-dir/--prefix).")
    parser.add_argument("--output-dir", type=Path, default=Path("samples"),
                         help="Directory to save numbered clips into (default: samples/).")
    parser.add_argument("--prefix", type=str, default="my_voice", help="Filename prefix for numbered clips.")
    parser.add_argument("--count", type=int, default=3, help="Number of clips to record (default: 3).")
    parser.add_argument("--duration", type=int, default=15, help="Duration per clip in seconds (10-20 recommended).")
    parser.add_argument("--samplerate", type=int, default=24000, help="Sample rate in Hz.")
    return parser.parse_args()


def record_clip(sd, duration, samplerate):
    print("Recording in 3 seconds. Speak naturally and clearly.")
    sd.sleep(3000)
    print("Recording...")
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
    sd.wait()
    print("Recording finished.")
    return audio


def main():
    args = parse_args()

    import sounddevice as sd
    import soundfile as sf

    if args.output is not None:
        targets = [args.output]
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        targets = [args.output_dir / f"{args.prefix}_{i + 1:02d}.wav" for i in range(args.count)]

    for i, target in enumerate(targets):
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"\n--- Clip {i + 1}/{len(targets)}: {target} ---")
        if i < len(SUGGESTED_SENTENCES):
            print(f"Suggested sentence (or say your own): \"{SUGGESTED_SENTENCES[i]}\"")
        input("Press Enter when ready...")

        audio = record_clip(sd, args.duration, args.samplerate)
        sf.write(str(target), audio, args.samplerate)
        print(f"Saved to {target}")

    print(f"\nDone. {len(targets)} clip(s) saved. Use them all for better quality, e.g.:")
    if args.output is not None:
        print(f"  python clone_voice.py --speaker {args.output} --text \"...\"")
    else:
        print(f"  python clone_voice.py --speaker {args.output_dir} --text \"...\"")


if __name__ == "__main__":
    main()
