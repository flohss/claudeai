/**
 * Unités internes de la simulation :
 *  - distance : unité astronomique (UA)
 *  - masse    : masse solaire (M☉)
 *  - temps    : année julienne
 * Dans ce système, G = 4π² et une orbite de 1 UA autour de 1 M☉ dure 1 an.
 */
export const G = 4 * Math.PI * Math.PI;

export const DAYS_PER_YEAR = 365.25;
export const SECONDS_PER_YEAR = DAYS_PER_YEAR * 86400;

export const AU_KM = 1.495978707e8;
export const AU_M = AU_KM * 1000;

export const SUN_MASS_KG = 1.98892e30;
export const SUN_RADIUS_KM = 695700;
export const EARTH_MASS_SUN = 3.0034896e-6;
export const EARTH_RADIUS_KM = 6371;
export const JUPITER_MASS_EARTH = 317.83;

export const G_SI = 6.6743e-11;

export const earthMassesToSun = (m: number) => m * EARTH_MASS_SUN;
export const sunMassesToEarth = (m: number) => m / EARTH_MASS_SUN;
export const kmToAu = (km: number) => km / AU_KM;
export const auToKm = (au: number) => au * AU_KM;
export const degToRad = (d: number) => (d * Math.PI) / 180;
export const radToDeg = (r: number) => (r * 180) / Math.PI;
