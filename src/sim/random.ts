import { hillRadius } from '../physics/orbits';
import { SPECTRAL_CLASSES, snowLine } from '../physics/stars';
import type { Body, PlanetType, SpectralClass } from '../physics/types';
import { AU_KM, earthMassesToSun } from '../physics/units';
import { estimateRadiusKm, makeOrbiter, makeStar } from './factory';
import type { SystemDefinition } from './Simulation';

/** Générateur pseudo-aléatoire déterministe (mulberry32). */
export function createRng(seed: number) {
  let s = seed >>> 0;
  const next = () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return {
    next,
    range: (min: number, max: number) => min + (max - min) * next(),
    int: (min: number, max: number) => Math.floor(min + (max - min + 1) * next()),
    /** Valeur répartie uniformément en échelle logarithmique. */
    logRange: (min: number, max: number) => Math.exp(Math.log(min) + (Math.log(max) - Math.log(min)) * next()),
    pick: <T,>(items: readonly T[]) => items[Math.floor(next() * items.length)],
    weighted: <T,>(items: readonly [T, number][]) => {
      const total = items.reduce((s2, [, w]) => s2 + w, 0);
      let r = next() * total;
      for (const [item, w] of items) {
        r -= w;
        if (r <= 0) return item;
      }
      return items[items.length - 1][0];
    },
  };
}

type Rng = ReturnType<typeof createRng>;

const SYLLABLES = ['ka', 'ri', 'tal', 'ven', 'os', 'mir', 'za', 'el', 'dor', 'yn', 'th', 'ar', 'lu', 'nex', 'sol', 'qi', 'ra', 'ber'];

function starName(rng: Rng): string {
  const n = rng.int(2, 3);
  let name = '';
  for (let k = 0; k < n; k++) name += rng.pick(SYLLABLES);
  return name.charAt(0).toUpperCase() + name.slice(1);
}

const PALETTES: Record<PlanetType, string[]> = {
  tellurique: ['#a0522d', '#c1532f', '#8c7b6b', '#4f8cc9', '#6b8e4e', '#d2b48c', '#9e9e9e'],
  'geante-gazeuse': ['#d9b38c', '#e6d3a1', '#c99e6e', '#e0c08a', '#b5835a'],
  'geante-glace': ['#9fe0e8', '#4a6fe0', '#7fd3e0', '#6aa8d8'],
  naine: ['#b9aa98', '#cbb49a', '#9a9a9a', '#d8d0c0'],
};

function choosePlanetType(rng: Rng, a: number, snow: number, giantsSoFar: number): PlanetType {
  if (a < snow) return rng.weighted<PlanetType>([['tellurique', 0.85], ['naine', 0.1], ['geante-gazeuse', 0.05]]);
  if (giantsSoFar < 2) return rng.weighted<PlanetType>([['geante-gazeuse', 0.6], ['geante-glace', 0.35], ['tellurique', 0.05]]);
  return rng.weighted<PlanetType>([['geante-glace', 0.45], ['geante-gazeuse', 0.2], ['naine', 0.35]]);
}

function massFor(rng: Rng, type: PlanetType): number {
  switch (type) {
    case 'tellurique':
      return rng.logRange(0.05, 5);
    case 'geante-gazeuse':
      return rng.logRange(30, 1200);
    case 'geante-glace':
      return rng.range(8, 25);
    case 'naine':
      return rng.logRange(0.001, 0.02);
  }
}

const LETTERS = 'bcdefghijklmnopqrstuvwxyz';

/**
 * Génère un système plausible : planètes rocheuses à l'intérieur de la ligne
 * des glaces, géantes au-delà, espacement assurant la stabilité (≥ 10 rayons de
 * Hill mutuels), et quelques lunes autour des planètes.
 */
export function randomSystem(seed = Math.floor(Math.random() * 1e9)): SystemDefinition {
  const rng = createRng(seed);
  const spectralClass = rng.weighted<SpectralClass>([['M', 0.3], ['K', 0.25], ['G', 0.22], ['F', 0.15], ['A', 0.06], ['B', 0.02]]);
  const name = starName(rng);
  const star = makeStar(spectralClass, name);
  const info = SPECTRAL_CLASSES[spectralClass];
  const variation = rng.range(0.9, 1.1);
  star.mass = info.mass * variation;
  star.star!.luminosity = info.luminosity * Math.pow(variation, 4);

  const L = star.star!.luminosity;
  const snow = snowLine(L);
  const count = rng.int(3, 9);
  const bodies: Body[] = [star];
  const planets: Body[] = [];

  let a = Math.max(0.03, rng.range(0.25, 0.6) * Math.sqrt(L));
  let giants = 0;
  for (let k = 0; k < count; k++) {
    const planetType = choosePlanetType(rng, a, snow, giants);
    if (planetType === 'geante-gazeuse' || planetType === 'geante-glace') giants += 1;
    const massEarth = massFor(rng, planetType);
    const mass = earthMassesToSun(massEarth);

    const prev = planets[planets.length - 1];
    if (prev) {
      const mutualHill = Math.cbrt((prev.mass + mass) / (3 * star.mass)) * ((prev.elements!.a + a) / 2);
      a = Math.max(a, prev.elements!.a + 10 * mutualHill);
    }

    const planet = makeOrbiter({
      name: `${name} ${LETTERS[k]}`,
      planetType,
      massEarth,
      radiusKm: estimateRadiusKm(planetType, massEarth),
      parentId: star.id,
      color: rng.pick(PALETTES[planetType]),
      elements: {
        a,
        e: rng.range(0, planetType === 'naine' ? 0.2 : 0.07),
        i: rng.range(0, 3),
        Omega: rng.range(0, 360),
        omega: rng.range(0, 360),
        nu: rng.range(0, 360),
      },
    });
    planets.push(planet);
    bodies.push(planet);
    a *= rng.range(1.4, 2.0);
  }

  for (const planet of planets) {
    const moonCount =
      planet.planetType === 'geante-gazeuse' ? rng.int(1, 4) : planet.planetType === 'geante-glace' ? rng.int(0, 2) : rng.next() < 0.3 ? 1 : 0;
    const el = planet.elements!;
    const hill = hillRadius(el.a, el.e, planet.mass, star.mass);
    const planetRadiusAu = planet.radiusKm / AU_KM;
    let moonA = planetRadiusAu * rng.range(4, 8);
    for (let k = 0; k < moonCount; k++) {
      if (moonA > 0.3 * hill) break;
      const parentEarth = planet.mass / earthMassesToSun(1);
      const massEarth = planet.planetType === 'tellurique' ? parentEarth * rng.range(0.003, 0.015) : parentEarth * rng.logRange(1e-5, 1e-4);
      bodies.push(
        makeOrbiter({
          name: `${planet.name}-${k + 1}`,
          kind: 'moon',
          planetType: 'naine',
          massEarth,
          radiusKm: estimateRadiusKm('naine', massEarth),
          parentId: planet.id,
          color: rng.pick(PALETTES.naine),
          albedo: 0.3,
          elements: { a: moonA, e: rng.range(0, 0.03), i: el.i + rng.range(-2, 2), Omega: rng.range(0, 360), omega: rng.range(0, 360), nu: rng.range(0, 360) },
        }),
      );
      moonA *= rng.range(1.6, 2.4);
    }
  }

  return { name: `Système ${name}`, bodies };
}
