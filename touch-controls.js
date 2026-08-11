(function () {
  const isTouch = "ontouchstart" in window || navigator.maxTouchPoints > 0;
  if (!isTouch) return;

  const pad = document.createElement("div");
  pad.id = "touchControls";
  pad.className = "touch-controls hidden";
  pad.innerHTML = `
    <div class="dpad">
      <button class="pad-btn dpad-up" type="button" data-key="ArrowUp" aria-label="Haut">▲</button>
      <button class="pad-btn dpad-left" type="button" data-key="ArrowLeft" aria-label="Gauche">◀</button>
      <button class="pad-btn dpad-right" type="button" data-key="ArrowRight" aria-label="Droite">▶</button>
      <button class="pad-btn dpad-down" type="button" data-key="ArrowDown" aria-label="Bas">▼</button>
    </div>
    <button class="pad-btn action-btn" type="button" data-key=" " aria-label="Action">●</button>
  `;
  document.body.appendChild(pad);

  const REPEAT_DELAY = 280;
  const REPEAT_INTERVAL = 110;

  function bindButton(btn) {
    const key = btn.dataset.key;
    let repeatTimer = null;
    let initialTimer = null;

    function fireKeydown() {
      window.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    }
    function fireKeyup() {
      window.dispatchEvent(new KeyboardEvent("keyup", { key, bubbles: true }));
    }

    function start(e) {
      e.preventDefault();
      btn.classList.add("active");
      fireKeydown();
      clearTimeout(initialTimer);
      clearInterval(repeatTimer);
      initialTimer = setTimeout(() => {
        repeatTimer = setInterval(fireKeydown, REPEAT_INTERVAL);
      }, REPEAT_DELAY);
    }
    function end(e) {
      e.preventDefault();
      btn.classList.remove("active");
      clearTimeout(initialTimer);
      clearInterval(repeatTimer);
      fireKeyup();
    }

    btn.addEventListener("touchstart", start, { passive: false });
    btn.addEventListener("touchend", end, { passive: false });
    btn.addEventListener("touchcancel", end, { passive: false });
  }

  pad.querySelectorAll(".pad-btn").forEach(bindButton);

  window.__setTouchControlsVisible = function (visible) {
    pad.classList.toggle("hidden", !visible);
    document.body.classList.toggle("pad-active", visible);
  };
})();
