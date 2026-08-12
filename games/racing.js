(function () {
  window.ARCADE_GAMES = window.ARCADE_GAMES || [];

  window.ARCADE_GAMES.push({
    id: "racing",
    name: "Turbo Racer",
    icon: "🏎️",
    accent: "#ff8a2e",
    description: "Fonce sur la route et évite le trafic, 1982.",
    hint: "←/→ pour changer de voie, ↑ accélérer, ↓ freiner. Espace pour rejouer.",

    start(canvas, setScore) {
      const ctx = canvas.getContext("2d");
      const W = canvas.width;
      const H = canvas.height;

      const ROAD_W = 300;
      const ROAD_L = (W - ROAD_W) / 2;
      const ROAD_R = ROAD_L + ROAD_W;

      const CAR_W = 34;
      const CAR_H = 56;
      const MIN_SPEED = 3;
      const MAX_SPEED = 11;
      const ACCEL = 0.09;
      const BRAKE = 0.16;
      const DRAG = 0.02;
      const STEER_SPEED = 5;

      let player, traffic, speed, distance, gameOver, spawnTimer, laneOffset;

      function reset() {
        player = { x: W / 2 - CAR_W / 2, y: H - 100 };
        traffic = [];
        speed = MIN_SPEED;
        distance = 0;
        gameOver = false;
        spawnTimer = 0;
        laneOffset = 0;
        updateScore();
      }

      function updateScore() {
        setScore(`DISTANCE ${Math.floor(distance)} m  •  VITESSE ${speed.toFixed(1)}`);
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

      function spawnTraffic() {
        const carW = CAR_W;
        const x = ROAD_L + 10 + Math.random() * (ROAD_W - carW - 20);
        const colors = ["#34f5ff", "#ffe45e", "#3dff8a", "#c084fc"];
        traffic.push({
          x,
          y: -CAR_H - 10,
          color: colors[Math.floor(Math.random() * colors.length)],
          speed: 1.5 + Math.random() * 1.5,
        });
      }

      function update() {
        if (gameOver) return;

        if (keys["ArrowUp"] || keys["w"] || keys["W"]) speed += ACCEL;
        else speed -= DRAG;
        if (keys["ArrowDown"] || keys["s"] || keys["S"]) speed -= BRAKE;
        speed = clamp(speed, MIN_SPEED, MAX_SPEED);

        if (keys["ArrowLeft"] || keys["a"] || keys["A"]) player.x -= STEER_SPEED;
        if (keys["ArrowRight"] || keys["d"] || keys["D"]) player.x += STEER_SPEED;
        player.x = clamp(player.x, ROAD_L + 6, ROAD_R - CAR_W - 6);

        distance += speed * 0.12;
        laneOffset = (laneOffset + speed) % 40;
        updateScore();

        spawnTimer -= 1;
        if (spawnTimer <= 0) {
          spawnTraffic();
          spawnTimer = Math.max(28, 60 - speed * 3);
        }

        traffic.forEach((t) => (t.y += speed - t.speed + 2));
        traffic = traffic.filter((t) => t.y < H + CAR_H);

        for (const t of traffic) {
          if (
            player.x < t.x + CAR_W &&
            player.x + CAR_W > t.x &&
            player.y < t.y + CAR_H &&
            player.y + CAR_H > t.y
          ) {
            gameOver = true;
          }
        }
      }

      function drawCar(x, y, body, windshield) {
        ctx.fillStyle = body;
        ctx.shadowColor = body;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.roundRect(x, y, CAR_W, CAR_H, 8);
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.fillStyle = windshield;
        ctx.fillRect(x + 6, y + 10, CAR_W - 12, 14);
        ctx.fillRect(x + 6, y + CAR_H - 22, CAR_W - 12, 12);
      }

      function draw() {
        ctx.fillStyle = "#0a2a0a";
        ctx.fillRect(0, 0, W, H);

        ctx.fillStyle = "#1a1a2a";
        ctx.fillRect(ROAD_L, 0, ROAD_W, H);

        ctx.strokeStyle = "#ffe45e";
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(ROAD_L, 0);
        ctx.lineTo(ROAD_L, H);
        ctx.moveTo(ROAD_R, 0);
        ctx.lineTo(ROAD_R, H);
        ctx.stroke();

        ctx.strokeStyle = "#556";
        ctx.lineWidth = 4;
        ctx.setLineDash([22, 22]);
        ctx.lineDashOffset = -laneOffset;
        for (let i = 1; i < 3; i++) {
          const x = ROAD_L + (ROAD_W / 3) * i;
          ctx.beginPath();
          ctx.moveTo(x, 0);
          ctx.lineTo(x, H);
          ctx.stroke();
        }
        ctx.setLineDash([]);

        traffic.forEach((t) => drawCar(t.x, t.y, t.color, "#0b0b16"));
        drawCar(player.x, player.y, "#ff2e88", "#0b0b16");

        if (gameOver) {
          ctx.fillStyle = "rgba(0,0,0,0.7)";
          ctx.fillRect(0, 0, W, H);
          ctx.fillStyle = "#ffe45e";
          ctx.font = "bold 28px Consolas, monospace";
          ctx.textAlign = "center";
          ctx.fillText("CRASH !", W / 2, H / 2 - 10);
          ctx.font = "16px Consolas, monospace";
          ctx.fillText(`Distance : ${Math.floor(distance)} m — Espace pour rejouer`, W / 2, H / 2 + 24);
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
