// ---------- Mots mêlés ----------
const WS_THEMES = {
  "Animaux": ["LION", "TIGRE", "GIRAFE", "ELEPHANT", "ZEBRE", "SINGE", "OURS", "RENARD", "LOUP", "PANDA", "KOALA", "SOURIS"],
  "Fruits": ["POMME", "BANANE", "ORANGE", "CITRON", "FRAISE", "ANANAS", "MANGUE", "CERISE", "RAISIN", "MELON", "PECHE", "KIWI"],
  "Métiers": ["MEDECIN", "PROFESSEUR", "POMPIER", "BOULANGER", "AVOCAT", "INGENIEUR", "INFIRMIER", "POLICIER", "CUISINIER", "MENUISIER"],
  "Pays": ["FRANCE", "ESPAGNE", "ITALIE", "ALLEMAGNE", "BELGIQUE", "SUISSE", "CANADA", "MAROC", "JAPON", "BRESIL"],
  "Sports": ["FOOTBALL", "TENNIS", "NATATION", "RUGBY", "BASKET", "JUDO", "CYCLISME", "ESCRIME", "GOLF", "BOXE"]
};

const WS_DIRECTIONS = [
  { dr: 0, dc: 1 }, { dr: 0, dc: -1 },
  { dr: 1, dc: 0 }, { dr: -1, dc: 0 },
  { dr: 1, dc: 1 }, { dr: -1, dc: -1 },
  { dr: 1, dc: -1 }, { dr: -1, dc: 1 }
];

