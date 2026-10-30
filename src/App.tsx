import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import { hillRadius } from './physics/orbits';
import { habitableZone } from './physics/stars';
import { AU_KM } from './physics/units';
import { distance } from './physics/vec3';
import type { SceneRenderer, ViewOptions } from './render/SceneRenderer';
import { protoplanetaryDisk, type DiskParams } from './sim/disk';
import { estimateRadiusKm, makeOrbiter } from './sim/factory';
import { emptySystem, solarSystem, tightBinary, wideBinary } from './sim/presets';
import { randomSystem } from './sim/random';
import { deserialize, serialize } from './sim/serialization';
import { decodeSystem, encodeSystem, sharedFromHash, shareUrl } from './sim/share';
import { createSimulation } from './sim/client';
import type { Simulation, SystemDefinition } from './sim/Simulation';
import { Telemetry } from './sim/telemetry';
import { BodyList } from './ui/BodyList';
import { BodyPanel } from './ui/BodyPanel';
import { ChartsPanel } from './ui/ChartsPanel';
import { DiskDialog } from './ui/DiskDialog';
import { EventLog } from './ui/EventLog';
import { ShareDialog } from './ui/ShareDialog';
import { SceneView } from './ui/SceneView';
import { StarsPanel } from './ui/StarsPanel';
import { TimeBar } from './ui/TimeBar';
import { TopBar, type PresetId } from './ui/TopBar';

/** Force un nouveau rendu à intervalle régulier pour les valeurs qui évoluent en continu. */
function useTick(ms: number) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), ms);
    return () => clearInterval(id);
  }, [ms]);
}

const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'];

// Une seule simulation (et un seul Worker) pour toute l'application, même si
// React appelle deux fois les initialisations en mode strict.
let appSimulation: Simulation | null = null;
const getSimulation = () => (appSimulation ??= createSimulation(solarSystem()));

