/* Dashboard généalogique — logique de rendu (aucune dépendance externe) */

function escapeHtml(s){
  if (s === null || s === undefined) return '';
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function fmtInt(n){
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString('fr-FR');
}
function normalize(s){
  return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}
function sectionTitle(num, title){
  return `<h2 class="section-title"><span class="num">${num}</span>${escapeHtml(title)}</h2>`;
}
function genLabel(g){
  if (g === null || g === undefined) return '?';
  if (g === 0) return 'G0';
  return g < 0 ? `G${g}` : `G+${g}`;
}
function genTitle(g){
  const rootName = (DATA.meta.root_name) || 'la référence';
  if (g === null || g === undefined) return 'Génération inconnue';
  if (g === 0) return `Génération de référence — ${rootName}`;
  if (g < 0) return `Génération ${g} — ${-g}ᵉ génération d'ascendants de ${rootName}`;
  return `Génération +${g} — ${g}ᵉ génération de descendants de ${rootName}`;
}
function relLabel(rel){
  if (rel === 'root') return 'Racine';
  if (rel === 'blood') return 'Sang';
  return 'Alliance';
}
function relTitle(rel){
  const rootName = (DATA.meta.root_name) || 'la référence';
  if (rel === 'root') return `Personne de référence de l'arbre`;
  if (rel === 'blood') return `Famille par le sang de ${rootName} (ascendant·e, descendant·e ou collatéral·e)`;
  return `Par alliance : lié·e à ${rootName} uniquement par un ou plusieurs mariages`;
}
function relBadgeHTML(rel){
  return `<span class="irel ${rel}" title="${escapeHtml(relTitle(rel))}">${relLabel(rel)}</span>`;
}
function lifeSpanShort(r){
  const by = r.birth.year ? r.birth.year : '?';
  if (r.death.known) {
    const dy = r.death.year ? r.death.year : '?';
    return `${by} – ${dy}` + (r.age_at_death != null ? ` (${r.age_at_death} ans)` : '');
  }
  if (r.alive) return `${by} – présent` + (r.current_age != null ? ` (${r.current_age} ans)` : '');
  return `${by} – ?`;
}
function personLink(id, name){
  const person = id ? INDEX[id] : null;
  if (!person) return escapeHtml(name || 'Inconnu(e)');
  return `<span class="link-name" data-open-id="${id}">${escapeHtml(name || person.name)}</span>`;
}
function barListHTML(items, max){
  return `<div class="bar-list">${items.map(([label, val]) => {
    const pct = max ? Math.round((val / max) * 100) : 0;
    return `<div class="row"><div class="rlabel" title="${escapeHtml(label)}">${escapeHtml(label)}</div>` +
           `<div class="rtrack"><div class="rfill" style="width:${pct}%"></div></div>` +
           `<div class="rval">${fmtInt(val)}</div></div>`;
  }).join('')}</div>`;
}

/* ------------------------------------------------------------------ */
/* Graphiques SVG (générés à la volée, sans bibliothèque externe)      */
/* ------------------------------------------------------------------ */

function barChartSVG(data, opts){
  opts = opts || {};
  const width = opts.width || 640, height = opts.height || 260;
  const padL = 44, padR = 14, padT = 14, padB = opts.padB || 58;
  const innerW = width - padL - padR, innerH = height - padT - padB;
  const maxVal = Math.max(1, ...data.map(d => d.value));
  const n = data.length || 1;
  const bw = innerW / n;
  const ticks = 4;
  let grid = '';
  for (let t = 0; t <= ticks; t++) {
    const y = padT + innerH - (innerH * t / ticks);
    const val = Math.round(maxVal * t / ticks);
    grid += `<line x1="${padL}" y1="${y.toFixed(1)}" x2="${width - padR}" y2="${y.toFixed(1)}" class="grid-line"/>`;
    grid += `<text x="${padL - 6}" y="${(y + 3).toFixed(1)}" text-anchor="end" class="axis-label">${fmtInt(val)}</text>`;
  }
  let bars = '', labels = '';
  const labelEvery = Math.max(1, Math.ceil(n / 32));
  data.forEach((d, i) => {
    const bh = (d.value / maxVal) * innerH;
    const x = padL + i * bw + bw * 0.18;
    const y = padT + innerH - bh;
    const w = bw * 0.64;
    const cls = opts.colorClass || 'bar';
    bars += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${Math.max(bh, 0).toFixed(1)}" class="${cls}"><title>${escapeHtml(d.label)} : ${fmtInt(d.value)}</title></rect>`;
    if (i % labelEvery === 0) {
      const lx = x + w / 2;
      const ly = height - padB + 12;
      labels += `<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="end" class="axis-label" transform="rotate(-55 ${lx.toFixed(1)} ${ly.toFixed(1)})">${escapeHtml(d.label)}</text>`;
    }
  });
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMinYMin meet">` +
    grid + `<line x1="${padL}" y1="${(padT + innerH).toFixed(1)}" x2="${width - padR}" y2="${(padT + innerH).toFixed(1)}" class="axis-line"/>` +
    bars + labels + `</svg>`;
}

function pyramidSVG(bands){
  const width = 640, rowH = 30, padL = 46, padR = 46, padT = 16, padB = 16, gap = 40;
  const height = rowH * bands.length + padT + padB;
  const innerW = width - padL - padR;
  const midX = padL + innerW / 2;
  const halfW = innerW / 2 - gap / 2;
  const maxVal = Math.max(1, ...bands.flatMap(b => [b.M, b.F]));
  let rows = '';
  bands.forEach((b, i) => {
    const y = padT + i * rowH;
    const mW = (b.M / maxVal) * halfW;
    const fW = (b.F / maxVal) * halfW;
    const barY = (y + rowH * 0.16).toFixed(1);
    const barH = (rowH * 0.68).toFixed(1);
    rows += `<rect x="${(midX - gap / 2 - mW).toFixed(1)}" y="${barY}" width="${mW.toFixed(1)}" height="${barH}" class="bar male"><title>${b.band} ans — Hommes : ${b.M}</title></rect>`;
    rows += `<rect x="${(midX + gap / 2).toFixed(1)}" y="${barY}" width="${fW.toFixed(1)}" height="${barH}" class="bar female"><title>${b.band} ans — Femmes : ${b.F}</title></rect>`;
    rows += `<text x="${midX.toFixed(1)}" y="${(y + rowH * 0.66).toFixed(1)}" text-anchor="middle" class="axis-label">${b.band}</text>`;
  });
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMinYMin meet">${rows}</svg>`;
}

function lineChartSVG(categories, series, opts){
  opts = opts || {};
  const width = opts.width || 760, height = opts.height || 300;
  const padL = 44, padR = 16, padT = 16, padB = 58;
  const innerW = width - padL - padR, innerH = height - padT - padB;
  const maxVal = Math.max(1, ...series.flatMap(s => s.values));
  const n = categories.length;
  const stepX = n > 1 ? innerW / (n - 1) : innerW;
  const ticks = 4;
  let grid = '';
  for (let t = 0; t <= ticks; t++) {
    const y = padT + innerH - (innerH * t / ticks);
    const val = Math.round(maxVal * t / ticks);
    grid += `<line x1="${padL}" y1="${y.toFixed(1)}" x2="${width - padR}" y2="${y.toFixed(1)}" class="grid-line"/>`;
    grid += `<text x="${padL - 6}" y="${(y + 3).toFixed(1)}" text-anchor="end" class="axis-label">${fmtInt(val)}</text>`;
  }
  const labelEvery = Math.max(1, Math.ceil(n / 24));
  let labels = '';
  categories.forEach((c, i) => {
    if (i % labelEvery === 0) {
      const x = padL + i * stepX;
      const ly = height - padB + 12;
      labels += `<text x="${x.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="end" class="axis-label" transform="rotate(-55 ${x.toFixed(1)} ${ly.toFixed(1)})">${escapeHtml(c)}</text>`;
    }
  });
  let paths = '';
  series.forEach(s => {
    const pts = s.values.map((v, i) => {
      const x = padL + i * stepX;
      const y = padT + innerH - (v / maxVal) * innerH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    paths += `<polyline points="${pts}" class="line-series" style="stroke:${s.color}"/>`;
    s.values.forEach((v, i) => {
      const x = padL + i * stepX;
      const y = padT + innerH - (v / maxVal) * innerH;
      paths += `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="2.6" class="line-dot" style="stroke:${s.color}"><title>${escapeHtml(categories[i])} — ${escapeHtml(s.name)} : ${v}</title></circle>`;
    });
  });
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMinYMin meet">` +
    grid + `<line x1="${padL}" y1="${(padT + innerH).toFixed(1)}" x2="${width - padR}" y2="${(padT + innerH).toFixed(1)}" class="axis-line"/>` +
    paths + labels + `</svg>`;
}

function timelineSVG(rows){
  const width = 760, rowH = 32, padL = 150, padR = 40, padT = 10, padB = 30;
  const height = rowH * rows.length + padT + padB;
  const allYears = rows.flatMap(r => [r.min, r.max]);
  const yMin = Math.min(...allYears), yMax = Math.max(...allYears);
  const innerW = width - padL - padR;
  const span = (yMax - yMin) || 1;
  const xScale = y => padL + ((y - yMin) / span) * innerW;
  let xticks = '';
  const step = 50;
  for (let yv = Math.ceil(yMin / step) * step; yv <= yMax; yv += step) {
    const x = xScale(yv);
    xticks += `<line x1="${x.toFixed(1)}" y1="${padT}" x2="${x.toFixed(1)}" y2="${height - padB + 4}" class="grid-line"/>`;
    xticks += `<text x="${x.toFixed(1)}" y="${height - padB + 16}" text-anchor="middle" class="axis-label">${yv}</text>`;
  }
  let bars = '';
  rows.forEach((r, i) => {
    const y = padT + i * rowH;
    const x1 = xScale(r.min), x2 = xScale(r.max);
    bars += `<text x="${padL - 10}" y="${(y + rowH * 0.62).toFixed(1)}" text-anchor="end" class="axis-label">${escapeHtml(r.label)}</text>`;
    bars += `<rect x="${x1.toFixed(1)}" y="${(y + rowH * 0.25).toFixed(1)}" width="${Math.max(x2 - x1, 3).toFixed(1)}" height="${(rowH * 0.5).toFixed(1)}" rx="3" class="bar gold"><title>${escapeHtml(r.label)} : ${r.min}–${r.max}</title></rect>`;
  });
  return `<svg class="chart" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMinYMin meet">${xticks}${bars}</svg>`;
}

/* ------------------------------------------------------------------ */
/* Rendu des onglets                                                    */
/* ------------------------------------------------------------------ */

function renderDemographie(){
  const s = DATA.stats.demographics;
  const genEntries = Object.entries(s.generation_counts)
    .sort((a, b) => Number(a[0]) - Number(b[0]))
    .map(([g, c]) => ({ label: genLabel(Number(g)), value: c }));
  const histEntries = s.age_at_death.histogram.map(h => ({ label: h.range, value: h.count }));
  const total = s.total_individuals;
  const pctM = total ? Math.round((s.sex_counts.M / total) * 100) : 0;
  const pctF = total ? Math.round((s.sex_counts.F / total) * 100) : 0;

  const kpis = `
    <div class="grid cols-4">
      <div class="card kpi"><div class="value">${fmtInt(total)}</div><div class="label">Individus recensés</div><div class="sub">${fmtInt(s.blood_count)} par le sang &middot; ${fmtInt(s.marriage_count)} par alliance</div></div>
      <div class="card kpi"><div class="value">${pctM}% / ${pctF}%</div><div class="label">Hommes / Femmes</div><div class="sub">${fmtInt(s.sex_counts.M)} H &middot; ${fmtInt(s.sex_counts.F)} F</div></div>
      <div class="card kpi"><div class="value">${fmtInt(s.deceased_count)}</div><div class="label">Décédé(e)s</div><div class="sub">${fmtInt(s.alive_count)} vivant(e)s probables</div></div>
      <div class="card kpi"><div class="value">${s.age_at_death.mean ?? '—'} ans</div><div class="label">Âge moyen au décès</div><div class="sub">médiane : ${s.age_at_death.median ?? '—'} ans (n=${s.age_at_death.count})</div></div>
    </div>
    <div class="grid cols-3" style="margin-top:16px;">
      <div class="card kpi"><div class="value">${s.oldest_living ? s.oldest_living.age + ' ans' : '—'}</div><div class="label">Doyen(ne) actuel(le)</div><div class="sub">${s.oldest_living ? personLink(s.oldest_living.id, s.oldest_living.name) : 'inconnu'}</div></div>
      <div class="card kpi"><div class="value">${s.oldest_at_death ? s.oldest_at_death.age + ' ans' : '—'}</div><div class="label">Record de longévité</div><div class="sub">${s.oldest_at_death ? personLink(s.oldest_at_death.id, s.oldest_at_death.name) + ' (' + s.oldest_at_death.date + ')' : ''}</div></div>
      <div class="card kpi"><div class="value">${s.youngest_at_death ? s.youngest_at_death.age + ' an' + (s.youngest_at_death.age > 1 ? 's' : '') : '—'}</div><div class="label">Décès le plus précoce</div><div class="sub">${s.youngest_at_death ? personLink(s.youngest_at_death.id, s.youngest_at_death.name) + ' (' + s.youngest_at_death.date + ')' : ''}</div></div>
    </div>`;

  const pyramid = `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Pyramide des âges (âge au décès, ou âge actuel pour les vivant(e)s)</h3>
      <div class="chart-wrap">${pyramidSVG(s.age_pyramid)}</div>
      <div class="legend"><span><span class="swatch" style="background:#5c7a99"></span>Hommes</span><span><span class="swatch" style="background:#a8536b"></span>Femmes</span></div>
    </div>`;

  const twoCharts = `
    <div class="two-col" style="margin-top:16px;">
      <div class="card">
        <h3 class="card-title">Répartition par génération</h3>
        <div class="chart-wrap">${barChartSVG(genEntries, { colorClass: 'bar gold' })}</div>
        <p class="card-note">G0 = génération de ${escapeHtml(DATA.meta.root_name || 'référence')}. Les valeurs négatives sont les ascendants, les positives les descendants.</p>
      </div>
      <div class="card">
        <h3 class="card-title">Distribution de l'âge au décès</h3>
        <div class="chart-wrap">${barChartSVG(histEntries)}</div>
      </div>
    </div>`;

  const centuryRows = Object.entries(s.age_at_death.distribution_by_century).map(([c, v]) => `
    <tr><td>${c}<sup>e</sup> siècle</td><td>${v.count}</td><td>${v.mean} ans</td><td>${v.median} ans</td></tr>`).join('');
  const centuryTable = `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Âge au décès par siècle</h3>
      <table class="data-table"><thead><tr><th>Siècle</th><th>Effectif</th><th>Âge moyen</th><th>Âge médian</th></tr></thead><tbody>${centuryRows}</tbody></table>
    </div>`;

  document.getElementById('panel-demographie').innerHTML =
    sectionTitle('01', 'Démographie') + kpis + pyramid + twoCharts + centuryTable;
}

function renderChronologie(){
  const s = DATA.stats.chronology;
  const decadeSet = new Set([
    ...Object.keys(s.births_by_decade),
    ...Object.keys(s.marriages_by_decade),
    ...Object.keys(s.deaths_by_decade),
  ].map(Number));
  const decades = Array.from(decadeSet).sort((a, b) => a - b);
  const series = [
    { name: 'Naissances', color: '#3f5b41', values: decades.map(d => s.births_by_decade[d] || 0) },
    { name: 'Mariages', color: '#a8791f', values: decades.map(d => s.marriages_by_decade[d] || 0) },
    { name: 'Décès', color: '#7a2733', values: decades.map(d => s.deaths_by_decade[d] || 0) },
  ];
  const cats = decades.map(d => String(d));

  const kpis = `
    <div class="grid cols-4">
      <div class="card kpi"><div class="value">${s.tree_depth_generations}</div><div class="label">Générations documentées</div></div>
      <div class="card kpi"><div class="value">${s.earliest_birth_year ?? '—'}</div><div class="label">Naissance la plus ancienne</div></div>
      <div class="card kpi"><div class="value">${s.latest_birth_year ?? '—'}</div><div class="label">Naissance la plus récente</div></div>
      <div class="card kpi"><div class="value">${s.avg_generational_gap ?? '—'} ans</div><div class="label">Écart générationnel moyen</div><div class="sub">n=${fmtInt(s.generational_gap_sample_size)} liens parent-enfant</div></div>
    </div>`;

  const linechart = `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Naissances, mariages et décès par décennie</h3>
      <div class="chart-wrap">${lineChartSVG(cats, series)}</div>
      <div class="legend">${series.map(sr => `<span><span class="swatch" style="background:${sr.color}"></span>${sr.name}</span>`).join('')}</div>
    </div>`;

  const timelineRows = s.generation_timeline.map(g => ({
    label: `${genLabel(g.generation)} (${g.count})`, min: g.min_year, max: g.max_year, count: g.count,
  }));
  const frise = `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Frise des générations</h3>
      <div class="chart-wrap">${timelineSVG(timelineRows)}</div>
      <p class="card-note">Étendue des années de naissance connues pour chaque génération relative à ${escapeHtml(DATA.meta.root_name || 'la référence')}.</p>
    </div>`;

  document.getElementById('panel-chronologie').innerHTML = sectionTitle('02', 'Chronologie') + kpis + linechart + frise;
}

function renderGeographie(){
  const s = DATA.stats.geography;
  const maxBirth = Math.max(1, ...s.birth_places_top.map(x => x[1]));
  const maxDeath = Math.max(1, ...s.death_places_top.map(x => x[1]));
  const maxMarr = Math.max(1, ...s.marriage_places_top.map(x => x[1]));

  const kpis = `
    <div class="grid cols-3">
      <div class="card kpi"><div class="value">${fmtInt(s.birth_places_top.length)}</div><div class="label">Lieux de naissance recensés (top)</div></div>
      <div class="card kpi"><div class="value">${fmtInt(s.migrations_count)}</div><div class="label">Migrations détectées</div><div class="sub">naissance / décès dans des régions différentes</div></div>
      <div class="card kpi"><div class="value">${s.concentration_zones[0] ? escapeHtml(s.concentration_zones[0][0]) : '—'}</div><div class="label">Zone de concentration principale</div><div class="sub">${s.concentration_zones[0] ? fmtInt(s.concentration_zones[0][1]) + ' individus' : ''}</div></div>
    </div>`;

  const placesGrid = `
    <div class="grid cols-3" style="margin-top:16px;">
      <div class="card"><h3 class="card-title">Lieux de naissance</h3>${barListHTML(s.birth_places_top.slice(0, 10), maxBirth)}</div>
      <div class="card"><h3 class="card-title">Lieux de mariage</h3>${barListHTML(s.marriage_places_top.slice(0, 10), maxMarr)}</div>
      <div class="card"><h3 class="card-title">Lieux de décès</h3>${barListHTML(s.death_places_top.slice(0, 10), maxDeath)}</div>
    </div>`;

  const zonesMax = Math.max(1, ...s.concentration_zones.map(z => z[1]));
  const chipCloud = `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Zones de concentration familiale (région / département de naissance)</h3>
      <div class="chip-cloud">${s.concentration_zones.map(([z, c]) => `<span class="chip" style="font-size:${(11 + (c / zonesMax) * 11).toFixed(0)}px">${escapeHtml(z)} &middot; ${fmtInt(c)}</span>`).join('')}</div>
    </div>`;

  const migRows = s.migrations_sample.slice(0, 40).map(m => `
    <tr><td>${personLink(m.id, m.name)}</td><td>${escapeHtml(m.from)}</td><td>${escapeHtml(m.to)}</td></tr>`).join('');
  const migTable = `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Exemples de migrations (naissance &rarr; décès)</h3>
      <div style="max-height:360px; overflow-y:auto;">
      <table class="data-table"><thead><tr><th>Individu</th><th>Lieu de naissance</th><th>Lieu de décès</th></tr></thead><tbody>${migRows || '<tr><td colspan=3 class="card-note">Aucune migration détectée</td></tr>'}</tbody></table>
      </div>
      <p class="card-note">${fmtInt(s.migrations_count)} migrations détectées au total (échantillon de ${Math.min(40, s.migrations_sample.length)} affiché ici).</p>
    </div>`;

  document.getElementById('panel-geographie').innerHTML = sectionTitle('03', 'Géographie') + kpis + placesGrid + chipCloud + migTable;
}

function renderFamilles(){
  const s = DATA.stats.family_structure;
  const kpis = `
    <div class="grid cols-4">
      <div class="card kpi"><div class="value">${fmtInt(s.total_families)}</div><div class="label">Familles (unions)</div></div>
      <div class="card kpi"><div class="value">${s.avg_children_per_family ?? '—'}</div><div class="label">Enfants / famille (moyenne)</div><div class="sub">médiane : ${s.median_children_per_family ?? '—'}</div></div>
      <div class="card kpi"><div class="value">${s.avg_age_at_marriage ?? '—'} ans</div><div class="label">Âge moyen au mariage</div><div class="sub">H : ${s.avg_age_at_marriage_husb ?? '—'} &middot; F : ${s.avg_age_at_marriage_wife ?? '—'}</div></div>
      <div class="card kpi"><div class="value">${s.avg_spouse_age_gap ?? '—'} ans</div><div class="label">Écart d'âge moyen entre conjoints</div></div>
    </div>
    <div class="grid cols-3" style="margin-top:16px;">
      <div class="card kpi"><div class="value">${fmtInt(s.large_families_count)}</div><div class="label">Familles nombreuses (&ge;5 enfants)</div></div>
      <div class="card kpi"><div class="value">${fmtInt(s.remarriages_count)}</div><div class="label">Remariages / recompositions</div></div>
      <div class="card kpi"><div class="value">${fmtInt(s.divorced_families)}</div><div class="label">Divorces enregistrés</div></div>
    </div>`;

  const largeRows = s.large_families_sample.map(f => `
    <tr><td>${personLink(f.husb_id, f.husb)} &times; ${personLink(f.wife_id, f.wife)}</td><td>${f.n_children}</td></tr>`).join('');
  const largeTable = `
    <div class="card" style="margin-top:16px;">
      <h3 class="card-title">Familles nombreuses (top 15)</h3>
      <table class="data-table"><thead><tr><th>Couple</th><th>Enfants</th></tr></thead><tbody>${largeRows || '<tr><td colspan=2 class="card-note">Aucune</td></tr>'}</tbody></table>
    </div>`;

  const remRows = s.remarriages_sample.map(r => `
    <tr><td>${personLink(r.id, r.name)}</td><td>${r.n_unions}</td></tr>`).join('');
  const remTable = `
    <div class="card" style="margin-top:16px;">
      <h3 class="card-title">Personnes remariées</h3>
      <table class="data-table"><thead><tr><th>Individu</th><th>Unions</th></tr></thead><tbody>${remRows || '<tr><td colspan=2 class="card-note">Aucun remariage détecté</td></tr>'}</tbody></table>
    </div>`;

  const famSearch = `
    <div class="search-bar" style="margin-top:16px;">
      <input type="text" id="famSearch" placeholder="Rechercher une famille (nom d'un conjoint)…">
      <span class="count" id="famCount"></span>
    </div>
    <div class="card wide">
      <div style="max-height:480px; overflow-y:auto;">
        <table class="data-table" id="famTable">
          <thead><tr><th>Époux</th><th>Épouse</th><th>Mariage</th><th>Enfants</th><th>Actions</th></tr></thead>
          <tbody id="famTableBody"></tbody>
        </table>
      </div>
    </div>`;

  document.getElementById('panel-familles').innerHTML =
    sectionTitle('04', 'Structure familiale') + kpis + `<div class="two-col" style="margin-top:16px;">${largeTable}${remTable}</div>` +
    famSearch + createUnionFormHTML();

  const fambody = document.getElementById('famTableBody');
  const famCount = document.getElementById('famCount');
  function renderFamRows(filter){
    const f = filter ? normalize(filter) : '';
    const filtered = DATA.families.filter(fam => !f || normalize((fam.husb_name || '') + ' ' + (fam.wife_name || '')).includes(f));
    famCount.textContent = `${fmtInt(filtered.length)} / ${fmtInt(DATA.families.length)} familles`;
    fambody.innerHTML = filtered.map(fam => `
      <tr>
        <td>${personLink(fam.husb, fam.husb_name)}</td>
        <td>${personLink(fam.wife, fam.wife_name)}</td>
        <td>${fam.marriage.known ? escapeHtml(fam.marriage.display || '?') + (fam.marriage.place ? ' — ' + escapeHtml(fam.marriage.place) : '') : '—'}</td>
        <td>${fam.n_children}</td>
        <td><div class="fam-row-actions">
          <button type="button" class="btn secondary small" data-fam-edit="${fam.id}">Modifier</button>
          <button type="button" class="btn danger small" data-fam-delete="${fam.id}">Supprimer</button>
        </div></td>
      </tr>`).join('');
  }
  renderFamRows('');
  document.getElementById('famSearch').addEventListener('input', e => renderFamRows(e.target.value));

  fambody.addEventListener('mousedown', e => {
    const editBtn = e.target.closest('[data-fam-edit]');
    const delBtn = e.target.closest('[data-fam-delete]');
    if (editBtn) openFamilyEditModal(editBtn.getAttribute('data-fam-edit'));
    if (delBtn) {
      const fam = DATA.families.find(f => f.id === delBtn.getAttribute('data-fam-delete'));
      const label = `${fam.husb_name || '?'} × ${fam.wife_name || '?'}`;
      if (confirm(`Supprimer l'union ${label} ? Les enfants deviendront orphelins (parents inconnus), ils ne seront pas supprimés.`)) {
        deleteFamily(STATE, fam.id);
        markDirty();
        refresh();
      }
    }
  });

  wireCreateUnionForm();
}

function renderPatronymes(){
  const s = DATA.stats.surnames;
  const maxTop = Math.max(1, ...s.top_surnames.map(x => x[1]));
  const kpis = `
    <div class="grid cols-3">
      <div class="card kpi"><div class="value">${fmtInt(s.total_distinct)}</div><div class="label">Patronymes distincts</div></div>
      <div class="card kpi"><div class="value">${s.top_surnames[0] ? escapeHtml(s.top_surnames[0][0]) : '—'}</div><div class="label">Patronyme le plus fréquent</div><div class="sub">${s.top_surnames[0] ? fmtInt(s.top_surnames[0][1]) + ' occurrences' : ''}</div></div>
      <div class="card kpi"><div class="value">${Object.keys(s.evolution_by_period).length}</div><div class="label">Périodes analysées (par 50 ans)</div></div>
    </div>`;

  const topList = `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Fréquence des patronymes (top 25)</h3>
      ${barListHTML(s.top_surnames, maxTop)}
    </div>`;

  const periods = Object.entries(s.evolution_by_period);
  const evoRows = periods.map(([p, list]) => `
    <tr><td>${p}&ndash;${Number(p) + 49}</td><td>${list.map(([n, c]) => `<span class="pill">${escapeHtml(n)} (${c})</span>`).join(' ')}</td></tr>`).join('');
  const evoTable = `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Évolution des patronymes dominants par période (année de naissance)</h3>
      <table class="data-table"><thead><tr><th>Période</th><th>Patronymes dominants</th></tr></thead><tbody>${evoRows}</tbody></table>
    </div>`;

  document.getElementById('panel-patronymes').innerHTML = sectionTitle('05', 'Patronymes') + kpis + topList + evoTable;
}

function renderQualite(){
  const s = DATA.stats.quality;
  const fieldLabels = {
    date_naissance: 'Date de naissance', lieu_naissance: 'Lieu de naissance',
    date_deces: 'Date de décès (parmi les décédé(e)s)', lieu_deces: 'Lieu de décès (parmi les décédé(e)s)',
    sexe_connu: 'Sexe renseigné', famille_parentale_connue: 'Filiation connue',
  };
  const compRows = Object.entries(s.completeness).map(([k, v]) => `
    <div class="row"><div class="rlabel">${fieldLabels[k] || k}</div><div class="rtrack"><div class="rfill" style="width:${v}%"></div></div><div class="rval">${v}%</div></div>`).join('');
  const completeness = `
    <div class="card wide">
      <h3 class="card-title">Taux de complétude des fiches</h3>
      <div class="bar-list">${compRows}</div>
    </div>`;

  const kpis = `
    <div class="grid cols-2" style="margin-top:16px;">
      <div class="card kpi"><div class="value">${fmtInt(s.anomalies_count)}</div><div class="label">Anomalies détectées</div></div>
      <div class="card kpi"><div class="value">${fmtInt(s.duplicates_count)}</div><div class="label">Doublons potentiels</div></div>
    </div>`;

  const typeLabels = {
    deces_avant_naissance: 'Décès avant naissance',
    age_deces_invraisemblable: 'Âge au décès invraisemblable',
    enfant_avant_parent: 'Enfant né avant son parent',
    parent_trop_jeune: 'Parent très jeune (< 10 ans)',
    parent_trop_age: 'Parent âgé (> 65 ans)',
    mariage_trop_jeune: 'Mariage précoce (< 12 ans)',
    deces_manquant_probable: 'Décès probable non renseigné',
  };
  const anomRows = s.anomalies.map(a => `
    <tr><td><span class="pill warn">${typeLabels[a.type] || a.type}</span></td><td>${personLink(a.id, a.name)}</td><td>${escapeHtml(a.detail)}</td></tr>`).join('');
  const anomTable = `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Anomalies (incohérences de dates)</h3>
      <div style="max-height:420px; overflow-y:auto;">
      <table class="data-table"><thead><tr><th>Type</th><th>Individu</th><th>Détail</th></tr></thead><tbody>${anomRows || '<tr><td colspan=3 class="card-note">Aucune anomalie détectée</td></tr>'}</tbody></table>
      </div>
    </div>`;

  const dupRows = s.duplicates.map(d => `
    <tr><td>${escapeHtml(d.name)}</td><td>${d.year ?? '?'}</td><td>${d.ids.map(id => personLink(id, INDEX[id] ? INDEX[id].name : id)).join(' &middot; ')}</td></tr>`).join('');
  const dupTable = `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Doublons potentiels (même prénom, nom et année de naissance)</h3>
      <div style="max-height:360px; overflow-y:auto;">
      <table class="data-table"><thead><tr><th>Nom</th><th>Année</th><th>Fiches concernées</th></tr></thead><tbody>${dupRows || '<tr><td colspan=3 class="card-note">Aucun doublon détecté</td></tr>'}</tbody></table>
      </div>
    </div>`;

  document.getElementById('panel-qualite').innerHTML = sectionTitle('06', 'Qualité des données') + completeness + kpis + anomTable + dupTable;
}

function renderIndividusPanel(){
  const gens = Array.from(new Set(DATA.individuals.map(r => r.generation).filter(g => g !== null && g !== undefined))).sort((a, b) => a - b);
  const genOptions = gens.map(g => `<option value="${g}">${genLabel(g)}</option>`).join('');

  document.getElementById('panel-individus').innerHTML = sectionTitle('07', 'Fiches individuelles') + `
    <div class="note-box">Cliquez sur une fiche pour consulter le détail : dates, lieux, ascendants, descendants et fratrie. « Sang » = famille par le sang (ascendant·e, descendant·e ou collatéral·e) ; « Alliance » = lié·e uniquement par un mariage.</div>
    <div class="search-bar">
      <input type="text" id="indSearch" placeholder="Rechercher par nom, prénom…">
      <select id="indSex"><option value="">Tous sexes</option><option value="M">Hommes</option><option value="F">Femmes</option></select>
      <select id="indStatus"><option value="">Tous statuts</option><option value="alive">Vivant(e)s</option><option value="deceased">Décédé(e)s</option></select>
      <select id="indGen"><option value="">Toutes générations</option>${genOptions}</select>
      <select id="indRelation"><option value="">Tous liens</option><option value="blood">Famille par le sang</option><option value="marriage">Par alliance</option></select>
      <span class="count" id="indCount"></span>
    </div>
    <div class="ind-list" id="indList"></div>
  `;

  const list = document.getElementById('indList');
  // mousedown (pas click) : si le champ de recherche a encore le focus, le
  // blur déclenché par le clic peut empêcher l'événement "click" de se
  // déclencher sur la ligne fraîchement affichée après un filtrage.
  list.addEventListener('mousedown', e => {
    const card = e.target.closest('.ind-card');
    if (card) openIndividual(card.dataset.id);
  });

  function apply(){
    const text = normalize(document.getElementById('indSearch').value);
    const sex = document.getElementById('indSex').value;
    const status = document.getElementById('indStatus').value;
    const gen = document.getElementById('indGen').value;
    const relation = document.getElementById('indRelation').value;
    let items = DATA.individuals.filter(r => {
      if (text && !normalize(r.name).includes(text)) return false;
      if (sex && r.sex !== sex) return false;
      if (status === 'alive' && !r.alive) return false;
      if (status === 'deceased' && !r.death.known) return false;
      if (gen !== '' && String(r.generation) !== gen) return false;
      if (relation === 'blood' && r.relation === 'marriage') return false;
      if (relation === 'marriage' && r.relation !== 'marriage') return false;
      return true;
    });
    items.sort((a, b) => (a.surname || '').localeCompare(b.surname || '') || (a.given || '').localeCompare(b.given || ''));
    document.getElementById('indCount').textContent = `${fmtInt(items.length)} / ${fmtInt(DATA.individuals.length)} individus`;
    const MAXR = 400;
    const shown = items.slice(0, MAXR);
    list.innerHTML = shown.map(r => `
      <div class="ind-card" data-id="${r.id}">
        <span class="sexdot ${r.sex}"></span>
        <span class="iname">${escapeHtml(r.name)}<small>${escapeHtml(r.birth.place || '')}</small></span>
        <span class="idates">${lifeSpanShort(r)}</span>
        ${relBadgeHTML(r.relation)}
        <span class="igen" title="${escapeHtml(genTitle(r.generation))}">${genLabel(r.generation)}</span>
      </div>`).join('') + (items.length > MAXR ? `<p class="card-note">Affinez la recherche pour afficher les ${fmtInt(items.length - MAXR)} fiches supplémentaires.</p>` : '');
  }
  ['indSearch', 'indSex', 'indStatus', 'indGen', 'indRelation'].forEach(id => {
    document.getElementById(id).addEventListener('input', apply);
    document.getElementById(id).addEventListener('change', apply);
  });
  apply();
}

/* ------------------------------------------------------------------ */
/* Arbre généalogique (pedigree ascendant, en éventail binaire)         */
/* ------------------------------------------------------------------ */

let treeRootId = null;
let treeDepth = 5;
let treeZoom = 1;

/** Père et mère d'un individu d'après STATE (source de vérité HUSB/WIFE). */
function getParentsFromState(id){
  const ind = STATE.individuals.get(id);
  if (!ind || !ind.famc.length) return [null, null];
  const fam = STATE.families.get(ind.famc[0]);
  if (!fam) return [null, null];
  return [fam.husb || null, fam.wife || null];
}

/** Calcule les positions (x, y) de chaque case d'un pedigree ascendant
 * binaire à profondeur fixe, en partant de la génération la plus profonde
 * (positions régulièrement espacées) puis en remontant : chaque ancêtre est
 * centré verticalement entre ses deux propres branches — c'est l'agencement
 * classique des chartes de pedigree généalogiques. */
function computeAncestorLayout(rootId, depth){
  const NODE_W = 190, NODE_H = 52, COL_W = 230, ROW_H = 62;
  const idsByGen = [[rootId]];
  for (let g = 0; g < depth - 1; g++) {
    const prev = idsByGen[g];
    const next = new Array(prev.length * 2).fill(null);
    prev.forEach((id, k) => {
      const [father, mother] = id ? getParentsFromState(id) : [null, null];
      next[2 * k] = father;
      next[2 * k + 1] = mother;
    });
    idsByGen.push(next);
  }

  const yByGen = new Array(depth);
  const deepest = depth - 1;
  yByGen[deepest] = idsByGen[deepest].map((_, k) => k * ROW_H);
  for (let g = deepest - 1; g >= 0; g--) {
    yByGen[g] = idsByGen[g].map((_, k) => (yByGen[g + 1][2 * k] + yByGen[g + 1][2 * k + 1]) / 2);
  }

  const nodes = [];
  const links = [];
  for (let g = 0; g < depth; g++) {
    idsByGen[g].forEach((id, k) => {
      const x = g * COL_W;
      const y = yByGen[g][k];
      nodes.push({ id, gen: g, x, y, w: NODE_W, h: NODE_H });
      if (g < depth - 1) {
        const fatherId = idsByGen[g + 1][2 * k];
        const motherId = idsByGen[g + 1][2 * k + 1];
        const fy = yByGen[g + 1][2 * k], my = yByGen[g + 1][2 * k + 1];
        if (id != null || fatherId != null) {
          links.push({ x1: x + NODE_W, y1: y + NODE_H / 2, x2: (g + 1) * COL_W, y2: fy + NODE_H / 2, show: !!(id && fatherId) });
        }
        if (id != null || motherId != null) {
          links.push({ x1: x + NODE_W, y1: y + NODE_H / 2, x2: (g + 1) * COL_W, y2: my + NODE_H / 2, show: !!(id && motherId) });
        }
      }
    });
  }
  const width = depth * COL_W;
  const height = Math.pow(2, deepest) * ROW_H;
  return { nodes, links, width, height, NODE_W, NODE_H };
}

function treeNodeHTML(node){
  if (!node.id) {
    return `<div class="tree-node empty" style="left:${node.x}px; top:${node.y}px; width:${node.w}px; min-height:${node.h}px;">?</div>`;
  }
  const r = INDEX[node.id];
  if (!r) return '';
  const isRoot = node.id === treeRootId;
  return `<div class="tree-node sex-${r.sex}${isRoot ? ' is-root' : ''}" data-open-id="${r.id}" style="left:${node.x}px; top:${node.y}px; width:${node.w}px; min-height:${node.h}px;" title="${escapeHtml(genTitle(r.generation))}">
    <div class="tn-name">${escapeHtml(r.name)}</div>
    <div class="tn-dates">${lifeSpanShort(r)}</div>
  </div>`;
}

function renderTreeCanvas(){
  const mount = document.getElementById('treeCanvasMount');
  if (!mount) return;
  if (!treeRootId || !INDEX[treeRootId]) {
    mount.innerHTML = `<p class="card-note" style="padding:20px;">Choisissez une personne pour afficher son arbre ascendant.</p>`;
    return;
  }
  const layout = computeAncestorLayout(treeRootId, treeDepth);
  const linksSVG = layout.links.filter(l => l.show).map(l =>
    `<line x1="${l.x1}" y1="${l.y1}" x2="${l.x2}" y2="${l.y2}"/>`
  ).join('');
  const nodesHTML = layout.nodes.map(treeNodeHTML).join('');
  mount.innerHTML = `
    <div class="tree-canvas" style="width:${layout.width}px; height:${layout.height}px; transform:scale(${treeZoom});">
      <svg class="tree-links" width="${layout.width}" height="${layout.height}">${linksSVG}</svg>
      ${nodesHTML}
    </div>`;
}

function renderArbre(){
  const panel = document.getElementById('panel-arbre');
  if (!treeRootId || !INDEX[treeRootId]) {
    treeRootId = (DATA.meta && DATA.meta.root_individual && INDEX[DATA.meta.root_individual])
      ? DATA.meta.root_individual
      : (DATA.individuals[0] ? DATA.individuals[0].id : null);
  }
  const root = treeRootId ? INDEX[treeRootId] : null;

  panel.innerHTML = `
    ${sectionTitle('08', 'Arbre généalogique')}
    <div class="note-box">Arbre ascendant (pedigree) centré sur la personne choisie. Cliquez sur une case pour ouvrir sa fiche ; utilisez « Voir dans l'arbre » depuis une fiche pour recentrer l'arbre sur cette personne.</div>
    <div class="tree-controls">
      <label style="font-size:12.5px; color:var(--ink-soft);">Personne au centre :
        <select id="treeRootSelect" style="margin-left:6px;">${personSelectOptions(treeRootId, null).replace('— Aucun —', '— Choisir —')}</select>
      </label>
      <label style="font-size:12.5px; color:var(--ink-soft);">Générations :
        <select id="treeDepthSelect" style="margin-left:6px;">
          ${[2, 3, 4, 5, 6, 7, 8].map(d => `<option value="${d}" ${d === treeDepth ? 'selected' : ''}>${d}</option>`).join('')}
        </select>
      </label>
      <div class="zoom-row">
        <button type="button" class="btn secondary small" id="treeZoomOut">&minus;</button>
        <span id="treeZoomLabel" style="font-size:12.5px; color:var(--ink-soft); min-width:38px; text-align:center;">${Math.round(treeZoom * 100)}%</span>
        <button type="button" class="btn secondary small" id="treeZoomIn">+</button>
      </div>
    </div>
    <div class="tree-scroll"><div id="treeCanvasMount"></div></div>
    ${root ? `
    <div class="tree-side">
      <h4>Conjoint(s) de ${escapeHtml(root.name)}</h4>
      <div class="rel-people">${root.spouses.length ? root.spouses.map(id => INDEX[id] ? `<span data-open-id="${id}">${escapeHtml(INDEX[id].name)}</span>` : '').join('') : '<span style="opacity:.55;">Aucun connu</span>'}</div>
      <h4 style="margin-top:14px;">Enfants de ${escapeHtml(root.name)}</h4>
      <div class="rel-people">${root.children.length ? root.children.map(id => INDEX[id] ? `<span data-open-id="${id}">${escapeHtml(INDEX[id].name)}</span>` : '').join('') : '<span style="opacity:.55;">Aucun connu</span>'}</div>
    </div>` : ''}
  `;

  renderTreeCanvas();

  document.getElementById('treeRootSelect').addEventListener('change', e => {
    if (e.target.value) { treeRootId = e.target.value; renderArbre(); }
  });
  document.getElementById('treeDepthSelect').addEventListener('change', e => {
    treeDepth = parseInt(e.target.value, 10); renderTreeCanvas();
  });
  function applyZoom(delta){
    treeZoom = Math.max(0.4, Math.min(1.5, Math.round((treeZoom + delta) * 10) / 10));
    document.getElementById('treeZoomLabel').textContent = `${Math.round(treeZoom * 100)}%`;
    const canvas = document.querySelector('#treeCanvasMount .tree-canvas');
    if (canvas) canvas.style.transform = `scale(${treeZoom})`;
  }
  document.getElementById('treeZoomIn').addEventListener('mousedown', () => applyZoom(0.1));
  document.getElementById('treeZoomOut').addEventListener('mousedown', () => applyZoom(-0.1));
}

/* ------------------------------------------------------------------ */
/* Fiche individuelle (modale)                                          */
/* ------------------------------------------------------------------ */

function openIndividual(id){
  const r = INDEX[id];
  if (!r) return;
  const relChips = (ids, emptyMsg) => ids.length
    ? ids.map(pid => {
        const p = INDEX[pid];
        return p ? `<span data-open-id="${p.id}">${escapeHtml(p.name)}</span>` : '';
      }).join('')
    : `<span style="opacity:.55; cursor:default;">${emptyMsg}</span>`;

  const statusPill = r.death.known
    ? `<span class="pill bad">Décédé(e)</span>`
    : (r.alive ? `<span class="pill ok">Vivant(e)${r.current_age != null ? ' · ' + r.current_age + ' ans' : ''}</span>` : `<span class="pill warn">Statut inconnu</span>`);

  document.getElementById('ficheContent').innerHTML = `
    <button class="close-btn" id="ficheClose" aria-label="Fermer">&times;</button>
    <h2>${escapeHtml(r.name)}</h2>
    <div class="fiche-sub">${escapeHtml(genTitle(r.generation))} &middot; ${r.sex === 'M' ? 'Homme' : r.sex === 'F' ? 'Femme' : 'Sexe inconnu'} &middot; ${statusPill} ${relBadgeHTML(r.relation)}</div>
    <dl class="fiche-facts">
      <dt>Naissance</dt><dd>${r.birth.known ? (escapeHtml(r.birth.display || 'date inconnue') + (r.birth.place ? ' — ' + escapeHtml(r.birth.place) : '')) : 'Inconnue'}</dd>
      <dt>Décès</dt><dd>${r.death.known ? (escapeHtml(r.death.display || 'date inconnue') + (r.death.place ? ' — ' + escapeHtml(r.death.place) : '') + (r.death.cause ? ' · Cause : ' + escapeHtml(r.death.cause) : '')) : (r.alive ? '—' : 'Inconnu')}</dd>
      ${r.age_at_death != null ? `<dt>Âge au décès</dt><dd>${r.age_at_death} ans</dd>` : ''}
      ${r.occupation ? `<dt>Profession</dt><dd>${escapeHtml(r.occupation)}</dd>` : ''}
    </dl>
    <div class="rel-block"><h4>Parents</h4><div class="rel-people">${relChips(r.parents, 'Inconnus')}</div></div>
    <div class="rel-block"><h4>Conjoint(s)</h4><div class="rel-people">${relChips(r.spouses, 'Aucun connu')}</div></div>
    <div class="rel-block"><h4>Enfants</h4><div class="rel-people">${relChips(r.children, 'Aucun connu')}</div></div>
    <div class="rel-block"><h4>Frères et sœurs</h4><div class="rel-people">${relChips(r.siblings, 'Aucun connu')}</div></div>
    <div class="fiche-actions">
      <button type="button" class="btn secondary" id="ficheTreeBtn">Voir dans l'arbre</button>
      <button type="button" class="btn secondary" id="ficheEditBtn">Modifier cette fiche</button>
      <button type="button" class="btn danger" id="ficheDeleteBtn">Supprimer</button>
    </div>
  `;
  document.getElementById('ficheClose').addEventListener('click', closeFiche);
  document.getElementById('modalOverlay').classList.add('open');
  currentFicheId = id;

  document.getElementById('ficheTreeBtn').addEventListener('mousedown', () => {
    closeFiche();
    treeRootId = id;
    goToTab('arbre');
    renderArbre();
  });
  document.getElementById('ficheEditBtn').addEventListener('mousedown', () => {
    closeFiche();
    goToTab('edition');
    renderPersonFormInto(document.getElementById('personFormMount'), id);
    document.getElementById('personFormMount').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  document.getElementById('ficheDeleteBtn').addEventListener('mousedown', () => {
    if (confirm(`Supprimer définitivement la fiche de ${r.name} ? Cette action ne peut pas être annulée (sauf en rechargeant le fichier d'origine).`)) {
      deleteIndividual(STATE, id);
      markDirty();
      closeFiche();
      refresh();
    }
  });
}
let currentFicheId = null;
function closeFiche(){
  document.getElementById('modalOverlay').classList.remove('open');
  currentFicheId = null;
}
function goToTab(tab){
  document.querySelectorAll('nav.tabs button').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === 'panel-' + tab));
}

/* ------------------------------------------------------------------ */
/* Édition : formulaires personne / union, chargement, export           */
/* ------------------------------------------------------------------ */

let dirty = false;
function markDirty(){ dirty = true; updateDirtyIndicator(); }
function updateDirtyIndicator(){
  const el = document.getElementById('dirtyIndicator');
  if (el) el.style.display = dirty ? 'inline-block' : 'none';
}

const QUALIFIER_OPTIONS = [
  ['', 'Date exacte'], ['ABT', 'Vers (ABT)'], ['EST', 'Estimée (EST)'],
  ['BEF', 'Avant (BEF)'], ['AFT', 'Après (AFT)'], ['CAL', 'Calculée (CAL)'],
];

function dateFieldsHTML(prefix, gedDate){
  const q = gedDate ? (gedDate.qualifier || '') : '';
  const d = gedDate ? (gedDate.day || '') : '';
  const m = gedDate ? (gedDate.month || '') : '';
  const y = gedDate ? (gedDate.year || '') : '';
  const qOpts = QUALIFIER_OPTIONS.map(([v, l]) => `<option value="${v}" ${v === q ? 'selected' : ''}>${l}</option>`).join('');
  const mOpts = ['', ...MONTH_LABELS_FR].map((label, i) => {
    if (i === 0) return `<option value="">Mois</option>`;
    return `<option value="${i}" ${i === Number(m) ? 'selected' : ''}>${label}</option>`;
  }).join('');
  return `
    <div class="date-fields">
      <select name="${prefix}Qualifier">${qOpts}</select>
      <input type="number" name="${prefix}Day" placeholder="Jour" min="1" max="31" value="${d}">
      <select name="${prefix}Month">${mOpts}</select>
      <input type="number" name="${prefix}Year" placeholder="Année" min="1" max="2200" value="${y}">
    </div>`;
}
function readDateFields(form, prefix){
  const q = form.elements[`${prefix}Qualifier`].value || null;
  const d = form.elements[`${prefix}Day`].value ? parseInt(form.elements[`${prefix}Day`].value, 10) : null;
  const m = form.elements[`${prefix}Month`].value ? parseInt(form.elements[`${prefix}Month`].value, 10) : null;
  const y = form.elements[`${prefix}Year`].value ? parseInt(form.elements[`${prefix}Year`].value, 10) : null;
  if (!d && !m && !y) return null;
  return buildGedDateFromForm(q, d, m, y);
}

function personSelectOptions(selectedId, excludeId){
  const people = DATA.individuals.filter(r => r.id !== excludeId)
    .slice().sort((a, b) => (a.surname || '').localeCompare(b.surname || '') || (a.given || '').localeCompare(b.given || ''));
  const opts = ['<option value="">— Aucun —</option>'];
  for (const p of people) {
    opts.push(`<option value="${p.id}" ${p.id === selectedId ? 'selected' : ''}>${escapeHtml(p.name)}${p.birth.year ? ' (' + p.birth.year + ')' : ''}</option>`);
  }
  return opts.join('');
}

function personFormHTML(existingId){
  const r = existingId ? INDEX[existingId] : null;
  const father = r ? (r.parents.map(pid => INDEX[pid]).find(p => p && p.sex === 'M') || (r.parents[0] ? INDEX[r.parents[0]] : null)) : null;
  const mother = r ? (r.parents.map(pid => INDEX[pid]).find(p => p && p.sex === 'F') || (r.parents[1] ? INDEX[r.parents[1]] : null)) : null;
  const fatherId = father ? father.id : (r && r.parents[0] ? r.parents[0] : '');
  const motherId = mother && mother.id !== fatherId ? mother.id : (r && r.parents[1] && r.parents[1] !== fatherId ? r.parents[1] : '');

  const birthGed = existingId ? STATE.individuals.get(existingId).birth.date : null;
  const deathGed = existingId ? STATE.individuals.get(existingId).death.date : null;
  const isDeceased = existingId ? STATE.individuals.get(existingId).death.known : false;

  return `
    <form id="personForm" class="edit-form" data-editing="${existingId || ''}">
      <div class="field span-2"><label>Prénom(s)</label><input type="text" name="given" value="${escapeHtml(r ? r.given : '')}" required></div>
      <div class="field span-2"><label>Nom de famille</label><input type="text" name="surname" value="${escapeHtml(r ? r.surname : '')}"></div>
      <div class="field"><label>Sexe</label>
        <select name="sex">
          <option value="U" ${(!r || r.sex === 'U') ? 'selected' : ''}>Inconnu</option>
          <option value="M" ${r && r.sex === 'M' ? 'selected' : ''}>Homme</option>
          <option value="F" ${r && r.sex === 'F' ? 'selected' : ''}>Femme</option>
        </select>
      </div>
      <div class="field span-3"><label>Profession</label><input type="text" name="occupation" value="${escapeHtml(r ? (r.occupation || '') : '')}"></div>

      <fieldset>
        <legend>Naissance</legend>
        <div class="field span-4" style="margin-bottom:8px;">${dateFieldsHTML('birth', birthGed)}</div>
        <div class="field span-4"><label>Lieu de naissance</label><input type="text" name="birthPlace" value="${escapeHtml(r ? (r.birth.place || '') : '')}" placeholder="Ville, département, région, pays"></div>
      </fieldset>

      <fieldset>
        <legend>Décès</legend>
        <div class="checkbox-row"><input type="checkbox" id="deceasedCheck" name="deceased" ${isDeceased ? 'checked' : ''}><label for="deceasedCheck" style="text-transform:none; font-size:13px;">Cette personne est décédée</label></div>
        <div id="deathFields" class="death-fields" style="display:${isDeceased ? 'grid' : 'none'};">
          <div class="field span-4">${dateFieldsHTML('death', deathGed)}</div>
          <div class="field span-2"><label>Lieu de décès</label><input type="text" name="deathPlace" value="${escapeHtml(r ? (r.death.place || '') : '')}"></div>
          <div class="field span-2"><label>Cause du décès</label><input type="text" name="deathCause" value="${escapeHtml(r ? (r.death.cause || '') : '')}"></div>
        </div>
      </fieldset>

      <div class="field span-2"><label>Père</label><select name="fatherId">${personSelectOptions(fatherId, existingId)}</select></div>
      <div class="field span-2"><label>Mère</label><select name="motherId">${personSelectOptions(motherId, existingId)}</select></div>

      <div class="action-row">
        <button type="submit" class="btn">${existingId ? 'Enregistrer les modifications' : 'Ajouter cette personne'}</button>
        ${existingId ? '<button type="button" class="btn secondary" id="personFormCancel">Annuler</button>' : ''}
      </div>
    </form>
    <div class="flash-msg" id="personFormFlash"></div>`;
}

function renderPersonFormInto(container, existingId){
  container.innerHTML = `<h3 class="card-title">${existingId ? 'Modifier la fiche' : 'Ajouter une personne'}</h3>` + personFormHTML(existingId);
  const form = document.getElementById('personForm');
  const deceasedCheck = document.getElementById('deceasedCheck');
  const deathFields = document.getElementById('deathFields');
  deceasedCheck.addEventListener('change', () => { deathFields.style.display = deceasedCheck.checked ? 'grid' : 'none'; });

  const cancelBtn = document.getElementById('personFormCancel');
  if (cancelBtn) cancelBtn.addEventListener('mousedown', () => renderPersonFormInto(container, null));

  form.addEventListener('submit', e => {
    e.preventDefault();
    const fields = {
      given: form.elements.given.value, surname: form.elements.surname.value, sex: form.elements.sex.value,
      birthDate: readDateFields(form, 'birth'), birthPlace: form.elements.birthPlace.value || null,
      deceased: form.elements.deceased.checked,
      deathDate: readDateFields(form, 'death'), deathPlace: form.elements.deathPlace.value || null,
      deathCause: form.elements.deathCause.value || null,
      occupation: form.elements.occupation.value || null,
      fatherId: form.elements.fatherId.value || null, motherId: form.elements.motherId.value || null,
    };
    const editingId = form.dataset.editing || null;
    let newId;
    if (editingId) { updateIndividual(STATE, editingId, fields); newId = editingId; }
    else { newId = addIndividual(STATE, fields); }
    markDirty();
    refresh();
    const flash = document.getElementById('personFormFlash');
    renderPersonFormInto(container, null);
    const flash2 = document.getElementById('personFormFlash');
    if (flash2) {
      flash2.textContent = editingId ? `Fiche de ${fields.given} ${fields.surname} mise à jour.` : `${fields.given} ${fields.surname} ajouté(e) avec succès.`;
      flash2.classList.add('show');
    }
  });
}

function createUnionFormHTML(){
  return `
    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Créer une union</h3>
      <form id="unionForm" class="edit-form">
        <div class="field span-2"><label>Époux</label><select name="husbId">${personSelectOptions('', null)}</select></div>
        <div class="field span-2"><label>Épouse</label><select name="wifeId">${personSelectOptions('', null)}</select></div>
        <fieldset>
          <legend>Mariage</legend>
          <div class="field span-4" style="margin-bottom:8px;">${dateFieldsHTML('marriage', null)}</div>
          <div class="field span-3"><label>Lieu de mariage</label><input type="text" name="marriagePlace"></div>
          <div class="checkbox-row" style="grid-column: span 1; align-items:flex-end;"><input type="checkbox" id="divorcedCheck" name="divorced"><label for="divorcedCheck" style="text-transform:none; font-size:13px;">Divorcé(e)s</label></div>
        </fieldset>
        <div class="action-row"><button type="submit" class="btn">Créer l'union</button></div>
      </form>
      <div class="flash-msg" id="unionFormFlash"></div>
    </div>`;
}
function wireCreateUnionForm(){
  const form = document.getElementById('unionForm');
  if (!form) return;
  form.addEventListener('submit', e => {
    e.preventDefault();
    const fields = {
      husbId: form.elements.husbId.value || null, wifeId: form.elements.wifeId.value || null,
      marriageDate: readDateFields(form, 'marriage'), marriagePlace: form.elements.marriagePlace.value || null,
      married: true, divorced: form.elements.divorced.checked,
    };
    if (!fields.husbId && !fields.wifeId) return;
    createFamily(STATE, fields);
    markDirty();
    refresh();
  });
}

function openFamilyEditModal(famId){
  const fam = DATA.families.find(f => f.id === famId);
  if (!fam) return;
  const stFam = STATE.families.get(famId);
  document.getElementById('ficheContent').innerHTML = `
    <button class="close-btn" id="ficheClose" aria-label="Fermer">&times;</button>
    <h2>${escapeHtml(fam.husb_name || '?')} × ${escapeHtml(fam.wife_name || '?')}</h2>
    <div class="fiche-sub">Modifier l'union</div>
    <form id="famEditForm" class="edit-form">
      <fieldset>
        <legend>Mariage</legend>
        <div class="field span-4" style="margin-bottom:8px;">${dateFieldsHTML('marriage', stFam.marriage.date)}</div>
        <div class="field span-3"><label>Lieu de mariage</label><input type="text" name="marriagePlace" value="${escapeHtml(stFam.marriage.place || '')}"></div>
        <div class="checkbox-row" style="grid-column: span 1; align-items:flex-end;"><input type="checkbox" id="divorcedCheckEdit" name="divorced" ${stFam.divorced ? 'checked' : ''}><label for="divorcedCheckEdit" style="text-transform:none; font-size:13px;">Divorcé(e)s</label></div>
      </fieldset>
      <div class="action-row"><button type="submit" class="btn">Enregistrer</button></div>
    </form>`;
  document.getElementById('ficheClose').addEventListener('click', closeFiche);
  document.getElementById('modalOverlay').classList.add('open');
  document.getElementById('famEditForm').addEventListener('submit', e => {
    e.preventDefault();
    const form = e.target;
    updateFamily(STATE, famId, {
      marriageDate: readDateFields(form, 'marriage'), marriagePlace: form.elements.marriagePlace.value || null,
      married: true, divorced: form.elements.divorced.checked,
    });
    markDirty();
    closeFiche();
    refresh();
  });
}

function renderEdition(){
  const panel = document.getElementById('panel-edition');
  panel.innerHTML = `
    ${sectionTitle('09', 'Édition')}
    <div class="note-box">Les modifications ne sont conservées que dans cette page (mémoire du navigateur). Pensez à <b>exporter en GEDCOM</b> pour sauvegarder votre travail, ou à le committer/pousser vous-même si ce fichier fait partie d'un dépôt.</div>

    <div class="card wide">
      <h3 class="card-title">Charger un fichier GEDCOM</h3>
      <div class="upload-row">
        <input type="file" id="loadGedFile" accept=".ged,.txt">
        <span style="color:var(--ink-faint); font-size:12.5px;">Remplace les données actuellement affichées.</span>
      </div>
      <div class="flash-msg" id="loadFlash"></div>
    </div>

    <div class="card wide" style="margin-top:16px;">
      <h3 class="card-title">Exporter en GEDCOM</h3>
      <p class="card-note">Génère un fichier .ged à partir de l'état actuel (avec vos éditions).</p>
      <div class="action-row">
        <button type="button" class="btn" id="exportGedBtn">Exporter en GEDCOM (.ged)</button>
        <span id="dirtyIndicator" class="pill warn" style="display:none; align-self:center;">Modifications non exportées</span>
      </div>
    </div>

    <div class="card wide" style="margin-top:16px;" id="personFormMount"></div>
  `;

  document.getElementById('loadGedFile').addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    if (dirty && !confirm('Charger ce fichier remplacera les données actuelles, y compris vos modifications non exportées. Continuer ?')) {
      e.target.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const newState = parseGedcomText(reader.result);
        if (newState.individuals.size === 0) throw new Error('Aucun individu détecté dans ce fichier.');
        STATE = newState;
        dirty = false;
        refresh();
        goToTab('demographie');
        const flash = document.getElementById('loadFlash');
        if (flash) { flash.textContent = `Fichier chargé : ${newState.individuals.size} individus, ${newState.families.size} familles.`; flash.classList.add('show'); }
      } catch (err) {
        alert('Impossible de lire ce fichier GEDCOM : ' + err.message);
      }
    };
    reader.readAsText(file, 'utf-8');
  });

  document.getElementById('exportGedBtn').addEventListener('mousedown', () => {
    const text = serializeGedcom(STATE);
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'export.ged';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    dirty = false;
    updateDirtyIndicator();
  });

  renderPersonFormInto(document.getElementById('personFormMount'), null);
}

