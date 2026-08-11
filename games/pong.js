(function () {
  window.ARCADE_GAMES = window.ARCADE_GAMES || [];

  window.ARCADE_GAMES.push({
    id: "pong",
    name: "Pong",
    icon: "🏓",
    accent: "#34f5ff",
    description: "Le duel de raquettes original, 1972.",
    hint: "↑/↓ ou W/S pour bouger ta raquette. Premier à 7 points gagne.",

    start(canvas, setScore) {
      const ctx = canvas.getContext("2d");
      const W = canvas.width;
      const H = canvas.height;

      const PADDLE_W = 12;
      const PADDLE_H = 80;
      const PADDLE_SPEED = 6.5;
      const BALL_SIZE = 10;
      const WIN_SCORE = 7;

      const player = { x: 20, y: H / 2 - PADDLE_H / 2, dy: 0 };
      const cpu = { x: W - 20 - PADDLE_W, y: H / 2 - PADDLE_H / 2 };
      let ball, running = true, gameOver = false;
      let scores = { player: 0, cpu: 0 };

      function resetBall(dir) {
        ball = {
          x: W / 2,
          y: H / 2,
          vx: 4.5 * dir,
          vy: (Math.random() * 4 - 2) || 2,
        };
      }
      resetBall(Math.random() < 0.5 ? 1 : -1);

      function updateScore() {
        setScore(`TOI ${scores.player} — ${scores.cpu} CPU`);
      }
      updateScore();

      const keys = {};
      function onKeyDown(e) {
        keys[e.key] = true;
        if (gameOver && e.key === " ") {
          scores = { player: 0, cpu: 0 };
          gameOver = false;
          running = true;
          resetBall(Math.random() < 0.5 ? 1 : -1);
          updateScore();
        }
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
        if (!running) return;

        if (keys["ArrowUp"] || keys["w"] || keys["W"]) player.y -= PADDLE_SPEED;
        if (keys["ArrowDown"] || keys["s"] || keys["S"]) player.y += PADDLE_SPEED;
        player.y = clamp(player.y, 0, H - PADDLE_H);

        const cpuCenter = cpu.y + PADDLE_H / 2;
        const targetY = ball.y;
        const cpuSpeed = 4.6;
        if (cpuCenter < targetY - 10) cpu.y += cpuSpeed;
        else if (cpuCenter > targetY + 10) cpu.y -= cpuSpeed;
        cpu.y = clamp(cpu.y, 0, H - PADDLE_H);

        ball.x += ball.vx;
        ball.y += ball.vy;

        if (ball.y <= 0 || ball.y >= H - BALL_SIZE) {
          ball.vy *= -1;
          ball.y = clamp(ball.y, 0, H - BALL_SIZE);
        }

        if (
          ball.x <= player.x + PADDLE_W &&
          ball.x + BALL_SIZE >= player.x &&
          ball.y + BALL_SIZE >= player.y &&
          ball.y <= player.y + PADDLE_H
        ) {
          ball.x = player.x + PADDLE_W;
          ball.vx = Math.abs(ball.vx) * 1.04;
          const hitPos = (ball.y + BALL_SIZE / 2 - (player.y + PADDLE_H / 2)) / (PADDLE_H / 2);
          ball.vy = hitPos * 5;
        }

        if (
          ball.x + BALL_SIZE >= cpu.x &&
          ball.x <= cpu.x + PADDLE_W &&
          ball.y + BALL_SIZE >= cpu.y &&
          ball.y <= cpu.y + PADDLE_H
        ) {
          ball.x = cpu.x - BALL_SIZE;
          ball.vx = -Math.abs(ball.vx) * 1.04;
          const hitPos = (ball.y + BALL_SIZE / 2 - (cpu.y + PADDLE_H / 2)) / (PADDLE_H / 2);
          ball.vy = hitPos * 5;
        }

        if (ball.x < -BALL_SIZE) {
          scores.cpu++;
          updateScore();
          checkWin();
          if (running) resetBall(1);
        } else if (ball.x > W) {
          scores.player++;
          updateScore();
          checkWin();
          if (running) resetBall(-1);
        }
      }

      function checkWin() {
        if (scores.player >= WIN_SCORE || scores.cpu >= WIN_SCORE) {
          running = false;
          gameOver = true;
        }
      }

      function draw() {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, W, H);

        ctx.strokeStyle = "#1a3a4a";
        ctx.setLineDash([8, 10]);
        ctx.beginPath();
        ctx.moveTo(W / 2, 0);
        ctx.lineTo(W / 2, H);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = "#34f5ff";
        ctx.shadowColor = "#34f5ff";
        ctx.shadowBlur = 12;
        ctx.fillRect(player.x, player.y, PADDLE_W, PADDLE_H);

        ctx.fillStyle = "#ff2e88";
        ctx.shadowColor = "#ff2e88";
        ctx.fillRect(cpu.x, cpu.y, PADDLE_W, PADDLE_H);

        ctx.fillStyle = "#ffe45e";
        ctx.shadowColor = "#ffe45e";
        ctx.fillRect(ball.x, ball.y, BALL_SIZE, BALL_SIZE);
        ctx.shadowBlur = 0;

        if (gameOver) {
          ctx.fillStyle = "rgba(0,0,0,0.7)";
          ctx.fillRect(0, 0, W, H);
          ctx.fillStyle = "#ffe45e";
          ctx.font = "bold 28px Consolas, monospace";
          ctx.textAlign = "center";
          const msg = scores.player > scores.cpu ? "TU AS GAGNÉ !" : "CPU GAGNE !";
          ctx.fillText(msg, W / 2, H / 2 - 10);
          ctx.font = "16px Consolas, monospace";
          ctx.fillText("Espace pour rejouer", W / 2, H / 2 + 24);
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
