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

/** Une étoile seule, pour construire son propre système. */
export function emptySystem(spectralClass: SpectralClass = 'G'): SystemDefinition {
  return { name: 'Nouveau système', bodies: [makeStar(spectralClass, 'Étoile')] };
}