export function App() {
  const sim = getSimulation();
  const telemetry = useMemo(() => new Telemetry(), []);
  useSyncExternalStore(sim.subscribe, sim.getVersion);
  useTick(250);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [renderer, setRenderer] = useState<SceneRenderer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [diskDialog, setDiskDialog] = useState(false);
  const [showCharts, setShowCharts] = useState(false);
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [options, setOptions] = useState<ViewOptions>({ showTrails: true, showLabels: true, showZones: true, followSelected: false });

  const selected = sim.getBody(selectedId);
  const star = sim.star;

  // L'historique des graphiques est enregistré en continu, même graphiques fermés.
  useEffect(() => {
    const id = setInterval(() => telemetry.record(sim), 250);
    return () => clearInterval(id);
  }, [sim, telemetry]);

  const loadSystem = useCallback(
    (def: SystemDefinition, placeFromElements = true) => {
      sim.load(def, placeFromElements);
      setSelectedId(null);
      setError(null);
      renderer?.clearTrails();
      renderer?.frameSystem(sim.bodies);
    },
    [sim, renderer],
  );

  // Un système reçu par lien (#systeme=…) est chargé à l'ouverture, ou quand le lien change.
  const openedHash = useRef<string | null>(null);
  useEffect(() => {
    if (!renderer) return;
    const openShared = async () => {
      const encoded = sharedFromHash(window.location.hash);
      if (!encoded || encoded === openedHash.current) return;
      openedHash.current = encoded;
      try {
        loadSystem(await decodeSystem(encoded), false);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    };
    void openShared();
    window.addEventListener('hashchange', openShared);
    return () => window.removeEventListener('hashchange', openShared);
  }, [renderer, loadSystem]);

  const share = async () => {
    try {
      const encoded = await encodeSystem(sim);
      // Le lien ouvert ici est déjà ce système : pas besoin de le recharger.
      openedHash.current = encoded;
      setShareLink(shareUrl(window.location.href, encoded));
    } catch (e) {
      setError(`Impossible de créer le lien : ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (e.code !== 'Space' || ['INPUT', 'SELECT', 'TEXTAREA', 'BUTTON'].includes(target.tagName)) return;
      e.preventDefault();
      sim.setPaused(!sim.paused);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [sim]);

  const onPreset = (id: PresetId) => {
    switch (id) {
      case 'solaire':
        return loadSystem(solarSystem());
      case 'kepler16':
        sim.setSpeed(30);
        return loadSystem(tightBinary());
      case 'centaure':
        sim.setSpeed(3652.5);
        return loadSystem(wideBinary());
      case 'aleatoire':
        return loadSystem(randomSystem());
      case 'disque':
        return setDiskDialog(true);
      case 'vide':
        return loadSystem(emptySystem(star?.star?.spectralClass ?? 'G'));
    }
  };

  const startDisk = (params: DiskParams) => {
    setDiskDialog(false);
    loadSystem(protoplanetaryDisk(params));
    // La vitesse demandée est volontairement haute : le budget de calcul la limitera.
    sim.setSpeed(3652.5);
    setOptions((o) => ({ ...o, showTrails: false }));
    setShowCharts(true);
  };

  const addPlanet = () => {
    if (!star) return;
    const planets = sim.children(star.id).filter((p) => p.kind === 'planet' && !p.circumbinary);
    const outermost = Math.max(0, ...planets.map((p) => p.elements?.a ?? 0));
    const hz = habitableZone(star.star!.luminosity);
    const a = outermost > 0 ? outermost * 1.6 : (hz.inner + hz.outer) / 2;
    const planet = makeOrbiter({
      name: `Planète ${planets.length + 1}`,
      planetType: 'tellurique',
      massEarth: 1,
      radiusKm: 6371,
      parentId: star.id,
      elements: { a, nu: Math.random() * 360 },
    });
    sim.addBody(planet);
    setSelectedId(planet.id);
  };

  const parentForMoon = selected && selected.kind === 'planet' ? selected : null;
  const addMoon = () => {
    const host = parentForMoon && sim.frameOf(parentForMoon);
    if (!parentForMoon || !host) return;
    const moons = sim.children(parentForMoon.id);
    const el = parentForMoon.elements;
    const hill = hillRadius(distance(parentForMoon.position, host.position), el?.e ?? 0, parentForMoon.mass, host.mass);
    const outermost = Math.max(0, ...moons.map((m) => m.elements?.a ?? 0));
    const a = outermost > 0 ? outermost * 1.6 : (parentForMoon.radiusKm * 15) / AU_KM;
    if (a > 0.4 * hill) {
      setError(`Plus de place pour une lune stable autour de ${parentForMoon.name} : elle serait arrachée par l'étoile.`);
      return;
    }
    const massEarth = 0.01;
    const moon = makeOrbiter({
      name: `${parentForMoon.name} ${ROMAN[moons.length] ?? moons.length + 1}`,
      kind: 'moon',
      planetType: 'naine',
      massEarth,
      radiusKm: estimateRadiusKm('naine', massEarth),
      parentId: parentForMoon.id,
      elements: { a, i: el?.i ?? 0, nu: Math.random() * 360 },
    });
    sim.addBody(moon);
    setSelectedId(moon.id);
    setError(null);
  };

  const save = () => {
    const blob = new Blob([serialize(sim)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sim.name.replace(/[^\p{L}\p{N}]+/gu, '-').toLowerCase() || 'systeme'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const load = async (file: File) => {
    try {
      loadSystem(deserialize(await file.text()), false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="app">
      <TopBar
        systemName={sim.name}
        onPreset={onPreset}
        onReset={() => {
          sim.reset();
          renderer?.clearTrails();
        }}
        onSave={save}
        onLoad={load}
        onFrame={() => renderer?.frameSystem(sim.bodies)}
        onShare={share}
      />
      <aside className="sidebar sidebar--left">
        {star && <StarsPanel sim={sim} />}
        <BodyList bodies={sim.bodies} selectedId={selectedId} onSelect={setSelectedId} onAddPlanet={addPlanet} onAddMoon={parentForMoon ? addMoon : null} />
      </aside>
      <main className="viewport">
        <SceneView sim={sim} selectedId={selected?.id ?? null} options={options} onPick={setSelectedId} onReady={setRenderer} />
        {error && (
          <div className="toast" role="alert">
            {error}
            <button type="button" className="icon" onClick={() => setError(null)} aria-label="Fermer">
              ×
            </button>
          </div>
        )}
        {showCharts && <ChartsPanel telemetry={telemetry} selectedId={selected?.id ?? null} onSelect={setSelectedId} onClose={() => setShowCharts(false)} />}
      </main>
      <aside className="sidebar sidebar--right">
        {selected ? (
          <BodyPanel sim={sim} body={selected} onClose={() => setSelectedId(null)} />
        ) : (
          <section className="panel">
            <h2>Fiche</h2>
            <p className="hint">Cliquez sur un corps (dans la vue ou la liste) pour afficher ses caractéristiques et le modifier.</p>
          </section>
        )}
        <EventLog events={sim.events} />
      </aside>
      <TimeBar sim={sim} options={options} onOptions={setOptions} showCharts={showCharts} onToggleCharts={() => setShowCharts((v) => !v)} />
      {diskDialog && <DiskDialog onStart={startDisk} onCancel={() => setDiskDialog(false)} />}
      {shareLink && <ShareDialog url={shareLink} onClose={() => setShareLink(null)} />}
    </div>
  );
}
