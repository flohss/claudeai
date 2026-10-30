import { SPECTRAL_CLASSES, snowLine } from '../physics/stars';
import type { Body, SpectralClass } from '../physics/types';
import { estimateRadiusKm, makeOrbiter, makeStar } from './factory';
import { createRng } from './random';
import type { FormationSettings, SystemDefinition } from './Simulation';

export interface DiskParams {
  spectralClass: SpectralClass;
  /** Nombre de planétésimaux */
  count: number;
  /** Masse solide totale du disque (M⊕) */
  massEarth: number;
  /** Bord intérieur et extérieur (UA) */
  innerAu: number;
  outerAu: number;
  /**
   * Agrandissement du rayon de capture. Avec les vrais rayons, les collisions
   * prendraient des millions d'années : on les gonfle pour voir la formation en
   * quelques minutes.
   */
  accretionScale: number;
  /** Les noyaux massifs capturent du gaz pour devenir des géantes */
  gas: boolean;
  seed: number;
}

export function defaultDiskParams(spectralClass: SpectralClass = 'G'): DiskParams {
  const L = SPECTRAL_CLASSES[spectralClass].luminosity;
  const snow = snowLine(L);
  return {
    spectralClass,
    count: 120,
    massEarth: 40,
    innerAu: +(0.5 * Math.sqrt(L)).toPrecision(2),
    outerAu: +(snow * 2).toPrecision(2),
    accretionScale: 800,
    gas: true,
    seed: Math.floor(Math.random() * 1e9),
  };
}

export const DEFAULT_FORMATION: Omit<FormationSettings, 'gasUntil'> & { gasLifetime: number } = {
  gasLifetime: 300,
  gasTimescale: 15,
  coreMassEarth: 3,
  maxGiantMassEarth: 320,
};

/**
 * Disque de planétésimaux autour d'une jeune étoile. La densité de surface
 * décroît en r^-1,5 et triple au-delà de la ligne des glaces, où la glace
 * d'eau s'ajoute aux roches : c'est là que se forment les noyaux des géantes.
 */
export function protoplanetaryDisk(params: DiskParams): SystemDefinition {
  const rng = createRng(params.seed);
  const star = makeStar(params.spectralClass, 'Jeune étoile');
  const L = star.star!.luminosity;
  const snow = snowLine(L);
  const inner = Math.max(params.innerAu, 0.05);
  const outer = Math.max(params.outerAu, inner * 1.5);

  // Masse ∝ Σ(r)·r·dr ∝ r^-0,5 dr : on tire √r uniformément.
  const radii: number[] = [];
  for (let k = 0; k < params.count; k++) {
    const s = Math.sqrt(inner) + (Math.sqrt(outer) - Math.sqrt(inner)) * rng.next();
    radii.push(s * s);
  }
  const weights = radii.map((r) => (r > snow ? 3 : 1) * rng.range(0.5, 1.5));
  const total = weights.reduce((s, w) => s + w, 0);

  const bodies: Body[] = [star];
  radii.forEach((a, k) => {
    const massEarth = (params.massEarth * weights[k]) / total;
    const icy = a > snow;
    const body = makeOrbiter({
      name: `Planétésimal ${k + 1}`,
      planetType: 'naine',
      massEarth,
      radiusKm: estimateRadiusKm('naine', massEarth),
      parentId: star.id,
      color: icy ? '#b8d4e0' : '#a08670',
      albedo: icy ? 0.5 : 0.2,
      elements: {
        a,
        e: rng.range(0, 0.02),
        i: rng.range(0, 0.5),
        Omega: rng.range(0, 360),
        omega: rng.range(0, 360),
        nu: rng.range(0, 360),
      },
    });
    body.kind = 'planetesimal';
    body.accretionScale = params.accretionScale;
    bodies.push(body);
  });

  const { gasLifetime, ...formation } = DEFAULT_FORMATION;
  return {
    name: 'Disque protoplanétaire',
    bodies,
    formation: params.gas ? { ...formation, gasUntil: gasLifetime } : null,
  };
}
