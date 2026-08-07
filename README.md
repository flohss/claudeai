# Synthés virtuels 🎹

Six instruments jouables dans le navigateur, plus une table de montage pour les réunir. Écrits en HTML/CSS/JavaScript pur avec l'API Web Audio — aucune dépendance, aucun build.

[`index.html`](index.html) est un **écran d'accueil** qui mène aux six studios et au montage :

| Page | Genre | Moteur |
| --- | --- | --- |
| [`chiptune.html`](chiptune.html) | **Chiptune 8-bit** | Oscillateurs carré/pulse/triangle, bitcrusher, vibrato |
| [`drums909.html`](drums909.html) | **House &amp; techno** | Dix voix de percussion synthétisées, saturation, filtre master |
| [`fm.html`](fm.html) | **FM** | Quatre opérateurs, huit algorithmes, rebouclage, chorus |
| [`trance.html`](trance.html) | **Trance** | Supersaw, filtre résonant à enveloppe, sidechain, réverbération |
| [`acid303.html`](acid303.html) | **Acid** | Monophonique, filtre 24 dB, glissando, accent, saturation |
| [`cordes.html`](cordes.html) | **Cordes pincées** | Modélisation physique : ligne à retard rebouclée, sans oscillateur |
| [`montage.html`](montage.html) | **Multipiste** | Table de mixage : réunit les rendus des six studios en un seul fichier |

Les six partagent la même architecture — séquenceur à motifs enchaînables, **bibliothèque de neuf morceaux** plus un emplacement vierge, partage par URL, annuler/rétablir, export WAV — mais rien de leur synthèse. Chaque studio ramène au menu par un lien en haut de page.

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

## Neuf morceaux fournis

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
| **Cascade** | 144 | Arpèges qui montent et retombent, basse tenue, percu en boucle de 12 |
| **Veillée** | 88 | Très lent, notes tenues sur quatre pas, sirène lointaine |

**Vierge** repart d'une page blanche, et le bouton **Retour** du navigateur annule un chargement — l'état précédent est déposé dans l'historique avant d'être remplacé.

### Écrire son propre morceau

La bibliothèque est un simple tableau `SONGS` dans [`chiptune.html`](chiptune.html), lisible et modifiable à la main. Un motif s'écrit sur 16 pas, dans la même notation que les liens partagés :

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

Un **accord** s'écrit entre parenthèses, précédé d'un `!` s'il est accentué : `(047)` est un Do majeur, `!(59c)` un Fa majeur accentué. Le groupe compte pour **un seul pas**. Comme une note isolée garde son écriture d'avant, les anciens motifs et les anciens liens se relisent sans changement.

Une piste part d'un preset et peut en corriger n'importe quel réglage (`bits: 3`, `wave: "triangle"`, `sweep: -18`…), fixer sa longueur de boucle avec `len`, et le morceau règle son `swing`. `chain` donne l'ordre des motifs, ici A A B B A C.

## Le groove

Quatre réglages font sortir le séquenceur de la grille rigide :

- **Accents** — la rangée **Acc.**, en tête de grille, accentue le pas entier : les notes concernées sonnent nettement plus fort et portent un liseré clair avec un point central. L'accent porte sur le pas, donc sur tout l'accord ; il tombe de lui-même quand la dernière note du pas est retirée.
- **Swing** — un curseur près du tempo qui retarde un pas sur deux, jusqu'à la moitié d'un pas. Quelques pourcents suffisent à faire respirer une boucle.
- **Longueur de boucle par piste** — le nombre à droite de chaque piste, de 1 à 16 pas. Donnez 16 à la mélodie, 12 à la basse et 10 à la percussion, et les trois ne se réalignent qu'au bout de 15 mesures : c'est la polyrythmie du morceau **Engrenage**. Les pas au-delà de la longueur sont estompés dans la grille, et chaque piste a sa propre tête de lecture.
- **Balayage de hauteur** — de −24 à +24 demi-tons parcourus sur la durée de la note. En négatif et court, c'est le « pew » descendant des percussions de NES ; en positif, un effet de montée.

## Les accords

Un pas ne porte plus une note mais **autant de hauteurs qu'on veut**. Un clic sur une case l'ajoute à son pas, un second l'en retire ; empiler trois cases dans la même colonne fait un accord. Ça vaut pour les studios 8-bit, trance et FM — la boîte à rythmes n'en a pas besoin, ses dix voix étant déjà des lignes indépendantes.

Au clavier, avec **Enreg. clavier** armé, la règle est celle d'un musicien : **une note encore tenue quand la suivante tombe rejoint le même pas**. Plaquez trois touches ensemble, vous obtenez un accord ; jouez-les l'une après l'autre, vous obtenez trois pas. Aucune fenêtre de temps n'intervient — une mélodie rapide reste une mélodie.

La transposition déplace l'accord entier, et refuse toujours plutôt que d'écraser : si une seule de ses notes devait sortir de la grille, rien ne bouge.

### Accords ou Mono

Le bouton **Accords**, dans la barre d'outils du séquenceur, bascule sur **Mono** : un pas ne retient plus qu'une hauteur, la note posée remplace celle qui occupait le pas, et les touches tenues ensemble ne se groupent plus. C'est le comportement d'avant, utile pour une ligne de basse ou de mélodie qu'on ne veut pas épaissir par mégarde.

Le mode ne touche **qu'à la saisie**. Un motif déjà écrit garde ses accords et continue de les jouer — passer en Mono n'efface jamais rien, il empêche seulement d'en créer. L'accent, lui, reste attaché au pas dans les deux modes.

C'est une préférence d'édition, pas une donnée du morceau : elle survit au chargement d'un titre de la bibliothèque, et elle voyage dans le lien partagé pour qu'un morceau rouvert reparte dans le mode où on l'a laissé.

Dans les morceaux fournis, les nappes de *Ascension*, *Nébuleuse* et *Orage* sont désormais de vraies triades, et le piano électrique de *Rhodes* enchaîne une progression accordée. Le studio 8-bit garde ses lignes monophoniques : c'est ce que faisaient les consoles, une voix par canal.

## La durée des notes

Chaque pas jouait une note de longueur fixe, un peu plus courte que le pas lui-même. Une nappe retombait donc avant le pas suivant : impossible de tenir un accord.

La rangée **Tenue**, sous la rangée d'accents, corrige ça. Un pas marqué *tenue* ne relance rien : il **prolonge la note précédente**. Trois pas tenus à la suite d'une note lui donnent quatre pas de long, et la grille dessine la note étirée sur toute sa durée, en retrait — on lit le rythme d'un coup d'œil.

