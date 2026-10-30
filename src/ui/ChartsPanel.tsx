import { useRef, useState } from 'react';
import type { Telemetry } from '../sim/telemetry';
import { num } from './format';
import { LineChart, type ChartSeries } from './LineChart';

/**
 * Palette catégorielle validée sur le fond sombre (#0d1220) : séparation pour
 * les daltonismes et contraste ≥ 3:1. L'ordre est fixe et une couleur reste
 * attachée au même corps tant qu'il est affiché.
 */
export const SERIES_COLORS = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'];
const MAX_SERIES = SERIES_COLORS.length;

type Tab = 'energie' | 'excentricite' | 'demi-grand-axe';

const TABS: [Tab, string][] = [
  ['energie', 'Énergie totale'],
  ['excentricite', 'Excentricité'],
  ['demi-grand-axe', 'Demi-grand axe'],
];

const DESCRIPTIONS: Record<Tab, string> = {
  energie:
    "Écart relatif de l'énergie totale depuis le début. Il doit rester proche de 0 : c'est la preuve que le calcul est précis. Les collisions dissipent de l'énergie (sauts, lignes pointillées).",
  excentricite: "0 = orbite circulaire. Les interactions entre planètes font osciller l'excentricité ; une hausse brutale annonce souvent une instabilité.",
  'demi-grand-axe': 'Taille moyenne de chaque orbite (échelle logarithmique). Une courbe qui dérive signale une migration ou une rencontre proche.',
};

interface Props {
  telemetry: Telemetry;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onClose: () => void;
}

const formatYears = (t: number) => `${num(t, 3)} an${t >= 2 ? 's' : ''}`;

export function ChartsPanel({ telemetry, selectedId, onSelect, onClose }: Props) {
  const [tab, setTab] = useState<Tab>('energie');
  const [showTable, setShowTable] = useState(false);
  const slots = useRef({ generation: -1, byId: new Map<string, number>() });

  if (slots.current.generation !== telemetry.generation) {
    slots.current = { generation: telemetry.generation, byId: new Map() };
  }

  // Corps affichés : les plus massifs encore présents, et toujours le corps sélectionné.
  const alive = [...telemetry.bodies.values()].filter((s) => s.alive).sort((a, b) => b.mass - a.mass);
  let shown = alive.slice(0, MAX_SERIES);
  const selected = alive.find((s) => s.id === selectedId);
  if (selected && !shown.includes(selected)) shown = [...shown.slice(0, MAX_SERIES - 1), selected];

  // Une couleur libérée seulement quand son corps n'est plus affiché : les autres ne changent jamais de couleur.
  const byId = slots.current.byId;
  const shownIds = new Set(shown.map((s) => s.id));
  for (const id of [...byId.keys()]) if (!shownIds.has(id)) byId.delete(id);
  for (const s of shown) {
    if (byId.has(s.id)) continue;
    const used = new Set(byId.values());
    byId.set(s.id, SERIES_COLORS.findIndex((_, k) => !used.has(k)));
  }
  const hidden = alive.length - shown.length;

  let series: ChartSeries[];
  if (tab === 'energie') {
    series = [{ id: 'energie', name: 'Énergie totale', color: SERIES_COLORS[0], values: telemetry.energyDrift }];
  } else {
    series = shown.map((s) => ({
      id: s.id,
      name: s.name,
      color: SERIES_COLORS[byId.get(s.id)!],
      values: tab === 'excentricite' ? s.eccentricity : s.semiMajorAxis,
      emphasized: s.id === selectedId,
    }));
  }

  const formatY =
    tab === 'energie' ? (v: number) => `${num(v, 2)} %` : tab === 'excentricite' ? (v: number) => num(v, 2) : (v: number) => `${num(v, 2)} UA`;
  const last = (values: number[]) => {
    for (let k = values.length - 1; k >= 0; k--) if (Number.isFinite(values[k])) return values[k];
    return NaN;
  };

  return (
    <section className="charts-drawer" aria-label="Graphiques">
      <header className="charts-header">
        <div className="tabs" role="tablist">
          {TABS.map(([id, label]) => (
            <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? 'is-active' : ''} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </div>
        <div className="row">
          <label className="check">
            <input type="checkbox" checked={showTable} onChange={(e) => setShowTable(e.target.checked)} /> Valeurs
          </label>
          <button type="button" className="icon" onClick={onClose} aria-label="Fermer les graphiques">
            ×
          </button>
        </div>
      </header>
      <p className="hint chart-description">
        {DESCRIPTIONS[tab]}
        {tab !== 'energie' && hidden > 0 && ` ${hidden} autre${hidden > 1 ? 's' : ''} corps non affiché${hidden > 1 ? 's' : ''} (les ${MAX_SERIES} plus massifs sont tracés).`}
      </p>
      {showTable ? (
        <table className="chart-table">
          <thead>
            <tr>
              <th scope="col">Série</th>
              <th scope="col">Actuel</th>
              <th scope="col">Min</th>
              <th scope="col">Max</th>
            </tr>
          </thead>
          <tbody>
            {series.map((s) => {
              const finite = s.values.filter(Number.isFinite);
              return (
                <tr key={s.id}>
                  <th scope="row">
                    <span className="legend-swatch" style={{ background: s.color }} /> {s.name}
                  </th>
                  <td>{finite.length ? formatY(last(s.values)) : '—'}</td>
                  <td>{finite.length ? formatY(Math.min(...finite)) : '—'}</td>
                  <td>{finite.length ? formatY(Math.max(...finite)) : '—'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <LineChart
          times={telemetry.times}
          series={series}
          yLabel={tab === 'energie' ? 'ΔE / E₀' : tab === 'excentricite' ? 'e' : 'a (UA)'}
          formatY={formatY}
          formatX={formatYears}
          logY={tab === 'demi-grand-axe'}
          includeZero={tab === 'energie'}
          markers={tab === 'energie' ? telemetry.markers : []}
          markerLabel="Changement de structure (collision, ajout, modification…)"
          onSeriesClick={onSelect}
          ariaLabel={`${TABS.find(([id]) => id === tab)![1]} en fonction du temps`}
        />
      )}
    </section>
  );
}
