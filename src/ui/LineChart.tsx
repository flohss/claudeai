import { useEffect, useRef, useState } from 'react';

export interface ChartSeries {
  id: string;
  name: string;
  color: string;
  values: number[];
  emphasized?: boolean;
}

interface Props {
  times: number[];
  series: ChartSeries[];
  /** Libellé de l'axe vertical, unité comprise */
  yLabel: string;
  formatY: (v: number) => string;
  formatX: (t: number) => string;
  logY?: boolean;
  /** La valeur 0 doit rester visible (ex. une dérive) */
  includeZero?: boolean;
  /** Instants à signaler par une ligne verticale */
  markers?: number[];
  markerLabel?: string;
  onSeriesClick?: (id: string) => void;
  ariaLabel: string;
}

const M = { top: 10, right: 14, bottom: 24, left: 56 };
const HEIGHT = 190;

/** Graduations « rondes » (1, 2, 5 × 10ⁿ) couvrant [min, max]. */
export function niceTicks(min: number, max: number, count = 5): number[] {
  if (!(max > min)) return [min];
  const raw = (max - min) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 5, 10].map((k) => k * mag).find((s) => s >= raw) ?? 10 * mag;
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) ticks.push(Math.abs(v) < step * 1e-9 ? 0 : v);
  return ticks;
}

function logTicks(min: number, max: number): number[] {
  const ticks: number[] = [];
  for (let e = Math.floor(Math.log10(min)); e <= Math.ceil(Math.log10(max)); e++) {
    for (const k of [1, 2, 5]) {
      const v = k * Math.pow(10, e);
      if (v >= min && v <= max) ticks.push(v);
    }
  }
  return ticks.length >= 2 ? ticks : [min, max];
}

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(600);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);
  return [ref, width] as const;
}

