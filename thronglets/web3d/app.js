// Thronglets 3D - the browser view.
//
// The simulation is NOT here. It runs in main_web.py, the same World the 2D
// page shows; this file only draws what /state says and sends what your hand
// does to /control. So a flock looks the same, learns the same and dies the
// same in either window - the only thing that differs is the picture.
//
// What the picture is made of: a physically-based sky whose sun really moves
// and really lights the scene (soft shadow maps, image-based ambient light
// taken from that same sky), filmic tone mapping, bloom on the things that
// glow - the signal each creature is calling, a predator's eyes - ambient
// occlusion, and instanced geometry so two hundred creatures and thirty
// thousand blades of grass are a handful of draw calls.

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { Sky } from 'three/addons/objects/Sky.js';
import { STRINGS } from '/3d/strings.js';

// ---------------------------------------------------------------- constants
const W = 200, H = 140;                       // the simulation's field, in its own units
const TOKEN_COLORS = ['#8b9088', '#eb4646', '#4682eb', '#f5c83c', '#c85ae6', '#46e1d2'];
const MOOD_COLORS = { joy: '#78d264', neutral: '#d6ccb4', sad: '#5a82d7', fear: '#e1554b' };
const PLAIN_BODY = '#e9dcc3';                 // a creature with no learned mood to show
const STATES = ['danger', 'food', 'distress', 'mate', 'idle'];
const MAX_CREATURES = 256, MAX_FOOD = 220, MAX_PREDATORS = 24;
const DAY_SECONDS = 240;                      // one full day when the clock runs

const QUALITY = {
  low:    { grass: 6000,  shadow: 1024, ao: false, bloom: true,  ratio: 1 },
  medium: { grass: 16000, shadow: 2048, ao: false, bloom: true,  ratio: Math.min(devicePixelRatio, 1.5) },
  high:   { grass: 32000, shadow: 4096, ao: true,  bloom: true,  ratio: Math.min(devicePixelRatio, 2) },
};

const SEASONS = {
  spring: { ground: '#6f9a4a', grass: ['#7fb650', '#a4cf62'], leaf: ['#7dbb5a', '#a6d36b'], flowers: 1, snow: 0 },
  summer: { ground: '#5f8a3e', grass: ['#5f9a3c', '#86b84c'], leaf: ['#3f7d3a', '#5c9a45'], flowers: .6, snow: 0 },
  autumn: { ground: '#8a7a42', grass: ['#a08f45', '#c2a04c'], leaf: ['#c9722c', '#e0a43a'], flowers: 0, snow: 0 },
  winter: { ground: '#dfe6ea', grass: ['#c9d3d6', '#eef3f5'], leaf: ['#b9c7cc', '#e6eef0'], flowers: 0, snow: 1 },
};

// ------------------------------------------------------------------ helpers
const $ = (id) => document.getElementById(id);
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const lerp = (a, b, t) => a + (b - a) * t;
const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
function rng(seed) {                           // deterministic: the landscape is the same every visit
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
function hash2(ix, iz) { const n = Math.sin(ix * 127.1 + iz * 311.7) * 43758.5453; return n - Math.floor(n); }
function noise2(x, z) {
  const ix = Math.floor(x), iz = Math.floor(z), fx = x - ix, fz = z - iz;
  const u = fx * fx * (3 - 2 * fx), v = fz * fz * (3 - 2 * fz);
  return lerp(lerp(hash2(ix, iz), hash2(ix + 1, iz), u), lerp(hash2(ix, iz + 1), hash2(ix + 1, iz + 1), u), v);
}
function fbm(x, z) { let a = 0, f = 1, w = .5; for (let i = 0; i < 4; i++) { a += noise2(x * f, z * f) * w; f *= 2; w *= .5; } return a; }

const LAKE = { x: 150, z: 26, r: 40 };
function outside(x, z) {                       // how far beyond the playing field, 0 inside it
  const dx = Math.max(0, Math.abs(x) - W / 2), dz = Math.max(0, Math.abs(z) - H / 2);
  return Math.hypot(dx, dz);
}
function groundY(x, z) {
  const d = outside(x, z);
  let y = (fbm(x * .06, z * .06) - .5) * .7;                         // the field: barely rolling
  y += smooth(8, 150, d) * (10 + 46 * fbm(x * .011 + 3.1, z * .011 - 1.7));   // hills beyond it
  const l = Math.hypot(x - LAKE.x, z - LAKE.z);
  y -= (1 - smooth(LAKE.r * .35, LAKE.r * 1.25, l)) * 7.5 * smooth(2, 26, d);  // a basin for the lake
  return y;
}
const WATER_Y = -2.2;
const simToScene = (sx, sy, out) => out.set(sx - W / 2, 0, sy - H / 2);

// ------------------------------------------------------------------ strings
let lang = (localStorage.getItem('thr-lang') || 'fr');
const T = (k) => (STRINGS[lang][k] ?? STRINGS.en[k] ?? k);
function applyStrings() {
  document.documentElement.lang = lang;
  document.querySelectorAll('[data-t]').forEach((el) => { el.textContent = T(el.dataset.t); });
  $('b-fr').classList.toggle('on', lang === 'fr');
  $('b-en').classList.toggle('on', lang === 'en');
  fillSelect('sel-season', ['spring', 'summer', 'autumn', 'winter'], view.season, 'season_');
  fillSelect('sel-weather', ['clear', 'rain', 'snow'], view.weather, 'weather_');
  fillSelect('sel-quality', ['low', 'medium', 'high'], view.quality, 'quality_');
  $('hint').textContent = T('hint_' + view.tool);
  if (last) updateUI(last);
}
function fillSelect(id, values, current, prefix) {
  const el = $(id); el.innerHTML = '';
  for (const v of values) { const o = document.createElement('option'); o.value = v; o.textContent = T(prefix + v);
    if (v === current) o.selected = true; el.appendChild(o); }
}

// --------------------------------------------------------------- view state
const view = {
  tool: 'look', season: 'summer', weather: 'clear',
  quality: localStorage.getItem('thr-quality') || 'medium',
  time: 0.42, clock: true, follow: false, selected: null,
};
let last = null;                              // the most recent /state

// ----------------------------------------------------------------- renderer
const canvas = $('scene');
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
} catch (err) {
  $('fatal').classList.remove('hidden');
  $('fatal').textContent = STRINGS[lang].noWebgl;
  throw err;
}
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.62;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0xb9d4e6, 0.0019);
const camera = new THREE.PerspectiveCamera(46, 1, 0.5, 2400);
camera.position.set(-46, 34, 118);
const controls = new OrbitControls(camera, canvas);
controls.target.set(6, 2, 4);
controls.enableDamping = true; controls.dampingFactor = .08;
controls.minDistance = 14; controls.maxDistance = 420;
controls.maxPolarAngle = Math.PI * .485;       // never under the ground
controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };

