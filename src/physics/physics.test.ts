import { describe, expect, it } from 'vitest';
import { pTypeCriticalAu, sTypeCriticalAu } from './binary';
import { density, equilibriumTemperature, equilibriumTemperatureFromFlux, escapeVelocity, rocheLimitKm, stellarFlux, surfaceGravity, zoneStatus } from './derived';
import { mergeBodies, recenter, totalEnergy, totalMomentum } from './nbody';
import { NBodyState } from './state';
import { elementsToState, mu, orbitalPeriod, stateToElements } from './orbits';
import { habitableZone, snowLine } from './stars';
import type { Body } from './types';
import { EARTH_MASS_SUN } from './units';
import { add, distance, length } from './vec3';

const body = (id: string, mass: number, radiusKm: number): Body => ({
  id,
  name: id,
  kind: 'planet',
  mass,
  radiusKm,
  color: '#fff',
  albedo: 0.3,
  parentId: null,
  elements: null,
  position: { x: 0, y: 0, z: 0 },
  velocity: { x: 0, y: 0, z: 0 },
});

describe('mécanique orbitale', () => {
  it("donne une période d'un an pour la Terre", () => {
    expect(orbitalPeriod(1, 1)).toBeCloseTo(1, 6);
  });

  it('place un corps circulaire à la bonne vitesse (2π UA/an à 1 UA)', () => {
    const s = elementsToState({ a: 1, e: 0, i: 0, Omega: 0, omega: 0, nu: 0 }, mu(1, 0));
    expect(length(s.position)).toBeCloseTo(1, 10);
    expect(length(s.velocity)).toBeCloseTo(2 * Math.PI, 10);
  });

  it('retrouve les éléments orbitaux après conversion aller-retour', () => {
    const el = { a: 2.3, e: 0.21, i: 12, Omega: 40, omega: 75, nu: 130 };
    const m = mu(1, 0.001);
    const s = elementsToState(el, m);
    const back = stateToElements(s.position, s.velocity, m);
    expect(back.a).toBeCloseTo(el.a, 8);
    expect(back.e).toBeCloseTo(el.e, 8);
    expect(back.i).toBeCloseTo(el.i, 6);
    expect(back.Omega).toBeCloseTo(el.Omega, 6);
    expect(back.omega).toBeCloseTo(el.omega, 6);
    expect(back.nu).toBeCloseTo(el.nu, 6);
  });
});

describe('intégrateur N corps', () => {
  const twoBody = (e: number) => {
    const star = body('etoile', 1, 695700);
    const planet = body('planete', EARTH_MASS_SUN, 6371);
    const s = elementsToState({ a: 1, e, i: 0, Omega: 0, omega: 0, nu: 0 }, mu(star.mass, planet.mass));
    planet.position = s.position;
    planet.velocity = s.velocity;
    const bodies = [star, planet];
    recenter(bodies);
    return bodies;
  };

  it("ramène la planète à son point de départ après une période", () => {
    const bodies = twoBody(0.3);
    const start = { ...bodies[1].position };
    const state = new NBodyState();
    state.load(bodies);
    state.computeAccelerations();
    const period = orbitalPeriod(1, 1, EARTH_MASS_SUN);
    const steps = 4000;
    for (let k = 0; k < steps; k++) state.step(period / steps);
    state.store(bodies);
    expect(distance(bodies[1].position, start)).toBeLessThan(1e-3);
  });

  it("conserve l'énergie et la quantité de mouvement sur 100 orbites", () => {
    const bodies = twoBody(0.1);
    const state = new NBodyState();
    state.load(bodies);
    state.computeAccelerations();
    const e0 = totalEnergy(bodies);
    for (let k = 0; k < 100 * 400; k++) state.step(1 / 400);
    state.store(bodies);
    expect(Math.abs((totalEnergy(bodies) - e0) / e0)).toBeLessThan(1e-4);
    expect(length(totalMomentum(bodies))).toBeLessThan(1e-12);
  });

  it('conserve masse et quantité de mouvement lors d\'une fusion', () => {
    const a = body('a', 2e-6, 6000);
    const b = body('b', 1e-6, 3000);
    a.velocity = { x: 1, y: 0, z: 0 };
    b.velocity = { x: -1, y: 2, z: 0 };
    const p0 = add(totalMomentum([a]), totalMomentum([b]));
    const [survivor, absorbed] = mergeBodies(a, b);
    expect(survivor).toBe(a);
    expect(absorbed).toBe(b);
    expect(survivor.mass).toBeCloseTo(3e-6, 15);
    const p1 = totalMomentum([survivor]);
    expect(p1.x).toBeCloseTo(p0.x, 15);
    expect(p1.y).toBeCloseTo(p0.y, 15);
    expect(survivor.radiusKm).toBeCloseTo(Math.cbrt(6000 ** 3 + 3000 ** 3), 6);
  });
});

