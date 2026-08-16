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
    "surprise": [
        "Quoi ? Je n'arrive pas a y croire, c'est vraiment toi qui as fait ca ?",

        "Attends, tu es serieux la ? Je ne m'attendais vraiment pas a ca, pas du tout !",

        "Waouh, je ne sais meme pas quoi dire, c'est completement inattendu.",

        "Ca alors, je n'aurais jamais imagine une chose pareille, jamais de la vie.",
    ],
    "peur": [
        "J'ai entendu un bruit bizarre dans le couloir, je n'ose meme pas bouger.",

        "Mon coeur bat tres vite, je crois que quelque chose ne va vraiment pas.",

        "Reste pres de moi, s'il te plait, j'ai vraiment peur la, tout de suite.",

        "Il fait tellement sombre ici, je n'aime pas du tout cet endroit, on s'en va.",
    ],
}

ADVANCED_CORPUS_SECTIONS = [
    ("Voyelles et sons", [
        "Papa a mange la banane a la cabane, la-bas.",
        "Il a fini ici, sans souci, avec Sissi.",
        "Une lune brune, tu as vu la brume ?",
        "Nous avons trouve la roue rouge sous la mousse rousse.",
        "Cet ete, mon frere a prefere rester chez lui.",
        "La fete bete d'Estelle a une jolie tete de mule.",
        "L'eau du seau coule sur le rocher, tot le matin.",
        "Le vent m'attend dans le grand champ, en attendant patiemment.",
        "Le pain de ce matin sent bon, plein de grains dores.",
        "Le pont s'effondre, on entend un long son profond.",
        "Un parfum brun flotte, chacun le trouve opportun.",
        "Deux jeunes peureux veulent du beurre et des oeufs frais.",
        "Le roi boit trois fois dans le foyer, quoi qu'il en soit.",
        "Depuis huit nuits, je suis dans la cuisine avec lui.",
        "Le soleil vermeil brille sur le portail et l'eventail.",
        "La montagne accompagne le peigne et la vigne du voisin.",
    ]),
    ("Consonnes et articulation", [
        "Paul a bu un bon bol de bouillon pres du port.",
        "Toto tond deux dindons dodus dans le jardin du domaine.",
        "Le coq gris gratte le gravier du grand quai gris.",
        "Fanny a vu vingt fauvettes voler vite au-dessus du fleuve.",
        "Suzanne a saisi six zestes de citron zeste avec soin.",
        "Charlotte cache jalousement ses chaussettes jaunes sous le lit.",
        "Le rire leger de Laura resonne, leger et rare a la fois.",
        "Manon nomme neuf noms de mammiferes marins connus.",
        "Le general range gentiment sa grange avec sa compagne.",
        "Xavier explique exactement pourquoi le taxi s'est arrete.",
    ]),
    ("Alphabet et epellation", [
        "A, B, C, D, E, F, G, H, I, J, K, L, M.",
        "N, O, P, Q, R, S, T, U, V, W, X, Y, Z.",
        "Maintenant l'alphabet a l'envers : Z, Y, X, W, V, U, T, S, R, Q, P, O, N.",
        "Voici comment on epelle un mot au telephone : A comme Anatole, B comme Berthe, "
        "C comme Celestine, D comme Desire.",
    ]),
    ("Nombres, dates et heures", [
        "Zero, un, deux, trois, quatre, cinq, six, sept, huit, neuf, dix.",
        "Onze, douze, treize, quatorze, quinze, seize, dix-sept, dix-huit, dix-neuf, vingt.",
        "Vingt et un, trente-deux, quarante-trois, cinquante-quatre, soixante-cinq.",
        "Soixante-seize, quatre-vingt-sept, quatre-vingt-dix-huit, cent.",
        "Deux cents, cinq cents, mille, dix mille, cent mille, un million.",
        "Premier, deuxieme, troisieme, quatrieme, cinquieme, dixieme, vingtieme.",
        "Il est huit heures et quart, puis neuf heures moins le quart, puis midi pile.",
        "Il est minuit et demi, puis une heure dix, puis deux heures moins cinq.",
        "Nous sommes le quinze mars deux mille vingt-quatre, un vendredi.",
        "Mon anniversaire est le sept juillet, en plein ete.",
        "Mon numero de telephone est le zero six, douze, trente-quatre, cinquante-six, soixante-dix-huit.",
        "Ca coute dix-neuf euros quatre-vingt-quinze, soit environ vingt euros.",
        "Le magasin annonce une reduction de trente pour cent sur tout le rayon.",
        "La reunion est prevue de quatorze heures a seize heures trente.",
    ]),
    ("Intonations et styles de parole", [
        "Est-ce que tu viens avec nous demain matin ?",
        "Tu es sur de toi, n'est-ce pas ?",
        "Quelle belle surprise, je n'en reviens pas !",
        "Ferme la porte et eteins la lumiere, s'il te plait.",
        "Non, je ne pense pas que ce soit une bonne idee.",
        "Oui, absolument, c'est exactement ce qu'il fallait faire.",
        "Euh... je ne sais pas trop, il faudrait que j'y reflechisse.",
        "Il me faut du pain, du beurre, des oeufs, du lait et du fromage.",
        "Si j'avais su, je serais parti plus tot ce matin-la.",
        "Il faudrait que tu viennes avant qu'il ne soit trop tard.",
        "Mesdames et messieurs, bienvenue a cette presentation officielle.",
        "Eh, salut toi, ca fait un bail qu'on s'est pas vus !",
        "Repete cette phrase tres vite, sans t'arreter, d'une traite.",
        "Maintenant, dis la meme phrase tres lentement, en detachant chaque mot.",
        "Dis cette phrase tres fort, comme si tu appelais quelqu'un de loin.",
        "Maintenant, dis la meme phrase tres doucement, presque a voix basse.",
        "Bonjour, comment allez-vous aujourd'hui ? J'espere que tout va bien pour vous.",
        "Salut, ca va ? Alors, quoi de neuf de ton cote ces derniers temps ?",
        "Peux-tu m'aider a porter ces sacs, s'il te plait, ils sont vraiment lourds ?",
        "Excusez-moi de vous deranger, pourriez-vous m'indiquer le chemin le plus proche ?",
    ]),
    ("Virelangues (articulation precise)", [
        "Un chasseur sachant chasser sait chasser sans son chien.",
        "Les chaussettes de l'archiduchesse sont-elles seches, archi-seches ?",
        "Si six scies scient six cypres, six cent six scies scient six cent six cypres.",
        "Cinq chiens chassent six chats a travers champs.",
        "Ces cerises sont si sures qu'on ne sait pas si s'en sont.",
        "Trois tortues trottaient sur trois toits tres etroits.",
        "Didon dina, dit-on, du dos d'un dodu dindon.",
        "Ton the t'a-t-il ote ta toux, tonton ?",
        "Natacha n'attacha pas son chat, ce qui facha Sacha.",
        "Je veux et j'exige d'exquises excuses.",
        "Douze douches douces dans une douzaine de douches.",
        "Poisson sans boisson est poison.",
    ]),
    ("Paragraphes longs (styles varies)", [
        "Il faisait nuit noire lorsque Julien poussa la porte grincante de la vieille "
        "maison. Le plancher craquait sous ses pas, et une odeur de poussiere flottait "
        "dans l'air. Il avanca lentement, une lampe torche a la main, cherchant la "
        "moindre trace de vie dans ce lieu abandonne depuis des annees. Soudain, un "
        "bruit sourd resonna a l'etage, le figeant sur place.",

        "Bonsoir a tous, voici les titres de cette edition. La municipalite a annonce "
        "ce matin la renovation complete du centre-ville, avec des travaux qui "
        "debuteront des le mois prochain. Du cote de la meteo, un temps ensoleille "
        "est attendu sur l'ensemble de la region pour les jours a venir. Nous "
        "reviendrons dans quelques instants avec un reportage complet sur ce sujet.",

        "Tu as vu l'heure qu'il est ? On va etre en retard ! Mais non, calme-toi, on "
        "a largement le temps. Tu dis toujours ca, et a chaque fois on court comme "
        "des fous. Cette fois, je te promets qu'on arrivera a l'heure, fais-moi "
        "confiance.",

        "Le soleil se couchait doucement derriere les collines, teintant le ciel de "
        "nuances orangees et roses. Un vent leger faisait bruisser les feuilles des "
        "arbres, tandis que les oiseaux regagnaient tranquillement leurs nids. Le "
        "calme du soir enveloppait peu a peu le paysage, comme une couverture douce "
        "et apaisante.",

        "Pour installer ce logiciel, commence par telecharger le fichier depuis le "
        "site officiel. Une fois le telechargement termine, double-clique sur le "
        "fichier pour lancer l'installation. Suis ensuite les instructions affichees "
        "a l'ecran, en acceptant les conditions d'utilisation lorsque cela t'est "
        "demande.",

        "Mon chat a decide, ce matin, qu'il etait hors de question de sortir de son "
        "panier avant midi. J'ai eu beau le supplier, le cajoler, meme lui promettre "
        "des croquettes en or, rien n'y a fait. Ce chat gouverne clairement cette "
        "maison, et je crois que j'ai simplement le droit d'y vivre.",

        "Decouvrez des aujourd'hui notre toute nouvelle gamme de produits, concue "
        "pour simplifier votre quotidien. Facile a utiliser, durable et abordable, "
        "elle repond a tous vos besoins. Profitez-en des maintenant, l'offre est "
        "valable pour une duree limitee seulement.",

        "Madame, Monsieur, je me permets de vous ecrire afin de vous faire part de "
        "ma candidature pour le poste que vous proposez. Fort de plusieurs annees "
        "d'experience dans ce domaine, je pense pouvoir apporter une reelle valeur "
        "ajoutee a votre equipe. Je reste a votre disposition pour tout entretien "
        "complementaire.",

        "Chers amis, nous voici reunis aujourd'hui pour celebrer un moment important. "
        "Ce projet, nous l'avons construit ensemble, pas a pas, avec patience et "
        "determination. Je tiens a remercier chacun d'entre vous pour votre "
        "engagement sans faille, car sans vous, rien de tout cela n'aurait ete "
        "possible.",

        "Il etait une fois, dans une foret tres lointaine, un petit renard qui "
        "n'avait peur de rien. Un jour, il rencontra un hibou tres sage, perche sur "
        "une branche. Le hibou lui dit : le vrai courage, ce n'est pas de n'avoir "
        "peur de rien, c'est d'avancer meme quand on a peur. Le petit renard n'oublia "
        "jamais cette lecon.",

        "Bonjour, vous etes bien sur le repondeur de Camille, je ne suis pas "
        "disponible pour le moment. Laissez-moi un message apres le signal sonore "
        "avec votre nom et votre numero, et je vous rappellerai des que possible. "
        "Merci beaucoup et a bientot.",

        "Et voila, le joueur recupere le ballon au milieu du terrain, il accelere, "
        "il elimine un premier adversaire, puis un deuxieme ! Il approche de la "
        "surface, il tire... et c'est but ! Quelle action magnifique, le public "
        "est en delire.",

        "Pour cette recette, commence par faire chauffer une casserole d'eau salee. "
        "Pendant ce temps, coupe les legumes en petits morceaux et fais-les revenir "
        "dans une poele avec un peu d'huile d'olive. Quand les pates sont cuites, "
        "melange le tout et ajoute une pincee de poivre avant de servir.",

        "Dors bien, mon petit, ferme doucement les yeux. Les etoiles veillent sur "
        "toi cette nuit, et demain sera un nouveau jour plein de belles decouvertes. "
        "Fais de beaux reves, et a demain matin.",

        "Bienvenue dans cette salle consacree aux peintres du dix-neuvieme siecle. "
        "Devant vous se trouve une oeuvre emblematique, peinte a l'huile sur toile, "
        "qui illustre parfaitement les techniques de l'epoque. Avancez de quelques "
        "pas pour decouvrir les details du tableau suivant.",

        "Je sais que la situation actuelle n'est pas facile pour tout le monde, "
        "mais je crois sincerement en notre capacite a surmonter cette periode. "
        "Ensemble, avec de la solidarite et de la perseverance, nous trouverons "
        "les solutions dont nous avons besoin. Ne baissons pas les bras.",

        "Je tenais a vous faire part de mon insatisfaction concernant la commande "
        "recue la semaine derniere. Le produit livre ne correspondait pas du tout "
        "a la description, et le delai annonce n'a pas ete respecte. J'attends une "
        "reponse rapide de votre part pour resoudre ce probleme.",
    ]),
    ("Mots et listes du quotidien", [
        "Lundi, mardi, mercredi, jeudi, vendredi, samedi, dimanche.",
        "Janvier, fevrier, mars, avril, mai, juin, juillet, aout, septembre, octobre, novembre, decembre.",
        "Le printemps, l'ete, l'automne et l'hiver.",
        "Rouge, orange, jaune, vert, bleu, violet, rose, marron, noir, blanc, gris.",
        "Mon pere, ma mere, mon frere, ma soeur, mes grands-parents, mes cousins.",
        "Boulanger, medecin, professeur, pompier, infirmiere, ingenieur, agriculteur.",
        "Le chien, le chat, l'oiseau, le poisson, le cheval, la vache, le mouton.",
        "La pomme, la banane, la fraise, le raisin, l'orange, la peche, le citron.",
        "Une chemise, un pantalon, une robe, des chaussures, un manteau, un chapeau.",
        "La voiture, le train, l'avion, le bateau, le velo, le bus, le tramway.",
        "La France, la Belgique, la Suisse, le Canada, le Senegal, la Tunisie.",
        "Paris, Lyon, Marseille, Bruxelles, Geneve, Montreal, Dakar.",
        "Grand et petit, chaud et froid, rapide et lent, facile et difficile.",
        "Heureux et triste, fort et faible, propre et sale, plein et vide.",
        "Je mange, tu manges, il mange, nous mangeons, vous mangez, ils mangent.",
        "Je vais, tu vas, il va, nous allons, vous allez, ils vont.",
        "J'aime lire, cuisiner, voyager, courir, dessiner et jardiner.",
        "Aujourd'hui, hier, demain, la semaine prochaine, le mois dernier, l'annee prochaine.",
        "La cuisine, le salon, la chambre, la salle de bain, le jardin, le garage.",
        "Un ordinateur, un telephone, une tablette, une television, une imprimante.",
        "Ecrire, lire, parler, ecouter, comprendre, expliquer, traduire.",
        "Merci beaucoup, de rien, avec plaisir, je t'en prie, pas de probleme.",
        "S'il te plait, excuse-moi, pardon, ce n'est pas grave, ne t'inquiete pas.",
        "Content, fatigue, occupe, malade, en forme, stresse, detendu.",
        "Ouvrir, fermer, allumer, eteindre, monter, descendre, entrer, sortir.",
        "Le matin, l'apres-midi, le soir, la nuit, tout au long de la journee.",
        "Petit dejeuner, dejeuner, gouter, diner, un bon repas en famille.",
        "A gauche, a droite, tout droit, en face, derriere, devant, a cote.",
    ]),
]


