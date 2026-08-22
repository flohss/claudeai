export function attachInput(canvas, game) {
  function toLocal(evt) {
    const rect = canvas.getBoundingClientRect();
    return { x: evt.clientX - rect.left, y: evt.clientY - rect.top };
  }

  let dragging = false;

  canvas.addEventListener("pointerdown", (evt) => {
    if (game.state !== "playing") return;
    const { x, y } = toLocal(evt);
    game.beginDraftAt(x, y);
    if (game.draft) {
      dragging = true;
      canvas.setPointerCapture(evt.pointerId);
    }
  });

  canvas.addEventListener("pointermove", (evt) => {
    const { x, y } = toLocal(evt);
    if (dragging) game.updateDraft(x, y);
  });

  canvas.addEventListener("pointerup", (evt) => {
    if (dragging) {
      game.endDraft();
      dragging = false;
    }
  });

  canvas.addEventListener("pointercancel", () => {
    if (dragging) {
      game.cancelDraft();
      dragging = false;
    }
  });
}
