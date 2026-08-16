/**
 * Liste des programmes BASIC préconfigurés, prêts à charger et exécuter.
 * Le code de chaque preset est intégré directement ici (et dupliqué en tant
 * que vrai fichier .bas dans /presets pour consultation/édition) afin que
 * l'émulateur fonctionne même ouvert en double-clic (file://), sans serveur
 * local et sans dépendre de fetch().
 */
const PRESET_LIST = [
  {
    id: 'hello',
    name: 'Bonjour le monde',
    file: 'presets/hello.bas',
    desc: "Le grand classique : affiche un message de bienvenue et une boucle FOR.",
    code: `10 REM Bonjour le monde - le classique des classiques
20 PRINT "BONJOUR, MONDE !"
30 PRINT "Bienvenue dans l'emulateur BASIC."
40 FOR I = 1 TO 3
50 PRINT "Ligne "; I
60 NEXT I
70 END
`,
  },
  {
    id: 'fizzbuzz',
    name: 'FizzBuzz',
    file: 'presets/fizzbuzz.bas',
    desc: 'Le célèbre exercice FizzBuzz de 1 à 30, avec IF/THEN et MOD.',
    code: `10 REM FizzBuzz de 1 a 30
20 FOR N = 1 TO 30
30 IF N MOD 15 = 0 THEN PRINT "FizzBuzz" : GOTO 80
40 IF N MOD 3 = 0 THEN PRINT "Fizz" : GOTO 80
50 IF N MOD 5 = 0 THEN PRINT "Buzz" : GOTO 80
60 PRINT N
80 NEXT N
90 END
`,
  },
  {
    id: 'fibonacci',
    name: 'Suite de Fibonacci',
    file: 'presets/fibonacci.bas',
    desc: 'Calcule N termes de la suite de Fibonacci saisis par l\'utilisateur.',
    code: `10 REM Suite de Fibonacci
20 INPUT "Combien de termes voulez-vous afficher"; N
30 A = 0
40 B = 1
50 FOR I = 1 TO N
60 PRINT A; " ";
70 T = A + B
80 A = B
90 B = T
100 NEXT I
110 PRINT
120 END
`,
  },
  {
    id: 'guess',
    name: 'Devine le nombre',
    file: 'presets/guess.bas',
    desc: 'Petit jeu où il faut deviner un nombre choisi au hasard (RND).',
    code: `10 REM Devine le nombre entre 1 et 100
20 PRINT "Je pense a un nombre entre 1 et 100."
30 SECRET = INT(RND(1) * 100) + 1
40 TRIES = 0
50 INPUT "Ton essai"; G
60 TRIES = TRIES + 1
70 IF G = SECRET THEN GOTO 110
80 IF G < SECRET THEN PRINT "Plus grand !"
90 IF G > SECRET THEN PRINT "Plus petit !"
100 GOTO 50
110 PRINT "Bravo ! Trouve en "; TRIES; " essais."
120 END
`,
  },
  {
    id: 'times-table',
    name: 'Table de multiplication',
    file: 'presets/times-table.bas',
    desc: "Affiche la table de multiplication d'un nombre saisi.",
    code: `10 REM Table de multiplication
20 INPUT "Table de quel nombre"; N
30 FOR I = 1 TO 10
40 PRINT N; " x "; I; " = "; N * I
50 NEXT I
60 END
`,
  },
  {
    id: 'primes',
    name: 'Nombres premiers',
    file: 'presets/primes.bas',
    desc: 'Liste tous les nombres premiers jusqu\'à une limite N.',
    code: `10 REM Nombres premiers jusqu'a N
20 INPUT "Jusqu'a quel nombre"; N
30 PRINT "Nombres premiers :"
40 FOR K = 2 TO N
50 P = 1
60 FOR D = 2 TO K - 1
70 IF K MOD D = 0 THEN P = 0
80 NEXT D
90 IF P = 1 THEN PRINT K; " ";
100 NEXT K
110 PRINT
120 END
`,
  },
  {
    id: 'stats',
    name: 'Statistiques (min/max/moyenne)',
    file: 'presets/stats.bas',
    desc: 'Saisit une liste de nombres dans un tableau (DIM) et calcule des statistiques.',
    code: `10 REM Statistiques sur une liste de nombres
20 INPUT "Combien de nombres"; N
30 DIM V(N)
40 SOMME = 0
50 FOR I = 1 TO N
60 PRINT "Nombre "; I; " : ";
70 INPUT X
80 V(I) = X
90 SOMME = SOMME + X
100 IF I = 1 THEN MINV = X : MAXV = X
110 IF X < MINV THEN MINV = X
120 IF X > MAXV THEN MAXV = X
130 NEXT I
140 PRINT "Somme = "; SOMME
150 PRINT "Moyenne = "; SOMME / N
160 PRINT "Minimum = "; MINV
170 PRINT "Maximum = "; MAXV
180 END
`,
  },
  {
    id: 'pyramid',
    name: "Pyramide d'étoiles",
    file: 'presets/pyramid.bas',
    desc: "Dessine une pyramide d'étoiles ASCII avec des boucles imbriquées.",
    code: `10 REM Pyramide d'etoiles
20 INPUT "Hauteur de la pyramide"; H
30 FOR I = 1 TO H
40 FOR S = 1 TO H - I
50 PRINT " ";
60 NEXT S
70 FOR E = 1 TO 2 * I - 1
80 PRINT "*";
90 NEXT E
100 PRINT
110 NEXT I
120 END
`,
  },
];

if (typeof window !== 'undefined') {
  window.PRESET_LIST = PRESET_LIST;
}
