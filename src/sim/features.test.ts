import { describe, expect, it } from 'vitest';
import { currentElements } from '../physics/derived';
import { EARTH_MASS_SUN } from '../physics/units';
import { distance } from '../physics/vec3';
import { defaultDiskParams, protoplanetaryDisk } from './disk';
import { makeOrbiter } from './factory';
import { emptySystem, solarSystem, tightBinary, wideBinary } from './presets';
import { deserialize, serialize } from './serialization';
import { Simulation } from './Simulation';
import { binaryStability } from './stability';
import { MAX_SAMPLES, Telemetry } from './telemetry';

const byName = (sim: Simulation, name: string) => sim.bodies.find((b) => b.name.startsWith(name))!;
const totalMass = (sim: Simulation) => sim.bodies.reduce((s, b) => s + b.mass, 0);

describe('Systèmes doubles', () => {
  it('place Kepler-16 b autour du barycentre et la garde stable', () => {
    const sim = new Simulation(tightBinary());
    const planet = byName(sim, 'Kepler-16 b');
    expect(distance(planet.position, sim.starsFrame().position)).toBeCloseTo(0.705, 1);
    sim.stepFor(20);
    expect(sim.events).toEqual([]);
    const el = currentElements(planet, sim.starsFrame());
    expect(el.a).toBeGreaterThan(0.68);
    expect(el.a).toBeLessThan(0.72);
    const stability = binaryStability(sim, planet)!;
    expect(stability.kind).toBe('P');
    expect(stability.stable).toBe(true);
    expect(stability.limitAu).toBeGreaterThan(0.6);
  });

  it("garde les planètes d'Alpha du Centaure stables sur 100 ans", () => {
    const sim = new Simulation(wideBinary());
    sim.stepFor(100);
    expect(sim.events).toEqual([]);
    for (const name of ['Centauri A b', 'Centauri A c', 'Centauri B b']) {
      expect(binaryStability(sim, byName(sim, name))!.stable).toBe(true);
    }
  });

  it('déstabilise une planète quand une compagne arrive trop près', () => {
    const def = emptySystem('G');
    def.bodies.push(makeOrbiter({ name: 'P', planetType: 'tellurique', massEarth: 1, radiusKm: 6371, parentId: def.bodies[0].id, elements: { a: 1 } }));
    const sim = new Simulation(def);
    sim.addCompanion('K', 1.8, 0.2);
    expect(sim.stars).toHaveLength(2);
    expect(binaryStability(sim, byName(sim, 'P'))!.stable).toBe(false);
    sim.stepFor(30);
    expect(sim.events.some((e) => ['evasion', 'ejection', 'collision'].includes(e.kind))).toBe(true);
  });

  it("recalcule l'orbite d'une planète circumbinaire quand une étoile change de classe", () => {
    const sim = new Simulation(tightBinary());
    const b = sim.stars.find((s) => s.parentId)!;
    sim.setStarClass(b.id, 'K');
    const el = currentElements(byName(sim, 'Kepler-16 b'), sim.starsFrame());
    expect(el.a).toBeCloseTo(0.705, 1);
    expect(el.e).toBeLessThan(0.05);
  });
});

describe('Limite de Roche', () => {
  it('disloque une lune trop proche en anneau, sans perte de masse', () => {
    const def = emptySystem('G');
    const planet = makeOrbiter({ name: 'Géante', planetType: 'geante-gazeuse', massEarth: 300, radiusKm: 70000, parentId: def.bodies[0].id, elements: { a: 5 } });
    const moon = makeOrbiter({ name: 'Lunette', kind: 'moon', planetType: 'naine', massEarth: 0.01, radiusKm: 1500, parentId: planet.id, elements: { a: 100000 / 1.496e8 } });
    def.bodies.push(planet, moon);
    const sim = new Simulation(def);
    const mass = totalMass(sim);
    sim.stepFor(0.001);
    expect(sim.bodies.map((b) => b.name)).not.toContain('Lunette');
    const p = byName(sim, 'Géante');
    expect(p.rings).toBeDefined();
    expect(p.rings!.outer).toBeGreaterThan(p.rings!.inner);
    expect(totalMass(sim)).toBeCloseTo(mass, 14);
    expect(sim.events[0].kind).toBe('roche');
  });
});

