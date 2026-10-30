import { G, kmToAu } from './units';
import type { Body } from './types';

/**
 * État dynamique compact pour l'intégration : positions, vitesses et masses
 * rangées dans des tableaux typés contigus. La boucle O(N²) de la gravité y
 * est environ 3,5 fois plus rapide que sur les objets `Body`, pour un résultat
 * identique à l'arrondi près.
 *
 * Usage : `load` depuis les corps, plusieurs `step`, puis `store` pour recopier
 * l'état dans les corps.
 */
export class NBodyState {
  n = 0;
  px = new Float64Array(0);
  py = new Float64Array(0);
  pz = new Float64Array(0);
  vx = new Float64Array(0);
  vy = new Float64Array(0);
  vz = new Float64Array(0);
  ax = new Float64Array(0);
  ay = new Float64Array(0);
  az = new Float64Array(0);
  m = new Float64Array(0);
  /** Rayon de collision (UA), agrandi par `accretionScale` */
  rc = new Float64Array(0);

  private resize(n: number): void {
    this.n = n;
    if (this.px.length >= n) return;
    const cap = Math.max(n, this.px.length * 2, 16);
    for (const k of ['px', 'py', 'pz', 'vx', 'vy', 'vz', 'ax', 'ay', 'az', 'm', 'rc'] as const) this[k] = new Float64Array(cap);
  }

  load(bodies: Body[]): void {
    this.resize(bodies.length);
    // L'ordre des corps a pu changer : le tri pour les collisions repart de zéro.
    this.orderSize = -1;
    for (let i = 0; i < bodies.length; i++) {
      const b = bodies[i];
      this.px[i] = b.position.x;
      this.py[i] = b.position.y;
      this.pz[i] = b.position.z;
      this.vx[i] = b.velocity.x;
      this.vy[i] = b.velocity.y;
      this.vz[i] = b.velocity.z;
      this.m[i] = b.mass;
      this.rc[i] = kmToAu(b.radiusKm * (b.accretionScale ?? 1));
    }
  }

  store(bodies: Body[]): void {
    for (let i = 0; i < this.n; i++) {
      const b = bodies[i];
      b.position.x = this.px[i];
      b.position.y = this.py[i];
      b.position.z = this.pz[i];
      b.velocity.x = this.vx[i];
      b.velocity.y = this.vy[i];
      b.velocity.z = this.vz[i];
    }
  }

  /** Accélérations gravitationnelles (UA/an²), chaque paire calculée une seule fois. */
  computeAccelerations(): void {
    const { n, px, py, pz, m, ax, ay, az } = this;
    ax.fill(0, 0, n);
    ay.fill(0, 0, n);
    az.fill(0, 0, n);
    for (let i = 0; i < n; i++) {
      const xi = px[i];
      const yi = py[i];
      const zi = pz[i];
      const mi = m[i];
      let sx = 0;
      let sy = 0;
      let sz = 0;
      for (let j = i + 1; j < n; j++) {
        const dx = px[j] - xi;
        const dy = py[j] - yi;
        const dz = pz[j] - zi;
        const d2 = dx * dx + dy * dy + dz * dz;
        const inv = G / (d2 * Math.sqrt(d2));
        const fi = m[j] * inv;
        const fj = mi * inv;
        sx += dx * fi;
        sy += dy * fi;
        sz += dz * fi;
        ax[j] -= dx * fj;
        ay[j] -= dy * fj;
        az[j] -= dz * fj;
      }
      ax[i] += sx;
      ay[i] += sy;
      az[i] += sz;
    }
  }

  /**
   * Un pas Velocity Verlet (kick-drift-kick), symplectique : l'énergie reste
   * bornée sur le long terme. Les accélérations doivent être à jour en entrée.
   */
  step(dt: number): void {
    this.kickDrift(dt);
    this.finishStep(dt);
  }

