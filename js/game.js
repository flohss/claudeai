import {
  SHAPES,
  LINE_COLORS,
  STATION_RADIUS,
  STATION_HIT_MARGIN,
  STATION_MIN_SPACING,
  TRAIN_SPEED,
  TRAIN_MAX_CARS,
  INITIAL_LINES_MAX,
  INITIAL_TRAIN_POOL,
  INITIAL_STATIONS,
  STATION_SPAWN_INTERVAL,
  PASSENGER_SPAWN_INTERVAL,
  MILESTONE_SCORE_STEP,
  LINE_OFFSET_GAP,
} from "./constants.js";
import { rand, choice, dist, clamp, pathForShape } from "./utils.js";
import { Station, Passenger, Line, Train } from "./entities.js";

const MILESTONE_CYCLE = ["train", "line", "capacity"];

export class Game {
  constructor(canvas, ui) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.ui = ui;
    this.resize();
    window.addEventListener("resize", () => this.resize());

    this.state = "start";
    this.reset();
  }

  resize() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  reset() {
    this.stations = [];
    this.lines = [];
    this.floaters = [];
    this.score = 0;
    this.elapsed = 0;
    this.linesMax = INITIAL_LINES_MAX;
    this.trainPool = INITIAL_TRAIN_POOL;
    this.milestoneIndex = 0;
    this.nextMilestoneScore = MILESTONE_SCORE_STEP;
    this.nextStationSpawn = rand(3, 6);
    this.nextPassengerSpawn = rand(...PASSENGER_SPAWN_INTERVAL);

    this.draft = null; // { line, extending, fromStart, points: [Station,...] }
    this.pointer = null;
    this.usedShapes = new Set();

    for (let i = 0; i < INITIAL_STATIONS; i++) this.spawnStation();
    this.updateUI();
  }

  start() {
    this.state = "playing";
  }

  restart() {
    this.reset();
    this.start();
  }

  // ---------- spawning ----------

  randomStationPosition() {
    const margin = 60;
    for (let attempt = 0; attempt < 60; attempt++) {
      const x = rand(margin, this.canvas.width - margin);
      const y = rand(margin + 40, this.canvas.height - margin - 60);
      if (this.stations.every((s) => dist(s, { x, y }) >= STATION_MIN_SPACING)) {
        return { x, y };
      }
    }
    return { x: rand(margin, this.canvas.width - margin), y: rand(margin, this.canvas.height - margin) };
  }

  pickShape() {
    const unused = SHAPES.filter((s) => !this.usedShapes.has(s));
    if (unused.length) {
      const s = choice(unused);
      this.usedShapes.add(s);
      return s;
    }
    return choice(SHAPES);
  }

  spawnStation() {
    const { x, y } = this.randomStationPosition();
    const shape = this.pickShape();
    this.stations.push(new Station(x, y, shape));
  }

  spawnPassenger() {
    if (!this.stations.length) return;
    const station = choice(this.stations);
    const otherShapes = SHAPES.filter((s) => s !== station.shape);
    const desired = choice(otherShapes);
    station.waiting.push(new Passenger(desired));
  }

  // ---------- upgrades ----------

  grantMilestone() {
    const kind = MILESTONE_CYCLE[this.milestoneIndex % MILESTONE_CYCLE.length];
    this.milestoneIndex++;

    if (kind === "train") {
      this.trainPool++;
      const emptyLine = this.lines.find((l) => l.trains.length === 0 && l.stations.length >= 2);
      if (emptyLine) this.assignTrain(emptyLine);
      this.toast("New train ready");
    } else if (kind === "line") {
      this.linesMax++;
      this.toast("New line available");
    } else {
      const candidates = this.lines.filter((l) => l.trains.some((t) => t.cars < TRAIN_MAX_CARS));
      if (candidates.length) {
        const line = choice(candidates);
        const train = line.trains.find((t) => t.cars < TRAIN_MAX_CARS);
        train.cars++;
        this.toast("Extra carriage added");
      } else {
        this.trainPool++;
        this.toast("New train ready");
      }
    }
  }

  toast(text) {
    if (this.ui && this.ui.toast) this.ui.toast(text);
  }

  assignTrain(line) {
    if (this.trainPool <= 0) return false;
    this.trainPool--;
    line.trains.push(new Train(line));
    return true;
  }

  // ---------- line building ----------

  hitTestStation(x, y) {
    let best = null;
    let bestD = Infinity;
    for (const s of this.stations) {
      const d = dist(s, { x, y });
      if (d <= s.radius + STATION_HIT_MARGIN && d < bestD) {
        best = s;
        bestD = d;
      }
    }
    return best;
  }

  findExtendableLine(station) {
    for (const line of this.lines) {
      if (line.stations.length < 2) continue;
      if (line.stations[0] === station) return { line, fromStart: true };
      if (line.stations[line.stations.length - 1] === station) return { line, fromStart: false };
    }
    return null;
  }

  beginDraftAt(x, y) {
    const station = this.hitTestStation(x, y);
    if (!station) return;

    const extend = this.findExtendableLine(station);
    if (extend) {
      this.draft = { line: extend.line, extending: true, fromStart: extend.fromStart, points: [station] };
      return;
    }

    if (this.lines.length >= this.linesMax) return;
    const usedColors = new Set(this.lines.map((l) => l.color));
    const color = LINE_COLORS.find((c) => !usedColors.has(c)) || choice(LINE_COLORS);
    this.draft = { line: null, color, extending: false, points: [station] };
  }

  updateDraft(x, y) {
    this.pointer = { x, y };
    if (!this.draft) return;
    const station = this.hitTestStation(x, y);
    if (!station) return;
    const pts = this.draft.points;
    if (pts[pts.length - 1] === station) return;
    if (pts.length >= 2 && pts[pts.length - 2] === station) {
      pts.pop();
      return;
    }
    if (!pts.includes(station)) pts.push(station);
  }

  endDraft() {
    if (!this.draft) return;
    const { points } = this.draft;

    if (this.draft.extending && points.length >= 2) {
      const line = this.draft.line;
      const newStations = points.slice(1);
      if (this.draft.fromStart) {
        for (const s of newStations) line.addStationAtStart(s);
      } else {
        for (const s of newStations) line.addStationAtEnd(s);
      }
      if (line.trains.length === 0) this.assignTrain(line);
    } else if (!this.draft.extending && points.length >= 2) {
      const line = new Line(this.draft.color);
      for (const s of points) line.addStationAtEnd(s);
      this.lines.push(line);
      this.assignTrain(line);
    }

    this.draft = null;
    this.updateUI();
  }

  cancelDraft() {
    this.draft = null;
  }

  deleteLine(lineId) {
    const idx = this.lines.findIndex((l) => l.id === lineId);
    if (idx === -1) return;
    const line = this.lines[idx];
    this.trainPool += line.trains.length;
    this.lines.splice(idx, 1);
    this.updateUI();
  }

  addTrainToLine(lineId) {
    const line = this.lines.find((l) => l.id === lineId);
    if (!line || this.trainPool <= 0) return;
    this.assignTrain(line);
    this.updateUI();
  }

  // ---------- update ----------

  update(dt) {
    if (this.state !== "playing") return;
    this.elapsed += dt;

    this.nextStationSpawn -= dt;
    if (this.nextStationSpawn <= 0) {
      this.spawnStation();
      this.nextStationSpawn = rand(...STATION_SPAWN_INTERVAL);
    }

    this.nextPassengerSpawn -= dt;
    if (this.nextPassengerSpawn <= 0) {
      this.spawnPassenger();
      this.nextPassengerSpawn = rand(...PASSENGER_SPAWN_INTERVAL);
    }

    for (const line of this.lines) {
      for (const train of line.trains) {
        train.update(dt, TRAIN_SPEED, (station, t) => this.handleArrival(station, t));
      }
    }

    for (const station of this.stations) {
      if (station.update(dt)) {
        this.gameOver();
        return;
      }
    }

    if (this.score >= this.nextMilestoneScore) {
      this.grantMilestone();
      this.nextMilestoneScore += MILESTONE_SCORE_STEP;
    }

    for (let i = this.floaters.length - 1; i >= 0; i--) {
      const f = this.floaters[i];
      f.life -= dt;
      f.y -= dt * 22;
      if (f.life <= 0) this.floaters.splice(i, 1);
    }

    this.updateUI();
  }

  handleArrival(station, train) {
    const delivered = [];
    train.passengers = train.passengers.filter((p) => {
      if (p.desiredShape === station.shape) {
        delivered.push(p);
        return false;
      }
      return true;
    });
    if (delivered.length) {
      this.score += delivered.length;
      this.floaters.push({ x: station.x, y: station.y - station.radius - 6, life: 1, text: `+${delivered.length}` });
    }

    const remainingCapacity = train.capacity - train.passengers.length;
    if (remainingCapacity > 0 && station.waiting.length) {
      const boarding = [];
      station.waiting = station.waiting.filter((p) => {
        if (boarding.length >= remainingCapacity) return true;
        if (train.line.servicesShape(p.desiredShape)) {
          boarding.push(p);
          return false;
        }
        return true;
      });
      train.passengers.push(...boarding);
    }
  }

  gameOver() {
    this.state = "gameover";
    if (this.ui && this.ui.gameOver) this.ui.gameOver(this.score, this.elapsed);
  }

  // ---------- rendering ----------

  computeLineOffsets() {
    const edgeMap = new Map();
    for (const line of this.lines) {
      for (let i = 0; i < line.stations.length - 1; i++) {
        const a = line.stations[i];
        const b = line.stations[i + 1];
        const key = a.id < b.id ? `${a.id}-${b.id}` : `${b.id}-${a.id}`;
        if (!edgeMap.has(key)) edgeMap.set(key, []);
        const arr = edgeMap.get(key);
        if (!arr.includes(line.id)) arr.push(line.id);
      }
    }
    return edgeMap;
  }

  render() {
    const { ctx, canvas } = this;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#0e1420";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const edgeMap = this.computeLineOffsets();

    for (const line of this.lines) {
      this.renderLine(line, edgeMap);
    }

    if (this.draft && this.draft.points.length) {
      ctx.save();
      ctx.strokeStyle = this.draft.extending ? this.draft.line.color : this.draft.color;
      ctx.globalAlpha = 0.55;
      ctx.lineWidth = 6;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      const pts = this.draft.points;
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i].x, pts[i].y);
      if (this.pointer) ctx.lineTo(this.pointer.x, this.pointer.y);
      ctx.stroke();
      ctx.restore();
    }

    for (const line of this.lines) {
      for (const train of line.trains) this.renderTrain(train);
    }

    for (const station of this.stations) this.renderStation(station);

    for (const f of this.floaters) {
      ctx.save();
      ctx.globalAlpha = clamp(f.life, 0, 1);
      ctx.fillStyle = "#7CFC9A";
      ctx.font = "bold 14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(f.text, f.x, f.y);
      ctx.restore();
    }
  }

  renderLine(line, edgeMap) {
    const { ctx } = this;
    if (line.stations.length < 2) return;
    ctx.save();
    ctx.strokeStyle = line.color;
    ctx.lineWidth = 6;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (let i = 0; i < line.stations.length - 1; i++) {
      const a = line.stations[i];
      const b = line.stations[i + 1];
      const key = a.id < b.id ? `${a.id}-${b.id}` : `${b.id}-${a.id}`;
      const group = edgeMap.get(key) || [line.id];
      const k = group.length;
      const idx = group.indexOf(line.id);
      const offset = (idx - (k - 1) / 2) * LINE_OFFSET_GAP;

      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const len = Math.hypot(dx, dy) || 1;
      const nx = (-dy / len) * offset;
      const ny = (dx / len) * offset;

      ctx.beginPath();
      ctx.moveTo(a.x + nx, a.y + ny);
      ctx.lineTo(b.x + nx, b.y + ny);
      ctx.stroke();
    }
    ctx.restore();
  }

  renderStation(station) {
    const { ctx } = this;
    const overcrowded = station.isOvercrowded();
    ctx.save();
    ctx.lineWidth = 3;
    ctx.strokeStyle = overcrowded ? "#ff5b5b" : "#e8edf5";
    ctx.fillStyle = "#0e1420";
    pathForShape(ctx, station.shape, station.x, station.y, station.radius);
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    const n = station.waiting.length;
    if (n > 0) {
      const cols = 5;
      const spacing = 7;
      ctx.save();
      for (let i = 0; i < Math.min(n, 15); i++) {
        const col = i % cols;
        const row = Math.floor(i / cols);
        const px = station.x - station.radius - 14 - (cols - 1 - col) * spacing;
        const py = station.y - station.radius + row * spacing;
        ctx.fillStyle = overcrowded ? "#ff5b5b" : "#9db4d1";
        ctx.beginPath();
        ctx.arc(px, py, 2.4, 0, Math.PI * 2);
        ctx.fill();
      }
      if (n > 15) {
        ctx.fillStyle = "#ff5b5b";
        ctx.font = "bold 11px sans-serif";
        ctx.fillText(`+${n - 15}`, station.x - station.radius - 44, station.y - station.radius + 20);
      }
      ctx.restore();
    }
  }

  renderTrain(train) {
    const { ctx } = this;
    const p = train.currentPoint();
    const idx = Math.min(Math.max(p.segment, 0), train.line.stations.length - 2);
    const a = train.line.stations[idx];
    const b = train.line.stations[idx + 1];
    const angle = Math.atan2(b.y - a.y, b.x - a.x);

    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(angle);
    ctx.fillStyle = train.line.color;
    ctx.strokeStyle = "#0e1420";
    ctx.lineWidth = 1.5;
    const w = 16 + (train.cars - 1) * 10;
    const h = 10;
    ctx.beginPath();
    ctx.roundRect(-w / 2, -h / 2, w, h, 3);
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    if (train.passengers.length > 0) {
      ctx.save();
      ctx.fillStyle = "#fff";
      ctx.font = "10px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(`${train.passengers.length}/${train.capacity}`, p.x, p.y - 12);
      ctx.restore();
    }
  }

  updateUI() {
    if (this.ui && this.ui.update) this.ui.update(this);
  }
}