describe('état compact', () => {
  it('donne les mêmes accélérations que la somme directe sur les objets', () => {
    const bodies = [body('a', 1, 695700), body('b', 1e-3, 70000), body('c', 3e-6, 6371)];
    bodies[1].position = { x: 5.2, y: 0.3, z: 0.1 };
    bodies[2].position = { x: -0.7, y: 0.7, z: 0 };
    const state = new NBodyState();
    state.load(bodies);
    state.computeAccelerations();
    // Accélération de c, calculée à la main
    let ax = 0;
    for (const o of [bodies[0], bodies[1]]) {
      const dx = o.position.x - bodies[2].position.x;
      const dy = o.position.y - bodies[2].position.y;
      const dz = o.position.z - bodies[2].position.z;
      const d = Math.hypot(dx, dy, dz);
      ax += (4 * Math.PI * Math.PI * o.mass * dx) / d ** 3;
    }
    expect(state.ax[2]).toBeCloseTo(ax, 12);
  });

  it('détecte deux corps qui se croisent entre deux pas', () => {
    const a = body('a', 1e-6, 6371);
    const b = body('b', 1e-6, 6371);
    a.position = { x: -0.01, y: 0, z: 0 };
    b.position = { x: 0.01, y: 0, z: 0 };
    a.velocity = { x: -10, y: 0, z: 0 };
    b.velocity = { x: 10, y: 0, z: 0 };
    const state = new NBodyState();
    state.load([a, b]);
    // Ils viennent de se croiser (ils s'éloignent) : seul le test continu le voit.
    expect(state.findCollision(0)).toBeNull();
    expect(state.findCollision(0.002)).toEqual([0, 1]);
  });
});

describe('grandeurs physiques', () => {
  const earthMass = EARTH_MASS_SUN;
  it('calcule la gravité terrestre', () => {
    expect(surfaceGravity(earthMass, 6371)).toBeCloseTo(9.82, 1);
  });
  it('calcule la vitesse de libération terrestre', () => {
    expect(escapeVelocity(earthMass, 6371)).toBeCloseTo(11.2, 1);
  });
  it('calcule la masse volumique terrestre', () => {
    expect(density(earthMass, 6371)).toBeCloseTo(5.51, 1);
  });
  it("donne ~255 K comme température d'équilibre de la Terre", () => {
    expect(equilibriumTemperature(1, 1, 0.306)).toBeGreaterThan(250);
    expect(equilibriumTemperature(1, 1, 0.306)).toBeLessThan(258);
  });
  it('place la Terre dans la zone habitable, Vénus et Mars en dehors', () => {
    const hz = habitableZone(1);
    expect(hz.inner).toBeLessThan(1);
    expect(hz.outer).toBeGreaterThan(1);
    expect(zoneStatus(1, 1)).toBe('habitable');
    expect(zoneStatus(1, 0.72)).toBe('trop-chaud');
    expect(zoneStatus(1, 1.52)).toBe('trop-froid');
  });
  it('situe la ligne des glaces vers 2,7 UA pour le Soleil', () => {
    expect(snowLine(1)).toBeCloseTo(2.7, 5);
  });
});

describe('systèmes doubles et marées', () => {
  it('donne les limites de stabilité de Holman-Wiegert pour une binaire circulaire de masses égales', () => {
    expect(sTypeCriticalAu(1, 0, 0.5)).toBeCloseTo(0.274, 3);
    expect(pTypeCriticalAu(1, 0, 0.5)).toBeCloseTo(2.3875, 3);
  });

  it('additionne le flux de deux étoiles', () => {
    const a = { ...body('a', 1, 695700), kind: 'star' as const, star: { spectralClass: 'G' as const, luminosity: 1, temperatureK: 5778 } };
    const b = { ...a, id: 'b', position: { x: 2, y: 0, z: 0 } };
    const p = body('p', EARTH_MASS_SUN, 6371);
    p.position = { x: 1, y: 0, z: 0 };
    expect(stellarFlux(p, [a, b])).toBeCloseTo(2, 10);
    expect(equilibriumTemperatureFromFlux(2, 0.3)).toBeCloseTo(equilibriumTemperature(1, 1, 0.3) * Math.pow(2, 0.25), 6);
  });

  it('place la limite de Roche Terre-Lune vers 18 400 km', () => {
    const roche = rocheLimitKm(6371, density(EARTH_MASS_SUN, 6371), 3.34);
    expect(roche).toBeGreaterThan(18000);
    expect(roche).toBeLessThan(19000);
  });

  it('additionne les luminosités quand deux étoiles fusionnent', () => {
    const a = { ...body('a', 1, 695700), kind: 'star' as const, star: { spectralClass: 'G' as const, luminosity: 1, temperatureK: 5778 } };
    const b = { ...body('b', 0.5, 400000), kind: 'star' as const, star: { spectralClass: 'K' as const, luminosity: 0.2, temperatureK: 4600 } };
    mergeBodies(a, b);
    expect(a.star.luminosity).toBeCloseTo(1.2, 10);
  });
});
