import { AU_M, SECONDS_PER_YEAR, SUN_MASS_KG } from './units';

/** Énergie d'un mégatonne de TNT (J). */
export const MEGATON_J = 4.184e15;
/** Énergie de l'impact de Chicxulub, qui a mis fin aux dinosaures (~10¹⁴ t de TNT). */
export const CHICXULUB_MT = 1e8;

/** Rayon de Schwarzschild (km) : l'horizon d'un trou noir de masse donnée (M☉). */
export const schwarzschildRadiusKm = (massSun: number) => 2.953 * massSun;

/**
 * Rayon de marée (km) : en deçà, un corps compact de masse `compactMass`
 * arrache la matière d'un corps de rayon `victimRadiusKm` et masse `victimMass`.
 */
export function tidalRadiusKm(victimRadiusKm: number, compactMass: number, victimMass: number): number {
  return victimRadiusKm * Math.cbrt(compactMass / victimMass);
}

/** Énergie cinétique libérée par une collision (J), dans le référentiel du centre de masse. */
export function impactEnergyJ(m1Sun: number, m2Sun: number, relativeSpeedAuPerYear: number): number {
  const m1 = m1Sun * SUN_MASS_KG;
  const m2 = m2Sun * SUN_MASS_KG;
  const v = (relativeSpeedAuPerYear * AU_M) / SECONDS_PER_YEAR;
  return 0.5 * ((m1 * m2) / (m1 + m2)) * v * v;
}

/**
 * Diamètre du cratère final (km), loi d'échelle de Collins, Melosh et Marcus (2005).
 * Impact à 45°, impacteur et sol rocheux. Les gros cratères s'effondrent en
 * cratères complexes, plus larges et moins profonds.
 */
export function craterDiameterKm(impactorDiameterKm: number, speedKmS: number, surfaceGravity: number, impactorDensity = 3000, targetDensity = 2500): number {
  const L = impactorDiameterKm * 1000;
  const v = speedKmS * 1000;
  const transient = 1.161 * Math.cbrt(impactorDensity / targetDensity) * L ** 0.78 * v ** 0.44 * surfaceGravity ** -0.22 * Math.sin(Math.PI / 4) ** (1 / 3);
  const transientKm = transient / 1000;
  // Diamètre de transition simple → complexe, proportionnel à 1/g (3,2 km sur Terre).
  const transitionKm = (3.2 * 9.81) / surfaceGravity;
  if (transientKm * 1.25 < transitionKm) return transientKm * 1.25;
  return (1.17 * transientKm ** 1.13) / transitionKm ** 0.13;
}

/** Conséquences d'un impact sur une planète rocheuse, d'après son énergie. */
export function impactSeverity(megatons: number): string {
  if (megatons < 1) return "explosion dans l'atmosphère, vitres brisées à des dizaines de kilomètres";
  if (megatons < 100) return 'destruction régionale (comme à la Toungouska en 1908)';
  if (megatons < 1e5) return 'catastrophe à l’échelle d’un continent';
  if (megatons < 1e7) return 'hiver d’impact mondial, effondrement des récoltes';
  if (megatons < 1e10) return 'extinction de masse (comme celle des dinosaures)';
  return 'stérilisation de la surface : les océans peuvent s’évaporer';
}