function wsStripAccents(str) {
  return str.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

const WordSearch = {
  size: 12,
  grid: [],
  placements: [], // {word, cells:[[r,c],...]}
  found: new Set(),
  timerInterval: null,
  startTime: null,
  selecting: false,
  selStart: null,
  selCells: [],

  init() {
    const themeSel = document.getElementById("ws-theme");
    Object.keys(WS_THEMES).forEach(t => {
      const opt = document.createElement("option");
      opt.value = t; opt.textContent = t;
      themeSel.appendChild(opt);
    });

    document.getElementById("ws-new").addEventListener("click", () => this.newGame());
    this.newGame();
  },

  newGame() {
    this.size = parseInt(document.getElementById("ws-size").value, 10);
    const theme = document.getElementById("ws-theme").value || Object.keys(WS_THEMES)[0];
    const words = [...WS_THEMES[theme]].sort((a, b) => b.length - a.length);

    this.placements = [];
    this.grid = Array.from({ length: this.size }, () => Array(this.size).fill(null));

    words.forEach(word => this.placeWord(wsStripAccents(word), word));

    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        if (!this.grid[r][c]) {
          this.grid[r][c] = letters[Math.floor(Math.random() * letters.length)];
        }
      }
    }

    this.found = new Set();
    this.renderGrid();
    this.renderWordList();
    this.startTimer();
    document.getElementById("ws-status").textContent = "";
  },

  placeWord(plain, display) {
    const attempts = 300;
    for (let i = 0; i < attempts; i++) {
      const dir = WS_DIRECTIONS[Math.floor(Math.random() * WS_DIRECTIONS.length)];
      const len = plain.length;
      const r = Math.floor(Math.random() * this.size);
      const c = Math.floor(Math.random() * this.size);

      const cells = [];
      let ok = true;
      for (let k = 0; k < len; k++) {
        const rr = r + dir.dr * k;
        const cc = c + dir.dc * k;
        if (rr < 0 || rr >= this.size || cc < 0 || cc >= this.size) { ok = false; break; }
        const existing = this.grid[rr][cc];
        if (existing && existing !== plain[k]) { ok = false; break; }
        cells.push([rr, cc]);
      }
      if (!ok) continue;
      cells.forEach(([rr, cc], k) => { this.grid[rr][cc] = plain[k]; });
      this.placements.push({ word: plain, display, cells });
      return true;
    }
    return false;
  },

  renderGrid() {
    const el = document.getElementById("ws-grid");
    el.innerHTML = "";
    el.style.gridTemplateColumns = `repeat(${this.size}, 1fr)`;
    for (let r = 0; r < this.size; r++) {
      for (let c = 0; c < this.size; c++) {
        const div = document.createElement("div");
        div.className = "cell";
        div.textContent = this.grid[r][c];
        div.dataset.r = r;
        div.dataset.c = c;
        el.appendChild(div);
      }
    }
    el.addEventListener("mousedown", e => this.onStart(e));
    el.addEventListener("mousemove", e => this.onMove(e));
    window.addEventListener("mouseup", () => this.onEnd());
    el.addEventListener("touchstart", e => this.onStart(e, true), { passive: false });
    el.addEventListener("touchmove", e => this.onMove(e, true), { passive: false });
    el.addEventListener("touchend", () => this.onEnd());
  },

  cellFromEvent(e, touch) {
    let target;
    if (touch) {
      const t = e.touches[0];
      target = document.elementFromPoint(t.clientX, t.clientY);
    } else {
      target = e.target;
    }
    if (!target || !target.classList.contains("cell")) return null;
    return { r: parseInt(target.dataset.r, 10), c: parseInt(target.dataset.c, 10) };
  },

  onStart(e, touch) {
    const cell = this.cellFromEvent(e, touch);
    if (!cell) return;
    if (touch) e.preventDefault();
    this.selecting = true;
    this.selStart = cell;
    this.updateSelection(cell);
  },

  onMove(e, touch) {
    if (!this.selecting) return;
    const cell = this.cellFromEvent(e, touch);
    if (!cell) return;
    if (touch) e.preventDefault();
    this.updateSelection(cell);
  },

  onEnd() {
    if (!this.selecting) return;
    this.selecting = false;
    this.commitSelection();
  },

  updateSelection(endCell) {
    this.clearSelectingClass();
    const start = this.selStart;
    const dr = Math.sign(endCell.r - start.r);
    const dc = Math.sign(endCell.c - start.c);
    const len = Math.max(Math.abs(endCell.r - start.r), Math.abs(endCell.c - start.c)) + 1;
    const cells = [];
    if (dr === 0 || dc === 0 || Math.abs(endCell.r - start.r) === Math.abs(endCell.c - start.c)) {
      for (let k = 0; k < len; k++) {
        cells.push([start.r + dr * k, start.c + dc * k]);
      }
    } else {
      cells.push([start.r, start.c]);
    }
    this.selCells = cells;
    cells.forEach(([r, c]) => {
      const el = this.cellEl(r, c);
      if (el) el.classList.add("selecting");
    });
  },

  clearSelectingClass() {
    document.querySelectorAll("#ws-grid .cell.selecting").forEach(el => el.classList.remove("selecting"));
  },

  cellEl(r, c) {
    return document.querySelector(`#ws-grid .cell[data-r="${r}"][data-c="${c}"]`);
  },

  commitSelection() {
    this.clearSelectingClass();
    if (this.selCells.length < 2) { this.selCells = []; return; }
    const str = this.selCells.map(([r, c]) => this.grid[r][c]).join("");
    const strRev = str.split("").reverse().join("");

    const match = this.placements.find(p =>
      !this.found.has(p.word) && (p.word === str || p.word === strRev)
    );
    if (match) {
      this.found.add(match.word);
      match.cells.forEach(([r, c]) => {
        const el = this.cellEl(r, c);
        if (el) el.classList.add("found");
      });
      this.renderWordList();
      if (this.found.size === this.placements.length) {
        this.stopTimer();
        document.getElementById("ws-status").textContent = "🎉 Bravo, tous les mots sont trouvés !";
      }
    }
    this.selCells = [];
  },

  renderWordList() {
    const ul = document.getElementById("ws-wordlist");
    ul.innerHTML = "";
    this.placements.forEach(p => {
      const li = document.createElement("li");
      li.textContent = p.display;
      if (this.found.has(p.word)) li.classList.add("done");
      ul.appendChild(li);
    });
  },

  startTimer() {
    this.stopTimer();
    this.startTime = Date.now();
    this.timerInterval = setInterval(() => {
      const s = Math.floor((Date.now() - this.startTime) / 1000);
      const mm = String(Math.floor(s / 60)).padStart(2, "0");
      const ss = String(s % 60).padStart(2, "0");
      document.getElementById("ws-timer").textContent = `${mm}:${ss}`;
    }, 1000);
  },

  stopTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    this.timerInterval = null;
  }
};