// ---------------------------------------------------------------- sky + sun
const sky = new Sky();
sky.scale.setScalar(4000);
scene.add(sky);
const skyU = sky.material.uniforms;
const sunDir = new THREE.Vector3(), moonDir = new THREE.Vector3(), tmpSky = new THREE.Color();
const sun = new THREE.DirectionalLight(0xffffff, 3);
sun.castShadow = true;
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.7;
Object.assign(sun.shadow.camera, { left: -150, right: 150, top: 130, bottom: -130, near: 10, far: 700 });
scene.add(sun, sun.target);
const hemi = new THREE.HemisphereLight(0xbfd8ff, 0x4a5a34, 0.5);
scene.add(hemi);

// The ambient light IS the sky: it is rendered into a small environment map,
// so a blue noon and an orange dusk light the undersides of things differently
// without a single hand-picked ambient colour.
const pmrem = new THREE.PMREMGenerator(renderer);
const skyScene = new THREE.Scene();
const skyCopy = new Sky(); skyCopy.scale.setScalar(4000); skyScene.add(skyCopy);
let envTarget = null, envStamp = -1;

const stars = (() => {
  const r = rng(11), n = 1400, pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const u = r() * 2 - 1, a = r() * Math.PI * 2, s = Math.sqrt(1 - u * u);
    pos.set([s * Math.cos(a) * 1800, Math.abs(u) * 1800 + 40, s * Math.sin(a) * 1800], i * 3);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const m = new THREE.PointsMaterial({ color: 0xffffff, size: 2.2, sizeAttenuation: false, transparent: true,
    opacity: 0, fog: false, depthWrite: false, toneMapped: false });
  const p = new THREE.Points(g, m); scene.add(p); return p;
})();
const moon = new THREE.Mesh(new THREE.SphereGeometry(34, 24, 16),
  new THREE.MeshBasicMaterial({ color: 0xdfe8ff, fog: false, toneMapped: false }));
scene.add(moon);

function applySky(dt) {
  const t = view.time;                         // 0 = midnight, .5 = noon
  const elev = Math.sin((t - .25) * Math.PI * 2) * 1.08;   // radians-ish, clipped by the horizon below
  const az = t * Math.PI * 2 + .6;
  sunDir.set(Math.cos(elev) * Math.sin(az), Math.sin(elev), Math.cos(elev) * Math.cos(az)).normalize();
  moonDir.copy(sunDir).multiplyScalar(-1);
  const day = smooth(-.24, .22, sunDir.y);     // 0 night .. 1 full day, through a long twilight
  const low = 1 - smooth(.05, .45, sunDir.y);  // 1 when the sun is on the horizon
  const wet = view.weather === 'clear' ? 0 : 1;

  skyU.sunPosition.value.copy(sunDir);
  skyU.turbidity.value = lerp(2.2, 14, wet);
  skyU.rayleigh.value = lerp(lerp(.25, 1.6, day), .5, wet) + low * day * 1.6;
  skyU.mieCoefficient.value = lerp(.004, .03, wet);
  skyU.mieDirectionalG.value = .82;

  // one light: the sun by day, the moon once it has set
  const useMoon = sunDir.y < -.04;
  const dir = useMoon ? moonDir : sunDir;
  sun.position.copy(dir).multiplyScalar(320);
  sun.target.position.set(0, 0, 0);
  const warm = new THREE.Color().setHSL(lerp(.08, .13, 1 - low), lerp(.85, .25, 1 - low), lerp(.62, .92, 1 - low));
  if (useMoon) { sun.color.set(0x9db4ff); sun.intensity = 1.25 * smooth(-.04, -.2, sunDir.y) * (1 - wet * .6); }
  else { sun.color.copy(warm); sun.intensity = lerp(.0, 3.4, smooth(-.02, .3, sunDir.y)) * (1 - wet * .68); }
  hemi.intensity = lerp(.42, .55, day) * (1 + wet * .5);
  hemi.color.set(0x5f74b8).lerp(tmpSky.set(0xbfd8ff), day);
  hemi.groundColor.set(0x1c2436).lerp(tmpSky.set(0x4a5a34), day);

  const fogDay = new THREE.Color(wet ? 0x9aa6ad : 0xbcd6e8);
  const fogDusk = new THREE.Color(0xe7a871), fogNight = new THREE.Color(0x121a30);
  const fog = fogNight.clone().lerp(fogDay.clone().lerp(fogDusk, low * (1 - wet) * .75), day);
  scene.fog.color.copy(fog);
  scene.fog.density = lerp(.0019, .0052, wet) + (view.season === 'winter' ? .0006 : 0);
  renderer.toneMappingExposure = lerp(.78, .62, day);

  stars.material.opacity = (1 - day) * (1 - wet) * .95;
  moon.position.copy(moonDir).multiplyScalar(1700);
  moon.visible = moonDir.y > -.05 && !wet;

  // re-bake the ambient light only when the sky has visibly moved
  const stamp = Math.round(t * 240) + (wet ? 1000 : 0);
  if (stamp !== envStamp) {
    envStamp = stamp;
    for (const k of ['sunPosition', 'turbidity', 'rayleigh', 'mieCoefficient', 'mieDirectionalG'])
      skyCopy.material.uniforms[k].value = skyU[k].value.clone ? skyU[k].value.clone() : skyU[k].value;
    const next = pmrem.fromScene(skyScene, 0, .5, 3000);
    if (envTarget) envTarget.dispose();
    envTarget = next;
    scene.environment = next.texture;
  }
  scene.environmentIntensity = lerp(.35, .62, day);
}

// ------------------------------------------------------------------ terrain
const terrain = (() => {
  const g = new THREE.PlaneGeometry(1100, 1100, 260, 260);
  g.rotateX(-Math.PI / 2);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) p.setY(i, groundY(p.getX(i), p.getZ(i)));
  g.computeVertexNormals();
  g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(p.count * 3), 3));
  const m = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .96, metalness: 0 });
  const mesh = new THREE.Mesh(g, m); mesh.receiveShadow = true; scene.add(mesh); return mesh;
})();
function paintTerrain() {
  const s = SEASONS[view.season], g = terrain.geometry, p = g.attributes.position, n = g.attributes.normal;
  const col = g.attributes.color, base = new THREE.Color(s.ground), rock = new THREE.Color('#7d776c');
  const sand = new THREE.Color('#b9a97c'), snow = new THREE.Color('#f2f5f7'), c = new THREE.Color();
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const steep = 1 - smooth(.72, .93, n.getY(i));
    c.copy(base).offsetHSL(0, 0, (fbm(x * .09, z * .09) - .5) * .09);
    c.lerp(sand, 1 - smooth(WATER_Y + .2, WATER_Y + 2.2, y));        // a shore around the water
    c.lerp(rock, steep * .85);
    c.lerp(snow, clamp(smooth(30, 52, y) + s.snow * (1 - steep) * .75, 0, 1));
    col.setXYZ(i, c.r, c.g, c.b);
  }
  col.needsUpdate = true;
}

