(() => {
  "use strict";

  const PALETTE = [
    "#000000", "#1d2b53", "#7e2553", "#008751",
    "#ab5236", "#5f574f", "#c2c3c7", "#fff1e8",
    "#ff004d", "#ffa300", "#ffec27", "#00e436",
    "#29adff", "#83769c", "#ff77a8", "#ffccaa",
    "#ffffff", "#c40000", "#e07a00", "#008000",
    "#00468c", "#6a1b9a", "#795548", "#607d8b"
  ];

  const MAX_DISPLAY_PX = 576;
  const MIN_CELL_PX = 6;
  const MAX_HISTORY = 60;

  const canvas = document.getElementById("pixel-canvas");
  const ctx = canvas.getContext("2d");
  const paletteEl = document.getElementById("palette");
  const hexInput = document.getElementById("hex-input");
  const activeSwatch = document.getElementById("active-color-swatch");
  const svCanvas = document.getElementById("sv-canvas");
  const svCtx = svCanvas.getContext("2d");
  const svWrapper = document.getElementById("sv-wrapper");
  const svCursor = document.getElementById("sv-cursor");
  const hueRange = document.getElementById("hue-range");
  const gridSizeSelect = document.getElementById("grid-size");
  const gridLinesCheckbox = document.getElementById("grid-lines");
  const undoBtn = document.getElementById("undo-btn");
  const redoBtn = document.getElementById("redo-btn");
  const clearBtn = document.getElementById("clear-btn");
  const exportBtn = document.getElementById("export-btn");
  const toolButtons = Array.from(document.querySelectorAll(".tool-btn"));

  const state = {
    gridSize: 16,
    cellSize: 0,
    grid: [],
    tool: "pencil",
    activeColor: "#1d2b53",
    hsv: { h: 230, s: 74, v: 33 },
    isPointerDown: false,
    isSvDragging: false,
    history: [],
    historyIndex: -1,
  };

  // ---- Color conversions ----
  function hexToRgb(hex) {
    let h = hex.replace("#", "");
    if (h.length === 3) h = h.split("").map((c) => c + c).join("");
    const num = parseInt(h, 16);
    return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
  }

  function rgbToHex(r, g, b) {
    return "#" + [r, g, b].map((x) => Math.round(x).toString(16).padStart(2, "0")).join("");
  }

  function rgbToHsv(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const d = max - min;
    let h = 0;
    if (d !== 0) {
      if (max === r) h = ((g - b) / d) % 6;
      else if (max === g) h = (b - r) / d + 2;
      else h = (r - g) / d + 4;
      h *= 60;
      if (h < 0) h += 360;
    }
    const s = max === 0 ? 0 : d / max;
    return { h, s: s * 100, v: max * 100 };
  }

  function hsvToRgb(h, s, v) {
    s /= 100; v /= 100;
    const c = v * s;
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = v - c;
    let r = 0, g = 0, b = 0;
    if (h < 60) { r = c; g = x; b = 0; }
    else if (h < 120) { r = x; g = c; b = 0; }
    else if (h < 180) { r = 0; g = c; b = x; }
    else if (h < 240) { r = 0; g = x; b = c; }
    else if (h < 300) { r = x; g = 0; b = c; }
    else { r = c; g = 0; b = x; }
    return { r: (r + m) * 255, g: (g + m) * 255, b: (b + m) * 255 };
  }

  function hexToHsv(hex) {
    const { r, g, b } = hexToRgb(hex);
    return rgbToHsv(r, g, b);
  }

  function hsvToHex(h, s, v) {
    const { r, g, b } = hsvToRgb(h, s, v);
    return rgbToHex(r, g, b);
  }

  function makeBlankGrid(size) {
    return new Array(size * size).fill(null);
  }

  function idx(x, y) {
    return y * state.gridSize + x;
  }

  function computeCellSize(size) {
    return Math.max(MIN_CELL_PX, Math.floor(MAX_DISPLAY_PX / size));
  }

  function setupCanvasSize() {
    state.cellSize = computeCellSize(state.gridSize);
    const px = state.cellSize * state.gridSize;
    canvas.width = px;
    canvas.height = px;
    canvas.style.width = px + "px";
    canvas.style.height = px + "px";
  }

  function render() {
    const size = state.gridSize;
    const cs = state.cellSize;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const checkerLight = "#f4f4f4";
    const checkerDark = "#dcdcdc";
    const checkerCell = Math.max(4, Math.floor(cs / 2));

    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const color = state.grid[idx(x, y)];
        const px = x * cs;
        const py = y * cs;
        if (color) {
          ctx.fillStyle = color;
          ctx.fillRect(px, py, cs, cs);
        } else {
          for (let cy = 0; cy < cs; cy += checkerCell) {
            for (let cx = 0; cx < cs; cx += checkerCell) {
              const parity = (Math.floor((px + cx) / checkerCell) + Math.floor((py + cy) / checkerCell)) % 2;
              ctx.fillStyle = parity === 0 ? checkerLight : checkerDark;
              ctx.fillRect(px + cx, py + cy, Math.min(checkerCell, cs - cx), Math.min(checkerCell, cs - cy));
            }
          }
        }
      }
    }

    if (gridLinesCheckbox.checked) {
      ctx.strokeStyle = "rgba(0,0,0,0.15)";
      ctx.lineWidth = 1;
      for (let i = 0; i <= size; i++) {
        const pos = i * cs + 0.5;
        ctx.beginPath();
        ctx.moveTo(pos, 0);
        ctx.lineTo(pos, canvas.height);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, pos);
        ctx.lineTo(canvas.width, pos);
        ctx.stroke();
      }
    }
  }

  function buildPalette() {
    paletteEl.innerHTML = "";
    PALETTE.forEach((color) => {
      const btn = document.createElement("button");
      btn.className = "palette-swatch";
      btn.style.background = color;
      btn.title = color;
      btn.addEventListener("click", () => setActiveColor(color));
      paletteEl.appendChild(btn);
    });
    syncPaletteSelection();
  }

  function syncPaletteSelection() {
    Array.from(paletteEl.children).forEach((btn) => {
      btn.classList.toggle("selected", btn.style.background === hexToRgbCss(state.activeColor));
    });
  }

  function hexToRgbCss(hex) {
    const el = document.createElement("div");
    el.style.color = hex;
    document.body.appendChild(el);
    const rgb = getComputedStyle(el).color;
    document.body.removeChild(el);
    return rgb;
  }

  function setActiveColor(color, options = {}) {
    const { skipHsvSync = false } = options;
    state.activeColor = color;
    activeSwatch.style.background = color;
    hexInput.value = color;
    syncPaletteSelection();
    if (!skipHsvSync) {
      state.hsv = hexToHsv(color);
    }
    hueRange.value = String(Math.round(state.hsv.h));
    drawSvCanvas(state.hsv.h);
    updateSvCursorPosition();
  }

  function setActiveColorFromHsv(h, s, v) {
    state.hsv = { h, s, v };
    const hex = hsvToHex(h, s, v);
    setActiveColor(hex, { skipHsvSync: true });
  }

  function drawSvCanvas(hue) {
    const w = svCanvas.width;
    const h = svCanvas.height;
    svCtx.fillStyle = hsvToHex(hue, 100, 100);
    svCtx.fillRect(0, 0, w, h);

    const whiteGrad = svCtx.createLinearGradient(0, 0, w, 0);
    whiteGrad.addColorStop(0, "rgba(255,255,255,1)");
    whiteGrad.addColorStop(1, "rgba(255,255,255,0)");
    svCtx.fillStyle = whiteGrad;
    svCtx.fillRect(0, 0, w, h);

    const blackGrad = svCtx.createLinearGradient(0, 0, 0, h);
    blackGrad.addColorStop(0, "rgba(0,0,0,0)");
    blackGrad.addColorStop(1, "rgba(0,0,0,1)");
    svCtx.fillStyle = blackGrad;
    svCtx.fillRect(0, 0, w, h);
  }

  function updateSvCursorPosition() {
    const { s, v } = state.hsv;
    svCursor.style.left = s + "%";
    svCursor.style.top = (100 - v) + "%";
  }

  function pickFromSvEvent(evt) {
    const rect = svWrapper.getBoundingClientRect();
    const x = Math.min(Math.max(evt.clientX - rect.left, 0), rect.width);
    const y = Math.min(Math.max(evt.clientY - rect.top, 0), rect.height);
    const s = (x / rect.width) * 100;
    const v = 100 - (y / rect.height) * 100;
    setActiveColorFromHsv(state.hsv.h, s, v);
  }

  function setTool(tool) {
    state.tool = tool;
    toolButtons.forEach((btn) => btn.classList.toggle("active", btn.dataset.tool === tool));
  }

  function cellFromEvent(evt) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const x = Math.floor(((evt.clientX - rect.left) * scaleX) / state.cellSize);
    const y = Math.floor(((evt.clientY - rect.top) * scaleY) / state.cellSize);
    if (x < 0 || y < 0 || x >= state.gridSize || y >= state.gridSize) return null;
    return { x, y };
  }

  function paintAt(x, y, colorOverride) {
    const color = colorOverride !== undefined ? colorOverride : (state.tool === "eraser" ? null : state.activeColor);
    const i = idx(x, y);
    if (state.grid[i] === color) return false;
    state.grid[i] = color;
    return true;
  }

  function floodFill(x, y, targetColor, replacementColor) {
    if (targetColor === replacementColor) return;
    const size = state.gridSize;
    const stack = [[x, y]];
    while (stack.length) {
      const [cx, cy] = stack.pop();
      if (cx < 0 || cy < 0 || cx >= size || cy >= size) continue;
      const i = idx(cx, cy);
      if (state.grid[i] !== targetColor) continue;
      state.grid[i] = replacementColor;
      stack.push([cx + 1, cy], [cx - 1, cy], [cx, cy + 1], [cx, cy - 1]);
    }
  }

  function handlePointerAction(x, y, isStart) {
    if (state.tool === "pencil" || state.tool === "eraser") {
      const changed = paintAt(x, y);
      if (changed) render();
    } else if (state.tool === "bucket") {
      if (!isStart) return;
      const target = state.grid[idx(x, y)];
      const replacement = state.activeColor;
      floodFill(x, y, target, replacement);
      render();
      pushHistory();
    } else if (state.tool === "picker") {
      if (!isStart) return;
      const color = state.grid[idx(x, y)];
      if (color) setActiveColor(color);
    }
  }

  function pushHistory() {
    state.history = state.history.slice(0, state.historyIndex + 1);
    state.history.push(state.grid.slice());
    if (state.history.length > MAX_HISTORY) {
      state.history.shift();
    }
    state.historyIndex = state.history.length - 1;
    updateHistoryButtons();
  }

  function updateHistoryButtons() {
    undoBtn.disabled = state.historyIndex <= 0;
    redoBtn.disabled = state.historyIndex >= state.history.length - 1;
  }

  function undo() {
    if (state.historyIndex <= 0) return;
    state.historyIndex--;
    state.grid = state.history[state.historyIndex].slice();
    render();
    updateHistoryButtons();
  }

  function redo() {
    if (state.historyIndex >= state.history.length - 1) return;
    state.historyIndex++;
    state.grid = state.history[state.historyIndex].slice();
    render();
    updateHistoryButtons();
  }

  function resetGrid(size, pushToHistory = true) {
    state.gridSize = size;
    state.grid = makeBlankGrid(size);
    setupCanvasSize();
    render();
    if (pushToHistory) {
      state.history = [];
      state.historyIndex = -1;
      pushHistory();
    }
  }

  function exportPNG() {
    const size = state.gridSize;
    const off = document.createElement("canvas");
    off.width = size;
    off.height = size;
    const octx = off.getContext("2d");
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        const color = state.grid[idx(x, y)];
        if (color) {
          octx.fillStyle = color;
          octx.fillRect(x, y, 1, 1);
        }
      }
    }
    off.toBlob((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "pixel-art.png";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, "image/png");
  }

  // Event wiring
  toolButtons.forEach((btn) => {
    btn.addEventListener("click", () => setTool(btn.dataset.tool));
  });

  hueRange.addEventListener("input", (e) => {
    setActiveColorFromHsv(Number(e.target.value), state.hsv.s, state.hsv.v);
  });

  hexInput.addEventListener("change", (e) => {
    const raw = e.target.value.trim();
    const match = /^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$/.exec(raw);
    if (!match) {
      hexInput.value = state.activeColor;
      return;
    }
    setActiveColor("#" + match[1].toLowerCase().replace(/^([0-9a-f])([0-9a-f])([0-9a-f])$/, "$1$1$2$2$3$3"));
  });

  svWrapper.addEventListener("pointerdown", (e) => {
    state.isSvDragging = true;
    svWrapper.setPointerCapture(e.pointerId);
    pickFromSvEvent(e);
  });

  svWrapper.addEventListener("pointermove", (e) => {
    if (!state.isSvDragging) return;
    pickFromSvEvent(e);
  });

  window.addEventListener("pointerup", () => {
    state.isSvDragging = false;
  });

  gridSizeSelect.addEventListener("change", (e) => {
    const newSize = parseInt(e.target.value, 10);
    const hasContent = state.grid.some((c) => c !== null);
    if (hasContent && !confirm("Changer la taille de la grille effacera le dessin actuel. Continuer ?")) {
      e.target.value = String(state.gridSize);
      return;
    }
    resetGrid(newSize);
  });

  gridLinesCheckbox.addEventListener("change", render);

  clearBtn.addEventListener("click", () => {
    if (state.grid.some((c) => c !== null) && !confirm("Effacer tout le dessin ?")) return;
    state.grid = makeBlankGrid(state.gridSize);
    render();
    pushHistory();
  });

  undoBtn.addEventListener("click", undo);
  redoBtn.addEventListener("click", redo);
  exportBtn.addEventListener("click", exportPNG);

  document.addEventListener("keydown", (e) => {
    const mod = e.ctrlKey || e.metaKey;
    if (!mod) return;
    if (e.key.toLowerCase() === "z" && !e.shiftKey) {
      e.preventDefault();
      undo();
    } else if (e.key.toLowerCase() === "y" || (e.key.toLowerCase() === "z" && e.shiftKey)) {
      e.preventDefault();
      redo();
    }
  });

  canvas.addEventListener("pointerdown", (e) => {
    const cell = cellFromEvent(e);
    if (!cell) return;
    state.isPointerDown = true;
    canvas.setPointerCapture(e.pointerId);
    handlePointerAction(cell.x, cell.y, true);
  });

  canvas.addEventListener("pointermove", (e) => {
    if (!state.isPointerDown) return;
    const cell = cellFromEvent(e);
    if (!cell) return;
    if (state.tool === "pencil" || state.tool === "eraser") {
      handlePointerAction(cell.x, cell.y, false);
    }
  });

  window.addEventListener("pointerup", () => {
    if (!state.isPointerDown) return;
    state.isPointerDown = false;
    if (state.tool === "pencil" || state.tool === "eraser") {
      pushHistory();
    }
  });

  // Init
  buildPalette();
  setActiveColor(state.activeColor);
  setTool("pencil");
  resetGrid(state.gridSize);
})();
