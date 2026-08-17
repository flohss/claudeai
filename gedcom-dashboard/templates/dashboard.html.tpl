<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{
  --paper: #f3e9d2;
  --paper-dark: #e9dab8;
  --paper-darker: #ddc89c;
  --ink: #3a2c1c;
  --ink-soft: #5c4a34;
  --ink-faint: #8a7658;
  --line: #c9b184;
  --line-soft: #ddcba3;
  --maroon: #7a2733;
  --maroon-dark: #5c1e27;
  --gold: #a8791f;
  --gold-light: #c99a3d;
  --forest: #3f5b41;
  --slate: #3d5266;
  --card-bg: #fbf5e6;
  --shadow: 0 2px 6px rgba(58,44,28,0.18);
  --radius: 3px;
  --male: #5c7a99;
  --female: #a8536b;
  --font-serif: Georgia, 'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', serif;
  --font-display: 'Palatino Linotype', Palatino, Georgia, serif;
}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;}
body{
  font-family: var(--font-serif);
  color: var(--ink);
  background:
    radial-gradient(ellipse at top left, rgba(255,255,255,0.25), transparent 60%),
    repeating-linear-gradient(0deg, rgba(160,130,80,0.035) 0px, rgba(160,130,80,0.035) 1px, transparent 1px, transparent 3px),
    linear-gradient(180deg, var(--paper) 0%, var(--paper-dark) 100%);
  min-height:100vh;
  line-height:1.5;
}
::selection{ background: var(--gold-light); color:#2a1c10; }
a{ color: var(--maroon); }

.wrap{ max-width:1240px; margin:0 auto; padding:0 20px 60px; }

/* ---------- header ---------- */
header.masthead{
  border-bottom: 4px double var(--ink-faint);
  padding: 28px 20px 18px;
  text-align:center;
  background: linear-gradient(180deg, rgba(255,255,255,0.35), transparent);
}
header.masthead .eyebrow{
  letter-spacing:0.32em; text-transform:uppercase; font-size:11px; color: var(--gold);
  font-family: var(--font-serif);
}
header.masthead h1{
  font-family: var(--font-display);
  font-size: clamp(26px, 4vw, 40px);
  margin: 6px 0 4px;
  color: var(--maroon-dark);
  font-weight: 700;
  letter-spacing: 0.02em;
}
header.masthead .subtitle{
  color: var(--ink-soft); font-style: italic; font-size:15px; margin-bottom: 14px;
}
.meta-chips{
  display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin-top:10px;
}
.meta-chip{
  border:1px solid var(--line); background: rgba(255,255,255,0.5);
  padding:5px 14px; border-radius:20px; font-size:12.5px; color: var(--ink-soft);
}
.meta-chip b{ color: var(--maroon-dark); }

/* ---------- nav tabs ---------- */
nav.tabs{
  display:flex; flex-wrap:wrap; gap:4px; justify-content:center;
  margin: 22px auto 0; padding: 0; list-style:none;
  border-bottom: 2px solid var(--line);
  position: sticky; top:0; z-index: 50;
  background: var(--paper);
  padding-top: 10px;
}
nav.tabs button{
  font-family: var(--font-serif);
  background: var(--paper-darker);
  border: 1px solid var(--line);
  border-bottom: none;
  padding: 10px 18px;
  font-size: 13.5px;
  letter-spacing:0.04em;
  cursor:pointer;
  color: var(--ink-soft);
  border-radius: 6px 6px 0 0;
  transform: translateY(2px);
  transition: all .15s ease;
}
nav.tabs button:hover{ color: var(--maroon-dark); background: var(--card-bg); }
nav.tabs button.active{
  background: var(--card-bg);
  color: var(--maroon-dark);
  font-weight:700;
  border-color: var(--line);
  transform: translateY(0);
  box-shadow: 0 -2px 0 var(--gold) inset;
}

main{ padding-top: 26px; }
.panel{ display:none; animation: fadein .25s ease; }
.panel.active{ display:block; }
@keyframes fadein{ from{opacity:0; transform:translateY(4px);} to{opacity:1; transform:none;} }

h2.section-title{
  font-family: var(--font-display);
  color: var(--maroon-dark);
  font-size: 22px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 8px;
  margin: 6px 0 18px;
  display:flex; align-items:baseline; gap:10px;
}
h2.section-title .num{ color: var(--gold); font-size:14px; letter-spacing:0.15em; }
h3.card-title{
  font-family: var(--font-display);
  font-size: 15.5px; color: var(--maroon-dark); margin:0 0 10px; letter-spacing:0.01em;
}
p.card-note{ color: var(--ink-faint); font-size: 12.5px; margin: 6px 0 0; }

/* ---------- grid & cards ---------- */
.grid{ display:grid; gap:16px; }
.grid.cols-2{ grid-template-columns: repeat(2, 1fr); }
.grid.cols-3{ grid-template-columns: repeat(3, 1fr); }
.grid.cols-4{ grid-template-columns: repeat(4, 1fr); }
@media (max-width: 900px){
  .grid.cols-2, .grid.cols-3, .grid.cols-4{ grid-template-columns: repeat(2,1fr); }
}
@media (max-width: 600px){
  .grid.cols-2, .grid.cols-3, .grid.cols-4{ grid-template-columns: 1fr; }
}

.card{
  background: var(--card-bg);
  border: 1px solid var(--line-soft);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px 18px;
  position: relative;
}
.card.kpi{
  text-align:center;
  padding: 18px 12px;
}
.card.kpi .value{
  font-family: var(--font-display);
  font-size: 30px; color: var(--maroon-dark); font-weight:700; line-height:1.1;
}
.card.kpi .label{
  margin-top:6px; font-size: 12px; text-transform:uppercase; letter-spacing:0.08em; color: var(--ink-soft);
}
.card.kpi .sub{ font-size:11.5px; color: var(--ink-faint); margin-top:4px; }
.card.wide{ grid-column: 1 / -1; }

.corner-seal{
  position:absolute; top:8px; right:10px; font-size: 16px; opacity:0.35;
}

/* ---------- charts (svg) ---------- */
.chart-wrap{ width:100%; overflow-x:auto; }
svg.chart{ width:100%; height:auto; display:block; font-family: var(--font-serif); }
.axis-label{ font-size: 9.5px; fill: var(--ink-soft); }
.axis-line{ stroke: var(--line); stroke-width:1; }
.grid-line{ stroke: var(--line-soft); stroke-width:1; stroke-dasharray:2 3; }
.bar{ fill: var(--maroon); opacity:0.85; cursor:default; transition: opacity .15s; }
.bar:hover{ opacity:1; }
.bar.male{ fill: var(--male); }
.bar.female{ fill: var(--female); }
.bar.gold{ fill: var(--gold); }
.bar.forest{ fill: var(--forest); }
.line-series{ fill:none; stroke-width:2.2; }
.line-dot{ fill: var(--card-bg); stroke-width:1.6; }
.legend{ display:flex; gap:16px; flex-wrap:wrap; font-size:12px; color: var(--ink-soft); margin-top:8px; justify-content:center; }
.legend .swatch{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }

/* ---------- tables & lists ---------- */
table.data-table{ width:100%; border-collapse:collapse; font-size:13px; }
table.data-table th{
  text-align:left; font-family: var(--font-display); color: var(--maroon-dark);
  border-bottom: 2px solid var(--line); padding: 7px 8px; font-size:12.5px;
}
table.data-table td{ padding: 7px 8px; border-bottom: 1px solid var(--line-soft); vertical-align:top; }
table.data-table tr:hover td{ background: rgba(168,121,31,0.06); }
.pill{
  display:inline-block; padding:2px 9px; border-radius:12px; font-size:11px;
  background: var(--paper-darker); color: var(--ink-soft); border:1px solid var(--line);
}
.pill.warn{ background:#f4e0c8; color:#7a4a12; border-color:#d9a95c; }
.pill.bad{ background:#f2dada; color:#7a2733; border-color:#d99999; }
.pill.ok{ background:#e1ead9; color:#3f5b41; border-color:#a9c79c; }
.link-name{ color: var(--maroon); cursor:pointer; text-decoration: underline dotted; user-select:none; }
.link-name:hover{ color: var(--maroon-dark); }

.bar-list{ display:flex; flex-direction:column; gap:7px; }
.bar-list .row{ display:grid; grid-template-columns: 140px 1fr 46px; align-items:center; gap:8px; font-size:12.5px;}
.bar-list .row .rlabel{ color: var(--ink-soft); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.bar-list .row .rtrack{ background: var(--paper-darker); border-radius:3px; height:11px; overflow:hidden; }
.bar-list .row .rfill{ height:100%; background: linear-gradient(90deg, var(--gold), var(--maroon)); }
.bar-list .row .rval{ text-align:right; color: var(--ink-faint); font-variant-numeric: tabular-nums; }

.chip-cloud{ display:flex; flex-wrap:wrap; gap:8px; }
.chip-cloud .chip{
  border:1px solid var(--line); border-radius:20px; padding:5px 12px; background: var(--paper-darker);
  color: var(--ink-soft);
}

/* ---------- individus tab ---------- */
.search-bar{
  display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin-bottom:16px;
  background: var(--card-bg); border:1px solid var(--line-soft); padding:12px 14px; border-radius: var(--radius);
}
.search-bar input[type=text]{
  flex:1; min-width:220px; padding:9px 12px; font-family: var(--font-serif); font-size:14px;
  border:1px solid var(--line); border-radius:3px; background:#fffdf7; color: var(--ink);
}
.search-bar select{
  padding:8px 10px; font-family: var(--font-serif); font-size:13px; border:1px solid var(--line); border-radius:3px; background:#fffdf7;
}
.search-bar .count{ font-size:12.5px; color: var(--ink-faint); white-space:nowrap; }

.ind-list{ display:flex; flex-direction:column; gap:6px; max-height: 640px; overflow-y:auto; padding-right:6px; }
.ind-card{
  display:grid; grid-template-columns: 20px 1fr auto auto; gap:10px; align-items:center;
  background: var(--card-bg); border:1px solid var(--line-soft); border-radius:3px;
  padding:9px 12px; cursor:pointer; transition: background .15s; user-select:none;
}
.ind-card:hover{ background: #fff8e8; border-color: var(--gold-light); }
.ind-card .sexdot{ width:11px; height:11px; border-radius:50%; }
.ind-card .sexdot.M{ background: var(--male); }
.ind-card .sexdot.F{ background: var(--female); }
.ind-card .sexdot.U{ background: var(--ink-faint); }
.ind-card .iname{ font-size:14px; }
.ind-card .iname small{ display:block; color: var(--ink-faint); font-size:11.5px; font-weight:normal; }
.ind-card .idates{ font-size:12px; color: var(--ink-soft); text-align:right; white-space:nowrap; }
.ind-card .igen{ font-size:11px; color:#fff; background: var(--slate); border-radius:10px; padding:2px 8px; }

/* ---------- modal fiche ---------- */
.modal-overlay{
  position:fixed; inset:0; background: rgba(30,20,10,0.55); z-index:200;
  display:none; align-items:flex-start; justify-content:center; padding: 40px 16px; overflow-y:auto;
}
.modal-overlay.open{ display:flex; }
.fiche{
  background: var(--card-bg); border:2px solid var(--line); border-radius:6px;
  max-width: 640px; width:100%; padding: 26px 28px 24px; position:relative;
  box-shadow: 0 12px 40px rgba(0,0,0,0.35);
}
.fiche .close-btn{
  position:absolute; top:12px; right:14px; background:none; border:none; font-size:20px; cursor:pointer; color: var(--ink-faint);
}
.fiche h2{ font-family: var(--font-display); color: var(--maroon-dark); margin:0 0 2px; font-size:22px; }
.fiche .fiche-sub{ color: var(--ink-faint); font-size:12.5px; margin-bottom:14px; }
.fiche dl.fiche-facts{ display:grid; grid-template-columns: 110px 1fr; gap:6px 10px; font-size:13.5px; margin: 0 0 16px; }
.fiche dl.fiche-facts dt{ color: var(--ink-soft); }
.fiche dl.fiche-facts dd{ margin:0; }
.fiche .rel-block{ margin-top:12px; }
.fiche .rel-block h4{ font-size:12px; text-transform:uppercase; letter-spacing:0.06em; color: var(--gold); margin:0 0 6px; }
.fiche .rel-people{ display:flex; flex-wrap:wrap; gap:6px; }
.fiche .rel-people span{
  background: var(--paper-darker); border:1px solid var(--line); border-radius:14px; padding:4px 10px; font-size:12.5px; cursor:pointer; user-select:none;
}
.fiche .rel-people span:hover{ background:#fff8e8; }

/* ---------- misc ---------- */
.two-col{ display:grid; grid-template-columns: 1.3fr 1fr; gap:16px; }
@media (max-width:900px){ .two-col{ grid-template-columns:1fr; } }
.note-box{
  background: rgba(168,121,31,0.08); border:1px solid var(--gold-light); border-radius:3px;
  padding:10px 14px; font-size:12.5px; color: var(--ink-soft); margin-bottom:16px;
}
/* ---------------------------------------------------------------- */
/* Arbre généalogique (pedigree)                                      */
/* ---------------------------------------------------------------- */
.tree-controls{ display:flex; gap:12px; flex-wrap:wrap; align-items:center; }
.tree-controls select{
  padding:8px 10px; font-family: var(--font-serif); font-size:13px; border:1px solid var(--line); border-radius:3px; background:#fffdf7;
}
.tree-controls .zoom-row{ display:flex; align-items:center; gap:8px; margin-left:auto; }
.tree-scroll{
  overflow:auto; border:1px solid var(--line-soft); border-radius:3px; background:
    repeating-linear-gradient(0deg, rgba(160,130,80,0.03) 0px, rgba(160,130,80,0.03) 1px, transparent 1px, transparent 3px), var(--paper);
  max-height:72vh; margin-top:14px;
}
.tree-canvas{ position:relative; transform-origin: top left; }
.tree-links{ position:absolute; top:0; left:0; pointer-events:none; }
.tree-links line{ stroke: var(--line); stroke-width:1.6; }
.tree-node{
  position:absolute; width:190px; min-height:52px; background:#fffdf7; border:1px solid var(--line);
  border-left:4px solid var(--ink-faint); border-radius:3px; padding:6px 10px; cursor:pointer; user-select:none;
  box-shadow:0 1px 3px rgba(58,44,28,0.15); font-size:12.5px; display:flex; flex-direction:column; justify-content:center;
  transition: background .15s;
}
.tree-node:hover{ background:#fff8e8; border-color: var(--gold-light); }
.tree-node.sex-M{ border-left-color: var(--male); }
.tree-node.sex-F{ border-left-color: var(--female); }
.tree-node.is-root{ border-width:2px; border-color: var(--gold); box-shadow:0 2px 10px rgba(168,121,31,0.35); }
.tree-node .tn-name{ font-weight:bold; color: var(--maroon-dark); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.tree-node .tn-dates{ color: var(--ink-soft); font-size:11px; margin-top:2px; }
.tree-node.empty{
  border-style:dashed; border-left-style:dashed; opacity:0.45; cursor:default; align-items:center; justify-content:center;
  color: var(--ink-faint); font-style:italic;
}
.tree-node.empty:hover{ background:#fffdf7; }
.tree-side{ margin-top:16px; }
.tree-side h4{ font-size:12px; text-transform:uppercase; letter-spacing:0.06em; color: var(--gold); margin:0 0 6px; }

/* ---------------------------------------------------------------- */
/* Formulaires d'édition                                              */
/* ---------------------------------------------------------------- */
.edit-form{ display:grid; grid-template-columns: repeat(4, 1fr); gap:12px 14px; min-width:0; }
.edit-form .field{ display:flex; flex-direction:column; gap:4px; min-width:0; }
.edit-form .field.span-2{ grid-column: span 2; }
.edit-form .field.span-4{ grid-column: span 4; }
.edit-form label{ font-size:11.5px; color: var(--ink-soft); text-transform:uppercase; letter-spacing:0.04em; }
.edit-form input[type=text], .edit-form input[type=number], .edit-form select, .edit-form textarea{
  padding:8px 10px; font-family: var(--font-serif); font-size:13.5px; min-width:0; max-width:100%;
  border:1px solid var(--line); border-radius:3px; background:#fffdf7; color: var(--ink);
}
.edit-form .checkbox-row{ display:flex; align-items:center; gap:8px; grid-column: span 4; }
.edit-form fieldset{ grid-column: span 4; border:1px solid var(--line-soft); border-radius:3px; padding:12px 14px 14px; margin:4px 0; min-width:0; }
.edit-form fieldset legend{ font-size:12px; color: var(--maroon-dark); padding:0 6px; font-weight:bold; }
.edit-form .date-fields{ display:grid; grid-template-columns: 1.3fr 0.7fr 1fr 0.9fr; gap:8px; min-width:0; }
.edit-form .action-row{ grid-column: span 4; }
.edit-form .death-fields{ display:grid; grid-template-columns: repeat(4,1fr); gap:12px 14px; grid-column: span 4; margin-top:10px; min-width:0; }
@media (max-width: 900px){
  .edit-form{ grid-template-columns: repeat(2, 1fr); }
  .edit-form .field.span-2, .edit-form .field.span-4, .edit-form fieldset, .edit-form .checkbox-row,
  .edit-form .action-row, .edit-form .death-fields{ grid-column: span 2; }
  .edit-form .date-fields{ grid-template-columns: repeat(2, 1fr); }
  .edit-form .death-fields{ grid-template-columns: repeat(2, 1fr); }
}
.btn{
  font-family: var(--font-serif); font-size:13px; padding:9px 18px; border-radius:3px; cursor:pointer;
  border:1px solid var(--maroon); background: var(--maroon); color:#fdf6e6; letter-spacing:0.02em;
  transition: background .15s;
}
.btn:hover{ background: var(--maroon-dark); }
.btn.secondary{ background: var(--card-bg); color: var(--maroon-dark); border-color: var(--line); }
.btn.secondary:hover{ background: var(--paper-darker); }
.btn.danger{ background: #fff; color: #b23333; border-color: #d99999; }
.btn.danger:hover{ background: #f8e6e6; }
.btn.small{ padding:4px 11px; font-size:11.5px; }
.action-row{ display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }
.fiche .fiche-actions{ display:flex; gap:8px; margin-top:16px; padding-top:14px; border-top:1px solid var(--line-soft); }
.upload-row{ display:flex; align-items:center; gap:14px; flex-wrap:wrap; }
.upload-row input[type=file]{ font-family: var(--font-serif); font-size:13px; }
.flash-msg{
  background:#e1ead9; border:1px solid #a9c79c; color:#2f4a30; border-radius:3px; padding:9px 14px;
  font-size:13px; margin-top:12px; display:none;
}
.flash-msg.show{ display:block; }
.fam-row-actions{ display:flex; gap:6px; margin-top:4px; }

footer.pagefoot{
  text-align:center; color: var(--ink-faint); font-size:11.5px; margin-top:50px; padding-top:18px;
  border-top:1px solid var(--line-soft);
}
.flourish{ text-align:center; color: var(--gold); letter-spacing:0.3em; font-size:12px; margin: 30px 0 6px; }
</style>
</head>
<body>

<header class="masthead">
  <div class="eyebrow">Registre Généalogique &middot; Analyse Archivistique</div>
  <h1 id="pageTitle">__ROOT_NAME__</h1>
  <div class="subtitle" id="pageSubtitle">__SUBTITLE__</div>
  <div class="meta-chips" id="metaChips"></div>
</header>

<div class="wrap">
<nav class="tabs" id="tabsNav">
  <button data-tab="demographie" class="active">Démographie</button>
  <button data-tab="chronologie">Chronologie</button>
  <button data-tab="geographie">Géographie</button>
  <button data-tab="familles">Familles</button>
  <button data-tab="patronymes">Patronymes</button>
  <button data-tab="qualite">Qualité des données</button>
  <button data-tab="individus">Fiches individuelles</button>
  <button data-tab="arbre">Arbre</button>
  <button data-tab="edition">Édition</button>
</nav>

<main>
  <section class="panel active" id="panel-demographie"></section>
  <section class="panel" id="panel-chronologie"></section>
  <section class="panel" id="panel-geographie"></section>
  <section class="panel" id="panel-familles"></section>
  <section class="panel" id="panel-patronymes"></section>
  <section class="panel" id="panel-qualite"></section>
  <section class="panel" id="panel-individus"></section>
  <section class="panel" id="panel-arbre"></section>
  <section class="panel" id="panel-edition"></section>
</main>

<div class="flourish">&#10086; &#10086; &#10086;</div>
<footer class="pagefoot">
  Document généré automatiquement à partir d'un fichier GEDCOM &mdash; __GENERATED_AT__<br>
  __SOURCE_LABEL__
</footer>
</div>

<div class="modal-overlay" id="modalOverlay">
  <div class="fiche" id="ficheContent"></div>
</div>

<script>
const RAW_GEDCOM_JSON = __RAW_GEDCOM_JSON__;
</script>
<script src="app.js"></script>
</body>
</html>
