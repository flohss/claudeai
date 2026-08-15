#!/usr/bin/env python3
"""Record one or more reference voice samples from the microphone for clone_voice.py.

Recording several clips (different sentences, tones, paces) gives XTTS-v2 a
richer voice embedding and noticeably improves cloning quality compared to a
single sample.

Sans argument, le script pose les questions directement (utile en cas de
double-clic). Avec des arguments, il fonctionne comme avant :
    python record_sample.py --output-dir samples --count 5 --duration 20
"""
import argparse
import re
import sys
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
    parser.add_argument("--output-dir", type=Path, default=None,
                         help="Directory to save numbered clips into (default: samples/).")
    parser.add_argument("--prefix", type=str, default=None, help="Filename prefix for numbered clips.")
    parser.add_argument("--count", type=int, default=None, help="Number of clips to record (default: 5).")
    parser.add_argument("--duration", type=int, default=None, help="Duration per clip in seconds (default: 20).")
    parser.add_argument("--samplerate", type=int, default=24000, help="Sample rate in Hz.")
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


def record_clip(sd, duration, samplerate):
    print("Enregistrement dans 3 secondes. Parle naturellement et clairement.")
    sd.sleep(3000)
    print("Enregistrement en cours...")
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
    sd.wait()
    print("Enregistrement termine.")
    return audio


def main():
    args = parse_args()
    interactive = args.output_dir is None and args.prefix is None and args.count is None and args.duration is None

    if interactive:
        print("=== Enregistrement d'echantillons de ta voix ===")
        print("Reponds aux questions, ou appuie directement sur Entree pour garder la valeur par defaut.\n")
        output_dir = Path(ask("Dossier ou enregistrer les fichiers", "samples"))
        prefix = ask("Prefixe des fichiers", "my_voice")
        count = ask("Combien de clips veux-tu enregistrer", 5, int)
        duration = ask("Duree de chaque clip, en secondes", 20, int)
        print()
    else:
        output_dir = args.output_dir or Path("samples")
        prefix = args.prefix or "my_voice"
        count = args.count or 5
        duration = args.duration or 20

    import sounddevice as sd
    import soundfile as sf

    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)\.wav$")
    existing = [int(m.group(1)) for f in output_dir.iterdir() if (m := pattern.match(f.name))]
    start = max(existing, default=0) + 1
    targets = [output_dir / f"{prefix}_{i:02d}.wav" for i in range(start, start + count)]

    for i, target in enumerate(targets):
        sentence = SUGGESTED_SENTENCES[(start - 1 + i) % len(SUGGESTED_SENTENCES)]
        print(f"\n--- Clip {i + 1}/{len(targets)} : {target} ---")
        print(f"Phrase suggeree (ou dis ce que tu veux) : \"{sentence}\"")
        input("Appuie sur Entree quand tu es pret(e)...")

        audio = record_clip(sd, duration, args.samplerate)
        sf.write(str(target), audio, args.samplerate)
        print(f"Enregistre dans {target}")

    print(f"\nTermine. {len(targets)} clip(s) enregistre(s) dans {output_dir}/")
    print("Tu peux relancer ce script plus tard pour ajouter d'autres clips sans ecraser ceux-ci.")
    print(f"Prochaine etape : lance clone_voice.py en utilisant {output_dir}/ comme voix de reference.")


if __name__ == "__main__":
    interactive_run = len(sys.argv) == 1
    try:
        main()
    except Exception as exc:
        print(f"\nUne erreur est survenue : {exc}")
    finally:
        if interactive_run:
            input("\nAppuie sur Entree pour fermer cette fenetre...")
