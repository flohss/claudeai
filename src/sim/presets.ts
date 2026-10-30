import type { SpectralClass } from '../physics/types';
import { makeOrbiter, makeStar } from './factory';
import type { SystemDefinition } from './Simulation';

/** Notre système solaire (éléments orbitaux J2000 approximatifs). */
export function solarSystem(): SystemDefinition {
  const sun = makeStar('G', 'Soleil');
  sun.color = '#fff1c9';
  const p = (name: string, planetType: Parameters<typeof makeOrbiter>[0]['planetType'], massEarth: number, radiusKm: number, a: number, e: number, i: number, Omega: number, omega: number, nu: number, color: string, albedo: number) =>
    makeOrbiter({ name, planetType, massEarth, radiusKm, parentId: sun.id, elements: { a, e, i, Omega, omega, nu }, color, albedo });

  const mercury = p('Mercure', 'tellurique', 0.0553, 2440, 0.387, 0.2056, 7.0, 48.3, 29.1, 175, '#a8a29a', 0.088);
  const venus = p('Vénus', 'tellurique', 0.815, 6052, 0.723, 0.0068, 3.39, 76.7, 54.9, 50, '#e8cf9a', 0.76);
  const earth = p('Terre', 'tellurique', 1, 6371, 1.0, 0.0167, 0.0, 0, 114.2, 0, '#3d7fd6', 0.306);
  const mars = p('Mars', 'tellurique', 0.107, 3390, 1.524, 0.0934, 1.85, 49.6, 286.5, 300, '#c1532f', 0.25);
  const jupiter = p('Jupiter', 'geante-gazeuse', 317.8, 69911, 5.203, 0.0484, 1.3, 100.5, 273.9, 20, '#d9b38c', 0.503);
  const saturn = p('Saturne', 'geante-gazeuse', 95.2, 58232, 9.537, 0.0539, 2.49, 113.7, 339.4, 280, '#e6d3a1', 0.342);
  const uranus = p('Uranus', 'geante-glace', 14.5, 25362, 19.19, 0.0473, 0.77, 74.0, 96.9, 140, '#9fe0e8', 0.3);
  const neptune = p('Neptune', 'geante-glace', 17.1, 24622, 30.07, 0.0086, 1.77, 131.8, 273.2, 250, '#4a6fe0', 0.29);
  const pluto = p('Pluton', 'naine', 0.0022, 1188, 39.48, 0.2488, 17.16, 110.3, 113.8, 30, '#cbb49a', 0.5);

  const m = (name: string, parent: { id: string }, massEarth: number, radiusKm: number, aKm: number, e: number, i: number, nu: number, color: string) =>
    makeOrbiter({ name, kind: 'moon', planetType: 'naine', massEarth, radiusKm, parentId: parent.id, elements: { a: aKm / 1.495978707e8, e, i, nu }, color, albedo: 0.2 });

  // Inclinaison des axes de rotation : elle oriente les anneaux.
  const tilts: [typeof earth, number][] = [[mercury, 0], [venus, 177], [earth, 23.4], [mars, 25.2], [jupiter, 3.1], [saturn, 26.7], [uranus, 97.8], [neptune, 28.3], [pluto, 120]];
  for (const [body, tilt] of tilts) body.axialTilt = tilt;
  saturn.rings = { inner: 1.24, outer: 2.27, color: '#d9c7a0', opacity: 0.8 };
  uranus.rings = { inner: 1.64, outer: 2.0, color: '#8a9aa6', opacity: 0.25 };

  return {
    name: 'Système solaire',
    bodies: [
      sun, mercury, venus, earth, mars, jupiter, saturn, uranus, neptune, pluto,
      m('Lune', earth, 0.0123, 1737, 384400, 0.0549, 5.15, 90, '#cfcfcf'),
      m('Io', jupiter, 0.015, 1821, 421700, 0.004, 2.2, 0, '#e8d55a'),
      m('Europe', jupiter, 0.008, 1561, 671034, 0.009, 2.0, 120, '#d8c8a8'),
      m('Ganymède', jupiter, 0.0248, 2634, 1070412, 0.0013, 2.1, 220, '#a89f94'),
      m('Callisto', jupiter, 0.018, 2410, 1882709, 0.0074, 2.0, 300, '#7d7266'),
      m('Titan', saturn, 0.0225, 2575, 1221870, 0.0288, 2.5, 60, '#e0a84a'),
    ],
  };
}