// the playing field's edge, drawn faintly so "inside" is readable from above
(() => {
  const pts = [];
  const add = (x, z) => pts.push(new THREE.Vector3(x, groundY(x, z) + .12, z));
  for (let x = -W / 2; x <= W / 2; x += 4) add(x, -H / 2);
  for (let z = -H / 2; z <= H / 2; z += 4) add(W / 2, z);
  for (let x = W / 2; x >= -W / 2; x -= 4) add(x, H / 2);
  for (let z = H / 2; z >= -H / 2; z -= 4) add(-W / 2, z);
  const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
    new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: .16 }));
  scene.add(line);
})();

// -------------------------------------------------------------------- water
const water = (() => {
  const g = new THREE.CircleGeometry(LAKE.r * 1.5, 64); g.rotateX(-Math.PI / 2);
  const m = new THREE.MeshPhysicalMaterial({ color: 0x2f6f86, roughness: .06, metalness: .0,
    transmission: 0, clearcoat: 1, clearcoatRoughness: .04, envMapIntensity: 1.6,
    transparent: true, opacity: .86 });
  // small moving ripples, written straight into the standard shader's normal
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uTime = water_time;
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWp;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvWp = (modelMatrix * vec4(position,1.0)).xyz;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform float uTime; varying vec3 vWp;')
      .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
        vec2 q = vWp.xz * .35;
        float rx = sin(q.x * 1.7 + uTime * 1.3) * .5 + sin(q.y * 2.3 - uTime * 1.1) * .5 + sin((q.x + q.y) * 3.1 + uTime * 1.9) * .3;
        float rz = cos(q.y * 1.9 + uTime * 1.2) * .5 + cos(q.x * 2.7 - uTime * .9) * .5 + cos((q.x - q.y) * 2.9 - uTime * 1.7) * .3;
        normal = normalize(normal + (viewMatrix * vec4(rx, 0.0, rz, 0.0)).xyz * .045);`);
  };
  const mesh = new THREE.Mesh(g, m); mesh.position.set(LAKE.x, WATER_Y, LAKE.z); mesh.receiveShadow = true;
  scene.add(mesh); return mesh;
})();
var water_time = { value: 0 };

// -------------------------------------------------------- trees, rocks, etc
const dummy = new THREE.Object3D();
const flora = { trunks: null, leaves: null, rocks: null, flowers: null, grass: null, treeSpots: [] };
function buildFlora() {
  const r = rng(7), spots = [];
  for (let tries = 0; spots.length < 190 && tries < 6000; tries++) {
    const x = (r() - .5) * 560, z = (r() - .5) * 520, d = outside(x, z);
    if (d > 190 || groundY(x, z) < WATER_Y + 1.4 || groundY(x, z) > 34) continue;
    if (d === 0 && r() > .035) continue;                   // only a few inside, so the flock stays visible
    if (spots.some((s) => Math.hypot(s.x - x, s.z - z) < 7)) continue;
    spots.push({ x, z, y: groundY(x, z), s: .8 + r() * .9, tilt: (r() - .5) * .12, kind: r() });
  }
  flora.treeSpots = spots;
  const trunkG = new THREE.CylinderGeometry(.42, .7, 6, 7); trunkG.translate(0, 3, 0);
  flora.trunks = new THREE.InstancedMesh(trunkG, new THREE.MeshStandardMaterial({ color: 0x6b4a32, roughness: .95 }), spots.length);
  const leafG = new THREE.IcosahedronGeometry(1, 1);
  flora.leaves = new THREE.InstancedMesh(leafG, new THREE.MeshStandardMaterial({ roughness: .85, flatShading: true }), spots.length * 3);
  for (const m of [flora.trunks, flora.leaves]) { m.castShadow = true; m.receiveShadow = true; scene.add(m); }
  spots.forEach((s, i) => {
    dummy.position.set(s.x, s.y - .3, s.z); dummy.rotation.set(s.tilt, s.kind * 6, s.tilt); dummy.scale.setScalar(s.s);
    dummy.updateMatrix(); flora.trunks.setMatrixAt(i, dummy.matrix);
    const blobs = [[0, 7.4, 0, 3.4], [1.5, 6.0, .7, 2.5], [-1.3, 6.3, -.9, 2.6]];
    blobs.forEach((b, k) => {
      dummy.position.set(s.x + b[0] * s.s, s.y + b[1] * s.s, s.z + b[2] * s.s);
      dummy.rotation.set(s.kind * 3 + k, s.kind * 5 + k * 2, 0);
      dummy.scale.set(b[3] * s.s, b[3] * s.s * (s.kind > .5 ? 1.25 : .9), b[3] * s.s);
      dummy.updateMatrix(); flora.leaves.setMatrixAt(i * 3 + k, dummy.matrix);
    });
  });

  const rr = rng(21), rocks = [];
  for (let tries = 0; rocks.length < 70 && tries < 3000; tries++) {
    const x = (rr() - .5) * 520, z = (rr() - .5) * 480, d = outside(x, z);
    if (d > 170 || (d === 0 && rr() > .1) || groundY(x, z) < WATER_Y + .5) continue;
    rocks.push({ x, z, s: .6 + rr() * rr() * 3.4, a: rr() * 6, b: rr() * 6 });
  }
  flora.rocks = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(1, 0),
    new THREE.MeshStandardMaterial({ color: 0x8b8880, roughness: .9, flatShading: true }), rocks.length);
  rocks.forEach((k, i) => { dummy.position.set(k.x, groundY(k.x, k.z) + k.s * .25, k.z); dummy.rotation.set(k.a, k.b, k.a);
    dummy.scale.set(k.s * 1.3, k.s * .8, k.s); dummy.updateMatrix(); flora.rocks.setMatrixAt(i, dummy.matrix); });
  flora.rocks.castShadow = flora.rocks.receiveShadow = true; scene.add(flora.rocks);

  const fr = rng(33), N = 520;
  flora.flowers = new THREE.InstancedMesh(new THREE.SphereGeometry(.34, 8, 6),
    new THREE.MeshStandardMaterial({ roughness: .6 }), N);
  const hues = ['#f2f0ea', '#f6d24a', '#e86aa0', '#b98cf0', '#ff8f5a'];
  for (let i = 0; i < N; i++) {
    const x = (fr() - .5) * (W + 90), z = (fr() - .5) * (H + 90);
    dummy.position.set(x, groundY(x, z) + .55 + fr() * .25, z); dummy.rotation.set(0, 0, 0);
    dummy.scale.setScalar(.7 + fr() * .7); dummy.updateMatrix(); flora.flowers.setMatrixAt(i, dummy.matrix);
    flora.flowers.setColorAt(i, new THREE.Color(hues[Math.floor(fr() * hues.length)]));
  }
  scene.add(flora.flowers);
}

const grassTime = { value: 0 };
function buildGrass() {
  if (flora.grass) { scene.remove(flora.grass); flora.grass.geometry.dispose(); flora.grass.material.dispose(); }
  const n = QUALITY[view.quality].grass, r = rng(5);
  const g = new THREE.PlaneGeometry(.34, 1.5, 1, 3); g.translate(0, .75, 0);
  const m = new THREE.MeshStandardMaterial({ roughness: .8, side: THREE.DoubleSide });
  // the wind: bend each blade by its height, out of phase by where it stands
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uTime = grassTime;
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nuniform float uTime;')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
        vec4 wp = instanceMatrix * vec4(0.0, 0.0, 0.0, 1.0);
        float sway = sin(uTime * 1.6 + wp.x * .21 + wp.z * .17) + .5 * sin(uTime * 2.9 + wp.x * .43);
        float bend = position.y * position.y * .22;
        transformed.x += sway * bend; transformed.z += sway * bend * .6;
        transformed.x *= 1.0 - position.y * .55;`);
  };
  const mesh = new THREE.InstancedMesh(g, m, n);
  mesh.receiveShadow = true;
  let i = 0;
  for (let tries = 0; i < n && tries < n * 4; tries++) {
    const x = (r() - .5) * (W + 130), z = (r() - .5) * (H + 130), y = groundY(x, z);
    if (y < WATER_Y + .7 || noise2(x * .08 + 9, z * .08) < .28) continue;   // bare patches, like real ground
    dummy.position.set(x, y - .05, z); dummy.rotation.set(0, r() * Math.PI, (r() - .5) * .3);
    const h = .6 + r() * 1.0; dummy.scale.set(1 + r() * .6, h, 1); dummy.updateMatrix();
    mesh.setMatrixAt(i++, dummy.matrix);
  }
  mesh.count = i; mesh.userData.total = i; mesh.userData.seed = [];
  for (let k = 0; k < i; k++) mesh.userData.seed.push(r());
  flora.grass = mesh; scene.add(mesh); paintFlora();
}
function paintFlora() {
  const s = SEASONS[view.season], a = new THREE.Color(), b = new THREE.Color(), c = new THREE.Color();
  if (flora.leaves) {
    a.set(s.leaf[0]); b.set(s.leaf[1]);
    flora.treeSpots.forEach((sp, i) => { for (let k = 0; k < 3; k++) {
      c.copy(a).lerp(b, (sp.kind * 7 + k * .37) % 1); flora.leaves.setColorAt(i * 3 + k, c); } });
    flora.leaves.instanceColor.needsUpdate = true;
    flora.leaves.count = flora.treeSpots.length * 3;
    flora.flowers.count = Math.round(520 * s.flowers);
  }
  if (flora.grass) {
    a.set(s.grass[0]); b.set(s.grass[1]);
    const seed = flora.grass.userData.seed;
    for (let i = 0; i < flora.grass.userData.total; i++) { c.copy(a).lerp(b, seed[i]); flora.grass.setColorAt(i, c); }
    flora.grass.instanceColor.needsUpdate = true;
    flora.grass.count = Math.round(flora.grass.userData.total * (s.snow ? .22 : 1));
    flora.grass.scale.y = s.snow ? .55 : 1;
  }
}

