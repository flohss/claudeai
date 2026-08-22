// ---------- Données des mots fléchés ----------
// Types de cellule : "block" (case noire), "clue" (case indice + flèche), "input" (case à remplir)
const CW_BLOCK = { type: "block" };
function clue(text, dir) { return { type: "clue", text, dir }; }
function input(letter) { return { type: "input", solution: letter }; }

const CROSSWORD_PUZZLES = [
  {
    name: "Le chat sur le toit",
    grid: [
      [CW_BLOCK, CW_BLOCK, CW_BLOCK, CW_BLOCK, clue("Couvre la maison", "down"), CW_BLOCK, CW_BLOCK],
      [clue("Animal qui miaule", "right"), input("C"), input("H"), input("A"), input("T"), CW_BLOCK, CW_BLOCK],
      [CW_BLOCK, CW_BLOCK, clue("Vêtement", "right"), input("R"), input("O"), input("B"), input("E")],
      [CW_BLOCK, CW_BLOCK, clue("Endroit où l'on dort", "right"), input("L"), input("I"), input("T"), CW_BLOCK],
      [CW_BLOCK, clue("Véhicule à deux roues", "right"), input("M"), input("O"), input("T"), input("O"), CW_BLOCK]
    ]
  },
  {
    name: "La maison",
    grid: [
      [CW_BLOCK, CW_BLOCK, CW_BLOCK, clue("Habitation", "down"), CW_BLOCK, CW_BLOCK, CW_BLOCK],
      [CW_BLOCK, CW_BLOCK, clue("Étendue d'eau salée", "right"), input("M"), input("E"), input("R"), CW_BLOCK],
      [CW_BLOCK, clue("Contient des affaires", "right"), input("S"), input("A"), input("C"), CW_BLOCK, CW_BLOCK],
      [CW_BLOCK, clue("Meuble pour dormir", "right"), input("L"), input("I"), input("T"), CW_BLOCK, CW_BLOCK],
      [clue("Fleur", "right"), input("R"), input("O"), input("S"), input("E"), CW_BLOCK, CW_BLOCK],
      [CW_BLOCK, clue("On l'ouvre pour entrer", "right"), input("P"), input("O"), input("R"), input("T"), input("E")],
      [CW_BLOCK, CW_BLOCK, clue("Abri d'oiseau", "right"), input("N"), input("I"), input("D"), CW_BLOCK]
    ]
  },
  {
    name: "L'école",
    grid: [
      [CW_BLOCK, CW_BLOCK, CW_BLOCK, clue("Établissement scolaire", "down"), CW_BLOCK, CW_BLOCK],
      [CW_BLOCK, clue("Papa", "right"), input("P"), input("E"), input("R"), input("E")],
      [clue("Étendue d'eau douce", "right"), input("L"), input("A"), input("C"), CW_BLOCK, CW_BLOCK],
      [CW_BLOCK, clue("Partie arrière du corps", "right"), input("D"), input("O"), input("S"), CW_BLOCK],
      [clue("Soirée dansante", "right"), input("B"), input("A"), input("L"), CW_BLOCK, CW_BLOCK],
      [clue("Voie en ville", "right"), input("R"), input("U"), input("E"), CW_BLOCK, CW_BLOCK]
    ]
  }
];
