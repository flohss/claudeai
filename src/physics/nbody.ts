import { NBodyState } from './state';
import { G } from './units';
import type { Body } from './types';
import { vec3, type Vec3 } from './vec3';

// Les calculs O(N²) sont faits sur des tableaux typés (voir state.ts) ;
// ces fonctions en sont des raccourcis pour travailler directement sur des corps.
const scratch = new NBodyState();

/** Calcule les accélérations gravitationnelles de chaque corps (UA/an²). */
export function computeAccelerations(bodies: Body[], out: Vec3[]): void {
  scratch.load(bodies);
  scratch.computeAccelerations();
  for (let i = 0; i < bodies.length; i++) {
    out[i].x = scratch.ax[i];
    out[i].y = scratch.ay[i];
    out[i].z = scratch.az[i];
  }
}

export const makeAccelerationBuffer = (n: number): Vec3[] => Array.from({ length: n }, () => vec3());

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

/** Première paire de corps qui se sont touchés pendant le dernier pas `dt` (voir `NBodyState.findCollision`). */
export function findCollision(bodies: Body[], dt = 0): [number, number] | null {
  scratch.load(bodies);
  return scratch.findCollision(dt);
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