  /**
   * Première moitié du pas : demi-impulsion puis déplacement. On peut tester les
   * collisions à ce stade, avant de calculer la gravité aux nouvelles positions :
   * deux corps qui se traversent subiraient sinon une attraction quasi infinie.
   */
  kickDrift(dt: number): void {
    const { n, px, py, pz, vx, vy, vz, ax, ay, az } = this;
    const half = dt / 2;
    for (let i = 0; i < n; i++) {
      vx[i] += ax[i] * half;
      vy[i] += ay[i] * half;
      vz[i] += az[i] * half;
      px[i] += vx[i] * dt;
      py[i] += vy[i] * dt;
      pz[i] += vz[i] * dt;
    }
  }

  /** Seconde moitié du pas : gravité aux nouvelles positions, puis demi-impulsion. */
  finishStep(dt: number): void {
    const { n, vx, vy, vz, ax, ay, az } = this;
    const half = dt / 2;
    this.computeAccelerations();
    for (let i = 0; i < n; i++) {
      vx[i] += ax[i] * half;
      vy[i] += ay[i] * half;
      vz[i] += az[i] * half;
    }
  }

  /** Indices des corps triés par x croissant, entretenus d'un pas à l'autre. */
  private order = new Int32Array(0);
  private orderSize = -1;

  /**
   * Première paire de corps qui se sont touchés pendant le dernier pas de durée
   * `dt`, ou null. On teste la distance minimale atteinte sur le pas (mouvement
   * relatif supposé rectiligne) pour ne pas manquer deux corps rapides qui se
   * croiseraient entre deux pas.
   *
   * Seules les paires proches en x sont testées (« sort and sweep ») : les corps
   * bougent peu entre deux pas, donc le tri par insertion reste presque linéaire.
   */
  findCollision(dt = 0): [number, number] | null {
    const { n, px, py, pz, vx, vy, vz, rc } = this;
    if (this.orderSize !== n || this.order.length < n) {
      if (this.order.length < n) this.order = new Int32Array(Math.max(n, 16) * 2);
      for (let i = 0; i < n; i++) this.order[i] = i;
      this.orderSize = n;
    }
    const order = this.order;
    for (let k = 1; k < n; k++) {
      const idx = order[k];
      const x = px[idx];
      let j = k - 1;
      while (j >= 0 && px[order[j]] > x) {
        order[j + 1] = order[j];
        j--;
      }
      order[j + 1] = idx;
    }

    let maxR = 0;
    let maxV2 = 0;
    for (let i = 0; i < n; i++) {
      if (rc[i] > maxR) maxR = rc[i];
      const v2 = vx[i] * vx[i] + vy[i] * vy[i] + vz[i] * vz[i];
      if (v2 > maxV2) maxV2 = v2;
    }
    // Deux corps peuvent se rapprocher d'au plus 2·vmax·dt pendant le pas.
    const reach = maxR + 2 * Math.sqrt(maxV2) * dt;

    for (let a = 0; a < n; a++) {
      const i = order[a];
      const xi = px[i];
      const yi = py[i];
      const zi = pz[i];
      const ri = rc[i];
      const limit = xi + ri + reach;
      for (let b = a + 1; b < n; b++) {
        const j = order[b];
        if (px[j] > limit) break;
        const r = ri + rc[j];
        let dx = px[j] - xi;
        let dy = py[j] - yi;
        let dz = pz[j] - zi;
        if (dt > 0) {
          const wx = vx[j] - vx[i];
          const wy = vy[j] - vy[i];
          const wz = vz[j] - vz[i];
          const w2 = wx * wx + wy * wy + wz * wz;
          if (w2 > 0) {
            const t = Math.min(Math.max((dx * wx + dy * wy + dz * wz) / w2, 0), dt);
            dx -= wx * t;
            dy -= wy * t;
            dz -= wz * t;
          }
        }
        if (dx * dx + dy * dy + dz * dz < r * r) return i < j ? [i, j] : [j, i];
      }
    }
    return null;
  }
}
