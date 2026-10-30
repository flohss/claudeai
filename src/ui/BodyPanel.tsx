import { useState } from 'react';
import {
  assessHabitability,
  currentElements,
  density,
  distanceAu,
  equilibriumTemperature,
  escapeVelocity,
  surfaceGravity,
  zoneStatus,
} from '../physics/derived';
import { orbitalPeriod } from '../physics/orbits';
import { SPECTRAL_CLASSES, habitableZone, snowLine } from '../physics/stars';
import type { Body, PlanetType } from '../physics/types';
import { AU_KM, EARTH_MASS_SUN, EARTH_RADIUS_KM, JUPITER_MASS_EARTH, SUN_RADIUS_KM } from '../physics/units';
import { PLANET_TYPE_LABELS, estimateRadiusKm } from '../sim/factory';
import type { BodyPatch, Simulation } from '../sim/Simulation';
import { duration, num } from './format';

interface Props {
  sim: Simulation;
  body: Body;
  onClose: () => void;
}

const ZONE_LABELS = { 'trop-chaud': 'Trop chaud', habitable: 'Zone habitable', 'trop-froid': 'Trop froid' } as const;
const VERDICT_LABELS = {
  'potentiellement-habitable': 'Potentiellement habitable',
  'lunes-candidates': 'Lunes potentiellement habitables',
  'non-habitable': 'Non habitable',
} as const;

function StarFacts({ sim, body }: { sim: Simulation; body: Body }) {
  const props = body.star!;
  const hz = habitableZone(props.luminosity);
  const planets = sim.bodies.filter((b) => b.kind === 'planet').length;
  const moons = sim.bodies.filter((b) => b.kind === 'moon').length;
  return (
    <dl className="facts">
      <dt>Classe</dt>
      <dd>{SPECTRAL_CLASSES[props.spectralClass].label}</dd>
      <dt>Masse</dt>
      <dd>{num(body.mass)} M☉</dd>
      <dt>Rayon</dt>
      <dd>{num(body.radiusKm / SUN_RADIUS_KM)} R☉</dd>
      <dt>Luminosité</dt>
      <dd>{num(props.luminosity)} L☉</dd>
      <dt>Température</dt>
      <dd>{num(props.temperatureK, 4)} K</dd>
      <dt>Zone habitable</dt>
      <dd>
        {num(hz.inner)} – {num(hz.outer)} UA
      </dd>
      <dt>Ligne des glaces</dt>
      <dd>{num(snowLine(props.luminosity))} UA</dd>
      <dt>Planètes / lunes</dt>
      <dd>
        {planets} / {moons}
      </dd>
    </dl>
  );
}

