import type { Vec3 } from './vec3';

export type BodyKind = 'star' | 'planet' | 'moon';

export type PlanetType = 'tellurique' | 'geante-gazeuse' | 'geante-glace' | 'naine';

export type SpectralClass = 'O' | 'B' | 'A' | 'F' | 'G' | 'K' | 'M';

/** Éléments orbitaux képlériens, relatifs au corps parent. Angles en degrés. */
export interface OrbitalElements {
  /** Demi-grand axe (UA) */
  a: number;
  /** Excentricité (0 = cercle) */
  e: number;
  /** Inclinaison */
  i: number;
  /** Longitude du nœud ascendant (Ω) */
  Omega: number;
  /** Argument du périastre (ω) */
  omega: number;
  /** Anomalie vraie initiale (ν) */
  nu: number;
}

export interface StarProps {
  spectralClass: SpectralClass;
  /** Luminosité (L☉) */
  luminosity: number;
  /** Température effective (K) */
  temperatureK: number;
}

export interface Body {
  id: string;
  name: string;
  kind: BodyKind;
  /** Uniquement pour les planètes et les lunes */
  planetType?: PlanetType;
  /** Uniquement pour l'étoile */
  star?: StarProps;
  /** Masse (M☉) */
  mass: number;
  radiusKm: number;
  color: string;
  /** Albédo de Bond (0..1), utilisé pour la température d'équilibre */
  albedo: number;
  /** Corps autour duquel l'objet a été placé en orbite (null pour l'étoile) */
  parentId: string | null;
  /** Éléments orbitaux de définition (null pour l'étoile) */
  elements: OrbitalElements | null;
  /** État dynamique, en coordonnées barycentriques (UA, UA/an) */
  position: Vec3;
  velocity: Vec3;
}
