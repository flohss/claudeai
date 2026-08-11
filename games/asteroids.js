(function () {
  window.ARCADE_GAMES = window.ARCADE_GAMES || [];

  window.ARCADE_GAMES.push({
    id: "asteroids",
    name: "Asteroids",
    icon: "☄️",
    accent: "#e8e8f5",
    description: "Pilote un vaisseau, pulvérise les astéroïdes, 1979.",
    hint: "←/→ tourner, ↑ propulser, Espace tirer. Le vaisseau réapparaît aux bords.",

    start(canvas, setScore) {
      const ctx = canvas.getContext("2d");
      const W = canvas.width;
      const H = canvas.height;

      function wrap(pos) {
        if (pos.x < 0) pos.x += W;
        if (pos.x > W) pos.x -= W;
        if (pos.y < 0) pos.y += H;
        if (pos.y > H) pos.y -= H;
      }

      let ship, bullets, asteroids, lives, score, gameOver, invuln;

      function newShip() {
        return { x: W / 2, y: H / 2, angle: -Math.PI / 2, vx: 0, vy: 0 };
      }

      function makeAsteroid(x, y, size) {
        const angle = Math.random() * Math.PI * 2;
        const speed = 0.6 + Math.random() * (size === 3 ? 0.4 : size === 2 ? 0.9 : 1.4);
        const points = [];
        const n = 10;
        for (let i = 0; i < n; i++) {
          const a = (i / n) * Math.PI * 2;
          const r = size * 14 * (0.75 + Math.random() * 0.5);
          points.push({ a, r });
        }
        return {
          x, y, size,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          rot: (Math.random() - 0.5) * 0.03,
          angle: 0,
          points,
        };
      }

      function spawnWave(count) {
        const arr = [];
        for (let i = 0; i < count; i++) {
          let x, y;
          do {
            x = Math.random() * W;
            y = Math.random() * H;
          } while (Math.hypot(x - W / 2, y - H / 2) < 120);
          arr.push(makeAsteroid(x, y, 3));
        }
        return arr;
      }

      function reset() {
        ship = newShip();
        bullets = [];
        asteroids = spawnWave(5);
        lives = 3;
        score = 0;
        gameOver = false;
        invuln = 120;
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
        if (gameOver && e.key === " ") {
          reset();
          return;
        }
        if (e.key === " " && !spaceLatch) {
          spaceLatch = true;
          bullets.push({
            x: ship.x + Math.cos(ship.angle) * 14,
            y: ship.y + Math.sin(ship.angle) * 14,
            vx: Math.cos(ship.angle) * 6 + ship.vx,
            vy: Math.sin(ship.angle) * 6 + ship.vy,
            life: 60,
          });
        }
      }
      function onKeyUp(e) {
        keys[e.key] = false;
        if (e.key === " ") spaceLatch = false;
      }
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("keyup", onKeyUp);

      function splitAsteroid(a) {
        score += a.size === 3 ? 20 : a.size === 2 ? 50 : 100;
        updateScore();
        if (a.size > 1) {
          asteroids.push(makeAsteroid(a.x, a.y, a.size - 1));
          asteroids.push(makeAsteroid(a.x, a.y, a.size - 1));
        }
      }

      function update() {
        if (gameOver) return;

        if (keys["ArrowLeft"] || keys["a"] || keys["A"]) ship.angle -= 0.06;
        if (keys["ArrowRight"] || keys["d"] || keys["D"]) ship.angle += 0.06;
        if (keys["ArrowUp"] || keys["w"] || keys["W"]) {
          ship.vx += Math.cos(ship.angle) * 0.12;
          ship.vy += Math.sin(ship.angle) * 0.12;
        }
        ship.vx *= 0.99;
        ship.vy *= 0.99;
        ship.x += ship.vx;
        ship.y += ship.vy;
        wrap(ship);
        if (invuln > 0) invuln--;

        bullets.forEach((b) => {
          b.x += b.vx;
          b.y += b.vy;
          wrap(b);
          b.life--;
        });
        bullets = bullets.filter((b) => b.life > 0);

        asteroids.forEach((a) => {
          a.x += a.vx;
          a.y += a.vy;
          a.angle += a.rot;
          wrap(a);
        });

        for (const b of bullets) {
          for (const a of asteroids) {
            if (Math.hypot(b.x - a.x, b.y - a.y) < a.size * 14) {
              b.life = 0;
              a.dead = true;
              splitAsteroid(a);
            }
          }
        }
        asteroids = asteroids.filter((a) => !a.dead);

        if (invuln <= 0) {
          for (const a of asteroids) {
            if (Math.hypot(ship.x - a.x, ship.y - a.y) < a.size * 14 + 6) {
              lives--;
              updateScore();
              if (lives <= 0) {
                gameOver = true;
              } else {
                ship = newShip();
                invuln = 120;
              }
              break;
            }
          }
        }

        if (asteroids.length === 0) {
          asteroids = spawnWave(5 + Math.floor(score / 500));
        }
      }

      function draw() {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, W, H);

        ctx.strokeStyle = "#e8e8f5";
        ctx.lineWidth = 1.5;
        asteroids.forEach((a) => {
          ctx.save();
          ctx.translate(a.x, a.y);
          ctx.rotate(a.angle);
          ctx.shadowColor = "#8888a8";
          ctx.shadowBlur = 6;
          ctx.beginPath();
          a.points.forEach((p, i) => {
            const px = Math.cos(p.a) * p.r;
            const py = Math.sin(p.a) * p.r;
            if (i === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          });
          ctx.closePath();
          ctx.stroke();
          ctx.restore();
        });
        ctx.shadowBlur = 0;

        ctx.fillStyle = "#ffe45e";
        ctx.shadowColor = "#ffe45e";
        ctx.shadowBlur = 6;
        bullets.forEach((b) => {
          ctx.beginPath();
          ctx.arc(b.x, b.y, 2, 0, Math.PI * 2);
          ctx.fill();
        });
        ctx.shadowBlur = 0;

        if (!gameOver && (invuln <= 0 || Math.floor(invuln / 6) % 2 === 0)) {
          ctx.save();
          ctx.translate(ship.x, ship.y);
          ctx.rotate(ship.angle);
          ctx.strokeStyle = "#34f5ff";
          ctx.shadowColor = "#34f5ff";
          ctx.shadowBlur = 10;
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.moveTo(14, 0);
          ctx.lineTo(-10, 9);
          ctx.lineTo(-5, 0);
          ctx.lineTo(-10, -9);
          ctx.closePath();
          ctx.stroke();
          ctx.restore();
          ctx.shadowBlur = 0;
        }

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