// ---------------------------------------------------------------- creatures
// One instanced mesh per body part. Each creature is a base transform
// (where it stands, which way it faces, how squashed its hop has it) times a
// fixed local transform for the part.
function part(geo, mat, local, shadow = true) {
  const mesh = new THREE.InstancedMesh(geo, mat, MAX_CREATURES);
  mesh.count = 0; mesh.castShadow = shadow; mesh.receiveShadow = shadow; mesh.frustumCulled = false;
  const m = new THREE.Matrix4();
  dummy.position.set(local[0], local[1], local[2]); dummy.rotation.set(0, 0, 0);
  dummy.scale.set(local[3], local[4] ?? local[3], local[5] ?? local[3]); dummy.updateMatrix(); m.copy(dummy.matrix);
  scene.add(mesh); return { mesh, local: m };
}
const sphere = new THREE.SphereGeometry(1, 28, 20), sphereLo = new THREE.SphereGeometry(1, 14, 10);
const bodyMat = new THREE.MeshPhysicalMaterial({ roughness: .62, sheen: 1, sheenRoughness: .45,
  sheenColor: new THREE.Color(0xffffff), clearcoat: .15, clearcoatRoughness: .6 });
const footMat = new THREE.MeshStandardMaterial({ color: 0x4a3b33, roughness: .7 });
const eyeMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: .15 });
const pupilMat = new THREE.MeshStandardMaterial({ color: 0x14100e, roughness: .1 });
const orbMat = new THREE.MeshBasicMaterial({ toneMapped: false });
const stalkMat = new THREE.MeshStandardMaterial({ color: 0x5a4a40, roughness: .8 });
const P = {
  body:   part(sphere, bodyMat, [0, 1.55, 0, 1.55, 1.42, 1.5]),
  footL:  part(sphereLo, footMat, [-.62, .3, .25, .5, .3, .68]),
  footR:  part(sphereLo, footMat, [.62, .3, .25, .5, .3, .68]),
  eyeL:   part(sphereLo, eyeMat, [-.55, 1.95, 1.2, .4]),
  eyeR:   part(sphereLo, eyeMat, [.55, 1.95, 1.2, .4]),
  pupilL: part(sphereLo, pupilMat, [-.55, 1.95, 1.52, .2], false),
  pupilR: part(sphereLo, pupilMat, [.55, 1.95, 1.52, .2], false),
  stalk:  part(new THREE.CylinderGeometry(.06, .08, 1, 6), stalkMat, [0, 3.25, 0, 1, .7, 1], false),
  orb:    part(sphereLo, orbMat, [0, 3.85, 0, .36], false),
};
const creatures = new Map();                  // id -> what we are drawing for it
const ghosts = [];                            // the ones that just died, shrinking away

const selRing = new THREE.Mesh(new THREE.RingGeometry(2.2, 2.7, 48),
  new THREE.MeshBasicMaterial({ color: 0x8fe3c0, transparent: true, opacity: .9, toneMapped: false,
    side: THREE.DoubleSide, depthWrite: false }));
selRing.rotation.x = -Math.PI / 2; selRing.visible = false; scene.add(selRing);

