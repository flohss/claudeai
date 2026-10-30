import type { Simulation, SystemDefinition } from './Simulation';
import { deserialize, serialize } from './serialization';

/** Paramètre de l'adresse qui porte le système partagé (après le #, jamais envoyé au serveur). */
export const SHARE_PARAM = 'systeme';
const PREFIX = 'v1.';
/** Au-delà, certaines messageries tronquent les liens. */
export const LONG_LINK_CHARS = 8000;

async function transform(bytes: Uint8Array, stream: CompressionStream | DecompressionStream): Promise<Uint8Array> {
  const out = new Blob([bytes]).stream().pipeThrough(stream);
  return new Uint8Array(await new Response(out).arrayBuffer());
}

function toBase64Url(bytes: Uint8Array): string {
  let bin = '';
  for (let k = 0; k < bytes.length; k += 0x8000) bin += String.fromCharCode(...bytes.subarray(k, k + 0x8000));
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function fromBase64Url(text: string): Uint8Array {
  const bin = atob(text.replace(/-/g, '+').replace(/_/g, '/'));
  const bytes = new Uint8Array(bin.length);
  for (let k = 0; k < bin.length; k++) bytes[k] = bin.charCodeAt(k);
  return bytes;
}

/**
 * Encode l'état actuel du système pour une adresse : JSON de sauvegarde, nombres
 * arrondis à 10 chiffres significatifs (bien au-delà de ce qui se voit), compressé
 * puis converti en base64 compatible avec les URL.
 */
export async function encodeSystem(sim: Simulation): Promise<string> {
  const json = JSON.stringify(JSON.parse(serialize(sim)), (_, v) =>
    typeof v === 'number' && !Number.isInteger(v) ? Number(v.toPrecision(10)) : v,
  );
  const bytes = await transform(new TextEncoder().encode(json), new CompressionStream('deflate-raw'));
  return PREFIX + toBase64Url(bytes);
}

export async function decodeSystem(encoded: string): Promise<SystemDefinition> {
  if (!encoded.startsWith(PREFIX)) throw new Error("Ce lien de partage n'est pas reconnu (version inconnue).");
  let text: string;
  try {
    const bytes = await transform(fromBase64Url(encoded.slice(PREFIX.length)), new DecompressionStream('deflate-raw'));
    text = new TextDecoder().decode(bytes);
  } catch {
    throw new Error('Ce lien de partage est incomplet ou abîmé (a-t-il été coupé en le copiant ?).');
  }
  return deserialize(text);
}

/** Lien complet vers la page actuelle avec le système encodé. */
export function shareUrl(pageUrl: string, encoded: string): string {
  const base = pageUrl.split('#')[0];
  return `${base}#${SHARE_PARAM}=${encoded}`;
}

/** Système encodé contenu dans le fragment d'une adresse, ou null. */
export function sharedFromHash(hash: string): string | null {
  const params = new URLSearchParams(hash.replace(/^#/, ''));
  return params.get(SHARE_PARAM);
}
