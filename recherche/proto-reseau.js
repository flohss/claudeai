// Prototype : un réseau de neurones entraîné sur les morceaux d'un studio,
// écrit à la main — propagation avant, rétropropagation, Adam. Aucune
// bibliothèque, aucun poids téléchargé : le corpus est déjà dans la page.
//
// On ne saura qu'à la mesure si ça vaut mieux qu'une chaîne de Markov. Le
// prototype entraîne donc les deux et les compare sur des morceaux mis de côté.
const fs = require("fs");

const ROWS = 13, K = 8;                       // 13 hauteurs, fenêtre de 8 pas
const SORTIES = 16;                           // 13 hauteurs + silence + tenue + accent
const LOW = "0123456789abc", ACC = "ABCDEFGHIJKLM";

// ---------------------------------------------------------------- le corpus
function motifsDe(fichier, steps) {
  const src = fs.readFileSync(fichier, "utf8");
  const zone = src.slice(src.indexOf("const SONGS"));
  const out = [];
  for (const bloc of zone.matchAll(/pats:\s*\[([^\]]*)\]/g))
    for (const m of bloc[1].matchAll(/"([^"]*)"/g)) {
      const pas = lire(m[1], steps);
      if (pas.some(v => v.notes.length)) out.push(pas);
    }
  return out;
}
function lire(motif, steps) {
  const jetons = (motif || "").match(/!?\([0-9a-c]+\)|./g) || [];
  const out = [];
  for (const j of jetons) {
    if (out.length >= steps) break;
    if (j === "-") out.push({ notes: [], tenue: false, accent: false });
    else if (j === "=") out.push({ notes: [], tenue: true, accent: false });
    else if (j[0] === "(" || j.startsWith("!(")) {
      const corps = j.slice(j.indexOf("(") + 1, j.indexOf(")"));
      out.push({ notes: [...corps].map(c => LOW.indexOf(c)), tenue: false, accent: j[0] === "!" });
    } else {
      const b = LOW.indexOf(j), a = ACC.indexOf(j);
      if (b >= 0) out.push({ notes: [b], tenue: false, accent: false });
      else if (a >= 0) out.push({ notes: [a], tenue: false, accent: true });
      else out.push({ notes: [], tenue: false, accent: false });
    }
  }
  while (out.length < steps) out.push({ notes: [], tenue: false, accent: false });
  return out;
}
// Transposer, c'est apprendre les intervalles plutôt que les notes : neuf
// morceaux deviennent cent huit, et le réseau cesse de mémoriser des hauteurs.
const transposer = (pas, t) => pas.map(v => ({
  notes: v.notes.map(n => (n + t) % 12), tenue: v.tenue, accent: v.accent }));

const vecteur = v => {
  const x = new Float64Array(SORTIES);
  v.notes.forEach(n => { if (n >= 0 && n < ROWS) x[n] = 1; });
  if (!v.notes.length) x[13] = 1;
  if (v.tenue) x[14] = 1;
  if (v.accent) x[15] = 1;
  return x;
};

function echantillons(motifs, steps) {
  const X = [], Y = [];
  for (const pas of motifs) {
    for (let s = 0; s < steps; s++) {
      const e = new Float64Array(K * SORTIES + 16 + 28);
      for (let k = 0; k < K; k++) {
        const idx = s - K + k;
        const v = idx >= 0 ? vecteur(pas[idx]) : null;
        if (v) e.set(v, k * SORTIES);
      }
      e[K * SORTIES + (s % 16)] = 1;         // où l'on est dans la mesure
      // Ce qui compte en musique, c'est l'intervalle, pas la hauteur absolue :
      // le donner explicitement évite au réseau de le redécouvrir tout seul
      // à partir de cent motifs, ce qu'il n'a pas de quoi faire.
      let der = -1;
      for (let k = s - 1; k >= 0 && der < 0; k--) if (pas[k].notes.length) der = pas[k].notes[0];
      const cour = pas[s].notes.length ? pas[s].notes[0] : -1;
      const base = K * SORTIES + 16;
      if (der >= 0 && cour >= 0) e[base + Math.max(0, Math.min(24, cour - der + 12))] = 1;
      else e[base + 25] = 1;                 // pas d'intervalle : début ou silence
      if (s % 4 === 0) e[base + 26] = 1;     // temps fort
      if (s % 16 === 0) e[base + 27] = 1;    // début de mesure
      const actifs = [];
      for (let i = 0; i < e.length; i++) if (e[i]) actifs.push(i);
      X.push(actifs); Y.push(vecteur(pas[s]));
    }
  }
  return { X, Y };
}