function OrbiterFacts({ sim, body }: { sim: Simulation; body: Body }) {
  const star = sim.star;
  const parent = sim.getBody(body.parentId);
  const massEarth = body.mass / EARTH_MASS_SUN;
  const g = surfaceGravity(body.mass, body.radiusKm);
  const osc = parent ? currentElements(body, parent) : null;
  const bound = osc && osc.a > 0 && Number.isFinite(osc.a) && osc.e < 1;
  // Une lune reçoit la lumière de l'étoile à la distance de sa planète.
  const dStar = star ? distanceAu(body, star) : NaN;
  const L = star?.star?.luminosity ?? 0;
  const temp = equilibriumTemperature(L, dStar, body.albedo);
  const zone = star ? zoneStatus(L, dStar) : null;
  const habit = star ? assessHabitability(body, L, dStar) : null;

  return (
    <>
      <dl className="facts">
        <dt>Type</dt>
        <dd>{body.planetType ? PLANET_TYPE_LABELS[body.planetType] : '—'}</dd>
        {parent && (
          <>
            <dt>En orbite autour de</dt>
            <dd>{parent.name}</dd>
          </>
        )}
        <dt>Masse</dt>
        <dd>
          {num(massEarth)} M⊕{massEarth > 30 && <> ({num(massEarth / JUPITER_MASS_EARTH)} M♃)</>}
        </dd>
        <dt>Rayon</dt>
        <dd>
          {num(body.radiusKm, 4)} km ({num(body.radiusKm / EARTH_RADIUS_KM)} R⊕)
        </dd>
        <dt>Masse volumique</dt>
        <dd>{num(density(body.mass, body.radiusKm))} g/cm³</dd>
        <dt>Gravité de surface</dt>
        <dd>
          {num(g)} m/s² ({num(g / 9.81)} g)
        </dd>
        <dt>Vitesse de libération</dt>
        <dd>{num(escapeVelocity(body.mass, body.radiusKm))} km/s</dd>
        <dt>Distance à l'étoile</dt>
        <dd>{num(dStar)} UA</dd>
        {bound && parent && (
          <>
            <dt>Demi-grand axe</dt>
            <dd>{parent.kind === 'star' ? `${num(osc.a)} UA` : `${num(osc.a * AU_KM, 4)} km`}</dd>
            <dt>Excentricité</dt>
            <dd>{num(osc.e, 2)}</dd>
            <dt>Inclinaison</dt>
            <dd>{num(osc.i, 2)}°</dd>
            <dt>Période orbitale</dt>
            <dd>{duration(orbitalPeriod(osc.a, parent.mass, body.mass))}</dd>
          </>
        )}
        <dt>Température d'équilibre</dt>
        <dd>
          {num(temp)} K ({num(temp - 273.15)} °C)
        </dd>
      </dl>
      {zone && habit && (
        <div className={`verdict verdict--${habit.verdict}`}>
          <span className={`badge badge--${zone}`}>{ZONE_LABELS[zone]}</span>
          <strong>{VERDICT_LABELS[habit.verdict]}</strong>
          <p>{habit.reason}</p>
          <p className="hint">Température sans effet de serre : la Terre y serait à −18 °C.</p>
        </div>
      )}
    </>
  );
}

interface FormState {
  name: string;
  planetType: PlanetType;
  massEarth: string;
  radiusKm: string;
  color: string;
  albedo: string;
  a: string;
  e: string;
  i: string;
}

const parse = (s: string) => Number(s.replace(',', '.'));

