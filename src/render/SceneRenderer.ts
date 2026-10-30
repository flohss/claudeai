import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CSS2DObject, CSS2DRenderer } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import { habitableZone, snowLine } from '../physics/stars';
import type { Body, PlanetType } from '../physics/types';
import { SUN_RADIUS_KM } from '../physics/units';
import type { Vec3 } from '../physics/vec3';
import { makeGlowTexture, makePlanetTexture } from './textures';

/** Unités de scène par UA. */
export const AU_SCALE = 10;
/** Exagération des distances lune-planète, sans quoi les lunes seraient dans leur planète. */
const MOON_DISTANCE_EXAGGERATION = 30;
const TRAIL_POINTS = 600;

export interface ViewOptions {
  showTrails: boolean;
  showLabels: boolean;
  showZones: boolean;
  followSelected: boolean;
}

/** Les tailles réelles sont invisibles à l'échelle d'un système : on utilise une échelle logarithmique. */
export function visualRadius(body: Body): number {
  if (body.kind === 'star') return 0.7 + 0.5 * Math.log10(1 + (body.radiusKm / SUN_RADIUS_KM) * 2);
  const r = 0.08 + 0.2 * Math.log10(1 + body.radiusKm / 1000);
  return body.kind === 'moon' ? r * 0.8 : r;
}

/** Physique : plan de l'écliptique = (x, y), z vers le haut. Three.js : y vers le haut. */
const toScene = (p: Vec3, out: THREE.Vector3) => out.set(p.x * AU_SCALE, p.z * AU_SCALE, -p.y * AU_SCALE);

interface Entry {
  body: Body;
  group: THREE.Group;
  mesh: THREE.Mesh;
  label: CSS2DObject;
  labelEl: HTMLDivElement;
  appearanceKey: string;
  trail?: { line: THREE.Line; positions: Float32Array; count: number };
  glow?: THREE.Sprite;
  light?: THREE.PointLight;
}

export class SceneRenderer {
  readonly camera: THREE.PerspectiveCamera;
  private readonly renderer: THREE.WebGLRenderer;
  private readonly labelRenderer: CSS2DRenderer;
  private readonly scene = new THREE.Scene();
  private readonly controls: OrbitControls;
  private readonly entries = new Map<string, Entry>();
  private readonly selectionRing: THREE.Mesh;
  private readonly habitableRing: THREE.Mesh;
  private readonly snowRing: THREE.LineLoop;
  private readonly tmp = new THREE.Vector3();
  private readonly lastFollow = new THREE.Vector3();
  private followId: string | null = null;
  private zonesKey = '';
  private readonly resizeObserver: ResizeObserver;