// ---------------------------------------------------------------- le réseau
function creer(nEntree, nCache, nSortie, alea) {
  const mk = (a, b) => {
    const w = new Float64Array(a * b);
    const lim = Math.sqrt(6 / (a + b));       // initialisation de Glorot
    for (let i = 0; i < w.length; i++) w[i] = (alea() * 2 - 1) * lim;
    return w;
  };
  return { nE: nEntree, nC: nCache, nS: nSortie,
           W1: mk(nEntree, nCache), b1: new Float64Array(nCache),
           W2: mk(nCache, nSortie), b2: new Float64Array(nSortie) };
}
const sigm = z => 1 / (1 + Math.exp(-z));
function avant(r, x) {
  const h = new Float64Array(r.nC);
  h.set(r.b1);
  for (const i of x) {                        // x est la liste des cases actives
    const d = i * r.nC;
    for (let j = 0; j < r.nC; j++) h[j] += r.W1[d + j];
  }
  for (let j = 0; j < r.nC; j++) h[j] = Math.tanh(h[j]);
  const y = new Float64Array(r.nS);
  for (let k = 0; k < r.nS; k++) {
    let s = r.b2[k];
    for (let j = 0; j < r.nC; j++) s += h[j] * r.W2[j * r.nS + k];
    y[k] = sigm(s);
  }
  return { h, y };
}
function adam(r) {
  const z = t => ({ m: new Float64Array(t.length), v: new Float64Array(t.length) });
  return { W1: z(r.W1), b1: z(r.b1), W2: z(r.W2), b2: z(r.b2), t: 0 };
}
function pas(r, o, grads, lr, decay) {
  o.t++;
  const b1 = 0.9, b2 = 0.999, eps = 1e-8;
  const c1 = 1 - Math.pow(b1, o.t), c2 = 1 - Math.pow(b2, o.t);
  for (const nom of ["W1", "b1", "W2", "b2"]) {
    const p = r[nom], g = grads[nom], s = o[nom];
    const d = nom[0] === "W" ? decay : 0;    // on ne freine pas les biais
    for (let i = 0; i < p.length; i++) {
      const gi = g[i] + d * p[i];
      s.m[i] = b1 * s.m[i] + (1 - b1) * gi;
      s.v[i] = b2 * s.v[i] + (1 - b2) * gi * gi;
      p[i] -= lr * (s.m[i] / c1) / (Math.sqrt(s.v[i] / c2) + eps);
    }
  }
}
// entropie croisée binaire : chaque sortie est un oui/non indépendant, ce qui
// laisse plusieurs hauteurs allumées à la fois — c'est ainsi qu'on a des accords
function lot(r, X, Y, idx) {
  const g = { W1: new Float64Array(r.W1.length), b1: new Float64Array(r.nC),
              W2: new Float64Array(r.W2.length), b2: new Float64Array(r.nS) };
  let perte = 0;
  for (const n of idx) {
    const x = X[n], t = Y[n];
    const { h, y } = avant(r, x);
    const dy = new Float64Array(r.nS);
    for (let k = 0; k < r.nS; k++) {
      const p = Math.min(1 - 1e-9, Math.max(1e-9, y[k]));
      perte -= t[k] * Math.log(p) + (1 - t[k]) * Math.log(1 - p);
      dy[k] = y[k] - t[k];                    // dérivée sigmoïde + BCE, simplifiée
    }
    const dh = new Float64Array(r.nC);
    for (let j = 0; j < r.nC; j++) {
      let s = 0;
      for (let k = 0; k < r.nS; k++) { g.W2[j * r.nS + k] += h[j] * dy[k]; s += r.W2[j * r.nS + k] * dy[k]; }
      dh[j] = s * (1 - h[j] * h[j]);
    }
    for (let k = 0; k < r.nS; k++) g.b2[k] += dy[k];
    for (let j = 0; j < r.nC; j++) g.b1[j] += dh[j];
    for (const i of x) {
      const d = i * r.nC;
      for (let j = 0; j < r.nC; j++) g.W1[d + j] += dh[j];
    }
  }
  const n = idx.length;
  for (const nom of ["W1", "b1", "W2", "b2"]) for (let i = 0; i < g[nom].length; i++) g[nom][i] /= n;
  return { g, perte: perte / n };
}
const perteSur = (r, X, Y, ech) => {
  let p = 0;
  for (const n of ech) {
    const { y } = avant(r, X[n]);
    for (let k = 0; k < SORTIES; k++) {
      const q = Math.min(1 - 1e-9, Math.max(1e-9, y[k]));
      p -= Y[n][k] * Math.log(q) + (1 - Y[n][k]) * Math.log(1 - q);
    }
  }
  return p / ech.length;
};

