# Synthés virtuels 🎹

Deux synthétiseurs jouables dans le navigateur, écrits en HTML/CSS/JavaScript pur avec l'API Web Audio — aucune dépendance, aucun build.

[`index.html`](index.html) est un **écran d'accueil** qui mène aux deux studios :

| Page | Genre | Moteur |
| --- | --- | --- |
| [`chiptune.html`](chiptune.html) | **Chiptune 8-bit** | Oscillateurs carré/pulse/triangle, bitcrusher, vibrato |
| [`trance.html`](trance.html) | **Trance** | Supersaw, filtre résonant à enveloppe, sidechain, réverbération, boîte à rythmes |

Les deux partagent la même architecture — séquenceur à motifs enchaînables, bibliothèque de morceaux, partage par URL, annuler/rétablir, export WAV — mais rien de leur synthèse. Chaque studio ramène au menu par un lien en haut de page.

## Utilisation

Ouvrez `index.html` dans un navigateur moderne (Chrome, Firefox, Edge, Safari), ou servez le dossier :

```bash
npx serve .
# ou
python3 -m http.server
```

## Trois pistes indépendantes

Dans le studio 8-bit, le séquenceur pilote **trois pistes** (Mélodie, Basse, Percu) qui jouent simultanément. Chaque piste possède son propre instrument complet — forme d'onde, octave, enveloppe ADSR, bitcrusher et vibrato — ainsi que son volume, son bouton muet et son solo.

Cliquer sur le nom d'une piste la sélectionne : les panneaux de réglage l'éditent alors, et le clavier la joue. Toucher un réglage bascule la piste en mode « Perso » sans altérer les autres.

## Sept morceaux fournis

La barre **Morceaux** charge un titre complet — motifs, chaîne, instruments, tempo et écho :

| Morceau | Tempo | Ambiance |
| --- | --- | --- |
| **Balade** | 120 | Majeur tranquille, arpèges et basse marchante |
| **Aventure** | 138 | Thème héroïque, progression I–V–vi–IV |
| **Donjon** | 100 | Mineur, mélodie cristalline noyée d'écho |
| **Course** | 176 | Doubles-croches continues, charleston serré |
| **Boss** | 152 | Chromatismes menaçants, basse en 4 bits |
| **Berceuse** | 76 | Très lent, sans percussion, écho long |
| **Engrenage** | 128 | Polyrythmie : boucles de 16, 12 et 10 pas qui se décalent |

**Vierge** repart d'une page blanche, et le bouton **Retour** du navigateur annule un chargement — l'état précédent est déposé dans l'historique avant d'être remplacé.

### Écrire son propre morceau

La bibliothèque est un simple tableau `SONGS` dans [`chiptune.html`](chiptune.html), lisible et modifiable à la main. Un motif s'écrit sur 16 caractères, un par pas, dans la même notation que les liens partagés :

```js
{
  name: "Aventure", bpm: 138, echo: [0.16, 0.18, 0.3], swing: 0.16, chain: "001102",
  tracks: [
    { preset: "leadgb", octave: 5, vol: 0.8, pats: [
      "0-4-7-c-b-9-7-4-", "579bc-b97-579---", "9--7--5-4--2--0-", ""] },
    { preset: "percu", octave: 3, vol: 0.7, len: 10, sweep: -18, pats: [
      "A-c-0-c-c-", …] }
  ]
}
```

`0123456789abc` valent Do, Do#, Ré… jusqu'au Do de l'octave supérieure, et `-` est un silence. Les **majuscules `A` à `M`** sont les mêmes hauteurs, accentuées — `b` est un Si, `B` un Do# accentué, jamais d'ambiguïté.

Une piste part d'un preset et peut en corriger n'importe quel réglage (`bits: 3`, `wave: "triangle"`, `sweep: -18`…), fixer sa longueur de boucle avec `len`, et le morceau règle son `swing`. `chain` donne l'ordre des motifs, ici A A B B A C.

## Le groove

Quatre réglages font sortir le séquenceur de la grille rigide :

- **Accents** — cliquez une case une fois pour poser une note, une deuxième pour l'accentuer (elle sonne nettement plus fort), une troisième pour l'effacer. La note accentuée porte un liseré clair et un point central.
- **Swing** — un curseur près du tempo qui retarde un pas sur deux, jusqu'à la moitié d'un pas. Quelques pourcents suffisent à faire respirer une boucle.
- **Longueur de boucle par piste** — le nombre à droite de chaque piste, de 1 à 16 pas. Donnez 16 à la mélodie, 12 à la basse et 10 à la percussion, et les trois ne se réalignent qu'au bout de 15 mesures : c'est la polyrythmie du morceau **Engrenage**. Les pas au-delà de la longueur sont estompés dans la grille, et chaque piste a sa propre tête de lecture.
- **Balayage de hauteur** — de −24 à +24 demi-tons parcourus sur la durée de la note. En négatif et court, c'est le « pew » descendant des percussions de NES ; en positif, un effet de montée.

