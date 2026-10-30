import { currentElements, density, rocheLimitKm, type Frame } from '../physics/derived';
import {
  centerOfMass,
  computeAccelerations,
  findCollision,
  makeAccelerationBuffer,
  mergeBodies,
  recenter,
  verletStep,
} from '../physics/nbody';
import { elementsToState, hillRadius, mu, orbitalPeriod } from '../physics/orbits';
import { SPECTRAL_CLASSES, snowLine, starPropsFor } from '../physics/stars';
import type { Body, OrbitalElements, PlanetType, SpectralClass } from '../physics/types';
import { AU_KM, DAYS_PER_YEAR, EARTH_MASS_SUN, G, SUN_RADIUS_KM } from '../physics/units';
import { add, clone, distance, dot, scale, sub, type Vec3 } from '../physics/vec3';
import { DEFAULT_COLOR, estimateRadiusKm, makeStar } from './factory';

/**
 * Paramètres du modèle (accéléré) de formation planétaire. Tant que le gaz du
 * disque n'est pas dissipé, un noyau assez massif au-delà de la ligne des glaces
 * capture du gaz et devient une géante gazeuse.
 */
export interface FormationSettings {
  /** Instant (années simulées) où le gaz du disque est dissipé */
  gasUntil: number;
  /** Temps caractéristique de croissance par capture de gaz (années) */
  gasTimescale: number;
  /** Masse minimale d'un noyau pour capturer du gaz (M⊕) */
  coreMassEarth: number;
  /** Masse maximale atteinte par capture de gaz (M⊕) */
  maxGiantMassEarth: number;
}

export interface SystemDefinition {
  name: string;
  bodies: Body[];
  /** Temps simulé (années). Absent = 0. */
  time?: number;
  formation?: FormationSettings | null;
}

export interface SimEvent {
  time: number;
  kind: 'collision' | 'ejection' | 'evasion' | 'formation' | 'roche' | 'info';
  message: string;
}

export type BodyPatch = Partial<Pick<Body, 'name' | 'planetType' | 'mass' | 'radiusKm' | 'color' | 'albedo' | 'rings' | 'axialTilt'>> & {
  elements?: OrbitalElements;
};

/** Distance au-delà de laquelle un corps non lié aux étoiles est considéré éjecté (UA). */
export const EJECTION_DISTANCE_AU = 1000;
/** Masse à partir de laquelle un planétésimal devient une protoplanète (M⊕). */
export const PROTOPLANET_MASS_EARTH = 0.5;
const MAX_EVENTS = 80;

/** Nombre court au format français pour le journal. */
const fr = (n: number, digits: number) => n.toPrecision(digits).replace('.', ',');

const cloneBody = (b: Body): Body => ({
  ...b,
  star: b.star ? { ...b.star } : undefined,
  rings: b.rings ? { ...b.rings } : undefined,
  elements: b.elements ? { ...b.elements } : null,
  position: clone(b.position),
  velocity: clone(b.velocity),
});

/**
 * Trie les corps pour qu'un parent soit toujours avant ses satellites, et les
 * étoiles avant tout le reste (une orbite circumbinaire dépend de toutes les étoiles).
 */
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
  return [...result.filter((b) => b.kind === 'star'), ...result.filter((b) => b.kind !== 'star')];
}

/** Type d'un corps issu du disque, d'après sa masse et sa position. */
function classify(massEarth: number, beyondSnowLine: boolean): PlanetType {
  if (massEarth >= 50) return 'geante-gazeuse';
  if (massEarth >= 3 && beyondSnowLine) return 'geante-glace';
  if (massEarth < 0.02) return 'naine';
  return 'tellurique';
}

