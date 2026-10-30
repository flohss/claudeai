import { currentElements } from '../physics/derived';
import {
  computeAccelerations,
  findCollision,
  makeAccelerationBuffer,
  mergeBodies,
  recenter,
  verletStep,
} from '../physics/nbody';
import { elementsToState, hillRadius, mu, orbitalPeriod } from '../physics/orbits';
import { SPECTRAL_CLASSES, starPropsFor } from '../physics/stars';
import type { Body, OrbitalElements, SpectralClass } from '../physics/types';
import { DAYS_PER_YEAR, G, SUN_RADIUS_KM } from '../physics/units';
import { add, clone, distance, dot, sub, type Vec3 } from '../physics/vec3';

export interface SystemDefinition {
  name: string;
  bodies: Body[];
  /** Temps simulé (années). Absent = 0. */
  time?: number;
}

export interface SimEvent {
  time: number;
  kind: 'collision' | 'ejection' | 'evasion' | 'info';
  message: string;
}

export type BodyPatch = Partial<Pick<Body, 'name' | 'planetType' | 'mass' | 'radiusKm' | 'color' | 'albedo'>> & {
  elements?: OrbitalElements;
};

/** Distance au-delà de laquelle un corps non lié à l'étoile est considéré éjecté (UA). */
export const EJECTION_DISTANCE_AU = 1000;
const MAX_EVENTS = 50;

const cloneBody = (b: Body): Body => ({
  ...b,
  star: b.star ? { ...b.star } : undefined,
  elements: b.elements ? { ...b.elements } : null,
  position: clone(b.position),
  velocity: clone(b.velocity),
});

/** Trie les corps pour qu'un parent soit toujours avant ses satellites. */
export function orderByHierarchy(bodies: Body[]): Body[] {
  const ids = new Set(bodies.map((b) => b.id));
  const placed = new Set<string>();
  const result: Body[] = [];
  let remaining = bodies.slice();
  while (remaining.length > 0) {
    const next = remaining.filter((b) => !b.parentId || !ids.has(b.parentId) || placed.has(b.parentId));
    if (next.length === 0) throw new Error('Hiérarchie de corps invalide (cycle de parents).');
    for (const b of next) {
      result.push(b);
      placed.add(b.id);
    }
    remaining = remaining.filter((b) => !placed.has(b.id));
  }
  return result;
}

/**
 * État complet d'une simulation, indépendant du rendu et de React.
 * Les composants s'abonnent via `subscribe` ; `version` change à chaque
 * modification structurelle (ajout, édition, collision…), pas à chaque pas.
 */
export class Simulation {
  name = '';
  bodies: Body[] = [];
  /** Temps simulé (années) */
  time = 0;
  /** Vitesse demandée (jours simulés par seconde réelle) */
  speed = 20;
  paused = false;
  /** Vitesse réellement atteinte, limitée par le budget de calcul (jours/s) */
  effectiveSpeed = 0;
  events: SimEvent[] = [];
  version = 0;

  private acc: Vec3[] = [];
  private dtMax = 0.001;
  private initial: SystemDefinition = { name: '', bodies: [] };
  private listeners = new Set<() => void>();

  constructor(def?: SystemDefinition, placeFromElements = true) {
    if (def) this.load(def, placeFromElements);
  }

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getVersion = (): number => this.version;

  private changed(): void {
    this.version += 1;
    this.listeners.forEach((l) => l());
  }

  get star(): Body | undefined {
    return this.bodies.find((b) => b.kind === 'star');
  }

  getBody(id: string | null | undefined): Body | undefined {
    return id ? this.bodies.find((b) => b.id === id) : undefined;
  }

  children(id: string): Body[] {
    return this.bodies.filter((b) => b.parentId === id);
  }

  /** Le corps et tous ses satellites, parents avant enfants. */
  private subtree(id: string): Body[] {
    const root = this.getBody(id);
    if (!root) return [];
    const out = [root];
    for (let k = 0; k < out.length; k++) out.push(...this.children(out[k].id));
    return out;
  }

  /**
   * Charge un système. Avec `placeFromElements`, les positions/vitesses sont
   * calculées à partir des éléments orbitaux ; sinon elles sont reprises telles quelles.
   */
  load(def: SystemDefinition, placeFromElements = true): void {
    this.name = def.name;
    this.time = def.time ?? 0;
    this.bodies = orderByHierarchy(def.bodies.map(cloneBody));
    if (placeFromElements) {
      for (const b of this.bodies) this.place(b);
      recenter(this.bodies);
    }
    this.events = [];
    this.initial = this.snapshot();
    this.rebuild();
  }

  /** Revient à l'état du dernier chargement. */
  reset(): void {
    const def = this.initial;
    this.load(def, false);
  }

