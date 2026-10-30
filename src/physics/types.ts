import type { Vec3 } from './vec3';

/** `planetesimal` : petit corps d'un disque protoplanétaire, appelé à fusionner. */
export type BodyKind = 'star' | 'planet' | 'moon' | 'planetesimal';

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

/** Ce qui reste d'une étoile en fin de vie. */
export type Remnant = 'naine-blanche' | 'etoile-a-neutrons' | 'trou-noir';

export interface StarProps {
  spectralClass: SpectralClass;
  /** Absent pour une étoile ordinaire */
  remnant?: Remnant;
  /** Luminosité (L☉) */
  luminosity: number;
  /** Température effective (K) */
  temperatureK: number;
}

/** Anneaux (non simulés comme des corps), dimensions en rayons de la planète. */
export interface Rings {
  inner: number;
  outer: number;
  color: string;
  /** Opacité moyenne (0..1) */
  opacity: number;
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
  /** Corps autour duquel l'objet a été placé en orbite (null pour l'étoile principale) */
  parentId: string | null;
  /**
   * Orbite circumbinaire : l'orbite est définie autour du barycentre de toutes
   * les étoiles et non autour du parent seul (planète « type Tatooine »).
   */
  circumbinary?: boolean;
  rings?: Rings;
  /** Inclinaison de l'axe de rotation (°), oriente les anneaux */
  axialTilt?: number;
  /**
   * Facteur d'agrandissement du rayon de capture lors des collisions. Utilisé par
   * le modèle accéléré de formation planétaire ; absent = rayon réel.
   */
  accretionScale?: number;
  /**
   * Corps venu de l'extérieur (étoile de passage, trou noir, planète vagabonde,
   * astéroïde) : il agit par sa gravité mais ne fait pas partie du système.
   */
  intruder?: boolean;
  /** Éléments orbitaux de définition (null pour l'étoile) */
  elements: OrbitalElements | null;
  /** État dynamique, en coordonnées barycentriques (UA, UA/an) */
  position: Vec3;
  velocity: Vec3;
}
