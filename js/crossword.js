// ---------- Moteur mots fléchés ----------
const Crossword = {
  current: null,

  init() {
    const sel = document.getElementById("cw-puzzle");
    CROSSWORD_PUZZLES.forEach((p, i) => {
      const opt = document.createElement("option");
      opt.value = i; opt.textContent = p.name;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => this.load(parseInt(sel.value, 10)));
    document.getElementById("cw-check").addEventListener("click", () => this.check());
    document.getElementById("cw-solve").addEventListener("click", () => this.solve());
    document.getElementById("cw-reset").addEventListener("click", () => this.load(parseInt(sel.value, 10)));
    this.load(0);
  },

  load(index) {
    this.current = CROSSWORD_PUZZLES[index];
    this.render();
    document.getElementById("cw-status").textContent = "";
  },

  render() {
    const grid = this.current.grid;
    const rows = grid.length;
    const cols = grid[0].length;
    const el = document.getElementById("cw-grid");
    el.innerHTML = "";
    el.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
    el.style.gridTemplateRows = `repeat(${rows}, 1fr)`;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cellData = grid[r][c];
        const div = document.createElement("div");
        div.className = "cw-cell";

        if (cellData.type === "block") {
          div.classList.add("block");
        } else if (cellData.type === "clue") {
          div.classList.add("clue");
          const span = document.createElement("span");
          span.className = "txt";
          span.textContent = cellData.text;
          div.appendChild(span);
          const arrow = document.createElement("span");
          arrow.className = `arrow ${cellData.dir}`;
          arrow.textContent = cellData.dir === "right" ? "➜" : "⬇";
          div.appendChild(arrow);
        } else if (cellData.type === "input") {
          div.classList.add("input");
          const input = document.createElement("input");
          input.maxLength = 1;
          input.dataset.r = r;
          input.dataset.c = c;
          input.addEventListener("input", e => this.onInput(e, r, c));
          input.addEventListener("keydown", e => this.onKeyDown(e, r, c));
          div.appendChild(input);
        }
        el.appendChild(div);
      }
    }
  },

  inputEl(r, c) {
    return document.querySelector(`#cw-grid input[data-r="${r}"][data-c="${c}"]`);
  },

  onInput(e, r, c) {
    const val = e.target.value.toUpperCase().replace(/[^A-ZÀ-Ÿ]/g, "");
    e.target.value = val.slice(-1);
    const cell = e.target.closest(".cw-cell");
    cell.classList.remove("correct", "wrong");
    if (e.target.value) this.focusNext(r, c);
  },

  onKeyDown(e, r, c) {
    const grid = this.current.grid;
    const rows = grid.length, cols = grid[0].length;
    const move = (rr, cc) => {
      if (rr >= 0 && rr < rows && cc >= 0 && cc < cols) {
        const target = this.inputEl(rr, cc);
        if (target) { target.focus(); e.preventDefault(); }
      }
    };
    if (e.key === "ArrowRight") move(r, c + 1);
    else if (e.key === "ArrowLeft") move(r, c - 1);
    else if (e.key === "ArrowDown") move(r + 1, c);
    else if (e.key === "ArrowUp") move(r - 1, c);
    else if (e.key === "Backspace" && !e.target.value) move(r, c - 1);
  },

  focusNext(r, c) {
    const grid = this.current.grid;
    if (c + 1 < grid[r].length && grid[r][c + 1].type === "input") {
      this.inputEl(r, c + 1).focus();
    } else if (r + 1 < grid.length && grid[r + 1][c] && grid[r + 1][c].type === "input") {
      this.inputEl(r + 1, c).focus();
    }
  },

  check() {
    const grid = this.current.grid;
    let allFilled = true;
    let allCorrect = true;
    for (let r = 0; r < grid.length; r++) {
      for (let c = 0; c < grid[r].length; c++) {
        const cellData = grid[r][c];
        if (cellData.type !== "input") continue;
        const input = this.inputEl(r, c);
        const div = input.closest(".cw-cell");
        div.classList.remove("correct", "wrong");
        if (!input.value) { allFilled = false; continue; }
        if (input.value === cellData.solution) {
          div.classList.add("correct");
        } else {
          div.classList.add("wrong");
          allCorrect = false;
        }
      }
    }
    const status = document.getElementById("cw-status");
    if (!allFilled) status.textContent = "Grille incomplète.";
    else if (allCorrect) status.textContent = "🎉 Bravo, la grille est complète et correcte !";
    else status.textContent = "Il y a des erreurs, continuez à chercher.";
  },

  solve() {
    const grid = this.current.grid;
    for (let r = 0; r < grid.length; r++) {
      for (let c = 0; c < grid[r].length; c++) {
        const cellData = grid[r][c];
        if (cellData.type !== "input") continue;
        const input = this.inputEl(r, c);
        input.value = cellData.solution;
        input.closest(".cw-cell").classList.remove("wrong");
        input.closest(".cw-cell").classList.add("correct");
      }
    }
    document.getElementById("cw-status").textContent = "Solution affichée.";
  }
};