/* ------------------------------------------------------------------ */
/* Initialisation                                                       */
/* ------------------------------------------------------------------ */

function renderMetaChips(){
  const m = DATA.meta;
  document.getElementById('metaChips').innerHTML = `
    <span class="meta-chip"><b>${fmtInt(m.total_individuals)}</b> individus</span>
    <span class="meta-chip"><b>${fmtInt(m.total_families)}</b> familles</span>
    <span class="meta-chip">Racine de l'arbre : <b>${escapeHtml(m.root_name || '—')}</b></span>
    <span class="meta-chip">Généré le <b>${escapeHtml((m.generated_at || '').slice(0, 10))}</b></span>
  `;
  const rootName = m.root_name || 'Arbre généalogique';
  document.getElementById('pageTitle').textContent = rootName;
  document.getElementById('pageSubtitle').textContent =
    `${fmtInt(m.total_individuals)} individus · ${fmtInt(m.total_families)} familles · analyse générée à partir d'un export GEDCOM`;
  document.title = `Registre généalogique — ${rootName}`;
}

function initTabs(){
  document.querySelectorAll('nav.tabs button').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('nav.tabs button').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
    });
  });
}

let STATE = null;
let DATA = null;
window.INDEX = {};

/** Recalcule les statistiques depuis STATE et redessine tous les onglets. */
function refresh(){
  DATA = analyzeGedcom(STATE);
  window.INDEX = {};
  DATA.individuals.forEach(r => { INDEX[r.id] = r; });

  renderMetaChips();
  renderDemographie();
  renderChronologie();
  renderGeographie();
  renderFamilles();
  renderPatronymes();
  renderQualite();
  renderIndividusPanel();
  renderArbre();
  renderEdition();

  if (document.getElementById('modalOverlay').classList.contains('open') && currentFicheId) {
    if (INDEX[currentFicheId]) openIndividual(currentFicheId);
    else closeFiche();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  STATE = reviveGedcomState(RAW_GEDCOM_JSON);
  initTabs();
  refresh();

  document.addEventListener('mousedown', e => {
    const t = e.target.closest('[data-open-id]');
    if (t) openIndividual(t.getAttribute('data-open-id'));
  });
  document.getElementById('modalOverlay').addEventListener('click', e => {
    if (e.target.id === 'modalOverlay') closeFiche();
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeFiche();
  });
});
