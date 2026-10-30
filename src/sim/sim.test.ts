import { describe, expect, it } from 'vitest';
import { currentElements } from '../physics/derived';
import { totalEnergy } from '../physics/nbody';
import { distance } from '../physics/vec3';
import { makeOrbiter, makeStar } from './factory';
import { emptySystem, solarSystem } from './presets';
import { randomSystem } from './random';
import { deserialize, serialize } from './serialization';
import { Simulation } from './Simulation';

const byName = (sim: Simulation, name: string) => sim.bodies.find((b) => b.name === name)!;

describe('Simulation', () => {
  it('garde le système solaire stable sur 10 ans', () => {
    const sim = new Simulation(solarSystem());
    const e0 = totalEnergy(sim.bodies);
    sim.stepFor(10);
    expect(sim.bodies).toHaveLength(16);
    expect(sim.events).toHaveLength(0);
    expect(Math.abs((totalEnergy(sim.bodies) - e0) / e0)).toBeLessThan(1e-4);
    const earth = currentElements(byName(sim, 'Terre'), sim.star!);
    expect(earth.a).toBeCloseTo(1, 1);
    const moon = currentElements(byName(sim, 'Lune'), byName(sim, 'Terre'));
    expect(moon.a * 1.496e8).toBeGreaterThan(370000);
    expect(moon.a * 1.496e8).toBeLessThan(400000);
  });

  it('fusionne deux planètes qui se percutent et le journalise', () => {
    const def = emptySystem('G');
    const star = def.bodies[0];
    const a = makeOrbiter({ name: 'A', planetType: 'tellurique', massEarth: 1, radiusKm: 6371, parentId: star.id, elements: { a: 1, nu: 0 } });
    const b = makeOrbiter({ name: 'B', planetType: 'tellurique', massEarth: 0.5, radiusKm: 5000, parentId: star.id, elements: { a: 1, nu: 180, i: 0.0 } });
    b.elements!.omega = 0;
    // Orbite rétrograde : les deux planètes se rencontrent forcément.
    b.elements!.i = 180;
    def.bodies.push(a, b);
    const sim = new Simulation(def);
    const massBefore = sim.bodies.reduce((s, x) => s + x.mass, 0);
    sim.stepFor(0.6);
    expect(sim.bodies).toHaveLength(2);
    expect(sim.events[0].kind).toBe('collision');
    expect(sim.events[0].message).toContain('A absorbe B');
    expect(sim.bodies.reduce((s, x) => s + x.mass, 0)).toBeCloseTo(massBefore, 12);
  });

  it("conserve la position angulaire d'une planète quand on modifie son orbite", () => {
    const sim = new Simulation(solarSystem());
    sim.stepFor(0.3);
    const mars = byName(sim, 'Mars');
    const before = Math.atan2(mars.position.y - sim.star!.position.y, mars.position.x - sim.star!.position.x);
    sim.updateBody(mars.id, { elements: { ...mars.elements!, a: 2, e: 0, i: 0 } });
    const after = Math.atan2(mars.position.y - sim.star!.position.y, mars.position.x - sim.star!.position.x);
    expect(after).toBeCloseTo(before, 1);
    expect(distance(mars.position, sim.star!.position)).toBeCloseTo(2, 2);
  });

  it("recalcule les orbites quand la classe de l'étoile change", () => {
    const sim = new Simulation(solarSystem());
    sim.setStarClass('M');
    expect(sim.star!.mass).toBeCloseTo(0.3);
    const earth = currentElements(byName(sim, 'Terre'), sim.star!);
    expect(earth.a).toBeCloseTo(1, 2);
    expect(earth.e).toBeLessThan(0.05);
  });

  it('supprime une planète avec ses lunes', () => {
    const sim = new Simulation(solarSystem());
    sim.removeBody(byName(sim, 'Jupiter').id);
    expect(sim.bodies.map((b) => b.name)).not.toContain('Io');
    expect(sim.bodies).toHaveLength(11);
  });

  it("libère une lune placée au-delà du rayon de Hill de sa planète", () => {
    const def = emptySystem('G');
    const star = def.bodies[0];
    const p = makeOrbiter({ name: 'P', planetType: 'tellurique', massEarth: 1, radiusKm: 6371, parentId: star.id, elements: { a: 1 } });
    const m = makeOrbiter({ name: 'M', kind: 'moon', planetType: 'naine', massEarth: 0.01, radiusKm: 1000, parentId: p.id, elements: { a: 0.05 } });
    def.bodies.push(p, m);
    const sim = new Simulation(def);
    sim.stepFor(0.01);
    expect(byName(sim, 'M').parentId).toBe(star.id);
    expect(sim.events.some((e) => e.kind === 'evasion')).toBe(true);
  });

  it("revient à l'état initial avec reset()", () => {
    const sim = new Simulation(solarSystem());
    const start = { ...byName(sim, 'Terre').position };
    sim.stepFor(0.5);
    sim.reset();
    expect(byName(sim, 'Terre').position).toEqual(start);
    expect(sim.time).toBe(0);
  });

  it('respecte le budget de calcul en temps réel', () => {
    const sim = new Simulation(solarSystem());
    sim.setSpeed(1e6);
    const t0 = performance.now();
    sim.advance(1, 20);
    expect(performance.now() - t0).toBeLessThan(200);
    expect(sim.effectiveSpeed).toBeLessThan(1e6);
  });
});

describe('Générateur aléatoire', () => {
  it('est déterministe pour une graine donnée', () => {
    const a = randomSystem(42);
    const b = randomSystem(42);
    expect(a.bodies.map((x) => [x.name, x.mass, x.elements?.a])).toEqual(b.bodies.map((x) => [x.name, x.mass, x.elements?.a]));
  });

  it('produit des systèmes stables sur 5 ans', () => {
    for (const seed of [1, 2, 3, 4, 5, 6, 7, 8]) {
      const sim = new Simulation(randomSystem(seed));
      const planets = sim.bodies.filter((b) => b.kind === 'planet').length;
      expect(planets).toBeGreaterThanOrEqual(3);
      sim.stepFor(5);
      expect(sim.events.filter((e) => e.kind !== 'info')).toEqual([]);
    }
  }, 60000);
});

describe('Sauvegarde', () => {
  it('reproduit exactement le système après sauvegarde et chargement', () => {
    const sim = new Simulation(solarSystem());
    sim.stepFor(0.2);
    const loaded = new Simulation(deserialize(serialize(sim)), false);
    expect(loaded.time).toBeCloseTo(sim.time, 12);
    expect(loaded.bodies.map((b) => b.position)).toEqual(sim.bodies.map((b) => b.position));
  });

  it('refuse un fichier invalide avec un message clair', () => {
    expect(() => deserialize('pas du json')).toThrow("n'est pas un JSON valide");
    expect(() => deserialize('{"format":"autre"}')).toThrow("pas une sauvegarde");
    const star = makeStar('G');
    expect(() => deserialize(JSON.stringify({ format: 'simulateur-systeme-solaire', version: 1, bodies: [star, star] }))).toThrow();
  });
});