def build_advanced_corpus():
    """Flatten all advanced sections (plus every emotion sentence) into (category, text) pairs."""
    sections = list(ADVANCED_CORPUS_SECTIONS)
    emotion_items = [sentence for sentences in EMOTION_SENTENCES.values() for sentence in sentences]
    sections = sections + [("Emotions (toutes)", emotion_items)]
    return [(category, text) for category, sentences in sections for text in sentences]


def estimate_duration(text: str, words_per_minute: float = 120.0) -> int:
    """Rough recording duration for a line: comfortable (not rushed) reading pace, plus margin."""
    words = len(text.split())
    seconds = (words / words_per_minute) * 60 + 3
    return int(max(6, min(90, round(seconds))))


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
    parser.add_argument("--avance", action="store_true",
                         help="Mode avance : parcourt un corpus phonetique complet (~1h), ignore --count/--duration.")
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


def save_clip(sf, target, audio, samplerate, denoise):
    if denoise:
        print("Reduction du bruit de fond...")
        audio = reduce_background_noise(audio, samplerate)
    audio = trim_silence(audio, samplerate)
    speech_seconds = len(audio) / samplerate
    if speech_seconds < 3:
        print(f"Attention : seulement {speech_seconds:.1f}s de parole detectee (silence ou micro trop bas). "
              f"Tu peux refaire ce clip juste apres si besoin.")
    audio = normalize_loudness(audio)
    sf.write(str(target), audio, samplerate)
    status = "debruite, nettoye et normalise" if denoise else "nettoye et normalise"
    print(f"Enregistre dans {target} ({speech_seconds:.1f}s de parole, {status})")


