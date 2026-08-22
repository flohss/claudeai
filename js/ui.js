export function createUI() {
  const scoreEl = document.getElementById("stat-score");
  const weekEl = document.getElementById("stat-week");
  const linesEl = document.getElementById("stat-lines");
  const trainsEl = document.getElementById("stat-trains");
  const toastsEl = document.getElementById("toasts");
  const linePanel = document.getElementById("line-panel");
  const gameoverOverlay = document.getElementById("gameover-overlay");
  const gameoverStats = document.getElementById("gameover-stats");

  return {
    update(game) {
      scoreEl.textContent = String(game.score);
      weekEl.textContent = String(1 + Math.floor(game.elapsed / 60));
      linesEl.textContent = `${game.lines.length}/${game.linesMax}`;
      trainsEl.textContent = String(game.trainPool);

      linePanel.innerHTML = "";
      for (const line of game.lines) {
        const chip = document.createElement("div");
        chip.className = "line-chip";

        const swatch = document.createElement("div");
        swatch.className = "swatch";
        swatch.style.background = line.color;
        chip.appendChild(swatch);

        const info = document.createElement("div");
        info.className = "info";
        const trainCount = line.trains.length;
        const stationCount = line.stations.length;
        info.textContent = `${stationCount} stops · ${trainCount} train${trainCount === 1 ? "" : "s"}`;
        chip.appendChild(info);

        const addBtn = document.createElement("button");
        addBtn.textContent = "+";
        addBtn.title = "Add train";
        addBtn.disabled = game.trainPool <= 0;
        addBtn.addEventListener("click", () => game.addTrainToLine(line.id));
        chip.appendChild(addBtn);

        const delBtn = document.createElement("button");
        delBtn.textContent = "×";
        delBtn.className = "danger";
        delBtn.title = "Remove line";
        delBtn.addEventListener("click", () => game.deleteLine(line.id));
        chip.appendChild(delBtn);

        linePanel.appendChild(chip);
      }
    },

    toast(text) {
      const el = document.createElement("div");
      el.className = "toast";
      el.textContent = text;
      toastsEl.appendChild(el);
      setTimeout(() => el.remove(), 2700);
    },

    gameOver(score, elapsedSeconds) {
      const minutes = Math.floor(elapsedSeconds / 60);
      const seconds = Math.floor(elapsedSeconds % 60);
      gameoverStats.textContent = `You delivered ${score} passengers and kept the network running for ${minutes}m ${seconds}s.`;
      gameoverOverlay.classList.remove("hidden");
    },

    hideGameOver() {
      gameoverOverlay.classList.add("hidden");
    },
  };
}