## Quatre motifs enchaînés

Le séquenceur contient **quatre motifs de 16 pas**, nommés A à D. Les pistes gardent leurs instruments d'un motif à l'autre : changer de motif change ce qui est joué, jamais le son.

Deux modes de lecture :

- **Boucle** — le motif affiché tourne en rond, pour composer tranquillement.
- **Morceau** — la **chaîne** se déroule puis reprend. Chaque morceau de la bibliothèque en fournit une ; **Balade** joue par exemple `A A B C`, soit quatre mesures avec une variation et une accalmie.

Cliquez `+A`…`+D` pour ajouter un maillon, un maillon pour le retirer. Pendant la lecture, le maillon courant s'allume et le motif joué est cerclé ; si **Suivre** est actif, la grille se cale automatiquement sur le motif entendu. **Dupliquer** recopie le motif courant dans le premier emplacement libre — la façon rapide de partir d'une variation.

## Le studio

- **Enregistrement au clavier** — armez **Enreg. clavier** et jouez : pendant la lecture les notes sont quantifiées sur le pas le plus proche, à l'arrêt elles s'écrivent pas à pas sous un curseur. Les flèches ← et → reculent en effaçant ou avancent sans écrire. La seconde octave du clavier se replie dans l'octave du motif.
- **Outils de motif** — décaler la boucle d'un pas, transposer d'un demi-ton, inverser le motif. La transposition refuse plutôt que d'écraser : si une note devait sortir de la grille, rien ne bouge et un message le dit.
- **Annuler / Rétablir** — `Ctrl+Z` et `Ctrl+Maj+Z`, jusqu'à 60 pas en arrière. Les états sont conservés sous leur forme encodée, la même que celle de l'URL. Une entrée par changement stabilisé, pas par cran de curseur.
- **Export WAV** — le morceau est rendu dans un `OfflineAudioContext`, avec exactement le même graphe audio que le direct : le fichier est identique à ce qu'on entend, produit plus vite que sa durée. En mode morceau il couvre toute la chaîne, sinon quatre mesures, plus de quoi laisser mourir les relâches et l'écho.
- **Capturer** — l'ancien enregistrement en temps réel reste disponible pour saisir une improvisation au clavier.

## Partager un morceau