  snapshot(): SystemDefinition {
    return { name: this.name, time: this.time, bodies: this.bodies.map(cloneBody) };
  }

  /** Place un corps sur son orbite de définition, relativement à l'état actuel de son parent. */
  private place(body: Body): void {
    const parent = this.getBody(body.parentId);
    if (!parent || !body.elements) return;
    const rel = elementsToState(body.elements, mu(parent.mass, body.mass));
    body.position = add(parent.position, rel.position);
    body.velocity = add(parent.velocity, rel.velocity);
  }

  /** Longitude vraie actuelle (Ω + ω + ν) d'un corps autour de son parent, en degrés. */
  private trueLongitude(body: Body): number | null {
    const parent = this.getBody(body.parentId);
    if (!parent) return null;
    const el = currentElements(body, parent);
    return el.Omega + el.omega + el.nu;
  }

  /**
   * Applique une modification à des corps puis les replace (avec leurs satellites)
   * sur leur orbite, en conservant leur position angulaire actuelle.
   */
  private replaceSubtrees(rootIds: string[], mutate: () => void): void {
    const affected: Body[] = [];
    const seen = new Set<string>();
    for (const id of rootIds) {
      for (const b of this.subtree(id)) {
        if (!seen.has(b.id)) {
          seen.add(b.id);
          affected.push(b);
        }
      }
    }
    const phases = new Map(affected.map((b) => [b.id, this.trueLongitude(b)]));
    mutate();
    for (const b of affected) {
      const phase = phases.get(b.id);
      if (b.elements && phase != null && Number.isFinite(phase)) {
        b.elements.nu = (((phase - b.elements.Omega - b.elements.omega) % 360) + 360) % 360;
      }
      this.place(b);
    }
    recenter(this.bodies, false);
    this.rebuild();
  }

  addBody(body: Body): void {
    if (body.parentId && !this.getBody(body.parentId)) throw new Error('Corps parent introuvable.');
    const b = cloneBody(body);
    this.bodies.push(b);
    this.place(b);
    recenter(this.bodies, false);
    this.bodies = orderByHierarchy(this.bodies);
    this.rebuild();
  }

  updateBody(id: string, patch: BodyPatch): void {
    const body = this.getBody(id);
    if (!body) return;
    const dynamic = patch.mass !== undefined || patch.elements !== undefined;
    const apply = () => {
      const { elements, ...rest } = patch;
      Object.assign(body, rest);
      if (elements) body.elements = { ...elements };
    };
    if (!dynamic) {
      apply();
      this.changed();
      return;
    }
    // Si l'étoile change de masse, toutes les orbites doivent être recalculées.
    const roots = body.kind === 'star' ? this.children(id).map((c) => c.id) : [id];
    this.replaceSubtrees(roots, apply);
  }

  setStarClass(spectralClass: SpectralClass): void {
    const star = this.star;
    if (!star) return;
    const info = SPECTRAL_CLASSES[spectralClass];
    this.replaceSubtrees(
      this.children(star.id).map((c) => c.id),
      () => {
        star.star = starPropsFor(spectralClass);
        star.mass = info.mass;
        star.radiusKm = info.radius * SUN_RADIUS_KM;
        star.color = info.color;
      },
    );
  }

  /** Supprime un corps et ses satellites (l'étoile ne peut pas être supprimée). */
  removeBody(id: string): void {
    const body = this.getBody(id);
    if (!body || body.kind === 'star') return;
    const ids = new Set(this.subtree(id).map((b) => b.id));
    this.bodies = this.bodies.filter((b) => !ids.has(b.id));
    recenter(this.bodies, false);
    this.rebuild();
  }

  setSpeed(daysPerSecond: number): void {
    this.speed = daysPerSecond;
    this.changed();
  }

  setPaused(paused: boolean): void {
    this.paused = paused;
    if (paused) this.effectiveSpeed = 0;
    this.changed();
  }

  private log(kind: SimEvent['kind'], message: string): void {
    this.events.unshift({ time: this.time, kind, message });
    if (this.events.length > MAX_EVENTS) this.events.length = MAX_EVENTS;
  }

  /** Recalcule les accélérations et le pas de temps maximal après un changement de structure. */
  private rebuild(): void {
    this.acc = makeAccelerationBuffer(this.bodies.length);
    if (this.bodies.length > 0) computeAccelerations(this.bodies, this.acc);
    this.dtMax = this.computeMaxDt();
    this.changed();
  }

