const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const p = await b.newPage({ viewport: { width: 1250, height: 1700 } });
  const errs = [];
  p.on("pageerror", e => errs.push(e.message));
  p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  await p.goto("file:///home/user/claudeai/trance.html");
  await p.waitForTimeout(700);
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });
  await p.click("#songs button:nth-child(1)");        // Ascension
  await p.waitForTimeout(500);
  await p.selectOption("#modeGamme", "mineur");
  await p.selectOption("#tonique", "0");
  await p.waitForTimeout(300);
  const avant = await p.$$eval("#seqGrid .seq-cell.on", e => e.map(x => x.dataset.step + ":" + x.dataset.off).sort());
  const t0 = Date.now();
  await p.click("#styleBtn");
  // on attend la fin de l'entraînement puis du jugement
  for (let k = 0; k < 120; k++) {
    await p.waitForTimeout(500);
    const t = await p.$eval("#styleBtn", e => e.textContent);
    if (!/Apprend/.test(t)) break;
  }
  await p.waitForTimeout(800);
  console.log("durée totale :", ((Date.now() - t0) / 1000).toFixed(1), "s");
  console.log("message :", await p.$eval("#gammeMsg", e => e.textContent));
  const apres = await p.$$eval("#seqGrid .seq-cell.on", e => e.map(x => x.dataset.step + ":" + x.dataset.off).sort());
  console.log("motif changé :", JSON.stringify(avant) !== JSON.stringify(apres));
  console.log("avant :", avant.join(" "));
  console.log("après :", apres.join(" "));
  console.log("poids en cache :", await p.evaluate(() => !!localStorage.getItem("synthes-virtuels/trance/reseau/1")));
  // deuxième clic : plus d'entraînement
  const t1 = Date.now();
  await p.click("#styleBtn");
  await p.waitForTimeout(1500);
  console.log("deuxième clic :", ((Date.now() - t1) / 1000).toFixed(1), "s —", await p.$eval("#gammeMsg", e => e.textContent));
  console.log("erreurs :", errs.length ? errs.join(" | ") : "aucune");
  await b.close();
})();
