import type { SimEvent } from '../sim/Simulation';
import { elapsed } from './format';

const ICONS: Record<SimEvent['kind'], string> = { collision: '💥', ejection: '🚀', evasion: '🌀', formation: '🪐', roche: '💫', info: 'ℹ️' };

export function EventLog({ events }: { events: SimEvent[] }) {
  return (
    <section className="panel">
      <h2>Journal</h2>
      {events.length === 0 ? (
        <p className="hint">Aucun événement. Les collisions, éjections, lunes arrachées ou disloquées et la naissance de protoplanètes apparaîtront ici.</p>
      ) : (
        <ul className="event-log">
          {events.map((e, k) => (
            <li key={`${e.time}-${k}`}>
              <span aria-hidden>{ICONS[e.kind]}</span>
              <span>
                <time>{elapsed(e.time)}</time> {e.message}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