Un pas ne peut pas à la fois poser une note et en prolonger une : marquer *tenue* sur un pas occupé est refusé avec un message, et poser une note sur un pas tenu annule sa tenue. Une tenue ne franchit pas la fin du motif — ni, dans le studio 8-bit, la longueur de boucle de la piste.

Une précision qui compte à l'oreille : la durée agit comme un **minimum**, pas comme un couperet. L'enveloppe de l'instrument va au bout de son déclin dans tous les cas ; la tenue ne peut qu'allonger une note, jamais l'écourter. Sur un timbre percussif — marimba, piano électrique — elle ne changera donc presque rien, ce qui est musicalement juste : un Rhodes décroît tout seul. Sur une nappe, un cuivre ou un orgue, la différence est franche. Mesurée sur le rendu WAV : le niveau efficace entre 1 et 1,4 seconde passe de 77 à 2083 avec douze pas tenus.

La batterie du studio trance n'a pas de rangée *Tenue* — prolonger un charleston n'a pas de sens, la version ouverte est déjà une voix à part.

Dans les liens partagés, un pas tenu s'écrit `=` : `(047)===` est un Do majeur qui dure quatre pas.

## Le balayage de filtre

Les réglages étaient figés pour tout un motif. Le geste central de la trance et de la techno — **le filtre qui se referme puis rouvre sur deux mesures** — était donc hors de portée.

Les studios [trance](trance.html) et [909](drums909.html) ont maintenant une **bande d'automation** sous la grille : une barre par pas, qu'on trace à la souris d'un seul glissé. Chaque point règle la coupure d'un **filtre passe-bas master**, placé après la réverbération et le délai — comme le filtre d'une table de mixage, il emporte tout le mixage, queues comprises.

Un point ne saute pas : le filtre **glisse jusqu'au point suivant** sur la durée d'un pas. Deux points éloignés suffisent donc à dessiner une longue montée, et une courbe dense donne un mouvement détaillé. Un pas sans point ne change rien : le filtre garde sa dernière valeur. Une bande entièrement vide laisse le son intact, filtre grand ouvert.

**Chaque motif a sa propre courbe** : A peut rester fermé pendant que B s'ouvre. Deux boutons complètent le tracé — **Ouvrir** met le motif à fond, **Vider** retire tous ses points.

La **résonance** du filtre master se règle dans le panneau Master (elle existait déjà sur la 909). C'est elle qui fait chanter le balayage plutôt que simplement l'assourdir.

Deux morceaux fournis s'en servent : le motif B d'*Orage* ouvre progressivement le filtre du grave à l'aigu — c'est la montée du morceau — et *Entrepôt* referme le filtre au milieu de chaque mesure avant de le rouvrir.

Dans les liens partagés, les courbes ferment le fragment, un caractère base 36 par pas et `-` pour un pas sans point. Elles sont ajoutées **à la fin** exprès : un lien produit avant leur existence se relit sans rien changer.

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

L'encodage est compact et lisible : chaque valeur est quantifiée puis écrite en base 36, un pas tient en un caractère (`-` pour un pas vide) et un accord entre parenthèses. Un morceau complet occupe environ 340 caractères :

```
#p=3.4o.1u.14.m.z.1.3.m.0.0.v~0012~2.5.5.28.n.c.5.1o.3.16.0.g.f.-47b047c959c7420_…
   └ master : version, tempo, volume, écho, piste, arpège, motif, mode, swing
                              └ chaîne : A A B C
                                     └ piste : onde, octave, ADSR, bits, vibrato,
                                       volume, état, longueur, balayage,
                                       puis les 4 motifs séparés par « _ »
```

Le décodage est tolérant : un lien tronqué, altéré ou d'une version inconnue retombe simplement sur le premier morceau de la bibliothèque, chaque valeur étant bornée à sa plage. Les liens produits par les versions précédentes restent lisibles : les champs apparus depuis reprennent leur valeur par défaut, un lien de la toute première version voit son contenu atterrir dans le motif A, et un lien d'avant les accords — sans le séparateur `_` — est redécoupé à longueur fixe. C'est vérifié page par page : les fragments produits par la version précédente rouvrent avec exactement la même grille, les mêmes accents et le même tempo.

## Fonctionnalités

