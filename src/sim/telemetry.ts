import { currentElements } from '../physics/derived';
import { totalEnergy } from '../physics/nbody';
import type { Simulation } from './Simulation';

export interface BodySeries {
  id: string;
  name: string;
  /** Masse au dernier échantillon (sert à choisir les séries affichées) */
  mass: number;
  /** Présent au dernier échantillon */
  alive: boolean;
  eccentricity: number[];
  semiMajorAxis: number[];
}

/** Nombre maximal d'échantillons conservés ; au-delà, on garde un point sur deux. */
export const MAX_SAMPLES = 600;
/** Nombre maximal de corps suivis (les plus massifs). */
const MAX_TRACKED = 40;

/**
 * Historique des grandeurs globales et orbitales d'une simulation. Tout
 * l'historique est conservé : quand le tampon est plein, sa résolution est
 * divisée par deux.
 */
export class Telemetry {
  times: number[] = [];
  /** Dérive relative de l'énergie totale, ΔE/E₀ (en %) */
  energyDrift: number[] = [];
  /** Instants où la structure du système a changé (collision, édition…) */
  markers: number[] = [];
  bodies = new Map<string, BodySeries>();
  /** Incrémenté à chaque nouvel échantillon */
  revision = 0;
  /** Incrémenté à chaque remise à zéro de l'historique */
  generation = 0;

  private e0: number | null = null;
  private epoch = -1;
  private lastVersion = -1;
  private lastTime = -1;

  reset(): void {
    this.times = [];
    this.energyDrift = [];
    this.markers = [];
    this.bodies.clear();
    this.e0 = null;
    this.lastTime = -1;
    this.revision += 1;
    this.generation += 1;
  }

  record(sim: Simulation): void {
    if (sim.epoch !== this.epoch) {
      this.reset();
      this.epoch = sim.epoch;
      this.lastVersion = sim.version;
    }
    if (sim.time === this.lastTime || sim.bodies.length < 2) return;
    if (sim.version !== this.lastVersion && this.times.length > 0) {
      // Les changements de structure font sauter l'énergie : on les signale.
      this.markers.push(sim.time);
    }
    this.lastVersion = sim.version;
    this.lastTime = sim.time;

    const energy = totalEnergy(sim.bodies);
    if (this.e0 === null) this.e0 = energy;
    const index = this.times.length;
    this.times.push(sim.time);
    this.energyDrift.push(((energy - this.e0) / Math.abs(this.e0)) * 100);

    const candidates = sim.bodies
      .filter((b) => b.kind === 'planet' || (b.kind === 'star' && b.parentId))
      .sort((a, b) => b.mass - a.mass)
      .slice(0, MAX_TRACKED);
    for (const s of this.bodies.values()) s.alive = false;
    for (const b of candidates) {
      const frame = sim.frameOf(b);
      if (!frame) continue;
      let s = this.bodies.get(b.id);
      if (!s) {
        s = { id: b.id, name: b.name, mass: b.mass, alive: true, eccentricity: new Array(index).fill(NaN), semiMajorAxis: new Array(index).fill(NaN) };
        this.bodies.set(b.id, s);
      }
      const el = currentElements(b, frame);
      const bound = el.a > 0 && Number.isFinite(el.a) && el.e < 1;
      s.name = b.name;
      s.mass = b.mass;
      s.alive = true;
      s.eccentricity.push(bound ? el.e : NaN);
      s.semiMajorAxis.push(bound ? el.a : NaN);
    }
    for (const s of this.bodies.values()) {
      if (s.eccentricity.length < index + 1) {
        s.eccentricity.push(NaN);
        s.semiMajorAxis.push(NaN);
      }
    }

    if (this.times.length > MAX_SAMPLES) this.decimate();
    this.revision += 1;
  }

  private decimate(): void {
    const keep = <T,>(arr: T[]) => arr.filter((_, k) => k % 2 === 0 || k === arr.length - 1);
    this.times = keep(this.times);
    this.energyDrift = keep(this.energyDrift);
    for (const s of this.bodies.values()) {
      s.eccentricity = keep(s.eccentricity);
      s.semiMajorAxis = keep(s.semiMajorAxis);
    }
  }
}
