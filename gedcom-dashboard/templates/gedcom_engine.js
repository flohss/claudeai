/* ==================================================================== *
 * Moteur GEDCOM côté navigateur : parsing, analyse, sérialisation et
 * gestion d'état (ajout / modification / suppression). Portage fidèle de
 * gedcom_parser.py et gedcom_analyze.py afin que le chargement d'un
 * fichier .ged et les éditions puissent tout recalculer en direct, sans
 * dépendance externe ni backend.
 * ==================================================================== */

const MONTHS_FR = {
  JAN: 1, FEV: 2, FEB: 2, MAR: 3, AVR: 4, APR: 4, MAI: 5, MAY: 5,
  JUN: 6, JUIN: 6, JUL: 7, JUIL: 7, AOU: 8, AUG: 8, SEP: 9,
  OCT: 10, NOV: 11, DEC: 12,
};
const MONTH_NAMES = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const MONTH_LABELS_FR = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];

/* ---------------------------------------------------------------- */
/* Dates GEDCOM                                                       */
/* ---------------------------------------------------------------- */

function makeGedDate(raw, year, month, day, qualifier, year2){
  return {
    raw: raw || '',
    year: year != null ? year : null,
    month: month != null ? month : null,
    day: day != null ? day : null,
    qualifier: qualifier || null,
    year2: year2 != null ? year2 : null,
  };
}

function gedDateSortKey(d){
  if (!d || d.year == null) return Infinity;
  return d.year * 372 + (d.month || 1) * 31 + (d.day || 1);
}

function gedDateDisplay(d){
  if (!d || d.year == null) return (d && d.raw) || '?';
  let base;
  if (d.day && d.month) base = `${String(d.day).padStart(2, '0')}/${String(d.month).padStart(2, '0')}/${d.year}`;
  else if (d.month) base = `${String(d.month).padStart(2, '0')}/${d.year}`;
  else base = String(d.year);
  const prefix = {
    ABT: 'vers ', EST: 'vers (est.) ', CAL: 'calculé ',
    BEF: 'avant ', AFT: 'après ', BET: 'entre ', FROM: 'de ',
  }[d.qualifier] || '';
  let txt = prefix + base;
  if ((d.qualifier === 'BET' || d.qualifier === 'FROM') && d.year2) txt += ` et ${d.year2}`;
  return txt;
}

function parseGedcomDate(raw){
  if (!raw) return null;
  raw = String(raw).trim();
  if (!raw) return null;

  let tokens = raw.toUpperCase().replace(/,/g, ' ').split(/\s+/).filter(Boolean);
  let qualifier = null;
  if (tokens.length && ['ABT', 'BEF', 'AFT', 'EST', 'CAL', 'FROM'].includes(tokens[0])) {
    qualifier = tokens[0];
    tokens = tokens.slice(1);
  } else if (tokens.length && tokens[0] === 'BET') {
    qualifier = 'BET';
    tokens = tokens.slice(1);
  }

  let year2 = null;
  if (qualifier === 'BET' && tokens.includes('AND')) {
    const idx = tokens.indexOf('AND');
    const tail = tokens.slice(idx + 1);
    tokens = tokens.slice(0, idx);
    const y2 = tail.find(t => /^\d{3,4}$/.test(t));
    year2 = y2 ? parseInt(y2, 10) : null;
  } else if (qualifier === 'FROM' && tokens.includes('TO')) {
    const idx = tokens.indexOf('TO');
    const tail = tokens.slice(idx + 1);
    tokens = tokens.slice(0, idx);
    const y2 = tail.find(t => /^\d{3,4}$/.test(t));
    year2 = y2 ? parseInt(y2, 10) : null;
  }

  let day = null, month = null, year = null;
  for (const tok of tokens) {
    if (MONTHS_FR[tok] !== undefined) month = MONTHS_FR[tok];
    else if (/^\d{3,4}$/.test(tok)) year = parseInt(tok, 10);
    else if (/^\d{1,2}$/.test(tok)) day = parseInt(tok, 10);
  }

  if (year == null) return makeGedDate(raw, null, null, null, qualifier, null);
  return makeGedDate(raw, year, month, day, qualifier, year2);
}

/** Construit une chaîne de date GEDCOM à partir de champs de formulaire. */
function buildGedcomDateString(qualifier, day, month, year){
  const parts = [];
  if (qualifier) parts.push(qualifier);
  if (day) parts.push(String(day));
  if (month) parts.push(MONTH_NAMES[month - 1]);
  if (year) parts.push(String(year));
  return parts.join(' ');
}

/* ---------------------------------------------------------------- */
/* Parsing GEDCOM (texte -> individus / familles bruts)               */
/* ---------------------------------------------------------------- */

function tokenizeGedcom(text){
  const lines = [];
  const rawLines = text.split(/\r\n|\r|\n/);
  const re = /^(\d+)\s+(@[^@]+@)?\s*([A-Za-z0-9_]+)\s?(.*)$/;
  for (const rawLine of rawLines) {
    const line = rawLine.replace(/\s+$/, '');
    if (!line.trim()) continue;
    const m = line.match(re);
    if (!m) continue;
    lines.push([parseInt(m[1], 10), m[2] || null, m[3], m[4] || '']);
  }
  return lines;
}

function newBlankIndividual(xref){
  return {
    xref,
    given: '', surname: '', full_name: '', sex: 'U',
    birth: { date: null, place: null, known: false },
    death: { date: null, place: null, cause: null, known: false },
    occupation: null,
    fams: [], famc: [],
  };
}
function newBlankFamily(xref){
  return {
    xref, husb: null, wife: null, chil: [],
    marriage: { date: null, place: null, known: false },
    divorced: false,
  };
}

