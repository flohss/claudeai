// Rend Éclipse piste par piste : cinq stems plus le mixage complet.
const { chromium } = require("playwright");
const fs = require("fs");
const DIR = "/home/user/claudeai/ableton/stems";
const NOMS = ["Lead", "Nappe", "Basse", "Pluck", "Batterie"];

const mesure = f => {
  const b = fs.readFileSync(f);
  let crete = 0, somme = 0, n = 0;
  for (let k = 44; k + 1 < b.length; k += 2) {
    const v = b.readInt16LE(k); crete = Math.max(crete, Math.abs(v)); somme += v * v; n++;
  }
  return { crete, rms: Math.round(Math.sqrt(somme / n)), sec: n / 44100 / 2, octets: b.length };
};

(async () => {
  fs.mkdirSync(DIR, { recursive: true });
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
    args: ["--autoplay-policy=no-user-gesture-required"] });
  const p = await b.newPage({ viewport: { width: 1250, height: 1500 }, acceptDownloads: true });
  const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  await p.goto("file:///home/user/claudeai/trance.html");
  await p.waitForTimeout(600);

  // Éclipse est le 6e morceau de la bibliothèque
  const titre = await p.$eval("#songs button:nth-child(6)", e => e.textContent);
  if (titre !== "Éclipse") throw new Error("6e morceau = " + titre);
  await p.click("#songs button:nth-child(6)");
  await p.waitForTimeout(500);

  const rendre = async (fichier) => {
    const dl = p.waitForEvent("download", { timeout: 180000 });
    await p.click("#wavBtn");
    await (await dl).saveAs(`${DIR}/${fichier}`);
    return mesure(`${DIR}/${fichier}`);
  };

  const m = await rendre("Eclipse-mixage.wav");
  console.log(`${"Mixage complet".padEnd(10)} crête ${String(m.crete).padStart(5)}  ` +
              `efficace ${String(m.rms).padStart(4)}  ${m.sec.toFixed(1)} s`);

  for (let i = 0; i < 5; i++) {
    // le 2e mini-bouton de la rangée est le solo
    await p.click(`#mixer .track-row:nth-child(${i + 1}) button[title="Solo"]`);
    await p.waitForTimeout(350);
    // décisif : les quatre autres rangées doivent être marquées silencieuses
    const muettes = await p.$$eval("#mixer .track-row.silent", e => e.length);
    if (muettes !== 4) errs.push(`${NOMS[i]} : ${muettes} rangée(s) silencieuse(s) au lieu de 4`);
    const s = await rendre(`Eclipse-${i + 1}-${NOMS[i]}.wav`);
    console.log(`${NOMS[i].padEnd(10)} crête ${String(s.crete).padStart(5)}  ` +
                `efficace ${String(s.rms).padStart(4)}  ${s.sec.toFixed(1)} s`);
    if (s.crete < 500) errs.push(`${NOMS[i]} : stem quasi muet (crête ${s.crete})`);
    if (Math.abs(s.sec - m.sec) > 0.5) errs.push(`${NOMS[i]} : durée ${s.sec} ≠ mixage ${m.sec}`);
    await p.click(`#mixer .track-row:nth-child(${i + 1}) button[title="Solo"]`);
    await p.waitForTimeout(250);
  }

  console.log("\nErreurs : " + (errs.length ? errs.join("\n") : "aucune"));
  await b.close();
})();
