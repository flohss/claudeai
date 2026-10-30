import { useState } from 'react';
import { pTypeCriticalAu, sTypeCriticalAu } from '../physics/binary';
import { currentElements } from '../physics/derived';
import { SPECTRAL_CLASSES, SPECTRAL_ORDER, habitableZone, snowLine } from '../physics/stars';
import type { Body, SpectralClass } from '../physics/types';
import type { Simulation } from '../sim/Simulation';
import { REMNANT_LABELS } from './BodyPanel';
import { num } from './format';

const parse = (s: string) => Number(s.replace(',', '.'));

function ClassSelect({ value, onChange }: { value: SpectralClass; onChange: (c: SpectralClass) => void }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value as SpectralClass)}>
      {SPECTRAL_ORDER.map((c) => (
        <option key={c} value={c}>
          {SPECTRAL_CLASSES[c].label}
        </option>
      ))}
    </select>
  );
}

function StarBlock({ sim, star }: { sim: Simulation; star: Body }) {
  const props = star.star!;
  const hz = habitableZone(props.luminosity);
  return (
    <div className="star-block">
      <label className="field">
        <span>
          <span className="dot" style={{ background: star.color }} /> {star.name}
        </span>
        {props.remnant || sim.evolutions.some((e) => e.starId === star.id) ? (
          <span className="remnant">{props.remnant ? REMNANT_LABELS[props.remnant] : 'Géante rouge (en cours)'}</span>
        ) : (
          <ClassSelect value={props.spectralClass} onChange={(c) => sim.setStarClass(star.id, c)} />
        )}
      </label>
      <dl className="facts compact">
        <dt>Masse</dt>
        <dd>{num(star.mass)} M☉</dd>
        <dt>Luminosité</dt>
        <dd>{num(props.luminosity)} L☉</dd>
        <dt>Zone habitable</dt>
        <dd>
          <span className="swatch swatch--hz" /> {num(hz.inner)} – {num(hz.outer)} UA
        </dd>
        <dt>Ligne des glaces</dt>
        <dd>
          <span className="swatch swatch--snow" /> {num(snowLine(props.luminosity))} UA
        </dd>
      </dl>
    </div>
  );
}

/** Orbite de l'étoile compagne et zones de stabilité des planètes (Holman-Wiegert). */
function BinaryBlock({ sim, primary, companion }: { sim: Simulation; primary: Body; companion: Body }) {
  const el = companion.elements;
  const [a, setA] = useState(String(+(el?.a ?? 20).toPrecision(4)));
  const [e, setE] = useState(String(+(el?.e ?? 0).toFixed(3)));
  const [error, setError] = useState<string | null>(null);
  const bin = currentElements(companion, primary);
  const total = primary.mass + companion.mass;
  const bound = bin.a > 0 && bin.e < 1;

  return (
    <div className="star-block">
      {bound && (
        <dl className="facts compact">
          <dt>Séparation moyenne</dt>
          <dd>{num(bin.a)} UA</dd>
          <dt>Planètes stables, étoile {primary.name}</dt>
          <dd>&lt; {num(sTypeCriticalAu(bin.a, bin.e, companion.mass / total))} UA</dd>
          <dt>Planètes stables, étoile {companion.name}</dt>
          <dd>&lt; {num(sTypeCriticalAu(bin.a, bin.e, primary.mass / total))} UA</dd>
          <dt>Planètes circumbinaires stables</dt>
          <dd>&gt; {num(pTypeCriticalAu(bin.a, bin.e, Math.min(primary.mass, companion.mass) / total))} UA</dd>
        </dl>
      )}
      <form
        className="field-grid"
        onSubmit={(ev) => {
          ev.preventDefault();
          const av = parse(a);
          const ev2 = parse(e);
          if (!(av > 0)) return setError('La séparation doit être positive.');
          if (!(ev2 >= 0 && ev2 <= 0.95)) return setError("L'excentricité doit être comprise entre 0 et 0,95.");
          setError(null);
          sim.updateBody(companion.id, { elements: { ...(el ?? { i: 0, Omega: 0, omega: 0, nu: 0 }), a: av, e: ev2 } });
        }}
      >
        <label className="field">
          <span>Séparation (UA)</span>
          <input inputMode="decimal" value={a} onChange={(ev) => setA(ev.target.value)} />
        </label>
        <label className="field">
          <span>Excentricité</span>
          <input inputMode="decimal" value={e} onChange={(ev) => setE(ev.target.value)} />
        </label>
        {error && <p className="error span-2">{error}</p>}
        <div className="row span-2">
          <button type="submit">Appliquer</button>
          <button
            type="button"
            className="danger"
            onClick={() => {
              if (window.confirm(`Retirer ${companion.name} et les planètes qui tournent autour ?`)) sim.removeBody(companion.id);
            }}
          >
            Retirer la compagne
          </button>
        </div>
      </form>
      <p className="hint">Les limites de stabilité suivent le critère de Holman et Wiegert (1999).</p>
    </div>
  );
}

function AddCompanion({ sim }: { sim: Simulation }) {
  const [open, setOpen] = useState(false);
  const [cls, setCls] = useState<SpectralClass>('K');
  const [a, setA] = useState('20');
  const [e, setE] = useState('0,3');
  const [error, setError] = useState<string | null>(null);
  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}>
        + Étoile compagne
      </button>
    );
  }
  return (
    <form
      className="star-block"
      onSubmit={(ev) => {
        ev.preventDefault();
        const av = parse(a);
        const ev2 = parse(e);
        if (!(av > 0)) return setError('La séparation doit être positive.');
        if (!(ev2 >= 0 && ev2 <= 0.95)) return setError("L'excentricité doit être comprise entre 0 et 0,95.");
        sim.addCompanion(cls, av, ev2);
        setOpen(false);
      }}
    >
      <h3>Nouvelle étoile compagne</h3>
      <label className="field">
        <span>Classe</span>
        <ClassSelect value={cls} onChange={setCls} />
      </label>
      <div className="field-grid">
        <label className="field">
          <span>Séparation (UA)</span>
          <input inputMode="decimal" value={a} onChange={(ev) => setA(ev.target.value)} />
        </label>
        <label className="field">
          <span>Excentricité</span>
          <input inputMode="decimal" value={e} onChange={(ev) => setE(ev.target.value)} />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <p className="hint">Les planètes existantes gardent leur étoile ; celles trop proches de la compagne deviendront instables.</p>
      <div className="row">
        <button type="submit" className="primary">
          Ajouter
        </button>
        <button type="button" onClick={() => setOpen(false)}>
          Annuler
        </button>
      </div>
    </form>
  );
}

export function StarsPanel({ sim }: { sim: Simulation }) {
  const stars = sim.stars;
  const primary = sim.star;
  const companion = stars.find((s) => s.parentId);
  return (
    <section className="panel">
      <h2>{stars.length > 1 ? 'Étoiles (système double)' : 'Étoile'}</h2>
      {stars.map((s) => (
        <StarBlock key={s.id} sim={sim} star={s} />
      ))}
      {primary && companion ? (
        <BinaryBlock key={companion.id} sim={sim} primary={primary} companion={companion} />
      ) : (
        <AddCompanion sim={sim} />
      )}
      <p className="hint">Changer de classe recalcule les orbites autour de la nouvelle masse.</p>
    </section>
  );
}