// ------------------------------------------------- la référence : Markov
// Ordre variable : on regarde les trois pas précédents, puis deux, puis un,
// et l'on retient le contexte le plus long qui ait été vu assez souvent.
function markov(motifs, steps, ordre = 3) {
  const tables = Array.from({ length: ordre + 1 }, () => new Map());
  const cle = (pas, s, o) => Array.from({ length: o }, (_, k) =>
    s - o + k >= 0 ? pas[s - o + k].notes.join(",") + (pas[s - o + k].tenue ? "=" : "") : "^").join("|");
  for (const pas of motifs)
    for (let s = 0; s < steps; s++) {
      const ev = pas[s].notes.join(",") + (pas[s].tenue ? "=" : "");
      for (let o = 0; o <= ordre; o++) {
        const t = tables[o], c = cle(pas, s, o);
        if (!t.has(c)) t.set(c, new Map());
        const m = t.get(c);
        m.set(ev, (m.get(ev) || 0) + 1);
      }
    }
  return { tables, ordre };
}
function probaMarkov(mk, pas, s, ev) {
  for (let o = mk.ordre; o >= 0; o--) {
    const cle = Array.from({ length: o }, (_, k) =>
      s - o + k >= 0 ? pas[s - o + k].notes.join(",") + (pas[s - o + k].tenue ? "=" : "") : "^").join("|");
    const m = mk.tables[o].get(cle);
    if (!m) continue;
    let tot = 0; for (const v of m.values()) tot += v;
    if (tot < 6 && o > 0) continue;           // contexte trop rare : on raccourcit
    // lissage : un peu de masse pour ce qu'on n'a jamais vu
    return ((m.get(ev) || 0) + 0.1) / (tot + 0.1 * 40);
  }
  return 1 / 40;
}

// ---------------------------------------------------------------- l'essai
const alea = (g => () => (g = (g * 1664525 + 1013904223) >>> 0) / 4294967296)(12345);

for (const [nom, fichier, steps] of [
  ["trance", "/home/user/claudeai/trance.html", 32],
  ["chiptune", "/home/user/claudeai/chiptune.html", 16]]) {
  const tous = motifsDe(fichier, steps);
  // on met de côté un motif sur cinq : le réseau ne doit jamais les voir
  const test = tous.filter((_, i) => i % 5 === 4);
  const app = tous.filter((_, i) => i % 5 !== 4);
  const augmente = [];
  for (const m of app) for (let t = 0; t < 12; t++) augmente.push(transposer(m, t));  // les douze tons

  const A = echantillons(augmente, steps), T = echantillons(test, steps);
  const r = creer(K * SORTIES + 16 + 28, 64, SORTIES, alea);
  const opt = adam(r);
  const tousIdx = A.X.map((_, i) => i), testIdx = T.X.map((_, i) => i);

  console.log(`\n=== ${nom} : ${tous.length} motifs, ${app.length} pour apprendre, ` +
              `${test.length} mis de côté → ${A.X.length} exemples augmentés`);
  console.log(`perte de départ sur les motifs mis de côté : ${perteSur(r, T.X, T.Y, testIdx).toFixed(4)}`);

  const t0 = Date.now();
  const TAILLE = 64;
  // Le réseau se met à surapprendre vers la dixième époque : on garde les poids
  // du meilleur passage sur les motifs mis de côté, pas ceux de la fin.
  let meilleur = Infinity, gardes = null, epMeilleure = 0;
  const copier = () => ({ W1: r.W1.slice(), b1: r.b1.slice(), W2: r.W2.slice(), b2: r.b2.slice() });
  for (let ep = 1; ep <= 30; ep++) {
    for (let i = tousIdx.length - 1; i > 0; i--) {
      const j = Math.floor(alea() * (i + 1));
      [tousIdx[i], tousIdx[j]] = [tousIdx[j], tousIdx[i]];
    }
    for (let d = 0; d + TAILLE <= tousIdx.length; d += TAILLE) {
      const { g } = lot(r, A.X, A.Y, tousIdx.slice(d, d + TAILLE));
      pas(r, opt, g, 0.004, 3e-4);
    }
    const v = perteSur(r, T.X, T.Y, testIdx);
    if (v < meilleur) { meilleur = v; gardes = copier(); epMeilleure = ep; }
    if (ep % 5 === 0)
      console.log(`  époque ${String(ep).padStart(2)} : ` +
                  `apprentissage ${perteSur(r, A.X, A.Y, tousIdx.slice(0, 800)).toFixed(4)}  ` +
                  `mis de côté ${v.toFixed(4)}`);
  }
  Object.assign(r, gardes);
  console.log(`  meilleur passage : époque ${epMeilleure}, perte ${meilleur.toFixed(4)}`);
  console.log(`  entraînement : ${((Date.now() - t0) / 1000).toFixed(1)} s`);

  // la référence markovienne, sur les mêmes données
  const mk = markov(augmente, steps);
  let lm = 0, n = 0;
  for (const pasM of test)
    for (let s = 0; s < steps; s++) {
      const ev = pasM[s].notes.join(",") + (pasM[s].tenue ? "=" : "");
      lm -= Math.log(probaMarkov(mk, pasM, s, ev)); n++;
    }
  console.log(`  Markov d'ordre variable, sur les mêmes motifs mis de côté : ` +
              `${(lm / n).toFixed(4)} par pas (log-vraisemblance négative)`);
  // la densité moyenne du corpus : le modèle ne l'invente pas, on la lui donne
  let notes = 0, total = 0;
  for (const m of app) for (const v of m) { if (v.notes.length) notes++; total++; }
  const densite = notes / total;
  console.log(`  densité du corpus : ${(densite * 100).toFixed(0)} % des pas portent une note`);
  console.log("  ce qu'il compose, en ré mineur :");
  for (const temp of [0.6, 0.9, 1.3])
    console.log(`    température ${temp} : ${ecrire(composer(r, steps, [0,2,3,5,7,8,10], 2, temp, alea, Math.round(steps * densite), densite))}`);
}