def run_simple_mode(sd, sf, output_dir, prefix, count, duration, samplerate, denoise):
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)\.wav$")
    existing = [int(m.group(1)) for f in output_dir.iterdir() if (m := pattern.match(f.name))]
    start = max(existing, default=0) + 1
    sentence_bank = SUGGESTED_SENTENCES
    targets = [output_dir / f"{prefix}_{i:02d}.wav" for i in range(start, start + count)]

    for i, target in enumerate(targets):
        sentence = sentence_bank[(start - 1 + i) % len(sentence_bank)]
        print(f"\n--- Clip {i + 1}/{len(targets)} : {target} ---")
        print(f"Phrase suggeree (ou dis ce que tu veux) : \"{sentence}\"")
        input("Appuie sur Entree quand tu es pret(e)...")
        audio = record_clip(sd, duration, samplerate)
        save_clip(sf, target, audio, samplerate, denoise)

    print(f"\nTermine. {len(targets)} clip(s) enregistre(s) dans {output_dir}/")
    print("Tu peux relancer ce script plus tard pour ajouter d'autres clips sans ecraser ceux-ci.")


def run_advanced_mode(sd, sf, output_dir, prefix, samplerate, denoise):
    items = build_advanced_corpus()
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)\.wav$")
    existing = [int(m.group(1)) for f in output_dir.iterdir() if (m := pattern.match(f.name))]
    start = max(existing, default=0) + 1

    remaining = items[start - 1:]
    if not remaining:
        print(f"\nLe corpus avance complet ({len(items)} phrases) a deja ete enregistre dans {output_dir}/.")
        print("Pour recommencer une deuxieme passe, vide ou renomme ce dossier au prealable.")
        return

    total_seconds = sum(estimate_duration(text) for _, text in remaining)
    print(f"\nMode avance : {len(remaining)} phrases restantes sur {len(items)}, "
          f"soit environ {round(total_seconds / 60)} minutes d'enregistrement pur "
          f"(prevoir davantage avec les pauses entre les clips).")
    print("Tape 'q' puis Entree a tout moment pour t'arreter : ta progression est sauvegardee "
          "et tu pourras reprendre plus tard en relancant ce mode.\n")

    previous_category = None
    recorded = 0
    for offset, (category, sentence) in enumerate(remaining):
        i = start + offset
        target = output_dir / f"{prefix}_{i:02d}.wav"
        if category != previous_category:
            category_total = sum(1 for c, _ in items if c == category)
            print(f"\n=== Categorie : {category} ({category_total} phrases) ===")
            previous_category = category

        remaining_seconds = sum(estimate_duration(text) for _, text in remaining[offset:])
        print(f"\n--- Clip {i} (phrase {offset + 1}/{len(remaining)}, "
              f"~{round(remaining_seconds / 60)} min restantes) : {target} ---")
        print(f"A dire : \"{sentence}\"")
        ready = input("Appuie sur Entree quand tu es pret(e) (ou tape 'q' pour arreter la session)...")
        if ready.strip().lower() in ("q", "quit", "stop"):
            print(f"\nSession arretee. {recorded} phrase(s) enregistree(s) sur {len(items)}.")
            print(f"Relance le mode avance plus tard pour continuer a partir de la phrase {i}.")
            return

        duration = estimate_duration(sentence)
        audio = record_clip(sd, duration, samplerate)
        save_clip(sf, target, audio, samplerate, denoise)
        recorded += 1

    print(f"\nTermine ! Les {len(items)} phrases du corpus avance ont ete enregistrees dans {output_dir}/.")