function syncCreatures(list) {
  const seen = new Set();
  for (const c of list) {
    seen.add(c.id);
    let k = creatures.get(c.id);
    if (!k) {
      k = { id: c.id, x: c.x - W / 2, z: c.y - H / 2, tx: 0, tz: 0, heading: Math.random() * 6, scale: 0,
            hop: Math.random() * 6, speed: 0, blink: Math.random() * 5, body: new THREE.Color(), orb: new THREE.Color() };
      creatures.set(c.id, k);
    }
    k.tx = c.x - W / 2; k.tz = c.y - H / 2; k.token = c.token; k.mood = c.mood; k.energy = c.energy; k.state = c.state;
  }
  for (const [id, k] of creatures) if (!seen.has(id)) { creatures.delete(id); k.dying = 1; ghosts.push(k); }
}
const mBase = new THREE.Matrix4(), mOut = new THREE.Matrix4(), q = new THREE.Quaternion(),
  vPos = new THREE.Vector3(), vScale = new THREE.Vector3(), yAxis = new THREE.Vector3(0, 1, 0), tmpC = new THREE.Color();
function drawCreatures(dt, time) {
  let i = 0;
  const follow = 1 - Math.exp(-dt * 9);
  const draw = (k, alive) => {
    if (i >= MAX_CREATURES) return;
    if (alive) {
      const dx = k.tx - k.x, dz = k.tz - k.z, dist = Math.hypot(dx, dz);
      if (dist > 60) { k.x = k.tx; k.z = k.tz; }                 // a reset: do not glide across the map
      else { k.x += dx * follow; k.z += dz * follow; }
      k.speed = lerp(k.speed, dist, .2);
      if (dist > .04) { let d = Math.atan2(dx, dz) - k.heading; d = Math.atan2(Math.sin(d), Math.cos(d)); k.heading += d * (1 - Math.exp(-dt * 7)); }
      k.scale = Math.min(1, k.scale + dt * 1.6);                 // born small
    } else { k.dying -= dt * 1.5; k.scale = Math.max(0, k.dying) * Math.max(0, k.dying); }
    const moving = clamp(k.speed * 1.4, 0, 1);
    k.hop += dt * (5 + moving * 9);
    const up = Math.abs(Math.sin(k.hop)) * (.12 + moving * .7), squash = 1 + Math.sin(k.hop * 2) * .05 * (.4 + moving);
    const fear = k.mood === 'fear' ? Math.sin(time * 38 + k.id) * .05 : 0;     // a frightened one trembles
    const size = k.scale * (.86 + .22 * clamp(k.energy ?? .5, 0, 1));
    vPos.set(k.x + fear, groundY(k.x, k.z) + up, k.z);
    q.setFromAxisAngle(yAxis, k.heading);
    vScale.set(size / Math.sqrt(squash), size * squash, size / Math.sqrt(squash));
    mBase.compose(vPos, q, vScale);
    k.y = vPos.y;
    const blink = (time + k.blink) % 4.2 < .12 ? .1 : 1;
    for (const key in P) {
      mOut.multiplyMatrices(mBase, P[key].local);
      if (blink < 1 && (key === 'eyeL' || key === 'eyeR' || key === 'pupilL' || key === 'pupilR')) {
        dummy.matrix.copy(mOut); dummy.matrix.decompose(dummy.position, dummy.quaternion, dummy.scale);
        dummy.scale.y *= blink; dummy.updateMatrix(); mOut.copy(dummy.matrix);
      }
      P[key].mesh.setMatrixAt(i, mOut);
    }
    tmpC.set(k.mood ? MOOD_COLORS[k.mood] : PLAIN_BODY); k.body.lerp(tmpC, k.scale < 1 ? 1 : .08);
    P.body.mesh.setColorAt(i, k.body);
    // the call it is making right now. Silence is a dull bead; a word glows.
    const pulse = k.token ? 7.5 + Math.sin(time * 5 + k.id) * 1.5 : .25;
    tmpC.set(TOKEN_COLORS[k.token ?? 0]).multiplyScalar(pulse); k.orb.lerp(tmpC, .25);
    P.orb.mesh.setColorAt(i, k.orb);
    i++;
  };
  for (const k of creatures.values()) draw(k, true);
  for (let g = ghosts.length - 1; g >= 0; g--) { if (ghosts[g].dying <= 0) ghosts.splice(g, 1); else draw(ghosts[g], false); }
  for (const key in P) { const m = P[key].mesh; m.count = i; m.instanceMatrix.needsUpdate = true;
    if (m.instanceColor) m.instanceColor.needsUpdate = true; }

  const s = view.selected != null ? creatures.get(view.selected) : null;
  selRing.visible = !!s;
  if (s) { selRing.position.set(s.x, groundY(s.x, s.z) + .15, s.z); selRing.scale.setScalar(1 + Math.sin(time * 4) * .06);
    if (view.follow) controls.target.lerp(vPos.set(s.x, 1.5, s.z), 1 - Math.exp(-dt * 4)); }
}

// ------------------------------------------------------- food and predators
const food = new THREE.InstancedMesh(new THREE.SphereGeometry(.55, 12, 9),
  new THREE.MeshStandardMaterial({ color: 0x9be25a, emissive: 0x6edc5a, emissiveIntensity: .55, roughness: .35 }), MAX_FOOD);
food.count = 0; food.castShadow = true; food.frustumCulled = false; scene.add(food);
let foodList = [];
function drawFood(time) {
  const n = Math.min(MAX_FOOD, foodList.length);
  for (let i = 0; i < n; i++) {
    const x = foodList[i][0] - W / 2, z = foodList[i][1] - H / 2;
    dummy.position.set(x, groundY(x, z) + .75 + Math.sin(time * 2 + x) * .12, z);
    dummy.rotation.set(0, 0, 0); dummy.scale.setScalar(1); dummy.updateMatrix(); food.setMatrixAt(i, dummy.matrix);
  }
  food.count = n; food.instanceMatrix.needsUpdate = true;
}

