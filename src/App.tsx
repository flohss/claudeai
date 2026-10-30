import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react';
import { hillRadius } from './physics/orbits';
import { habitableZone } from './physics/stars';
import { AU_KM } from './physics/units';
import type { SceneRenderer, ViewOptions } from './render/SceneRenderer';
import { estimateRadiusKm, makeOrbiter } from './sim/factory';
import { emptySystem, solarSystem } from './sim/presets';
import { randomSystem } from './sim/random';
import { deserialize, serialize } from './sim/serialization';
import { Simulation, type SystemDefinition } from './sim/Simulation';
import { BodyList } from './ui/BodyList';
import { BodyPanel } from './ui/BodyPanel';
import { EventLog } from './ui/EventLog';
import { SceneView } from './ui/SceneView';
import { StarPanel } from './ui/StarPanel';
import { TimeBar } from './ui/TimeBar';
import { TopBar } from './ui/TopBar';

/** Force un nouveau rendu à intervalle régulier pour les valeurs qui évoluent en continu. */
function useTick(ms: number) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), ms);
    return () => clearInterval(id);
  }, [ms]);
}

export function App() {
  const sim = useMemo(() => new Simulation(solarSystem()), []);
  useSyncExternalStore(sim.subscribe, sim.getVersion);
  useTick(250);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [renderer, setRenderer] = useState<SceneRenderer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<ViewOptions>({ showTrails: true, showLabels: true, showZones: true, followSelected: false });

  const selected = sim.getBody(selectedId);
  const star = sim.star;

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

  const addPlanet = () => {
    if (!star) return;
    const planets = sim.children(star.id);
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
    if (!parentForMoon || !star) return;
    const moons = sim.children(parentForMoon.id);
    const el = parentForMoon.elements;
    const hill = hillRadius(el?.a ?? 1, el?.e ?? 0, parentForMoon.mass, star.mass);
    const outermost = Math.max(0, ...moons.map((m) => m.elements?.a ?? 0));
    const a = outermost > 0 ? outermost * 1.6 : (parentForMoon.radiusKm * 15) / AU_KM;
    if (a > 0.4 * hill) {
      setError(`Plus de place pour une lune stable autour de ${parentForMoon.name} : elle serait arrachée par l'étoile.`);
      return;
    }
    const massEarth = 0.01;
    const moon = makeOrbiter({
      name: `${parentForMoon.name} ${['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII'][moons.length] ?? moons.length + 1}`,
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
        onSolar={() => loadSystem(solarSystem())}
        onRandom={() => loadSystem(randomSystem())}
        onEmpty={() => loadSystem(emptySystem(star?.star?.spectralClass ?? 'G'))}
        onReset={() => {
          sim.reset();
          renderer?.clearTrails();
        }}
        onSave={save}
        onLoad={load}
        onFrame={() => renderer?.frameSystem(sim.bodies)}
      />
      <aside className="sidebar sidebar--left">
        {star && <StarPanel star={star} onChangeClass={(c) => sim.setStarClass(c)} />}
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
      <TimeBar sim={sim} options={options} onOptions={setOptions} />
    </div>
  );
}
