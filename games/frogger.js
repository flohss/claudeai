(function () {
  window.ARCADE_GAMES = window.ARCADE_GAMES || [];

  window.ARCADE_GAMES.push({
    id: "frogger",
    name: "Frogger",
    icon: "🐸",
    accent: "#84cc16",
    description: "Traverse la route et la rivière sans te faire écraser, 1981.",
    hint: "Flèches pour sauter case par case. Atteins les 5 nids sans te noyer.",

    start(canvas, setScore) {
      const ctx = canvas.getContext("2d");
      const W = canvas.width;
      const H = canvas.height;
      const CELL = 28;
      const COLS = Math.floor(W / CELL);
      const ROWS = Math.floor(H / CELL);
      const OFFSET_X = (W - COLS * CELL) / 2;

      const HOME_ROW = 1;
      const RIVER_ROWS = [3, 4, 5, 6];
      const MEDIAN_ROW = 7;
      const ROAD_ROWS = [8, 9, 10, 11, 12];
      const START_ROW = ROWS - 2;

      let frog, lanes, homes, lives, score, gameOver, won, moveAcc;

      function buildLanes() {
        const arr = {};
        RIVER_ROWS.forEach((r, i) => {
          const dir = i % 2 === 0 ? 1 : -1;
          const speed = 0.9 + i * 0.25;
          const gap = 170;
          const objW = 90;
          const objs = [];
          for (let x = -gap; x < W + gap; x += gap) objs.push({ x });
          arr[r] = { dir, speed, objW, objs, kind: "log" };
        });
        ROAD_ROWS.forEach((r, i) => {
          const dir = i % 2 === 0 ? -1 : 1;
          const speed = 1.3 + i * 0.35;
          const gap = 150 - i * 8;
          const objW = 40;
          const objs = [];
          for (let x = -gap; x < W + gap; x += gap) objs.push({ x: x + i * 37 });
          arr[r] = { dir, speed, objW, objs, kind: "car" };
        });
        return arr;
      }

      function resetFrog() {
        frog = { col: Math.floor(COLS / 2), row: START_ROW, offsetX: 0, onLog: null };
      }

      function reset() {
        lanes = buildLanes();
        homes = [false, false, false, false, false];
        lives = 3;
        score = 0;
        gameOver = false;
        won = false;
        moveAcc = 0;
        resetFrog();
        updateScore();
      }

      function updateScore() {
        setScore(`SCORE ${score}  •  VIES ${lives}  •  NIDS ${homes.filter(Boolean).length}/5`);
      }

      reset();

      const keyMap = {
        ArrowUp: { dc: 0, dr: -1 }, w: { dc: 0, dr: -1 }, W: { dc: 0, dr: -1 },
        ArrowDown: { dc: 0, dr: 1 }, s: { dc: 0, dr: 1 }, S: { dc: 0, dr: 1 },
        ArrowLeft: { dc: -1, dr: 0 }, a: { dc: -1, dr: 0 }, A: { dc: -1, dr: 0 },
        ArrowRight: { dc: 1, dr: 0 }, d: { dc: 1, dr: 0 }, D: { dc: 1, dr: 0 },
      };

      function onKeyDown(e) {
        if (gameOver && e.key === " ") {
          reset();
          return;
        }
        const mv = keyMap[e.key];
        if (!mv || gameOver) return;
        const newCol = clamp(frog.col + mv.dc, 0, COLS - 1);
        const newRow = clamp(frog.row + mv.dr, HOME_ROW, START_ROW);
        if (mv.dr < 0 && newRow < frog.row) score += 5;
        frog.col = newCol;
        frog.row = newRow;
        frog.offsetX = 0;
        updateScore();
      }
      window.addEventListener("keydown", onKeyDown);

      function clamp(v, min, max) {
        return Math.max(min, Math.min(max, v));
      }

      function loseLife() {
        lives -= 1;
        updateScore();
        if (lives <= 0) {
          gameOver = true;
        } else {
          resetFrog();
        }
      }

      function frogX() {
        return OFFSET_X + frog.col * CELL + frog.offsetX;
      }

      function update(dt) {
        if (gameOver) return;

        for (const r in lanes) {
          const lane = lanes[r];
          lane.objs.forEach((o) => {
            o.x += lane.dir * lane.speed;
            if (lane.dir > 0 && o.x > W + 100) o.x -= W + 200;
            if (lane.dir < 0 && o.x < -200) o.x += W + 200;
          });
        }

        const laneRoad = lanes[frog.row];
        if (ROAD_ROWS.includes(frog.row) && laneRoad) {
          const fx = frogX();
          for (const o of laneRoad.objs) {
            if (fx + CELL * 0.7 > o.x && fx + CELL * 0.3 < o.x + laneRoad.objW) {
              loseLife();
              return;
            }
          }
        }

        if (RIVER_ROWS.includes(frog.row)) {
          const laneRiver = lanes[frog.row];
          const fx = frogX();
          let onLog = false;
          for (const o of laneRiver.objs) {
            if (fx + CELL * 0.6 > o.x && fx + CELL * 0.4 < o.x + laneRiver.objW) {
              onLog = true;
              frog.offsetX += laneRiver.dir * laneRiver.speed;
              break;
            }
          }
          if (!onLog) {
            loseLife();
            return;
          }
          const absX = frogX();
          if (absX < -CELL || absX > W) {
            loseLife();
            return;
          }
        }

        if (frog.row === HOME_ROW) {
          const fx = frogX() + CELL / 2;
          const slotW = W / homes.length;
          const slotIndex = clamp(Math.floor(fx / slotW), 0, homes.length - 1);
          if (!homes[slotIndex]) {
            homes[slotIndex] = true;
            score += 50;
            updateScore();
            if (homes.every(Boolean)) {
              gameOver = true;
              won = true;
            } else {
              resetFrog();
            }
          } else {
            loseLife();
          }
        }
      }

      function draw() {
        ctx.fillStyle = "#0a1a0a";
        ctx.fillRect(0, 0, W, H);

        ctx.fillStyle = "#123a5a";
        RIVER_ROWS.forEach((r) => ctx.fillRect(0, r * CELL, W, CELL));

        ctx.fillStyle = "#222";
        ROAD_ROWS.forEach((r) => ctx.fillRect(0, r * CELL, W, CELL));

        ctx.fillStyle = "#1a3a1a";
        ctx.fillRect(0, MEDIAN_ROW * CELL, W, CELL);
        ctx.fillRect(0, START_ROW * CELL, W, CELL * 2);
        ctx.fillRect(0, 0, W, CELL);

        const slotW = W / homes.length;
        homes.forEach((filled, i) => {
          ctx.fillStyle = filled ? "#3dff8a" : "#0d2a0d";
          ctx.shadowColor = "#3dff8a";
          ctx.shadowBlur = filled ? 8 : 0;
          ctx.fillRect(i * slotW + 10, HOME_ROW * CELL + 4, slotW - 20, CELL - 8);
          ctx.shadowBlur = 0;
        });

        Object.entries(lanes).forEach(([r, lane]) => {
          ctx.fillStyle = lane.kind === "log" ? "#8a5a2e" : "#ff2e88";
          ctx.shadowColor = ctx.fillStyle;
          ctx.shadowBlur = 5;
          lane.objs.forEach((o) => {
            ctx.fillRect(o.x, r * CELL + 4, lane.objW, CELL - 8);
          });
        });
        ctx.shadowBlur = 0;

        ctx.fillStyle = "#3dff8a";
        ctx.shadowColor = "#3dff8a";
        ctx.shadowBlur = 10;
        ctx.fillRect(frogX() + 3, frog.row * CELL + 3, CELL - 6, CELL - 6);
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
