// Créer, Compléter, Sublimer : contraintes dures et progrès mesurable.
const { chromium } = require("playwright");
(async () => {
  const b = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome" });
  const res = [], errs = [];
  const soft = (n, ok, d) => res.push(`${ok ? "OK  " : "FAIL"} ${n}: ${d}`);
  const ctx = await b.newContext({ viewport: { width: 1250, height: 1800 } });
  const p = await ctx.newPage();
  p.on("pageerror", e => errs.push(e.message));
  p.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  await p.goto("file:///home/user/claudeai/trance.html");
  await p.waitForTimeout(700);
  await p.evaluate(() => { try { localStorage.clear(); } catch (e) {} });

  const attendre = async id => {
    await p.click(id);
    for (let k = 0; k < 250; k++) {
      await p.waitForTimeout(300);
      if (!/%|Apprend/.test(await p.$eval(id, e => e.textContent))) break;
    }
    await p.waitForTimeout(400);
  };
  const etat = () => p.evaluate(() => ({
    notes: [...document.querySelectorAll("#seqGrid .seq-cell.on")]
      .map(c => +c.dataset.step * 100 + +c.dataset.off).sort((a, b) => a - b),
    hors: document.querySelectorAll("#seqGrid .seq-cell.on.hors-gamme").length,
    msg: document.getElementById("iaMsg").textContent }));
  const note = m => { const x = m.match(/note (-?[\d.]+)/); return x ? +x[1] : NaN; };

  for (const [mode, ton] of [["mineur", "2"], ["majeur", "5"], ["penta", "9"]]) {
    await p.click("#songs button:nth-child(10)");            // Vierge
    await p.waitForTimeout(400);
    await p.selectOption("#modeGamme", mode);
    await p.selectOption("#tonique", ton);
    await p.waitForTimeout(250);

    await attendre("#creerBtn");
    let e = await etat();
    soft(`${mode}/${ton} — Créer écrit un motif`, e.notes.length >= 6, e.notes.length + " notes");
    soft(`${mode}/${ton} — Créer reste dans la gamme`, e.hors === 0, e.hors + " hors gamme");
    const avantNote = note(e.msg), avantN = e.notes.length;

    await attendre("#sublimerBtn");
    const e2 = await etat();
    soft(`${mode}/${ton} — Sublimer améliore ou égale`, note(e2.msg) <= avantNote + 1e-6,
         `${avantNote} → ${note(e2.msg)}`);
    soft(`${mode}/${ton} — Sublimer garde la densité`, e2.notes.length === avantN,
         `${avantN} → ${e2.notes.length}`);
    soft(`${mode}/${ton} — Sublimer reste dans la gamme`, e2.hors === 0, e2.hors + " hors gamme");

    // on efface la moitié des notes, puis on complète
    await p.evaluate(() => {
      const d = [...document.querySelectorAll("#seqGrid .seq-cell.on")];
      d.slice(0, Math.floor(d.length / 2)).forEach(c => c.click());
    });
    await p.waitForTimeout(400);
    const restantes = (await etat()).notes;
    await attendre("#completerBtn");
    const e3 = await etat();
    soft(`${mode}/${ton} — Compléter ne touche pas à ce qui est écrit`,
         restantes.every(v => e3.notes.includes(v)),
         `${restantes.length} gardées sur ${restantes.length}`);
    soft(`${mode}/${ton} — Compléter ajoute`, e3.notes.length > restantes.length,
         `${restantes.length} → ${e3.notes.length}`);
    soft(`${mode}/${ton} — Compléter reste dans la gamme`, e3.hors === 0, e3.hors + " hors gamme");

    await p.keyboard.press("Control+z");
    await p.waitForTimeout(500);
    soft(`${mode}/${ton} — Ctrl+Z annule`,
         JSON.stringify((await etat()).notes) === JSON.stringify(restantes), "revenu en arrière");
  }

  // la recherche longue doit faire au moins aussi bien que la rapide
  await p.click("#songs button:nth-child(10)");
  await p.waitForTimeout(400);
  await p.selectOption("#ambition", "0");
  await attendre("#creerBtn");
  const rapide = note((await etat()).msg);
  await p.selectOption("#ambition", "2");
  await p.click("#songs button:nth-child(10)");
  await p.waitForTimeout(400);
  await attendre("#creerBtn");
  const longue = note((await etat()).msg);
  soft("chercher plus longtemps trouve mieux", longue <= rapide + 0.02,
       `rapide ${rapide}, longue ${longue}`);

  console.log(res.join("\n"));
  console.log("\nErreurs: " + (errs.length ? errs.join("\n") : "aucune"));
  console.log("BILAN: " + (res.some(r => r.startsWith("FAIL")) || errs.length ? "ÉCHECS PRÉSENTS" : "tout passe"));
  await b.close();
})();
