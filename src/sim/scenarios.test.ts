import { describe, expect, it } from 'vitest';
import { currentElements, equilibriumTemperatureFromFlux, stellarFlux } from '../physics/derived';
import { CHICXULUB_MT, MEGATON_J, craterDiameterKm, impactEnergyJ, schwarzschildRadiusKm } from '../physics/impacts';
import { hyperbolicState, mu } from '../physics/orbits';
import { EARTH_MASS_SUN, SUN_MASS_KG } from '../physics/units';
import { distance, dot, length, sub } from '../physics/vec3';
import { makeOrbiter } from './factory';
import { emptySystem, solarSystem } from './presets';
import { deserialize, serialize } from './serialization';
import { KM_S, Simulation } from './Simulation';

const byName = (sim: Simulation, name: string) => sim.bodies.find((b) => b.name === name)!;
const sunAndEarth = () => {
  const def = emptySystem('G');
  def.bodies[0].name = 'Soleil';
  def.bodies.push(makeOrbiter({ name: 'Terre', planetType: 'tellurique', massEarth: 1, radiusKm: 6371, parentId: def.bodies[0].id, elements: { a: 1 } }));
  return new Simulation(def);
};
/** Énergie orbitale spécifique de la planète par rapport à l'étoile (< 0 : liée). */
const boundEnergy = (sim: Simulation, planet: string) => {
  const p = byName(sim, planet);
  const s = sim.star!;
  const r = sub(p.position, s.position);
  const v = sub(p.velocity, s.velocity);
  return dot(v, v) / 2 - mu(s.mass, p.mass) / length(r);
};

describe('Physique des événements', () => {
  it('place un corps sur une hyperbole qui passe à la distance voulue', () => {
    const m = mu(1, 0);
    const s = hyperbolicState(2, 30 * KM_S, 50, { i: 10, Omega: 30, omega: 60 }, m);
    expect(length(s.position)).toBeCloseTo(50, 6);
    // Énergie = v∞² / 2
    expect(dot(s.velocity, s.velocity) / 2 - m / length(s.position)).toBeCloseTo((30 * KM_S) ** 2 / 2, 6);
    // Le corps se dirige vers l'étoile
    expect(dot(s.position, s.velocity)).toBeLessThan(0);
    const el = currentElements({ ...emptySystem().bodies[0], position: s.position, velocity: s.velocity, mass: 0 }, { position: { x: 0, y: 0, z: 0 }, velocity: { x: 0, y: 0, z: 0 }, mass: 1 });
    expect(el.a * (1 - el.e)).toBeCloseTo(2, 6);
    expect(s.timeToPeriapsis).toBeGreaterThan(0);
  });

  it("donne l'ordre de grandeur de Chicxulub et de Meteor Crater", () => {
    const m = (3000 * (4 / 3) * Math.PI * 5000 ** 3) / SUN_MASS_KG;
    const mt = impactEnergyJ(EARTH_MASS_SUN, m, 20 * KM_S) / MEGATON_J;
    expect(mt / CHICXULUB_MT).toBeGreaterThan(0.3);
    expect(mt / CHICXULUB_MT).toBeLessThan(3);
    const chicxulub = craterDiameterKm(10, 20, 9.81);
    expect(chicxulub).toBeGreaterThan(80);
    expect(chicxulub).toBeLessThan(250);
    const meteor = craterDiameterKm(0.05, 12.8, 9.81, 7800);
    expect(meteor).toBeGreaterThan(0.6);
    expect(meteor).toBeLessThan(2);
    expect(schwarzschildRadiusKm(1)).toBeCloseTo(2.95, 2);
  });
});

