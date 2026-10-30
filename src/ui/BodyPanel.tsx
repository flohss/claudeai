import { useState } from 'react';
import {
  assessHabitability,
  currentElements,
  density,
  equilibriumTemperatureFromFlux,
  escapeVelocity,
  rocheLimitKm,
  stellarFlux,
  surfaceGravity,
  zoneStatusFromFlux,
} from '../physics/derived';
import { orbitalPeriod } from '../physics/orbits';
import { SPECTRAL_CLASSES, habitableZone, snowLine } from '../physics/stars';
import type { Body, PlanetType } from '../physics/types';
import { AU_KM, EARTH_MASS_SUN, EARTH_RADIUS_KM, JUPITER_MASS_EARTH, SUN_RADIUS_KM } from '../physics/units';
import { PLANET_TYPE_LABELS, estimateRadiusKm } from '../sim/factory';
import type { BodyPatch, Simulation } from '../sim/Simulation';
import { binaryStability } from '../sim/stability';
import { distance } from '../physics/vec3';
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

/** Masse volumique supposée d'une lune rocheuse pour la limite de Roche affichée (g/cm³). */
const ROCKY_MOON_DENSITY = 3;

function StarFacts({ sim, body }: { sim: Simulation; body: Body }) {
  const props = body.star!;
  const hz = habitableZone(props.luminosity);
  const orbiting = sim.bodies.filter((b) => b.parentId === body.id && b.kind !== 'star' && !b.circumbinary);
  const primary = body.parentId ? sim.getBody(body.parentId) : undefined;
  const bin = primary ? currentElements(body, primary) : null;
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
      <dt>Zone habitable propre</dt>
      <dd>
        {num(hz.inner)} – {num(hz.outer)} UA
      </dd>
      <dt>Ligne des glaces</dt>
      <dd>{num(snowLine(props.luminosity))} UA</dd>
      <dt>Corps en orbite</dt>
      <dd>{orbiting.filter((b) => b.kind !== 'planetesimal').length}</dd>
      {primary && bin && bin.a > 0 && (
        <>
          <dt>Orbite autour de {primary.name}</dt>
          <dd>
            {num(bin.a)} UA, e = {num(bin.e, 2)}
          </dd>
          <dt>Période de la binaire</dt>
          <dd>{duration(orbitalPeriod(bin.a, primary.mass, body.mass))}</dd>
        </>
      )}
    </dl>
  );
}

