# Éclipse — refaire le morceau dans Ableton Live

Tout ce qui suit est relevé directement dans le moteur de la page trance, pas
reconstitué de mémoire. Le fichier **`Eclipse.mid`** contient les notes ; ce
document contient les sons.

---

## 0. Si le MIDI seul sonne plat

C'est normal, et ce n'est pas une déception à corriger : **un fichier MIDI ne
transporte aucun son**. Il ne dit que quelle note, quand, et combien de temps.
Tout ce qui fait le caractère d'Éclipse est justement ce qu'il ne transporte pas.

Le morceau est volontairement pauvre en notes — 90 en dix mesures, une harmonie
qui ne bouge pas pendant huit temps. Ce qui remplit ce vide, ce sont quatre
réglages, et ils comptent dans cet ordre :

1. **Une réverbération de 4,2 secondes** en départ, généreusement dosée. C'est le
   plus gros écart à lui tout seul. Sans elle il ne reste que cinq lignes espacées.
2. **L'attaque de 900 ms sur la nappe.** L'accord *entre* au lieu de se poser.
   C'est ce qui fait qu'on ne sent plus le début des notes.
3. **La relâche de 2,2 s sur la nappe**, qui fait déborder chaque accord sur le
   suivant — l'harmonie devient continue.
4. **Le délai en croche pointée, 357 ms, retour 55 %**, avec le pluck à 50 % de
   départ. C'est le miroitement.

Faites ces quatre-là avant tout le reste : vous aurez l'essentiel en cinq
minutes. Les enveloppes de filtre, le sidechain et les faders affinent, ils ne
fondent pas le morceau.

Et pour ne pas travailler à l'aveugle, le dossier **`stems/`** contient le rendu
audio du morceau, piste par piste, tel que la page le joue. Posez le stem sur une
piste audio à côté de la piste MIDI correspondante : vous entendez la cible,
vous réglez votre Drift jusqu'à ce que les deux se confondent, puis vous coupez
le stem. C'est la façon la plus rapide d'approcher un son qu'on n'a pas construit
soi-même.

---

## 1. Le fichier MIDI

Glissez `Eclipse.mid` dans la vue Arrangement : Live crée **cinq pistes**, règle
le tempo à **126 BPM** et nomme chaque piste avec l'instrument à y poser —
*Lead - Drift Unison*, *Nappe - Drift Unison*, *Basse - Drift mono*,
*Pluck - Drift Unison*, *Batterie - Drum Rack*. Renommez-les à votre goût une
fois les instruments en place.

- 4/4, **10 mesures**, 90 notes.
- Trois **repères** marquent la structure : *Motif A* aux mesures 1 et 3,
  *Motif B* aux mesures 5 et 7, *Motif C* à la mesure 9.
- Chaque piste porte un **programme General MIDI** approchant, uniquement pour
  que le fichier s'écoute tel quel hors DAW. Live les ignore à l'import.
- La batterie est sur le **canal 10** avec les hauteurs General MIDI
  (36 grosse caisse, 39 clap, 42 charley fermé) : elle tombe juste dans un Drum
  Rack standard.
- Les hauteurs sont données en **numéros de note MIDI** dans ce document, parce
  que les conventions d'octave diffèrent d'un logiciel à l'autre. Live affiche
  par défaut Do3 = 60.

### Structure

L'original enchaîne trois motifs de deux mesures dans l'ordre **A A B B C**.

| Mesures | Motif | Ce qui entre |
| --- | --- | --- |
| 1–4 | A | Nappe seule, grosse caisse toutes les deux mesures |
| 5–8 | B | Le lead entre, le pluck aussi, charley aux temps 2 et 4 |
| 9–10 | C | Le clap remplace le charley, l'harmonie s'éclaire |

### Harmonie

**Ré mineur.** La nappe tient un accord entier par motif, deux mesures durant :

