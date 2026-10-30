import * as THREE from 'three';
import type { PlanetType } from '../physics/types';

function hashString(s: string): number {
  let h = 2166136261;
  for (let k = 0; k < s.length; k++) {
    h ^= s.charCodeAt(k);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function seeded(seed: number) {
  let s = seed || 1;
  return () => {
    s ^= s << 13;
    s ^= s >>> 17;
    s ^= s << 5;
    return ((s >>> 0) % 100000) / 100000;
  };
}

/** Variation de luminosité d'une couleur (k > 1 éclaircit, k < 1 assombrit). */
function shade(color: THREE.Color, k: number): string {
  return `#${color.clone().multiplyScalar(k).getHexString()}`;
}

/** Texture procédurale : bandes pour les géantes, taches pour les planètes rocheuses, cratères pour les naines. */
export function makePlanetTexture(type: PlanetType, color: string, seedKey: string): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 256;
  canvas.height = 128;
  const ctx = canvas.getContext('2d')!;
  const rand = seeded(hashString(seedKey));
  const base = new THREE.Color(color);
  ctx.fillStyle = color;
  ctx.fillRect(0, 0, 256, 128);

  if (type === 'geante-gazeuse' || type === 'geante-glace') {
    const contrast = type === 'geante-gazeuse' ? 0.25 : 0.08;
    let y = 0;
    while (y < 128) {
      const h = 3 + rand() * (type === 'geante-gazeuse' ? 12 : 20);
      ctx.fillStyle = shade(base, 1 + (rand() - 0.5) * 2 * contrast);
      ctx.fillRect(0, y, 256, h);
      y += h;
    }
    if (type === 'geante-gazeuse' && rand() < 0.6) {
      ctx.fillStyle = shade(base, 0.75);
      ctx.beginPath();
      ctx.ellipse(60 + rand() * 140, 70 + rand() * 20, 14, 7, 0, 0, Math.PI * 2);
      ctx.fill();
    }
  } else if (type === 'tellurique') {
    for (let k = 0; k < 60; k++) {
      ctx.fillStyle = shade(base, 0.6 + rand() * 0.7);
      ctx.globalAlpha = 0.35;
      ctx.beginPath();
      ctx.ellipse(rand() * 256, 15 + rand() * 98, 6 + rand() * 26, 4 + rand() * 14, rand() * Math.PI, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 0.7;
    ctx.fillStyle = '#f2f6fa';
    ctx.fillRect(0, 0, 256, 6);
    ctx.fillRect(0, 122, 256, 6);
    ctx.globalAlpha = 1;
  } else {
    for (let k = 0; k < 70; k++) {
      const r = 1 + rand() * 6;
      const x = rand() * 256;
      const y = 10 + rand() * 108;
      ctx.fillStyle = shade(base, 0.7);
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = shade(base, 1.2);
      ctx.lineWidth = 0.8;
      ctx.stroke();
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

let glow: THREE.CanvasTexture | null = null;

export function makeGlowTexture(): THREE.CanvasTexture {
  if (glow) return glow;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 128;
  const ctx = canvas.getContext('2d')!;
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.15, 'rgba(255,255,255,0.6)');
  g.addColorStop(0.4, 'rgba(255,255,255,0.12)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  glow = new THREE.CanvasTexture(canvas);
  return glow;
}

/**
 * Texture radiale d'anneaux : u = 0 au bord intérieur, 1 au bord extérieur.
 * Des bandes de densité variable, avec une division sombre comme celle de Cassini.
 */
export function makeRingTexture(color: string, seedKey: string): THREE.CanvasTexture {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 1;
  const ctx = canvas.getContext('2d')!;
  const rand = seeded(hashString(`anneau-${seedKey}`));
  const base = new THREE.Color(color);
  const gap = 0.55 + rand() * 0.2;
  for (let x = 0; x < 512; x++) {
    const u = x / 511;
    let alpha = 0.35 + 0.65 * rand();
    if (Math.abs(u - gap) < 0.025) alpha *= 0.08;
    alpha *= Math.min(1, u * 12, (1 - u) * 12);
    ctx.fillStyle = shade(base, 0.8 + rand() * 0.35);
    ctx.globalAlpha = alpha;
    ctx.fillRect(x, 0, 1, 1);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}
