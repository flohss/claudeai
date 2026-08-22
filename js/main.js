import { Game } from "./game.js";
import { attachInput } from "./input.js";
import { createUI } from "./ui.js";

const canvas = document.getElementById("game-canvas");
const ui = createUI();
const game = new Game(canvas, ui);
attachInput(canvas, game);
window.__game = game;

const startOverlay = document.getElementById("start-overlay");
const startBtn = document.getElementById("start-btn");
const gameoverOverlay = document.getElementById("gameover-overlay");
const restartBtn = document.getElementById("restart-btn");

startBtn.addEventListener("click", () => {
  startOverlay.classList.add("hidden");
  game.start();
});

restartBtn.addEventListener("click", () => {
  gameoverOverlay.classList.add("hidden");
  game.restart();
});

let lastTime = performance.now();
function loop(now) {
  const dt = Math.min(0.05, (now - lastTime) / 1000);
  lastTime = now;
  game.update(dt);
  game.render();
  requestAnimationFrame(loop);
}
requestAnimationFrame(loop);
