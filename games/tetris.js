(function () {
  window.ARCADE_GAMES = window.ARCADE_GAMES || [];

  window.ARCADE_GAMES.push({
    id: "tetris",
    name: "Tetris",
    icon: "🧩",
    accent: "#a78bfa",
    description: "Empile les tétrominos, efface des lignes, 1984.",
    hint: "←/→ déplacer, ↑ tourner, ↓ chute rapide, Espace chute instantanée.",

    start(canvas, setScore) {
      const ctx = canvas.getContext("2d");
      const W = canvas.width;
      const H = canvas.height;

      const COLS = 10;
      const ROWS = 20;
      const CELL = 20;
      const BOARD_LEFT = 40;
      const BOARD_TOP = (H - ROWS * CELL) / 2;

      const SHAPES = {
        I: { cells: [[0, 1], [1, 1], [2, 1], [3, 1]], color: "#34f5ff" },
        J: { cells: [[0, 0], [0, 1], [1, 1], [2, 1]], color: "#3468ff" },
        L: { cells: [[2, 0], [0, 1], [1, 1], [2, 1]], color: "#ff8a2e" },
        O: { cells: [[1, 0], [2, 0], [1, 1], [2, 1]], color: "#ffe45e" },
        S: { cells: [[1, 0], [2, 0], [0, 1], [1, 1]], color: "#3dff8a" },
        T: { cells: [[1, 0], [0, 1], [1, 1], [2, 1]], color: "#c084fc" },
        Z: { cells: [[0, 0], [1, 0], [1, 1], [2, 1]], color: "#ff2e88" },
      };
      const KEYS = Object.keys(SHAPES);

      let board, current, next, score, level, linesCleared, gameOver, dropAcc, dropInterval;

      function emptyBoard() {
        return Array.from({ length: ROWS }, () => Array(COLS).fill(null));
      }

      function spawnPiece() {
        const key = KEYS[Math.floor(Math.random() * KEYS.length)];
        const shape = SHAPES[key];
        return {
          cells: shape.cells.map(([x, y]) => ({ x, y })),
          color: shape.color,
          x: 3,
          y: 0,
        };
      }

      function reset() {
        board = emptyBoard();
        current = spawnPiece();
        next = spawnPiece();
        score = 0;
        level = 1;
        linesCleared = 0;
        gameOver = false;
        dropAcc = 0;
        dropInterval = 600;
        updateScore();
      }

      function updateScore() {
        setScore(`SCORE ${score}  •  NIVEAU ${level}  •  LIGNES ${linesCleared}`);
      }

      reset();

      function cellsAt(piece, ox, oy, cells) {
        return (cells || piece.cells).map((c) => ({ x: piece.x + c.x + ox, y: piece.y + c.y + oy }));
      }

      function collides(cells) {
        return cells.some(({ x, y }) => {
          if (x < 0 || x >= COLS || y >= ROWS) return true;
          if (y < 0) return false;
          return board[y][x] !== null;
        });
      }

      function lockPiece() {
        for (const { x, y } of cellsAt(current, 0, 0)) {
          if (y >= 0) board[y][x] = current.color;
        }
        clearLines();
        current = next;
        next = spawnPiece();
        if (collides(cellsAt(current, 0, 0))) {
          gameOver = true;
        }
      }

      function clearLines() {
        let cleared = 0;
        for (let y = ROWS - 1; y >= 0; y--) {
          if (board[y].every((c) => c !== null)) {
            board.splice(y, 1);
            board.unshift(Array(COLS).fill(null));
            cleared++;
            y++;
          }
        }
        if (cleared > 0) {
          const points = [0, 100, 300, 500, 800][cleared] || 800;
          score += points * level;
          linesCleared += cleared;
          level = 1 + Math.floor(linesCleared / 10);
          dropInterval = Math.max(120, 600 - (level - 1) * 45);
          updateScore();
        }
      }

      function move(dx) {
        const moved = cellsAt(current, dx, 0);
        if (!collides(moved)) current.x += dx;
      }

      function softDrop() {
        const moved = cellsAt(current, 0, 1);
        if (!collides(moved)) {
          current.y += 1;
          return true;
        }
        lockPiece();
        return false;
      }

      function hardDrop() {
        while (softDrop()) {}
      }

      function rotate() {
        const pivot = current.cells[1] || current.cells[0];
        const rotated = current.cells.map((c) => {
          const rx = pivot.y - c.y + pivot.x;
          const ry = c.x - pivot.x + pivot.y;
          return { x: rx, y: ry };
        });
        const test = cellsAt(current, 0, 0, rotated);
        if (!collides(test)) current.cells = rotated;
        else {
          const kicks = [-1, 1, -2, 2];
          for (const k of kicks) {
            const kicked = cellsAt({ ...current, x: current.x + k }, 0, 0, rotated);
            if (!collides(kicked)) {
              current.x += k;
              current.cells = rotated;
              break;
            }
          }
        }
      }

      function onKeyDown(e) {
        if (gameOver) {
          if (e.key === " ") reset();
          return;
        }
        if (e.key === "ArrowLeft" || e.key === "a" || e.key === "A") move(-1);
        else if (e.key === "ArrowRight" || e.key === "d" || e.key === "D") move(1);
        else if (e.key === "ArrowDown" || e.key === "s" || e.key === "S") softDrop();
        else if (e.key === "ArrowUp" || e.key === "w" || e.key === "W") rotate();
        else if (e.key === " ") {
          e.preventDefault();
          hardDrop();
        }
      }
      window.addEventListener("keydown", onKeyDown);

      function update(dt) {
        if (gameOver) return;
        dropAcc += dt;
        if (dropAcc >= dropInterval) {
          dropAcc = 0;
          softDrop();
        }
      }

      function drawCell(px, py, color) {
        ctx.fillStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = 6;
        ctx.fillRect(px + 1, py + 1, CELL - 2, CELL - 2);
      }

      function draw() {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, W, H);
        ctx.shadowBlur = 0;

        ctx.strokeStyle = "#2a2a4a";
        ctx.strokeRect(BOARD_LEFT, BOARD_TOP, COLS * CELL, ROWS * CELL);

        for (let y = 0; y < ROWS; y++) {
          for (let x = 0; x < COLS; x++) {
            if (board[y][x]) {
              drawCell(BOARD_LEFT + x * CELL, BOARD_TOP + y * CELL, board[y][x]);
            }
          }
        }

        if (!gameOver) {
          for (const { x, y } of cellsAt(current, 0, 0)) {
            if (y >= 0) drawCell(BOARD_LEFT + x * CELL, BOARD_TOP + y * CELL, current.color);
          }
        }
        ctx.shadowBlur = 0;

        ctx.fillStyle = "#8888a8";
        ctx.font = "13px Consolas, monospace";
        const previewX = BOARD_LEFT + COLS * CELL + 30;
        const previewY = BOARD_TOP + 10;
        ctx.fillText("Prochain :", previewX, previewY);
        if (next) {
          for (const c of next.cells) {
            drawCell(previewX + c.x * CELL, previewY + 16 + c.y * CELL, next.color);
          }
        }
        ctx.shadowBlur = 0;

        if (gameOver) {
          ctx.fillStyle = "rgba(0,0,0,0.7)";
          ctx.fillRect(0, 0, W, H);
          ctx.fillStyle = "#ffe45e";
          ctx.font = "bold 28px Consolas, monospace";
          ctx.textAlign = "center";
          ctx.fillText("GAME OVER", W / 2, H / 2 - 10);
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
