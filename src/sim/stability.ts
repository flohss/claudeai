import { pTypeCriticalAu, sTypeCriticalAu } from '../physics/binary';
import { currentElements } from '../physics/derived';
import type { Body } from '../physics/types';
import type { Simulation } from './Simulation';

/**
 * Stabilité d'une orbite planétaire dans un système double (critère de Holman-Wiegert).
 * Renvoie null hors système double.
 */
export function binaryStability(sim: Simulation, body: Body): { stable: boolean; limitAu: number; kind: 'S' | 'P' } | null {
  const stars = sim.stars;
  const primary = sim.star;
  const companion = stars.find((s) => s.parentId);
  if (stars.length !== 2 || !primary || !companion || body.kind === 'star') return null;
  const parent = sim.getBody(body.parentId);
  if (!body.circumbinary && parent?.kind !== 'star') return null;
  const bin = currentElements(companion, primary);
  if (!(bin.a > 0) || bin.e >= 1) return null;
  const frame = sim.frameOf(body)!;
  const a = currentElements(body, frame).a;
  if (body.circumbinary) {
    const limitAu = pTypeCriticalAu(bin.a, bin.e, Math.min(primary.mass, companion.mass) / (primary.mass + companion.mass));
    return { stable: a > limitAu, limitAu, kind: 'P' };
  }
  const other = parent === primary ? companion : primary;
  const limitAu = sTypeCriticalAu(bin.a, bin.e, other.mass / (primary.mass + companion.mass));
  return { stable: a > 0 && a < limitAu, limitAu, kind: 'S' };
}
