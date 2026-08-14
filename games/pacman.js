(function () {
  window.ARCADE_GAMES = window.ARCADE_GAMES || [];

  window.ARCADE_GAMES.push({
    id: "pacman",
    name: "Pac-Man",
    icon: "🟡",
    accent: "#fbbf24",
    description: "Dévore tous les points, évite les fantômes, 1980.",
    hint: "Flèches pour te déplacer dans le labyrinthe. Les pastilles rendent les fantômes vulnérables.",

    start(canvas, setScore) {
      const ctx = canvas.getContext("2d");
      const W = canvas.width;
      const H = canvas.height;

      const CELLS_X = 9;
      const CELLS_Y = 7;
      const CELL = 24;
      const COLS = CELLS_X * 2 + 1;
      const ROWS = CELLS_Y * 2 + 1;
      const OFFSET_X = (W - COLS * CELL) / 2;
      const OFFSET_Y = (H - ROWS * CELL) / 2;
      const STEP_MS = 150;
      const GHOST_STEP_MS = 175;
      const FRIGHT_MS = 6500;

      function generateMaze() {
        const grid = Array.from({ length: ROWS }, () => Array(COLS).fill(true));
        const visited = Array.from({ length: CELLS_Y }, () => Array(CELLS_X).fill(false));
        let cx = 0, cy = 0;
        visited[cy][cx] = true;
        grid[2 * cy + 1][2 * cx + 1] = false;
        const stack = [[cx, cy]];
        while (stack.length) {
          [cx, cy] = stack[stack.length - 1];
          const neighbors = [];
          if (cx > 0 && !visited[cy][cx - 1]) neighbors.push([cx - 1, cy, "L"]);
          if (cx < CELLS_X - 1 && !visited[cy][cx + 1]) neighbors.push([cx + 1, cy, "R"]);
          if (cy > 0 && !visited[cy - 1][cx]) neighbors.push([cx, cy - 1, "U"]);
          if (cy < CELLS_Y - 1 && !visited[cy + 1][cx]) neighbors.push([cx, cy + 1, "D"]);
          if (!neighbors.length) {
            stack.pop();
            continue;
          }
          const [nx, ny, dir] = neighbors[Math.floor(Math.random() * neighbors.length)];
          const gy = 2 * cy + 1, gx = 2 * cx + 1;
          if (dir === "L") grid[gy][gx - 1] = false;
          if (dir === "R") grid[gy][gx + 1] = false;
          if (dir === "U") grid[gy - 1][gx] = false;
          if (dir === "D") grid[gy + 1][gx] = false;
          grid[2 * ny + 1][2 * nx + 1] = false;
          visited[ny][nx] = true;
          stack.push([nx, ny]);
        }
        for (let gy = 1; gy < ROWS - 1; gy++) {
          for (let gx = 1; gx < COLS - 1; gx++) {
            if (!grid[gy][gx]) continue;
            if (gy % 2 === 1 && gx % 2 === 0) {
              if (!grid[gy][gx - 1] && !grid[gy][gx + 1] && Math.random() < 0.12) grid[gy][gx] = false;
            } else if (gx % 2 === 1 && gy % 2 === 0) {
              if (!grid[gy - 1][gx] && !grid[gy + 1][gx] && Math.random() < 0.12) grid[gy][gx] = false;
            }
          }
        }
        return grid;
      }

      function bigCell(cx, cy) {
        return { x: 2 * cx + 1, y: 2 * cy + 1 };
      }

      function bfsFirstStep(start, target) {
        const key = (x, y) => y * COLS + x;
        const visited = new Set([key(start.x, start.y)]);
        const queue = [{ x: start.x, y: start.y, first: null }];
        const dirs = [
          { dx: 1, dy: 0 }, { dx: -1, dy: 0 }, { dx: 0, dy: 1 }, { dx: 0, dy: -1 },
        ];
        let qi = 0;
        while (qi < queue.length) {
          const cur = queue[qi++];
          if (cur.x === target.x && cur.y === target.y) return cur.first || { dx: 0, dy: 0 };
          for (const d of dirs) {
            const nx = cur.x + d.dx, ny = cur.y + d.dy;
            if (nx < 0 || ny < 0 || nx >= COLS || ny >= ROWS) continue;
            if (grid[ny][nx]) continue;
            const k = key(nx, ny);
            if (visited.has(k)) continue;
            visited.add(k);
            queue.push({ x: nx, y: ny, first: cur.first || d });
          }
        }
        return null;
      }

      let grid, dots, pellets, player, ghosts, score, lives, gameOver, won, invuln;
      let stepAcc, ghostStepAcc;

      const GHOST_COLORS = ["#ff2e88", "#34f5ff", "#c084fc"];

      function buildGhosts() {
        const center = bigCell(Math.floor(CELLS_X / 2), Math.floor(CELLS_Y / 2));
        const spots = [
          center,
          bigCell(Math.max(0, Math.floor(CELLS_X / 2) - 1), Math.floor(CELLS_Y / 2)),
          bigCell(Math.min(CELLS_X - 1, Math.floor(CELLS_X / 2) + 1), Math.floor(CELLS_Y / 2)),
        ];
        return spots.map((s, i) => ({
          x: s.x, y: s.y, spawn: s,
          dir: { dx: 0, dy: -1 },
          color: GHOST_COLORS[i],
          frightened: 0,
          mode: i === 0 ? "chase" : "wander",
        }));
      }

      function reset() {
        grid = generateMaze();
        dots = new Set();
        pellets = new Set();
        for (let y = 0; y < ROWS; y++) {
          for (let x = 0; x < COLS; x++) {
            if (!grid[y][x]) dots.add(`${x},${y}`);
          }
        }
        const corners = [
          bigCell(0, 0), bigCell(CELLS_X - 1, 0),
          bigCell(0, CELLS_Y - 1), bigCell(CELLS_X - 1, CELLS_Y - 1),
        ];
        corners.forEach((c) => {
          const k = `${c.x},${c.y}`;
          dots.delete(k);
          pellets.add(k);
        });

        const start = bigCell(Math.floor(CELLS_X / 2), CELLS_Y - 1);
        player = { x: start.x, y: start.y, dir: { dx: 0, dy: 0 }, queued: { dx: 0, dy: 0 } };
        dots.delete(`${start.x},${start.y}`);

        ghosts = buildGhosts();
        ghosts.forEach((g) => dots.delete(`${g.x},${g.y}`));

        score = 0;
        lives = 3;
        gameOver = false;
        won = false;
        invuln = 8;
        stepAcc = 0;
        ghostStepAcc = 0;
        updateScore();
      }

      function updateScore() {
        setScore(`SCORE ${score}  •  VIES ${lives}`);
      }

      reset();

      const dirMap = {
        ArrowUp: { dx: 0, dy: -1 }, w: { dx: 0, dy: -1 }, W: { dx: 0, dy: -1 },
        ArrowDown: { dx: 0, dy: 1 }, s: { dx: 0, dy: 1 }, S: { dx: 0, dy: 1 },
        ArrowLeft: { dx: -1, dy: 0 }, a: { dx: -1, dy: 0 }, A: { dx: -1, dy: 0 },
        ArrowRight: { dx: 1, dy: 0 }, d: { dx: 1, dy: 0 }, D: { dx: 1, dy: 0 },
      };

      function onKeyDown(e) {
        if (gameOver && e.key === " ") {
          reset();
          return;
        }
        const d = dirMap[e.key];
        if (d) player.queued = d;
      }
      window.addEventListener("keydown", onKeyDown);

      function canMove(x, y, d) {
        const nx = x + d.dx, ny = y + d.dy;
        if (nx < 0 || ny < 0 || nx >= COLS || ny >= ROWS) return false;
        return !grid[ny][nx];
      }

      function loseLife() {
        lives -= 1;
        updateScore();
        if (lives <= 0) {
          gameOver = true;
          return;
        }
        const start = bigCell(Math.floor(CELLS_X / 2), CELLS_Y - 1);
        player.x = start.x;
        player.y = start.y;
        player.dir = { dx: 0, dy: 0 };
        player.queued = { dx: 0, dy: 0 };
        ghosts.forEach((g) => {
          g.x = g.spawn.x;
          g.y = g.spawn.y;
          g.frightened = 0;
        });
        invuln = 12;
      }

      function stepPlayer() {
        if (canMove(player.x, player.y, player.queued)) player.dir = player.queued;
        if (canMove(player.x, player.y, player.dir)) {
          player.x += player.dir.dx;
          player.y += player.dir.dy;
        }
        const k = `${player.x},${player.y}`;
        if (dots.has(k)) {
          dots.delete(k);
          score += 10;
          updateScore();
        }
        if (pellets.has(k)) {
          pellets.delete(k);
          score += 50;
          updateScore();
          ghosts.forEach((g) => (g.frightened = FRIGHT_MS));
        }
        if (dots.size === 0 && pellets.size === 0) {
          gameOver = true;
          won = true;
        }
      }

      function stepGhosts() {
        ghosts.forEach((g) => {
          if (g.frightened > 0) g.frightened = Math.max(0, g.frightened - GHOST_STEP_MS);

          let dirs = [
            { dx: 1, dy: 0 }, { dx: -1, dy: 0 }, { dx: 0, dy: 1 }, { dx: 0, dy: -1 },
          ].filter((d) => canMove(g.x, g.y, d));
          if (!dirs.length) return;

          const reverse = { dx: -g.dir.dx, dy: -g.dir.dy };
          const nonReverse = dirs.filter((d) => !(d.dx === reverse.dx && d.dy === reverse.dy));
          const options = nonReverse.length ? nonReverse : dirs;

          const dist = Math.hypot(g.x - player.x, g.y - player.y);
          const shouldChase = g.mode === "chase" ? Math.random() < 0.75 : dist <= 4;

          let chosen;
          if (g.frightened > 0 || !shouldChase) {
            chosen = options[Math.floor(Math.random() * options.length)];
          } else {
            const step = bfsFirstStep({ x: g.x, y: g.y }, { x: player.x, y: player.y });
            chosen = step && options.some((o) => o.dx === step.dx && o.dy === step.dy)
              ? step
              : options[Math.floor(Math.random() * options.length)];
          }
          g.dir = chosen;
          g.x += chosen.dx;
          g.y += chosen.dy;
        });
      }

      function checkCollisions() {
        if (invuln > 0) {
          invuln -= 1;
          return;
        }
        for (const g of ghosts) {
          if (g.x === player.x && g.y === player.y) {
            if (g.frightened > 0) {
              g.x = g.spawn.x;
              g.y = g.spawn.y;
              g.frightened = 0;
              score += 100;
              updateScore();
            } else {
              loseLife();
              return;
            }
          }
        }
      }

      function update(dt) {
        if (gameOver) return;
        stepAcc += dt;
        if (stepAcc >= STEP_MS) {
          stepAcc = 0;
          stepPlayer();
          checkCollisions();
        }
        ghostStepAcc += dt;
        if (ghostStepAcc >= GHOST_STEP_MS) {
          ghostStepAcc = 0;
          stepGhosts();
          checkCollisions();
        }
      }

      function cellPx(gx, gy) {
        return { x: OFFSET_X + gx * CELL, y: OFFSET_Y + gy * CELL };
      }

      function draw() {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, W, H);

        for (let y = 0; y < ROWS; y++) {
          for (let x = 0; x < COLS; x++) {
            if (grid[y][x]) {
              const p = cellPx(x, y);
              ctx.fillStyle = "#161642";
              ctx.fillRect(p.x, p.y, CELL, CELL);
            }
          }
        }

        ctx.fillStyle = "#ffe45e";
        dots.forEach((k) => {
          const [x, y] = k.split(",").map(Number);
          const p = cellPx(x, y);
          ctx.beginPath();
          ctx.arc(p.x + CELL / 2, p.y + CELL / 2, 2.4, 0, Math.PI * 2);
          ctx.fill();
        });

        const pulse = 5 + Math.sin(performance.now() / 150) * 1.5;
        ctx.fillStyle = "#fbbf24";
        ctx.shadowColor = "#fbbf24";
        ctx.shadowBlur = 8;
        pellets.forEach((k) => {
          const [x, y] = k.split(",").map(Number);
          const p = cellPx(x, y);
          ctx.beginPath();
          ctx.arc(p.x + CELL / 2, p.y + CELL / 2, pulse, 0, Math.PI * 2);
          ctx.fill();
        });
        ctx.shadowBlur = 0;

        ghosts.forEach((g) => {
          const p = cellPx(g.x, g.y);
          const cx = p.x + CELL / 2, cy = p.y + CELL / 2;
          const frightenedFlicker = g.frightened > 0 && g.frightened < 1500 && Math.floor(performance.now() / 150) % 2 === 0;
          const color = g.frightened > 0 ? (frightenedFlicker ? "#e8e8f5" : "#3468ff") : g.color;
          ctx.fillStyle = color;
          ctx.shadowColor = color;
          ctx.shadowBlur = 6;
          ctx.beginPath();
          ctx.arc(cx, cy, CELL / 2 - 3, Math.PI, 0);
          ctx.lineTo(cx + CELL / 2 - 3, cy + CELL / 2 - 4);
          ctx.lineTo(cx, cy + CELL / 2 - 8);
          ctx.lineTo(cx - CELL / 2 + 3, cy + CELL / 2 - 4);
          ctx.closePath();
          ctx.fill();
          ctx.shadowBlur = 0;
          ctx.fillStyle = "#fff";
          ctx.beginPath();
          ctx.arc(cx - 4, cy - 2, 2.6, 0, Math.PI * 2);
          ctx.arc(cx + 4, cy - 2, 2.6, 0, Math.PI * 2);
          ctx.fill();
        });

        const pp = cellPx(player.x, player.y);
        const pcx = pp.x + CELL / 2, pcy = pp.y + CELL / 2;
        const angle = Math.atan2(player.dir.dy, player.dir.dx);
        const mouth = Math.abs(Math.sin(performance.now() / 100)) * 0.28 + 0.06;
        ctx.fillStyle = "#fbbf24";
        ctx.shadowColor = "#fbbf24";
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.moveTo(pcx, pcy);
        ctx.arc(pcx, pcy, CELL / 2 - 2, angle + mouth * Math.PI, angle + (2 - mouth) * Math.PI);
        ctx.closePath();
        ctx.fill();
        ctx.shadowBlur = 0;

        if (gameOver) {
          ctx.fillStyle = "rgba(0,0,0,0.7)";
          ctx.fillRect(0, 0, W, H);
          ctx.fillStyle = "#ffe45e";
          ctx.font = "bold 28px Consolas, monospace";
          ctx.textAlign = "center";
          ctx.fillText(won ? "LABYRINTHE NETTOYÉ !" : "GAME OVER", W / 2, H / 2 - 10);
          ctx.font = "16px Consolas, monospace";
          ctx.fillText(`Score : ${score} — Espace pour rejouer`, W / 2, H / 2 + 24);
          ctx.textAlign = "start";
        }
      }

      let raf, last = performance.now();
      function loop(now) {
        const dt = now - last;
        last = now;
        update(dt);
        draw();
        raf = requestAnimationFrame(loop);
      }
      raf = requestAnimationFrame(loop);

      return function stop() {
        cancelAnimationFrame(raf);
        window.removeEventListener("keydown", onKeyDown);
      };
    },
  });
})();
