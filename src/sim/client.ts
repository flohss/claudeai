import type { Body, SpectralClass } from '../physics/types';
import { newId } from './factory';
import type { CommandMessage, CommandName, Port, StateMessage } from './protocol';
import { Simulation, type BodyPatch, type ImpactorSpec, type ImpulseDirection, type IntruderSpec, type SystemDefinition } from './Simulation';

/**
 * Côté fil principal : un miroir de la simulation qui tourne dans le Worker.
 * L'interface lit ce miroir comme une `Simulation` ordinaire. Chaque commande
 * est appliquée localement tout de suite (l'interface réagit sans attendre),
 * puis transmise au Worker dont l'état fait foi dès qu'il l'a appliquée.
 */
export class SimulationClient extends Simulation {
  private seq = 0;
  private serverVersion = -1;

  constructor(private readonly port: Port) {
    super();
    port.onmessage = (e) => this.receive(e.data as StateMessage);
  }

  private send<M extends CommandName>(method: M, args: CommandMessage['args']): void {
    this.seq += 1;
    const msg: CommandMessage = { type: 'command', seq: this.seq, method, args };
    this.port.postMessage(msg);
  }

  private receive(msg: StateMessage): void {
    // Tant que le Worker n'a pas appliqué nos dernières commandes, son état est périmé.
    if (msg?.type !== 'state' || msg.ack < this.seq) return;
    if (msg.structure) {
      this.name = msg.structure.name;
      this.bodies = msg.structure.bodies;
      this.events = msg.structure.events;
      this.formation = msg.structure.formation;
      this.evolutions = msg.structure.evolutions;
      this.serverVersion = msg.version;
    } else if (msg.version !== this.serverVersion) {
      return;
    }
    const k = msg.kinematics;
    if (k.length === this.bodies.length * 6) {
      for (let i = 0; i < this.bodies.length; i++) {
        const b = this.bodies[i];
        b.position.x = k[i * 6];
        b.position.y = k[i * 6 + 1];
        b.position.z = k[i * 6 + 2];
        b.velocity.x = k[i * 6 + 3];
        b.velocity.y = k[i * 6 + 4];
        b.velocity.z = k[i * 6 + 5];
      }
    }
    this.time = msg.time;
    this.effectiveSpeed = msg.effectiveSpeed;
    if (msg.structure) this.changed();
  }

  /** Le calcul se fait dans le Worker. */
  override advance(): void {}

  override load(def: SystemDefinition, placeFromElements = true): void {
    super.load(def, placeFromElements);
    // On envoie l'état déjà placé : le Worker repart exactement du même point.
    this.send('load', [this.snapshot(), false]);
  }

  override reset(): void {
    super.reset();
    this.send('reset', []);
  }

  override addBody(body: Body): void {
    super.addBody(body);
    this.send('addBody', [body]);
  }

  override updateBody(id: string, patch: BodyPatch): void {
    super.updateBody(id, patch);
    this.send('updateBody', [id, patch]);
  }

  override setStarClass(starId: string, spectralClass: SpectralClass): void {
    super.setStarClass(starId, spectralClass);
    this.send('setStarClass', [starId, spectralClass]);
  }

  override addCompanion(spectralClass: SpectralClass, a: number, e: number, id = newId('etoile')): Body | undefined {
    const companion = super.addCompanion(spectralClass, a, e, id);
    this.send('addCompanion', [spectralClass, a, e, id]);
    return companion;
  }

  override removeBody(id: string): void {
    super.removeBody(id);
    this.send('removeBody', [id]);
  }

  override setSpeed(daysPerSecond: number): void {
    super.setSpeed(daysPerSecond);
    this.send('setSpeed', [daysPerSecond]);
  }

  override setPaused(paused: boolean): void {
    super.setPaused(paused);
    this.send('setPaused', [paused]);
  }

  override launchIntruder(spec: IntruderSpec): number {
    const eta = super.launchIntruder(spec);
    this.send('launchIntruder', [spec]);
    return eta;
  }

  override launchImpactor(spec: ImpactorSpec): void {
    super.launchImpactor(spec);
    this.send('launchImpactor', [spec]);
  }

  override supernova(starId: string, remnantMass: number): void {
    super.supernova(starId, remnantMass);
    this.send('supernova', [starId, remnantMass]);
  }

  override collapseToBlackHole(starId: string): void {
    super.collapseToBlackHole(starId);
    this.send('collapseToBlackHole', [starId]);
  }

  override startRedGiant(starId: string, durationYears: number): void {
    super.startRedGiant(starId, durationYears);
    this.send('startRedGiant', [starId, durationYears]);
  }

  override applyImpulse(id: string, deltaVKmS: number, direction: ImpulseDirection): void {
    super.applyImpulse(id, deltaVKmS, direction);
    this.send('applyImpulse', [id, deltaVKmS, direction]);
  }
}

/**
 * Crée la simulation de l'application : dans un Worker si le navigateur le
 * permet, sinon sur le fil principal.
 */
export function createSimulation(def: SystemDefinition): Simulation {
  try {
    const worker = new Worker(new URL('./sim.worker.ts', import.meta.url), { type: 'module' });
    const client = new SimulationClient(worker as unknown as Port);
    client.load(def);
    return client;
  } catch {
    return new Simulation(def);
  }
}
