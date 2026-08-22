// ---------- Sudoku ----------
const Sudoku = {
  solution: [],
  board: [],
  given: [],
  notes: [],
  selected: null,
  notesMode: false,
  mistakes: 0,
  timerInterval: null,
  startTime: null,

  init() {
    document.getElementById("su-new").addEventListener("click", () => this.newGame());
    document.getElementById("su-notes").addEventListener("click", () => this.toggleNotes());
    document.getElementById("su-check").addEventListener("click", () => this.checkBoard());
    document.getElementById("su-solve").addEventListener("click", () => this.revealSolution());
    document.addEventListener("keydown", e => this.onKeyDown(e));
    this.buildNumpad();
    this.newGame();
  },

  buildNumpad() {
    const pad = document.getElementById("su-numpad");
    pad.innerHTML = "";
    for (let n = 1; n <= 9; n++) {
      const btn = document.createElement("button");
      btn.textContent = n;
      btn.addEventListener("click", () => this.enterValue(n));
      pad.appendChild(btn);
    }
    const erase = document.createElement("button");
    erase.textContent = "⌫";
    erase.addEventListener("click", () => this.enterValue(0));
    pad.appendChild(erase);
  },

  newGame() {
    const difficulty = document.getElementById("su-difficulty").value;
    this.solution = this.generateSolved();
    this.board = this.solution.map(row => [...row]);
    this.notes = Array.from({ length: 9 }, () => Array.from({ length: 9 }, () => new Set()));

    const removeCount = { facile: 36, moyen: 46, difficile: 52 }[difficulty] || 46;
    this.dig(this.board, removeCount);

    this.given = this.board.map(row => row.map(v => v !== 0));
    this.mistakes = 0;
    document.getElementById("su-mistakes").textContent = "0";
    this.selected = null;
    this.render();
    this.startTimer();
    document.getElementById("su-status").textContent = "";
  },

  // ---- Génération d'une grille pleine valide ----
  generateSolved() {
    const board = Array.from({ length: 9 }, () => Array(9).fill(0));
    this.fillCell(board, 0);
    return board;
  },

  fillCell(board, pos) {
    if (pos === 81) return true;
    const r = Math.floor(pos / 9), c = pos % 9;
    const nums = [1, 2, 3, 4, 5, 6, 7, 8, 9];
    for (let i = nums.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [nums[i], nums[j]] = [nums[j], nums[i]];
    }
    for (const n of nums) {
      if (this.isValid(board, r, c, n)) {
        board[r][c] = n;
        if (this.fillCell(board, pos + 1)) return true;
        board[r][c] = 0;
      }
    }
    return false;
  },

  isValid(board, r, c, n) {
    for (let i = 0; i < 9; i++) {
      if (board[r][i] === n || board[i][c] === n) return false;
    }
    const br = Math.floor(r / 3) * 3, bc = Math.floor(c / 3) * 3;
    for (let i = 0; i < 3; i++) {
      for (let j = 0; j < 3; j++) {
        if (board[br + i][bc + j] === n) return false;
      }
    }
    return true;
  },

  countSolutions(board, limit) {
    let count = 0;
    const solve = () => {
      if (count >= limit) return;
      let best = null;
      for (let r = 0; r < 9; r++) {
        for (let c = 0; c < 9; c++) {
          if (board[r][c] === 0) {
            const cands = [];
            for (let n = 1; n <= 9; n++) if (this.isValid(board, r, c, n)) cands.push(n);
            if (!best || cands.length < best.cands.length) best = { r, c, cands };
            if (best.cands.length === 0) return;
          }
        }
      }
      if (!best) { count++; return; }
      for (const n of best.cands) {
        board[best.r][best.c] = n;
        solve();
        board[best.r][best.c] = 0;
        if (count >= limit) return;
      }
    };
    solve();
    return count;
  },

  dig(board, removeCount) {
    const cells = [];
    for (let r = 0; r < 9; r++) for (let c = 0; c < 9; c++) cells.push([r, c]);
    for (let i = cells.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [cells[i], cells[j]] = [cells[j], cells[i]];
    }
    let removed = 0;
    for (const [r, c] of cells) {
      if (removed >= removeCount) break;
      const backup = board[r][c];
      board[r][c] = 0;
      const copy = board.map(row => [...row]);
      const solutions = this.countSolutions(copy, 2);
      if (solutions === 1) {
        removed++;
      } else {
        board[r][c] = backup;
      }
    }
  },

  // ---- Rendu ----
  render() {
    const grid = document.getElementById("su-grid");
    grid.innerHTML = "";
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        const div = document.createElement("div");
        div.className = "su-cell";
        if (r % 3 === 2 && r !== 8) div.classList.add("su-row-thick");
        div.dataset.r = r;
        div.dataset.c = c;
        this.renderCell(div, r, c);
        div.addEventListener("click", () => this.selectCell(r, c));
        grid.appendChild(div);
      }
    }
  },

  renderCell(div, r, c) {
    div.innerHTML = "";
    div.classList.remove("wrong");
    const val = this.board[r][c];
    if (this.given[r][c]) {
      div.classList.add("given");
      div.textContent = val;
    } else if (val !== 0) {
      div.classList.remove("given");
      div.textContent = val;
    } else if (this.notes[r][c].size > 0) {
      const notesEl = document.createElement("div");
      notesEl.className = "notes";
      for (let n = 1; n <= 9; n++) {
        const span = document.createElement("span");
        span.textContent = this.notes[r][c].has(n) ? n : "";
        notesEl.appendChild(span);
      }
      div.appendChild(notesEl);
    } else {
      div.textContent = "";
    }
  },

  cellDiv(r, c) {
    return document.querySelector(`#su-grid .su-cell[data-r="${r}"][data-c="${c}"]`);
  },

  selectCell(r, c) {
    document.querySelectorAll("#su-grid .su-cell").forEach(el => {
      el.classList.remove("selected", "same-value");
    });
    this.selected = { r, c };
    this.cellDiv(r, c).classList.add("selected");
    const val = this.board[r][c];
    if (val !== 0) {
      for (let rr = 0; rr < 9; rr++) {
        for (let cc = 0; cc < 9; cc++) {
          if ((rr !== r || cc !== c) && this.board[rr][cc] === val) {
            this.cellDiv(rr, cc).classList.add("same-value");
          }
        }
      }
    }
  },

  onKeyDown(e) {
    if (!this.selected) return;
    if (!document.getElementById("sudoku").classList.contains("active")) return;
    const { r, c } = this.selected;
    if (e.key >= "1" && e.key <= "9") {
      this.enterValue(parseInt(e.key, 10));
    } else if (e.key === "Backspace" || e.key === "Delete" || e.key === "0") {
      this.enterValue(0);
    } else if (e.key === "ArrowRight") this.moveSelection(r, Math.min(8, c + 1));
    else if (e.key === "ArrowLeft") this.moveSelection(r, Math.max(0, c - 1));
    else if (e.key === "ArrowDown") this.moveSelection(Math.min(8, r + 1), c);
    else if (e.key === "ArrowUp") this.moveSelection(Math.max(0, r - 1), c);
  },

  moveSelection(r, c) {
    this.selectCell(r, c);
  },

  toggleNotes() {
    this.notesMode = !this.notesMode;
    document.getElementById("su-notes").textContent = `Notes : ${this.notesMode ? "On" : "Off"}`;
  },

  enterValue(n) {
    if (!this.selected) return;
    const { r, c } = this.selected;
    if (this.given[r][c]) return;

    if (this.notesMode) {
      if (n === 0) {
        this.notes[r][c].clear();
      } else if (this.notes[r][c].has(n)) {
        this.notes[r][c].delete(n);
      } else {
        this.notes[r][c].add(n);
      }
      this.board[r][c] = 0;
    } else {
      this.board[r][c] = n;
      this.notes[r][c].clear();
      if (n !== 0 && n !== this.solution[r][c]) {
        this.mistakes++;
        document.getElementById("su-mistakes").textContent = this.mistakes;
      }
    }
    this.renderCell(this.cellDiv(r, c), r, c);
    this.selectCell(r, c);
    this.checkWin();
  },

  checkWin() {
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        if (this.board[r][c] !== this.solution[r][c]) return;
      }
    }
    this.stopTimer();
    document.getElementById("su-status").textContent = "🎉 Bravo, la grille est résolue !";
  },

  checkBoard() {
    let hasError = false;
    let complete = true;
    for (let r = 0; r < 9; r++) {
      for (let c = 0; c < 9; c++) {
        const div = this.cellDiv(r, c);
        div.classList.remove("wrong");
        if (this.board[r][c] === 0) { complete = false; continue; }
        if (this.board[r][c] !== this.solution[r][c]) {
          div.classList.add("wrong");
          hasError = true;
        }
      }
    }
    const status = document.getElementById("su-status");
    if (hasError) status.textContent = "Des erreurs sont surlignées en rouge.";
    else if (!complete) status.textContent = "Pas d'erreur pour l'instant, continuez !";
    else status.textContent = "🎉 Bravo, la grille est correcte !";
  },

  revealSolution() {
    this.board = this.solution.map(row => [...row]);
    this.notes = Array.from({ length: 9 }, () => Array.from({ length: 9 }, () => new Set()));
    this.render();
    this.stopTimer();
    document.getElementById("su-status").textContent = "Solution affichée.";
  },

  startTimer() {
    this.stopTimer();
    this.startTime = Date.now();
    this.timerInterval = setInterval(() => {
      const s = Math.floor((Date.now() - this.startTime) / 1000);
      const mm = String(Math.floor(s / 60)).padStart(2, "0");
      const ss = String(s % 60).padStart(2, "0");
      document.getElementById("su-timer").textContent = `${mm}:${ss}`;
    }, 1000);
  },

  stopTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    this.timerInterval = null;
  }
};
