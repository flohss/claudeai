/* Outils partagés par les suites de test.
   Aucune dépendance en dehors de Playwright : le serveur statique est écrit ici. */
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const MIME = {
  '.html':'text/html; charset=utf-8',
  '.js':'text/javascript; charset=utf-8',
  '.md':'text/markdown; charset=utf-8',
  '.png':'image/png', '.jpg':'image/jpeg', '.svg':'image/svg+xml'
};

/** Sert un dossier en local, le temps des tests. */
export function serve(root, port){
  const srv = http.createServer(async (req, res) => {
    const url = decodeURIComponent(req.url.split('?')[0]);
    const file = path.resolve(root, '.' + (url === '/' ? '/index.html' : url));
    if(!file.startsWith(path.resolve(root))){ res.writeHead(403); return res.end(); }
    try {
      const buf = await readFile(file);
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
      res.end(buf);
    } catch {
      res.writeHead(404); res.end('non trouvé');
    }
  });
  return new Promise(ok => srv.listen(port, () => ok(srv)));
}

/** Ouvre Chromium. Message clair si Playwright n'est pas installé. */
export async function launch(){
  let pw;
  try {
    pw = await import('playwright');
  } catch {
    console.error('\nPlaywright est absent. Installe-le une fois pour toutes :\n' +
                  '  npm install\n  npx playwright install chromium\n');
    process.exit(2);
  }
  return pw.chromium.launch({
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader']
  });
}

/** Ouvre une page en collectant les erreurs JavaScript. */
export async function openPage(browser, url, opts = {}){
  const ctx = await browser.newContext({ viewport:{ width:900, height:1300 }, ...opts });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => {
    // le faux positif de Playwright quand il synthétise un événement tactile
    if(m.type() === 'error' && !/cancelable=false/.test(m.text()))
      errors.push('console: ' + m.text());
  });
  await page.goto(url, { waitUntil:'networkidle' });
  page.jsErrors = errors;
  return page;
}

/** Petit rapporteur : enregistre les contrôles et décide du code de sortie. */
export function reporter(){
  const results = [];
  return {
    results,
    section(title){ console.log('\n  ── ' + title); },
    check(label, ok, detail = ''){
      results.push({ label, ok: !!ok, detail });
      console.log('    ' + (ok ? '✔' : '✘') + ' ' + label + (detail ? '   ' + detail : ''));
      return !!ok;
    },
    /** Contrôle qu'une valeur tombe dans un intervalle, en affichant la valeur. */
    range(label, value, lo, hi, unit = ''){
      const ok = value >= lo && value <= hi;
      return this.check(label, ok, '→ ' + value + unit + ' (attendu ' + lo + '–' + hi + unit + ')');
    }
  };
}

export const sleep = ms => new Promise(r => setTimeout(r, ms));