| Mesures | Accord | Notes MIDI |
| --- | --- | --- |
| 1–4 | Ré mineur | 50, 53, 57 |
| 5–8 | Si♭ majeur (1er renversement) | 50, 53, 58 |
| 9–10 | Fa majeur puis Do majeur | 53, 57, 60 puis 48, 52, 55 |

C'est le cœur du morceau : **une seule harmonie qui ne bouge pas pendant huit
temps**. Si vous ne deviez garder qu'une chose, c'est celle-là.

---

## 2. Les cinq instruments

Le moteur d'origine est soustractif : oscillateurs → filtre passe-bas résonant à
enveloppe → ampli.

Les quatre sons mélodiques emploient un **supersaw** : sept dents de scie
désaccordées en éventail symétrique autour de la fondamentale, avec compensation
de niveau.

### Avec quel synthé ?

**Toutes éditions, Intro et Lite comprises : `Drift`.** Il est livré avec Live
depuis la version 11.3, et il a les deux choses qui comptent ici — un mode de
voix **Unison**, qui empile quatre voix désaccordées par note, et un **filtre
résonant à enveloppe**. Un seul Drift par piste suffit.

L'original empile sept voix, Drift en empile quatre. À l'oreille, la différence
est mince ; si vous y tenez, mettez **deux Drift en Unison dans un Instrument
Rack** (présent dans Intro) et désaccordez le second de quelques centièmes.

**Standard et Suite** : `Wavetable` fait la même chose avec sept voix d'un coup
— Osc 1 sur une dent de scie, **Unison → Classic, 7 voix**, et le réglage
*Amount* dosé selon la colonne « désaccord » ci-dessous. `Analog` convient pour
la basse. Ces deux appareils **ne sont pas dans Intro** ni dans Lite.

Une correspondance à garder en tête dans tous les cas : la résonance des tableaux
ci-dessous est donnée en **Q**, comme dans le moteur d'origine, alors que Drift
l'exprime en pourcentage. Les valeurs de Q sont là pour ordonner les quatre sons
entre eux — le pluck est le plus résonant, la nappe le moins — plus que pour être
recopiées telles quelles.

### Nappe — la pièce maîtresse

| Réglage | Valeur |
| --- | --- |
| Oscillateur | Supersaw, 7 voix, désaccord **±32 centièmes** |
| Attaque | **900 ms** |
| Déclin | 1 200 ms |
| Maintien | 80 % |
| Relâche | **2 200 ms** |
| Filtre | Passe-bas 12 dB, coupure **1 258 Hz**, résonance moyenne (Q ≈ 4) |
| Enveloppe de filtre | ouvre jusqu'à **3 264 Hz**, retombe en **1 400 ms** |
| Départ réverb | 60 % |
| Départ délai | 12 % |
| Fader | **−4,4 dB** |

L'attaque de 900 ms est ce qui fait entrer la nappe en fondu au lieu de la poser.
Combinée à la relâche de 2,2 s et à une réverbération de 4,2 s, elle explique
pourquoi le morceau paraît plus lent qu'il n'est.

### Lead

| Réglage | Valeur |
| --- | --- |
| Oscillateur | Supersaw, 7 voix, désaccord ±22 centièmes |
| ADSR | 10 ms / 250 ms / 55 % / 350 ms |
| Filtre | Passe-bas, coupure **3 629 Hz**, résonance forte (Q ≈ 9) |
| Enveloppe de filtre | ouvre jusqu'à 16 kHz, retombe en 350 ms |
| Départs | réverb 32 %, délai 28 % |
| Fader | **−7,1 dB** |

### Basse

| Réglage | Valeur |
| --- | --- |
| Oscillateur | Une seule dent de scie, pas de désaccord |
| ADSR | 4 ms / 160 ms / 10 % / 80 ms |
| Filtre | Passe-bas, coupure **599 Hz**, résonance forte (Q ≈ 11) |
| Enveloppe de filtre | ouvre jusqu'à 3 629 Hz, retombe en **140 ms** |
| Départs | réverb 5 %, pas de délai |
| Fader | **−3,1 dB** |

