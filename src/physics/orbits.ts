import { G, degToRad, radToDeg } from './units';
import type { OrbitalElements } from './types';
import { cross, dot, length, scale, sub, type Vec3 } from './vec3';

/** Paramètre gravitationnel μ = G(M + m) */
export const mu = (parentMass: number, mass: number) => G * (parentMass + mass);

/** Convertit des éléments orbitaux en position/vitesse relatives au parent. */
export function elementsToState(el: OrbitalElements, muValue: number): { position: Vec3; velocity: Vec3 } {
  const e = Math.min(Math.max(el.e, 0), 0.99);
  const nu = degToRad(el.nu);
  const p = el.a * (1 - e * e);
  const r = p / (1 + e * Math.cos(nu));

  const px = r * Math.cos(nu);
  const py = r * Math.sin(nu);
  const k = Math.sqrt(muValue / p);
  const vx = -k * Math.sin(nu);
  const vy = k * (e + Math.cos(nu));

  const cO = Math.cos(degToRad(el.Omega));
  const sO = Math.sin(degToRad(el.Omega));
  const cw = Math.cos(degToRad(el.omega));
  const sw = Math.sin(degToRad(el.omega));
  const ci = Math.cos(degToRad(el.i));
  const si = Math.sin(degToRad(el.i));

  const r11 = cO * cw - sO * sw * ci;
  const r12 = -cO * sw - sO * cw * ci;
  const r21 = sO * cw + cO * sw * ci;
  const r22 = -sO * sw + cO * cw * ci;
  const r31 = sw * si;
  const r32 = cw * si;

  return {
    position: { x: r11 * px + r12 * py, y: r21 * px + r22 * py, z: r31 * px + r32 * py },
    velocity: { x: r11 * vx + r12 * vy, y: r21 * vx + r22 * vy, z: r31 * vx + r32 * vy },
  };
}

const EPS = 1e-9;
const wrap360 = (deg: number) => ((deg % 360) + 360) % 360;
const safeAcos = (x: number) => Math.acos(Math.min(1, Math.max(-1, x)));

/**
 * Éléments osculateurs à partir d'un état relatif.
 * Pour une trajectoire non liée (énergie ≥ 0), `a` est négatif ou infini.
 */
export function stateToElements(r: Vec3, v: Vec3, muValue: number): OrbitalElements {
  const rLen = length(r);
  const v2 = dot(v, v);
  const h = cross(r, v);
  const hLen = length(h);
  const n: Vec3 = { x: -h.y, y: h.x, z: 0 };
  const nLen = length(n);

  const eVec = scale(sub(scale(r, v2 - muValue / rLen), scale(v, dot(r, v))), 1 / muValue);
  const e = length(eVec);
  const energy = v2 / 2 - muValue / rLen;
  const a = Math.abs(energy) < 1e-14 ? Infinity : -muValue / (2 * energy);
  const i = hLen > 0 ? radToDeg(safeAcos(h.z / hLen)) : 0;

  let Omega = 0;
  if (nLen > EPS) {
    Omega = radToDeg(Math.atan2(n.y, n.x));
  }

  let omega = 0;
  let nu: number;
  if (e > EPS) {
    if (nLen > EPS) {
      omega = radToDeg(safeAcos(dot(n, eVec) / (nLen * e)));
      if (eVec.z < 0) omega = 360 - omega;
    } else {
      omega = radToDeg(Math.atan2(eVec.y, eVec.x));
      if (h.z < 0) omega = 360 - omega;
    }
    nu = radToDeg(safeAcos(dot(eVec, r) / (e * rLen)));
    if (dot(r, v) < 0) nu = 360 - nu;
  } else if (nLen > EPS) {
    nu = radToDeg(safeAcos(dot(n, r) / (nLen * rLen)));
    if (r.z < 0) nu = 360 - nu;
  } else {
    nu = radToDeg(Math.atan2(r.y, r.x));
  }

  return { a, e, i, Omega: wrap360(Omega), omega: wrap360(omega), nu: wrap360(nu) };
}

/** Période orbitale képlérienne (années). */
export function orbitalPeriod(a: number, parentMass: number, mass = 0): number {
  return 2 * Math.PI * Math.sqrt((a * a * a) / mu(parentMass, mass));
}

/** Rayon de Hill : zone où la gravité du corps domine celle de son parent (UA). */
export function hillRadius(a: number, e: number, mass: number, parentMass: number): number {
  return a * (1 - e) * Math.cbrt(mass / (3 * parentMass));
}