def main():
    args = parse_args()
    interactive = len(sys.argv) == 1

    if interactive:
        print("=== Enregistrement d'echantillons de ta voix ===")
        print("Reponds aux questions, ou appuie directement sur Entree pour garder la valeur par defaut.\n")
        base_dir = Path(ask("Dossier de base ou enregistrer les fichiers", "samples"))
        mode_choice = ask(
            "Mode : simple (quelques clips au choix) ou avance "
            "(~1h, corpus phonetique complet et exhaustif)", "simple",
        )
        mode = mode_choice.strip().lower()
        if mode not in ("simple", "avance"):
            print("Mode non reconnu, utilisation de 'simple'.")
            mode = "simple"

        if mode == "avance":
            emotion = ""
            prefix = ask("Prefixe des fichiers", "avance")
            count = duration = None
        else:
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
        mode = "avance" if args.avance else "simple"
        emotion = args.emotion or ""
        prefix = args.prefix or ("avance" if mode == "avance" else "my_voice")
        count = args.count or 5
        duration = args.duration or 20
        denoise = not args.no_denoise

    if mode == "avance":
        output_dir = base_dir / "avance"
    else:
        output_dir = base_dir / normalize_label(emotion) if emotion else base_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    import sounddevice as sd
    import soundfile as sf

    if mode == "avance":
        run_advanced_mode(sd, sf, output_dir, prefix, args.samplerate, denoise)
    else:
        run_simple_mode(sd, sf, output_dir, prefix, count, duration, args.samplerate, denoise)

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
