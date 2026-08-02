# Synthé 8-Bit 🎹

Un synthétiseur virtuel 8-bit (chiptune) jouable dans le navigateur, écrit en HTML/CSS/JavaScript pur avec l'API Web Audio — aucune dépendance, aucun build.

## Utilisation

Ouvrez simplement `index.html` dans un navigateur moderne (Chrome, Firefox, Edge, Safari), ou servez le dossier :

```bash
npx serve .
# ou
python3 -m http.server
```

## Trois pistes indépendantes

Le séquenceur pilote **trois pistes** (Mélodie, Basse, Percu) qui jouent simultanément. Chaque piste possède son propre instrument complet — forme d'onde, octave, enveloppe ADSR, bitcrusher et vibrato — ainsi que son volume, son bouton muet et son solo.

Cliquer sur le nom d'une piste la sélectionne : les panneaux de réglage l'éditent alors, et le clavier la joue. Toucher un réglage bascule la piste en mode « Perso » sans altérer les autres.

## Partager un morceau

L'adresse de la page contient tout votre morceau. Chaque modification met à jour le fragment d'URL (sans polluer l'historique), et le bouton **Partager** copie le lien dans le presse-papiers — l'ouvrir restitue les trois motifs, les instruments, le mixage, le tempo et l'écho à l'identique.

L'encodage est compact et lisible : chaque valeur est quantifiée puis écrite en base 36, et les 16 pas d'une piste tiennent en 16 caractères (un par hauteur, `-` pour un pas vide). Un morceau complet occupe environ 150 caractères :

```
#p=1.4o.1u.14.m.z.1.3.m~2.5.5.28.n.c.5.1o.3.16.0.-47b047c959c7420~…
   └ master : version, tempo, volume, écho, piste courante, arpège
                          └ piste : onde, octave, ADSR, bits, vibrato, volume, état, 16 pas
```

Le décodage est tolérant : un lien tronqué, altéré ou d'une version inconnue retombe simplement sur le morceau de démo, chaque valeur étant bornée à sa plage.

## Fonctionnalités

- **6 formes d'onde chiptune** : carré 50 %, impulsion 25 %, impulsion 12,5 % (les classiques de la NES/Game Boy), triangle, dents de scie et bruit style console 8-bit.
- **Enveloppe ADSR** complète : attaque, déclin, maintien, relâche.
- **Bitcrusher** par piste : réduction de la résolution de 8 à 2 bits pour un grain rétro.
- **Vibrato** par piste : LFO avec vitesse et profondeur réglables (jusqu'à 6 demi-tons, effet sirène).
- **Écho rétro** (master) : delay avec mix, temps et feedback réglables, placé après les bitcrusher pour que les répétitions gardent le grain 8-bit.
- **Arpégiateur** : modes montant, descendant, aller-retour et aléatoire, vitesse réglable — maintenez plusieurs notes pour lancer l'arpège.
- **Séquenceur 16 pas × 3 pistes** : bande de résumé des trois pistes, piano-roll détaillé d'une octave avec les notes des autres pistes en repère, tempo 60–240 BPM, horloge audio précise (lookahead) et motifs de démo préchargés.
- **5 presets** : Lead GB, Basse, Cristal, Percu, Sirène — applicables à la piste sélectionnée.
- **Partage par URL** : le morceau complet tient dans le lien, restitué à l'identique à l'ouverture.
- **Enregistrement** : capture le mixage complet et exporte un fichier `.webm`/`.ogg` en un clic.
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

## Structure

Tout tient dans un seul fichier : [`index.html`](index.html) (interface, styles rétro et moteur audio).