function parseGedcomText(text){
  const lines = tokenizeGedcom(text);
  const individuals = new Map();
  const families = new Map();
  let headerSource = null;
  let headerAuthor = null;
  const n = lines.length;
  let i = 0;

  while (i < n) {
    const [level, xref, tag, value] = lines[i];

    if (level === 0 && tag === 'INDI' && xref) {
      const ind = newBlankIndividual(xref);
      i++;
      let ctxTag = null, ctxObj = null;
      while (i < n && lines[i][0] > 0) {
        const [lv, , ltag, lval] = lines[i];
        if (lv === 1) {
          ctxTag = null; ctxObj = null;
          if (ltag === 'NAME') {
            ind.full_name = lval.replace(/\//g, '').trim();
            const m = lval.match(/^(.*?)\/(.*)\//);
            if (m) { ind.given = m[1].trim(); ind.surname = m[2].trim(); }
            else { ind.given = lval.trim(); }
            ctxTag = 'NAME';
          } else if (ltag === 'SEX') {
            ind.sex = (lval.trim()[0]) || 'U';
          } else if (ltag === 'BIRT') {
            ind.birth.known = true; ctxTag = 'BIRT'; ctxObj = ind.birth;
          } else if (ltag === 'DEAT') {
            ind.death.known = true; ctxTag = 'DEAT'; ctxObj = ind.death;
          } else if (ltag === 'OCCU') {
            ind.occupation = lval.trim() || null;
          } else if (ltag === 'FAMS') {
            ind.fams.push(lval.trim());
          } else if (ltag === 'FAMC') {
            ind.famc.push(lval.trim());
          }
        } else if (lv === 2 && ctxObj && (ctxTag === 'BIRT' || ctxTag === 'DEAT')) {
          if (ltag === 'DATE') ctxObj.date = parseGedcomDate(lval);
          else if (ltag === 'PLAC') ctxObj.place = lval.trim() || null;
          else if (ltag === 'CAUS') ctxObj.cause = lval.trim() || null;
        }
        i++;
      }
      individuals.set(xref, ind);
      continue;
    }

    if (level === 0 && tag === 'FAM' && xref) {
      const fam = newBlankFamily(xref);
      i++;
      let inMarr = false;
      while (i < n && lines[i][0] > 0) {
        const [lv, , ltag, lval] = lines[i];
        if (lv === 1) {
          inMarr = false;
          if (ltag === 'HUSB') fam.husb = lval.trim();
          else if (ltag === 'WIFE') fam.wife = lval.trim();
          else if (ltag === 'CHIL') fam.chil.push(lval.trim());
          else if (ltag === 'MARR') { fam.marriage.known = true; inMarr = true; }
          else if (ltag === 'DIV') fam.divorced = true;
        } else if (lv === 2 && inMarr) {
          if (ltag === 'DATE') fam.marriage.date = parseGedcomDate(lval);
          else if (ltag === 'PLAC') fam.marriage.place = lval.trim() || null;
        }
        i++;
      }
      families.set(xref, fam);
      continue;
    }

    if (level === 0 && tag === 'SOUR' && xref) {
      i++;
      while (i < n && lines[i][0] > 0) {
        const [lv, , ltag, lval] = lines[i];
        if (lv === 2 && ltag === 'NAME' && headerSource == null) headerSource = lval.trim();
        if (lv === 1 && ltag === 'AUTH' && headerAuthor == null) headerAuthor = lval.trim();
        i++;
      }
      continue;
    }

    i++;
  }

  return { individuals, families, headerSource, headerAuthor };
}

/* ---------------------------------------------------------------- */
/* Sérialisation (état en mémoire -> texte GEDCOM 5.5.1)              */
/* ---------------------------------------------------------------- */

function gedcomEscapeName(given, surname){
  return `${given || ''} /${surname || ''}/`.trim();
}

function serializeGedcom(gs){
  const out = [];
  out.push('0 HEAD');
  out.push('1 GEDC');
  out.push('2 VERS 5.5.1');
  out.push('2 FORM LINEAGE-LINKED');
  out.push('1 CHAR UTF-8');
  out.push('1 LANG French');
  const now = new Date();
  const dd = String(now.getDate()).padStart(2, '0');
  const mon = MONTH_NAMES[now.getMonth()];
  out.push(`1 DATE ${dd} ${mon} ${now.getFullYear()}`);

  for (const ind of gs.individuals.values()) {
    out.push(`0 ${ind.xref} INDI`);
    out.push(`1 NAME ${gedcomEscapeName(ind.given, ind.surname)}`);
    if (ind.given) out.push(`2 GIVN ${ind.given}`);
    if (ind.surname) out.push(`2 SURN ${ind.surname}`);
    out.push(`1 SEX ${ind.sex || 'U'}`);
    if (ind.birth.known || ind.birth.date || ind.birth.place) {
      out.push('1 BIRT');
      if (ind.birth.date) out.push(`2 DATE ${ind.birth.date.raw}`);
      if (ind.birth.place) out.push(`2 PLAC ${ind.birth.place}`);
    }
    if (ind.death.known || ind.death.date || ind.death.place) {
      out.push('1 DEAT Y');
      if (ind.death.date) out.push(`2 DATE ${ind.death.date.raw}`);
      if (ind.death.place) out.push(`2 PLAC ${ind.death.place}`);
      if (ind.death.cause) out.push(`2 CAUS ${ind.death.cause}`);
    }
    if (ind.occupation) out.push(`1 OCCU ${ind.occupation}`);
    for (const f of ind.fams) out.push(`1 FAMS ${f}`);
    for (const f of ind.famc) out.push(`1 FAMC ${f}`);
  }

  for (const fam of gs.families.values()) {
    out.push(`0 ${fam.xref} FAM`);
    if (fam.husb) out.push(`1 HUSB ${fam.husb}`);
    if (fam.wife) out.push(`1 WIFE ${fam.wife}`);
    for (const c of fam.chil) out.push(`1 CHIL ${c}`);
    if (fam.marriage.known || fam.marriage.date || fam.marriage.place) {
      out.push('1 MARR');
      if (fam.marriage.date) out.push(`2 DATE ${fam.marriage.date.raw}`);
      if (fam.marriage.place) out.push(`2 PLAC ${fam.marriage.place}`);
    }
    if (fam.divorced) out.push('1 DIV Y');
  }

  if (gs.headerAuthor || gs.headerSource) {
    out.push('0 @SRC1@ SOUR');
    if (gs.headerAuthor) out.push(`1 AUTH ${gs.headerAuthor}`);
    if (gs.headerSource) { out.push('1 DATA'); out.push(`2 NAME ${gs.headerSource}`); }
  }

  out.push('0 TRLR');
  return out.join('\n') + '\n';
}

/* ---------------------------------------------------------------- */
/* Statistiques (portage fidèle de gedcom_analyze.py)                 */
/* ---------------------------------------------------------------- */

function mean(arr){ return arr.reduce((a, b) => a + b, 0) / arr.length; }
function median(arr){
  const s = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}
function round1(x){ return Math.round(x * 10) / 10; }
function round2(x){ return Math.round(x * 100) / 100; }

function counterAdd(map, key, delta){
  if (key === null || key === undefined) return;
  map.set(key, (map.get(key) || 0) + (delta === undefined ? 1 : delta));
}
function counterMostCommon(map, n){
  const arr = Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
  return n ? arr.slice(0, n) : arr;
}

function placeParts(place){
  if (!place) return [];
  return place.split(',').map(p => p.trim()).filter(Boolean);
}
function placeRegion(place){
  const parts = placeParts(place);
  if (parts.length >= 2) return parts[parts.length - 2];
  return parts.length ? parts[parts.length - 1] : null;
}
function placeCountry(place){
  const parts = placeParts(place);
  return parts.length ? parts[parts.length - 1] : null;
}

function ageYears(by, bm, bd, ey, em, ed){
  if (by == null || ey == null) return null;
  let age = ey - by;
  const bmv = bm || 1, bdv = bd || 1, emv = em || 1, edv = ed || 1;
  if (emv < bmv || (emv === bmv && edv < bdv)) age -= 1;
  return age;
}

function displayName(ind){
  return ind.full_name || `${ind.given} ${ind.surname}`.trim() || '(nom non renseigné)';
}

function findProband(gs){
  if (gs.headerAuthor) {
    const target = new Set(gs.headerAuthor.toUpperCase().split(/\s+/).filter(Boolean));
    let best = null, bestScore = 0;
    for (const [xref, ind] of gs.individuals) {
      const tokens = new Set(`${ind.given} ${ind.surname}`.toUpperCase().split(/\s+/).filter(Boolean));
      let score = 0;
      for (const t of tokens) if (target.has(t)) score++;
      if (score > bestScore && score >= 2) { best = xref; bestScore = score; }
    }
    if (best) return best;
  }
  for (const [xref, ind] of gs.individuals) if (ind.famc.length) return xref;
  const first = gs.individuals.keys().next();
  return first.done ? null : first.value;
}

function computeGenerations(gs, root){
  const generation = new Map();
  if (root == null) return generation;
  const visitedGlobal = new Set();
  const allIds = Array.from(gs.individuals.keys());
  const startNodes = [root, ...allIds.filter(x => x !== root)];

  for (const start of startNodes) {
    if (visitedGlobal.has(start)) continue;
    const compGen = new Map([[start, 0]]);
    const queue = [start];
    let head = 0;
    while (head < queue.length) {
      const cur = queue[head++];
      const gen = compGen.get(cur);
      const ind = gs.individuals.get(cur);
      if (!ind) continue;
      for (const famcId of ind.famc) {
        const fam = gs.families.get(famcId);
        if (!fam) continue;
        for (const parent of [fam.husb, fam.wife]) {
          if (parent && !compGen.has(parent)) { compGen.set(parent, gen - 1); queue.push(parent); }
        }
      }
      for (const famsId of ind.fams) {
        const fam = gs.families.get(famsId);
        if (!fam) continue;
        const spouse = fam.husb === cur ? fam.wife : fam.husb;
        if (spouse && !compGen.has(spouse)) { compGen.set(spouse, gen); queue.push(spouse); }
        for (const childId of fam.chil) {
          if (!compGen.has(childId)) { compGen.set(childId, gen + 1); queue.push(childId); }
        }
      }
    }
    for (const k of compGen.keys()) visitedGlobal.add(k);
    for (const [k, v] of compGen) generation.set(k, v);
  }
  return generation;
}

function histogram(values, binSize, maxVal){
  const nBins = Math.floor(maxVal / binSize);
  const counts = new Array(nBins).fill(0);
  for (const v of values) {
    const idx = Math.min(Math.floor(v / binSize), counts.length - 1);
    counts[idx]++;
  }
  return counts.map((c, i) => ({ range: `${i * binSize}-${(i + 1) * binSize - 1}`, count: c }));
}

/** Analyse complète : reproduit exactement la forme de sortie de gedcom_analyze.py */
function analyzeGedcom(gs){
  const CURRENT_YEAR = new Date().getFullYear();
  const individuals = gs.individuals;
  const families = gs.families;

  const root = findProband(gs);
  const generation = computeGenerations(gs, root);

  const childrenOf = new Map(), parentsOf = new Map(), spousesOf = new Map();
  const push = (map, key, val) => { if (!map.has(key)) map.set(key, []); map.get(key).push(val); };

  for (const fam of families.values()) {
    const parents = [fam.husb, fam.wife].filter(Boolean);
    for (const p of parents) for (const c of fam.chil) push(childrenOf, p, c);
    for (const c of fam.chil) { if (!parentsOf.has(c)) parentsOf.set(c, []); parentsOf.get(c).push(...parents); }
    if (fam.husb && fam.wife) { push(spousesOf, fam.husb, fam.wife); push(spousesOf, fam.wife, fam.husb); }
  }
  const siblingsOf = new Map();
  for (const fam of families.values()) {
    for (const c of fam.chil) {
      if (!siblingsOf.has(c)) siblingsOf.set(c, new Set());
      for (const c2 of fam.chil) if (c2 !== c) siblingsOf.get(c).add(c2);
    }
  }

  const indRecords = [];
  const agesAtDeath = [];
  const aliveRecords = [];
  let deceasedCount = 0;

  for (const [xref, ind] of individuals) {
    const by = ind.birth.date ? ind.birth.date.year : null;
    const bm = ind.birth.date ? ind.birth.date.month : null;
    const bd = ind.birth.date ? ind.birth.date.day : null;
    const dy = ind.death.date ? ind.death.date.year : null;
    const dm = ind.death.date ? ind.death.date.month : null;
    const dd = ind.death.date ? ind.death.date.day : null;

    let ageAtDeath = null;
    if (ind.death.known) {
      deceasedCount++;
      if (by != null && dy != null) {
        const a = ageYears(by, bm, bd, dy, dm, dd);
        if (a != null && a >= 0 && a <= 115) { ageAtDeath = a; agesAtDeath.push(a); }
      }
    }

    const isAlive = !ind.death.known && (by == null || (CURRENT_YEAR - by) < 100);
    let currentAge = null;
    if (isAlive && by != null) { currentAge = CURRENT_YEAR - by; aliveRecords.push([xref, currentAge]); }

    indRecords.push({
      id: xref,
      given: ind.given, surname: ind.surname, name: displayName(ind),
      sex: (ind.sex === 'M' || ind.sex === 'F') ? ind.sex : 'U',
      birth: { year: by, month: bm, day: bd, display: ind.birth.date ? gedDateDisplay(ind.birth.date) : null, place: ind.birth.place, known: ind.birth.known },
      death: { year: dy, month: dm, day: dd, display: ind.death.date ? gedDateDisplay(ind.death.date) : null, place: ind.death.place, cause: ind.death.cause, known: ind.death.known },
      age_at_death: ageAtDeath, current_age: currentAge, alive: isAlive,
      occupation: ind.occupation, generation: generation.has(xref) ? generation.get(xref) : null,
      parents: Array.from(new Set(parentsOf.get(xref) || [])).sort(),
      children: Array.from(new Set(childrenOf.get(xref) || [])).sort(),
      siblings: Array.from(siblingsOf.get(xref) || []).sort(),
      spouses: Array.from(new Set(spousesOf.get(xref) || [])).sort(),
      famc: ind.famc, fams: ind.fams,
    });
  }
  const indById = new Map(indRecords.map(r => [r.id, r]));

  const famRecords = [];
  const remarriagePeople = new Map();
  for (const [xref, fam] of families) {
    const husb = indById.get(fam.husb), wife = indById.get(fam.wife);
    const mYear = fam.marriage.date ? fam.marriage.date.year : null;
    let ageHusb = null, ageWife = null;
    if (mYear) {
      if (husb && husb.birth.year) ageHusb = mYear - husb.birth.year;
      if (wife && wife.birth.year) ageWife = mYear - wife.birth.year;
    }
    let ageGap = null;
    if (husb && wife && husb.birth.year && wife.birth.year) ageGap = husb.birth.year - wife.birth.year;

    famRecords.push({
      id: xref, husb: fam.husb, wife: fam.wife,
      husb_name: husb ? husb.name : null, wife_name: wife ? wife.name : null,
      children: fam.chil, n_children: fam.chil.length,
      marriage: { year: mYear, display: fam.marriage.date ? gedDateDisplay(fam.marriage.date) : null, place: fam.marriage.place, known: fam.marriage.known },
      divorced: fam.divorced,
      age_husb_at_marriage: ageHusb, age_wife_at_marriage: ageWife, spouse_age_gap: ageGap,
    });
    if (fam.husb) counterAdd(remarriagePeople, fam.husb);
    if (fam.wife) counterAdd(remarriagePeople, fam.wife);
  }

  /* ---- Démographie ---- */
  const total = indRecords.length;
  const sexCounts = new Map();
  for (const r of indRecords) counterAdd(sexCounts, r.sex);
  const genCounts = new Map();
  for (const r of indRecords) if (r.generation != null) counterAdd(genCounts, r.generation);

  const ageByCentury = new Map();
  for (const r of indRecords) {
    if (r.age_at_death != null && r.death.year) {
      const century = Math.floor((r.death.year - 1) / 100) + 1;
      if (!ageByCentury.has(century)) ageByCentury.set(century, []);
      ageByCentury.get(century).push(r.age_at_death);
    }
  }
  const ageDistByCentury = {};
  for (const c of Array.from(ageByCentury.keys()).sort((a, b) => a - b)) {
    const v = ageByCentury.get(c);
    ageDistByCentury[String(c)] = { count: v.length, mean: round1(mean(v)), median: median(v) };
  }

  const pyramidBins = [];
  for (let b = 0; b <= 100; b += 10) pyramidBins.push(b);
  const pyramid = new Map(pyramidBins.map(b => [b, { M: 0, F: 0 }]));
  for (const r of indRecords) {
    const age = r.age_at_death != null ? r.age_at_death : r.current_age;
    if (age == null || (r.sex !== 'M' && r.sex !== 'F')) continue;
    const b = Math.min(Math.floor(age / 10) * 10, 100);
    pyramid.get(b)[r.sex]++;
  }
  const agePyramid = pyramidBins.map(b => ({ band: b < 100 ? `${b}-${b + 9}` : '100+', M: pyramid.get(b).M, F: pyramid.get(b).F }));

  let oldestLiving = null;
  for (const [id, age] of aliveRecords) if (!oldestLiving || age > oldestLiving[1]) oldestLiving = [id, age];
  let oldestDeath = null, youngestDeath = null;
  for (const r of indRecords) {
    if (r.age_at_death == null) continue;
    if (!oldestDeath || r.age_at_death > oldestDeath.age_at_death) oldestDeath = r;
    if (!youngestDeath || r.age_at_death < youngestDeath.age_at_death) youngestDeath = r;
  }

  const demographics = {
    total_individuals: total,
    sex_counts: { M: sexCounts.get('M') || 0, F: sexCounts.get('F') || 0, U: sexCounts.get('U') || 0 },
    generation_counts: Object.fromEntries(Array.from(genCounts.entries()).sort((a, b) => a[0] - b[0]).map(([k, v]) => [String(k), v])),
    age_at_death: {
      count: agesAtDeath.length,
      mean: agesAtDeath.length ? round1(mean(agesAtDeath)) : null,
      median: agesAtDeath.length ? median(agesAtDeath) : null,
      min: agesAtDeath.length ? Math.min(...agesAtDeath) : null,
      max: agesAtDeath.length ? Math.max(...agesAtDeath) : null,
      distribution_by_century: ageDistByCentury,
      histogram: histogram(agesAtDeath, 10, 110),
    },
    alive_count: indRecords.filter(r => r.alive).length,
    deceased_count: deceasedCount,
    unknown_status_count: total - deceasedCount - indRecords.filter(r => r.alive).length,
    age_pyramid: agePyramid,
    oldest_living: oldestLiving ? { id: oldestLiving[0], name: indById.get(oldestLiving[0]).name, age: oldestLiving[1] } : null,
    oldest_at_death: oldestDeath ? { id: oldestDeath.id, name: oldestDeath.name, age: oldestDeath.age_at_death, date: oldestDeath.death.display } : null,
    youngest_at_death: youngestDeath ? { id: youngestDeath.id, name: youngestDeath.name, age: youngestDeath.age_at_death, date: youngestDeath.death.display } : null,
  };

  /* ---- Chronologie ---- */
  const decadeCounter = (years) => {
    const c = new Map();
    for (const y of years) if (y != null) counterAdd(c, Math.floor(y / 10) * 10);
    return Object.fromEntries(Array.from(c.entries()).sort((a, b) => a[0] - b[0]));
  };
  const birthYears = indRecords.map(r => r.birth.year).filter(y => y);
  const deathYears = indRecords.map(r => r.death.year).filter(y => y);
  const marriageYears = famRecords.map(f => f.marriage.year).filter(y => y);

  const gaps = [];
  for (const r of indRecords) {
    const by = r.birth.year;
    if (!by) continue;
    for (const pid of r.parents) {
      const p = indById.get(pid);
      if (p && p.birth.year) {
        const gap = by - p.birth.year;
        if (gap >= 10 && gap <= 70) gaps.push(gap);
      }
    }
  }
  const knownGens = Array.from(generation.values()).filter(g => g != null);

  const genYearRange = new Map();
  for (const r of indRecords) {
    if (r.generation != null && r.birth.year) {
      if (!genYearRange.has(r.generation)) genYearRange.set(r.generation, []);
      genYearRange.get(r.generation).push(r.birth.year);
    }
  }
  const generationTimeline = Array.from(genYearRange.entries()).sort((a, b) => a[0] - b[0])
    .map(([g, v]) => ({ generation: g, min_year: Math.min(...v), max_year: Math.max(...v), count: v.length }));

  const chronology = {
    births_by_decade: decadeCounter(birthYears),
    marriages_by_decade: decadeCounter(marriageYears),
    deaths_by_decade: decadeCounter(deathYears),
    earliest_birth_year: birthYears.length ? Math.min(...birthYears) : null,
    latest_birth_year: birthYears.length ? Math.max(...birthYears) : null,
    tree_depth_generations: knownGens.length ? (Math.max(...knownGens) - Math.min(...knownGens) + 1) : 0,
    oldest_generation: knownGens.length ? Math.min(...knownGens) : null,
    youngest_generation: knownGens.length ? Math.max(...knownGens) : null,
    avg_generational_gap: gaps.length ? round1(mean(gaps)) : null,
    generational_gap_sample_size: gaps.length,
    generation_timeline: generationTimeline,
  };

  /* ---- Géographie ---- */
  const birthPlaces = new Map(), deathPlaces = new Map(), marriagePlaces = new Map(), birthRegions = new Map(), birthCountries = new Map();
  for (const r of indRecords) {
    if (r.birth.place) {
      counterAdd(birthPlaces, r.birth.place);
      counterAdd(birthRegions, placeRegion(r.birth.place));
      counterAdd(birthCountries, placeCountry(r.birth.place));
    }
    if (r.death.place) counterAdd(deathPlaces, r.death.place);
  }
  for (const f of famRecords) if (f.marriage.place) counterAdd(marriagePlaces, f.marriage.place);

  const migrations = [];
  let migrationCount = 0;
  for (const r of indRecords) {
    const bp = r.birth.place, dp = r.death.place;
    if (bp && dp) {
      const br = placeRegion(bp), dr = placeRegion(dp);
      if (br && dr && br !== dr) {
        migrationCount++;
        if (migrations.length < 60) migrations.push({ id: r.id, name: r.name, from: bp, to: dp });
      }
    }
  }

  const geography = {
    birth_places_top: counterMostCommon(birthPlaces, 20),
    death_places_top: counterMostCommon(deathPlaces, 20),
    marriage_places_top: counterMostCommon(marriagePlaces, 20),
    birth_regions_top: counterMostCommon(birthRegions, 15).filter(([k]) => k),
    birth_countries_top: counterMostCommon(birthCountries, 10).filter(([k]) => k),
    migrations_count: migrationCount,
    migrations_sample: migrations,
    concentration_zones: counterMostCommon(birthRegions, 8).filter(([k]) => k),
  };

  /* ---- Structure familiale ---- */
  const siblingSizes = famRecords.filter(f => f.n_children > 0).map(f => f.n_children);
  const largeFamilies = famRecords.filter(f => f.n_children >= 5);
  const agesHusb = famRecords.map(f => f.age_husb_at_marriage).filter(a => a != null && a >= 10 && a <= 90);
  const agesWife = famRecords.map(f => f.age_wife_at_marriage).filter(a => a != null && a >= 10 && a <= 90);
  const allMarriageAges = [...agesHusb, ...agesWife];
  const ageGaps = famRecords.map(f => f.spouse_age_gap).filter(g => g != null && Math.abs(g) <= 40).map(Math.abs);

  const remarried = Array.from(remarriagePeople.entries()).filter(([, cnt]) => cnt > 1);
  const remarriedDetails = remarried.filter(([pid]) => indById.has(pid)).map(([pid, cnt]) => ({ id: pid, name: indById.get(pid).name, n_unions: cnt }));

  const familyStructure = {
    total_families: famRecords.length,
    avg_children_per_family: siblingSizes.length ? round2(mean(siblingSizes)) : null,
    median_children_per_family: siblingSizes.length ? median(siblingSizes) : null,
    large_families_count: largeFamilies.length,
    large_families_sample: [...largeFamilies].sort((a, b) => b.n_children - a.n_children).slice(0, 15)
      .map(f => ({ id: f.id, husb: f.husb_name, wife: f.wife_name, husb_id: f.husb, wife_id: f.wife, n_children: f.n_children })),
    avg_age_at_marriage: allMarriageAges.length ? round1(mean(allMarriageAges)) : null,
    avg_age_at_marriage_husb: agesHusb.length ? round1(mean(agesHusb)) : null,
    avg_age_at_marriage_wife: agesWife.length ? round1(mean(agesWife)) : null,
    avg_spouse_age_gap: ageGaps.length ? round1(mean(ageGaps)) : null,
    remarriages_count: remarriedDetails.length,
    remarriages_sample: [...remarriedDetails].sort((a, b) => b.n_unions - a.n_unions).slice(0, 20),
    divorced_families: famRecords.filter(f => f.divorced).length,
  };

  /* ---- Patronymes ---- */
  const surnameCasing = new Map();
  for (const r of indRecords) {
    if (r.surname) {
      const key = r.surname.trim().toUpperCase();
      if (!surnameCasing.has(key)) surnameCasing.set(key, new Map());
      counterAdd(surnameCasing.get(key), r.surname.trim());
    }
  }
  const surnameCanonical = new Map();
  for (const [key, variants] of surnameCasing) surnameCanonical.set(key, counterMostCommon(variants, 1)[0][0]);

  const surnameCounts = new Map();
  for (const r of indRecords) if (r.surname) counterAdd(surnameCounts, surnameCanonical.get(r.surname.trim().toUpperCase()));

  const surnameByPeriod = new Map();
  for (const r of indRecords) {
    if (r.surname && r.birth.year) {
      const period = Math.floor(r.birth.year / 50) * 50;
      if (!surnameByPeriod.has(period)) surnameByPeriod.set(period, new Map());
      counterAdd(surnameByPeriod.get(period), surnameCanonical.get(r.surname.trim().toUpperCase()));
    }
  }
  const surnameEvolution = {};
  for (const period of Array.from(surnameByPeriod.keys()).sort((a, b) => a - b)) {
    surnameEvolution[String(period)] = counterMostCommon(surnameByPeriod.get(period), 5);
  }

  const surnames = {
    total_distinct: surnameCounts.size,
    top_surnames: counterMostCommon(surnameCounts, 25),
    evolution_by_period: surnameEvolution,
  };

  /* ---- Qualité des données ---- */
  const anomalies = [];
  for (const r of indRecords) {
    const by = r.birth.year, dy = r.death.year;
    if (by && !r.death.known && (CURRENT_YEAR - by) >= 100) {
      anomalies.push({ type: 'deces_manquant_probable', id: r.id, name: r.name, detail: `Né(e) en ${by} (aurait ${CURRENT_YEAR - by} ans), aucun décès enregistré` });
    }
    if (by && dy && dy < by) anomalies.push({ type: 'deces_avant_naissance', id: r.id, name: r.name, detail: `Naissance ${by}, décès ${dy}` });
    if (by && dy && (dy - by) > 115) anomalies.push({ type: 'age_deces_invraisemblable', id: r.id, name: r.name, detail: `Âge au décès : ${dy - by} ans` });
    for (const pid of r.parents) {
      const p = indById.get(pid);
      if (p && p.birth.year && by) {
        const gap = by - p.birth.year;
        if (gap < 0) anomalies.push({ type: 'enfant_avant_parent', id: r.id, name: r.name, detail: `Né(e) en ${by}, avant la naissance de ${p.name} (${p.birth.year})` });
        else if (gap < 10) anomalies.push({ type: 'parent_trop_jeune', id: r.id, name: r.name, detail: `${p.name} n'avait que ${gap} ans à sa naissance` });
        else if (gap > 65) anomalies.push({ type: 'parent_trop_age', id: r.id, name: r.name, detail: `${p.name} avait ${gap} ans à sa naissance` });
      }
    }
  }
  for (const f of famRecords) {
    if (f.marriage.year) {
      for (const [role, age] of [['époux', f.age_husb_at_marriage], ['épouse', f.age_wife_at_marriage]]) {
        if (age != null && age < 12) anomalies.push({ type: 'mariage_trop_jeune', id: f.id, name: `${f.husb_name} × ${f.wife_name}`, detail: `${role} âgé(e) de ${age} ans au mariage` });
      }
    }
  }

  const completenessFields = {
    date_naissance: total ? indRecords.filter(r => r.birth.year).length / total : 0,
    lieu_naissance: total ? indRecords.filter(r => r.birth.place).length / total : 0,
    date_deces: deceasedCount ? indRecords.filter(r => r.death.known && r.death.year).length / deceasedCount : 0,
    lieu_deces: deceasedCount ? indRecords.filter(r => r.death.known && r.death.place).length / deceasedCount : 0,
    sexe_connu: total ? indRecords.filter(r => r.sex === 'M' || r.sex === 'F').length / total : 0,
    famille_parentale_connue: total ? indRecords.filter(r => r.parents.length).length / total : 0,
  };

  const titleCase = (s) => s.replace(/\b\w/g, c => c.toUpperCase());
  const dupMap = new Map();
  for (const r of indRecords) {
    const g = r.given.trim().toLowerCase(), s = r.surname.trim().toLowerCase();
    if (g && s) {
      const key = `${g}${s}${r.birth.year ?? ''}`;
      if (!dupMap.has(key)) dupMap.set(key, { given: g, surname: s, year: r.birth.year ?? null, ids: [] });
      dupMap.get(key).ids.push(r.id);
    }
  }
  const duplicates = Array.from(dupMap.values()).filter(d => d.ids.length > 1)
    .map(d => ({ name: `${titleCase(d.given)} ${titleCase(d.surname)}`, year: d.year, ids: d.ids }));

  const quality = {
    anomalies_count: anomalies.length,
    anomalies: anomalies.slice(0, 200),
    completeness: Object.fromEntries(Object.entries(completenessFields).map(([k, v]) => [k, round1(v * 100)])),
    duplicates_count: duplicates.length,
    duplicates: duplicates.slice(0, 50),
  };

  return {
    meta: {
      generated_at: new Date().toISOString().slice(0, 19),
      total_individuals: total,
      total_families: famRecords.length,
      source_label: gs.headerSource,
      root_individual: root,
      root_name: indById.has(root) ? indById.get(root).name : null,
    },
    individuals: indRecords,
    families: famRecords,
    stats: { demographics, chronology, geography, family_structure: familyStructure, surnames, quality },
  };
}

/* ---------------------------------------------------------------- */
/* Gestion d'état : ajout / modification / suppression                */
/*                                                                    */
/* Les familles (FAM) sont la seule source de vérité pour les liens   */
/* de parenté ; les individus ne stockent que des identifiants de     */
/* famille (fams[]/famc[]). Les relations (parents/enfants/conjoints/ */
/* fratrie) sont toujours recalculées par analyzeGedcom() à partir de */
/* cet état, jamais stockées directement sur l'individu.              */
/* ---------------------------------------------------------------- */

function nextXref(map, prefix){
  let n = 1000001;
  while (map.has(`@${prefix}${n}@`)) n++;
  return `@${prefix}${n}@`;
}

function buildGedDateFromForm(qualifier, day, month, year){
  const str = buildGedcomDateString(qualifier, day, month, year);
  return str ? parseGedcomDate(str) : null;
}

/** Trouve une famille existante avec exactement ce couple parent(s), ou en crée une. */
function findOrCreateFamilyForParents(gs, fatherId, motherId){
  fatherId = fatherId || null;
  motherId = motherId || null;
  if (!fatherId && !motherId) return null;
  for (const fam of gs.families.values()) {
    if ((fam.husb || null) === fatherId && (fam.wife || null) === motherId) return fam.xref;
  }
  const xref = nextXref(gs.families, 'F');
  const fam = newBlankFamily(xref);
  fam.husb = fatherId;
  fam.wife = motherId;
  gs.families.set(xref, fam);
  if (fatherId && gs.individuals.has(fatherId)) gs.individuals.get(fatherId).fams.push(xref);
  if (motherId && gs.individuals.has(motherId)) gs.individuals.get(motherId).fams.push(xref);
  return xref;
}

/** Une famille sans enfant et avec au plus un conjoint ne représente aucune
 * union ni filiation réelle : elle peut être nettoyée automatiquement. */
function isVestigialFamily(fam){
  return fam.chil.length === 0 && (!fam.husb || !fam.wife);
}

/** Supprime une famille "vestige" (voir isVestigialFamily) et nettoie les références. */
function garbageCollectFamily(gs, famId){
  const fam = gs.families.get(famId);
  if (!fam || !isVestigialFamily(fam)) return;
  gs.families.delete(famId);
  for (const other of gs.individuals.values()) {
    other.fams = other.fams.filter(f => f !== famId);
    other.famc = other.famc.filter(f => f !== famId);
  }
}

/** Détache un individu de sa famille parentale actuelle (s'il en a une). */
function detachFromCurrentParentFamily(gs, indXref){
  const ind = gs.individuals.get(indXref);
  if (!ind) return;
  for (const famcId of [...ind.famc]) {
    const fam = gs.families.get(famcId);
    if (fam) fam.chil = fam.chil.filter(c => c !== indXref);
    ind.famc = ind.famc.filter(f => f !== famcId);
    if (fam) garbageCollectFamily(gs, famcId);
  }
}

/**
 * Crée un nouvel individu.
 * fields: { given, surname, sex, birthDate:GedDate|null, birthPlace, deceased,
 *           deathDate:GedDate|null, deathPlace, deathCause, occupation, fatherId, motherId }
 * Retourne le xref créé.
 */
function addIndividual(gs, fields){
  const xref = nextXref(gs.individuals, 'I');
  const ind = newBlankIndividual(xref);
  ind.given = (fields.given || '').trim();
  ind.surname = (fields.surname || '').trim();
  ind.full_name = `${ind.given} ${ind.surname}`.trim();
  ind.sex = fields.sex || 'U';
  ind.birth.date = fields.birthDate || null;
  ind.birth.place = fields.birthPlace || null;
  ind.birth.known = !!(ind.birth.date || ind.birth.place);
  ind.death.known = !!fields.deceased;
  ind.death.date = fields.deceased ? (fields.deathDate || null) : null;
  ind.death.place = fields.deceased ? (fields.deathPlace || null) : null;
  ind.death.cause = fields.deceased ? (fields.deathCause || null) : null;
  ind.occupation = fields.occupation || null;

  gs.individuals.set(xref, ind);

  const famcId = findOrCreateFamilyForParents(gs, fields.fatherId || null, fields.motherId || null);
  if (famcId) {
    const fam = gs.families.get(famcId);
    if (!fam.chil.includes(xref)) fam.chil.push(xref);
    ind.famc.push(famcId);
  }
  return xref;
}

/** Modifie un individu existant (champs personnels + lien vers les parents). */
function updateIndividual(gs, xref, fields){
  const ind = gs.individuals.get(xref);
  if (!ind) return;
  ind.given = (fields.given || '').trim();
  ind.surname = (fields.surname || '').trim();
  ind.full_name = `${ind.given} ${ind.surname}`.trim();
  ind.sex = fields.sex || 'U';
  ind.birth.date = fields.birthDate || null;
  ind.birth.place = fields.birthPlace || null;
  ind.birth.known = !!(ind.birth.date || ind.birth.place);
  ind.death.known = !!fields.deceased;
  ind.death.date = fields.deceased ? (fields.deathDate || null) : null;
  ind.death.place = fields.deceased ? (fields.deathPlace || null) : null;
  ind.death.cause = fields.deceased ? (fields.deathCause || null) : null;
  ind.occupation = fields.occupation || null;

  const currentFamc = ind.famc[0] || null;
  const currentFam = currentFamc ? gs.families.get(currentFamc) : null;
  const currentFather = currentFam ? (currentFam.husb || null) : null;
  const currentMother = currentFam ? (currentFam.wife || null) : null;
  const newFather = fields.fatherId || null;
  const newMother = fields.motherId || null;

  if (newFather !== currentFather || newMother !== currentMother) {
    detachFromCurrentParentFamily(gs, xref);
    const famcId = findOrCreateFamilyForParents(gs, newFather, newMother);
    if (famcId) {
      const fam = gs.families.get(famcId);
      if (!fam.chil.includes(xref)) fam.chil.push(xref);
      ind.famc.push(famcId);
    }
  }
}

/** Supprime un individu et nettoie toutes les références familiales. */
function deleteIndividual(gs, xref){
  if (!gs.individuals.has(xref)) return;
  gs.individuals.delete(xref);
  const emptied = [];
  for (const fam of gs.families.values()) {
    let touched = false;
    if (fam.husb === xref) { fam.husb = null; touched = true; }
    if (fam.wife === xref) { fam.wife = null; touched = true; }
    if (fam.chil.includes(xref)) { fam.chil = fam.chil.filter(c => c !== xref); touched = true; }
    if (touched && isVestigialFamily(fam)) emptied.push(fam.xref);
  }
  for (const famId of emptied) {
    gs.families.delete(famId);
    for (const other of gs.individuals.values()) {
      other.fams = other.fams.filter(f => f !== famId);
      other.famc = other.famc.filter(f => f !== famId);
    }
  }
  // toute autre famille peut encore référencer xref dans les fams/famc d'individus restants : nettoyage défensif
  for (const other of gs.individuals.values()) {
    other.fams = other.fams.filter(f => gs.families.has(f));
    other.famc = other.famc.filter(f => gs.families.has(f));
  }
}

/** Crée une union (famille) entre deux individus existants (ou un seul, l'autre étant inconnu). */
function createFamily(gs, fields){
  const husbId = fields.husbId || null;
  const wifeId = fields.wifeId || null;
  for (const fam of gs.families.values()) {
    if ((fam.husb || null) === husbId && (fam.wife || null) === wifeId && (husbId || wifeId)) {
      updateFamily(gs, fam.xref, fields);
      return fam.xref;
    }
  }
  const xref = nextXref(gs.families, 'F');
  const fam = newBlankFamily(xref);
  fam.husb = husbId;
  fam.wife = wifeId;
  fam.marriage.date = fields.marriageDate || null;
  fam.marriage.place = fields.marriagePlace || null;
  fam.marriage.known = !!(fam.marriage.date || fam.marriage.place || fields.married);
  fam.divorced = !!fields.divorced;
  gs.families.set(xref, fam);
  if (husbId && gs.individuals.has(husbId)) gs.individuals.get(husbId).fams.push(xref);
  if (wifeId && gs.individuals.has(wifeId)) gs.individuals.get(wifeId).fams.push(xref);
  return xref;
}

/** Modifie les informations de mariage d'une famille existante. */
function updateFamily(gs, xref, fields){
  const fam = gs.families.get(xref);
  if (!fam) return;
  fam.marriage.date = fields.marriageDate || null;
  fam.marriage.place = fields.marriagePlace || null;
  fam.marriage.known = !!(fam.marriage.date || fam.marriage.place || fields.married);
  fam.divorced = !!fields.divorced;
}

/** Supprime une union : les enfants deviennent orphelins (parents inconnus), pas supprimés. */
function deleteFamily(gs, xref){
  const fam = gs.families.get(xref);
  if (!fam) return;
  if (fam.husb && gs.individuals.has(fam.husb)) {
    const h = gs.individuals.get(fam.husb);
    h.fams = h.fams.filter(f => f !== xref);
  }
  if (fam.wife && gs.individuals.has(fam.wife)) {
    const w = gs.individuals.get(fam.wife);
    w.fams = w.fams.filter(f => f !== xref);
  }
  for (const c of fam.chil) {
    if (gs.individuals.has(c)) {
      const child = gs.individuals.get(c);
      child.famc = child.famc.filter(f => f !== xref);
    }
  }
  gs.families.delete(xref);
}

/* ---------------------------------------------------------------- */
/* Réhydratation de l'état brut embarqué par build_dashboard.py       */
/* (gedcom_parser.to_raw_json) ou reçu du parseGedcomText() client.   */
/* ---------------------------------------------------------------- */

function reviveGedcomState(raw){
  const individuals = new Map();
  for (const xref in raw.individuals) {
    const r = raw.individuals[xref];
    individuals.set(xref, {
      xref, given: r.given, surname: r.surname, full_name: r.full_name, sex: r.sex,
      birth: { date: r.birth.date, place: r.birth.place, known: r.birth.known },
      death: { date: r.death.date, place: r.death.place, cause: r.death.cause, known: r.death.known },
      occupation: r.occupation, fams: r.fams, famc: r.famc,
    });
  }
  const families = new Map();
  for (const xref in raw.families) {
    const r = raw.families[xref];
    families.set(xref, {
      xref, husb: r.husb, wife: r.wife, chil: r.chil,
      marriage: { date: r.marriage.date, place: r.marriage.place, known: r.marriage.known },
      divorced: r.divorced,
    });
  }
  return { individuals, families, headerSource: raw.header_source, headerAuthor: raw.header_author };
}