/**
 * Kepler-16 : une naine orange et une naine rouge en orbite serrée, autour
 * desquelles tourne une planète de la masse de Saturne (première planète
 * circumbinaire découverte, 2011). Elle se trouve juste au-delà de la limite de
 * stabilité de Holman-Wiegert (~0,65 UA). Kepler-16 c est hypothétique.
 */
export function tightBinary(): SystemDefinition {
  const a = makeStar('K', 'Kepler-16 A');
  a.mass = 0.69;
  const b = makeStar('M', 'Kepler-16 B');
  b.mass = 0.2;
  b.star!.luminosity = 0.005;
  b.parentId = a.id;
  b.elements = { a: 0.224, e: 0.16, i: 0, Omega: 0, omega: 263.5, nu: 0 };
  const planet = makeOrbiter({
    name: 'Kepler-16 b',
    planetType: 'geante-gazeuse',
    massEarth: 105.8,
    radiusKm: 52700,
    parentId: a.id,
    elements: { a: 0.7048, e: 0.0069, i: 0.3, omega: 318, nu: 90 },
    color: '#d8c49a',
  });
  planet.circumbinary = true;
  const outer = makeOrbiter({
    name: 'Kepler-16 c (hypothétique)',
    planetType: 'geante-glace',
    massEarth: 15,
    radiusKm: 24000,
    parentId: a.id,
    elements: { a: 1.6, e: 0.02, i: 1, nu: 250 },
  });
  outer.circumbinary = true;
  return { name: 'Kepler-16 (binaire serrée)', bodies: [a, b, planet, outer] };
}

/**
 * Alpha du Centaure A et B : deux étoiles proches du Soleil sur une orbite large
 * et très excentrique. Chaque étoile peut retenir des planètes jusqu'à ~2,8 UA.
 * Les planètes sont hypothétiques, placées dans la zone habitable de chaque étoile.
 */
export function wideBinary(): SystemDefinition {
  const a = makeStar('G', 'Alpha Centauri A');
  a.mass = 1.08;
  a.star!.luminosity = 1.52;
  const b = makeStar('K', 'Alpha Centauri B');
  b.mass = 0.91;
  b.star!.luminosity = 0.5;
  b.parentId = a.id;
  b.elements = { a: 23.4, e: 0.52, i: 0, Omega: 0, omega: 0, nu: 180 };
  const pa = makeOrbiter({ name: 'Centauri A b (hypothétique)', planetType: 'tellurique', massEarth: 1.2, radiusKm: 6700, parentId: a.id, elements: { a: 1.25, e: 0.01, nu: 40 }, color: '#4f8cc9' });
  const pa2 = makeOrbiter({ name: 'Centauri A c (hypothétique)', planetType: 'geante-glace', massEarth: 12, radiusKm: 23000, parentId: a.id, elements: { a: 2.4, e: 0.02, nu: 200 } });
  const pb = makeOrbiter({ name: 'Centauri B b (hypothétique)', planetType: 'tellurique', massEarth: 0.8, radiusKm: 5900, parentId: b.id, elements: { a: 0.75, e: 0.01, nu: 120 }, color: '#6b8e4e' });
  return { name: 'Alpha du Centaure (binaire large)', bodies: [a, b, pa, pa2, pb] };
}

/** Une étoile seule, pour construire son propre système. */
export function emptySystem(spectralClass: SpectralClass = 'G'): SystemDefinition {
  return { name: 'Nouveau système', bodies: [makeStar(spectralClass, 'Étoile')] };
}