function EditForm({ sim, body }: { sim: Simulation; body: Body }) {
  const parent = sim.getBody(body.parentId);
  const aInKm = parent?.kind !== 'star';
  const el = body.elements;
  const [form, setForm] = useState<FormState>(() => ({
    name: body.name,
    planetType: body.planetType ?? 'tellurique',
    massEarth: String(+(body.mass / EARTH_MASS_SUN).toPrecision(4)),
    radiusKm: String(Math.round(body.radiusKm)),
    color: body.color,
    albedo: String(body.albedo),
    a: el ? String(+(aInKm ? el.a * AU_KM : el.a).toPrecision(5)) : '',
    e: el ? String(+el.e.toFixed(4)) : '0',
    i: el ? String(+el.i.toFixed(2)) : '0',
  }));
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });

  const apply = (e: React.FormEvent) => {
    e.preventDefault();
    const massEarth = parse(form.massEarth);
    const radiusKm = parse(form.radiusKm);
    const albedo = parse(form.albedo);
    const aValue = parse(form.a);
    const ecc = parse(form.e);
    const inc = parse(form.i);
    if (!form.name.trim()) return setError('Le nom est obligatoire.');
    if (!(massEarth > 0)) return setError('La masse doit être positive.');
    if (!(radiusKm > 0)) return setError('Le rayon doit être positif.');
    if (!(albedo >= 0 && albedo < 1)) return setError("L'albédo doit être compris entre 0 et 1.");
    if (!(ecc >= 0 && ecc <= 0.95)) return setError("L'excentricité doit être comprise entre 0 et 0,95.");
    if (!(inc >= 0 && inc <= 180)) return setError("L'inclinaison doit être comprise entre 0 et 180°.");
    const aAu = aInKm ? aValue / AU_KM : aValue;
    if (!(aAu > 0) || !parent) return setError('Le demi-grand axe doit être positif.');
    if (aAu * (1 - ecc) * AU_KM < parent.radiusKm + radiusKm) return setError(`Avec cette orbite, le corps traverserait ${parent.name}.`);

    const patch: BodyPatch = {
      name: form.name.trim(),
      planetType: form.planetType,
      mass: massEarth * EARTH_MASS_SUN,
      radiusKm,
      color: form.color,
      albedo,
      elements: { Omega: el?.Omega ?? 0, omega: el?.omega ?? 0, nu: el?.nu ?? 0, a: aAu, e: ecc, i: inc },
    };
    setError(null);
    sim.updateBody(body.id, patch);
  };

  return (
    <form className="edit-form" onSubmit={apply}>
      <h3>Modifier</h3>
      <label className="field">
        <span>Nom</span>
        <input value={form.name} onChange={set('name')} />
      </label>
      <label className="field">
        <span>Type</span>
        <select value={form.planetType} onChange={set('planetType')}>
          {(Object.keys(PLANET_TYPE_LABELS) as PlanetType[]).map((t) => (
            <option key={t} value={t}>
              {PLANET_TYPE_LABELS[t]}
            </option>
          ))}
        </select>
      </label>
      <div className="field-grid">
        <label className="field">
          <span>Masse (M⊕)</span>
          <input inputMode="decimal" value={form.massEarth} onChange={set('massEarth')} />
        </label>
        <label className="field">
          <span>Rayon (km)</span>
          <span className="with-button">
            <input inputMode="decimal" value={form.radiusKm} onChange={set('radiusKm')} />
            <button
              type="button"
              title="Estimer le rayon à partir du type et de la masse"
              onClick={() => {
                const m = parse(form.massEarth);
                if (m > 0) setForm({ ...form, radiusKm: String(Math.round(estimateRadiusKm(form.planetType, m))) });
              }}
            >
              ≈
            </button>
          </span>
        </label>
        <label className="field">
          <span>Demi-grand axe ({aInKm ? 'km' : 'UA'})</span>
          <input inputMode="decimal" value={form.a} onChange={set('a')} />
        </label>
        <label className="field">
          <span>Excentricité</span>
          <input inputMode="decimal" value={form.e} onChange={set('e')} />
        </label>
        <label className="field">
          <span>Inclinaison (°)</span>
          <input inputMode="decimal" value={form.i} onChange={set('i')} />
        </label>
        <label className="field">
          <span>Albédo</span>
          <input inputMode="decimal" value={form.albedo} onChange={set('albedo')} />
        </label>
        <label className="field">
          <span>Couleur</span>
          <input type="color" value={form.color} onChange={set('color')} />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button type="submit" className="primary">
          Appliquer
        </button>
        <button
          type="button"
          className="danger"
          onClick={() => {
            const moons = sim.children(body.id).length;
            if (window.confirm(`Supprimer ${body.name}${moons ? ` et ses ${moons} lune(s)` : ''} ?`)) sim.removeBody(body.id);
          }}
        >
          Supprimer
        </button>
      </div>
      <p className="hint">L'orbite modifiée repart de la position actuelle du corps.</p>
    </form>
  );
}

export function BodyPanel({ sim, body, onClose }: Props) {
  return (
    <section className="panel body-panel">
      <header className="panel-header">
        <h2>
          <span className="dot" style={{ background: body.color }} />
          {body.name}
        </h2>
        <button type="button" className="icon" onClick={onClose} aria-label="Fermer la fiche">
          ×
        </button>
      </header>
      {body.kind === 'star' ? <StarFacts sim={sim} body={body} /> : <OrbiterFacts sim={sim} body={body} />}
      {body.kind !== 'star' && <EditForm key={`${body.id}-${body.parentId}`} sim={sim} body={body} />}
    </section>
  );
}
