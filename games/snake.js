(function () {
  window.ARCADE_GAMES = window.ARCADE_GAMES || [];

  window.ARCADE_GAMES.push({
    id: "snake",
    name: "Snake",
    icon: "🐍",
    accent: "#3dff8a",
    description: "Mange, grandis, évite ta propre queue.",
    hint: "Flèches ou WASD pour diriger. Espace pour rejouer après une partie.",

    start(canvas, setScore) {
      const ctx = canvas.getContext("2d");
      const W = canvas.width;
      const H = canvas.height;
      const CELL = 20;
      const COLS = Math.floor(W / CELL);
      const ROWS = Math.floor(H / CELL);
      const STEP_MS = 100;

      let snake, dir, nextDir, food, score, gameOver, acc;

      function reset() {
        snake = [
          { x: Math.floor(COLS / 2), y: Math.floor(ROWS / 2) },
          { x: Math.floor(COLS / 2) - 1, y: Math.floor(ROWS / 2) },
          { x: Math.floor(COLS / 2) - 2, y: Math.floor(ROWS / 2) },
        ];
        dir = { x: 1, y: 0 };
        nextDir = { x: 1, y: 0 };
        score = 0;
        gameOver = false;
        acc = 0;
        placeFood();
        updateScore();
      }

      function placeFood() {
        let pos;
        do {
          pos = {
            x: Math.floor(Math.random() * COLS),
            y: Math.floor(Math.random() * ROWS),
          };
        } while (snake.some((s) => s.x === pos.x && s.y === pos.y));
        food = pos;
      }

      function updateScore() {
        setScore(`SCORE ${score}`);
      }

      reset();

      const keyMap = {
        ArrowUp: { x: 0, y: -1 }, w: { x: 0, y: -1 }, W: { x: 0, y: -1 },
        ArrowDown: { x: 0, y: 1 }, s: { x: 0, y: 1 }, S: { x: 0, y: 1 },
        ArrowLeft: { x: -1, y: 0 }, a: { x: -1, y: 0 }, A: { x: -1, y: 0 },
        ArrowRight: { x: 1, y: 0 }, d: { x: 1, y: 0 }, D: { x: 1, y: 0 },
      };

      function onKeyDown(e) {
        if (gameOver && e.key === " ") {
          reset();
          return;
        }
        const d = keyMap[e.key];
        if (!d) return;
        if (d.x === -dir.x && d.y === -dir.y) return;
        nextDir = d;
      }
      window.addEventListener("keydown", onKeyDown);

      function update(dt) {
        if (gameOver) return;
        acc += dt;
        if (acc < STEP_MS) return;
        acc = 0;

        dir = nextDir;
        const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y };

        if (head.x < 0 || head.x >= COLS || head.y < 0 || head.y >= ROWS) {
          gameOver = true;
          return;
        }
        if (snake.some((s) => s.x === head.x && s.y === head.y)) {
          gameOver = true;
          return;
        }

        snake.unshift(head);
        if (head.x === food.x && head.y === food.y) {
          score++;
          updateScore();
          placeFood();
        } else {
          snake.pop();
        }
      }

      function draw() {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, W, H);

        ctx.fillStyle = "#ff2e88";
        ctx.shadowColor = "#ff2e88";
        ctx.shadowBlur = 10;
        ctx.fillRect(food.x * CELL + 2, food.y * CELL + 2, CELL - 4, CELL - 4);
        ctx.shadowBlur = 0;

        snake.forEach((s, i) => {
          ctx.fillStyle = i === 0 ? "#3dff8a" : "#1fa860";
          ctx.shadowColor = "#3dff8a";
          ctx.shadowBlur = i === 0 ? 10 : 0;
          ctx.fillRect(s.x * CELL + 1, s.y * CELL + 1, CELL - 2, CELL - 2);
        });
        ctx.shadowBlur = 0;

        if (gameOver) {
          ctx.fillStyle = "rgba(0,0,0,0.7)";
          ctx.fillRect(0, 0, W, H);
          ctx.fillStyle = "#ffe45e";
          ctx.font = "bold 28px Consolas, monospace";
          ctx.textAlign = "center";
          ctx.fillText("GAME OVER", W / 2, H / 2 - 10);
          ctx.font = "16px Consolas, monospace";
          ctx.fillText(`Score final : ${score} — Espace pour rejouer`, W / 2, H / 2 + 24);
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