/** Mélange de deux couleurs pondéré par la masse. */
function blendColors(c1: string, m1: number, c2: string, m2: number): string {
  const p = (c: string, k: number) => parseInt(c.slice(1 + 2 * k, 3 + 2 * k), 16);
  const w = m1 / (m1 + m2);
  return `#${[0, 1, 2]
    .map((k) => Math.round(p(c1, k) * w + p(c2, k) * (1 - w)).toString(16).padStart(2, '0'))
    .join('')}`;
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
  /** Incrémenté à chaque chargement ou réinitialisation (repart d'un nouvel historique) */
  epoch = 0;
  formation: FormationSettings | null = null;

  private acc: Vec3[] = [];
  private dtMax = 0.001;
  private protoCounter = 0;
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

  get stars(): Body[] {
    return this.bodies.filter((b) => b.kind === 'star');
  }

  /** L'étoile principale (sans parent). */
  get star(): Body | undefined {
    return this.bodies.find((b) => b.kind === 'star' && !b.parentId) ?? this.bodies.find((b) => b.kind === 'star');
  }

  getBody(id: string | null | undefined): Body | undefined {
    return id ? this.bodies.find((b) => b.id === id) : undefined;
  }

  children(id: string): Body[] {
    return this.bodies.filter((b) => b.parentId === id);
  }

  /** Barycentre de toutes les étoiles. */
  starsFrame(): Frame {
    return centerOfMass(this.stars);
  }

  /** Référentiel dans lequel l'orbite d'un corps est définie (parent, ou barycentre des étoiles). */
  frameOf(body: Body): Frame | undefined {
    if (body.circumbinary && this.stars.length > 0) return this.starsFrame();
    return this.getBody(body.parentId);
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
    this.formation = def.formation ? { ...def.formation } : null;
    this.bodies = orderByHierarchy(def.bodies.map(cloneBody));
    this.protoCounter = this.bodies.filter((b) => b.accretionScale && b.kind !== 'planetesimal').length;
    if (placeFromElements) {
      for (const b of this.bodies) this.place(b);
      recenter(this.bodies);
    }
    this.events = [];
    this.initial = this.snapshot();
    this.epoch += 1;
    this.rebuild();
  }

  /** Revient à l'état du dernier chargement. */
  reset(): void {
    this.load(this.initial, false);
  }

  snapshot(): SystemDefinition {
    return {
      name: this.name,
      time: this.time,
      formation: this.formation ? { ...this.formation } : null,
      bodies: this.bodies.map(cloneBody),
    };
  }

  /** Place un corps sur son orbite de définition, relativement à l'état actuel de son référentiel. */
  private place(body: Body): void {
    const frame = this.frameOf(body);
    if (!frame || !body.elements) return;
    const rel = elementsToState(body.elements, mu(frame.mass, body.mass));
    body.position = add(frame.position, rel.position);
    body.velocity = add(frame.velocity, rel.velocity);
  }

  /** Longitude vraie actuelle (Ω + ω + ν) d'un corps dans son référentiel, en degrés. */
  private trueLongitude(body: Body): number | null {
    const frame = this.frameOf(body);
    if (!frame) return null;
    const el = currentElements(body, frame);
    return el.Omega + el.omega + el.nu;
  }

  /**
   * Applique une modification à des corps puis les replace (avec leurs satellites)
   * sur leur orbite, en conservant leur position angulaire actuelle.
   */
  private replaceSubtrees(rootIds: string[], mutate: () => void): void {
    const seen = new Set<string>();
    for (const id of rootIds) for (const b of this.subtree(id)) seen.add(b.id);
    // Ordre de placement : celui de `bodies` (étoiles d'abord, parents avant enfants).
    const affected = this.bodies.filter((b) => seen.has(b.id));
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

  /** Corps dont l'orbite dépend d'une étoile : l'étoile elle-même si elle est compagne, ses satellites, les planètes circumbinaires. */
  private dependentsOfStar(star: Body): string[] {
    const ids = this.children(star.id).map((c) => c.id);
    if (star.parentId) ids.unshift(star.id);
    for (const b of this.bodies) if (b.circumbinary && !ids.includes(b.id)) ids.push(b.id);
    return ids;
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
    // Si une étoile change, toutes les orbites qui en dépendent sont recalculées.
    const roots = body.kind === 'star' ? this.dependentsOfStar(body) : [id];
    this.replaceSubtrees(roots, apply);
  }

  setStarClass(starId: string, spectralClass: SpectralClass): void {
    const star = this.getBody(starId);
    if (!star || star.kind !== 'star') return;
    const info = SPECTRAL_CLASSES[spectralClass];
    this.replaceSubtrees(this.dependentsOfStar(star), () => {
      star.star = starPropsFor(spectralClass);
      star.mass = info.mass;
      star.radiusKm = info.radius * SUN_RADIUS_KM;
      star.color = info.color;
    });
  }

  /** Ajoute une étoile compagne en orbite autour de l'étoile principale. */
  addCompanion(spectralClass: SpectralClass, a: number, e: number): Body | undefined {
    const primary = this.star;
    if (!primary) return undefined;
    const companion = makeStar(spectralClass, `${primary.name} B`);
    companion.parentId = primary.id;
    companion.elements = { a, e, i: 0, Omega: 0, omega: 0, nu: 180 };
    this.addBody(companion);
    this.log('info', `${companion.name} rejoint le système (séparation ${fr(a, 3)} UA).`);
    this.changed();
    return this.getBody(companion.id);
  }

  /** Supprime un corps et ses satellites (l'étoile principale ne peut pas être supprimée). */
  removeBody(id: string): void {
    const body = this.getBody(id);
    if (!body || body === this.star) return;
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
      const frame = this.frameOf(b);
      if (!frame) continue;
      let { a, e } = b.elements ?? { a: distance(b.position, frame.position), e: 0 };
      const osc = currentElements(b, frame);
      if (osc.a > 0 && Number.isFinite(osc.a) && osc.e < 1) {
        a = osc.a;
        e = osc.e;
      }
      const period = orbitalPeriod(a, frame.mass, b.mass);
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
      if ((k & 31) === 31) {
        // Les règles plus coûteuses ne sont évaluées que périodiquement.
        this.handleEscapes();
        this.handleRoche();
        if (performance.now() - start > budgetMs) break;
      }
    }
    this.handleEscapes();
    this.handleRoche();
    this.handleGasAccretion(done);
    return done;
  }

  private handleCollisions(dt: number): void {
    let pair = findCollision(this.bodies, dt);
    if (!pair) return;
    while (pair) {
      const a = this.bodies[pair[0]];
      const b = this.bodies[pair[1]];
      const colorA = a.color;
      const colorB = b.color;
      const [survivor, absorbed] = mergeBodies(a, b);
      this.bodies = this.bodies.filter((x) => x !== absorbed);
      for (const x of this.bodies) if (x.parentId === absorbed.id) x.parentId = survivor.id;
      if (survivor.accretionScale) {
        const [cs, ca] = survivor === a ? [colorA, colorB] : [colorB, colorA];
        survivor.color = blendColors(cs, survivor.mass - absorbed.mass, ca, absorbed.mass);
        this.growFromDisk(survivor);
      }
      // Les fusions de planétésimaux sont trop nombreuses pour être toutes journalisées.
      if (absorbed.kind !== 'planetesimal') {
        this.log('collision', `Collision : ${survivor.name} absorbe ${absorbed.name}.`);
      }
      pair = findCollision(this.bodies);
    }
    this.bodies = orderByHierarchy(this.bodies);
    this.rebuild();
  }

  /** Met à jour type, rayon et statut d'un corps issu du disque après une croissance. */
  private growFromDisk(body: Body): void {
    if (body.kind === 'star') return;
    const massEarth = body.mass / EARTH_MASS_SUN;
    const star = this.star;
    const beyond = !!star?.star && distance(body.position, star.position) > snowLine(star.star.luminosity);
    const type = classify(massEarth, beyond);
    if (type !== body.planetType && (type === 'geante-gazeuse' || type === 'geante-glace')) body.color = DEFAULT_COLOR[type];
    body.planetType = type;
    body.radiusKm = estimateRadiusKm(type, massEarth);
    if (body.kind === 'planetesimal' && massEarth >= PROTOPLANET_MASS_EARTH) {
      this.protoCounter += 1;
      body.kind = 'planet';
      body.name = `Protoplanète ${this.protoCounter}`;
      this.log('formation', `${body.name} se forme (${fr(massEarth, 2)} M⊕).`);
    }
  }

  /** Capture du gaz du disque par les noyaux massifs au-delà de la ligne des glaces. */
  private handleGasAccretion(years: number): void {
    const f = this.formation;
    const star = this.star;
    if (!f || !star?.star || years <= 0) return;
    const before = this.time - years;
    if (before < f.gasUntil && this.time >= f.gasUntil) {
      this.log('formation', 'Le gaz du disque se dissipe : les géantes cessent de grossir.');
      this.changed();
    }
    if (before >= f.gasUntil) return;
    const snow = snowLine(star.star.luminosity);
    const growth = Math.exp(Math.min(years, f.gasUntil - before) / f.gasTimescale);
    let changed = false;
    for (const b of this.bodies) {
      if (!b.accretionScale || b.kind === 'star' || b.kind === 'moon') continue;
      const massEarth = b.mass / EARTH_MASS_SUN;
      if (massEarth < f.coreMassEarth || massEarth >= f.maxGiantMassEarth) continue;
      if (distance(b.position, star.position) < snow) continue;
      const wasGiant = b.planetType === 'geante-gazeuse';
      b.mass = Math.min(b.mass * growth, f.maxGiantMassEarth * EARTH_MASS_SUN);
      this.growFromDisk(b);
      if (!wasGiant && b.planetType === 'geante-gazeuse') {
        this.log('formation', `${b.name} capture le gaz du disque et devient une géante gazeuse.`);
      }
      changed = true;
    }
    if (changed) this.rebuild();
  }

  /** Une lune qui passe sous la limite de Roche de sa planète est disloquée en anneau. */
  private handleRoche(): void {
    let changed = false;
    for (const moon of this.bodies.slice()) {
      const planet = this.getBody(moon.parentId);
      if (!planet || planet.kind === 'star' || moon.kind === 'star') continue;
      const limitKm = rocheLimitKm(planet.radiusKm, density(planet.mass, planet.radiusKm), density(moon.mass, moon.radiusKm));
      if (distance(moon.position, planet.position) * AU_KM > limitKm) continue;
      // La masse rejoint la planète (quantité de mouvement conservée), les débris forment un anneau.
      const m = planet.mass + moon.mass;
      planet.velocity = add(scale(planet.velocity, planet.mass / m), scale(moon.velocity, moon.mass / m));
      planet.mass = m;
      planet.rings = {
        inner: Math.min(planet.rings?.inner ?? 1.25, 1.25),
        outer: Math.max(limitKm / planet.radiusKm, planet.rings?.outer ?? 0),
        color: planet.rings?.color ?? moon.color,
        opacity: Math.min(0.9, (planet.rings?.opacity ?? 0.35) + 0.25),
      };
      this.bodies = this.bodies.filter((b) => b !== moon);
      for (const b of this.bodies) if (b.parentId === moon.id) b.parentId = planet.id;
      this.log('roche', `${moon.name} franchit la limite de Roche de ${planet.name} : disloquée par les marées, elle forme un anneau.`);
      changed = true;
    }
    if (changed) this.rebuild();
  }

  /** Corps arrachés à leur parent, corps éjectés hors du système. */
  private handleEscapes(): void {
    const primary = this.star;
    if (!primary) return;
    const binary = this.stars.length > 1;
    let structural = false;

    for (const b of this.bodies) {
      const parent = this.getBody(b.parentId);
      if (!parent || b.circumbinary || b.kind === 'star') continue;
      const r = sub(b.position, parent.position);
      const v = sub(b.velocity, parent.velocity);
      const d = Math.sqrt(dot(r, r));
      const energy = dot(v, v) / 2 - mu(parent.mass, b.mass) / d;
      if (parent.kind === 'star') {
        // Dans un système double, une planète libérée de son étoile tourne autour des deux.
        if (binary && energy >= 0) {
          this.log('evasion', `${b.name} quitte l'orbite de ${parent.name} et tourne désormais autour des deux étoiles.`);
          b.circumbinary = true;
          b.parentId = primary.id;
          b.elements = currentElements(b, this.starsFrame());
          structural = true;
        }
        continue;
      }
      const host = this.frameOf(parent);
      const hill = host ? hillRadius(distance(parent.position, host.position), 0, parent.mass, host.mass) : Infinity;
      if (energy >= 0 || d > hill) {
        const newParent = parent.circumbinary ? primary : this.getBody(parent.parentId) ?? primary;
        this.log('evasion', `${b.name} s'échappe de l'orbite de ${parent.name}.`);
        b.parentId = newParent.id;
        b.circumbinary = parent.circumbinary;
        b.kind = 'planet';
        const frame = this.frameOf(b);
        if (frame) b.elements = currentElements(b, frame);
        structural = true;
      }
    }

    const frame = this.starsFrame();
    const ejected: Body[] = [];
    for (const b of this.bodies) {
      if (b.kind === 'star') continue;
      const r = sub(b.position, frame.position);
      const d = Math.sqrt(dot(r, r));
      if (d < EJECTION_DISTANCE_AU) continue;
      const v = sub(b.velocity, frame.velocity);
      if (dot(v, v) / 2 - (G * (frame.mass + b.mass)) / d >= 0) ejected.push(b);
    }
    if (ejected.length > 0) {
      const ids = new Set(ejected.map((b) => b.id));
      for (const b of ejected) {
        if (b.kind !== 'planetesimal') this.log('ejection', `${b.name} est éjectée du système.`);
      }
      this.bodies = this.bodies.filter((b) => !ids.has(b.id));
      for (const b of this.bodies) if (b.parentId && ids.has(b.parentId)) b.parentId = primary.id;
      structural = true;
    }

    if (structural) {
      this.bodies = orderByHierarchy(this.bodies);
      this.rebuild();
    }
  }
}
