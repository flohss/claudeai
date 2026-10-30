import { describe, expect, it } from 'vitest';
import { SimulationClient } from './client';
import { tightBinary, solarSystem } from './presets';
import type { Port } from './protocol';
import { SimulationServer } from './server';

/** Deux ports reliés en mémoire ; les messages sont copiés comme par un vrai Worker. */
function channel(): [Port, Port, () => void] {
  const queue: (() => void)[] = [];
  const a: Port = { onmessage: null, postMessage: (m) => queue.push(() => b.onmessage?.({ data: structuredClone(m) } as MessageEvent)) };
  const b: Port = { onmessage: null, postMessage: (m) => queue.push(() => a.onmessage?.({ data: structuredClone(m) } as MessageEvent)) };
  const flush = () => {
    while (queue.length) queue.shift()!();
  };
  return [a, b, flush];
}

function setup() {
  const [clientPort, serverPort, flush] = channel();
  const server = new SimulationServer(serverPort, Infinity);
  const client = new SimulationClient(clientPort);
  return { server, client, flush };
}

describe('Simulation dans un Worker', () => {
  it("reflète dans le miroir l'état calculé par le Worker", () => {
    const { server, client, flush } = setup();
    client.load(solarSystem());
    flush();
    expect(server.sim.bodies).toHaveLength(16);
    client.setSpeed(365.25);
    flush();
    server.tick(0.5);
    flush();
    expect(client.time).toBeCloseTo(0.5, 9);
    const earthServer = server.sim.bodies.find((b) => b.name === 'Terre')!;
    const earthClient = client.bodies.find((b) => b.name === 'Terre')!;
    expect(earthClient.position).toEqual(earthServer.position);
    expect(earthClient.velocity).toEqual(earthServer.velocity);
  });

  it("ne fait pas de calcul sur le fil principal", () => {
    const { client } = setup();
    client.load(solarSystem());
    client.advance();
    expect(client.time).toBe(0);
  });

  it('ignore les états publiés avant que le Worker ait appliqué les commandes', () => {
    const { server, client, flush } = setup();
    client.load(solarSystem());
    flush();
    server.tick(0.1);
    // Commande envoyée, mais l'état en attente a été publié avant elle.
    const mars = client.bodies.find((b) => b.name === 'Mars')!;
    client.removeBody(mars.id);
    expect(client.bodies.some((b) => b.name === 'Mars')).toBe(false);
    flush();
    expect(client.bodies.some((b) => b.name === 'Mars')).toBe(false);
    expect(server.sim.bodies.some((b) => b.name === 'Mars')).toBe(false);
  });

  it("donne le même identifiant à l'étoile compagne des deux côtés", () => {
    const { server, client, flush } = setup();
    client.load(solarSystem());
    const companion = client.addCompanion('M', 60, 0.1)!;
    flush();
    expect(server.sim.getBody(companion.id)?.kind).toBe('star');
    expect(client.getBody(companion.id)?.kind).toBe('star');
  });

  it('transmet événements et changements de structure (collisions, fusion)', () => {
    const { server, client, flush } = setup();
    client.load(tightBinary());
    flush();
    const b = client.stars.find((s) => s.parentId)!;
    client.updateBody(b.id, { elements: { ...b.elements!, a: 0.6, e: 0.6 } });
    client.setSpeed(3652.5);
    flush();
    for (let k = 0; k < 40 && client.events.length === 0; k++) {
      server.tick(0.1);
      flush();
    }
    // Une compagne sur une orbite aussi excentrique bouleverse les planètes.
    expect(client.events.length).toBeGreaterThan(0);
    expect(client.bodies.map((x) => x.id)).toEqual(server.sim.bodies.map((x) => x.id));
  });
});