/** Courbes temporelles en SVG, avec réticule, infobulle et légende cliquable. */
export function LineChart({ times, series, yLabel, formatY, formatX, logY, includeZero, markers = [], markerLabel, onSeriesClick, ariaLabel }: Props) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  const plotW = Math.max(50, width - M.left - M.right);
  const plotH = HEIGHT - M.top - M.bottom;
  const n = times.length;

  let lo = Infinity;
  let hi = -Infinity;
  for (const s of series)
    for (const v of s.values)
      if (Number.isFinite(v) && (!logY || v > 0)) {
        lo = Math.min(lo, v);
        hi = Math.max(hi, v);
      }
  const hasData = n >= 2 && Number.isFinite(lo);
  if (includeZero) {
    lo = Math.min(lo, 0);
    hi = Math.max(hi, 0);
  }
  if (hasData && hi - lo < 1e-12) {
    const pad = logY ? lo * 0.5 : Math.max(Math.abs(lo) * 0.1, 1e-6);
    lo -= pad;
    hi += pad;
  }
  if (hasData && logY) {
    lo /= 1.15;
    hi *= 1.15;
  } else if (hasData) {
    const pad = (hi - lo) * 0.06;
    lo -= includeZero && lo === 0 ? 0 : pad;
    hi += pad;
  }

  const t0 = times[0] ?? 0;
  const t1 = times[n - 1] ?? 1;
  const x = (t: number) => M.left + ((t - t0) / (t1 - t0 || 1)) * plotW;
  const y = logY
    ? (v: number) => M.top + plotH - ((Math.log10(v) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo))) * plotH
    : (v: number) => M.top + plotH - ((v - lo) / (hi - lo)) * plotH;

  const path = (values: number[]) => {
    let d = '';
    let pen = false;
    for (let k = 0; k < n; k++) {
      const v = values[k];
      if (!Number.isFinite(v) || (logY && v <= 0)) {
        pen = false;
        continue;
      }
      d += `${pen ? 'L' : 'M'}${x(times[k]).toFixed(1)},${y(v).toFixed(1)}`;
      pen = true;
    }
    return d;
  };

  const yTicks = hasData ? (logY ? logTicks(lo, hi) : niceTicks(lo, hi, 4)) : [];
  const xTicks = hasData ? niceTicks(t0, t1, Math.max(2, Math.floor(plotW / 110))) : [];

  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    const rect = (e.currentTarget as SVGRectElement).getBoundingClientRect();
    const t = t0 + ((e.clientX - rect.left) / rect.width) * (t1 - t0);
    let best = 0;
    for (let k = 1; k < n; k++) if (Math.abs(times[k] - t) < Math.abs(times[best] - t)) best = k;
    setHover(best);
  };

  const hoverRows =
    hover !== null && hover < n
      ? series
          .map((s) => ({ s, v: s.values[hover] }))
          .filter((r) => Number.isFinite(r.v))
          .sort((a, b) => b.v - a.v)
      : [];
  const hoverX = hover !== null && hover < n ? x(times[hover]) : 0;

  return (
    <div className="chart" ref={ref}>
      {series.length > 1 && (
        <ul className="legend" aria-label="Légende">
          {series.map((s) => (
            <li key={s.id}>
              <button type="button" className={s.emphasized ? 'is-emphasized' : ''} onClick={() => onSeriesClick?.(s.id)} title="Sélectionner ce corps">
                <span className="legend-swatch" style={{ background: s.color }} />
                {s.name}
              </button>
            </li>
          ))}
        </ul>
      )}
      {!hasData ? (
        <p className="hint chart-empty">Lancez la simulation pour collecter des données.</p>
      ) : (
        <div className="chart-plot">
          <svg width={width} height={HEIGHT} role="img" aria-label={ariaLabel}>
            {yTicks.map((v) => (
              <g key={`y${v}`}>
                <line className="grid" x1={M.left} x2={M.left + plotW} y1={y(v)} y2={y(v)} />
                <text className="tick" x={M.left - 6} y={y(v)} textAnchor="end" dominantBaseline="middle">
                  {formatY(v)}
                </text>
              </g>
            ))}
            {includeZero && lo < 0 && hi > 0 && <line className="zero" x1={M.left} x2={M.left + plotW} y1={y(0)} y2={y(0)} />}
            {xTicks.map((t) => (
              <text key={`x${t}`} className="tick" x={x(t)} y={HEIGHT - 6} textAnchor="middle">
                {formatX(t)}
              </text>
            ))}
            <text className="axis-label" transform={`translate(12 ${M.top + plotH / 2}) rotate(-90)`} textAnchor="middle">
              {yLabel}
            </text>
            {markers
              .filter((t) => t >= t0 && t <= t1)
              .map((t, k) => (
                <line key={`m${k}`} className="marker" x1={x(t)} x2={x(t)} y1={M.top} y2={M.top + plotH}>
                  {markerLabel && <title>{markerLabel}</title>}
                </line>
              ))}
            {series
              .slice()
              .sort((a, b) => Number(!!a.emphasized) - Number(!!b.emphasized))
              .map((s) => (
                <path
                  key={s.id}
                  d={path(s.values)}
                  fill="none"
                  stroke={s.color}
                  strokeWidth={s.emphasized ? 3 : 2}
                  strokeOpacity={series.some((o) => o.emphasized) && !s.emphasized ? 0.55 : 1}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              ))}
            {hover !== null && hover < n && (
              <g>
                <line className="crosshair" x1={hoverX} x2={hoverX} y1={M.top} y2={M.top + plotH} />
                {hoverRows.map(({ s, v }) => (
                  <circle key={s.id} cx={hoverX} cy={y(v)} r={4} fill={s.color} className="hover-dot" />
                ))}
              </g>
            )}
            <rect
              x={M.left}
              y={M.top}
              width={plotW}
              height={plotH}
              fill="transparent"
              onPointerMove={onMove}
              onPointerLeave={() => setHover(null)}
            />
          </svg>
          {hover !== null && hover < n && hoverRows.length > 0 && (
            <div className="chart-tooltip" style={{ left: Math.min(hoverX + 12, width - 200), top: M.top }}>
              <div className="tooltip-title">{formatX(times[hover])}</div>
              {hoverRows.map(({ s, v }) => (
                <div key={s.id} className="tooltip-row">
                  <span className="legend-swatch" style={{ background: s.color }} />
                  <span className="tooltip-name">{s.name}</span>
                  <span className="tooltip-value">{formatY(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
