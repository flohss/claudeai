(function () {
  window.ARCADE_GAMES = window.ARCADE_GAMES || [];

  window.ARCADE_GAMES.push({
    id: "invaders",
    name: "Space Invaders",
    icon: "👾",
    accent: "#ff2e88",
    description: "Repousse l'invasion extraterrestre, 1978.",
    hint: "←/→ ou A/D pour bouger, Espace pour tirer. 3 vies.",

    start(canvas, setScore) {
      const ctx = canvas.getContext("2d");
      const W = canvas.width;
      const H = canvas.height;

      const PLAYER_W = 34;
      const PLAYER_H = 16;
      const PLAYER_SPEED = 5.5;
      const BULLET_SPEED = 7;
      const ENEMY_BULLET_SPEED = 4;

      const ROWS = 4;
      const COLS = 8;
      const ENEMY_W = 30;
      const ENEMY_H = 20;
      const ENEMY_PAD = 14;
      const ENEMY_OFFSET_TOP = 40;
      const ENEMY_COLORS = ["#ff2e88", "#ff8a2e", "#ffe45e", "#3dff8a"];

      let player, bullets, enemyBullets, enemies, enemyDir, enemySpeed;
      let score, lives, gameOver, won;

      function buildEnemies() {
        const arr = [];
        const totalW = COLS * (ENEMY_W + ENEMY_PAD) - ENEMY_PAD;
        const offsetLeft = (W - totalW) / 2;
        for (let r = 0; r < ROWS; r++) {
          for (let c = 0; c < COLS; c++) {
            arr.push({
              x: offsetLeft + c * (ENEMY_W + ENEMY_PAD),
              y: ENEMY_OFFSET_TOP + r * (ENEMY_H + ENEMY_PAD),
              alive: true,
              color: ENEMY_COLORS[r % ENEMY_COLORS.length],
            });
          }
        }
        return arr;
      }

      function reset() {
        player = { x: W / 2 - PLAYER_W / 2 };
        bullets = [];
        enemyBullets = [];
        enemies = buildEnemies();
        enemyDir = 1;
        enemySpeed = 0.6;
        score = 0;
        lives = 3;
        gameOver = false;
        won = false;
        updateScore();
      }

      function updateScore() {
        setScore(`SCORE ${score}  •  VIES ${lives}`);
      }

      reset();

      const keys = {};
      let spaceLatch = false;
      function onKeyDown(e) {
        keys[e.key] = true;
        if (e.key === " ") {
          if (gameOver) {
            reset();
          } else if (!spaceLatch) {
            bullets.push({ x: player.x + PLAYER_W / 2 - 2, y: H - 40 });
            spaceLatch = true;
          }
        }
      }
      function onKeyUp(e) {
        keys[e.key] = false;
        if (e.key === " ") spaceLatch = false;
      }
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("keyup", onKeyUp);

      function clamp(v, min, max) {
        return Math.max(min, Math.min(max, v));
      }

      function update() {
        if (gameOver) return;

        if (keys["ArrowLeft"] || keys["a"] || keys["A"]) player.x -= PLAYER_SPEED;
        if (keys["ArrowRight"] || keys["d"] || keys["D"]) player.x += PLAYER_SPEED;
        player.x = clamp(player.x, 0, W - PLAYER_W);

        bullets.forEach((b) => (b.y -= BULLET_SPEED));
        bullets = bullets.filter((b) => b.y > -10);

        enemyBullets.forEach((b) => (b.y += ENEMY_BULLET_SPEED));
        enemyBullets = enemyBullets.filter((b) => b.y < H + 10);

        const alive = enemies.filter((e) => e.alive);
        let hitEdge = false;
        for (const e of alive) {
          e.x += enemyDir * enemySpeed;
          if (e.x <= 0 || e.x + ENEMY_W >= W) hitEdge = true;
        }
        if (hitEdge) {
          enemyDir *= -1;
          for (const e of alive) e.y += 12;
        }

        if (Math.random() < 0.015 && alive.length) {
          const shooter = alive[Math.floor(Math.random() * alive.length)];
          enemyBullets.push({ x: shooter.x + ENEMY_W / 2 - 2, y: shooter.y + ENEMY_H });
        }

        for (const b of bullets) {
          for (const e of alive) {
            if (
              e.alive &&
              b.x < e.x + ENEMY_W &&
              b.x + 4 > e.x &&
              b.y < e.y + ENEMY_H &&
              b.y + 10 > e.y
            ) {
              e.alive = false;
              b.y = -100;
              score += 10;
              updateScore();
            }
          }
        }

        for (const b of enemyBullets) {
          if (
            b.x < player.x + PLAYER_W &&
            b.x + 4 > player.x &&
            b.y < H - 24 + PLAYER_H &&
            b.y + 10 > H - 24
          ) {
            b.y = H + 100;
            lives--;
            updateScore();
            if (lives <= 0) gameOver = true;
          }
        }

        for (const e of alive) {
          if (e.y + ENEMY_H >= H - 30) {
            gameOver = true;
          }
        }

        if (enemies.every((e) => !e.alive)) {
          gameOver = true;
          won = true;
        }
      }

      function draw() {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, W, H);

        enemies.forEach((e) => {
          if (!e.alive) return;
          ctx.fillStyle = e.color;
          ctx.shadowColor = e.color;
          ctx.shadowBlur = 6;
          ctx.fillRect(e.x, e.y, ENEMY_W, ENEMY_H);
        });
        ctx.shadowBlur = 0;

        ctx.fillStyle = "#ffe45e";
        ctx.shadowColor = "#ffe45e";
        ctx.shadowBlur = 6;
        bullets.forEach((b) => ctx.fillRect(b.x, b.y, 4, 10));

        ctx.fillStyle = "#ff2e88";
        ctx.shadowColor = "#ff2e88";
        enemyBullets.forEach((b) => ctx.fillRect(b.x, b.y, 4, 10));
        ctx.shadowBlur = 0;

        ctx.fillStyle = "#34f5ff";
        ctx.shadowColor = "#34f5ff";
        ctx.shadowBlur = 10;
        ctx.fillRect(player.x, H - 24, PLAYER_W, PLAYER_H);
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
