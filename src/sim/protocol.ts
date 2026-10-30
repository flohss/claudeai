import type { Body } from '../physics/types';
import type { FormationSettings, SimEvent, Simulation } from './Simulation';

/** Canal de messages : un Worker, `self` dans le Worker, ou un canal en mémoire pour les tests. */
export interface Port {
  postMessage(message: unknown, transfer?: Transferable[]): void;
  onmessage: ((event: MessageEvent) => void) | null;
}

/** Méthodes de `Simulation` que le fil principal peut faire exécuter au Worker. */
export const COMMANDS = ['load', 'reset', 'addBody', 'updateBody', 'setStarClass', 'addCompanion', 'removeBody', 'setSpeed', 'setPaused'] as const;
export type CommandName = (typeof COMMANDS)[number];

export interface CommandMessage {
  type: 'command';
  /** Numéro croissant, renvoyé par le Worker une fois la commande appliquée */
  seq: number;
  method: CommandName;
  args: Parameters<Simulation[CommandName]>;
}

/** État publié par le Worker, plusieurs dizaines de fois par seconde. */
export interface StateMessage {
  type: 'state';
  /** Dernière commande appliquée */
  ack: number;
  /** `version` de la simulation dans le Worker */
  version: number;
  time: number;
  effectiveSpeed: number;
  /** Positions et vitesses, 6 valeurs par corps dans l'ordre de `bodies` */
  kinematics: Float64Array;
  /** Présent seulement quand la structure a changé depuis la dernière publication */
  structure?: {
    name: string;
    bodies: Body[];
    events: SimEvent[];
    formation: FormationSettings | null;
  };
}
