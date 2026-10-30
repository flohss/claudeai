import { currentElements, density, rocheLimitKm, surfaceGravity, type Frame } from '../physics/derived';
import {
  CHICXULUB_MT,
  MEGATON_J,
  craterDiameterKm,
  impactEnergyJ,
  impactSeverity,
  schwarzschildRadiusKm,
  tidalRadiusKm,
} from '../physics/impacts';
import { centerOfMass, findCollision, mergeBodies, recenter } from '../physics/nbody';
import { NBodyState } from '../physics/state';
import { elementsToState, hillRadius, hyperbolicState, mu, orbitalPeriod } from '../physics/orbits';
import { SPECTRAL_CLASSES, snowLine, starPropsFor } from '../physics/stars';
import type { Body, OrbitalElements, PlanetType, Remnant, SpectralClass } from '../physics/types';
import { AU_KM, DAYS_PER_YEAR, EARTH_MASS_SUN, G, SUN_RADIUS_KM, kmToAu } from '../physics/units';
import { add, clone, cross, distance, dot, length, scale, sub, type Vec3 } from '../physics/vec3';
import { num } from '../format';
import { DEFAULT_COLOR, estimateRadiusKm, makeOrbiter, makeStar } from './factory';

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

/** Évolution progressive d'une étoile (phase de géante rouge, en temps accéléré). */
export interface StellarEvolution {
  starId: string;
  start: number;
  duration: number;
  from: { mass: number; radiusKm: number; luminosity: number };
  to: { mass: number; radiusKm: number; luminosity: number };
}

export interface SystemDefinition {
  name: string;
  bodies: Body[];
  /** Temps simulé (années). Absent = 0. */
  time?: number;
  formation?: FormationSettings | null;
  evolutions?: StellarEvolution[];
}

export interface SimEvent {
  time: number;
  kind: 'collision' | 'ejection' | 'evasion' | 'formation' | 'roche' | 'impact' | 'maree' | 'etoile' | 'intrus' | 'info';
  message: string;
  /** Lieu de l'événement, pour l'effet visuel */
  position?: Vec3;
  flash?: 'impact' | 'supernova' | 'maree';
}

/** Corps venu de l'extérieur qui traverse le système. */
export interface IntruderSpec {
  id: string;
  name: string;
  type: 'etoile' | 'trou-noir' | 'planete';
  /** Masse (M☉) */
  mass: number;
  /** Pour une étoile */
  spectralClass?: SpectralClass;
  periapsisAu: number;
  speedKmS: number;
  /** Orientation de la trajectoire (°) */
  i: number;
  Omega: number;
  omega: number;
}

/** Astéroïde ou planétésimal lancé sur un corps. */
export interface ImpactorSpec {
  id: string;
  targetId: string;
  name: string;
  /** Diamètre (km) */
  diameterKm: number;
  /** Masse (M☉) */
  mass: number;
  speedKmS: number;
  /** Direction d'arrivée (°) */
  azimuth: number;
  elevation: number;
}

export type ImpulseDirection = 'prograde' | 'retrograde' | 'exterieur' | 'interieur' | 'perpendiculaire';

/** 1 km/s en UA/an */
export const KM_S = 0.210945;

export type BodyPatch = Partial<Pick<Body, 'name' | 'planetType' | 'mass' | 'radiusKm' | 'color' | 'albedo' | 'rings' | 'axialTilt'>> & {
  elements?: OrbitalElements;
};

/** Distance au-delà de laquelle un corps non lié aux étoiles est considéré éjecté (UA). */
export const EJECTION_DISTANCE_AU = 1000;
/** Masse à partir de laquelle un planétésimal devient une protoplanète (M⊕). */
export const PROTOPLANET_MASS_EARTH = 0.5;
const MAX_EVENTS = 80;

/** Nombre court au format français pour le journal. */
const fr = (n: number, digits: number) => num(n, digits);

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

