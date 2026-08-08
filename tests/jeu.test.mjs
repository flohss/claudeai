/* Suite de test de labyrinthe3d.html — le jeu.
   Chaque contrôle est une assertion, pas un simple affichage. */
import { openPage, reporter, sleep } from './lib.mjs';

export default async function testJeu(browser, base){
  const R = reporter();
  const url = base + '/labyrinthe3d.html';

  /* ---------------------------------------------------------------- chargement */
  R.section('Chargement');
  const page = await openPage(browser, url);
  R.check('three.js est disponible',
    (await page.evaluate(() => typeof window.THREE)) === 'object');
  R.check('le menu est construit',
    (await page.evaluate(() => document.querySelectorAll('#patternOpts .opt').length)) === 5);

  /* --------------------------------------------------- hasard et arbre couvrant */
  R.section('Génération : hasard et structure du labyrinthe');
  // Une première génération réelle : elle donne accès à la classe du générateur,
  // qui n'est pas exportée directement.
  await page.evaluate(() => { LAB.state.speed = 'instant'; });
  await page.click('#startBtn');
  await page.waitForFunction(() => LAB.builder && LAB.builder.done, null, { timeout:20000 });

  const struct = await page.evaluate(() => {
    const B = LAB.builder.constructor;
    const out = {};
    for(const pat of ['classique','ramifie','eparpille','ouvert','salles']){
      const vus = new Set();
      let aretes = 0, atteignables = 0, total = 0;
      for(let i=0;i<12;i++){
        const b = new B(12, pat, (i * 2654435761) >>> 0);
        const it = b.run(); while(!it.next().done);
        vus.add(Array.from(b.bitmap).join(''));
        // arêtes réellement ouvertes entre cases voisines
        let e = 0;
        for(let r=0;r<b.size;r++) for(let c=0;c<b.size;c++){
          if(r<b.size-1 && b.bitmap[(2*r+2)*b.N + (2*c+1)] === 0) e++;
          if(c<b.size-1 && b.bitmap[(2*r+1)*b.N + (2*c+2)] === 0) e++;
        }
        aretes = e;
        atteignables = b.dist.reduce((a,d) => a + (d >= 0 ? 1 : 0), 0);
        total = b.total;
      }
      out[pat] = { distincts: vus.size, aretes, atteignables, total };
    }
    return out;
  });

  for(const [pat, v] of Object.entries(struct)){
    R.check('« ' + pat + ' » : 12 tirages, 12 tracés distincts',
      v.distincts === 12, '→ ' + v.distincts + '/12');
    R.check('« ' + pat + ' » : toutes les cases sont atteignables',
      v.atteignables === v.total, '→ ' + v.atteignables + '/' + v.total);
    if(pat === 'ouvert')
      R.check('« ouvert » : plus de n−1 arêtes (le tressage ajoute des boucles)',
        v.aretes > v.total - 1, '→ ' + v.aretes + ' > ' + (v.total - 1));
    else
      R.check('« ' + pat + ' » : exactement n−1 arêtes (arbre couvrant)',
        v.aretes === v.total - 1, '→ ' + v.aretes + ' = ' + (v.total - 1));
  }

  /* ------------------------------------------------------------------- graines */
  R.section('Graine partageable');
  const codes = await page.evaluate(() => {
    let ok = 0, total = 0;
    for(const t of ['antique','neon','foret','espace','glace','volcan'])
      for(const p of ['classique','ramifie','eparpille','ouvert','salles'])
        for(const d of ['facile','moyen','difficile','expert'])
          for(const s of [0, 1, 999999, 16777215]){
            total++;
            const r = LAB.parseCode(LAB.makeCode(t,p,d,s));
            if(r && r.theme===t && r.pattern===p && r.diff===d && r.seed===s) ok++;
          }
    return { ok, total };
  });
  R.check('aller-retour code ↔ configuration', codes.ok === codes.total,
    '→ ' + codes.ok + '/' + codes.total);
  R.check('un code invalide est rejeté', (await page.evaluate(() => LAB.parseCode('NIMPORTEQUOI'))) === null);

  const rejeu = await page.evaluate(() => {
    const B = LAB.builder.constructor;
    const a = new B(12, 'classique', 424242); { const it=a.run(); while(!it.next().done); }
    const b = new B(12, 'classique', 424242); { const it=b.run(); while(!it.next().done); }
    const c = new B(12, 'classique', 424243); { const it=c.run(); while(!it.next().done); }
    const s = x => Array.from(x.bitmap).join('');
    return { identique: s(a) === s(b), different: s(a) !== s(c) };
  });
  R.check('même graine → labyrinthe identique', rejeu.identique);
  R.check('graine différente → labyrinthe différent', rejeu.different);

  await page.click('#genBackBtn');
  await page.fill('#seedInput', 'NEON-5D5PGS');
  await page.click('#seedBtn');
  R.check('l’interface accepte un code collé',
    (await page.evaluate(() => LAB.state.theme)) === 'neon');

  /* ------------------------------------------------------------------- décors */
  R.section('Construction des six décors en 3D');
  for(const theme of ['antique','neon','foret','espace','glace','volcan']){
    const p = await openPage(browser, url, { viewport:{ width:640, height:420 } });
    await p.evaluate(t => { LAB.state.theme = t; LAB.state.speed = 'instant'; LAB.state.diff = 'facile'; }, theme);
    await p.click('#startBtn');
    await p.waitForFunction(() => LAB.builder && LAB.builder.done, null, { timeout:20000 });
    await p.click('#playBtn');
    await sleep(500);
    const ok = (await p.evaluate(() => LAB.gameState)) === 'playing';
    R.check('décor « ' + theme +' » : rendu 3D sans erreur',
      ok && p.jsErrors.length === 0, p.jsErrors[0] || '');
    await p.context().close();
  }

  /* ------------------------------------------------- commandes tactiles et 3D */
  R.section('Commandes, pause et chronomètre');
  const m = await openPage(browser, url,
    { viewport:{ width:412, height:915 }, hasTouch:true, isMobile:true });
  await m.evaluate(() => { LAB.state.speed = 'instant'; LAB.state.diff = 'facile'; });
  await m.click('#startBtn');
  await m.waitForFunction(() => LAB.builder && LAB.builder.done, null, { timeout:20000 });
  await m.click('#playBtn');
  await sleep(300);

  const avant = await m.evaluate(() => ({ x:LAB.player.x, z:LAB.player.z, yaw:LAB.player.yaw }));
  await m.evaluate(() => {
    const z = document.getElementById('joystickZone');
    const mk = (type,x,y) => { const t = new Touch({ identifier:1, target:z, clientX:x, clientY:y });
      z.dispatchEvent(new TouchEvent(type, { bubbles:true, cancelable:true,
        touches:[t], changedTouches:[t], targetTouches:[t] })); };
    mk('touchstart', 90, 700); mk('touchmove', 90, 640);
  });
  await sleep(700);
  const apres = await m.evaluate(() => ({ x:LAB.player.x, z:LAB.player.z }));
  R.check('le joystick déplace le joueur',
    Math.hypot(apres.x - avant.x, apres.z - avant.z) > 0.5);
  R.check('le joueur n’a pas traversé de mur', await m.evaluate(() => {
    const c = Math.round(LAB.player.x/4), r = Math.round(LAB.player.z/4);
    return LAB.maze.bitmap[r*LAB.maze.N + c] === 0;
  }));

  await m.evaluate(() => {
    const z = document.getElementById('lookZone');
    const mk = (type,x,y) => { const t = new Touch({ identifier:2, target:z, clientX:x, clientY:y });
      z.dispatchEvent(new TouchEvent(type, { bubbles:true, cancelable:true,
        touches:[t], changedTouches:[t], targetTouches:[t] })); };
    mk('touchstart', 300, 500); mk('touchmove', 200, 500); mk('touchend', 200, 500);
  });
  R.check('le glissement fait pivoter la vue',
    Math.abs((await m.evaluate(() => LAB.player.yaw)) - avant.yaw) > 0.1);

  await m.click('#pauseBtn'); await sleep(150);
  R.check('la pause suspend la partie', (await m.evaluate(() => LAB.gameState)) === 'paused');
  const t1 = await m.textContent('#timer');
  await m.click('#ovPrimary'); await sleep(150);
  R.check('la reprise conserve le temps écoulé',
    (await m.evaluate(() => LAB.gameState)) === 'playing' && t1 !== '00:00', '→ ' + t1);

  // Le chronomètre doit suivre l'horloge réelle même à faible cadence d'images.
  const t0 = Date.now();
  const avantSec = await m.evaluate(() => document.getElementById('timer').textContent);
  await sleep(6000);
  const apresSec = await m.evaluate(() => document.getElementById('timer').textContent);
  const toSec = s => +s.slice(0,2)*60 + +s.slice(3);
  const ecoule = (Date.now() - t0) / 1000;
  const compte = toSec(apresSec) - toSec(avantSec);
  R.range('le chronomètre suit l’horloge réelle', Math.round(compte), Math.round(ecoule) - 2,
    Math.round(ecoule) + 1, ' s');

  /* ------------------------------------------------------------------- indice */
  R.section('Indice au sol');
  await m.click('#hintBtn'); await sleep(300);
  const pts = await m.evaluate(() => LAB.hintGroup ? LAB.hintGroup.children.length : 0);
  R.check('l’indice trace un chemin', pts > 1, '→ ' + pts + ' repères');
  R.check('le compteur d’indices s’incrémente', (await m.evaluate(() => LAB.hintsUsed)) === 1);
  await sleep(7500);
  R.check('l’indice s’efface après sept secondes',
    (await m.evaluate(() => LAB.hintGroup)) === null);

  /* ------------------------------------------------------- résolution comparée */
  R.section('Résolution comparée');
  await m.click('#pauseBtn'); await sleep(150);
  await m.evaluate(() => { LAB.state.speed = 'instant'; });
  await m.click('#ovSolve');
  await m.waitForFunction(() => LAB.solver && LAB.solver.done, null, { timeout:30000 });
  const sv = await m.evaluate(() => ({ bfs: LAB.solver.bfs, hand: LAB.solver.hand }));
  R.check('le parcours en largeur trouve un chemin', sv.bfs && sv.bfs.len > 0, '→ ' + sv.bfs.len + ' cases');
  R.check('la main gauche produit un relevé', !!sv.hand);
  R.check('un verdict est affiché', await m.isVisible('#verdict'));

  const taux = await m.evaluate(() => {
    const B = LAB.builder.constructor;
    const essai = (pat, size, N) => {
      let echecs = 0;
      for(let i=0;i<N;i++){
        const b = new B(size, pat, (i * 2654435761) >>> 0);
        const it = b.run(); while(!it.next().done);
        const D = [[-1,0],[0,1],[1,0],[0,-1]];
        const ouvert = (r1,c1,r2,c2) => b.bitmap[(r1+r2+1)*b.N + (c1+c2+1)] === 0;
        let r=0, c=0, dir=1, pas=0; const max = size*size*12;
        while(pas < max){
          if(r === b.exit.r && c === b.exit.c) break;
          let bouge = false;
          for(const t of [3,0,1,2]){
            const d = (dir+t)%4, nr = r+D[d][0], nc = c+D[d][1];
            if(nr<0||nr>=size||nc<0||nc>=size||!ouvert(r,c,nr,nc)) continue;
            dir = d; r = nr; c = nc; bouge = true; break;
          }
          if(!bouge) break;
          pas++;
        }
        if(!(r === b.exit.r && c === b.exit.c)) echecs++;
      }
      return echecs;
    };
    return { avecBoucles: essai('ouvert', 12, 60), sansBoucle: essai('classique', 12, 60) };
  });
  R.check('la main gauche ne se perd jamais dans un labyrinthe parfait',
    taux.sansBoucle === 0, '→ ' + taux.sansBoucle + '/60 échecs');
  R.range('la main gauche échoue sur les labyrinthes à boucles',
    Math.round(taux.avecBoucles / 60 * 100), 5, 60, ' %');

  /* --------------------------------------------------------------------- sons */
  R.section('Sonorisation');
  const s = await openPage(browser, url, { viewport:{ width:430, height:940 } });
  await s.evaluate(() => {
    window.__notes = [];
    const AC = window.AudioContext || window.webkitAudioContext;
    const orig = AC.prototype.createOscillator;
    AC.prototype.createOscillator = function(){
      const o = orig.call(this);
      const rec = { t: performance.now(), f:0 };
      window.__notes.push(rec);
      queueMicrotask(() => { rec.f = o.frequency.value; });
      return o;
    };
    LAB.state.pattern = 'classique'; LAB.state.diff = 'moyen'; LAB.state.speed = 'normal';
  });
  await s.click('#startBtn');
  await s.waitForFunction(() => LAB.builder && LAB.builder.done, null, { timeout:40000 });
  await sleep(200);
  const audio = await s.evaluate(() => {
    const n = window.__notes;
    const span = n.length > 1 ? (n[n.length-1].t - n[0].t)/1000 : 0;
    return { nb:n.length, cadence: span > 0 ? n.length/span : 0,
             freqs: [...new Set(n.map(x => Math.round(x.f)))].sort((a,b)=>a-b) };
  });
  R.check('des notes sont émises pendant la conception', audio.nb > 10, '→ ' + audio.nb);
  R.range('la cadence reste bridée', Math.round(audio.cadence), 1, 22, ' notes/s');
  R.check('les notes suivent la gamme prévue',
    audio.freqs.some(f => f >= 195 && f <= 197) && audio.freqs.some(f => f < 120),
    '→ ' + audio.freqs.slice(0,10).join(', ') + ' Hz');

  await s.evaluate(() => { window.__notes = []; });
  await s.click('#genSound');
  await s.click('#genBackBtn'); await s.click('#startBtn');
  await s.waitForFunction(() => LAB.builder && LAB.builder.done, null, { timeout:40000 });
  R.check('le bouton coupe réellement le son',
    (await s.evaluate(() => window.__notes.length)) === 0);
  await s.reload({ waitUntil:'networkidle' });
  R.check('le réglage du son survit au rechargement',
    (await s.textContent('#genSound')).trim() === '🔇');

  /* -------------------------------------------- lisibilité du journal de bord */
  R.section('Journal de bord : la conclusion doit rester visible');
  const j = await openPage(browser, url, { viewport:{ width:430, height:940 } });
  await j.evaluate(() => { LAB.state.pattern='classique'; LAB.state.diff='expert';
    LAB.state.speed='instant'; });
  await j.click('#startBtn');
  await j.waitForFunction(() => LAB.builder && LAB.builder.done, null, { timeout:40000 });
  await sleep(300);
  const journal = await j.evaluate(() => {
    const el = document.getElementById('log');
    const dernier = el.lastElementChild;
    if(!dernier) return { ok:false, raison:'journal vide' };
    const b = el.getBoundingClientRect(), d = dernier.getBoundingClientRect();
    return { ok: d.bottom <= b.bottom + 1 && d.top >= b.top - 1,
             texte: dernier.textContent.trim().slice(0,60) };
  });
  R.check('la dernière ligne du journal est dans le cadre visible',
    journal.ok, '→ « ' + (journal.texte || journal.raison) + ' »');
  await j.context().close();

  /* ------------------------------------------------------------ erreurs console */
  R.section('Journal du navigateur');
  const toutes = [...page.jsErrors, ...m.jsErrors, ...s.jsErrors];
  R.check('aucune erreur JavaScript', toutes.length === 0, toutes[0] || '');

  await page.context().close(); await m.context().close(); await s.context().close();
  return R.results;
}
