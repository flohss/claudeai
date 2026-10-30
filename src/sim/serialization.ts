import type { Body } from '../physics/types';
import type { FormationSettings, Simulation, SystemDefinition } from './Simulation';

export const FILE_FORMAT = 'simulateur-systeme-solaire';
export const FILE_VERSION = 1;

interface SystemFile {
  format: typeof FILE_FORMAT;
  version: number;
  name: string;
  time: number;
  formation?: FormationSettings | null;
  bodies: Body[];
}

export function serialize(sim: Simulation): string {
  const snap = sim.snapshot();
  const file: SystemFile = {
    format: FILE_FORMAT,
    version: FILE_VERSION,
    name: snap.name,
    time: snap.time ?? 0,
    formation: snap.formation ?? null,
    bodies: snap.bodies,
  };
  return JSON.stringify(file, null, 2);
}

const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const isVec = (v: unknown) => !!v && typeof v === 'object' && ['x', 'y', 'z'].every((k) => isNum((v as Record<string, unknown>)[k]));

/** Lit un fichier de sauvegarde. Lève une erreur explicite si le contenu est invalide. */
export function deserialize(text: string): SystemDefinition {
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error("Le fichier n'est pas un JSON valide.");
  }
  const file = data as Partial<SystemFile>;
  if (!file || file.format !== FILE_FORMAT) throw new Error("Ce fichier n'est pas une sauvegarde du simulateur.");
  if (file.version !== FILE_VERSION) throw new Error(`Version de fichier non prise en charge : ${String(file.version)}.`);
  if (!Array.isArray(file.bodies) || file.bodies.length === 0) throw new Error('La sauvegarde ne contient aucun corps.');

  const stars = file.bodies.filter((b) => b?.kind === 'star');
  if (stars.length === 0) throw new Error('La sauvegarde doit contenir au moins une étoile.');
  if (stars.filter((b) => !b.parentId).length !== 1) throw new Error('La sauvegarde doit contenir une seule étoile principale.');
  const ids = new Set<string>();
  for (const b of file.bodies) {
    if (!b || typeof b.id !== 'string' || typeof b.name !== 'string') throw new Error('Corps invalide dans la sauvegarde.');
    if (!isNum(b.mass) || b.mass <= 0 || !isNum(b.radiusKm) || b.radiusKm <= 0) throw new Error(`Masse ou rayon invalide pour « ${b.name} ».`);
    if (!isVec(b.position) || !isVec(b.velocity)) throw new Error(`Position ou vitesse invalide pour « ${b.name} ».`);
    if (ids.has(b.id)) throw new Error(`Identifiant en double : ${b.id}.`);
    ids.add(b.id);
  }
  for (const b of file.bodies) {
    if (b.parentId && !ids.has(b.parentId)) throw new Error(`Parent introuvable pour « ${b.name} ».`);
  }
  const f = file.formation;
  const formation =
    f && [f.gasUntil, f.gasTimescale, f.coreMassEarth, f.maxGiantMassEarth].every(isNum) ? f : null;
  return { name: file.name ?? 'Système importé', time: isNum(file.time) ? file.time : 0, formation, bodies: file.bodies };
}