describe('Formation planétaire', () => {
  it('génère un disque déterministe dont la masse solide est celle demandée', () => {
    const params = { ...defaultDiskParams('G'), seed: 3, count: 50, massEarth: 20 };
    const a = protoplanetaryDisk(params);
    const b = protoplanetaryDisk(params);
    expect(a.bodies.map((x) => x.elements?.a)).toEqual(b.bodies.map((x) => x.elements?.a));
    const solid = a.bodies.filter((x) => x.kind === 'planetesimal').reduce((s, x) => s + x.mass, 0) / EARTH_MASS_SUN;
    expect(solid).toBeCloseTo(20, 8);
    expect(a.bodies.filter((x) => x.kind === 'planetesimal')).toHaveLength(50);
  });

  it('fait fusionner les planétésimaux en protoplanètes en conservant la masse', () => {
    const sim = new Simulation(protoplanetaryDisk({ ...defaultDiskParams('G'), seed: 5, count: 60, massEarth: 30, accretionScale: 1500, gas: false }));
    const mass = totalMass(sim);
    sim.stepFor(60);
    expect(sim.bodies.length).toBeLessThan(61);
    expect(sim.bodies.some((b) => b.kind === 'planet')).toBe(true);
    expect(sim.events.some((e) => e.kind === 'formation')).toBe(true);
    // Les planétésimaux éjectés emportent leur masse ; sinon elle est conservée.
    if (!sim.events.some((e) => e.kind === 'ejection')) expect(totalMass(sim)).toBeCloseTo(mass, 12);
  }, 60000);

  it("fait capturer du gaz aux noyaux massifs tant que le disque n'est pas dissipé", () => {
    const def = emptySystem('G');
    const core = makeOrbiter({ name: 'Noyau', planetType: 'geante-glace', massEarth: 8, radiusKm: 20000, parentId: def.bodies[0].id, elements: { a: 5 } });
    core.accretionScale = 1;
    def.bodies.push(core);
    def.formation = { gasUntil: 60, gasTimescale: 10, coreMassEarth: 3, maxGiantMassEarth: 320 };
    const sim = new Simulation(def);
    sim.stepFor(40);
    const giant = byName(sim, 'Noyau');
    expect(giant.planetType).toBe('geante-gazeuse');
    expect(sim.events.some((e) => e.message.includes('capture le gaz'))).toBe(true);
    sim.stepFor(30);
    const massAfterGas = giant.mass;
    sim.stepFor(20);
    expect(giant.mass).toBe(massAfterGas);
    expect(sim.events.some((e) => e.message.includes('se dissipe'))).toBe(true);
  }, 30000);
});

describe('Télémétrie', () => {
  it("enregistre l'énergie et les orbites, et borne la taille de l'historique", () => {
    const sim = new Simulation(tightBinary());
    const t = new Telemetry();
    for (let k = 0; k < MAX_SAMPLES + 150; k++) {
      sim.stepFor(0.01);
      t.record(sim);
    }
    expect(t.times.length).toBeLessThanOrEqual(MAX_SAMPLES);
    expect(t.times[0]).toBeCloseTo(0.01, 6);
    expect(t.times[t.times.length - 1]).toBeCloseTo(sim.time, 9);
    expect(Math.max(...t.energyDrift.map(Math.abs))).toBeLessThan(0.01);
    const kepler = [...t.bodies.values()].find((s) => s.name === 'Kepler-16 b')!;
    expect(kepler.eccentricity).toHaveLength(t.times.length);
    expect(kepler.semiMajorAxis.at(-1)).toBeCloseTo(0.705, 1);
  });

  it("signale les changements de structure et repart de zéro à chaque chargement", () => {
    const sim = new Simulation(solarSystem());
    const t = new Telemetry();
    sim.stepFor(0.01);
    t.record(sim);
    sim.removeBody(byName(sim, 'Mars').id);
    sim.stepFor(0.01);
    t.record(sim);
    expect(t.markers).toHaveLength(1);
    sim.load(tightBinary());
    sim.stepFor(0.01);
    t.record(sim);
    expect(t.times).toHaveLength(1);
    expect(t.markers).toHaveLength(0);
  });
});

describe('Sauvegarde des nouveautés', () => {
  it('conserve étoiles compagnes, anneaux et paramètres de formation', () => {
    const def = tightBinary();
    def.formation = { gasUntil: 100, gasTimescale: 20, coreMassEarth: 3, maxGiantMassEarth: 320 };
    const sim = new Simulation(def);
    sim.stepFor(0.1);
    const loaded = new Simulation(deserialize(serialize(sim)), false);
    expect(loaded.stars).toHaveLength(2);
    expect(loaded.formation).toEqual(def.formation);
    expect(byName(loaded, 'Kepler-16 b').circumbinary).toBe(true);
    const solar = new Simulation(deserialize(serialize(new Simulation(solarSystem()))), false);
    expect(byName(solar, 'Saturne').rings?.outer).toBeCloseTo(2.27);
  });
});
