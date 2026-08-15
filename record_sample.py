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
import re
from pathlib import Path

SUGGESTED_SENTENCES = [
    "Bonjour, je m'appelle... et voici un echantillon de ma voix. "
    "Je l'enregistre pour entrainer un modele de clonage vocal, donc j'essaie de parler "
    "aussi naturellement que possible, comme dans une conversation normale.",

    "Le temps aujourd'hui est plutot agreable, avec un ciel degage et une legere brise. "
    "Ce genre de journee me donne envie de sortir me promener, peut-etre en foret ou "
    "le long de la riviere, pour profiter un peu du soleil.",

    "Pourrais-tu me dire quelle heure il est, s'il te plait ? J'ai l'impression d'avoir "
    "perdu la notion du temps depuis ce matin, et je ne voudrais surtout pas rater "
    "mon rendez-vous de cet apres-midi.",

    "J'aime beaucoup ecouter de la musique le soir en rentrant chez moi. Ca m'aide a "
    "decompresser apres une longue journee de travail, et parfois je me surprends "
    "meme a chantonner en preparant le diner.",

    "C'est incroyable a quel point la technologie a evolue ces dernieres annees. "
    "Il y a encore dix ans, personne n'aurait imagine qu'on pourrait un jour reproduire "
    "une voix humaine avec autant de precision.",

    "Attends, tu es serieux ? Je n'arrive pas a y croire ! Raconte-moi tout depuis le "
    "debut, je veux connaitre les moindres details, parce que la, franchement, "
    "tu m'as vraiment surpris.",

    "Un, deux, trois, quatre, cinq, six, sept, huit, neuf, dix. Lundi, mardi, mercredi, "
    "jeudi, vendredi, samedi, dimanche. Janvier, fevrier, mars, avril, mai, juin, "
    "juillet, aout, septembre, octobre, novembre, decembre.",

    "Merci beaucoup pour ton aide, ca me touche vraiment. Je ne sais pas ce que j'aurais "
    "fait sans toi ces derniers temps, et je tenais a te le dire, meme si je ne le "
    "montre pas toujours tres bien.",

    "Alors, on se retrouve demain a la meme heure, au meme endroit ? N'oublie pas "
    "d'apporter les documents dont on a parle la derniere fois, ce serait vraiment "
    "dommage de devoir tout reporter encore une fois.",

    "Je pense qu'il faut qu'on en discute calmement, sans se precipiter. Ce genre de "
    "decision merite qu'on prenne le temps de peser le pour et le contre, plutot que "
    "de se lancer tete baissee.",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Record microphone sample(s) to use as voice-cloning references.")
    parser.add_argument("--output", type=Path, default=None,
                         help="Output wav file path for a single recording (overrides --output-dir/--prefix).")
    parser.add_argument("--output-dir", type=Path, default=Path("samples"),
                         help="Directory to save numbered clips into (default: samples/).")
    parser.add_argument("--prefix", type=str, default="my_voice", help="Filename prefix for numbered clips.")
    parser.add_argument("--count", type=int, default=3, help="Number of clips to record (default: 3).")
    parser.add_argument("--duration", type=int, default=20, help="Duration per clip in seconds (15-25 recommended).")
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
        pattern = re.compile(rf"^{re.escape(args.prefix)}_(\d+)\.wav$")
        existing = [int(m.group(1)) for f in args.output_dir.iterdir() if (m := pattern.match(f.name))]
        start = max(existing, default=0) + 1
        targets = [args.output_dir / f"{args.prefix}_{i:02d}.wav" for i in range(start, start + args.count)]

    sentence_offset = (start - 1) if args.output is None else 0
    for i, target in enumerate(targets):
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"\n--- Clip {i + 1}/{len(targets)}: {target} ---")
        sentence = SUGGESTED_SENTENCES[(sentence_offset + i) % len(SUGGESTED_SENTENCES)]
        print(f"Suggested sentence (or say your own): \"{sentence}\"")
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