const predators = [];
function makePredator() {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.IcosahedronGeometry(2.3, 1),
    new THREE.MeshStandardMaterial({ color: 0x2a1518, roughness: .5, metalness: .2, flatShading: true }));
  body.position.y = 2.5; body.scale.set(1, .85, 1.25); body.castShadow = true; g.add(body);
  const spikeM = new THREE.MeshStandardMaterial({ color: 0x1a0c0e, roughness: .4, flatShading: true });
  for (let i = 0; i < 9; i++) {
    const s = new THREE.Mesh(new THREE.ConeGeometry(.42, 1.9, 5), spikeM);
    const a = (i / 9) * Math.PI * 2;
    s.position.set(Math.cos(a) * 1.5, 3.9 + Math.sin(i * 2.1) * .4, Math.sin(a) * 1.9 - .3);
    s.rotation.set(Math.sin(a) * .7 - .2, 0, -Math.cos(a) * .7); s.castShadow = true; g.add(s);
  }
  const eyeM = new THREE.MeshBasicMaterial({ color: new THREE.Color(14, .5, .3), toneMapped: false });
  for (const sx of [-.8, .8]) { const e = new THREE.Mesh(new THREE.SphereGeometry(.3, 10, 8), eyeM); e.position.set(sx, 2.9, 2.7); g.add(e); }
  g.visible = false; scene.add(g);
  return { g, x: 0, z: 0, heading: 0, fresh: true };
}
for (let i = 0; i < MAX_PREDATORS; i++) predators.push(makePredator());
let predList = [];
function drawPredators(dt, time) {
  predators.forEach((p, i) => {
    const t = predList[i];
    if (!t) { p.g.visible = false; p.fresh = true; return; }
    const tx = t[0] - W / 2, tz = t[1] - H / 2;
    if (p.fresh) { p.x = tx; p.z = tz; p.fresh = false; }
    const dx = tx - p.x, dz = tz - p.z, k = 1 - Math.exp(-dt * 9);
    if (Math.hypot(dx, dz) > .03) { let d = Math.atan2(dx, dz) - p.heading; d = Math.atan2(Math.sin(d), Math.cos(d)); p.heading += d * (1 - Math.exp(-dt * 5)); }
    p.x += dx * k; p.z += dz * k;
    p.g.visible = true; p.g.position.set(p.x, groundY(p.x, p.z) + Math.abs(Math.sin(time * 6 + i)) * .25, p.z);
    p.g.rotation.y = p.heading;
  });
}

// ------------------------------------------------------------------ weather
const precip = (() => {
  const n = 2600, pos = new Float32Array(n * 3), r = rng(3);
  for (let i = 0; i < n; i++) pos.set([(r() - .5) * 260, r() * 120, (r() - .5) * 260], i * 3);
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const dot = document.createElement('canvas'); dot.width = dot.height = 32;
  const cx = dot.getContext('2d'), grad = cx.createRadialGradient(16, 16, 0, 16, 16, 16);
  grad.addColorStop(0, 'rgba(255,255,255,1)'); grad.addColorStop(.5, 'rgba(255,255,255,.7)'); grad.addColorStop(1, 'rgba(255,255,255,0)');
  cx.fillStyle = grad; cx.fillRect(0, 0, 32, 32);
  const m = new THREE.PointsMaterial({ color: 0xffffff, size: .7, transparent: true, opacity: .8, depthWrite: false,
    map: new THREE.CanvasTexture(dot), alphaTest: .02 });
  const p = new THREE.Points(g, m); p.visible = false; p.frustumCulled = false; scene.add(p); return p;
})();
function drawWeather(dt) {
  const kind = view.weather;
  precip.visible = kind !== 'clear';
  if (!precip.visible) return;
  const rain = kind === 'rain', a = precip.geometry.attributes.position, speed = rain ? 95 : 11;
  precip.material.size = rain ? .3 : .6; precip.material.opacity = rain ? .55 : .9;
  precip.material.color.set(rain ? 0xa9c3d6 : 0xffffff);
  for (let i = 0; i < a.count; i++) {
    let y = a.getY(i) - speed * dt;
    if (!rain) a.setX(i, a.getX(i) + Math.sin(y * .3 + i) * dt * 2.5);
    if (y < -3) y += 120;
    a.setY(i, y);
  }
  a.needsUpdate = true;
  precip.position.set(controls.target.x, 0, controls.target.z);
}

// ----------------------------------------------------------- the hand marker
const handRing = new THREE.Mesh(new THREE.RingGeometry(.86, 1, 48),
  new THREE.MeshBasicMaterial({ transparent: true, opacity: .75, toneMapped: false, side: THREE.DoubleSide, depthWrite: false }));
handRing.rotation.x = -Math.PI / 2; handRing.visible = false; scene.add(handRing);
const TOOL_RING = { look: [0xffffff, 2.2], food: [0x9be25a, 12], predator: [0xff5a4a, 3.5], fire: [0xff9a3a, 6] };

// ------------------------------------------------------------ post-processing
let composer, bloom, ao, smaa;
function buildPipeline() {
  const qv = QUALITY[view.quality];
  renderer.setPixelRatio(qv.ratio);
  renderer.setSize(innerWidth, innerHeight, false);
  sun.shadow.mapSize.set(qv.shadow, qv.shadow);
  if (sun.shadow.map) { sun.shadow.map.dispose(); sun.shadow.map = null; }
  const target = new THREE.WebGLRenderTarget(innerWidth * qv.ratio, innerHeight * qv.ratio,
    { type: THREE.HalfFloatType, samples: 0 });
  composer = new EffectComposer(renderer, target);
  composer.addPass(new RenderPass(scene, camera));
  if (qv.ao) {
    ao = new GTAOPass(scene, camera, innerWidth, innerHeight);
    ao.updateGtaoMaterial({ radius: 2.2, distanceExponent: 1.2, thickness: 1.2, scale: 1.1, samples: 12 });
    composer.addPass(ao);
  }
  if (qv.bloom) { bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), .42, .55, 3.2); composer.addPass(bloom); }
  composer.addPass(new OutputPass());
  smaa = new SMAAPass(innerWidth * qv.ratio, innerHeight * qv.ratio); composer.addPass(smaa);
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
}
addEventListener('resize', buildPipeline);

// ------------------------------------------------------------------ network
async function post(action, extra = {}) {
  try {
    const r = await fetch('/control', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, ...extra }) });
    return await r.json();
  } catch { return null; }
}
let polling = false;
async function poll() {
  if (polling) return; polling = true;
  try {
    const r = await fetch('/state'); const s = await r.json();
    last = s;
    $('start').classList.toggle('hidden', !!s.started);
    if (!s.started) { $('o-resume').classList.toggle('hidden', !s.save_exists); }
    else { syncCreatures(s.creatures); foodList = s.food; predList = s.predators; updateUI(s); }
  } catch { /* the server is restarting; keep the last picture */ }
  polling = false;
}

