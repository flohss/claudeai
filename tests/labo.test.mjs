/* Suite de test de labo-algorithmes.html — le laboratoire.
   Les propriétés mathématiques sont vérifiées contre des références calculées
   indépendamment dans le test, jamais contre le code testé lui-même. */
import { openPage, reporter, sleep } from './lib.mjs';

export default async function testLabo(browser, base){
  const R = reporter();
  const url = base + '/labo-algorithmes.html';

  R.section('Chargement');
  const page = await openPage(browser, url);
  R.check('les quatre onglets sont présents',
    (await page.evaluate(() => document.querySelectorAll('[data-tab]').length)) === 4);
  R.check('les huit algorithmes sont déclarés',
    (await page.evaluate(() => Object.keys(LABO.ALGOS).length)) === 8);

  /* ------------------------------------------------- couverture des croisements */
  R.section('Couverture terrain × algorithme');
  const cov = await page.evaluate(() => {
    const out = [];
    for(const t of Object.keys(LABO.TERRAINS))
      for(const k of Object.keys(LABO.ALGOS)){
        if(LABO.ALGOS[k].terrains.indexOf(t) < 0) continue;
        try {
          const size = t === 'image' ? 40 : LABO.TERRAINS[t].def;
          const r = new LABO.Run(t, k, size, 12345, {});
          out.push({ paire: t + ' × ' + k, fini: r.finish(3e6) });
        } catch(e){ out.push({ paire: t + ' × ' + k, fini:false, err:e.message }); }
      }
    return out;
  });
  R.check('les ' + cov.length + ' croisements possibles aboutissent',
    cov.every(c => c.fini), (cov.find(c => !c.fini) || {}).paire || '');

  /* ------------------------------------------------------- propriétés d'arbre */
  R.section('Arbre couvrant : n−1 arêtes et connexité');
  const arbres = await page.evaluate(() => {
    const out = {};
    for(const t of ['grille','nuage'])
      for(const k of ['dfs','prim','kruskal']){
        let ok = 0; const N = 20;
        for(let i=0;i<N;i++){
          const r = new LABO.Run(t, k, LABO.TERRAINS[t].def, (1000+i*7919)>>>0, {});
          r.finish();
          if(r.st.counters.retenues === r.g.n - 1 && LABO.allReachable(r)) ok++;
        }
        out[t + '/' + k] = ok + '/' + N;
      }
    return out;
  });
  for(const [k,v] of Object.entries(arbres))
    R.check(k, v === '20/20', '→ ' + v);

  R.section('Prim et Kruskal atteignent le même optimum');
  const poids = await page.evaluate(() => {
    const out = {};
    for(const t of ['grille','nuage']){
      let ok = 0; const N = 20;
      for(let i=0;i<N;i++){
        const s = (1000+i*7919)>>>0, size = LABO.TERRAINS[t].def;
        const a = new LABO.Run(t,'prim',size,s,{}); a.finish();
        const b = new LABO.Run(t,'kruskal',size,s,{}); b.finish();
        if(Math.abs(a.treeWeight() - b.treeWeight()) < 1e-9) ok++;
      }
      out[t] = ok + '/' + N;
    }
    return out;
  });
  for(const [k,v] of Object.entries(poids))
    R.check('poids identique sur ' + k, v === '20/20', '→ ' + v);

  /* ------------------------------------------------------------- A* et Dijkstra */
  R.section('A* : jamais plus coûteux, et toujours optimal');
  const astar = await page.evaluate(() => {
    const out = {};
    for(const [t, mode, size, label] of [['grille','maze',14,'labyrinthe'],
                                         ['grille','open',14,'grille à obstacles'],
                                         ['nuage','maze',90,'nuage']]){
      let pire = 0, memeCout = 0, d = 0, a = 0; const N = 20;
      for(let i=0;i<N;i++){
        const s = (1000+i*7919)>>>0;
        const x = new LABO.Run(t,'dijkstra',size,s,{gridMode:mode}); x.finish();
        const y = new LABO.Run(t,'astar',size,s,{gridMode:mode}); y.finish();
        d += x.st.counters.examines; a += y.st.counters.examines;
        if(y.st.counters.examines > x.st.counters.examines) pire++;
        if(Math.abs(x.st.dist[x.target] - y.st.dist[y.target]) < 1e-9) memeCout++;
      }
      out[label] = { pire, memeCout, N, gain:(d/a).toFixed(2) };
    }
    return out;
  });
  for(const [k,v] of Object.entries(astar)){
    R.check('A* n’examine jamais plus que Dijkstra — ' + k, v.pire === 0,
      '→ gain ' + v.gain + '×');
    R.check('même coût optimal — ' + k, v.memeCout === v.N, '→ ' + v.memeCout + '/' + v.N);
  }

  /* ------------------------------------ régression : le départ ne doit pas être muré */
  R.section('Grille à obstacles : départ et arrivée toujours reliés');
  const ends = await page.evaluate(() => {
    let degenere = 0; const N = 40;
    for(let i=1;i<=N;i++){
      const r = new LABO.Run('grille','dijkstra',11,i,{gridMode:'open'});
      r.finish();
      // un départ emmuré donnerait une recherche vide et une cible confondue
      if(r.target === r.start || r.st.counters.examines < 5) degenere++;
    }
    return degenere;
  });
  R.check('aucune configuration dégénérée', ends === 0, '→ ' + ends + '/40');

  /* ---------------------------------------------- diamètre mesuré par la page */
  R.section('Diamètre de l’arbre : double balayage');
  const diam = await page.evaluate(() => {
    const out = {};
    for(const algo of ['dfs','prim','kruskal','division']){
      let exact = 0; const N = 30;
      for(let i=0;i<N;i++){
        const r = new LABO.Run('grille',algo,12,(31+i*7919)>>>0,{}); r.finish();
        const mesure = LABO.measure(r).chemin;
        // référence indépendante, recalculée ici
        const adj = r.g.nodes.map(() => []);
        for(let k=0;k<r.g.edges.length;k++) if(r.st.chosen[k]){
          const e = r.g.edges[k]; adj[e.a].push(e.b); adj[e.b].push(e.a);
        }
        const bfs = s => { const d = new Int32Array(adj.length).fill(-1); d[s] = 0;
          const q=[s]; let h=0, f=s;
          while(h<q.length){ const v=q[h++]; if(d[v]>d[f]) f=v;
            for(const w of adj[v]) if(d[w]===-1){ d[w]=d[v]+1; q.push(w); } }
          return { f, d }; };
        const a = bfs(0), b = bfs(a.f);
        if(mesure === b.d[b.f]) exact++;
      }
      out[algo] = exact + '/' + N;
    }
    return out;
  });
  for(const [k,v] of Object.entries(diam))
    R.check('diamètre exact pour ' + k, v === '30/30', '→ ' + v);

  /* ------------------------------------------------------------- main au mur */
  R.section('Main au mur : sa limite est structurelle');
  const mur = await page.evaluate(() => {
    const essai = boucles => {
      let echecs = 0; const N = 40;
      for(let i=0;i<N;i++){
        const r = new LABO.Run('grille','mur',12,(31+i*7919)>>>0,{ loops:boucles });
        r.finish();
        const last = r.st.logs[r.st.logs.length-1];
        if(last && last.msg.indexOf('Abandon') === 0) echecs++;
      }
      return echecs;
    };
    return { sans: essai(false), avec: essai(true) };
  });
  R.check('sort toujours d’un labyrinthe parfait', mur.sans === 0, '→ ' + mur.sans + '/40');
  R.check('échoue parfois en présence de boucles', mur.avec > 0, '→ ' + mur.avec + '/40');

  /* ------------------------------------------------------------ segmentation */
  R.section('Segmentation d’image');
  const seg = await page.evaluate(() => {
    const c = [];
    for(const thr of [8,16,30,60]){
      const r = new LABO.Run('image','kruskal',48,7,{ threshold:thr });
      r.finish();
      c.push({ thr, regions: r.st.comp.count });
    }
    return c;
  });
  const decroissant = seg.every((v,i) => i === 0 || v.regions <= seg[i-1].regions);
  R.check('le nombre de régions décroît quand le seuil monte', decroissant,
    '→ ' + seg.map(x => x.thr + ':' + x.regions).join('  '));
  R.range('à seuil moyen, on retrouve l’ordre de grandeur des zones réelles (7)',
    seg[2].regions, 4, 14, ' régions');

  /* ------------------------------------------------------------ écrans de doc */
  R.section('Écrans explicatifs');
  await page.click('[data-tab="comprendre"]');
  const algos = await page.evaluate(() => Object.keys(LABO.DOC));
  R.check('une fiche par algorithme', algos.length === 8, '→ ' + algos.length);
  for(const k of algos){
    await page.evaluate(x => { LABO.docKey = x; }, k);
    await sleep(120);
    const sections = await page.evaluate(() =>
      document.querySelectorAll('#docPanel h2').length);
    const a = await page.evaluate(() => LABO.exRun.st.counters.examines + LABO.exRun.st.counters.aretes);
    await sleep(450);
    const b = await page.evaluate(() => LABO.exRun.st.counters.examines + LABO.exRun.st.counters.aretes);
    await page.click('#verifBtn');
    await page.waitForFunction(() => {
      const t = document.getElementById('verifOut').textContent;
      return t && t !== 'Calcul en cours…';
    }, null, { timeout:60000 });
    const out = await page.textContent('#verifOut');
    const sain = !/Erreur|NaN|undefined|Infinity/.test(out);
    R.check('fiche « ' + k + ' » : 7 sections, démo animée, vérification chiffrée',
      sections === 7 && b > a && sain,
      sections !== 7 ? '→ ' + sections + ' sections'
        : b <= a ? '→ démonstration figée' : sain ? '' : '→ ' + out.slice(0,60));
  }

  /* ----------------------------------------------------- interface et graines */
  R.section('Interface');
  await page.click('[data-tab="observer"]');
  for(const [nom, attendu] of [['Profondeur','La pile'], ['Prim','Le tas de priorité'],
                               ['Kruskal','Union-find'], ['Largeur','La file'],
                               ['Division','Zones en attente']]){
    await page.locator('#algoOpts .opt', { hasText:nom }).first().click();
    R.check('le panneau de structure suit « ' + nom + ' »',
      (await page.textContent('#structName')) === attendu);
  }
  const code = await page.inputValue('#seedInput');
  await page.click('#seedNewBtn');
  await page.fill('#seedInput', code);
  await page.click('#seedBtn');
  R.check('aller-retour de la graine', (await page.inputValue('#seedInput')) === code, '→ ' + code);

  /* ------------------------------------------------------------ onglet Mesurer */
  R.section('Onglet Mesurer');
  await page.click('[data-tab="stats"]');
  await page.fill('#runsRange','40');
  await page.dispatchEvent('#runsRange','input');
  await page.click('#statsRunBtn');
  await page.waitForFunction(() => document.querySelector('#statsOut table'), null, { timeout:90000 });
  const cellules = await page.evaluate(() =>
    [...document.querySelectorAll('#statsOut table td')].map(t => t.textContent));
  R.check('le tableau ne contient aucune valeur invalide',
    !cellules.some(c => /NaN|undefined|Infinity/.test(c)), '→ ' + cellules.length + ' cellules');
  const hist = await page.evaluate(() => {
    const cv = document.getElementById('histCv');
    const d = cv.getContext('2d').getImageData(0,0,cv.width,cv.height).data;
    let n = 0; for(let i=0;i<d.length;i+=40) if(d[i]>20||d[i+1]>20||d[i+2]>20) n++;
    return n;
  });
  R.check('l’histogramme est dessiné', hist > 100, '→ ' + hist + ' pixels tracés');

  await page.click('#checkBtn');
  await page.waitForFunction(() => {
    const e = document.querySelector('#checkOut .note');
    return e && e.textContent.indexOf('Vérification…') < 0;
  }, null, { timeout:120000 });
  const controles = await page.evaluate(() => {
    const html = document.querySelector('#checkOut .note').innerHTML;
    return { total: (html.match(/[✔✘]/g) || []).length, echecs: (html.match(/✘/g) || []).length };
  });
  R.check('le bouton des invariantes ne signale aucun échec',
    controles.echecs === 0 && controles.total >= 8,
    '→ ' + (controles.total - controles.echecs) + '/' + controles.total);

  /* ------------------------------------------------ ergonomie des commandes */
  R.section('Barre de commandes');
  await page.click('[data-tab="observer"]');
  const ergo = await page.evaluate(() => {
    const bar = document.querySelector('.cmdBar');
    const board = document.querySelector('.board');
    return { avantPlateau: bar.getBoundingClientRect().top < board.getBoundingClientRect().top,
             collante: getComputedStyle(bar).position === 'sticky' };
  });
  R.check('les commandes sont au-dessus du plateau', ergo.avantPlateau);
  R.check('la barre reste accessible pendant le défilement', ergo.collante);

  for(const largeur of [360, 412, 900]){
    const p = await openPage(browser, url,
      { viewport:{ width:largeur, height:900 }, isMobile: largeur < 700, hasTouch: largeur < 700 });
    const etats = [];
    for(const phase of ['repos','encours','fini']){
      if(phase === 'encours'){
        await p.evaluate(() => { LABO.ui.speed = 'lent'; LABO.resetRun(); });
        await p.click('#runBtn'); await sleep(250);
      }
      if(phase === 'fini'){ await p.click('#endBtn'); await sleep(250); }
      etats.push(await p.evaluate(() =>
        [...document.querySelectorAll('.cmdBar .row .btn')].map(e => ({
          txt: e.textContent.trim(), coupe: e.scrollWidth > e.clientWidth + 1 }))));
    }
    const coupes = etats.flat().filter(x => x.coupe);
    const uneLigne = await p.evaluate(() => new Set(
      [...document.querySelectorAll('.cmdBar .row .btn')]
        .map(e => Math.round(e.getBoundingClientRect().top))).size === 1);
    R.check('à ' + largeur + ' px : libellés entiers et boutons sur une ligne',
      coupes.length === 0 && uneLigne,
      coupes.length ? '→ tronqué : ' + coupes.map(c => c.txt).join(', ') : '');
    await p.context().close();
  }

  /* ------------------------------------------ lisibilité du journal de bord */
  R.section('Journal de bord : la conclusion doit rester visible');
  await page.click('[data-tab="observer"]');
  await page.evaluate(() => { LABO.ui.terrain='grille'; LABO.ui.algo='prim'; LABO.ui.size=22;
    LABO.ui.speed='eclair'; LABO.resetRun(); });
  await page.click('#runBtn');
  await page.waitForFunction(() => LABO.run.done, null, { timeout:30000 });
  await sleep(400);
  const journal = await page.evaluate(() => {
    const el = document.getElementById('log');
    const dernier = el.lastElementChild;
    if(!dernier) return { ok:false, raison:'journal vide' };
    const b = el.getBoundingClientRect(), d = dernier.getBoundingClientRect();
    return { ok: d.bottom <= b.bottom + 1 && d.top >= b.top - 1,
             texte: dernier.textContent.trim().slice(0,60),
             debord: Math.round(el.scrollHeight - el.clientHeight) };
  });
  R.check('la dernière ligne du journal est dans le cadre visible',
    journal.ok, '→ « ' + (journal.texte || journal.raison) + ' »');

  R.section('Journal du navigateur');
  R.check('aucune erreur JavaScript', page.jsErrors.length === 0, page.jsErrors[0] || '');

  await page.context().close();
  return R.results;
}