- **6 formes d'onde chiptune** : carré 50 %, impulsion 25 %, impulsion 12,5 % (les classiques de la NES/Game Boy), triangle, dents de scie et bruit style console 8-bit.
- **Enveloppe ADSR** complète : attaque, déclin, maintien, relâche.
- **Bitcrusher** par piste : réduction de la résolution de 8 à 2 bits pour un grain rétro.
- **Vibrato** par piste : LFO avec vitesse et profondeur réglables (jusqu'à 6 demi-tons, effet sirène).
- **Écho rétro** (master) : delay avec mix, temps et feedback réglables, placé après les bitcrusher pour que les répétitions gardent le grain 8-bit.
- **Arpégiateur** : modes montant, descendant, aller-retour et aléatoire, vitesse réglable — maintenez plusieurs notes pour lancer l'arpège.
- **Séquenceur 4 motifs × 16 pas × 3 pistes** : mode boucle ou mode morceau avec chaîne de motifs, bande de résumé des trois pistes, piano-roll détaillé d'une octave avec les notes des autres pistes en repère, tempo 60–240 BPM et horloge audio précise (lookahead).
- **Groove** : accents par pas, swing jusqu'à 50 %, et longueur de boucle réglable piste par piste pour des polyrythmies.
- **Accords** : autant de hauteurs qu'on veut sur un même pas, à la souris ou au clavier — les touches encore tenues se groupent sur le pas courant. Un bouton **Accords / Mono** ramène le séquenceur à une note par pas quand on préfère.
- **Durée de note** : une rangée **Tenue** prolonge une note sur les pas suivants, pour les nappes tenues et les basses legato.
- **Balayage de filtre** : une bande d'automation par motif, tracée à la souris, qui pilote un filtre passe-bas master (trance et 909).
- **Balayage de hauteur** par piste : −24 à +24 demi-tons sur la durée de la note.
- **5 presets** : Lead GB, Basse, Cristal, Percu, Sirène — applicables à la piste sélectionnée.
- **Bibliothèque de 9 morceaux** prêts à jouer, plus un emplacement vierge, écrits en clair dans le source.
- **Partage par URL** : le morceau complet — motifs, chaîne et réglages — tient dans le lien, restitué à l'identique à l'ouverture.
- **Export WAV** : rendu hors ligne du morceau complet, plus rapide que le temps réel.
- **Enregistrement au clavier** : écriture quantifiée pendant la lecture, ou pas à pas à l'arrêt.
- **Outils de motif** : décalage, transposition, inversion, avec annuler/rétablir sur 60 pas.
- **Capture en direct** : enregistre le mixage joué et exporte un `.webm`/`.ogg`.
- **Export / import JSON** : le morceau entier dans un fichier texte lisible et modifiable à la main.
- **Info-bulles** : chaque paramètre explique son effet au survol et au focus clavier.
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

Le bouton **Lecture** figure deux fois : en tête de la section *Pistes*, et à sa place d'origine dans la barre du séquenceur, huit cents pixels plus bas. Les deux font la même chose et affichent toujours le même état — on ne remonte pas la page pour lancer la lecture.

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

**Motifs de 32 pas** (deux mesures), **accords** sur chaque pas et **notes tenues** — les nappes sont des triades tenues sur la mesure entière —, quatre motifs enchaînables, et **neuf morceaux fournis** plus un emplacement vierge :

| Morceau | Tempo | Ambiance |
| --- | --- | --- |
| **Ascension** | 138 | Uplifting classique, nappe majeure, montée franche |
| **Nébuleuse** | 132 | Plus profond et plus lent, réverbération longue |
| **Orage** | 142 | Agressif, filtre qui s'ouvre progressivement sur le motif B |
| **Aurore** | 140 | Majeur lumineux, pluck en arpèges, balayage de filtre sur la reprise |
| **Cavale** | 146 | Tendu, basse syncopée, le motif C referme le filtre avant la relance |
| **Éclipse** | 126 | Fa majeur ouvert sur son relatif mineur, très aéré, nappes tenues sur deux mesures |
| **Falaise** | 136 | Lead descendant en notes longues, montée de filtre sur le motif C |
| **Néon** | 144 | Rapide et sec, pluck en doubles-croches, filtre en creux |
| **Aube** | 120 | Le plus lent de la page, dans la veine d'*Éclipse* : la nappe fait tout |

## La boîte à rythmes 909

[`drums909.html`](drums909.html) synthétise **dix voix** de percussion, sans aucun échantillon :

| Voix | Synthèse |
| --- | --- |
| **BD** grosse caisse | Sinus dont la hauteur chute de cinq fois la fondamentale, plus un claquement d'attaque |
| **SD** caisse claire | Deux triangles inharmoniques mêlés à du bruit filtré en bande |
| **CP** clap | Trois éclats de bruit rapprochés puis une traîne, en passe-bande |
| **LT / MT / HT** toms | Sinus à hauteur descendante, avec une pointe de bruit |
| **RS** rimshot | Deux carrés très brefs, autour de 1,5 kHz |
| **CH / OH** charleys | Six carrés à rapports inharmoniques passés au passe-haut — la recette analogique |
| **CY** cymbale | Le même empilement, décroissance longue et passe-haut plus bas |

Chaque voix se règle en niveau, accord, chute, grain et départ réverb. Le pas-à-pas fait 16 temps, avec **accent** au deuxième clic, **shuffle** jusqu'à 55 %, et un **aléa** qui décale légèrement les frappes pour casser la rigidité machine.

Le master enchaîne **saturation** (courbe douce, jamais d'écrêtage net), **filtre résonant** balayable — au curseur ou à la bande d'automation —, réverbération courte, puis un **limiteur** : la résonance peut pousser le signal bien au-delà du plein niveau, et sans lui le rendu saturerait.

Neuf grooves fournis :

| Groove | Tempo | Caractère |
| --- | --- | --- |
| **Chicago** | 124 | House shufflée, clap sur le contretemps |
| **Detroit** | 134 | Techno en doubles-croches, rimshot continu |
| **Entrepôt** | 128 | Charleys ouverts, filtre qui se referme au milieu de la mesure |
| **Garage** | 132 | Shuffle marqué, charley chaloupé, caisse claire tardive |
| **Berlin** | 138 | Minimal, filtre bas et résonant, toms en fin de motif |
| **Rave** | 148 | Dur et rapide, charleys ouverts, cymbale sur les départs |
| **Sous-sol** | 122 | Shuffle lourd, grosse caisse en contretemps, rimshot isolé |
| **Marteau** | 150 | Le plus dur : saturation forte, charleys pleins, cymbale à l'entrée |
| **Cassure** | 134 | Breakbeat, grosse caisse déplacée, toms en fin de motif |

## Le synthé FM

Les trois autres moteurs sont *soustractifs* : on part d'une onde riche et le filtre lui enlève des choses. [`fm.html`](fm.html) fonctionne à l'envers — **un oscillateur module la fréquence d'un autre**, et le timbre naît de leur rapport. C'est la seule famille de synthèse de la collection où le filtre ne joue aucun rôle.

**Quatre opérateurs**, chacun avec son rapport de fréquence, son niveau, son désaccord fin et son enveloppe ADSR complète. Un rapport entier donne un son harmonique, un rapport fractionnaire le rend inharmonique : c'est toute la différence entre un piano électrique et une cloche.

**Huit algorithmes** décrivent qui module qui :

| Algorithme | Câblage | Caractère |
| --- | --- | --- |
| **Pile** | 4→3→2→1 | Métallique, agressif |
| **Double** | 4→3→1, 2→1 | Deux couleurs sur une porteuse |
| **Y** | 3→2→1, 4→1 | Corps plus complexe |
| **2 paires** | 2→1, 4→3 | Le piano électrique classique |
| **Paire+2** | 2→1, plus deux sinus purs | Doux, hybride |
| **Étoile** | 4 module 1, 2 et 3 | Trois voix liées |
| **Pile+1** | 3→2→1, plus un sinus | Attaque nette sur fond pur |
| **Additif** | aucune modulation | Orgue, quatre sinus empilés |

Le **diagramme s'affiche à l'écran** : les opérateurs se placent par étage selon leur profondeur de modulation, les flèches montrent le sens, et un liseré jaune marque ceux qui sortent vraiment du son. Le **rebouclage** ramène le dernier opérateur sur lui-même — Web Audio interdisant les boucles sans retard, une ligne à retard d'un bloc la rend légale.

La profondeur de modulation suit la fréquence du modulateur, de sorte que **le timbre reste le même d'un bout à l'autre du clavier** au lieu de devenir criard dans l'aigu.

Six presets — Piano él., Cloche, Marimba, Basse FM, Cuivre, Verre — et neuf morceaux :

| Morceau | Tempo | Caractère |
| --- | --- | --- |
| **Rhodes** | 96 | Piano électrique, progression en accords plaqués |
| **Carillon** | 78 | Cloches inharmoniques et marimba |
| **Fanfare** | 128 | Cuivres en algorithme Y, basse FM appuyée |
| **Verre** | 84 | Timbres de verre tenus, cloches espacées, très réverbéré |
| **Poursuite** | 132 | Cuivres en accords courts, marimba rapide, basse continue |
| **Choral** | 66 | Quatre accords tenus une mesure chacun, presque un orgue |
| **Tubulaire** | 72 | Cloches tenues et verre lointain, très peu de notes |
| **Vapeur** | 92 | Piano électrique en triades, marimba sur le contretemps |
| **Rouages** | 148 | Marimba mécanique, cuivres en réponse, basse martelée |

C'est la page où les **accords** comptent le plus : un piano électrique qui ne sait pas plaquer une triade, ce n'est pas un piano électrique.

## Écrire avec une gamme, et faire proposer la suite

Le séquenceur savait éditer ; il ne savait rien suggérer. Deux commandes changent ça, dans les quatre studios mélodiques.

### Le guide de gamme

Choisissez une **tonique** et un **mode** — majeur, mineur naturel ou harmonique, les quatre modes anciens, pentatonique mineure, blues. Les rangées de la grille qui n'appartiennent pas à la gamme **s'effacent sans disparaître** : elles restent cliquables, et une note déjà écrite là garde toute sa couleur. Une note hors gamme n'est pas une faute, c'est une information.

En *fa majeur*, il ne reste que huit rangées éclairées sur treize. Écrire juste devient une affaire de viser ce qui brille.

**Dans la gamme** ramène chaque note du motif sur le degré le plus proche — à égale distance, elle monte. Accents et tenues sont conservés : seules les hauteurs bougent. Ctrl+Z annule.

Ce réglage est une paire de lunettes, pas de la musique : il n'entre **ni dans le lien partagé ni dans le JSON**, et se retient d'une visite à l'autre.

### Réponse

**Réponse** écrit dans un motif libre la phrase qui répond à celle en cours : même rythme, mêmes accents, mêmes tenues, mais le dessin mélodique **retourné autour de sa première note**, puis ramené dans la gamme, la dernière note revenant sur la tonique.

C'est l'**inversion**, un procédé d'écriture, pas un tirage au sort : la réponse est toujours parente de la question. `Ré Sol Do` donne `Ré La Do` — le saut de quarte vers le haut devient un saut de quinte vers le bas.

Un détail qui décide de tout : le miroir sort souvent de la grille de treize rangées. Il est **replié par octaves**, jamais rogné. Rogner ferait un unisson là où l'inversion demandait une sixte, et la réponse ne ressemblerait plus à rien.

La 909 n'a pas ces commandes — elle n'a pas de hauteurs — et sur la piste de batterie du studio trance, les deux boutons répondent « piste rythmique » plutôt que d'abîmer le motif.

## Une suite d'accords en degrés

À côté du guide de gamme, un menu de progressions toutes prêtes, une case de degrés modifiable et un bouton. `6 4 1 5` en fa majeur écrit `vi IV I V` — c'est-à-dire, note pour note, l'harmonie d'*Éclipse*.

Les triades ne viennent pas d'une table de qualités : elles s'**empilent en tierces de la gamme**. Le degré porte donc sa qualité tout seul — mineure sur ii, iii et vi d'un majeur, diminuée sur vii — et changer de mode change les accords sans qu'une ligne de code s'en occupe. Les mêmes `1 4 5` donnent Fa Si♭ Do en fa majeur et Rém Solm Lam en ré mineur.

Les altérations s'écrivent selon la tonalité : en fa majeur, la note entre La et Si s'affiche **Si♭**, pas La#.

La progression se répartit sur toute la longueur du motif, en triades tenues, et remplace ce qui s'y trouvait — Ctrl+Z annule.

## Créer, compléter, sublimer

Le studio trance a trois boutons qui écrivent. Ce sont **le même algorithme**, un recuit simulé sous contraintes ; seuls changent le point de départ et ce qu'on s'interdit de toucher.

| Bouton | Point de départ | Gelé |
| --- | --- | --- |
| **Créer** | rien | rien |
| **Compléter** | ce que vous avez écrit | vos notes |
| **Sublimer** | le motif entier | rien, la densité est la sienne |

La recherche essaie des milliers de retouches — une hauteur déplacée d'un degré, une note glissée dans le temps, deux hauteurs échangées — garde ce qui améliore, et **accepte parfois ce qui dégrade**, de moins en moins souvent à mesure que la température baisse. C'est ce qui lui permet de traverser une vallée pour trouver mieux, là où l'ancien bouton *Variante* s'arrêtait au premier creux.

Le réseau note chaque proposition. Deux préférences s'ajoutent, que le réseau ne peut pas connaître : les hauteurs de **l'accord en cours sur les autres pistes** tirent les temps forts, et les sauts de plus d'une quinte sont pénalisés.

**Le biais vers le silence est neutralisé par construction** : la densité est fixée avant la recherche et aucune retouche ne la change, si bien que toutes les propositions comparées ont le même nombre de notes. C'est la leçon de [`recherche/`](recherche/), appliquée.

En ré mineur, *Créer* sort par exemple `Ré Ré Si♭ Ré Si♭ La Si♭ La` — tonique, sixte bémol, quinte. Chercher trois fois plus longtemps fait tomber la note de 0,41 à 0,29 : la recherche progresse vraiment, elle ne tourne pas en rond.

### Un morceau entier

Un quatrième bouton, **Morceau**, écrit tout : les cinq pistes, trois motifs, et la chaîne qui les enchaîne. Un clic sur un onglet vierge et il y a une musique.

L'ordre d'écriture est celui d'un arrangeur, et il n'est pas décoratif. La **nappe** passe en premier et pose la progression de la case des degrés — la même dans les trois motifs, c'est ce qui en fait un morceau plutôt que trois idées côte à côte. La **basse** vient ensuite : la fondamentale est posée puis **gelée** sur chaque changement d'accord, et le recuit ne cherche qu'autour. Le **pluck** et le **lead** enfin, qui brodent dessus. Comme la fonction de coût récompense les notes de l'accord du moment sur les temps forts, chaque couche est composée **en entendant les précédentes** — dans son propre motif, pas dans celui qui se trouve à l'écran.

La **batterie** ne passe pas par le réseau : sans hauteurs, il n'aurait rien à apprendre. Elle suit les règles du genre et monte d'un motif à l'autre — grosse caisse une mesure sur deux puis quatre au sol, clap sur les contretemps, charleys qui se densifient, cymbale à l'arrivée des motifs pleins.

Trois motifs, donc, enchaînés **A A B B C B** : A pose le décor à la nappe et à la basse, B ouvre, C tend. Mesuré sur le rendu WAV, découpé au tempo, l'énergie suit : `0,060 · 0,073 · 0,078 · 0,079 · 0,082 · 0,079`. A est bien le plus léger, C bien le sommet.

### Il tire une intention

Premier jet, le bouton écrivait toujours **le même morceau**. Mesuré plutôt que supposé : six morceaux d'affilée donnaient une seule tonalité, une seule progression, un seul tempo, et — Jaccard sur les cases posées — une nappe identique à `1,00` et une batterie identique à `1,00`. Les couches mélodiques, elles, variaient déjà beaucoup (`0,03`) : le recuit explore. Mais elles reposaient toutes sur le même lit harmonique et rythmique, et c'est le lit qu'on entend.

Avant d'écrire la moindre note, le bouton tire donc une **intention** : tonalité et mode (mineur, dorien, phrygien, harmonique, majeur, pondérés), progression, tempo, swing, forme de l'arrangement parmi six, style de nappe (tenue, pompe, stabs, relance), densités, et un **caractère rythmique par couche** — carré, croches, contretemps, galop, syncope. Ce caractère est un bonus par position dans les deux temps, ajouté au coût : c'est ce qui distingue une basse carrée d'une basse en galop à hauteurs et à densité égales, donc exactement ce que le réseau — qui juge le style *moyen* des neuf morceaux — ne saurait pas demander tout seul.

S'y ajoute un terme d'**écart** : une couche est composée en s'éloignant de ce qui est déjà écrit — les autres couches du même motif, pour ne pas frapper toutes ensemble, et le même instrument dans les autres motifs, pour que B ne redise pas A. C'est de la recherche de nouveauté, au même titre que la recherche de style.

La batterie est faite de **figures** — des listes de pas — et non de modulos, et son charley respire : quelques coups ôtés, quelques doubles ajoutés entre les temps.

**Ce que vous avez réglé n'est pas tiré au sort.** Gamme, degrés, tempo, swing : si vous y avez touché, le bouton s'y plie, au premier clic comme au dixième.

Il a fallu **deux mécanismes**, parce qu'aucun ne suffit seul.

Une **trace de ce que le bouton a lui-même posé** : un réglage qui ne vaut plus ce qu'il y avait mis est le vôtre. C'est ce qui rattrape les liens partagés et les fichiers importés, qui changent la valeur sans déclencher le moindre événement. La trace ne retient que ce qu'il a *tiré*, jamais ce qu'il a respecté — sinon il le reprendrait pour sien au clic suivant, et votre choix ne durerait qu'un morceau.

Et un **guet du geste**, parce qu'un geste ne change pas toujours la valeur : si le bouton tire `1 4 5 1` et que vous écrivez ensuite la même chose, il n'y voit que sa propre trace intacte. `setSlider` annonce donc qu'il écrit, pour que les valeurs qu'il pose lui-même ne repassent pas pour les vôtres — c'est ce qui manquait à la première version, qui guettait `input` sans réserve et croyait que vous aviez choisi le tempo qu'elle venait de tirer. Charger un morceau efface ces choix : ils portaient sur un autre morceau.

| | avant | après |
| --- | --- | --- |
| tonalités distinctes sur 8 | 1 | 7 |
| progressions distinctes | 1 | 4 |
| tempos distincts | 1 | 7 |
| ressemblance nappe | 1,00 | 0,17 |
| ressemblance batterie | 1,00 | 0,49 |
| **ressemblance d'ensemble** | **0,64** | **0,16** |

La batterie reste la plus ressemblante, et c'est juste : la grosse caisse de trance est quatre au sol et le restera. Deux paires toutes deux muettes ne comptent pas comme identiques — ce serait tenir un accord parfait entre deux silences pour de la redite.

**Sans gamme choisie, il en choisit une.** La première version refusait de travailler tant qu'on ne lui avait pas réglé une gamme à sept degrés — or la gamme par défaut est chromatique, si bien qu'un clic sur un onglet neuf ne faisait rien du tout et que le message d'alerte s'effaçait avant qu'on ait pu le lire. Il déduit désormais la tonalité de ce qui est déjà écrit : la gamme qui accueille le plus de notes, la tonique et sa quinte départageant les relatives, qui contiennent exactement les mêmes notes. Page blanche, ce sera mineur — le ton du genre.

L'apprentissage, enfin, **rend compte au bouton qui l'a demandé**. `rEntrainer` datait du temps où *Variante* était seul à s'en servir et écrivait sa progression sur ce bouton-là, quel qu'ait été le clic. Un clic sur *Morceau* laissait donc *Variante* figé sur `Apprend 92 %` — la dernière valeur affichée, la douzième époque appelant la suite sans repasser par l'affichage — et rien ne le rendait, puisque seul son propre gestionnaire savait le faire. Le test regarde désormais les cinq boutons à la fois : celui qu'on clique, et les quatre autres, qui ne doivent pas bouger d'un caractère.

### Il apprend de vous

Le corpus n'est pas seulement les neuf morceaux fournis : **vos propres motifs y entrent, à poids triple**. Neuf morceaux contre quatre motifs à vous, la moyenne les noierait — ce serait apprendre le style de la page et pas le vôtre.

Les poids sont rangés sous une **empreinte de ce que vous avez écrit**. Changer de matériel redemande donc un apprentissage de quelques secondes ; revenir à un motif d'avant retrouve les poids d'avant sans rien recalculer.

## Le réseau qui juge

Le studio trance a un bouton **Variante**. Il ne compose pas : il **choisit**.

Un perceptron à une couche cachée — propagation avant, rétropropagation et Adam écrits à la main, aucune bibliothèque — s'entraîne sur les **neuf morceaux déjà dans la page**, augmentés par transposition. Rien n'est téléchargé, rien n'est appelé au dehors. Quatre secondes au premier clic, puis les poids restent dans le navigateur.

Le bouton fabrique une quinzaine de variantes musicales du motif — une note déplacée d'un degré, le motif décalé dans le temps, une note avancée ou retardée — et garde celle que le réseau trouve la plus proche du style du corpus. Sur le motif A d'*Ascension*, il avance la note du temps fort d'un seizième : une syncope, figure fréquente dans les neuf morceaux. Au clic suivant il annonce qu'aucune variante ne fait mieux — il a convergé.

Les variantes se déplacent **par degrés de la gamme**, jamais par demi-tons : une note monte au degré suivant, pas au demi-ton suivant. Sans gamme choisie, elles se limitent aux hauteurs déjà présentes dans le motif. Une première version déplaçait d'un demi-ton puis « recollait » sur la gamme — sans gamme active, elle posait donc des notes étrangères à tous les coups. Vérifié depuis sur quatre gammes et trois morceaux : zéro note hors gamme après trois passages, densité conservée.

**Pourquoi juger et non composer**, c'est [`recherche/`](recherche/) qui l'explique, mesures à l'appui : le réseau bat nettement une chaîne de Markov en prédiction, mais laissé à écrire seul il pose une note puis se tait. Les trois quarts des pas d'un motif sont des silences, donc prédire « silence » suffit à bien mesurer, et le modèle s'y enfonce.

Le même biais a resurgi dans le juge : la première version proposait « une note en moins » parmi les variantes, et le réseau la choisissait à tous les coups — retirer une note améliore toujours une surprise moyenne. **Toutes les variantes gardent maintenant le même nombre de notes**, et la comparaison redevient honnête.

## Un LFO par piste

Dans le studio trance, chaque piste a son oscillateur lent, **calé sur le tempo** : la vitesse se donne en valeurs de note, de la double-croche à quatre mesures, et suit le morceau si le tempo change.

Trois destinations :

- **Filtre** — jusqu'à deux octaves de balayage, en centièmes de ton pour rester musical d'un bout à l'autre du clavier. C'est le geste signature du genre, celui qui demandait jusqu'ici de dessiner la bande d'automation à la main, motif par motif.
- **Hauteur** — jusqu'à un demi-ton : le vibrato.
- **Volume** — le trémolo, dont le repos descend d'autant que la profondeur monte, pour que le sommet reste le niveau nominal.

Éteint, il ne laisse aucune trace : le rendu retrouve l'échantillon près le fichier d'origine.

Le réglage voyage dans le lien partagé et dans le JSON, et un lien d'avant se relit sans perdre quoi que ce soit.

## L'interface dit ce qu'on entend

Deux réglages pouvaient rendre un morceau méconnaissable sans que rien ne le signale. Un fichier réel l'a montré : deux pistes sur cinq à zéro, deux autres calées à fond à droite, et une console qui n'en laissait rien voir.

- **Chaque rangée de la table de mixage affiche son niveau**, en pour cent. À zéro, elle affiche **muet** en couleur d'alerte et s'éteint comme une piste rendue muette — parce que c'est la même surdité. Là où les pistes ont un panoramique, un **G** ou un **D** apparaît dès qu'elle est calée franchement d'un côté.
- **Les panneaux qui n'agissent pas sur la piste choisie le disent.** La batterie du studio trance a ses propres enveloppes et ne traverse pas le filtre de piste : ses panneaux *Enveloppe* et *Filtre* s'éteignent, leurs curseurs se bloquent, et la légende porte la mention « sans effet ici ». Le désaccord et l'octave aussi. Le choix d'onde reste actif : c'est lui qui fait sortir la piste du mode batterie.

Le contraste de ces mentions est vérifié par test, y compris sur la rangée éteinte — un avertissement à demi effacé n'avertit personne.

## Sortir les pistes séparées

**Exporter ZIP**, à côté d'Exporter WAV, rend le morceau **une piste à la fois** et réunit le tout dans une archive : un fichier par piste, plus le mixage complet, plus une notice qui rappelle le tempo, le nombre de mesures et la chaîne. C'est ce qu'il faut pour reprendre un morceau dans un vrai séquenceur — chaque piste sur sa propre voie, avec ses propres effets.

Tous les fichiers font **exactement la même longueur**, y compris la traîne de réverbération : ils se calent à zéro dans n'importe quel logiciel, sans décalage à corriger.

Deux détails de fabrication :

- **Aucune bibliothèque n'est chargée.** L'archive est écrite à la main — la norme ZIP tient en trois structures, et le navigateur sait dégonfler tout seul avec `CompressionStream`. Là où il ne sait pas, les fichiers sont rangés tels quels, ce qui reste une archive parfaitement valide. Sur un morceau trance, la compression fait tomber 35 Mo à 19.
- **Les pistes muettes sont omises.** Un groove qui n'emploie que sept voix sur dix ne livre pas trois fichiers silencieux. Le numéro du fichier reste celui de la voix, si bien que les trous se lisent : `909-1-Grosse caisse`, `909-3-Clap`, `909-5-Tom médium`.

La basse acide n'a pas ce bouton : elle est monophonique, il n'y a rien à séparer.

## Sortir les notes en MIDI

**Exporter MIDI** écrit le morceau en fichier **MIDI de type 1** : une piste par partie, plus une piste d'entête qui porte le tempo, la mesure en 4/4 et **un repère par maillon de la chaîne**. Déposé dans un séquenceur, il donne autant de pistes nommées, tout modifiable note à note.

Ce qui s'y trouve :

- Les **accords** deviennent des notes simultanées, les **tenues** des notes longues, les **accents** une vélocité de 112 contre 88.
- Le **swing est écrit tel qu'on l'entend**, plutôt que laissé au séquenceur d'accueil.
- Les batteries — la piste du studio trance et la 909 entière — partent sur le **canal 10** aux hauteurs General MIDI : elles tombent juste dans un Drum Rack sans rien régler. La 909 tient sur une seule piste, parce qu'un Drum Rack *est* déjà la vue multipiste d'une boîte à rythmes : un pad par voix.
- Le **glissando** de la 303 s'écrit en liaison, la note débordant sur la suivante — ce que tout synthé monophonique en mode legato relit comme un portamento.
- Les noms de piste sont ramenés à l'**ASCII** : la norme MIDI ne garantit pas l'UTF-8, et un accent mal lu donne une piste au nom illisible.

Un fichier MIDI ne transporte **aucun son**. Pour les timbres, il y a l'export ZIP ci-dessus ; pour les rebâtir à la main, [`ableton/Eclipse-Ableton.md`](ableton/Eclipse-Ableton.md) montre la méthode sur un morceau.

Une note de fabrication : ce même morceau avait déjà été écrit en MIDI par un script Python, hors navigateur, à partir du source de la page. Les deux implémentations produisent aujourd'hui **exactement les mêmes notes** — même tic, même hauteur, même vélocité, sur les 90 notes d'*Éclipse*. C'est la vérification qui compte, plus que n'importe quel test unitaire.

## Sauvegarder un morceau en JSON

Le lien partagé est compact mais illisible. **Exporter JSON** enregistre le même morceau dans un fichier fait pour être ouvert : valeurs réelles au lieu de base 36, une entrée par piste, et les motifs dans la notation documentée plus haut.

```json
{
  "format": "synthes-virtuels/trance",
  "version": 1,
  "nom": "Morceau trance",
  "master": { "volume": 0.55, "bpm": 132, "swing": 0, "revSize": 3.6, "filtQ": 6 },
  "chaine": "001122",
  "mode": "morceau",
  "accords": true,
  "filtre": ["--------------------------------", "…"],
  "pistes": [
    {
      "nom": "Nappe", "preset": null,
      "volume": 0.58, "muet": false, "solo": false,
      "reglages": { "wave": "supersaw", "octave": 3, "detune": 32, "attack": 1.4, … },
      "motifs": ["(037)===============================", "…"]
    }
  ]
}
```

**Importer JSON** relit ce fichier. Tout est là — pistes, instruments complets, quatre motifs, chaîne, courbes de filtre, réglages master —, donc l'aller-retour rend exactement l'état de départ. C'est vérifié par un test : l'état encodé avant l'export et après l'import sont la même chaîne, sur les quatre studios.

Comme le fichier est du texte, **on peut le modifier à la main** : changer un tempo, renommer une piste, réécrire un motif, mettre une voix en muet. Le fichier réimporté prend les modifications.

Trois garde-fous, parce qu'un fichier arrive de l'extérieur :

- Un fichier venant d'un autre studio est **refusé en le nommant** (« Fichier du studio 8-bit ») plutôt qu'à moitié chargé. Un JSON malformé dit « JSON invalide ». Dans les deux cas, rien ne bouge.
- Chaque valeur lue est vérifiée avant d'être posée, puis **tout repasse par le codec des liens partagés** : ses bornes et ses garde-fous sont déjà éprouvés, et aucune valeur du fichier n'atteint le moteur audio sans passer par eux. Un tempo à 99999 revient à 150, un volume à −50 revient à 0.
- Un import est **annulable** : `Ctrl+Z` rend l'état précédent.

## Les info-bulles

Un libellé de curseur dit son nom, pas son effet : « Grain », « Env. montée » ou « Rapport » ne parlent qu'à qui sait déjà. **Survolez n'importe quel paramètre** et une bulle explique à quoi il sert et ce qu'on entend quand on le bouge — 108 explications au total, écrites une par une pour chaque studio.

Le `title` natif du navigateur n'aurait pas suffi : il arrive après une seconde, se coupe, ne se met jamais en forme, et **n'apparaît pas au clavier**. La bulle maison s'ouvre au survol comme à la prise de focus — utile, puisqu'un curseur se règle très bien aux flèches — se ferme avec `Échap`, se replace toute seule quand il n'y a pas la place au-dessus, et se referme d'elle-même après quelques secondes au doigt, faute d'événement de sortie sur écran tactile.

La cible est **la ligne entière**, pas le curseur seul : c'est bien plus facile à viser.

## La basse acide

[`acid303.html`](acid303.html) est la compagne naturelle de la boîte à rythmes : **une seule voix**, et tout le caractère dans la façon dont elle est jouée.

**L'oscillateur ne s'arrête jamais.** C'est l'architecture de la machine d'origine, et ce n'est pas un détail : un seul oscillateur tourne en continu, et le séquenceur ne fait qu'ouvrir une porte et déplacer sa fréquence. C'est ce qui rend le glissando possible — sans ça, chaque note serait un nouvel oscillateur et il n'y aurait rien à faire glisser.

Trois rangées commandent le pas entier :

- **Acc.** — la note frappe plus fort *et* ouvre le filtre plus grand. Sur une ligne monophonique, c'est ce qui crée le relief.
- **Gliss.** — la hauteur coule depuis la note précédente, et **l'enveloppe de filtre ne repart pas**. C'est de là que vient le son : une note glissée sonne plus sourde que ses voisines, et c'est ce contraste qui fait le motif.
- **Tenue** — la note se prolonge sur le pas suivant.

Le filtre est un **passe-bas à 24 dB par octave**, obtenu en chaînant deux `BiquadFilter` : l'API n'en offre que 12 par filtre, et à cette pente-là le son reste bien trop ouvert pour le genre. La résonance monte assez haut pour que le filtre siffle, et une **bande d'automation** sous la grille permet de dessiner la coupure pas par pas — la main sur le bouton, sans la main.

Neuf motifs fournis :

| Motif | Tempo | Caractère |
| --- | --- | --- |
| **Acide** | 132 | La ligne classique, avec une montée de coupure sur le motif C |
| **Cuve** | 126 | Plus lente et plus saturée, notes tenues |
| **Sirop** | 138 | Arpège rapide et filtre plus ouvert |
| **Filature** | 128 | Shuffle marqué, glissandos espacés, coupure très basse |
| **Sonde** | 140 | Une note sur deux, glissandos rares, filtre court |
| **Vertige** | 136 | Le plus résonant : longue enveloppe, saturation forte, coupure en creux |
| **Bitume** | 120 | Le shuffle le plus lourd, descente chromatique sur le motif C |
| **Spirale** | 146 | Doubles-croches continues, aucun silence, filtre bref |
| **Résine** | 130 | Glissando immédiat sur la même note, la signature de la machine |

Un détail de méthode : les motifs sont écrits en jetons plutôt qu'en chaînes, parce qu'un glissando s'écrit `/3` — deux caractères pour **un** pas. Mes trois premiers motifs faisaient 14 ou 15 pas au lieu de 16 et se sont fait attraper par le test ; les six suivants sont passés par un générateur qui compte les jetons à l'écriture, et le même piège s'est représenté trois fois — sans le compteur, ils partaient à 14.

## Les cordes pincées

Les cinq autres moteurs fabriquent une forme d'onde puis la sculptent. [`cordes.html`](cordes.html) fait l'inverse : il **simule un objet qui vibre**.

Une note y est une **ligne à retard** — un tampon circulaire — qu'on remplit d'une bouffée de bruit, puis qu'on reboucle sur elle-même à travers un filtre qui l'amortit. Le bruit tourne, s'appauvrit à chaque tour, et ce qui en sort est une corde. C'est le **Karplus-Strong**, et il n'y a pas un seul oscillateur dans la page.

Conséquence : **la hauteur ne se règle pas, elle se mesure**. Elle vaut la fréquence d'échantillonnage divisée par la longueur de la ligne. C'est ce qui rend ce moteur agréable à vérifier — un test rend une note en WAV, cherche sa période par autocorrélation, et compare à la note demandée. Le résultat tient dans les **8 centièmes de demi-ton** sur trois octaves.

Cette précision demande du soin : chaque filtre de la boucle ajoute son propre retard, qu'il faut retrancher de la longueur sous peine d'entendre une note trop grave. Le reste fractionnaire est absorbé par un filtre passe-tout, celui-là même qui sert aussi à la raideur.

Les réglages sont physiques, et s'entendent :

- **Durée** — le gain de rebouclage. Plus il approche de 1, plus la corde entretient sa propre vibration.
- **Brillance** — l'amortissement des aigus à chaque tour. Bas, la corde est sourde ; haut, elle reste claire longtemps.
- **Raideur** — l'inharmonicité. Une corde idéale a des partiels exactement multiples ; une corde épaisse et rigide les décale vers l'aigu. C'est ce qui sépare un piano d'une harpe.
- **Pince** — où la corde est pincée, du chevalet au milieu. La pince supprime les partiels dont un ventre tombe sous le doigt : près du chevalet le son est nasillard, au milieu il est rond.
- **Matière** — la nature de l'excitation, du bruit (un doigt) à l'impulsion (un bec ou un marteau).
- **Corps** — deux résonances larges après la corde. Sans elles le son est juste mais sec, comme une corde tendue en l'air.

Deux commandes propres au geste : l'**arpège** égrène les notes d'un accord comme une main qui balaie les cordes, et la rangée **Étouf.** pose la main dessus pour couper ce qui résonne — l'inverse d'une tenue, et la seule façon d'arrêter une corde qui décide toute seule quand elle s'éteint.

Six instruments : **Guitare**, **Harpe**, **Clavecin**, **Koto**, **Contrebasse**, **Cithare**. Neuf morceaux :

| Morceau | Tempo | Caractère |
| --- | --- | --- |
| **Sarabande** | 76 | Accords plaqués à la guitare |
| **Pluie** | 112 | Harpe en arpèges |
| **Atelier** | 128 | Clavecin sec |
| **Berceau** | 68 | Harpe et cithare, réverbération longue |
| **Ricochet** | 132 | Koto rebondissant sur des accords de guitare |
| **Charpente** | 104 | Clavecin à deux voix, le plus écrit de la page |
| **Bruine** | 96 | Cithare en gouttes sur une harpe tenue |
| **Estuaire** | 60 | Le plus lent : quatre accords, presque rien d'autre |
| **Bal** | 124 | Guitare rythmique et koto en réponse |

Le bruit d'excitation vient d'une suite **reproductible** : une même note rend toujours exactement le même signal. Ce n'est pas un détail — c'est ce qui permet à un test de comparer deux rendus, et ça évite les mauvaises surprises intermittentes qu'un bruit vraiment aléatoire avait déjà causées ailleurs dans ce projet.

## Relier les studios : la table de montage

Les quatre studios ne savent faire qu'une chose à la fois. Un morceau complet demande pourtant une boîte à rythmes **et** un synthé, et rien ne permettait de les réunir.

Les faire jouer ensemble et en phase supposerait qu'ils partagent une horloge audio. Ce sont des documents séparés, avec chacun son `AudioContext` ; il faudrait des iframes et du `postMessage`, ce qui fonctionnerait en local mais serait bloqué par la politique de sécurité des pages publiées. Une passerelle qui casse là où on s'en sert n'en est pas une.

Chaque studio sait en revanche **rendre son morceau en WAV**. [`montage.html`](montage.html) est le chaînon qui manquait : on y dépose ces rendus, on les cale, on les mixe, on ressort un seul fichier.

Par piste : **volume**, **muet**, **solo**, **décalage en mesures** et **boucler**. La forme d'onde est dessinée, ce qui montre d'un coup d'œil où le morceau respire et où il frappe.

Deux détails font tout le travail :

- **Boucler** répète une piste courte jusqu'à la fin du montage. C'est ce qui permet de poser deux mesures de batterie sous huit mesures de synthé, sans rien réexporter.
- La longueur du montage est fixée par les pistes **non bouclées** — les pistes bouclées la remplissent. Si tout est bouclé, la plus longue donne la mesure. Une piste décalée repousse la fin d'autant.

Le **tempo** du montage ne change aucun son : il sert seulement à exprimer les décalages et la règle en mesures.

Le mixage passe par un **limiteur** avec une attaque de 0,5 ms : quatre pistes qui s'additionnent dépassent vite le plein niveau, et sans lui le rendu saturerait. La lecture et l'export partagent exactement le même graphe audio, donc le fichier est ce qu'on a entendu.

## Rejouer un morceau dans un vrai séquenceur

Le dossier [`ableton/`](ableton/) contient de quoi reprendre *Éclipse* ailleurs que dans le navigateur :

- **`Eclipse.mid`** — fichier MIDI de type 1, à glisser dans l'Arrangement. Cinq pistes nommées d'après l'instrument à y poser, 10 mesures, 90 notes, 126 BPM, batterie sur le canal 10 aux hauteurs General MIDI, et trois repères qui marquent la structure `A A B B C`. Tout y est modifiable, note à note.
- **`Eclipse-Ableton.md`** — les sons, relevés dans le moteur de la page plutôt que reconstitués : oscillateurs, enveloppes, filtres, départs, faders, sidechain. Le morceau se rebâtit **avec l'édition de base** de Live : `Drift` et son mode Unison remplacent `Wavetable`, absent d'Intro et de Lite.
- **`eclipse-midi.py`** — le générateur d'origine, écrit avant que les studios sachent le faire eux-mêmes. Il relit le morceau directement dans `trance.html`. Il sert aujourd'hui de **contre-épreuve** au bouton *Exporter MIDI* : deux implémentations séparées, mêmes notes au tic près.
- **`verif-midi.py`** — le vérificateur, qui relit le fichier produit sans rien supposer de la façon dont il a été écrit : hauteurs, durées, chevauchements, notes jamais relâchées.
- **`eclipse-stems.js`** — rend le morceau **piste par piste** en solotant chaque piste tour à tour, plus le mixage complet. Les WAV ne sont pas versionnés — 27 Mo pour six fichiers — mais se regénèrent en une commande. Le studio sait maintenant le faire tout seul : voir **Exporter ZIP** plus haut.

Un fichier MIDI ne transporte aucun son : l'attaque de 900 ms de la nappe, la réverbération de 4,2 s et le délai pointé, qui font tout le caractère du morceau, n'y sont pas. Les stems servent de cible à l'oreille pendant qu'on rebâtit les instruments.

## Structure

Huit fichiers autonomes, sans dépendance ni build :

- [`index.html`](index.html) — l'accueil, avec une vignette animée par studio : onde carrée crantée, pas-à-pas qui défile, porteuse déformée par sa modulante, dents de scie désaccordées, ligne de basse reliée par ses glissandos.
- [`chiptune.html`](chiptune.html) — le synthé 8-bit.
- [`drums909.html`](drums909.html) — la boîte à rythmes.
- [`fm.html`](fm.html) — le synthé FM.
- [`trance.html`](trance.html) — le studio trance.
- [`acid303.html`](acid303.html) — la basse acide.
- [`cordes.html`](cordes.html) — les cordes pincées.
- [`montage.html`](montage.html) — la table de montage, qui ne synthétise rien et se contente d'assembler des WAV.

Chaque studio est un document séparé : leurs identifiants, leurs styles, leurs raccourcis clavier et leur contexte audio ne se marchent jamais dessus.