L'adresse de la page contient tout votre morceau. Chaque modification met à jour le fragment d'URL (sans polluer l'historique), et le bouton **Partager** copie le lien dans le presse-papiers — l'ouvrir restitue les quatre motifs, la chaîne, les instruments, le mixage, le tempo et l'écho à l'identique.

L'encodage est compact et lisible : chaque valeur est quantifiée puis écrite en base 36, et les 16 pas d'un motif tiennent en 16 caractères (un par hauteur, `-` pour un pas vide). Un morceau complet occupe environ 320 caractères :

```
#p=3.4o.1u.14.m.z.1.3.m.0.0.v~0012~2.5.5.28.n.c.5.1o.3.16.0.g.f.-47b047c959c7420…
   └ master : version, tempo, volume, écho, piste, arpège, motif, mode, swing
                              └ chaîne : A A B C
                                     └ piste : onde, octave, ADSR, bits, vibrato,
                                       volume, état, longueur, balayage,
                                       puis les 4 motifs bout à bout
```

Le décodage est tolérant : un lien tronqué, altéré ou d'une version inconnue retombe simplement sur le premier morceau de la bibliothèque, chaque valeur étant bornée à sa plage. Les liens produits par les versions précédentes restent lisibles : les champs apparus depuis reprennent leur valeur par défaut, et un lien de la toute première version voit son contenu atterrir dans le motif A.

## Fonctionnalités

- **6 formes d'onde chiptune** : carré 50 %, impulsion 25 %, impulsion 12,5 % (les classiques de la NES/Game Boy), triangle, dents de scie et bruit style console 8-bit.
- **Enveloppe ADSR** complète : attaque, déclin, maintien, relâche.
- **Bitcrusher** par piste : réduction de la résolution de 8 à 2 bits pour un grain rétro.
- **Vibrato** par piste : LFO avec vitesse et profondeur réglables (jusqu'à 6 demi-tons, effet sirène).
- **Écho rétro** (master) : delay avec mix, temps et feedback réglables, placé après les bitcrusher pour que les répétitions gardent le grain 8-bit.
- **Arpégiateur** : modes montant, descendant, aller-retour et aléatoire, vitesse réglable — maintenez plusieurs notes pour lancer l'arpège.
- **Séquenceur 4 motifs × 16 pas × 3 pistes** : mode boucle ou mode morceau avec chaîne de motifs, bande de résumé des trois pistes, piano-roll détaillé d'une octave avec les notes des autres pistes en repère, tempo 60–240 BPM et horloge audio précise (lookahead).
- **Groove** : accents par pas, swing jusqu'à 50 %, et longueur de boucle réglable piste par piste pour des polyrythmies.
- **Balayage de hauteur** par piste : −24 à +24 demi-tons sur la durée de la note.
- **5 presets** : Lead GB, Basse, Cristal, Percu, Sirène — applicables à la piste sélectionnée.
- **Bibliothèque de 7 morceaux** prêts à jouer, plus un emplacement vierge, écrits en clair dans le source.
- **Partage par URL** : le morceau complet — motifs, chaîne et réglages — tient dans le lien, restitué à l'identique à l'ouverture.
- **Export WAV** : rendu hors ligne du morceau complet, plus rapide que le temps réel.
- **Enregistrement au clavier** : écriture quantifiée pendant la lecture, ou pas à pas à l'arrêt.
- **Outils de motif** : décalage, transposition, inversion, avec annuler/rétablir sur 60 pas.
- **Capture en direct** : enregistre le mixage joué et exporte un `.webm`/`.ogg`.
- **Oscilloscope** temps réel, coloré selon la piste sélectionnée.
- **Clavier virtuel de 2 octaves** (souris et tactile, avec glissando) + sélecteur d'octave (0 à 7).
- **Polyphonie** illimitée.

## Clavier d'ordinateur

Le mappage utilise la position physique des touches, donc il fonctionne aussi bien en AZERTY qu'en QWERTY :

- **Rangée du milieu** (Q S D F G H J K L M en AZERTY) : touches blanches — Do, Ré, Mi, Fa, Sol, La, Si…
- **Rangée du haut** (Z E T Y U O P en AZERTY) : touches noires — Do#, Ré#, Fa#, Sol#, La#…
- **W / X** (en AZERTY) : octave −1 / +1
- **1 / 2 / 3** : sélectionner la piste
- **Espace** : lancer ou arrêter le séquenceur
- **Ctrl+Z** / **Ctrl+Maj+Z** : annuler, rétablir
- **← / →** (enregistrement armé) : reculer en effaçant, avancer sans écrire

## Le studio trance

[`trance.html`](trance.html) reprend l'architecture du séquenceur mais change tout le reste.

**Cinq pistes** : Lead, Nappe, Basse, Pluck et une **batterie de synthèse** (grosse caisse à hauteur descendante, clap en trois éclats, charleston fermé et ouvert, crash). La grille s'adapte : treize lignes de hauteurs pour les pistes mélodiques, cinq lignes de percussions pour la batterie.

**Le moteur** :

- **Supersaw** — sept dents de scie désaccordées en éventail symétrique autour de la fondamentale, avec compensation de niveau. C'est le timbre signature du genre.
- **Filtre résonant à enveloppe** — chaque note traverse son propre passe-bas qui s'ouvre puis retombe. Fréquence, résonance, montée et durée réglables : de quoi passer du pluck sec au lead qui s'ouvre.
- **Sidechain** — chaque coup de grosse caisse creuse le volume des pistes qui l'ont demandé, avec un temps de remontée global. C'est le pompage caractéristique, dosable piste par piste.
- **Réverbération à convolution** — la réponse impulsionnelle est un bruit décroissant généré à la volée, de 0,5 à 5 secondes.
- **Délai pointé de 3/16** — calé sur le tempo, avec retour réglable.
- **Panoramique** par piste.

**Motifs de 32 pas** (deux mesures), quatre motifs enchaînables, trois morceaux fournis — *Ascension* (138 BPM, uplifting), *Nébuleuse* (132, plus profond), *Orage* (142, agressif) — plus un emplacement vierge.

## Structure

Trois fichiers autonomes, sans dépendance ni build :

- [`index.html`](index.html) — l'accueil, avec une vignette animée par studio (onde carrée crantée d'un côté, dents de scie désaccordées de l'autre).
- [`chiptune.html`](chiptune.html) — le synthé 8-bit.
- [`trance.html`](trance.html) — le studio trance.

Chaque studio est un document séparé : leurs identifiants, leurs styles, leurs raccourcis clavier et leur contexte audio ne se marchent jamais dessus.
