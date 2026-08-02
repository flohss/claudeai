# Synthé 8-Bit 🎹

Un synthétiseur virtuel 8-bit (chiptune) jouable dans le navigateur, écrit en HTML/CSS/JavaScript pur avec l'API Web Audio — aucune dépendance, aucun build.

## Utilisation

Ouvrez simplement `index.html` dans un navigateur moderne (Chrome, Firefox, Edge, Safari), ou servez le dossier :

```bash
npx serve .
# ou
python3 -m http.server
```

## Fonctionnalités

- **6 formes d'onde chiptune** : carré 50 %, impulsion 25 %, impulsion 12,5 % (les classiques de la NES/Game Boy), triangle, dents de scie et bruit style console 8-bit.
- **Enveloppe ADSR** complète : attaque, déclin, maintien, relâche.
- **Bitcrusher** : réduction de la résolution de 8 à 2 bits pour un grain rétro.
- **Vibrato** : LFO avec vitesse et profondeur réglables (jusqu'à 6 demi-tons, effet sirène).
- **Écho rétro** : delay avec mix, temps et feedback réglables (l'écho passe dans le bitcrusher).
- **Arpégiateur** : modes montant, descendant, aller-retour et aléatoire, vitesse réglable — maintenez plusieurs notes pour lancer l'arpège.
- **Séquenceur 16 pas** : piano-roll d'une octave, tempo 60–240 BPM, horloge audio précise (lookahead), motif de démo préchargé — le sélecteur d'octave transpose la séquence en direct.
- **5 presets** : Lead GB, Basse, Cristal, Percu, Sirène.
- **Enregistrement** : capture la sortie audio et exporte un fichier `.webm`/`.ogg` en un clic.
- **Oscilloscope** temps réel.
- **Clavier virtuel de 2 octaves** (souris et tactile, avec glissando) + sélecteur d'octave (1 à 7).
- **Polyphonie** illimitée.

## Clavier d'ordinateur

Le mappage utilise la position physique des touches, donc il fonctionne aussi bien en AZERTY qu'en QWERTY :

- **Rangée du milieu** (Q S D F G H J K L M en AZERTY) : touches blanches — Do, Ré, Mi, Fa, Sol, La, Si…
- **Rangée du haut** (Z E T Y U O P en AZERTY) : touches noires — Do#, Ré#, Fa#, Sol#, La#…
- **W / X** (en AZERTY) : octave −1 / +1

## Structure

Tout tient dans un seul fichier : [`index.html`](index.html) (interface, styles rétro et moteur audio).
