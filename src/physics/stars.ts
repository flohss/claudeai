import type { SpectralClass, StarProps } from './types';

export interface SpectralClassInfo {
  label: string;
  /** Masse typique (M☉) */
  mass: number;
  /** Rayon typique (R☉) */
  radius: number;
  /** Luminosité typique (L☉) */
  luminosity: number;
  temperatureK: number;
  color: string;
  description: string;
}

/** Valeurs représentatives d'étoiles de la séquence principale. */
export const SPECTRAL_CLASSES: Record<SpectralClass, SpectralClassInfo> = {
  O: { label: 'O — géante bleue', mass: 30, radius: 9, luminosity: 140000, temperatureK: 38000, color: '#9bb0ff', description: 'Extrêmement massive et lumineuse, vie très courte.' },
  B: { label: 'B — bleu-blanc', mass: 6, radius: 3.5, luminosity: 800, temperatureK: 18000, color: '#aabfff', description: 'Très chaude, zone habitable lointaine.' },
  A: { label: 'A — blanche', mass: 2.1, radius: 1.8, luminosity: 20, temperatureK: 8700, color: '#cad7ff', description: 'Comme Sirius ou Véga.' },
  F: { label: 'F — blanc-jaune', mass: 1.3, radius: 1.25, luminosity: 2.8, temperatureK: 6600, color: '#f8f7ff', description: 'Un peu plus chaude que le Soleil.' },
  G: { label: 'G — naine jaune', mass: 1, radius: 1, luminosity: 1, temperatureK: 5778, color: '#fff1c9', description: 'Comme le Soleil.' },
  K: { label: 'K — naine orange', mass: 0.7, radius: 0.75, luminosity: 0.25, temperatureK: 4600, color: '#ffd2a1', description: 'Stable et longévive, bonne candidate pour la vie.' },
  M: { label: 'M — naine rouge', mass: 0.3, radius: 0.35, luminosity: 0.015, temperatureK: 3300, color: '#ffb070', description: "L'étoile la plus courante ; zone habitable très proche." },
};

export const SPECTRAL_ORDER: SpectralClass[] = ['O', 'B', 'A', 'F', 'G', 'K', 'M'];

export function starPropsFor(spectralClass: SpectralClass): StarProps {
  const info = SPECTRAL_CLASSES[spectralClass];
  return { spectralClass, luminosity: info.luminosity, temperatureK: info.temperatureK };
}

/**
 * Zone habitable « conservatrice » (flux stellaire reçu entre ~1,1 et ~0,53 fois
 * celui de la Terre), en UA.
 */
export function habitableZone(luminosity: number): { inner: number; outer: number } {
  return { inner: Math.sqrt(luminosity / 1.1), outer: Math.sqrt(luminosity / 0.53) };
}

/** Ligne des glaces : au-delà, l'eau gèle et les géantes peuvent se former (UA). */
export function snowLine(luminosity: number): number {
  return 2.7 * Math.sqrt(luminosity);
}