describe('Intrus', () => {
  it('fait traverser le système par un trou noir qui déchire la planète trop proche', () => {
    const sim = sunAndEarth();
    const eta = sim.launchIntruder({ id: 'tn', name: 'Trou noir', type: 'trou-noir', mass: 10, periapsisAu: 1, speedKmS: 30, i: 0, Omega: 0, omega: 0 });
    expect(eta).toBeGreaterThan(1);
    const bh = sim.getBody('tn')!;
    expect(bh.star?.remnant).toBe('trou-noir');
    expect(bh.intruder).toBe(true);
    // Le trou noir n'est pas une étoile du système et n'éclaire rien.
    expect(sim.stars.map((s) => s.name)).toEqual(['Soleil']);
    expect(sim.luminousBodies.map((s) => s.name)).toEqual(['Soleil']);
    const before = currentElements(byName(sim, 'Terre'), sim.star!);
    sim.stepFor(eta + 2);
    // Un trou noir de 10 M☉ qui frôle l'orbite terrestre la bouleverse forcément.
    const earth = sim.bodies.find((b) => b.name === 'Terre');
    if (earth && sim.star && boundEnergy(sim, 'Terre') < 0) {
      const after = currentElements(earth, sim.star);
      expect(Math.abs(after.a - before.a) + Math.abs(after.e - before.e)).toBeGreaterThan(0.1);
    }
  });

  it('spaghettifie un corps qui passe sous le rayon de marée', () => {
    const sim = sunAndEarth();
    sim.launchIntruder({ id: 'tn', name: 'Trou noir', type: 'trou-noir', mass: 10, periapsisAu: 0.02, speedKmS: 30, i: 0, Omega: 0, omega: 0 });
    // On place le trou noir juste à côté de la Terre.
    const bh = sim.getBody('tn')!;
    const earth = byName(sim, 'Terre');
    const massBefore = bh.mass;
    sim.updateBody(bh.id, {});
    bh.position = { ...earth.position, x: earth.position.x + 0.03 };
    bh.velocity = { ...earth.velocity };
    sim.updateBody(bh.id, {});
    sim.stepFor(0.001);
    expect(sim.bodies.some((b) => b.name === 'Terre')).toBe(false);
    expect(sim.events[0].kind).toBe('maree');
    expect(sim.events[0].message).toContain('spaghettification');
    expect(bh.mass).toBeCloseTo(massBefore + EARTH_MASS_SUN, 12);
  });

  it("fait repartir pour de bon l'étoile de passage", () => {
    const sim = sunAndEarth();
    const eta = sim.launchIntruder({ id: 'e', name: 'Étoile de passage', type: 'etoile', mass: 0.7, spectralClass: 'K', periapsisAu: 30, speedKmS: 400, i: 30, Omega: 0, omega: 0 });
    // Pendant le passage, elle éclaire aussi la Terre.
    expect(sim.luminousBodies).toHaveLength(2);
    sim.stepFor(eta + 1000 / (400 * KM_S));
    expect(sim.getBody('e')).toBeUndefined();
    expect(sim.events[0].message).toContain("s'éloigne définitivement");
    // Passage lointain et rapide : la Terre reste en orbite.
    expect(currentElements(byName(sim, 'Terre'), sim.star!).a).toBeCloseTo(1, 1);
  });
});