// ------------------------------------------------- ce qu'il compose vraiment
// La perte dit qu'il prédit bien ; elle ne dit pas qu'il écrit bien. On génère
// pas à pas, en imposant la gamme comme contrainte dure : le réseau propose,
// la théorie dispose. Un modèle faible donne alors du médiocre écoutable ; un
// modèle fort donne du bon. Dans les deux cas, jamais de fausse note.
function composer(r, steps, gammePas, tonique, temperature, alea, cible, moyNote) {
  const pas = [];
  let poses = 0;
  const dansGamme = n => gammePas.includes((((n - tonique) % 12) + 12) % 12);
  for (let s = 0; s < steps; s++) {
    const e = new Float64Array(K * SORTIES + 16 + 28);
    for (let k = 0; k < K; k++) {
      const idx = s - K + k;
      if (idx >= 0) e.set(vecteur(pas[idx]), k * SORTIES);
    }
    e[K * SORTIES + (s % 16)] = 1;
    let der = -1;
    for (let k = s - 1; k >= 0 && der < 0; k--) if (pas[k].notes.length) der = pas[k].notes[0];
    const base = K * SORTIES + 16;
    e[base + 25] = 1;                          // l'intervalle n'est pas encore connu
    if (s % 4 === 0) e[base + 26] = 1;
    if (s % 16 === 0) e[base + 27] = 1;
    const actifs = [];
    for (let i = 0; i < e.length; i++) if (e[i]) actifs.push(i);
    const { y } = avant(r, actifs);

    // Un bon prédicteur n'est pas un bon générateur : le silence est majoritaire
    // dans le corpus, donc le modèle le prédit très bien, et livré à lui-même il
    // s'y enfonce et n'en sort plus. On lui impose la densité — combien de notes
    // dans le motif — et il ne décide plus que d'où elles tombent et lesquelles.
    const restants = cible - poses, dispo = steps - s;
    let pNote = Math.pow(1 - y[13], 1 / temperature);
    if (restants <= 0) pNote = 0;
    else if (restants >= dispo) pNote = 1;
    else pNote = Math.min(1, pNote * (restants / dispo) / Math.max(0.02, moyNote));
    if (alea() >= pNote) { pas.push({ notes: [], tenue: y[14] > 0.5, accent: false }); continue; }
    poses++;
    // on ne retient que les hauteurs de la gamme, et l'on tire parmi elles
    const cand = [];
    for (let n = 0; n < ROWS; n++) if (dansGamme(n)) cand.push([n, Math.pow(y[n], 1 / temperature)]);
    const tot = cand.reduce((a, c) => a + c[1], 0);
    let t = alea() * tot, choix = cand[0][0];
    for (const [n, w] of cand) { t -= w; if (t <= 0) { choix = n; break; } }
    pas.push({ notes: [choix], tenue: false, accent: y[15] > 0.55 });
  }
  return pas;
}
// Déclarée en « function » et non en « const » : elle est appelée plus haut
// dans le fichier, et une const n'est pas hissée — la zone morte lève.
function ecrire(pas) {
  return pas.map(v => v.notes.length
    ? (v.accent ? ACC : LOW)[v.notes[0]] : (v.tenue ? "=" : "-")).join("");
}