function OrbiterFacts({ sim, body }: { sim: Simulation; body: Body }) {
  const stars = sim.stars;
  const parent = sim.getBody(body.parentId);
  const frame = sim.frameOf(body);
  const massEarth = body.mass / EARTH_MASS_SUN;
  const g = surfaceGravity(body.mass, body.radiusKm);
  const osc = frame ? currentElements(body, frame) : null;
  const bound = osc && osc.a > 0 && Number.isFinite(osc.a) && osc.e < 1;
  const aroundStars = body.circumbinary || parent?.kind === 'star';
  // Une lune reçoit la lumière des étoiles à la distance de sa planète.
  const flux = stellarFlux(body, stars);
  const temp = equilibriumTemperatureFromFlux(flux, body.albedo);
  const zone = stars.length ? zoneStatusFromFlux(flux) : null;
  const habit = stars.length && body.kind !== 'planetesimal' ? assessHabitability(body, flux) : null;
  const stability = binaryStability(sim, body);
  const rocheKm = body.kind === 'planet' && body.planetType !== 'naine' ? rocheLimitKm(body.radiusKm, density(body.mass, body.radiusKm), ROCKY_MOON_DENSITY) : null;
  const hostName = body.circumbinary ? 'les deux étoiles' : parent?.name;

  return (
    <>
      <dl className="facts">
        <dt>Type</dt>
        <dd>{body.kind === 'planetesimal' ? 'Planétésimal' : body.planetType ? PLANET_TYPE_LABELS[body.planetType] : '—'}</dd>
        {hostName && (
          <>
            <dt>En orbite autour de</dt>
            <dd>{hostName}</dd>
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
        {frame && (
          <>
            <dt>{body.circumbinary ? 'Distance au barycentre' : parent?.kind === 'star' ? "Distance à l'étoile" : `Distance à ${parent?.name}`}</dt>
            <dd>{aroundStars ? `${num(distance(body.position, frame.position))} UA` : `${num(distance(body.position, frame.position) * AU_KM, 4)} km`}</dd>
          </>
        )}
        {bound && frame && (
          <>
            <dt>Demi-grand axe</dt>
            <dd>{aroundStars ? `${num(osc.a)} UA` : `${num(osc.a * AU_KM, 4)} km`}</dd>
            <dt>Excentricité</dt>
            <dd>{num(osc.e, 2)}</dd>
            <dt>Inclinaison</dt>
            <dd>{num(osc.i, 2)}°</dd>
            <dt>Période orbitale</dt>
            <dd>{duration(orbitalPeriod(osc.a, frame.mass, body.mass))}</dd>
          </>
        )}
        {rocheKm && (
          <>
            <dt title="En deçà, une lune rocheuse serait disloquée par les forces de marée et formerait un anneau.">Limite de Roche</dt>
            <dd>
              {num(rocheKm, 3)} km ({num(rocheKm / body.radiusKm, 2)} R)
            </dd>
          </>
        )}
        <dt>Flux reçu</dt>
        <dd>{num(flux)} × Terre</dd>
        <dt>Température d'équilibre</dt>
        <dd>
          {num(temp)} K ({num(temp - 273.15)} °C)
        </dd>
      </dl>
      {stability && (
        <div className={`verdict ${stability.stable ? 'verdict--potentiellement-habitable' : 'verdict--instable'}`}>
          <strong>{stability.stable ? 'Orbite stable' : 'Orbite instable'}</strong>
          <p>
            {stability.kind === 'P'
              ? `Une planète circumbinaire est stable au-delà de ${num(stability.limitAu)} UA du barycentre.`
              : `Autour d'une étoile d'un système double, une orbite est stable jusqu'à ${num(stability.limitAu)} UA.`}
          </p>
          <p className="hint">Critère de Holman et Wiegert (1999).</p>
        </div>
      )}
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
  tilt: string;
  hasRings: boolean;
  ringInner: string;
  ringOuter: string;
  ringOpacity: string;
  ringColor: string;
}

const parse = (s: string) => Number(s.replace(',', '.'));

function EditForm({ sim, body }: { sim: Simulation; body: Body }) {
  const parent = sim.getBody(body.parentId);
  const frame = sim.frameOf(body);
  const aInKm = parent?.kind !== 'star' && !body.circumbinary;
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
    tilt: String(body.axialTilt ?? 0),
    hasRings: !!body.rings,
    ringInner: String(+(body.rings?.inner ?? 1.3).toFixed(2)),
    ringOuter: String(+(body.rings?.outer ?? 2.2).toFixed(2)),
    ringOpacity: String(+(body.rings?.opacity ?? 0.6).toFixed(2)),
    ringColor: body.rings?.color ?? '#d9c7a0',
  }));
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.type === 'checkbox' ? (e.target as HTMLInputElement).checked : e.target.value });

  const apply = (e: React.FormEvent) => {
    e.preventDefault();
    const massEarth = parse(form.massEarth);
    const radiusKm = parse(form.radiusKm);
    const albedo = parse(form.albedo);
    const aValue = parse(form.a);
    const ecc = parse(form.e);
    const inc = parse(form.i);
    const tilt = parse(form.tilt);
    if (!form.name.trim()) return setError('Le nom est obligatoire.');
    if (!(massEarth > 0)) return setError('La masse doit être positive.');
    if (!(radiusKm > 0)) return setError('Le rayon doit être positif.');
    if (!(albedo >= 0 && albedo < 1)) return setError("L'albédo doit être compris entre 0 et 1.");
    if (!(ecc >= 0 && ecc <= 0.95)) return setError("L'excentricité doit être comprise entre 0 et 0,95.");
    if (!(inc >= 0 && inc <= 180)) return setError("L'inclinaison doit être comprise entre 0 et 180°.");
    if (!(tilt >= 0 && tilt <= 180)) return setError("L'inclinaison de l'axe doit être comprise entre 0 et 180°.");
    const aAu = aInKm ? aValue / AU_KM : aValue;
    if (!(aAu > 0) || !parent || !frame) return setError('Le demi-grand axe doit être positif.');
    if (!body.circumbinary && aAu * (1 - ecc) * AU_KM < parent.radiusKm + radiusKm) return setError(`Avec cette orbite, le corps traverserait ${parent.name}.`);

    let rings: BodyPatch['rings'] = undefined;
    if (form.hasRings) {
      const inner = parse(form.ringInner);
      const outer = parse(form.ringOuter);
      const opacity = parse(form.ringOpacity);
      if (!(inner >= 1 && outer > inner)) return setError("Les anneaux doivent commencer au-delà de la surface (≥ 1 rayon) et le bord extérieur dépasser l'intérieur.");
      if (!(opacity > 0 && opacity <= 1)) return setError("L'opacité des anneaux doit être comprise entre 0 et 1.");
      rings = { inner, outer, opacity, color: form.ringColor };
    }

    const patch: BodyPatch = {
      name: form.name.trim(),
      planetType: form.planetType,
      mass: massEarth * EARTH_MASS_SUN,
      radiusKm,
      color: form.color,
      albedo,
      axialTilt: tilt,
      rings,
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
          <span>Axe de rotation (°)</span>
          <input inputMode="decimal" value={form.tilt} onChange={set('tilt')} />
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
      <fieldset className="subform">
        <legend>
          <label className="check">
            <input type="checkbox" checked={form.hasRings} onChange={set('hasRings')} /> Anneaux
          </label>
        </legend>
        {form.hasRings && (
          <div className="field-grid">
            <label className="field">
              <span>Bord intérieur (rayons)</span>
              <input inputMode="decimal" value={form.ringInner} onChange={set('ringInner')} />
            </label>
            <label className="field">
              <span>Bord extérieur (rayons)</span>
              <input inputMode="decimal" value={form.ringOuter} onChange={set('ringOuter')} />
            </label>
            <label className="field">
              <span>Opacité</span>
              <input inputMode="decimal" value={form.ringOpacity} onChange={set('ringOpacity')} />
            </label>
            <label className="field">
              <span>Couleur</span>
              <input type="color" value={form.ringColor} onChange={set('ringColor')} />
            </label>
          </div>
        )}
      </fieldset>
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
      <p className="hint">
        L'orbite modifiée repart de la position actuelle du corps. Les anneaux sont décoratifs : leurs particules ne sont pas simulées.
      </p>
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
      {body.kind !== 'star' && <EditForm key={`${body.id}-${body.parentId}-${body.kind}`} sim={sim} body={body} />}
    </section>
  );
}
