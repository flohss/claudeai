// Le réseau doit apprendre de VOS motifs, pas seulement des neuf fournis.
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const res = [], errs = [];
  const soft = (n, ok, d) => res.push(`${ok ? "OK  " : "FAIL"} ${n}: ${d}`);
  const p = await (await b.newContext({ viewport: { width: 1250, height: 1800 } })).newPage();
  p.on("pageerror", e => errs.push(e.message));
  p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  await p.goto("file:///home/user/claudeai/trance.html");
  await p.waitForTimeout(700);
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
  await p.click("#songs button:nth-child(10)");
  await p.waitForTimeout(400);
  await p.selectOption("#modeGamme", "mineur");
  await p.selectOption("#tonique", "2");
  await p.waitForTimeout(250);

  const attendre = async id => {
    await p.click(id);
    for (let k = 0; k < 250; k++) {
      await p.waitForTimeout(300);
      if (!/%|Apprend/.test(await p.$eval(id, e => e.textContent))) break;
    }
    await p.waitForTimeout(400);
  };
  const cles = () => p.evaluate(() => Object.keys(localStorage).filter(k => /reseau/.test(k)));

  // on écrit un motif bien à nous, puis on apprend
  await p.evaluate(() => {
    for (const [s, o] of [[0,2],[2,5],[4,9],[6,5],[8,2],[10,5],[12,9],[14,5]])
      document.querySelector(`#seqGrid .seq-cell[data-step="${s}"][data-off="${o}"]`).click();
  });
  await p.waitForTimeout(600);
  await attendre("#sublimerBtn");
  const c1 = await cles();
  soft("les poids sont rangés sous une empreinte", c1.length === 1, c1.join(" "));

  // on change nos motifs : le réseau doit réapprendre, sous une autre empreinte
  await p.evaluate(() => {
    document.querySelector('#seqGrid .seq-cell[data-step="20"][data-off="7"]').click();
  });
  await p.waitForTimeout(600);
  await attendre("#sublimerBtn");
  const c2 = await cles();
  soft("changer de matériel change l'empreinte", c2.length === 2,
       c2.length + " jeux de poids rangés");

  // revenir en arrière retrouve les poids d'avant, sans réapprendre
  await p.keyboard.press("Control+z");
  await p.waitForTimeout(700);
  const t0 = Date.now();
  await attendre("#sublimerBtn");
  const rapide = (Date.now() - t0) / 1000;
  soft("revenir en arrière réutilise les poids d'avant", rapide < 4 && (await cles()).length === 2,
       `${rapide.toFixed(1)} s, ${(await cles()).length} jeux`);

  console.log(res.join("\n"));
  console.log("\nErreurs: " + (errs.length ? errs.join("\n") : "aucune"));
  console.log("BILAN: " + (res.some(r => r.startsWith("FAIL")) || errs.length ? "ÉCHECS PRÉSENTS" : "tout passe"));
  await b.close();
})();
