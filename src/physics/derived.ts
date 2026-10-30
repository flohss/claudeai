import { habitableZone } from './stars';
import { mu, stateToElements } from './orbits';
import type { Body, OrbitalElements } from './types';
import { AU_KM, EARTH_MASS_SUN, G_SI, SUN_MASS_KG } from './units';
import { distance, sub, type Vec3 } from './vec3';

/** Gravité de surface (m/s²). */
export function surfaceGravity(massSun: number, radiusKm: number): number {
  const r = radiusKm * 1000;
  return (G_SI * massSun * SUN_MASS_KG) / (r * r);
}

/** Vitesse de libération (km/s). */
export function escapeVelocity(massSun: number, radiusKm: number): number {
  return Math.sqrt((2 * G_SI * massSun * SUN_MASS_KG) / (radiusKm * 1000)) / 1000;
}

/** Masse volumique moyenne (g/cm³). */
export function density(massSun: number, radiusKm: number): number {
  const volumeCm3 = (4 / 3) * Math.PI * (radiusKm * 1e5) ** 3;
  return (massSun * SUN_MASS_KG * 1000) / volumeCm3;
}

/** Température d'équilibre radiatif (K), sans effet de serre. */
export function equilibriumTemperature(luminosity: number, distanceAu: number, albedo: number): number {
  return equilibriumTemperatureFromFlux(luminosity / (distanceAu * distanceAu), albedo);
}

/** Même calcul à partir du flux reçu, en multiples du flux reçu par la Terre. */
export function equilibriumTemperatureFromFlux(flux: number, albedo: number): number {
  return 278.6 * Math.pow(flux * (1 - albedo), 0.25);
}

/** Flux total reçu de toutes les étoiles (1 = flux reçu par la Terre). */
export function stellarFlux(body: Body, stars: Body[]): number {
  let flux = 0;
  for (const s of stars) {
    if (s === body || !s.star) continue;
    const d = distance(body.position, s.position);
    flux += s.star.luminosity / (d * d);
  }
  return flux;
}

export type ZoneStatus = 'trop-chaud' | 'habitable' | 'trop-froid';

/** Bornes de la zone habitable exprimées en flux : la Terre reçoit 1. */
export const HZ_FLUX_INNER = 1.1;
export const HZ_FLUX_OUTER = 0.53;

export function zoneStatusFromFlux(flux: number): ZoneStatus {
  if (flux > HZ_FLUX_INNER) return 'trop-chaud';
  if (flux < HZ_FLUX_OUTER) return 'trop-froid';
  return 'habitable';
}

export function zoneStatus(luminosity: number, distanceAu: number): ZoneStatus {
  const hz = habitableZone(luminosity);
  if (distanceAu < hz.inner) return 'trop-chaud';
  if (distanceAu > hz.outer) return 'trop-froid';
  return 'habitable';
}

/**
 * Limite de Roche (km) : en deçà, les forces de marée de la planète disloquent
 * un satellite fluide de masse volumique `satelliteDensity`.
 */
export function rocheLimitKm(planetRadiusKm: number, planetDensity: number, satelliteDensity: number): number {
  return 2.44 * planetRadiusKm * Math.cbrt(planetDensity / satelliteDensity);
}

export interface Habitability {
  verdict: 'potentiellement-habitable' | 'non-habitable' | 'lunes-candidates';
  reason: string;
}

export function assessHabitability(body: Body, flux: number): Habitability {
  const zone = zoneStatusFromFlux(flux);
  const massEarth = body.mass / EARTH_MASS_SUN;
  const giant = body.planetType === 'geante-gazeuse' || body.planetType === 'geante-glace';

  if (zone === 'trop-chaud') return { verdict: 'non-habitable', reason: "Trop proche de l'étoile : l'eau s'évapore." };
  if (zone === 'trop-froid') return { verdict: 'non-habitable', reason: "Trop loin de l'étoile : l'eau gèle." };
  if (giant) {
    return { verdict: 'lunes-candidates', reason: "Dans la zone habitable, mais c'est une géante sans surface solide : ses lunes pourraient être habitables." };
  }
  if (massEarth < 0.1) return { verdict: 'non-habitable', reason: 'Trop petite pour retenir une atmosphère durablement.' };
  if (massEarth > 10) return { verdict: 'non-habitable', reason: 'Trop massive : elle a probablement accumulé une épaisse enveloppe de gaz.' };
  return { verdict: 'potentiellement-habitable', reason: "Dans la zone habitable, de taille compatible avec de l'eau liquide en surface." };
}

/** Référentiel autour duquel on mesure une orbite : un corps, ou le barycentre de plusieurs. */
export interface Frame {
  position: Vec3;
  velocity: Vec3;
  mass: number;
}

/** Éléments osculateurs actuels d'un corps dans le référentiel d'un parent. */
export function currentElements(body: Body, parent: Frame): OrbitalElements {
  return stateToElements(sub(body.position, parent.position), sub(body.velocity, parent.velocity), mu(parent.mass, body.mass));
}

export function distanceAu(a: Body, b: Body): number {
  return distance(a.position, b.position);
}

export function distanceKm(a: Body, b: Body): number {
  return distanceAu(a, b) * AU_KM;
}
