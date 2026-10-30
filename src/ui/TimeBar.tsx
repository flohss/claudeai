import type { ViewOptions } from '../render/SceneRenderer';
import type { Simulation } from '../sim/Simulation';
import { elapsed, speedLabel } from './format';

const SPEEDS = [1, 10, 30, 100, 365.25, 1000, 3652.5, 10000];

interface Props {
  sim: Simulation;
  options: ViewOptions;
  onOptions: (o: ViewOptions) => void;
  showCharts: boolean;
  onToggleCharts: () => void;
}

export function TimeBar({ sim, options, onOptions, showCharts, onToggleCharts }: Props) {
  const limited = !sim.paused && sim.effectiveSpeed > 0 && sim.effectiveSpeed < sim.speed * 0.85;
  const toggle = (k: keyof ViewOptions) => onOptions({ ...options, [k]: !options[k] });
  return (
    <footer className="timebar">
      <div className="time-controls">
        <button type="button" className="play" onClick={() => sim.setPaused(!sim.paused)} aria-label={sim.paused ? 'Lecture' : 'Pause'} title="Espace">
          {sim.paused ? '▶' : '❚❚'}
        </button>
        <div className="speeds" role="group" aria-label="Vitesse de simulation">
          {SPEEDS.map((s) => (
            <button type="button" key={s} className={sim.speed === s ? 'is-active' : ''} onClick={() => sim.setSpeed(s)}>
              {speedLabel(s)}
            </button>
          ))}
        </div>
        <div className="clock">
          <span>T + {elapsed(sim.time)}</span>
          {limited && (
            <span className="warning" title="La machine ne peut pas calculer assez vite tout en gardant la précision : la simulation ralentit au lieu de devenir fausse.">
              limité à {speedLabel(sim.effectiveSpeed)}
            </span>
          )}
        </div>
      </div>
      <div className="toggles">
        <button type="button" className={showCharts ? 'is-active' : ''} aria-pressed={showCharts} onClick={onToggleCharts}>
          📈 Graphiques
        </button>
        <label>
          <input type="checkbox" checked={options.showTrails} onChange={() => toggle('showTrails')} /> Trajectoires
        </label>
        <label>
          <input type="checkbox" checked={options.showLabels} onChange={() => toggle('showLabels')} /> Noms
        </label>
        <label>
          <input type="checkbox" checked={options.showZones} onChange={() => toggle('showZones')} /> Zones
        </label>
        <label>
          <input type="checkbox" checked={options.followSelected} onChange={() => toggle('followSelected')} /> Suivre la sélection
        </label>
      </div>
    </footer>
  );
}