### Pluck

| Réglage | Valeur |
| --- | --- |
| Oscillateur | Dent de scie, désaccord ±8 centièmes |
| ADSR | 2 ms / 180 ms / **0 %** / 140 ms |
| Filtre | Passe-bas, coupure 1 729 Hz, résonance très forte (Q ≈ 14) |
| Enveloppe de filtre | ouvre jusqu'à 16 kHz, retombe en 160 ms |
| Départs | réverb 45 %, **délai 50 %** |
| Fader | **−9,4 dB** |

Le maintien à zéro est ce qui en fait un pluck : la note meurt pendant que le
filtre se referme.

### Batterie

Trois voix seulement dans ce morceau, toutes de synthèse dans l'original :

| Voix | Note MIDI | Synthèse d'origine |
| --- | --- | --- |
| Grosse caisse | 36 | Sinus dont la hauteur chute de 160 à 45 Hz en 90 ms, plus un claquement de bruit de 20 ms |
| Clap | 39 | Trois éclats de bruit en passe-bande à 1,5 kHz espacés de 12 ms, puis une traîne de 220 ms |
| Charley fermé | 42 | Bruit en passe-haut à 7 kHz, extinction en 45 ms |

Fader **−1,9 dB**.

Rien n'oblige à les resynthétiser : les trois notes tombent aux hauteurs
General MIDI, donc n'importe quel Drum Rack de la bibliothèque de base répond
juste. La grosse caisse est le seul son qui gagne à être refait — un Drift en
sinus, une enveloppe sur la hauteur, et vous avez la chute de 160 à 45 Hz.

---

## 3. Le mixage

### Sidechain

Chaque piste se creuse à chaque grosse caisse, avec une **remontée de 300 ms**.
Dans Live : un **Compressor** sur chaque piste, entrée sidechain sur la piste de
batterie, release 300 ms. Les profondeurs d'origine :

| Piste | Creusement |
| --- | --- |
| Basse | **85 %** |
| Nappe | 75 % |
| Lead | 55 % |
| Pluck | 50 % |

C'est beaucoup pour la basse et la nappe : c'est voulu, le pompage fait partie
du morceau.

Si le routage sidechain vous résiste, il y a le vieux truc, qui marche dans
toutes les éditions : un **Auto Pan** avec les deux canaux en phase (Phase 0°)
ne panoramique plus, il module le volume. Synchronisé en croche, forme adoucie,
il pompe comme un sidechain sans avoir à router quoi que ce soit. Il pompe en
revanche *tout le temps*, y compris là où la grosse caisse ne joue pas — sur les
quatre premières mesures d'Éclipse, où elle ne frappe que deux fois par cycle,
ça s'entend.

### Départs communs

- **Réverb** : décroissance **4,2 s**. C'est la plus longue de toute la
  collection, et ce n'est pas un accident — c'est elle qui remplit le vide.
- **Délai** : croche pointée, soit **357 ms** à 126 BPM, retour **55 %**.
  Dans Live, réglez le Delay sur 3/16 en mode synchronisé.

### Master

Fader **−5,2 dB**, puis un **limiteur** : cinq pistes plus une réverbération de
quatre secondes dépassent vite le plein niveau.

---

## 4. Ce qu'il ne faut pas « améliorer »

Trois choses paraîtront trop simples et ne le sont pas :

1. **La grosse caisse ne joue que deux fois par cycle** dans les quatre premières
   mesures. Toute la tension vient de là.
2. **L'accord ne change pas pendant huit temps.** La tentation d'ajouter un
   mouvement harmonique tuerait le morceau.
3. **Il n'y a pas de montée de filtre.** Les autres morceaux du studio en ont
   une, celui-ci non — sa bande d'automation est vide.
