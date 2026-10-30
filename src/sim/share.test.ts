import { describe, expect, it } from 'vitest';
import { protoplanetaryDisk, defaultDiskParams } from './disk';
import { solarSystem, tightBinary } from './presets';
import { decodeSystem, encodeSystem, sharedFromHash, shareUrl } from './share';
import { Simulation } from './Simulation';

describe('Partage par lien', () => {
  it('reconstruit le système à partir du lien', async () => {
    const sim = new Simulation(tightBinary());
    sim.stepFor(0.3);
    const url = shareUrl('https://exemple.org/simulateur/#ancien', await encodeSystem(sim));
    expect(url.startsWith('https://exemple.org/simulateur/#systeme=v1.')).toBe(true);
    const def = await decodeSystem(sharedFromHash(new URL(url).hash)!);
    const copy = new Simulation(def, false);
    expect(copy.name).toBe(sim.name);
    expect(copy.time).toBeCloseTo(sim.time, 8);
    expect(copy.stars).toHaveLength(2);
    for (let i = 0; i < sim.bodies.length; i++) {
      expect(copy.bodies[i].id).toBe(sim.bodies[i].id);
      expect(copy.bodies[i].position.x).toBeCloseTo(sim.bodies[i].position.x, 8);
      expect(copy.bodies[i].velocity.y).toBeCloseTo(sim.bodies[i].velocity.y, 7);
    }
  });

  it('produit des liens courts pour les systèmes usuels', async () => {
    expect((await encodeSystem(new Simulation(solarSystem()))).length).toBeLessThan(4000);
    expect((await encodeSystem(new Simulation(protoplanetaryDisk({ ...defaultDiskParams('G'), count: 120 })))).length).toBeLessThan(30000);
  });

  it('explique pourquoi un lien abîmé ne marche pas', async () => {
    const encoded = await encodeSystem(new Simulation(solarSystem()));
    await expect(decodeSystem(encoded.slice(0, encoded.length / 2))).rejects.toThrow(/incomplet ou abîmé/);
    await expect(decodeSystem('v9.abc')).rejects.toThrow(/version inconnue/);
    expect(sharedFromHash('#autre=1')).toBeNull();
  });
});