  constructor(private readonly container: HTMLElement, private readonly onPick: (id: string | null) => void) {
    const { clientWidth: w, clientHeight: h } = container;
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(w, h);
    container.appendChild(this.renderer.domElement);

    this.labelRenderer = new CSS2DRenderer();
    this.labelRenderer.setSize(w, h);
    this.labelRenderer.domElement.className = 'label-layer';
    container.appendChild(this.labelRenderer.domElement);

    this.camera = new THREE.PerspectiveCamera(50, w / h, 0.01, 1e6);
    this.camera.position.set(0, 140, 220);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.1;
    this.controls.minDistance = 0.3;
    this.controls.maxDistance = 20000;

    this.scene.background = new THREE.Color('#03040a');
    this.scene.add(new THREE.AmbientLight(0xffffff, 0.22));
    this.scene.add(this.makeStarfield());

    this.selectionRing = new THREE.Mesh(
      new THREE.RingGeometry(1.25, 1.4, 48),
      new THREE.MeshBasicMaterial({ color: '#7cc4ff', transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthTest: false }),
    );
    this.selectionRing.renderOrder = 10;
    this.selectionRing.visible = false;
    this.scene.add(this.selectionRing);

    this.habitableRing = new THREE.Mesh(
      new THREE.RingGeometry(1, 2, 128),
      new THREE.MeshBasicMaterial({ color: '#3fbf6a', transparent: true, opacity: 0.12, side: THREE.DoubleSide, depthWrite: false }),
    );
    this.habitableRing.rotation.x = -Math.PI / 2;
    this.scene.add(this.habitableRing);

    const snowGeom = new THREE.BufferGeometry().setFromPoints(
      Array.from({ length: 256 }, (_, k) => new THREE.Vector3(Math.cos((k / 256) * Math.PI * 2), 0, Math.sin((k / 256) * Math.PI * 2))),
    );
    this.snowRing = new THREE.LineLoop(snowGeom, new THREE.LineDashedMaterial({ color: '#8fd8ff', dashSize: 0.04, gapSize: 0.04, transparent: true, opacity: 0.45 }));
    this.snowRing.computeLineDistances();
    this.scene.add(this.snowRing);

    this.renderer.domElement.addEventListener('pointerdown', this.onPointerDown);
    this.renderer.domElement.addEventListener('pointerup', this.onPointerUp);
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);
  }

  private makeStarfield(): THREE.Points {
    const n = 4000;
    const positions = new Float32Array(n * 3);
    const colors = new Float32Array(n * 3);
    for (let k = 0; k < n; k++) {
      const u = Math.random() * 2 - 1;
      const t = Math.random() * Math.PI * 2;
      const s = Math.sqrt(1 - u * u);
      const r = 50000;
      positions.set([r * s * Math.cos(t), r * u, r * s * Math.sin(t)], k * 3);
      const c = 0.5 + Math.random() * 0.5;
      colors.set([c, c, c * (0.85 + Math.random() * 0.3)], k * 3);
    }
    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    return new THREE.Points(geom, new THREE.PointsMaterial({ size: 1.5, sizeAttenuation: false, vertexColors: true }));
  }

  private resize(): void {
    const { clientWidth: w, clientHeight: h } = this.container;
    if (w === 0 || h === 0) return;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.labelRenderer.setSize(w, h);
  }

  // Sélection : un clic sans glisser choisit le corps le plus proche à l'écran.
  private downAt: { x: number; y: number } | null = null;
  private onPointerDown = (e: PointerEvent) => {
    this.downAt = { x: e.clientX, y: e.clientY };
  };
  private onPointerUp = (e: PointerEvent) => {
    if (!this.downAt || Math.hypot(e.clientX - this.downAt.x, e.clientY - this.downAt.y) > 5) return;
    this.downAt = null;
    const rect = this.renderer.domElement.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    let best: string | null = null;
    let bestDist = Infinity;
    for (const [id, entry] of this.entries) {
      entry.group.getWorldPosition(this.tmp);
      const depth = this.tmp.distanceTo(this.camera.position);
      this.tmp.project(this.camera);
      if (this.tmp.z > 1) continue;
      const sx = ((this.tmp.x + 1) / 2) * rect.width;
      const sy = ((1 - this.tmp.y) / 2) * rect.height;
      const pixelRadius = (visualRadius(entry.body) / depth) * (rect.height / (2 * Math.tan((this.camera.fov * Math.PI) / 360)));
      const d = Math.hypot(sx - mx, sy - my);
      if (d < Math.max(14, pixelRadius + 6) && d < bestDist) {
        best = id;
        bestDist = d;
      }
    }
    this.onPick(best);
  };

  private createEntry(body: Body): Entry {
    const group = new THREE.Group();
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 32));
    group.add(mesh);

    const labelEl = document.createElement('div');
    labelEl.className = `body-label body-label--${body.kind}`;
    labelEl.addEventListener('click', () => this.onPick(body.id));
    const label = new CSS2DObject(labelEl);
    group.add(label);

    const entry: Entry = { body, group, mesh, label, labelEl, appearanceKey: '' };
    if (body.kind !== 'moon') {
      const positions = new Float32Array(TRAIL_POINTS * 3);
      const geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geom.setDrawRange(0, 0);
      const line = new THREE.Line(geom, new THREE.LineBasicMaterial({ transparent: true, opacity: 0.45 }));
      line.frustumCulled = false;
      this.scene.add(line);
      entry.trail = { line, positions, count: 0 };
    }
    this.scene.add(group);
    return entry;
  }

  private updateAppearance(entry: Entry): void {
    const b = entry.body;
    const key = [b.kind, b.planetType, b.color, b.radiusKm.toFixed(0), b.name].join('|');
    if (key === entry.appearanceKey) return;
    entry.appearanceKey = key;

    const r = visualRadius(b);
    entry.mesh.scale.setScalar(r);
    entry.label.position.set(0, r * 1.3, 0);
    entry.labelEl.textContent = b.name;

    (entry.mesh.material as THREE.Material).dispose();
    if (b.kind === 'star') {
      entry.mesh.material = new THREE.MeshBasicMaterial({ color: b.color });
      if (!entry.glow) {
        entry.glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: makeGlowTexture(), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
        entry.group.add(entry.glow);
        entry.light = new THREE.PointLight(0xffffff, 2.2, 0, 0);
        entry.group.add(entry.light);
      }
      entry.glow.material.color.set(b.color);
      entry.glow.scale.setScalar(r * 7);
      entry.light!.color.set(b.color);
    } else {
      const texture = makePlanetTexture(b.planetType as PlanetType, b.color, b.id);
      entry.mesh.material = new THREE.MeshStandardMaterial({ map: texture, roughness: 0.9, metalness: 0 });
    }
    if (entry.trail) (entry.trail.line.material as THREE.LineBasicMaterial).color.set(b.color);
  }

  private disposeEntry(entry: Entry): void {
    this.scene.remove(entry.group);
    entry.labelEl.remove();
    entry.mesh.geometry.dispose();
    const mat = entry.mesh.material as THREE.MeshStandardMaterial;
    mat.map?.dispose();
    mat.dispose();
    if (entry.trail) {
      this.scene.remove(entry.trail.line);
      entry.trail.line.geometry.dispose();
    }
  }

  clearTrails(): void {
    for (const entry of this.entries.values()) {
      if (entry.trail) {
        entry.trail.count = 0;
        entry.trail.line.geometry.setDrawRange(0, 0);
      }
    }
  }

  private pushTrail(entry: Entry, pos: THREE.Vector3, step: number): void {
    const trail = entry.trail!;
    const p = trail.positions;
    if (trail.count > 0) {
      const last = (trail.count - 1) * 3;
      const dx = pos.x - p[last];
      const dy = pos.y - p[last + 1];
      const dz = pos.z - p[last + 2];
      if (dx * dx + dy * dy + dz * dz < step * step) return;
    }
    if (trail.count === TRAIL_POINTS) {
      p.copyWithin(0, 3);
      trail.count -= 1;
    }
    p.set([pos.x, pos.y, pos.z], trail.count * 3);
    trail.count += 1;
    const geom = trail.line.geometry;
    geom.setDrawRange(0, trail.count);
    (geom.getAttribute('position') as THREE.BufferAttribute).needsUpdate = true;
  }

  /** Synchronise la scène avec l'état de la simulation. Appelé à chaque image. */
  update(bodies: Body[], selectedId: string | null, options: ViewOptions): void {
    const alive = new Set<string>();
    for (const body of bodies) {
      alive.add(body.id);
      let entry = this.entries.get(body.id);
      if (!entry) {
        entry = this.createEntry(body);
        this.entries.set(body.id, entry);
      }
      entry.body = body;
      this.updateAppearance(entry);
    }
    for (const [id, entry] of this.entries) {
      if (!alive.has(id)) {
        this.disposeEntry(entry);
        this.entries.delete(id);
      }
    }

    // Positions : les parents d'abord (les corps sont triés par hiérarchie).
    const byId = new Map(bodies.map((b) => [b.id, b]));
    const star = bodies.find((b) => b.kind === 'star');
    for (const body of bodies) {
      const entry = this.entries.get(body.id)!;
      const parent = byId.get(body.parentId ?? '');
      if (parent && parent.kind !== 'star') {
        // Lune : distance au parent exagérée pour rester visible.
        const parentEntry = this.entries.get(parent.id)!;
        const rel = new THREE.Vector3();
        toScene({ x: body.position.x - parent.position.x, y: body.position.y - parent.position.y, z: body.position.z - parent.position.z }, rel);
        const d = rel.length();
        if (d > 0) rel.multiplyScalar((visualRadius(parent) + d * MOON_DISTANCE_EXAGGERATION) / d);
        entry.group.position.copy(parentEntry.group.position).add(rel);
      } else {
        toScene(body.position, entry.group.position);
      }

      // Les noms des lunes n'apparaissent que de près, sinon ils recouvrent ceux des planètes.
      const related = body.id === selectedId || body.parentId === selectedId || byId.get(selectedId ?? '')?.parentId === body.parentId;
      entry.label.visible =
        options.showLabels && (body.kind !== 'moon' || related || entry.group.position.distanceTo(this.camera.position) < 25);
      entry.labelEl.classList.toggle('is-selected', body.id === selectedId);
      if (entry.trail) {
        entry.trail.line.visible = options.showTrails;
        if (star && body !== star) {
          const r = entry.group.position.distanceTo(this.entries.get(star.id)!.group.position);
          this.pushTrail(entry, entry.group.position, (2 * Math.PI * r) / 400);
        }
      }
    }

    // Zones de l'étoile (zone habitable et ligne des glaces).
    if (star?.star) {
      const starPos = this.entries.get(star.id)!.group.position;
      const L = star.star.luminosity;
      const zKey = L.toPrecision(6);
      if (zKey !== this.zonesKey) {
        this.zonesKey = zKey;
        const hz = habitableZone(L);
        this.habitableRing.geometry.dispose();
        this.habitableRing.geometry = new THREE.RingGeometry(hz.inner * AU_SCALE, hz.outer * AU_SCALE, 160);
        const s = snowLine(L) * AU_SCALE;
        this.snowRing.scale.setScalar(s);
      }
      this.habitableRing.position.copy(starPos);
      this.snowRing.position.copy(starPos);
    }
    this.habitableRing.visible = options.showZones && !!star;
    this.snowRing.visible = options.showZones && !!star;

    // Sélection et suivi caméra.
    const selected = selectedId ? this.entries.get(selectedId) : undefined;
    if (selected) {
      const r = visualRadius(selected.body);
      this.selectionRing.visible = true;
      this.selectionRing.position.copy(selected.group.position);
      this.selectionRing.scale.setScalar(r);
      this.selectionRing.quaternion.copy(this.camera.quaternion);
    } else {
      this.selectionRing.visible = false;
    }

    if (options.followSelected && selected) {
      const pos = selected.group.position;
      if (this.followId !== selected.body.id) {
        // Nouvelle cible : on se rapproche en douceur.
        this.followId = selected.body.id;
        const offset = this.camera.position.clone().sub(this.controls.target);
        const wanted = Math.max(visualRadius(selected.body) * 12, 3);
        if (offset.length() > wanted * 4) offset.setLength(wanted);
        this.controls.target.copy(pos);
        this.camera.position.copy(pos).add(offset);
      } else {
        const delta = pos.clone().sub(this.lastFollow);
        this.controls.target.add(delta);
        this.camera.position.add(delta);
      }
      this.lastFollow.copy(pos);
    } else {
      this.followId = null;
    }
  }

  /**
   * Recentre la caméra sur le système. On cadre sur la distance médiane des
   * planètes : cadrer sur la plus lointaine rendrait les planètes intérieures invisibles.
   */
  frameSystem(bodies: Body[]): void {
    const star = bodies.find((b) => b.kind === 'star');
    const distances = bodies
      .filter((b) => b.kind === 'planet' && star)
      .map((b) => Math.hypot(b.position.x - star!.position.x, b.position.y - star!.position.y, b.position.z - star!.position.z) * AU_SCALE)
      .sort((x, y) => x - y);
    const median = distances.length ? distances[Math.floor((distances.length - 1) / 2)] : 10;
    const r = Math.max(median * 1.5, 8);
    this.controls.target.set(0, 0, 0);
    this.camera.position.set(0, r * 0.9, r * 1.4);
    this.followId = null;
  }

  render(): void {
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    this.labelRenderer.render(this.scene, this.camera);
  }

  dispose(): void {
    this.resizeObserver.disconnect();
    this.renderer.domElement.removeEventListener('pointerdown', this.onPointerDown);
    this.renderer.domElement.removeEventListener('pointerup', this.onPointerUp);
    for (const entry of this.entries.values()) this.disposeEntry(entry);
    this.entries.clear();
    this.controls.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
    this.labelRenderer.domElement.remove();
  }
}