  /** ~200 pas par orbite au périastre pour l'orbite la plus rapide. */
  private computeMaxDt(): number {
    let dt = 2 / DAYS_PER_YEAR;
    for (const b of this.bodies) {
      const parent = this.getBody(b.parentId);
      if (!parent) continue;
      let { a, e } = b.elements ?? { a: distance(b.position, parent.position), e: 0 };
      const osc = currentElements(b, parent);
      if (osc.a > 0 && Number.isFinite(osc.a) && osc.e < 1) {
        a = osc.a;
        e = osc.e;
      }
      const period = orbitalPeriod(a, parent.mass, b.mass);
      dt = Math.min(dt, (period * Math.pow(1 - Math.min(e, 0.95), 1.5)) / 200);
    }
    return Math.max(dt, 1e-7);
  }

  get maxTimeStep(): number {
    return this.dtMax;
  }

  /**
   * Avance la simulation de `realSeconds` secondes réelles à la vitesse choisie.
   * Le calcul est limité à `budgetMs` : si la machine ne suit pas, la simulation
   * ralentit (vitesse effective plus basse) au lieu de perdre en précision.
   */
  advance(realSeconds: number, budgetMs = 12): void {
    if (this.paused || this.bodies.length < 2 || realSeconds <= 0) {
      this.effectiveSpeed = 0;
      return;
    }
    const target = (this.speed * realSeconds) / DAYS_PER_YEAR;
    const done = this.run(target, budgetMs);
    const instant = (done / realSeconds) * DAYS_PER_YEAR;
    this.effectiveSpeed = this.effectiveSpeed === 0 ? instant : this.effectiveSpeed * 0.9 + instant * 0.1;
  }

  /** Avance d'une durée simulée fixe (années), sans limite de temps de calcul. */
  stepFor(years: number): void {
    this.run(years, Infinity);
  }

  private run(years: number, budgetMs: number): number {
    const start = performance.now();
    const steps = Math.max(1, Math.ceil(years / this.dtMax));
    const dt = years / steps;
    let done = 0;
    for (let k = 0; k < steps; k++) {
      verletStep(this.bodies, this.acc, dt);
      this.time += dt;
      done += dt;
      this.handleCollisions(dt);
      if ((k & 15) === 15 && performance.now() - start > budgetMs) break;
    }
    this.handleEscapes();
    return done;
  }

  private handleCollisions(dt: number): void {
    let pair = findCollision(this.bodies, dt);
    if (!pair) return;
    while (pair) {
      const [survivor, absorbed] = mergeBodies(this.bodies[pair[0]], this.bodies[pair[1]]);
      this.bodies = this.bodies.filter((b) => b !== absorbed);
      for (const b of this.bodies) if (b.parentId === absorbed.id) b.parentId = survivor.id;
      this.log('collision', `Collision : ${survivor.name} absorbe ${absorbed.name}.`);
      pair = findCollision(this.bodies);
    }
    this.bodies = orderByHierarchy(this.bodies);
    this.rebuild();
  }

  /** Lunes arrachées à leur planète, corps éjectés hors du système. */
  private handleEscapes(): void {
    const star = this.star;
    if (!star) return;
    let structural = false;

    for (const b of this.bodies) {
      const parent = this.getBody(b.parentId);
      if (!parent || parent === star) continue;
      const r = sub(b.position, parent.position);
      const v = sub(b.velocity, parent.velocity);
      const energy = dot(v, v) / 2 - mu(parent.mass, b.mass) / Math.sqrt(dot(r, r));
      const pd = distance(parent.position, star.position);
      const hill = hillRadius(pd, 0, parent.mass, star.mass);
      if (energy >= 0 || Math.sqrt(dot(r, r)) > hill) {
        this.log('evasion', `${b.name} s'échappe de l'orbite de ${parent.name}.`);
        b.parentId = star.id;
        b.kind = 'planet';
        b.elements = currentElements(b, star);
        structural = true;
      }
    }

    const ejected: Body[] = [];
    for (const b of this.bodies) {
      if (b === star) continue;
      const r = sub(b.position, star.position);
      const d = Math.sqrt(dot(r, r));
      if (d < EJECTION_DISTANCE_AU) continue;
      const v = sub(b.velocity, star.velocity);
      if (dot(v, v) / 2 - (G * (star.mass + b.mass)) / d >= 0) ejected.push(b);
    }
    if (ejected.length > 0) {
      const ids = new Set(ejected.map((b) => b.id));
      for (const b of ejected) this.log('ejection', `${b.name} est éjectée du système.`);
      this.bodies = this.bodies.filter((b) => !ids.has(b.id));
      for (const b of this.bodies) if (b.parentId && ids.has(b.parentId)) b.parentId = star.id;
      structural = true;
    }

    if (structural) {
      this.bodies = orderByHierarchy(this.bodies);
      this.rebuild();
    }
  }
}
