import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

/* =========================================================================
   VORTEX INFINI — jeu de vol à la première personne dans un tunnel d'énergie
   procédural sans fin, avec portes à franchir, orbes à collecter et
   post-traitement cinématique (bloom, aberration chromatique, vignette).
   ========================================================================= */

// ---------------------------------------------------------------------------
// Constantes de conception
// ---------------------------------------------------------------------------
const TUNNEL_RADIUS = 9;
const RING_SEGMENTS = 24;
const STEP = 3.5;
const LENGTH_SEGMENTS = 130;
const PLAYER_MAX_OFFSET = TUNNEL_RADIUS * 0.82;
const SAFE_RADIUS = TUNNEL_RADIUS * 0.85;

const clock = new THREE.Clock();
const tmpA = new THREE.Vector3();
const tmpB = new THREE.Vector3();

// ---------------------------------------------------------------------------
// Chemin procédural du vortex : fonction pure de la distance parcourue "s"
// ---------------------------------------------------------------------------
function pathPoint(s, out) {
  const x =
    7.5 * Math.sin(s * 0.045) +
    4.0 * Math.sin(s * 0.0357 + 1.3) +
    2.2 * Math.sin(s * 0.0253 + 2.1);
  const y =
    7.5 * Math.cos(s * 0.0374 + 0.4) +
    4.0 * Math.cos(s * 0.0294 + 2.7) +
    2.2 * Math.cos(s * 0.0341 + 0.6);
  out.set(x, y, -s);
  return out;
}

const _p1 = new THREE.Vector3();
const _p2 = new THREE.Vector3();
const UP = new THREE.Vector3(0, 1, 0);
const UP_ALT = new THREE.Vector3(0, 0, 1);

function frameAt(s, out) {
  pathPoint(s, out.center);
  pathPoint(s - 0.5, _p1);
  pathPoint(s + 0.5, _p2);
  out.tangent.subVectors(_p2, _p1).normalize();
  const up = Math.abs(out.tangent.dot(UP)) > 0.98 ? UP_ALT : UP;
  out.normal.copy(up).addScaledVector(out.tangent, -up.dot(out.tangent)).normalize();
  out.binormal.crossVectors(out.tangent, out.normal).normalize();
  return out;
}

function makeFrame() {
  return {
    center: new THREE.Vector3(),
    tangent: new THREE.Vector3(),
    normal: new THREE.Vector3(),
    binormal: new THREE.Vector3(),
  };
}

function worldOffset(frame, px, py, out) {
  out.copy(frame.binormal).multiplyScalar(px).addScaledVector(frame.normal, py);
  return out;
}

// ---------------------------------------------------------------------------
// Renderer / scène / caméra
// ---------------------------------------------------------------------------
const canvas = document.getElementById("scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x030014);
scene.fog = new THREE.Fog(0x030014, 40, 230);

const camera = new THREE.PerspectiveCamera(78, window.innerWidth / window.innerHeight, 0.1, 600);

// ---------------------------------------------------------------------------
// Post-traitement : bloom + aberration chromatique / vignette / grain
// ---------------------------------------------------------------------------
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));

const bloomPass = new UnrealBloomPass(new THREE.Vector2(window.innerWidth, window.innerHeight), 0.85, 0.4, 0.32);
composer.addPass(bloomPass);

