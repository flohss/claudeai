(function () {
  window.ARCADE_GAMES = window.ARCADE_GAMES || [];

  window.ARCADE_GAMES.push({
    id: "missile-command",
    name: "Missile Command",
    icon: "🚀",
    accent: "#f43f5e",
    description: "Défends tes villes des missiles ennemis, 1980.",
    hint: "Flèches pour viser, Espace pour tirer. Protège tes 6 villes.",

    start(canvas, setScore) {
      const ctx = canvas.getContext("2d");
      const W = canvas.width;
      const H = canvas.height;
      const GROUND_Y = H - 24;
      const CANNON_X = W / 2;
      const CANNON_Y = GROUND_Y;
      const EXPLOSION_MAX_R = 34;
      const FIRE_COOLDOWN = 260;

      let cities, crosshair, playerMissiles, enemyMissiles, explosions;
      let score, gameOver, spawnTimer, fireTimer, wave, waveTimer;

      function buildCities() {
        const arr = [];
        const slots = [70, 155, 240, 400, 485, 570];
        for (const x of slots) arr.push({ x, alive: true });
        return arr;
      }

      function reset() {
        cities = buildCities();
        crosshair = { x: W / 2, y: H / 2 };
        playerMissiles = [];
        enemyMissiles = [];
        explosions = [];
        score = 0;
        gameOver = false;
        spawnTimer = 60;
        fireTimer = 0;
        wave = 1;
        waveTimer = 0;
        updateScore();
      }

      function updateScore() {
        setScore(`SCORE ${score}  •  VAGUE ${wave}  •  VILLES ${cities.filter((c) => c.alive).length}`);
      }

      reset();

      const keys = {};
      function onKeyDown(e) {
        keys[e.key] = true;
        if (gameOver && e.key === " ") {
          reset();
          return;
        }
        if (e.key === " ") e.preventDefault();
      }
      function onKeyUp(e) {
        keys[e.key] = false;
      }
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("keyup", onKeyUp);

      function clamp(v, min, max) {
        return Math.max(min, Math.min(max, v));
      }

      function aliveCities() {
        return cities.filter((c) => c.alive);
      }

      function spawnEnemy() {
        const alive = aliveCities();
        const startX = Math.random() * W;
        let targetX;
        if (alive.length && Math.random() < 0.75) {
          targetX = alive[Math.floor(Math.random() * alive.length)].x;
        } else {
          targetX = Math.random() * W;
        }
        const speed = 0.55 + wave * 0.07 + Math.random() * 0.3;
        enemyMissiles.push({
          x: startX,
          y: -10,
          startX,
          startY: -10,
          targetX,
          targetY: GROUND_Y,
          speed,
          trail: [],
        });
      }

      function fireMissile() {
        playerMissiles.push({
          x: CANNON_X,
          y: CANNON_Y,
          startX: CANNON_X,
          startY: CANNON_Y,
          targetX: crosshair.x,
          targetY: crosshair.y,
          speed: 7,
        });
      }

      function addExplosion(x, y) {
        explosions.push({ x, y, r: 4, growing: true });
      }

      function update() {
        if (gameOver) return;

        if (keys["ArrowLeft"] || keys["a"] || keys["A"]) crosshair.x -= 6.5;
        if (keys["ArrowRight"] || keys["d"] || keys["D"]) crosshair.x += 6.5;
        if (keys["ArrowUp"] || keys["w"] || keys["W"]) crosshair.y -= 6.5;
        if (keys["ArrowDown"] || keys["s"] || keys["S"]) crosshair.y += 6.5;
        crosshair.x = clamp(crosshair.x, 0, W);
        crosshair.y = clamp(crosshair.y, 20, GROUND_Y - 10);

        fireTimer -= 16;
        if (keys[" "] && fireTimer <= 0) {
          fireMissile();
          fireTimer = FIRE_COOLDOWN;
        }

        spawnTimer -= 1;
        if (spawnTimer <= 0) {
          spawnEnemy();
          spawnTimer = Math.max(18, 55 - wave * 3);
        }

        waveTimer += 1;
        if (waveTimer > 600) {
          wave += 1;
          waveTimer = 0;
          updateScore();
        }

        playerMissiles.forEach((m) => {
          const dx = m.targetX - m.startX;
          const dy = m.targetY - m.startY;
          const dist = Math.hypot(dx, dy) || 1;
          const step = m.speed / dist;
          m.progress = (m.progress || 0) + step;
          m.x = m.startX + dx * Math.min(1, m.progress);
          m.y = m.startY + dy * Math.min(1, m.progress);
          if (m.progress >= 1) {
            m.dead = true;
            addExplosion(m.targetX, m.targetY);
          }
        });
        playerMissiles = playerMissiles.filter((m) => !m.dead);

        enemyMissiles.forEach((m) => {
          const dx = m.targetX - m.startX;
          const dy = m.targetY - m.startY;
          const dist = Math.hypot(dx, dy) || 1;
          const step = m.speed / dist;
          m.progress = (m.progress || 0) + step;
          m.x = m.startX + dx * Math.min(1, m.progress);
          m.y = m.startY + dy * Math.min(1, m.progress);
          if (m.progress >= 1) {
            m.dead = true;
            addExplosion(m.x, m.y);
            const city = cities.find((c) => c.alive && Math.abs(c.x - m.targetX) < 20 && m.targetY >= GROUND_Y - 4);
            if (city) {
              city.alive = false;
              updateScore();
            }
          }
        });

        explosions.forEach((ex) => {
          if (ex.growing) {
            ex.r += 1.6;
            if (ex.r >= EXPLOSION_MAX_R) ex.growing = false;
          } else {
            ex.r -= 1.1;
          }
        });
        explosions = explosions.filter((ex) => ex.r > 0);

        for (const m of enemyMissiles) {
          if (m.dead) continue;
          for (const ex of explosions) {
            if (Math.hypot(m.x - ex.x, m.y - ex.y) < ex.r) {
              m.dead = true;
              score += 25;
            }
          }
        }
        enemyMissiles = enemyMissiles.filter((m) => !m.dead);
        updateScore();

        if (aliveCities().length === 0) {
          gameOver = true;
        }
      }

      function draw() {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, W, H);

        ctx.strokeStyle = "#3a2a4a";
        ctx.beginPath();
        ctx.moveTo(0, GROUND_Y);
        ctx.lineTo(W, GROUND_Y);
        ctx.stroke();

        ctx.fillStyle = "#8888a8";
        ctx.beginPath();
        ctx.moveTo(CANNON_X - 16, GROUND_Y);
        ctx.lineTo(CANNON_X, GROUND_Y - 26);
        ctx.lineTo(CANNON_X + 16, GROUND_Y);
        ctx.closePath();
        ctx.fill();

        cities.forEach((c) => {
          if (!c.alive) {
            ctx.fillStyle = "#331313";
            ctx.fillRect(c.x - 16, GROUND_Y - 10, 32, 10);
            return;
          }
          ctx.fillStyle = "#34f5ff";
          ctx.shadowColor = "#34f5ff";
          ctx.shadowBlur = 8;
          ctx.fillRect(c.x - 16, GROUND_Y - 18, 32, 18);
          ctx.fillRect(c.x - 20, GROUND_Y - 6, 40, 6);
          ctx.shadowBlur = 0;
        });

        ctx.strokeStyle = "#ff2e88";
        ctx.lineWidth = 2;
        enemyMissiles.forEach((m) => {
          ctx.beginPath();
          ctx.moveTo(m.startX, m.startY);
          ctx.lineTo(m.x, m.y);
          ctx.stroke();
        });

        ctx.strokeStyle = "#34f5ff";
        playerMissiles.forEach((m) => {
          ctx.beginPath();
          ctx.moveTo(m.startX, m.startY);
          ctx.lineTo(m.x, m.y);
          ctx.stroke();
        });

        explosions.forEach((ex) => {
          const grad = ctx.createRadialGradient(ex.x, ex.y, 0, ex.x, ex.y, ex.r);
          grad.addColorStop(0, "#ffe45e");
          grad.addColorStop(0.6, "#ff8a2e");
          grad.addColorStop(1, "rgba(255,46,136,0)");
          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(ex.x, ex.y, ex.r, 0, Math.PI * 2);
          ctx.fill();
        });

        ctx.strokeStyle = "#3dff8a";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(crosshair.x - 10, crosshair.y);
        ctx.lineTo(crosshair.x + 10, crosshair.y);
        ctx.moveTo(crosshair.x, crosshair.y - 10);
        ctx.lineTo(crosshair.x, crosshair.y + 10);
        ctx.stroke();

        if (gameOver) {
          ctx.fillStyle = "rgba(0,0,0,0.7)";
          ctx.fillRect(0, 0, W, H);
          ctx.fillStyle = "#ffe45e";
          ctx.font = "bold 28px Consolas, monospace";
          ctx.textAlign = "center";
          ctx.fillText("VILLES DÉTRUITES", W / 2, H / 2 - 10);
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
