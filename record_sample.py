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
import unicodedata
from pathlib import Path

from audio_utils import normalize_loudness, reduce_background_noise, trim_silence

EMOTION_SENTENCES = {
    "joyeux": [
        "C'est genial, je n'aurais jamais imagine que ca se passerait aussi bien ! "
        "J'ai vraiment envie de faire la fete pour celebrer ca, tout de suite !",

        "Regarde, on a enfin reussi, apres tout ce temps a y travailler ! "
        "Je suis tellement content que j'en sourirais toute la journee.",

        "Youpi, c'est exactement la nouvelle que j'attendais depuis des semaines ! "
        "Il faut absolument qu'on partage ca avec tout le monde, c'est trop bien.",

        "Franchement, cette journee restera gravee dans ma memoire pour longtemps. "
        "Tout s'est enchaine a merveille, du matin jusqu'au soir, c'etait parfait.",
    ],
    "triste": [
        "Je ne sais pas trop quoi dire... c'est vraiment difficile a accepter, "
        "et j'ai l'impression que rien ne va pouvoir arranger les choses pour le moment.",

        "Ca me rend triste d'y repenser, meme si je sais que le temps va finir par "
        "attenuer un peu cette peine, ca reste dur en ce moment.",

        "J'aurais tellement voulu que ca se passe autrement, mais on ne peut pas "
        "toujours controler ce qui nous arrive, meme quand on fait de son mieux.",

        "Il y a des jours ou tout parait plus lourd que d'habitude, ou meme les "
        "petites choses du quotidien demandent un effort plus grand que d'habitude.",
    ],
    "colere": [
        "Non, mais serieusement, c'est inadmissible ! On ne peut pas continuer a "
        "accepter que les choses se passent comme ca, encore une fois.",

        "J'en ai vraiment assez de devoir tout repeter dix fois avant que quelqu'un "
        "ne m'ecoute, c'est franchement epuisant a la longue.",

        "Ca me met hors de moi quand les gens ne respectent meme pas les regles "
        "les plus elementaires, alors qu'on leur a explique plusieurs fois.",

        "Il est hors de question que je laisse passer ca sans rien dire, "
        "cette fois-ci, ca va vraiment trop loin.",
    ],
    "calme": [
        "Prends ton temps, il n'y a vraiment aucune urgence. On peut tres bien "
        "en reparler plus tard, une fois que tout le monde sera plus dispo.",

        "Respire un bon coup, tout va bien se passer. On va avancer etape par "
        "etape, sans se precipiter, et ca va tres bien se derouler.",

        "C'est une belle soiree calme, sans rien de particulier a faire, "
        "juste le plaisir de se poser tranquillement avec un bon livre.",

        "On a largement le temps devant nous, alors autant en profiter "
        "pour faire les choses correctement, sans stress inutile.",
    ],
}

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
                         help="Base directory to save numbered clips into (default: samples/).")
    parser.add_argument("--emotion", type=str, default=None,
                         help="Optional label (e.g. joyeux, triste, colere, calme). Saves clips into "
                              "<output-dir>/<emotion>/ with matching suggested sentences, for emotion-specific cloning.")
    parser.add_argument("--prefix", type=str, default=None, help="Filename prefix for numbered clips.")
    parser.add_argument("--count", type=int, default=None, help="Number of clips to record (default: 5).")
    parser.add_argument("--duration", type=int, default=None, help="Duration per clip in seconds (default: 20).")
    parser.add_argument("--no-denoise", action="store_true",
                         help="Skip automatic background noise reduction (denoising is on by default).")
    parser.add_argument("--samplerate", type=int, default=24000, help="Sample rate in Hz.")
    return parser.parse_args()


def normalize_label(label: str) -> str:
    stripped = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii")
    return stripped.strip().lower()


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
    interactive = len(sys.argv) == 1

    if interactive:
        print("=== Enregistrement d'echantillons de ta voix ===")
        print("Reponds aux questions, ou appuie directement sur Entree pour garder la valeur par defaut.\n")
        base_dir = Path(ask("Dossier de base ou enregistrer les fichiers", "samples"))
        emotion = ask(
            f"Etiquette emotion/style pour cette serie (options avec phrases dediees : "
            f"{', '.join(EMOTION_SENTENCES)} ; vide = neutre)", "",
        )
        prefix = ask("Prefixe des fichiers", "my_voice")
        count = ask("Combien de clips veux-tu enregistrer", 5, int)
        duration = ask("Duree de chaque clip, en secondes", 20, int)
        denoise_choice = ask("Reduire automatiquement le bruit de fond (recommande)", "oui")
        denoise = denoise_choice.strip().lower() not in ("non", "n", "no")
        print()
    else:
        base_dir = args.output_dir or Path("samples")
        emotion = args.emotion or ""
        prefix = args.prefix or "my_voice"
        count = args.count or 5
        duration = args.duration or 20
        denoise = not args.no_denoise

    output_dir = base_dir / normalize_label(emotion) if emotion else base_dir
    sentence_bank = EMOTION_SENTENCES.get(normalize_label(emotion), SUGGESTED_SENTENCES)

    import sounddevice as sd
    import soundfile as sf

    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)\.wav$")
    existing = [int(m.group(1)) for f in output_dir.iterdir() if (m := pattern.match(f.name))]
    start = max(existing, default=0) + 1
    targets = [output_dir / f"{prefix}_{i:02d}.wav" for i in range(start, start + count)]

    for i, target in enumerate(targets):
        sentence = sentence_bank[(start - 1 + i) % len(sentence_bank)]
        print(f"\n--- Clip {i + 1}/{len(targets)} : {target} ---")
        print(f"Phrase suggeree (ou dis ce que tu veux) : \"{sentence}\"")
        input("Appuie sur Entree quand tu es pret(e)...")

        audio = record_clip(sd, duration, args.samplerate)
        if denoise:
            print("Reduction du bruit de fond...")
            audio = reduce_background_noise(audio, args.samplerate)
        audio = trim_silence(audio, args.samplerate)
        speech_seconds = len(audio) / args.samplerate
        if speech_seconds < 3:
            print(f"Attention : seulement {speech_seconds:.1f}s de parole detectee (silence ou micro trop bas). "
                  f"Tu peux refaire ce clip juste apres si besoin.")
        audio = normalize_loudness(audio)
        sf.write(str(target), audio, args.samplerate)
        status = "debruite, nettoye et normalise" if denoise else "nettoye et normalise"
        print(f"Enregistre dans {target} ({speech_seconds:.1f}s de parole, {status})")

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
