import { G, kmToAu } from './units';
import type { Body } from './types';
import { vec3, type Vec3 } from './vec3';

/** Calcule les accélérations gravitationnelles de chaque corps (UA/an²). */
export function computeAccelerations(bodies: Body[], out: Vec3[]): void {
  const n = bodies.length;
  for (let i = 0; i < n; i++) {
    const a = out[i];
    a.x = 0;
    a.y = 0;
    a.z = 0;
  }
  for (let i = 0; i < n; i++) {
    const bi = bodies[i];
    const pi = bi.position;
    for (let j = i + 1; j < n; j++) {
      const bj = bodies[j];
      const dx = bj.position.x - pi.x;
      const dy = bj.position.y - pi.y;
      const dz = bj.position.z - pi.z;
      const d2 = dx * dx + dy * dy + dz * dz;
      const invD3 = 1 / (d2 * Math.sqrt(d2));
      const fi = G * bj.mass * invD3;
      const fj = G * bi.mass * invD3;
      out[i].x += dx * fi;
      out[i].y += dy * fi;
      out[i].z += dz * fi;
      out[j].x -= dx * fj;
      out[j].y -= dy * fj;
      out[j].z -= dz * fj;
    }
  }
}

export const makeAccelerationBuffer = (n: number): Vec3[] => Array.from({ length: n }, () => vec3());

/**
 * Un pas d'intégration Velocity Verlet (kick-drift-kick), symplectique :
 * l'énergie reste bornée sur le long terme. `acc` doit contenir les
 * accélérations à l'instant courant ; elle est mise à jour en sortie.
 */
export function verletStep(bodies: Body[], acc: Vec3[], dt: number): void {
  const half = dt / 2;
  const n = bodies.length;
  for (let i = 0; i < n; i++) {
    const b = bodies[i];
    b.velocity.x += acc[i].x * half;
    b.velocity.y += acc[i].y * half;
    b.velocity.z += acc[i].z * half;
    b.position.x += b.velocity.x * dt;
    b.position.y += b.velocity.y * dt;
    b.position.z += b.velocity.z * dt;
  }
  computeAccelerations(bodies, acc);
  for (let i = 0; i < n; i++) {
    const b = bodies[i];
    b.velocity.x += acc[i].x * half;
    b.velocity.y += acc[i].y * half;
    b.velocity.z += acc[i].z * half;
  }
}

export function totalEnergy(bodies: Body[]): number {
  let kinetic = 0;
  let potential = 0;
  for (let i = 0; i < bodies.length; i++) {
    const b = bodies[i];
    const v = b.velocity;
    kinetic += 0.5 * b.mass * (v.x * v.x + v.y * v.y + v.z * v.z);
    for (let j = i + 1; j < bodies.length; j++) {
      const c = bodies[j];
      const dx = c.position.x - b.position.x;
      const dy = c.position.y - b.position.y;
      const dz = c.position.z - b.position.z;
      potential -= (G * b.mass * c.mass) / Math.sqrt(dx * dx + dy * dy + dz * dz);
    }
  }
  return kinetic + potential;
}

export function totalMomentum(bodies: Body[]): Vec3 {
  const p = vec3();
  for (const b of bodies) {
    p.x += b.mass * b.velocity.x;
    p.y += b.mass * b.velocity.y;
    p.z += b.mass * b.velocity.z;
  }
  return p;
}

export function centerOfMass(bodies: Body[]): { position: Vec3; velocity: Vec3; mass: number } {
  const position = vec3();
  const velocity = vec3();
  let mass = 0;
  for (const b of bodies) {
    mass += b.mass;
    position.x += b.mass * b.position.x;
    position.y += b.mass * b.position.y;
    position.z += b.mass * b.position.z;
    velocity.x += b.mass * b.velocity.x;
    velocity.y += b.mass * b.velocity.y;
    velocity.z += b.mass * b.velocity.z;
  }
  if (mass > 0) {
    position.x /= mass;
    position.y /= mass;
    position.z /= mass;
    velocity.x /= mass;
    velocity.y /= mass;
    velocity.z /= mass;
  }
  return { position, velocity, mass };
}

/** Ramène le système dans le référentiel du centre de masse (évite la dérive). */
export function recenter(bodies: Body[], positions = true): void {
  const com = centerOfMass(bodies);
  for (const b of bodies) {
    if (positions) {
      b.position.x -= com.position.x;
      b.position.y -= com.position.y;
      b.position.z -= com.position.z;
    }
    b.velocity.x -= com.velocity.x;
    b.velocity.y -= com.velocity.y;
    b.velocity.z -= com.velocity.z;
  }
}

/**
 * Renvoie la première paire de corps qui se sont touchés pendant le dernier pas
 * de durée `dt`, ou null. On teste la distance minimale atteinte sur le pas
 * (mouvement relatif supposé rectiligne) pour ne pas manquer deux corps rapides
 * qui se croiseraient entre deux pas.
 */
export function findCollision(bodies: Body[], dt = 0): [number, number] | null {
  for (let i = 0; i < bodies.length; i++) {
    const a = bodies[i];
    const ra = kmToAu(a.radiusKm * (a.accretionScale ?? 1));
    for (let j = i + 1; j < bodies.length; j++) {
      const b = bodies[j];
      const r = ra + kmToAu(b.radiusKm * (b.accretionScale ?? 1));
      let dx = b.position.x - a.position.x;
      let dy = b.position.y - a.position.y;
      let dz = b.position.z - a.position.z;
      if (dt > 0) {
        const wx = b.velocity.x - a.velocity.x;
        const wy = b.velocity.y - a.velocity.y;
        const wz = b.velocity.z - a.velocity.z;
        const w2 = wx * wx + wy * wy + wz * wz;
        if (w2 > 0) {
          const t = Math.min(Math.max((dx * wx + dy * wy + dz * wz) / w2, 0), dt);
          dx -= wx * t;
          dy -= wy * t;
          dz -= wz * t;
        }
      }
      if (dx * dx + dy * dy + dz * dz < r * r) return [i, j];
    }
  }
  return null;
}

/**
 * Fusion parfaitement inélastique : le corps le plus massif absorbe l'autre.
 * La masse et la quantité de mouvement sont conservées ; le volume s'additionne.
 * Renvoie [survivant, absorbé]. Le survivant est modifié sur place.
 */
export function mergeBodies(a: Body, b: Body): [Body, Body] {
  const [big, small] = a.mass >= b.mass ? [a, b] : [b, a];
  const m = big.mass + small.mass;
  const w1 = big.mass / m;
  const w2 = small.mass / m;
  big.position = {
    x: big.position.x * w1 + small.position.x * w2,
    y: big.position.y * w1 + small.position.y * w2,
    z: big.position.z * w1 + small.position.z * w2,
  };
  big.velocity = {
    x: big.velocity.x * w1 + small.velocity.x * w2,
    y: big.velocity.y * w1 + small.velocity.y * w2,
    z: big.velocity.z * w1 + small.velocity.z * w2,
  };
  big.mass = m;
  if (big.star && small.star) big.star.luminosity += small.star.luminosity;
  if (big.kind !== 'star') {
    big.radiusKm = Math.cbrt(big.radiusKm ** 3 + small.radiusKm ** 3);
  }
  return [big, small];
}