/**
 * Éléments orbitaux de référence d'un corps qui change d'hôte. Une trajectoire
 * non liée (hyperbolique) n'a pas d'orbite de référence : on garde alors une
 * orbite circulaire à la distance actuelle, dans le même plan.
 */
function referenceElements(el: OrbitalElements, distanceAu: number): OrbitalElements {
  if (el.a > 0 && Number.isFinite(el.a) && el.e < 1) return el;
  return { ...el, a: distanceAu, e: 0 };
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
  evolutions: StellarEvolution[] = [];

  /** Copie compacte de l'état dynamique, synchronisée avec `bodies` par `rebuild`. */
  private state = new NBodyState();
  private dtMax = 0.001;
  private protoCounter = 0;
  /** Corps déjà signalés comme n'étant plus liés à leur étoile */
  private unboundLogged = new Set<string>();
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

  protected changed(): void {
    this.version += 1;
    this.listeners.forEach((l) => l());
  }

  /** Étoiles du système (sans les étoiles ou trous noirs de passage). */
  get stars(): Body[] {
    return this.bodies.filter((b) => b.kind === 'star' && !b.intruder);
  }

  /** Toutes les sources de lumière, y compris une étoile de passage. */
  get luminousBodies(): Body[] {
    return this.bodies.filter((b) => b.kind === 'star' && (b.star?.luminosity ?? 0) > 0);
  }

  /** L'étoile principale (sans parent). */
  get star(): Body | undefined {
    const stars = this.stars;
    return stars.find((b) => !b.parentId) ?? stars[0];
  }

  /** Index par identifiant, reconstruit quand le tableau `bodies` est remplacé. */
  private index = new Map<string, Body>();
  private indexOf: Body[] | null = null;

  getBody(id: string | null | undefined): Body | undefined {
    if (!id) return undefined;
    if (this.indexOf !== this.bodies || this.index.size !== this.bodies.length) {
      this.index = new Map(this.bodies.map((b) => [b.id, b]));
      this.indexOf = this.bodies;
    }
    return this.index.get(id);
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
    this.evolutions = (def.evolutions ?? []).map((e) => structuredClone(e));
    this.bodies = orderByHierarchy(def.bodies.map(cloneBody));
    this.protoCounter = this.bodies.filter((b) => b.accretionScale && b.kind !== 'planetesimal').length;
    if (placeFromElements) {
      for (const b of this.bodies) this.place(b);
      recenter(this.bodies);
    }
    this.events = [];
    this.unboundLogged.clear();
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
      evolutions: this.evolutions.map((e) => structuredClone(e)),
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
      // Le rayon (donc le rayon de collision) a pu changer.
      this.rebuild();
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
  addCompanion(spectralClass: SpectralClass, a: number, e: number, id?: string): Body | undefined {
    const primary = this.star;
    if (!primary) return undefined;
    const companion = makeStar(spectralClass, `${primary.name} B`);
    if (id) companion.id = id;
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

  private log(kind: SimEvent['kind'], message: string, extra?: Pick<SimEvent, 'position' | 'flash'>): void {
    this.events.unshift({ time: this.time, kind, message, ...extra });
    if (this.events.length > MAX_EVENTS) this.events.length = MAX_EVENTS;
  }

  /** Recalcule les accélérations et le pas de temps maximal après un changement de structure. */
  private rebuild(): void {
    this.state.load(this.bodies);
    this.state.computeAccelerations();
    this.dtMax = this.computeMaxDt();
    this.prepareTidal();
    this.changed();
  }

  /** Corps compacts (trous noirs, étoiles à neutrons) et carré des rayons de marée de leurs victimes (UA²). */
  private tidal: { index: number; r2: Float64Array }[] = [];

  private prepareTidal(): void {
    this.tidal = [];
    this.bodies.forEach((c, index) => {
      const remnant = c.star?.remnant;
      if (remnant !== 'trou-noir' && remnant !== 'etoile-a-neutrons') return;
      const r2 = new Float64Array(this.bodies.length);
      this.bodies.forEach((v, j) => {
        if (j === index || v.mass >= c.mass || v.star?.remnant === 'trou-noir' || v.star?.remnant === 'etoile-a-neutrons') return;
        const r = kmToAu(tidalRadiusKm(v.radiusKm, c.mass, v.mass));
        r2[j] = r * r;
      });
      this.tidal.push({ index, r2 });
    });
  }

  /** Renvoie [compact, victime] si un corps vient de passer sous un rayon de marée. */
  private findTidalDisruption(): [number, number] | null {
    const { px, py, pz } = this.state;
    for (const { index: c, r2 } of this.tidal) {
      for (let j = 0; j < r2.length; j++) {
        if (r2[j] === 0) continue;
        const dx = px[j] - px[c];
        const dy = py[j] - py[c];
        const dz = pz[j] - pz[c];
        if (dx * dx + dy * dy + dz * dz < r2[j]) return [c, j];
      }
    }
    return null;
  }

  private handleTidalDisruption(c: number, j: number): void {
    const compact = this.bodies[c];
    const victim = this.bodies[j];
    const position = clone(victim.position);
    const wasHost = victim.kind === 'star' && !victim.intruder;
    mergeBodies(compact, victim);
    this.bodies = this.bodies.filter((x) => x !== victim);
    for (const x of this.bodies) if (x.parentId === victim.id) x.parentId = compact.id;
    // Un intrus qui détruit l'étoile du système en devient le centre.
    if (wasHost) compact.intruder = false;
    const fate = compact.star?.remnant === 'trou-noir' ? 'ses débris tombent dans le trou noir' : "ses débris s'écrasent sur l'étoile à neutrons";
    this.log('maree', `${victim.name} est déchiquetée par les forces de marée de ${compact.name} (« spaghettification ») ; ${fate}.`, {
      position,
      flash: 'maree',
    });
    this.bodies = orderByHierarchy(this.bodies);
    this.rebuild();
  }

  /** ~200 pas par orbite au périastre pour l'orbite la plus rapide. */
  private computeMaxDt(): number {
    let dt = 2 / DAYS_PER_YEAR;
    for (const b of this.bodies) {
      const frame = this.frameOf(b);
      if (!frame) continue;
      let a = distance(b.position, frame.position);
      let e = 0;
      if (b.elements && b.elements.a > 0 && b.elements.e < 1) ({ a, e } = b.elements);
      const osc = currentElements(b, frame);
      if (osc.a > 0 && Number.isFinite(osc.a) && osc.e < 1) {
        a = osc.a;
        e = osc.e;
      }
      const period = orbitalPeriod(a, frame.mass, b.mass);
      const candidate = (period * Math.pow(1 - Math.min(e, 0.95), 1.5)) / 200;
      // Garde-fou : une valeur invalide ne doit jamais contaminer tout le calcul.
      if (Number.isFinite(candidate) && candidate > 0) dt = Math.min(dt, candidate);
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

  /**
   * Pas maximal imposé par les intrus : leur rencontre avec un corps doit être
   * découpée finement, quelle que soit la stabilité des orbites du système.
   */
  private encounterDt(): number {
    let dt = Infinity;
    const { px, py, pz, m, n } = this.state;
    for (let c = 0; c < n; c++) {
      if (!this.bodies[c]?.intruder) continue;
      for (let j = 0; j < n; j++) {
        if (j === c) continue;
        const d2 = (px[j] - px[c]) ** 2 + (py[j] - py[c]) ** 2 + (pz[j] - pz[c]) ** 2;
        const d = Math.sqrt(d2);
        const candidate = 0.01 * Math.sqrt((d2 * d) / (G * (m[c] + m[j])));
        if (Number.isFinite(candidate)) dt = Math.min(dt, candidate);
      }
    }
    return Math.max(dt, 1e-8);
  }

  private run(years: number, budgetMs: number): number {
    const start = performance.now();
    let done = 0;
    let encounter = this.encounterDt();
    // L'intégration se fait dans `state` ; les corps sont mis à jour avant
    // chaque règle qui les lit, et `rebuild` recharge l'état après une modification.
    // Le pas est recalculé à chaque tour : une fusion, une lune née d'un impact
    // ou l'approche d'un intrus peuvent exiger des pas plus fins.
    for (let k = 0; done < years * (1 - 1e-12); k++) {
      const dt = Math.min(this.dtMax, encounter, years - done);
      this.state.kickDrift(dt);
      this.time += dt;
      done += dt;
      // Collisions et marées sont testées avant la gravité aux nouvelles positions.
      // Après une fusion, `rebuild` recalcule les accélérations et la demi-impulsion
      // finale est sautée (la collision, inélastique, ne conserve pas l'énergie).
      const pair = this.state.findCollision(dt);
      const disruption = pair ? null : this.tidal.length > 0 ? this.findTidalDisruption() : null;
      if (pair) {
        this.state.store(this.bodies);
        this.handleCollisions(pair);
      } else if (disruption) {
        this.state.store(this.bodies);
        this.handleTidalDisruption(...disruption);
      } else {
        this.state.finishStep(dt);
      }
      if ((k & 31) === 31) {
        encounter = this.encounterDt();
        // Les règles plus coûteuses ne sont évaluées que périodiquement.
        this.state.store(this.bodies);
        this.handleEscapes();
        this.handleRoche();
        this.applyEvolutions();
        if (performance.now() - start > budgetMs) break;
      }
    }
    this.state.store(this.bodies);
    this.handleEscapes();
    this.handleRoche();
    this.handleGasAccretion(done);
    this.applyEvolutions();
    return done;
  }

  private handleCollisions(first: [number, number]): void {
    let pair: [number, number] | null = first;
    while (pair) {
      const a = this.bodies[pair[0]];
      const b = this.bodies[pair[1]];
      const colorA = a.color;
      const colorB = b.color;
      const relativeSpeed = length(sub(a.velocity, b.velocity));
      const [survivor, absorbed] = mergeBodies(a, b);
      this.bodies = this.bodies.filter((x) => x !== absorbed);
      for (const x of this.bodies) if (x.parentId === absorbed.id) x.parentId = survivor.id;
      if (survivor.accretionScale) {
        const [cs, ca] = survivor === a ? [colorA, colorB] : [colorB, colorA];
        survivor.color = blendColors(cs, survivor.mass - absorbed.mass, ca, absorbed.mass);
        this.growFromDisk(survivor);
      }
      // Les fusions de planétésimaux sont trop nombreuses pour être toutes journalisées.
      if (absorbed.kind !== 'planetesimal') this.describeCollision(survivor, absorbed, relativeSpeed);
      pair = findCollision(this.bodies);
    }
    this.bodies = orderByHierarchy(this.bodies);
    this.rebuild();
  }

  /** Journalise une collision, avec l'énergie libérée et ses conséquences. */
  private describeCollision(survivor: Body, absorbed: Body, relativeSpeed: number): void {
    const position = clone(survivor.position);
    const remnant = survivor.star?.remnant;
    if (remnant === 'trou-noir' || remnant === 'etoile-a-neutrons') {
      const fate = remnant === 'trou-noir' ? 'ses débris tombent dans le trou noir' : "ses débris s'écrasent sur l'étoile à neutrons";
      this.log('maree', `${absorbed.name} est déchiquetée par les forces de marée de ${survivor.name} (« spaghettification ») ; ${fate}.`, {
        position,
        flash: 'maree',
      });
      if (absorbed.kind === 'star' && !absorbed.intruder) survivor.intruder = false;
      return;
    }
    if (survivor.kind === 'star') {
      this.log('collision', `${absorbed.name} est engloutie par ${survivor.name}.`, { position, flash: 'impact' });
      return;
    }
    const before = survivor.mass - absorbed.mass;
    const ratio = absorbed.mass / before;
    const megatons = impactEnergyJ(before, absorbed.mass, relativeSpeed) / MEGATON_J;
    const speedKmS = relativeSpeed / KM_S;
    const energy = `${fr(megatons, 2)} Mt de TNT, ${fr(megatons / CHICXULUB_MT, 2)} × Chicxulub`;
    const solid = survivor.planetType === 'tellurique' || survivor.planetType === 'naine';
    if (ratio < 1e-3) {
      let detail: string;
      if (!solid) {
        detail = "il disparaît dans l'atmosphère de la géante, comme la comète Shoemaker-Levy 9 sur Jupiter en 1994";
      } else {
        const g = surfaceGravity(before, survivor.radiusKm);
        const crater = craterDiameterKm(absorbed.radiusKm * 2, speedKmS, g);
        detail = `cratère d'environ ${fr(crater, 2)} km ; ${impactSeverity(megatons)}`;
      }
      this.log('impact', `Impact de ${absorbed.name} sur ${survivor.name} à ${fr(speedKmS, 2)} km/s : ${energy} ; ${detail}.`, { position, flash: 'impact' });
      return;
    }
    let message = `Impact géant : ${survivor.name} absorbe ${absorbed.name} (${energy}).`;
    if (solid) message += ' La surface fond entièrement en un océan de magma.';
    // Comme pour la formation de la Lune, une partie des débris peut se rassembler en orbite.
    if (ratio >= 0.01 && survivor.kind === 'planet' && !survivor.accretionScale) {
      const moonMassEarth = (0.15 * absorbed.mass) / EARTH_MASS_SUN;
      const moonRadius = estimateRadiusKm('naine', moonMassEarth);
      const roche = rocheLimitKm(survivor.radiusKm, density(survivor.mass, survivor.radiusKm), 3.3);
      const moon = makeOrbiter({
        name: `Lune de ${survivor.name}`,
        kind: 'moon',
        planetType: 'naine',
        massEarth: moonMassEarth,
        radiusKm: moonRadius,
        parentId: survivor.id,
        color: '#b9b2a8',
        elements: { a: kmToAu(roche * 1.6), e: 0.02 },
      });
      survivor.mass -= moon.mass;
      this.bodies.push(moon);
      this.place(moon);
      message += ` Une partie des débris s'agrège en orbite : naissance de « ${moon.name} ».`;
    }
    this.log('impact', message, { position, flash: 'impact' });
  }

  // ─── Événements déclenchés par l'utilisateur ──────────────────────────────

  /**
   * Fait traverser le système par un corps venu de loin, sur une trajectoire
   * hyperbolique autour du barycentre des étoiles. Renvoie le temps (années)
   * avant son passage au plus près.
   */
  launchIntruder(spec: IntruderSpec): number {
    const frame = this.stars.length ? this.starsFrame() : centerOfMass(this.bodies);
    const outermost = Math.max(0, ...this.bodies.map((b) => distance(b.position, frame.position)));
    const startDistance = Math.min(Math.max(spec.periapsisAu * 4, outermost * 1.3, 15), EJECTION_DISTANCE_AU * 0.6);
    const body =
      spec.type === 'planete'
        ? makeOrbiter({
            id: spec.id,
            name: spec.name,
            planetType: 'geante-gazeuse',
            massEarth: spec.mass / EARTH_MASS_SUN,
            radiusKm: estimateRadiusKm('geante-gazeuse', spec.mass / EARTH_MASS_SUN),
            parentId: '',
            elements: { a: 1 },
            color: '#8d7bb8',
          })
        : makeStar(spec.spectralClass ?? 'K', spec.name);
    body.id = spec.id;
    body.parentId = null;
    body.elements = null;
    body.intruder = true;
    if (spec.type === 'etoile') body.mass = spec.mass;
    if (spec.type === 'trou-noir') this.makeRemnant(body, 'trou-noir', spec.mass);
    const muValue = mu(frame.mass, body.mass);
    const hyper = hyperbolicState(spec.periapsisAu, spec.speedKmS * KM_S, startDistance, spec, muValue);
    body.position = add(frame.position, hyper.position);
    body.velocity = add(frame.velocity, hyper.velocity);
    this.bodies.push(body);
    this.bodies = orderByHierarchy(this.bodies);
    const what = spec.type === 'trou-noir' ? 'Un trou noir' : spec.type === 'etoile' ? 'Une étoile' : 'Une planète vagabonde';
    this.log('intrus', `${what} (${body.name}) approche : passage au plus près à ${fr(spec.periapsisAu, 3)} UA dans environ ${fr(hyper.timeToPeriapsis, 2)} ans.`);
    this.rebuild();
    return hyper.timeToPeriapsis;
  }

  /** Lance un impacteur droit sur un corps. */
  launchImpactor(spec: ImpactorSpec): void {
    const target = this.getBody(spec.targetId);
    if (!target) return;
    const az = (spec.azimuth * Math.PI) / 180;
    const el = (spec.elevation * Math.PI) / 180;
    const dir = { x: Math.cos(el) * Math.cos(az), y: Math.cos(el) * Math.sin(az), z: Math.sin(el) };
    // Départ à 60 rayons de la cible : assez loin pour que la trajectoire se courbe, assez près pour toucher.
    const d = kmToAu(target.radiusKm * 60);
    const radiusKm = spec.diameterKm / 2;
    const body = makeOrbiter({ id: spec.id, name: spec.name, planetType: 'naine', massEarth: spec.mass / EARTH_MASS_SUN, radiusKm, parentId: '', elements: { a: 1 }, color: '#8a7f73' });
    body.parentId = null;
    body.elements = null;
    body.intruder = true;
    body.position = add(target.position, scale(dir, d));
    body.velocity = sub(target.velocity, scale(dir, spec.speedKmS * KM_S));
    this.bodies.push(body);
    this.bodies = orderByHierarchy(this.bodies);
    this.rebuild();
  }

  /** Transforme une étoile en astre compact (masse, rayon, luminosité, couleur). */
  private makeRemnant(star: Body, remnant: Remnant, mass: number): void {
    star.mass = mass;
    star.star = { ...(star.star ?? starPropsFor('M')), remnant };
    if (remnant === 'trou-noir') {
      star.radiusKm = schwarzschildRadiusKm(mass);
      star.star.luminosity = 0;
      star.star.temperatureK = 0;
      star.color = '#000000';
    } else if (remnant === 'etoile-a-neutrons') {
      star.radiusKm = 12;
      star.star.luminosity = 1e-4;
      star.star.temperatureK = 600000;
      star.color = '#cfe3ff';
    } else {
      star.radiusKm = 7000;
      star.star.luminosity = 1e-3;
      star.star.temperatureK = 25000;
      star.color = '#e8eeff';
    }
  }

  /**
   * Supernova : l'étoile perd brutalement l'essentiel de sa masse. Les planètes
   * gardent leur vitesse mais l'attraction chute : au-delà de 50 % de masse
   * perdue, une orbite circulaire n'est plus liée.
   */
  supernova(starId: string, remnantMass: number): void {
    const star = this.getBody(starId);
    if (!star?.star) return;
    const lost = 1 - remnantMass / star.mass;
    const remnant: Remnant = remnantMass > 3 ? 'trou-noir' : remnantMass >= 1.2 ? 'etoile-a-neutrons' : 'naine-blanche';
    this.makeRemnant(star, remnant, remnantMass);
    const names = { 'trou-noir': 'un trou noir', 'etoile-a-neutrons': 'une étoile à neutrons', 'naine-blanche': 'une naine blanche' };
    this.log(
      'etoile',
      `Supernova ! ${star.name} expulse ${fr(lost * 100, 2)} % de sa masse et laisse ${names[remnant]}.` +
        (lost > 0.5 ? " Plus de la moitié de la masse a disparu : les planètes sur des orbites presque circulaires ne sont plus retenues." : ' Les orbites s’élargissent.'),
      { position: clone(star.position), flash: 'supernova' },
    );
    this.evolutions = this.evolutions.filter((e) => e.starId !== starId);
    this.rebuild();
  }

  /** L'étoile devient un trou noir de même masse : les orbites ne changent pas, la lumière disparaît. */
  collapseToBlackHole(starId: string): void {
    const star = this.getBody(starId);
    if (!star?.star) return;
    this.makeRemnant(star, 'trou-noir', star.mass);
    this.log(
      'etoile',
      `${star.name} s'effondre en un trou noir de même masse (horizon de ${fr(star.radiusKm, 2)} km). Les orbites ne changent pas : seule la masse compte pour la gravité. Mais les planètes plongent dans le noir et le froid.`,
      { position: clone(star.position), flash: 'maree' },
    );
    this.evolutions = this.evolutions.filter((e) => e.starId !== starId);
    this.rebuild();
  }

  /**
   * Phase de géante rouge, en temps accéléré : l'étoile gonfle jusqu'à ~250 fois
   * son rayon, devient des milliers de fois plus lumineuse et perd 30 % de sa
   * masse. Elle engloutit les planètes proches ; les autres s'éloignent.
   * Elle finit en naine blanche.
   */
  startRedGiant(starId: string, durationYears: number): void {
    const star = this.getBody(starId);
    if (!star?.star || star.star.remnant) return;
    this.evolutions = this.evolutions.filter((e) => e.starId !== starId);
    this.evolutions.push({
      starId,
      start: this.time,
      duration: Math.max(durationYears, 0.1),
      from: { mass: star.mass, radiusKm: star.radiusKm, luminosity: star.star.luminosity },
      to: { mass: star.mass * 0.7, radiusKm: 256 * SUN_RADIUS_KM * Math.sqrt(star.mass), luminosity: 2500 * star.mass },
    });
    this.log('etoile', `${star.name} épuise son hydrogène et commence à gonfler en géante rouge.`);
    this.changed();
  }

  private applyEvolutions(): void {
    if (this.evolutions.length === 0) return;
    let changed = false;
    for (const evo of this.evolutions.slice()) {
      const star = this.getBody(evo.starId);
      if (!star?.star) {
        this.evolutions = this.evolutions.filter((e) => e !== evo);
        continue;
      }
      const f = Math.min(1, (this.time - evo.start) / evo.duration);
      const geo = (a: number, b: number) => a * Math.pow(b / a, f);
      const radius = geo(evo.from.radiusKm, evo.to.radiusKm);
      // L'essentiel de la masse est perdu en fin de phase, quand l'étoile est la plus grosse.
      const mass = evo.from.mass + (evo.to.mass - evo.from.mass) * f * f;
      // On ne reconstruit l'état que si l'étoile a sensiblement changé.
      if (Math.abs(radius / star.radiusKm - 1) > 0.003 || Math.abs(mass / star.mass - 1) > 0.001 || f >= 1) {
        star.radiusKm = radius;
        star.mass = mass;
        star.star.luminosity = geo(evo.from.luminosity, evo.to.luminosity);
        star.star.temperatureK = 3500 + (5800 - 3500) * (1 - f);
        star.color = blendColors('#ff7a3d', f, '#fff1c9', 1 - f + 1e-9);
        changed = true;
      }
      if (f >= 1) {
        this.evolutions = this.evolutions.filter((e) => e !== evo);
        this.makeRemnant(star, 'naine-blanche', evo.to.mass * 0.78);
        this.log(
          'etoile',
          `${star.name} rejette ses couches externes (nébuleuse planétaire) : il reste une naine blanche de la taille de la Terre.`,
          { position: clone(star.position), flash: 'supernova' },
        );
      }
    }
    if (changed) this.rebuild();
  }

  /**
   * Donne une impulsion à un corps (et à ses lunes). Les directions sont
   * relatives à son orbite ; pour un corps sans orbite, elles sont prises dans
   * le plan de référence.
   */
  applyImpulse(id: string, deltaVKmS: number, direction: ImpulseDirection): void {
    const body = this.getBody(id);
    if (!body) return;
    const frame = this.frameOf(body) ?? centerOfMass(this.bodies.filter((b) => b !== body));
    let r = sub(body.position, frame.position);
    let v = sub(body.velocity, frame.velocity);
    if (length(r) < 1e-9 || length(v) < 1e-9 || length(cross(r, v)) < 1e-12) {
      r = { x: 1, y: 0, z: 0 };
      v = { x: 0, y: 1, z: 0 };
    }
    const unit = (u: Vec3) => scale(u, 1 / length(u));
    const dirs: Record<ImpulseDirection, Vec3> = {
      prograde: unit(v),
      retrograde: scale(unit(v), -1),
      exterieur: unit(r),
      interieur: scale(unit(r), -1),
      perpendiculaire: unit(cross(r, v)),
    };
    const dv = scale(dirs[direction], deltaVKmS * KM_S);
    const moved = body.kind === 'star' ? [body] : this.subtree(id);
    for (const b of moved) b.velocity = add(b.velocity, dv);
    const labels: Record<ImpulseDirection, string> = {
      prograde: 'dans le sens du mouvement',
      retrograde: 'contre le mouvement',
      exterieur: "vers l'extérieur",
      interieur: "vers l'intérieur",
      perpendiculaire: 'perpendiculairement à son orbite',
    };
    this.log('info', `${body.name} reçoit une impulsion de ${fr(deltaVKmS, 3)} km/s ${labels[direction]}.`);
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
        if (!binary && energy >= 0 && !this.unboundLogged.has(b.id)) {
          // Signalée une seule fois : l'éjection proprement dite n'arrive qu'à 1 000 UA.
          this.unboundLogged.add(b.id);
          this.log('evasion', `${b.name} n'est plus retenue par ${parent.name} : elle quitte le système.`);
        }
        // Dans un système double, une planète libérée de son étoile tourne autour des deux.
        if (binary && energy >= 0) {
          this.log('evasion', `${b.name} quitte l'orbite de ${parent.name} et tourne désormais autour des deux étoiles.`);
          b.circumbinary = true;
          b.parentId = primary.id;
          const frame = this.starsFrame();
          b.elements = referenceElements(currentElements(b, frame), distance(b.position, frame.position));
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
        if (frame) b.elements = referenceElements(currentElements(b, frame), distance(b.position, frame.position));
        structural = true;
      }
    }

    const frame = this.starsFrame();
    const ejected: Body[] = [];
    for (const b of this.bodies) {
      if (b.kind === 'star' && !b.intruder) continue;
      const r = sub(b.position, frame.position);
      const d = Math.sqrt(dot(r, r));
      if (d < EJECTION_DISTANCE_AU) continue;
      const v = sub(b.velocity, frame.velocity);
      if (dot(v, v) / 2 - (G * (frame.mass + b.mass)) / d >= 0) ejected.push(b);
    }
    if (ejected.length > 0) {
      const ids = new Set(ejected.map((b) => b.id));
      for (const b of ejected) {
        if (b.intruder) this.log('intrus', `${b.name} s'éloigne définitivement du système.`);
        else if (b.kind !== 'planetesimal') this.log('ejection', `${b.name} est éjectée du système.`);
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