// ----------------------------------------------------------------------- UI
const pct = (v) => Math.round(v * 100) + '%';
const signedPct = (v) => (v >= 0 ? '+' : '') + Math.round(v * 100) + '%';
function setSigned(el, v) {                    // a bar growing from the middle
  const half = clamp(Math.abs(v), 0, 1) * 50;
  el.style.left = (v >= 0 ? 50 : 50 - half) + '%'; el.style.width = half + '%';
  el.style.background = v > .05 ? 'var(--good)' : v < -.05 ? 'var(--bad)' : '#9aa69a';
}
function updateUI(s) {
  $('s-pop').textContent = s.pop; $('s-births').textContent = s.births; $('s-deaths').textContent = s.deaths;
  $('s-tick').textContent = s.tick; $('s-speed').textContent = 'x' + s.speed;
  $('b-pause').textContent = s.paused ? T('resume') : T('pause');
  $('b-pause').classList.toggle('on', s.paused);

  const learning = !!s.disposition;
  $('f-learning').classList.toggle('hidden', !learning);
  $('f-nolearning').classList.toggle('hidden', learning);
  if (learning) {
    const d = s.disposition.value;
    setSigned($('f-disp-fill'), d);
    $('f-disp-text').textContent = T('theFlock') + ' ' + (lang === 'fr' ? s.disposition.label_fr : s.disposition.label_en)
      + '  ' + signedPct(d);
    const ch = s.choices || { approach: 0, flee: 0, ignore: 1 };
    $('f-ch-a').style.width = pct(ch.approach); $('f-ch-f').style.width = pct(ch.flee); $('f-ch-i').style.width = pct(ch.ignore);
    $('f-ch-text').innerHTML = `<span class="a">${pct(ch.approach)} ${T('chApproach')}</span>` +
      `<span class="f">${pct(ch.flee)} ${T('chFlee')}</span><span class="i">${pct(ch.ignore)} ${T('chIgnore')}</span>`;
    const dr = s.dread;
    $('f-dread-fill').style.width = pct(dr ? dr.understood : 0);
    $('f-dread-text').textContent = !dr || dr.understood <= 0 ? T('dreadNone')
      : T('dreadSome').replace('{pct}', Math.round(dr.understood * 100)).replace('{gain}', Math.round(dr.mean_bonus * 100));
  }
  let html = '';
  for (const st of STATES) {
    const top = (s.vocabulary[st] || [])[0] || [0, 0];
    const dot = top[0] === 0 ? '<span class="dot silent"></span>' : `<span class="dot" style="background:${TOKEN_COLORS[top[0]]}"></span>`;
    html += `<div class="vrow"><span class="name">${T('st_' + st)}</span>${dot}<span class="bar"><div style="width:${pct(top[1])};` +
      `background:${TOKEN_COLORS[top[0]]}"></div></span><span class="pct">${pct(top[1])}</span></div>`;
  }
  $('f-vocab').innerHTML = html;
  const db = s.deaths_by || {};
  $('f-deaths').textContent = `${T('dPred')} ${db.predator ?? 0} · ${T('dStarve')} ${db.starved ?? 0} · ${T('dAge')} ${db.age ?? 0} · ${T('dYou')} ${db.killed ?? 0}`;

  const m = s.selected;
  if (view.selected != null && !m) { view.selected = null; }
  $('mind').classList.toggle('hidden', !m);
  if (!m) return;
  $('m-title').textContent = T('creature') + ' #' + m.id;
  $('m-swatch').style.background = TOKEN_COLORS[m.token ?? 0]; $('m-swatch').style.color = TOKEN_COLORS[m.token ?? 0];
  $('m-meta').textContent = `${T('generation')} ${m.generation} · ${T('age')} ${m.age} · ${T('st_' + m.state)}`;
  $('m-energy').style.width = pct(m.energy ?? 0);
  const has = m.value !== undefined;
  $('m-learned').classList.toggle('hidden', !has);
  if (!has) return;
  $('m-feeling').textContent = (lang === 'fr' ? m.disposition_fr : m.disposition_en) + '  ' + signedPct(m.disposition);
  $('m-mood').innerHTML = `<span style="color:${MOOD_COLORS[m.emotion]}">● ${T('mood_' + m.emotion)}</span>` +
    ` · ${T('valence')} ${signedPct(m.valence)} · ${T('arousal')} ${pct(m.arousal)}`;
  setSigned($('m-value'), m.value);
  $('m-decided').textContent = `${T('decided')} ${T('act_' + m.act)} (${pct(m.confidence)}) · ${T('surprise')} ${m.surprise.toFixed(3)}`;
  $('m-dread').style.width = pct(clamp(m.flee_bonus / .6, 0, 1));
  $('m-dread-text').textContent = m.dread > 0 ? T('runs').replace('{pct}', Math.round(m.flee_bonus * 100)) : T('hunterNone');
  $('m-words').innerHTML = m.meanings.map((v, i) => {
    const h = Math.max(2, Math.min(1, Math.abs(v) / .08) * 20);
    return `<div class="w"><div class="col" style="height:${h}px;background:${v > 0 ? 'var(--good)' : 'var(--bad)'}"></div>` +
      `<div class="dot" style="background:${TOKEN_COLORS[i + 1]}"></div></div>`; }).join('');
  $('m-dwells-n').textContent = `(${m.memories.length}/${m.replay_size})`;
  $('m-mem').innerHTML = m.memories.length ? m.memories.map((k) => {
    const col = k.target > 0 ? 'var(--good)' : 'var(--bad)';
    return `<tr><td style="width:56px"><span class="mb" style="width:${Math.max(2, Math.min(1, k.shock / .6) * 50)}px;background:${col}"></span></td>` +
      `<td>${lang === 'fr' ? k.label_fr : k.label_en}</td><td class="v" style="color:${col}">${k.target >= 0 ? '+' : ''}${k.target.toFixed(2)}</td></tr>`;
  }).join('') : `<tr><td class="dim">${T('dwellsNone')}</td></tr>`;
}
function toast(msg) { const t = $('toast'); t.textContent = msg; t.classList.remove('hidden');
  clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.add('hidden'), 1800); }

// -------------------------------------------------------------------- input
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0),
  hit = new THREE.Vector3(), proj = new THREE.Vector3();