describe('Impacts', () => {
  it("décrit l'impact de Chicxulub sur la Terre", () => {
    const sim = new Simulation(solarSystem());
    const earth = byName(sim, 'Terre');
    const massBefore = earth.mass;
    const m = (3000 * (4 / 3) * Math.PI * 5000 ** 3) / SUN_MASS_KG;
    sim.launchImpactor({ id: 'ast', targetId: earth.id, name: 'Chicxulub', diameterKm: 10, mass: m, speedKmS: 20, azimuth: 120, elevation: 5 });
    sim.stepFor(0.01);
    expect(sim.getBody('ast')).toBeUndefined();
    const e = sim.events.find((x) => x.kind === 'impact')!;
    expect(e.message).toMatch(/Impact de Chicxulub sur Terre/);
    expect(e.message).toMatch(/Mt de TNT/);
    expect(e.message).toMatch(/cratère d'environ/);
    expect(e.message).toMatch(/extinction de masse/);
    expect(e.flash).toBe('impact');
    expect(earth.mass).toBeCloseTo(massBefore + m, 18);
  });

  it("forme une lune lors d'un impact géant, comme Théia", () => {
    const sim = sunAndEarth();
    const earth = byName(sim, 'Terre');
    const theia = 0.1 * EARTH_MASS_SUN;
    const total = sim.bodies.reduce((s, b) => s + b.mass, 0) + theia;
    sim.launchImpactor({ id: 'theia', targetId: earth.id, name: 'Théia', diameterKm: 6780, mass: theia, speedKmS: 4, azimuth: 0, elevation: 0 });
    sim.stepFor(0.01);
    const e = sim.events.find((x) => x.kind === 'impact')!;
    expect(e.message).toMatch(/Impact géant/);
    expect(e.message).toMatch(/naissance/);
    const moon = sim.bodies.find((b) => b.kind === 'moon')!;
    expect(moon.parentId).toBe(earth.id);
    expect(sim.bodies.reduce((s, b) => s + b.mass, 0)).toBeCloseTo(total, 14);
    sim.stepFor(0.05);
    expect(sim.bodies.some((b) => b.kind === 'moon')).toBe(true);
  });
});

describe("Destin de l'étoile", () => {
  it('libère la Terre si le Soleil perd plus de la moitié de sa masse', () => {
    const sim = sunAndEarth();
    expect(boundEnergy(sim, 'Terre')).toBeLessThan(0);
    sim.supernova(sim.star!.id, 0.4);
    expect(sim.star!.star!.remnant).toBe('naine-blanche');
    expect(boundEnergy(sim, 'Terre')).toBeGreaterThan(0);
    expect(sim.events[0].flash).toBe('supernova');
    sim.stepFor(0.1);
    sim.stepFor(0.1);
    // Signalé tout de suite, et une seule fois.
    expect(sim.events.filter((e) => e.message === "Terre n'est plus retenue par Soleil : elle quitte le système.")).toHaveLength(1);

    const sim2 = sunAndEarth();
    sim2.supernova(sim2.star!.id, 0.6);
    expect(boundEnergy(sim2, 'Terre')).toBeLessThan(0);
  });

  it("ne change pas l'orbite quand l'étoile devient un trou noir de même masse", () => {
    const sim = sunAndEarth();
    sim.collapseToBlackHole(sim.star!.id);
    sim.stepFor(1);
    const el = currentElements(byName(sim, 'Terre'), sim.star!);
    expect(el.a).toBeCloseTo(1, 3);
    const flux = stellarFlux(byName(sim, 'Terre'), sim.luminousBodies);
    expect(flux).toBe(0);
    expect(equilibriumTemperatureFromFlux(flux, 0.3)).toBeCloseTo(2.725, 2);
  });

  it('fait gonfler le Soleil en géante rouge qui engloutit les planètes proches', () => {
    const sim = new Simulation(solarSystem());
    for (const moon of sim.bodies.filter((b) => b.kind === 'moon')) sim.removeBody(moon.id);
    const marsA0 = currentElements(byName(sim, 'Mars'), sim.star!).a;
    sim.startRedGiant(sim.star!.id, 10);
    sim.stepFor(5);
    expect(sim.star!.radiusKm).toBeGreaterThan(10 * 695700);
    sim.stepFor(5.5);
    const swallowed = sim.events.filter((e) => e.message.includes('engloutie')).map((e) => e.message);
    expect(swallowed.some((m) => m.startsWith('Mercure'))).toBe(true);
    expect(swallowed.some((m) => m.startsWith('Vénus'))).toBe(true);
    // Le Soleil a perdu de la masse : l'orbite de Mars s'est élargie.
    expect(currentElements(byName(sim, 'Mars'), sim.star!).a).toBeGreaterThan(marsA0 * 1.3);
    expect(sim.star!.star!.remnant).toBe('naine-blanche');
    expect(sim.evolutions).toHaveLength(0);
  });

  it("libère une planète poussée au-delà de la vitesse de libération", () => {
    const sim = sunAndEarth();
    sim.applyImpulse(byName(sim, 'Terre').id, 13, 'prograde');
    expect(boundEnergy(sim, 'Terre')).toBeGreaterThan(0);
    const sim2 = sunAndEarth();
    sim2.applyImpulse(byName(sim2, 'Terre').id, 5, 'prograde');
    const el = currentElements(byName(sim2, 'Terre'), sim2.star!);
    expect(el.a).toBeGreaterThan(1.2);
  });

  it("laisse les planètes lointaines derrière une étoile expulsée, emmène les proches", () => {
    const def = emptySystem('G');
    const star = def.bodies[0];
    def.bodies.push(
      makeOrbiter({ name: 'Proche', planetType: 'tellurique', massEarth: 1, radiusKm: 6371, parentId: star.id, elements: { a: 0.1 } }),
      makeOrbiter({ name: 'Lointaine', planetType: 'tellurique', massEarth: 1, radiusKm: 6371, parentId: star.id, elements: { a: 30 } }),
    );
    const sim = new Simulation(def);
    sim.applyImpulse(sim.star!.id, 20, 'perpendiculaire');
    expect(boundEnergy(sim, 'Proche')).toBeLessThan(0);
    expect(boundEnergy(sim, 'Lointaine')).toBeGreaterThan(0);
  });
});

describe('Sauvegarde des événements', () => {
  it('reprend une géante rouge en cours et les intrus', () => {
    const sim = sunAndEarth();
    sim.startRedGiant(sim.star!.id, 10);
    sim.launchIntruder({ id: 'tn', name: 'Trou noir', type: 'trou-noir', mass: 5, periapsisAu: 50, speedKmS: 30, i: 0, Omega: 0, omega: 0 });
    sim.stepFor(1);
    const copy = new Simulation(deserialize(serialize(sim)), false);
    expect(copy.evolutions).toHaveLength(1);
    expect(copy.getBody('tn')?.intruder).toBe(true);
    expect(copy.star!.name).toBe('Soleil');
    expect(distance(copy.getBody('tn')!.position, sim.getBody('tn')!.position)).toBe(0);
  });
});
