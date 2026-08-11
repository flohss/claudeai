(function () {
  window.ARCADE_GAMES = window.ARCADE_GAMES || [];

  window.ARCADE_GAMES.push({
    id: "breakout",
    name: "Casse-Briques",
    icon: "🧱",
    accent: "#ffe45e",
    description: "Détruis toutes les briques sans perdre la balle.",
    hint: "←/→ ou A/D pour bouger la raquette. Espace pour rejouer.",

    start(canvas, setScore) {
      const ctx = canvas.getContext("2d");
      const W = canvas.width;
      const H = canvas.height;

      const PADDLE_W = 90;
      const PADDLE_H = 12;
      const PADDLE_SPEED = 7;
      const BALL_SIZE = 8;

      const ROWS = 5;
      const COLS = 9;
      const BRICK_W = 62;
      const BRICK_H = 20;
      const BRICK_PAD = 6;
      const BRICK_OFFSET_TOP = 40;
      const BRICK_OFFSET_LEFT = (W - (COLS * (BRICK_W + BRICK_PAD) - BRICK_PAD)) / 2;
      const ROW_COLORS = ["#ff2e88", "#ff8a2e", "#ffe45e", "#3dff8a", "#34f5ff"];

      let paddle, ball, bricks, lives, score, gameOver, won;

      function buildBricks() {
        const arr = [];
        for (let r = 0; r < ROWS; r++) {
          for (let c = 0; c < COLS; c++) {
            arr.push({
              x: BRICK_OFFSET_LEFT + c * (BRICK_W + BRICK_PAD),
              y: BRICK_OFFSET_TOP + r * (BRICK_H + BRICK_PAD),
              alive: true,
              color: ROW_COLORS[r % ROW_COLORS.length],
            });
          }
        }
        return arr;
      }

      function resetBall() {
        ball = {
          x: W / 2,
          y: H - 60,
          vx: 3.4 * (Math.random() < 0.5 ? 1 : -1),
          vy: -3.4,
        };
      }

      function reset() {
        paddle = { x: W / 2 - PADDLE_W / 2 };
        bricks = buildBricks();
        lives = 3;
        score = 0;
        gameOver = false;
        won = false;
        resetBall();
        updateScore();
      }

      function updateScore() {
        setScore(`SCORE ${score}  •  VIES ${lives}`);
      }

      reset();

      const keys = {};
      function onKeyDown(e) {
        keys[e.key] = true;
        if (gameOver && e.key === " ") reset();
      }
      function onKeyUp(e) {
        keys[e.key] = false;
      }
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("keyup", onKeyUp);

      function clamp(v, min, max) {
        return Math.max(min, Math.min(max, v));
      }

      function update() {
        if (gameOver) return;

        if (keys["ArrowLeft"] || keys["a"] || keys["A"]) paddle.x -= PADDLE_SPEED;
        if (keys["ArrowRight"] || keys["d"] || keys["D"]) paddle.x += PADDLE_SPEED;
        paddle.x = clamp(paddle.x, 0, W - PADDLE_W);

        ball.x += ball.vx;
        ball.y += ball.vy;

        if (ball.x <= 0 || ball.x + BALL_SIZE >= W) ball.vx *= -1;
        if (ball.y <= 0) ball.vy *= -1;

        const paddleY = H - 24;
        if (
          ball.y + BALL_SIZE >= paddleY &&
          ball.y + BALL_SIZE <= paddleY + PADDLE_H + 6 &&
          ball.x + BALL_SIZE >= paddle.x &&
          ball.x <= paddle.x + PADDLE_W &&
          ball.vy > 0
        ) {
          ball.vy = -Math.abs(ball.vy);
          const hitPos = (ball.x + BALL_SIZE / 2 - (paddle.x + PADDLE_W / 2)) / (PADDLE_W / 2);
          ball.vx = hitPos * 4.5;
        }

        if (ball.y > H) {
          lives--;
          updateScore();
          if (lives <= 0) {
            gameOver = true;
          } else {
            resetBall();
          }
        }

        for (const b of bricks) {
          if (!b.alive) continue;
          if (
            ball.x + BALL_SIZE >= b.x &&
            ball.x <= b.x + BRICK_W &&
            ball.y + BALL_SIZE >= b.y &&
            ball.y <= b.y + BRICK_H
          ) {
            b.alive = false;
            ball.vy *= -1;
            score += 10;
            updateScore();
            break;
          }
        }

        if (bricks.every((b) => !b.alive)) {
          gameOver = true;
          won = true;
        }
      }

      function draw() {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, W, H);

        bricks.forEach((b) => {
          if (!b.alive) return;
          ctx.fillStyle = b.color;
          ctx.shadowColor = b.color;
          ctx.shadowBlur = 6;
          ctx.fillRect(b.x, b.y, BRICK_W, BRICK_H);
        });
        ctx.shadowBlur = 0;

        ctx.fillStyle = "#34f5ff";
        ctx.shadowColor = "#34f5ff";
        ctx.shadowBlur = 10;
        ctx.fillRect(paddle.x, H - 24, PADDLE_W, PADDLE_H);

        ctx.fillStyle = "#fff";
        ctx.shadowColor = "#fff";
        ctx.fillRect(ball.x, ball.y, BALL_SIZE, BALL_SIZE);
        ctx.shadowBlur = 0;

        if (gameOver) {
          ctx.fillStyle = "rgba(0,0,0,0.7)";
          ctx.fillRect(0, 0, W, H);
          ctx.fillStyle = "#ffe45e";
          ctx.font = "bold 28px Consolas, monospace";
          ctx.textAlign = "center";
          ctx.fillText(won ? "VICTOIRE !" : "GAME OVER", W / 2, H / 2 - 10);
          ctx.font = "16px Consolas, monospace";
          ctx.fillText(`Score : ${score} — Espace pour rejouer`, W / 2, H / 2 + 24);
          ctx.textAlign = "start";
        }
      }

      let raf;
      function loop() {
        update();
        draw();
        raf = requestAnimationFrame(loop);
      }
      loop();

      return function stop() {
        cancelAnimationFrame(raf);
        window.removeEventListener("keydown", onKeyDown);
        window.removeEventListener("keyup", onKeyUp);
      };
    },
  });
})();
