import { SPECTRAL_CLASSES, starPropsFor } from '../physics/stars';
import type { Body, OrbitalElements, PlanetType, SpectralClass } from '../physics/types';
import { SUN_RADIUS_KM, earthMassesToSun } from '../physics/units';
import { vec3 } from '../physics/vec3';

let counter = 0;
export function newId(prefix = 'c'): string {
  counter += 1;
  return `${prefix}-${Date.now().toString(36)}-${counter.toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
}

export const PLANET_TYPE_LABELS: Record<PlanetType, string> = {
  tellurique: 'Tellurique (rocheuse)',
  'geante-gazeuse': 'Géante gazeuse',
  'geante-glace': 'Géante de glace',
  naine: 'Planète naine',
};

export const DEFAULT_ALBEDO: Record<PlanetType, number> = {
  tellurique: 0.3,
  'geante-gazeuse': 0.45,
  'geante-glace': 0.3,
  naine: 0.5,
};

export const DEFAULT_COLOR: Record<PlanetType, string> = {
  tellurique: '#4f8cc9',
  'geante-gazeuse': '#d8b48a',
  'geante-glace': '#7fd3e0',
  naine: '#b9aa98',
};

export function makeStar(spectralClass: SpectralClass, name = 'Étoile'): Body {
  const info = SPECTRAL_CLASSES[spectralClass];
  return {
    id: newId('etoile'),
    name,
    kind: 'star',
    star: starPropsFor(spectralClass),
    mass: info.mass,
    radiusKm: info.radius * SUN_RADIUS_KM,
    color: info.color,
    albedo: 0,
    parentId: null,
    elements: null,
    position: vec3(),
    velocity: vec3(),
  };
}

export interface OrbiterSpec {
  name: string;
  kind?: 'planet' | 'moon';
  planetType: PlanetType;
  massEarth: number;
  radiusKm: number;
  parentId: string;
  elements: Partial<OrbitalElements> & { a: number };
  color?: string;
  albedo?: number;
  id?: string;
}

export function makeOrbiter(spec: OrbiterSpec): Body {
  return {
    id: spec.id ?? newId(spec.kind === 'moon' ? 'lune' : 'planete'),
    name: spec.name,
    kind: spec.kind ?? 'planet',
    planetType: spec.planetType,
    mass: earthMassesToSun(spec.massEarth),
    radiusKm: spec.radiusKm,
    color: spec.color ?? DEFAULT_COLOR[spec.planetType],
    albedo: spec.albedo ?? DEFAULT_ALBEDO[spec.planetType],
    parentId: spec.parentId,
    elements: { e: 0, i: 0, Omega: 0, omega: 0, nu: 0, ...spec.elements },
    position: vec3(),
    velocity: vec3(),
  };
}

/** Relation masse-rayon approximative selon le type de planète (rayon en km). */
export function estimateRadiusKm(planetType: PlanetType, massEarth: number): number {
  switch (planetType) {
    case 'tellurique':
      return 6371 * Math.pow(massEarth, 0.27);
    case 'geante-glace':
      return 6371 * Math.pow(massEarth, 0.55);
    case 'geante-gazeuse':
      return 69911 * Math.pow(massEarth / 317.8, massEarth < 317.8 ? 0.3 : -0.04);
    case 'naine':
      return 6371 * Math.pow(massEarth, 0.3);
  }
}
