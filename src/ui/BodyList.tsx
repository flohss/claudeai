import type { Body } from '../physics/types';
import { EARTH_MASS_SUN } from '../physics/units';
import { num } from './format';

interface Props {
  bodies: Body[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAddPlanet: () => void;
  onAddMoon: (() => void) | null;
}

function Item({ body, bodies, selectedId, onSelect, depth }: { body: Body; bodies: Body[]; selectedId: string | null; onSelect: (id: string) => void; depth: number }) {
  const children = bodies.filter((b) => b.parentId === body.id && b.kind !== 'planetesimal');
  return (
    <li>
      <button
        type="button"
        className={`body-item${body.id === selectedId ? ' is-selected' : ''}`}
        style={{ paddingLeft: 8 + depth * 16 }}
        onClick={() => onSelect(body.id)}
      >
        <span className="dot" style={{ background: body.color }} />
        <span className="body-name">{body.name}</span>
        {body.circumbinary && (
          <span className="tag" title="Tourne autour des deux étoiles">
            circumbinaire
          </span>
        )}
        {body.rings && (
          <span className="tag" aria-label="anneaux" title="Anneaux">
            ◎
          </span>
        )}
      </button>
      {children.length > 0 && (
        <ul>
          {children.map((c) => (
            <Item key={c.id} body={c} bodies={bodies} selectedId={selectedId} onSelect={onSelect} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  );
}

export function BodyList({ bodies, selectedId, onSelect, onAddPlanet, onAddMoon }: Props) {
  const roots = bodies.filter((b) => !b.parentId);
  const planetesimals = bodies.filter((b) => b.kind === 'planetesimal');
  const planetesimalMass = planetesimals.reduce((s, b) => s + b.mass, 0) / EARTH_MASS_SUN;
  return (
    <section className="panel">
      <h2>Corps du système</h2>
      <ul className="body-list">
        {roots.map((b) => (
          <Item key={b.id} body={b} bodies={bodies} selectedId={selectedId} onSelect={onSelect} depth={0} />
        ))}
      </ul>
      {planetesimals.length > 0 && (
        <p className="hint planetesimal-count">
          + {planetesimals.length} planétésimaux ({num(planetesimalMass)} M⊕ au total), cliquables dans la vue.
        </p>
      )}
      <div className="row">
        <button type="button" onClick={onAddPlanet}>
          + Planète
        </button>
        <button type="button" onClick={onAddMoon ?? undefined} disabled={!onAddMoon} title={onAddMoon ? undefined : "Sélectionnez d'abord une planète"}>
          + Lune
        </button>
      </div>
    </section>
  );
}
