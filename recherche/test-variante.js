// « Variante » ne doit jamais poser une note hors de la gamme choisie.
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const res = [], errs = [];
  const soft = (n, ok, d) => res.push(`${ok ? "OK  " : "FAIL"} ${n}: ${d}`);
  const ctx = await b.newContext({ viewport: { width: 1250, height: 1700 } });
  const p = await ctx.newPage();
  p.on("pageerror", e => errs.push(e.message));
  p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  await p.goto("file:///home/user/claudeai/trance.html");
  await p.waitForTimeout(700);
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });

  const cliquer = async () => {
    await p.click("#styleBtn");
    for (let k = 0; k < 120; k++) {
      await p.waitForTimeout(400);
      if (!/Apprend/.test(await p.$eval("#styleBtn", e => e.textContent))) break;
    }
    await p.waitForTimeout(700);
  };
  const hors = () => p.$$eval("#seqGrid .seq-cell.on.hors-gamme", e => e.length);
  const notes = () => p.$$eval("#seqGrid .seq-cell.on", e => e.length);

  // plusieurs gammes, plusieurs morceaux, plusieurs pistes
  for (const [mode, ton] of [["mineur", "2"], ["majeur", "5"], ["penta", "9"], ["blues", "0"]]) {
    for (const morceau of [1, 4, 6]) {
      await p.click(`#songs button:nth-child(${morceau})`);
      await p.waitForTimeout(350);
      await p.selectOption("#modeGamme", mode);
      await p.selectOption("#tonique", ton);
      await p.waitForTimeout(200);
      await p.click("#gammeSnap");                 // on part d'un motif propre
      await p.waitForTimeout(300);
      const av = await notes(), avHors = await hors();
      for (let tour = 0; tour < 3; tour++) await cliquer();
      const ap = await notes(), apHors = await hors();
      soft(`${mode}/${ton} morceau ${morceau} — rien hors de la gamme`,
           apHors === 0 && avHors === 0, `${apHors} notes hors gamme après trois passages`);
      soft(`${mode}/${ton} morceau ${morceau} — densité conservée`, ap === av,
           `${av} notes avant, ${ap} après`);
    }
  }
  console.log(res.join("\n"));
  console.log("\nErreurs: " + (errs.length ? errs.join("\n") : "aucune"));
  console.log("BILAN: " + (res.some(r => r.startsWith("FAIL")) || errs.length ? "ÉCHECS PRÉSENTS" : "tout passe"));
  await b.close();
})();
