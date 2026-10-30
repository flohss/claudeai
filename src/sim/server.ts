import { COMMANDS, type CommandMessage, type Port, type StateMessage } from './protocol';
import { Simulation } from './Simulation';

/**
 * Côté Worker : possède la simulation, la fait avancer en continu et publie
 * son état. Le calcul n'occupe plus le fil principal, qui ne fait qu'afficher.
 */
export class SimulationServer {
  readonly sim = new Simulation();
  private ack = 0;
  private publishedVersion = -1;
  private publishedTime = -1;
  private last = performance.now();
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor(
    private readonly port: Port,
    /** Temps de calcul accordé par tick (ms) ; le reste sert aux messages */
    private readonly budgetMs = 13,
  ) {
    port.onmessage = (e) => this.handle(e.data as CommandMessage);
  }

  private handle(msg: CommandMessage): void {
    if (msg?.type !== 'command' || !COMMANDS.includes(msg.method)) return;
    // Liste blanche ci-dessus : seules les méthodes publiques prévues sont appelables.
    (this.sim[msg.method] as (...args: unknown[]) => unknown).apply(this.sim, msg.args);
    this.ack = msg.seq;
    this.publish();
  }

  /** Avance de `realSeconds` (par défaut : le temps réel écoulé depuis le dernier tick) et publie. */
  tick(realSeconds?: number): void {
    const now = performance.now();
    const dt = realSeconds ?? Math.min(0.1, (now - this.last) / 1000);
    this.last = now;
    this.sim.advance(dt, this.budgetMs);
    this.publish();
  }

  start(intervalMs = 16): void {
    this.last = performance.now();
    this.timer = setInterval(() => this.tick(), intervalMs);
  }

  stop(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  private publish(): void {
    const sim = this.sim;
    const structural = sim.version !== this.publishedVersion;
    if (!structural && sim.time === this.publishedTime && sim.effectiveSpeed === 0) return;
    const n = sim.bodies.length;
    const kinematics = new Float64Array(n * 6);
    for (let i = 0; i < n; i++) {
      const b = sim.bodies[i];
      kinematics.set([b.position.x, b.position.y, b.position.z, b.velocity.x, b.velocity.y, b.velocity.z], i * 6);
    }
    const msg: StateMessage = {
      type: 'state',
      ack: this.ack,
      version: sim.version,
      time: sim.time,
      effectiveSpeed: sim.effectiveSpeed,
      kinematics,
    };
    if (structural) {
      msg.structure = { name: sim.name, bodies: sim.bodies, events: sim.events, formation: sim.formation, evolutions: sim.evolutions };
    }
    this.publishedVersion = sim.version;
    this.publishedTime = sim.time;
    this.port.postMessage(msg, [kinematics.buffer]);
  }
}
