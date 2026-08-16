/**
 * Liste des programmes BASIC préconfigurés, prêts à charger et exécuter.
 * Chaque entrée pointe vers un vrai fichier .bas du dossier /presets.
 */
const PRESET_LIST = [
  {
    id: 'hello',
    name: 'Bonjour le monde',
    file: 'presets/hello.bas',
    desc: "Le grand classique : affiche un message de bienvenue et une boucle FOR.",
  },
  {
    id: 'fizzbuzz',
    name: 'FizzBuzz',
    file: 'presets/fizzbuzz.bas',
    desc: 'Le célèbre exercice FizzBuzz de 1 à 30, avec IF/THEN et MOD.',
  },
  {
    id: 'fibonacci',
    name: 'Suite de Fibonacci',
    file: 'presets/fibonacci.bas',
    desc: 'Calcule N termes de la suite de Fibonacci saisis par l\'utilisateur.',
  },
  {
    id: 'guess',
    name: 'Devine le nombre',
    file: 'presets/guess.bas',
    desc: 'Petit jeu où il faut deviner un nombre choisi au hasard (RND).',
  },
  {
    id: 'times-table',
    name: 'Table de multiplication',
    file: 'presets/times-table.bas',
    desc: "Affiche la table de multiplication d'un nombre saisi.",
  },
  {
    id: 'primes',
    name: 'Nombres premiers',
    file: 'presets/primes.bas',
    desc: 'Liste tous les nombres premiers jusqu\'à une limite N.',
  },
  {
    id: 'stats',
    name: 'Statistiques (min/max/moyenne)',
    file: 'presets/stats.bas',
    desc: 'Saisit une liste de nombres dans un tableau (DIM) et calcule des statistiques.',
  },
  {
    id: 'pyramid',
    name: "Pyramide d'étoiles",
    file: 'presets/pyramid.bas',
    desc: "Dessine une pyramide d'étoiles ASCII avec des boucles imbriquées.",
  },
];

if (typeof window !== 'undefined') {
  window.PRESET_LIST = PRESET_LIST;
}
