import {
  STATION_CAPACITY,
  STATION_OVERCROWD_TIME,
  STATION_RADIUS,
  TRAIN_CAPACITY_PER_CAR,
  DWELL_TIME,
} from "./constants.js";
import { dist } from "./utils.js";

let nextId = 1;
function id() {
  return nextId++;
}

export class Station {
  constructor(x, y, shape) {
    this.id = id();
    this.x = x;
    this.y = y;
    this.shape = shape;
    this.radius = STATION_RADIUS;
    this.waiting = [];
    this.overcrowdTimer = 0;
  }

  isOvercrowded() {
    return this.waiting.length > STATION_CAPACITY;
  }

  update(dt) {
    if (this.isOvercrowded()) {
      this.overcrowdTimer += dt;
      return this.overcrowdTimer >= STATION_OVERCROWD_TIME;
    }
    this.overcrowdTimer = Math.max(0, this.overcrowdTimer - dt * 2);
    return false;
  }
}

export class Passenger {
  constructor(desiredShape) {
    this.id = id();
    this.desiredShape = desiredShape;
  }
}

export class Line {
  constructor(color) {
    this.id = id();
    this.color = color;
    this.stations = [];
    this.trains = [];
    this.cumulative = [0];
    this.totalLength = 0;
  }

  addStationAtEnd(station) {
    if (this.stations[this.stations.length - 1] === station) return;
    this.stations.push(station);
    this.recompute();
  }

  addStationAtStart(station) {
    if (this.stations[0] === station) return;
    this.stations.unshift(station);
    this.recompute(true);
  }

  recompute(prepended = false) {
    const oldTotal = this.totalLength;
    const cumulative = [0];
    for (let i = 1; i < this.stations.length; i++) {
      const d = dist(this.stations[i - 1], this.stations[i]);
      cumulative.push(cumulative[i - 1] + d);
    }
    this.cumulative = cumulative;
    this.totalLength = cumulative[cumulative.length - 1] || 0;

    if (prepended) {
      const added = this.totalLength - oldTotal;
      for (const train of this.trains) {
        train.progress += added;
      }
    }
  }

  servicesShape(shape) {
    return this.stations.some((s) => s.shape === shape);
  }

  pointAtProgress(progress) {
    const c = this.cumulative;
    if (this.stations.length === 1) return { x: this.stations[0].x, y: this.stations[0].y, segment: 0 };
    let seg = 0;
    for (let i = 0; i < c.length - 1; i++) {
      if (progress >= c[i] && progress <= c[i + 1]) {
        seg = i;
        break;
      }
      seg = i;
    }
    const segLen = c[seg + 1] - c[seg] || 1;
    const t = (progress - c[seg]) / segLen;
    const a = this.stations[seg];
    const b = this.stations[seg + 1];
    return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, segment: seg };
  }
}

export class Train {
  constructor(line) {
    this.id = id();
    this.line = line;
    this.progress = 0;
    this.dir = 1;
    this.cars = 1;
    this.passengers = [];
    this.dwellTimer = 0;
    this.dwellStationIndex = null;
  }

  get capacity() {
    return this.cars * TRAIN_CAPACITY_PER_CAR;
  }

  currentPoint() {
    return this.line.pointAtProgress(this.progress);
  }

  update(dt, speed, onArrive) {
    if (this.line.stations.length < 2) return;

    if (this.dwellTimer > 0) {
      this.dwellTimer -= dt;
      return;
    }

    const c = this.line.cumulative;
    const prev = this.progress;
    let next = prev + this.dir * speed * dt;

    // find nearest station threshold crossed in direction of travel
    let crossedIndex = null;
    if (this.dir > 0) {
      for (let i = 0; i < c.length; i++) {
        if (c[i] > prev + 1e-6 && c[i] <= next + 1e-6) {
          crossedIndex = i;
          next = c[i];
          break;
        }
      }
    } else {
      for (let i = c.length - 1; i >= 0; i--) {
        if (c[i] < prev - 1e-6 && c[i] >= next - 1e-6) {
          crossedIndex = i;
          next = c[i];
          break;
        }
      }
    }

    this.progress = Math.max(0, Math.min(this.line.totalLength, next));

    if (crossedIndex !== null) {
      this.dwellTimer = DWELL_TIME;
      this.dwellStationIndex = crossedIndex;
      if (crossedIndex === c.length - 1) this.dir = -1;
      else if (crossedIndex === 0) this.dir = 1;
      onArrive(this.line.stations[crossedIndex], this);
    }
  }
}
