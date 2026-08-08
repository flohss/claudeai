#!/usr/bin/env node
/* Lanceur des suites de test.
   Usage :  node tests/run.mjs            (tout)
            node tests/run.mjs jeu        (le jeu seul)
            node tests/run.mjs labo       (le laboratoire seul) */
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { serve, launch } from './lib.mjs';
import testJeu from './jeu.test.mjs';
import testLabo from './labo.test.mjs';

const racine = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PORT = 8907;
const cible = (process.argv[2] || 'tout').toLowerCase();

const suites = [];
if(cible === 'tout' || cible === 'jeu')  suites.push(['Jeu — labyrinthe3d.html', testJeu]);
if(cible === 'tout' || cible === 'labo') suites.push(['Laboratoire — labo-algorithmes.html', testLabo]);
if(!suites.length){
  console.error('Cible inconnue : ' + cible + '  (attendu : tout, jeu, labo)');
  process.exit(2);
}

const serveur = await serve(racine, PORT);
const base = 'http://127.0.0.1:' + PORT;
const navigateur = await launch();
const debut = Date.now();
let tous = [];

try {
  for(const [titre, suite] of suites){
    console.log('\n══ ' + titre);
    const r = await suite(navigateur, base);
    tous = tous.concat(r.map(x => ({ ...x, suite: titre })));
  }
} finally {
  await navigateur.close();
  serveur.close();
}

const echecs = tous.filter(r => !r.ok);
const duree = ((Date.now() - debut)/1000).toFixed(0);
console.log('\n' + '─'.repeat(64));
console.log((tous.length - echecs.length) + ' contrôles réussis sur ' + tous.length +
            '  ·  ' + duree + ' s');
if(echecs.length){
  console.log('\nÉchecs :');
  for(const e of echecs) console.log('  ✘ [' + e.suite + '] ' + e.label + '  ' + e.detail);
}
process.exit(echecs.length ? 1 : 0);