function groundAt(ev) {                        // where on the field the cursor points, in SIM units
  ndc.set((ev.clientX / innerWidth) * 2 - 1, -(ev.clientY / innerHeight) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  if (!ray.ray.intersectPlane(groundPlane, hit)) return null;
  const sx = hit.x + W / 2, sy = hit.z + H / 2;
  return { sx, sy, x: hit.x, z: hit.z, inside: sx >= 0 && sx <= W && sy >= 0 && sy <= H };
}
function creatureAt(ev) {                      // the creature under the cursor, judged on screen
  let best = null, bestD = 1e9;
  for (const k of creatures.values()) {
    proj.set(k.x, (k.y ?? 0) + 1.6, k.z).project(camera);
    if (proj.z > 1) continue;
    const px = (proj.x + 1) / 2 * innerWidth, py = (1 - proj.y) / 2 * innerHeight;
    const dist = camera.position.distanceTo(vPos.set(k.x, 1.6, k.z));
    const radius = Math.max(12, 1.9 * innerHeight / (2 * Math.tan(camera.fov * Math.PI / 360) * dist));
    const d = Math.hypot(px - ev.clientX, py - ev.clientY);
    if (d < radius && d < bestD) { best = k; bestD = d; }
  }
  return best;
}
function select(id) { view.selected = id; if (id == null) view.follow = false; $('m-follow').classList.toggle('on', view.follow); post('select', { id }); }
function setTool(tool) {
  view.tool = tool;
  document.querySelectorAll('.tool').forEach((b) => b.classList.toggle('on', b.dataset.tool === tool));
  $('hint').textContent = T('hint_' + tool);
  post('fire_tool', { armed: tool === 'fire' });
}
let down = null, handStamp = 0;
canvas.addEventListener('pointerdown', (ev) => { down = { x: ev.clientX, y: ev.clientY, b: ev.button }; $('ctx').classList.add('hidden'); });
canvas.addEventListener('pointerup', (ev) => {
  if (!down || Math.hypot(ev.clientX - down.x, ev.clientY - down.y) > 6) { down = null; return; }   // that was a drag
  const c = creatureAt(ev), g = groundAt(ev);
  if (down.b === 2) { if (c) openMenu(ev, c); down = null; return; }
  if (view.tool === 'look') select(c ? c.id : null);
  else if (g && g.inside) post('click', { x: g.sx, y: g.sy, button: view.tool === 'predator' ? 'right' : 'left' });
  down = null;
});
canvas.addEventListener('contextmenu', (ev) => ev.preventDefault());
canvas.addEventListener('pointermove', (ev) => {
  const g = groundAt(ev), now = performance.now();
  const ring = TOOL_RING[view.tool];
  handRing.visible = !!(g && g.inside);
  if (g && g.inside) { handRing.position.set(g.x, groundY(g.x, g.z) + .2, g.z); handRing.scale.setScalar(ring[1]); handRing.material.color.set(ring[0]); }
  canvas.style.cursor = view.tool === 'look' && creatureAt(ev) ? 'pointer' : 'default';
  if (now - handStamp > 60) { handStamp = now; post('hand', g && g.inside ? { x: g.sx, y: g.sy } : { x: null, y: null }); }
});
canvas.addEventListener('pointerleave', () => { handRing.visible = false; post('hand', { x: null, y: null }); });

function openMenu(ev, c) {
  select(c.id);
  const el = $('ctx');
  el.innerHTML = ['pet', 'feed', 'hurt', 'kill'].map((k) =>
    `<button class="${k === 'pet' || k === 'feed' ? 'good' : 'bad'}" data-act="${k}">${T('act' + k[0].toUpperCase() + k.slice(1))}</button>`).join('');
  el.style.left = Math.min(ev.clientX, innerWidth - 190) + 'px'; el.style.top = Math.min(ev.clientY, innerHeight - 170) + 'px';
  el.classList.remove('hidden');
}
document.addEventListener('click', (ev) => {
  const act = ev.target.closest('[data-act]');
  if (act && view.selected != null) { post('act', { id: view.selected, kind: act.dataset.act }); $('ctx').classList.add('hidden'); }
});
document.querySelectorAll('.tool').forEach((b) => b.addEventListener('click', () => setTool(b.dataset.tool)));
$('b-pause').onclick = () => post(last && last.paused ? 'resume' : 'pause');
$('b-slower').onclick = () => last && post('speed', { value: Math.max(1, Math.round(last.speed / 2)) });
$('b-faster').onclick = () => last && post('speed', { value: Math.min(200, last.speed * 2) });
$('b-save').onclick = async () => { await post('save'); toast(T('saved')); };
$('b-reset').onclick = () => { if (confirm(T('resetAsk'))) { select(null); post('reset'); } };
$('b-fr').onclick = () => { lang = 'fr'; localStorage.setItem('thr-lang', lang); applyStrings(); };
$('b-en').onclick = () => { lang = 'en'; localStorage.setItem('thr-lang', lang); applyStrings(); };
$('m-close').onclick = () => select(null);
$('m-follow').onclick = () => { view.follow = !view.follow; $('m-follow').classList.toggle('on', view.follow); };
$('b-clock').onclick = () => { view.clock = !view.clock; $('b-clock').textContent = view.clock ? '❚❚' : '▶'; };
$('r-time').oninput = (ev) => { view.time = +ev.target.value; };
$('sel-season').onchange = (ev) => { view.season = ev.target.value; paintTerrain(); paintFlora(); };
$('sel-weather').onchange = (ev) => { view.weather = ev.target.value; };
$('sel-quality').onchange = (ev) => { view.quality = ev.target.value; localStorage.setItem('thr-quality', view.quality);
  buildPipeline(); buildGrass(); };
$('o-go').onclick = () => post('start', { mode: $('o-mode').value, init_pop: +$('o-pop').value,
  adaptive_traits: $('o-traits').checked, learning: $('o-learn').checked, use_ai: $('o-ai').checked });
$('o-resume').onclick = () => post('start', { resume_save: true });
addEventListener('keydown', (ev) => {
  if (ev.target.tagName === 'INPUT' || ev.target.tagName === 'SELECT') return;
  if (ev.code === 'Space') { ev.preventDefault(); $('b-pause').click(); }
  else if (ev.key >= '1' && ev.key <= '4') setTool(['look', 'food', 'predator', 'fire'][+ev.key - 1]);
  else if (ev.key === 'Escape') { select(null); $('ctx').classList.add('hidden'); }
  else if (ev.key === 'f' || ev.key === 'F') $('m-follow').click();
  else if (ev.key === 'h' || ev.key === 'H') document.querySelectorAll('.glass').forEach((e) => e.classList.toggle('uihide'));
});
document.querySelectorAll('[data-tip]').forEach((el) => {
  el.addEventListener('mouseenter', () => { const t = $('tooltip'); t.textContent = T(el.dataset.tip); t.classList.remove('hidden');
    const r = el.getBoundingClientRect(); t.style.left = Math.min(r.left, innerWidth - 270) + 'px'; t.style.top = (r.bottom + 8) + 'px'; });
  el.addEventListener('mouseleave', () => $('tooltip').classList.add('hidden'));
});

// --------------------------------------------------------------------- loop
buildFlora(); paintTerrain(); buildPipeline(); buildGrass(); applyStrings();
$('b-clock').textContent = '❚❚';
const clock = new THREE.Clock();
let frames = 0;
function frame() {
  const dt = Math.min(.1, clock.getDelta()), time = clock.elapsedTime;
  if (view.clock) { view.time = (view.time + dt / DAY_SECONDS) % 1; $('r-time').value = view.time; }
  const h = view.time * 24; $('s-clock').textContent = String(Math.floor(h)).padStart(2, '0') + ':' + String(Math.floor((h % 1) * 60)).padStart(2, '0');
  grassTime.value = time; water_time.value = time;
  applySky(dt);
  drawCreatures(dt, time); drawFood(time); drawPredators(dt, time); drawWeather(dt);
  controls.update();
  composer.render(dt);
  frames++;
  requestAnimationFrame(frame);
}
setInterval(poll, 100); poll();
requestAnimationFrame(frame);

// for automated checks: what the page believes it is showing
window.__thr = { view, creatures, get frames() { return frames; }, renderer, scene, camera, controls, get last() { return last; } };
