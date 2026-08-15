#!/usr/bin/env python3
"""Record a reference voice sample from the microphone for use with clone_voice.py.

Usage:
    python record_sample.py --output samples/my_voice.wav --duration 20
"""
import argparse
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Record a microphone sample to use as a voice-cloning reference.")
    parser.add_argument("--output", type=Path, default=Path("samples/my_voice.wav"), help="Output wav file path.")
    parser.add_argument("--duration", type=int, default=20, help="Recording duration in seconds (10-30 recommended).")
    parser.add_argument("--samplerate", type=int, default=24000, help="Sample rate in Hz.")
    return parser.parse_args()


def main():
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    import sounddevice as sd
    import soundfile as sf

    print(f"Recording {args.duration}s of audio in 3 seconds. Speak naturally and clearly, "
          f"as if reading a short paragraph aloud.")
    sd.sleep(3000)
    print("Recording...")
    audio = sd.rec(int(args.duration * args.samplerate), samplerate=args.samplerate, channels=1)
    sd.wait()
    print("Recording finished.")

    sf.write(str(args.output), audio, args.samplerate)
    print(f"Saved reference sample to {args.output}")


if __name__ == "__main__":
    main()