const finalShader = {
  uniforms: {
    tDiffuse: { value: null },
    uTime: { value: 0 },
    uAberration: { value: 0.0011 },
    uGrain: { value: 0.018 },
    uBoost: { value: 0 },
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform float uTime;
    uniform float uAberration;
    uniform float uGrain;
    uniform float uBoost;
    varying vec2 vUv;

    float hash(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }

    void main() {
      vec2 centered = vUv - 0.5;
      float dist = length(centered);
      float amt = uAberration * (1.0 + dist * 2.2) * (1.0 + uBoost * 2.0);
      vec2 dir = normalize(centered + 1e-6);

      float r = texture2D(tDiffuse, vUv - dir * amt).r;
      float g = texture2D(tDiffuse, vUv).g;
      float b = texture2D(tDiffuse, vUv + dir * amt).b;
      vec3 color = vec3(r, g, b);

      float vig = smoothstep(0.95, 0.35, dist);
      color *= mix(0.55, 1.0, vig);

      float grain = (hash(vUv * vec2(1920.0, 1080.0) + fract(uTime) * 97.0) - 0.5) * uGrain;
      color += grain;

      gl_FragColor = vec4(color, 1.0);
    }
  `,
};
const finalPass = new ShaderPass(finalShader);
composer.addPass(finalPass);
composer.addPass(new OutputPass());

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  composer.setSize(window.innerWidth, window.innerHeight);
  bloomPass.setSize(window.innerWidth, window.innerHeight);
});

// ---------------------------------------------------------------------------
// Éclairage minimal (la scène est majoritairement émissive / auto-éclairée)
// ---------------------------------------------------------------------------
scene.add(new THREE.AmbientLight(0x33224d, 1.2));
const playerLight = new THREE.PointLight(0x66e0ff, 2.2, 40, 2);
scene.add(playerLight);

// ---------------------------------------------------------------------------
// Tunnel : lattice d'énergie généré/reconstruit autour de la caméra
// ---------------------------------------------------------------------------
const tunnelGeometry = new THREE.BufferGeometry();
const tunnelPositions = new Float32Array((LENGTH_SEGMENTS + 1) * RING_SEGMENTS * 3);
const tunnelUvs = new Float32Array((LENGTH_SEGMENTS + 1) * RING_SEGMENTS * 2);
const tunnelIndices = [];
for (let i = 0; i < LENGTH_SEGMENTS; i++) {
  for (let j = 0; j < RING_SEGMENTS; j++) {
    const a = i * RING_SEGMENTS + j;
    const b = i * RING_SEGMENTS + ((j + 1) % RING_SEGMENTS);
    const c = (i + 1) * RING_SEGMENTS + j;
    const d = (i + 1) * RING_SEGMENTS + ((j + 1) % RING_SEGMENTS);
    tunnelIndices.push(a, c, b, b, c, d);
  }
}
tunnelGeometry.setIndex(tunnelIndices);
tunnelGeometry.setAttribute("position", new THREE.BufferAttribute(tunnelPositions, 3));
tunnelGeometry.setAttribute("uv", new THREE.BufferAttribute(tunnelUvs, 2));

const tunnelMaterial = new THREE.ShaderMaterial({
  uniforms: {
    uTime: { value: 0 },
    uCameraPos: { value: new THREE.Vector3() },
    uColorA: { value: new THREE.Color(0x27e6ff) },
    uColorB: { value: new THREE.Color(0xb35bff) },
    uFogFar: { value: 210 },
  },
  transparent: true,
  depthWrite: false,
  side: THREE.DoubleSide,
  blending: THREE.AdditiveBlending,
  vertexShader: `
    uniform vec3 uCameraPos;
    varying vec2 vUv;
    varying float vDist;
    void main() {
      vUv = uv;
      vDist = length(uCameraPos - position);
      gl_Position = projectionMatrix * viewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform float uTime;
    uniform vec3 uColorA;
    uniform vec3 uColorB;
    uniform float uFogFar;
    varying vec2 vUv;
    varying float vDist;

    float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }

    void main() {
      float longFreq = 12.0;
      float lineLong = abs(fract(vUv.x * longFreq) - 0.5);
      float lineRing = abs(fract(vUv.y - uTime * 0.06) - 0.5);
      float glowLong = smoothstep(0.06, 0.0, lineLong);
      float glowRing = smoothstep(0.035, 0.0, lineRing);
      float grid = clamp(glowLong * 0.8 + glowRing * 0.8, 0.0, 1.0);

      float flicker = 0.82 + 0.18 * sin(uTime * 2.4 + vUv.y * 24.0 + hash(floor(vUv * 30.0)) * 6.28318);
      vec3 color = mix(uColorA, uColorB, sin(vUv.y * 1.4 + uTime * 0.15) * 0.5 + 0.5);
      color *= grid * flicker;

      float fog = clamp(1.0 - vDist / uFogFar, 0.0, 1.0);
      float distFade = smoothstep(0.0, 14.0, vDist);
      float alpha = grid * fog * distFade * 0.85;
      if (alpha < 0.02) discard;
      gl_FragColor = vec4(color * 1.05, alpha);
    }
  `,
});
const tunnelMesh = new THREE.Mesh(tunnelGeometry, tunnelMaterial);
tunnelMesh.frustumCulled = false;
scene.add(tunnelMesh);

function rebuildTunnel(centerS) {
  const s0 = Math.floor(centerS / STEP) * STEP - STEP * 6;
  const posAttr = tunnelGeometry.attributes.position;
  const uvAttr = tunnelGeometry.attributes.uv;
  const f = rebuildTunnel._frame || (rebuildTunnel._frame = makeFrame());
  const v = rebuildTunnel._v || (rebuildTunnel._v = new THREE.Vector3());

  for (let i = 0; i <= LENGTH_SEGMENTS; i++) {
    const s = s0 + i * STEP;
    frameAt(s, f);
    for (let j = 0; j < RING_SEGMENTS; j++) {
      const angle = (j / RING_SEGMENTS) * Math.PI * 2;
      const wobble = 1.0 + 0.05 * Math.sin(angle * 3.0 + s * 0.05);
      const r = TUNNEL_RADIUS * wobble;
      v.copy(f.center)
        .addScaledVector(f.binormal, Math.cos(angle) * r)
        .addScaledVector(f.normal, Math.sin(angle) * r);
      const idx = i * RING_SEGMENTS + j;
      posAttr.array[idx * 3] = v.x;
      posAttr.array[idx * 3 + 1] = v.y;
      posAttr.array[idx * 3 + 2] = v.z;
      uvAttr.array[idx * 2] = j / RING_SEGMENTS;
      uvAttr.array[idx * 2 + 1] = s / STEP;
    }
  }
  posAttr.needsUpdate = true;
  uvAttr.needsUpdate = true;
  tunnelGeometry.computeBoundingSphere();
}

// ---------------------------------------------------------------------------
// Champ d'étoiles (effet spatial en arrière-plan)
// ---------------------------------------------------------------------------
function buildStarfield(count, spread) {
  const positions = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    const r = spread * (0.3 + Math.random() * 0.7);
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(THREE.MathUtils.randFloatSpread(2));
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = -Math.random() * spread * 3;
    sizes[i] = Math.random() * 2 + 0.4;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  const mat = new THREE.PointsMaterial({
    color: 0xcfe9ff,
    size: 1.4,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.85,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  return points;
}
const starfield = buildStarfield(2600, 260);
scene.add(starfield);

// Traînées de vitesse (particules filantes qui accentuent le défilement)
const STREAK_COUNT = 220;
const streakGeo = new THREE.BufferGeometry();
const streakPositions = new Float32Array(STREAK_COUNT * 3);
const streakData = [];
for (let i = 0; i < STREAK_COUNT; i++) {
  streakData.push({ s: Math.random() * 400, px: THREE.MathUtils.randFloatSpread(2) * TUNNEL_RADIUS, py: THREE.MathUtils.randFloatSpread(2) * TUNNEL_RADIUS });
}
streakGeo.setAttribute("position", new THREE.BufferAttribute(streakPositions, 3));
const streakMat = new THREE.PointsMaterial({
  color: 0xaef8ff,
  size: 0.35,
  transparent: true,
  opacity: 0.9,
  depthWrite: false,
  blending: THREE.AdditiveBlending,
});
const streaks = new THREE.Points(streakGeo, streakMat);
scene.add(streaks);

function updateStreaks(cameraS) {
  const f = updateStreaks._frame || (updateStreaks._frame = makeFrame());
  const v = updateStreaks._v || (updateStreaks._v = new THREE.Vector3());
  for (let i = 0; i < STREAK_COUNT; i++) {
    const d = streakData[i];
    if (d.s < cameraS - 4) {
      d.s = cameraS + 60 + Math.random() * 80;
      const r = (0.3 + Math.random() * 0.7) * TUNNEL_RADIUS;
      const a = Math.random() * Math.PI * 2;
      d.px = Math.cos(a) * r;
      d.py = Math.sin(a) * r;
    }
    frameAt(d.s, f);
    worldOffset(f, d.px, d.py, v).add(f.center);
    streakPositions[i * 3] = v.x;
    streakPositions[i * 3 + 1] = v.y;
    streakPositions[i * 3 + 2] = v.z;
  }
  streakGeo.attributes.position.needsUpdate = true;
}

// ---------------------------------------------------------------------------
// Portes (défis) et orbes (collectibles)
// ---------------------------------------------------------------------------
class GateManager {
  constructor() {
    this.gates = [];
    this.nextS = 30;
    this.pool = [];
  }

  _makeMesh() {
    const group = new THREE.Group();
    const torus = new THREE.Mesh(
      new THREE.TorusGeometry(TUNNEL_RADIUS * 0.92, 0.32, 10, 56, Math.PI * 2),
      new THREE.MeshBasicMaterial({ color: 0xff6b3d, transparent: true, opacity: 0.95 })
    );
    group.add(torus);
    group.matrixAutoUpdate = false;
    group.userData.torus = torus;
    scene.add(group);
    return group;
  }

  spawnUpTo(targetS, difficulty) {
    while (this.nextS < targetS) {
      const spacing = THREE.MathUtils.lerp(46, 30, Math.min(difficulty, 1));
      const gapWidth = THREE.MathUtils.lerp(2.05, 1.15, Math.min(difficulty, 1));
      const gapAngle = Math.random() * Math.PI * 2;
      const mesh = this.pool.pop() || this._makeMesh();
      mesh.visible = true;
      mesh.userData.torus.geometry.dispose();
      mesh.userData.torus.geometry = new THREE.TorusGeometry(TUNNEL_RADIUS * 0.92, 0.32, 10, 56, Math.PI * 2 - gapWidth);
      mesh.userData.torus.rotation.z = gapAngle + gapWidth / 2;
      mesh.userData.torus.material.color.setHex(0xff6b3d);

      const f = makeFrame();
      frameAt(this.nextS, f);
      mesh.matrix.makeBasis(f.binormal, f.normal, f.tangent);
      mesh.matrix.setPosition(f.center);

      this.gates.push({ s: this.nextS, gapAngle, gapWidth, mesh, resolved: false });
      this.nextS += spacing;
    }
  }

  update(cameraS, onResult) {
    for (let i = this.gates.length - 1; i >= 0; i--) {
      const g = this.gates[i];
      if (!g.resolved && cameraS >= g.s) {
        g.resolved = true;
        onResult(g);
      }
      if (cameraS - g.s > 25) {
        g.mesh.visible = false;
        this.pool.push(g.mesh);
        this.gates.splice(i, 1);
      }
    }
  }

  reset() {
    for (const g of this.gates) {
      g.mesh.visible = false;
      this.pool.push(g.mesh);
    }
    this.gates.length = 0;
    this.nextS = 30;
  }
}

class OrbManager {
  constructor() {
    this.orbs = [];
    this.nextS = 15;
    this.pool = [];
    this.geometry = new THREE.IcosahedronGeometry(0.55, 1);
  }

  _makeMesh() {
    const mat = new THREE.MeshBasicMaterial({ color: 0xffd76a, transparent: true, opacity: 0.95 });
    const mesh = new THREE.Mesh(this.geometry, mat);
    scene.add(mesh);
    return mesh;
  }

  spawnUpTo(targetS) {
    while (this.nextS < targetS) {
      if (Math.random() < 0.75) {
        const mesh = this.pool.pop() || this._makeMesh();
        mesh.visible = true;
        const px = THREE.MathUtils.randFloatSpread(2) * TUNNEL_RADIUS * 0.55;
        const py = THREE.MathUtils.randFloatSpread(2) * TUNNEL_RADIUS * 0.55;
        this.orbs.push({ s: this.nextS, px, py, mesh, collected: false });
      }
      this.nextS += 9 + Math.random() * 6;
    }
  }

  update(cameraS, dt, playerPx, playerPy, onCollect) {
    const f = this.update._frame || (this.update._frame = makeFrame());
    const v = this.update._v || (this.update._v = new THREE.Vector3());
    for (let i = this.orbs.length - 1; i >= 0; i--) {
      const o = this.orbs[i];
      frameAt(o.s, f);
      worldOffset(f, o.px, o.py, v).add(f.center);
      o.mesh.position.copy(v);
      o.mesh.rotation.y += dt * 1.6;
      o.mesh.rotation.x += dt * 0.9;

      if (!o.collected && Math.abs(o.s - cameraS) < 2.2) {
        const dx = o.px - playerPx;
        const dy = o.py - playerPy;
        if (Math.sqrt(dx * dx + dy * dy) < 2.1) {
          o.collected = true;
          onCollect(o);
        }
      }

      if (cameraS - o.s > 10) {
        o.mesh.visible = false;
        this.pool.push(o.mesh);
        this.orbs.splice(i, 1);
      }
    }
  }

  reset() {
    for (const o of this.orbs) {
      o.mesh.visible = false;
      this.pool.push(o.mesh);
    }
    this.orbs.length = 0;
    this.nextS = 15;
  }
}

const gateManager = new GateManager();
const orbManager = new OrbManager();

// ---------------------------------------------------------------------------
// Entrées : souris + clavier (ZQSD / flèches), lissées avec inertie
// ---------------------------------------------------------------------------
const input = { mouseX: 0, mouseY: 0, key: { up: 0, down: 0, left: 0, right: 0, boost: false } };

window.addEventListener("mousemove", (e) => {
  input.mouseX = (e.clientX / window.innerWidth) * 2 - 1;
  input.mouseY = -((e.clientY / window.innerHeight) * 2 - 1);
});
window.addEventListener("touchmove", (e) => {
  if (!e.touches[0]) return;
  input.mouseX = (e.touches[0].clientX / window.innerWidth) * 2 - 1;
  input.mouseY = -((e.touches[0].clientY / window.innerHeight) * 2 - 1);
}, { passive: true });

const KEY_MAP = {
  ArrowUp: "up", KeyW: "up", KeyZ: "up",
  ArrowDown: "down", KeyS: "down",
  ArrowLeft: "left", KeyA: "left", KeyQ: "left",
  ArrowRight: "right", KeyD: "right",
  ShiftLeft: "boost", ShiftRight: "boost",
};
window.addEventListener("keydown", (e) => {
  const k = KEY_MAP[e.code];
  if (k === "boost") input.key.boost = true;
  else if (k) input.key[k] = 1;
  if (e.code === "Escape") togglePause();
});
window.addEventListener("keyup", (e) => {
  const k = KEY_MAP[e.code];
  if (k === "boost") input.key.boost = false;
  else if (k) input.key[k] = 0;
});

// ---------------------------------------------------------------------------
// Audio synthétisé (aucun fichier externe requis)
// ---------------------------------------------------------------------------
class AudioEngine {
  constructor() {
    this.ctx = null;
    this.hum = null;
  }
  ensure() {
    if (this.ctx) return;
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = this.ctx.createOscillator();
    osc.type = "sawtooth";
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 220;
    const gain = this.ctx.createGain();
    gain.gain.value = 0.045;
    osc.connect(filter).connect(gain).connect(this.ctx.destination);
    osc.start();
    this.hum = { osc, filter, gain };
  }
  setSpeed(speedRatio) {
    if (!this.hum) return;
    this.hum.osc.frequency.setTargetAtTime(50 + speedRatio * 90, this.ctx.currentTime, 0.15);
    this.hum.filter.frequency.setTargetAtTime(160 + speedRatio * 500, this.ctx.currentTime, 0.15);
  }
  blip(freq, dur, type = "sine", vol = 0.09) {
    if (!this.ctx) return;
    const t0 = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    osc.frequency.exponentialRampToValueAtTime(Math.max(30, freq * 0.6), t0 + dur);
    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(vol, t0);
    gain.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    osc.connect(gain).connect(this.ctx.destination);
    osc.start(t0);
    osc.stop(t0 + dur);
  }
  gate() { this.blip(660, 0.18, "triangle", 0.08); }
  orb() { this.blip(1100, 0.12, "sine", 0.07); }
  hit() { this.blip(120, 0.35, "sawtooth", 0.16); }
}
const audio = new AudioEngine();

// ---------------------------------------------------------------------------
// État du jeu
// ---------------------------------------------------------------------------
const HUD = {
  root: document.getElementById("hud"),
  score: document.getElementById("hud-score"),
  combo: document.getElementById("hud-combo"),
  speed: document.getElementById("hud-speed"),
  distance: document.getElementById("hud-distance"),
  level: document.getElementById("hud-level"),
  shieldBar: document.getElementById("shield-bar"),
  boostFill: document.getElementById("boost-fill"),
  warning: document.getElementById("warning"),
};
const startScreen = document.getElementById("start-screen");
const pauseScreen = document.getElementById("pause-screen");
const gameoverScreen = document.getElementById("gameover-screen");
const hitFlash = document.getElementById("hit-flash");
const loading = document.getElementById("loading");
const bestScoreEl = document.getElementById("best-score");

const BEST_KEY = "vortex-infini-best-score";
bestScoreEl.textContent = Math.floor(Number(localStorage.getItem(BEST_KEY) || 0));

let state = "menu"; // menu | playing | paused | gameover

const player = {
  px: 0, py: 0,          // position réelle dans le tunnel
  targetPx: 0, targetPy: 0,
  s: 0,                  // distance parcourue le long du vortex
  speed: 24,
  boost: 1,
  boostEnergy: 1,
  shields: 3,
  invuln: 0,
  score: 0,
  combo: 0,
  gatesPassed: 0,
  elapsed: 0,
};

function resetGame() {
  player.px = 0; player.py = 0;
  player.targetPx = 0; player.targetPy = 0;
  player.s = 0;
  player.speed = 24;
  player.boost = 1;
  player.boostEnergy = 1;
  player.shields = 3;
  player.invuln = 2;
  player.score = 0;
  player.combo = 0;
  player.gatesPassed = 0;
  player.elapsed = 0;
  gateManager.reset();
  orbManager.reset();
  gateManager.spawnUpTo(200, 0);
  orbManager.spawnUpTo(200);
  updateShieldHUD();
}

function updateShieldHUD() {
  const cells = HUD.shieldBar.children;
  for (let i = 0; i < cells.length; i++) {
    cells[i].classList.toggle("lost", i >= player.shields);
  }
}

function damagePlayer() {
  if (player.invuln > 0) return;
  player.shields -= 1;
  player.combo = 0;
  player.invuln = 1.6;
  audio.hit();
  hitFlash.classList.add("active");
  setTimeout(() => hitFlash.classList.remove("active"), 140);
  updateShieldHUD();
  if (player.shields <= 0) endGame();
}

function endGame() {
  state = "gameover";
  document.getElementById("final-score").textContent = Math.floor(player.score);
  document.getElementById("final-distance").textContent = Math.floor(player.s);
  document.getElementById("final-gates").textContent = player.gatesPassed;
  const best = Number(localStorage.getItem(BEST_KEY) || 0);
  if (player.score > best) localStorage.setItem(BEST_KEY, String(Math.floor(player.score)));
  bestScoreEl.textContent = Math.floor(Number(localStorage.getItem(BEST_KEY) || 0));
  gameoverScreen.classList.remove("hidden");
  document.exitPointerLock?.();
}

function togglePause() {
  if (state === "playing") {
    state = "paused";
    pauseScreen.classList.remove("hidden");
  } else if (state === "paused") {
    state = "playing";
    pauseScreen.classList.add("hidden");
  }
}

function startGame() {
  resetGame();
  state = "playing";
  audio.ensure();
  startScreen.classList.add("hidden");
  gameoverScreen.classList.add("hidden");
  pauseScreen.classList.add("hidden");
  HUD.root.classList.remove("hidden");
}

document.getElementById("btn-play").addEventListener("click", startGame);
document.getElementById("btn-restart").addEventListener("click", startGame);
document.getElementById("btn-resume").addEventListener("click", togglePause);

// ---------------------------------------------------------------------------
// Boucle de simulation
// ---------------------------------------------------------------------------
function angleDiff(a, b) {
  let d = a - b;
  while (d > Math.PI) d -= Math.PI * 2;
  while (d < -Math.PI) d += Math.PI * 2;
  return d;
}

function updatePlayer(dt) {
  const kx = input.key.right - input.key.left;
  const ky = input.key.up - input.key.down;
  player.targetPx = THREE.MathUtils.clamp(
    input.mouseX * PLAYER_MAX_OFFSET + kx * PLAYER_MAX_OFFSET * 0.7,
    -PLAYER_MAX_OFFSET, PLAYER_MAX_OFFSET
  );
  player.targetPy = THREE.MathUtils.clamp(
    input.mouseY * PLAYER_MAX_OFFSET + ky * PLAYER_MAX_OFFSET * 0.7,
    -PLAYER_MAX_OFFSET, PLAYER_MAX_OFFSET
  );
  const smoothing = 1 - Math.pow(0.001, dt);
  player.px += (player.targetPx - player.px) * smoothing;
  player.py += (player.targetPy - player.py) * smoothing;

  const wantBoost = input.key.boost && player.boostEnergy > 0.05;
  const targetBoost = wantBoost ? 2.05 : 1;
  player.boost += (targetBoost - player.boost) * (1 - Math.pow(0.0005, dt));
  if (wantBoost) player.boostEnergy = Math.max(0, player.boostEnergy - dt * 0.35);
  else player.boostEnergy = Math.min(1, player.boostEnergy + dt * 0.18);

  player.elapsed += dt;
  const difficulty = Math.min(player.elapsed / 90, 1);
  const baseSpeed = 22 + difficulty * 26;
  player.speed += (baseSpeed - player.speed) * dt * 0.5;

  const effectiveSpeed = player.speed * player.boost;
  player.s += effectiveSpeed * dt;
  if (player.invuln > 0) player.invuln = Math.max(0, player.invuln - dt);

  return { difficulty, effectiveSpeed };
}

const frame = makeFrame();
const camOffset = new THREE.Vector3();
const lookTarget = new THREE.Vector3();

function updateCamera() {
  frameAt(player.s, frame);
  worldOffset(frame, player.px, player.py, camOffset);
  camera.position.copy(frame.center).add(camOffset);

  frameAt(player.s + 6, frame.lookFrame || (frame.lookFrame = makeFrame()));
  const lf = frame.lookFrame;
  const leanPx = player.px * 0.65;
  const leanPy = player.py * 0.65;
  worldOffset(lf, leanPx, leanPy, lookTarget).add(lf.center);

  camera.up.copy(frame.normal);
  camera.lookAt(lookTarget);
  camera.rotation.z += (player.targetPx - player.px) * -0.012;

  camera.fov = THREE.MathUtils.lerp(camera.fov, 78 + (player.boost - 1) * 22, 0.08);
  camera.updateProjectionMatrix();

  playerLight.position.copy(camera.position);

  tunnelMaterial.uniforms.uCameraPos.value.copy(camera.position);
}

let warningTimer = 0;

function evaluateGate(g) {
  const playerAngle = Math.atan2(player.py, player.px);
  const playerR = Math.hypot(player.px, player.py);
  const diff = Math.abs(angleDiff(playerAngle, g.gapAngle));
  const throughGap = diff < g.gapWidth / 2 && playerR < SAFE_RADIUS;
  if (throughGap) {
    player.gatesPassed += 1;
    player.combo += 1;
    const gain = 15 * (1 + Math.min(player.combo, 10) * 0.15);
    player.score += gain;
    audio.gate();
    HUD.combo.textContent = player.combo > 1 ? `COMBO x${player.combo}` : "";
  } else {
    damagePlayer();
    HUD.combo.textContent = "";
  }
}

function updateHUD() {
  HUD.score.textContent = Math.floor(player.score);
  HUD.speed.textContent = Math.floor(player.speed * player.boost);
  HUD.distance.textContent = Math.floor(player.s);
  HUD.level.textContent = 1 + Math.floor(player.elapsed / 30);
  HUD.boostFill.style.width = `${Math.round(player.boostEnergy * 100)}%`;

  const nearGate = gateManager.gates.find((g) => !g.resolved && g.s - player.s < 14 && g.s - player.s > 0);
  if (nearGate) {
    const playerAngle = Math.atan2(player.py, player.px);
    const diff = Math.abs(angleDiff(playerAngle, nearGate.gapAngle));
    const aligned = diff < nearGate.gapWidth / 2;
    warningTimer = aligned ? 0 : Math.min(1, warningTimer + 0.1);
  } else {
    warningTimer = Math.max(0, warningTimer - 0.1);
  }
  HUD.warning.classList.toggle("hidden", warningTimer < 0.4);
}

// ---------------------------------------------------------------------------
// Boucle d'animation
// ---------------------------------------------------------------------------
function animate() {
  requestAnimationFrame(animate);
  const dt = Math.min(clock.getDelta(), 0.05);
  const t = clock.elapsedTime;

  tunnelMaterial.uniforms.uTime.value = t;
  finalPass.uniforms.uTime.value = t;

  if (state === "playing") {
    const { difficulty } = updatePlayer(dt);
    gateManager.spawnUpTo(player.s + 220, difficulty);
    orbManager.spawnUpTo(player.s + 220);
    gateManager.update(player.s, evaluateGate);
    orbManager.update(player.s, dt, player.px, player.py, () => {
      player.score += 8;
      audio.orb();
    });
    rebuildTunnel(player.s);
    updateCamera();
    updateStreaks(player.s);
    audio.setSpeed((player.speed * player.boost - 20) / 60);
    finalPass.uniforms.uBoost.value = player.boost - 1;
    updateHUD();
  } else if (state === "menu") {
    // Caméra flottante lente dans le menu pour montrer l'effet.
    player.s += dt * 6;
    rebuildTunnel(player.s);
    frameAt(player.s, frame);
    camera.position.copy(frame.center);
    frameAt(player.s + 6, frame);
    camera.up.copy(frame.normal);
    camera.lookAt(frame.center);
    updateStreaks(player.s);
  }

  starfield.rotation.z += dt * 0.002;
  composer.render();
}

// Initialisation
resetGame();
rebuildTunnel(0);
loading.classList.add("hidden");
animate();
