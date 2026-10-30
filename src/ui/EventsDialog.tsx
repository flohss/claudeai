import { useEffect, useRef, useState } from 'react';
import { MEGATON_J, impactEnergyJ } from '../physics/impacts';
import { SPECTRAL_CLASSES, SPECTRAL_ORDER } from '../physics/stars';
import type { Body, SpectralClass } from '../physics/types';
import { EARTH_MASS_SUN, JUPITER_MASS_EARTH, SUN_MASS_KG } from '../physics/units';
import { newId } from '../sim/factory';
import { KM_S, type ImpulseDirection, type Simulation } from '../sim/Simulation';
import { num } from './format';

type Tab = 'intrus' | 'impact' | 'etoile' | 'impulsion';

interface Props {
  sim: Simulation;
  selectedId: string | null;
  /** Appelé après le déclenchement, avec le corps à sélectionner et la vitesse conseillée (jours/s) */
  onDone: (focusId: string | null, speed: number | null) => void;
  onCancel: () => void;
}

const parse = (s: string) => Number(s.replace(',', '.'));
const random = (min: number, max: number) => min + Math.random() * (max - min);

/** Impacteurs de référence : diamètre (km) et masse volumique (kg/m³). */
const IMPACTORS = [
  { id: 'tcheliabinsk', label: 'Tcheliabinsk (20 m, 2013)', diameterKm: 0.02, density: 3300 },
  { id: 'toungouska', label: 'Toungouska (60 m, 1908)', diameterKm: 0.06, density: 3000 },
  { id: 'meteor', label: 'Meteor Crater (50 m de fer)', diameterKm: 0.05, density: 7800 },
  { id: 'chicxulub', label: 'Chicxulub (10 km, fin des dinosaures)', diameterKm: 10, density: 3000 },
  { id: 'vesta', label: 'Vesta (525 km)', diameterKm: 525, density: 3460 },
  { id: 'theia', label: 'Théia (taille de Mars, impact géant)', diameterKm: 6780, density: 3900 },
] as const;

const massSunFor = (diameterKm: number, density: number) => (density * (4 / 3) * Math.PI * ((diameterKm * 1000) / 2) ** 3) / SUN_MASS_KG;

/** Vitesse de simulation conseillée pour qu'un événement arrive en ~15 s. */
function speedFor(years: number): number {
  const options = [1, 10, 30, 100, 365.25, 1000, 3652.5, 10000];
  const ideal = (years * 365.25) / 15;
  return [...options].reverse().find((s) => s <= ideal) ?? 1;
}

function BodySelect({ bodies, value, onChange }: { bodies: Body[]; value: string; onChange: (id: string) => void }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {bodies.map((b) => (
        <option key={b.id} value={b.id}>
          {b.name}
        </option>
      ))}
    </select>
  );
}

export function EventsDialog({ sim, selectedId, onDone, onCancel }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);

  const selected = sim.getBody(selectedId);
  const stars = sim.stars.filter((s) => !s.star?.remnant);
  const allStars = sim.stars;
  const targets = sim.bodies.filter((b) => (b.kind === 'planet' || b.kind === 'moon') && !b.intruder);
  const movable = sim.bodies.filter((b) => b.kind !== 'planetesimal');

  const [tab, setTab] = useState<Tab>(selected && selected.kind !== 'star' ? 'impact' : 'intrus');
  const [error, setError] = useState<string | null>(null);

  // Intrus
  const [intruderType, setIntruderType] = useState<'etoile' | 'trou-noir' | 'planete'>('trou-noir');
  const [intruderClass, setIntruderClass] = useState<SpectralClass>('K');
  const [bhMass, setBhMass] = useState('10');
  const [rogueMass, setRogueMass] = useState('5');
  const [periapsis, setPeriapsis] = useState('5');
  const [intruderSpeed, setIntruderSpeed] = useState('30');
  const [inclination, setInclination] = useState('10');

  // Impact
  const defaultTarget = selected && targets.includes(selected) ? selected.id : (targets.find((b) => b.name === 'Terre') ?? targets[0])?.id ?? '';
  const [targetId, setTargetId] = useState(defaultTarget);
  const [impactor, setImpactor] = useState<(typeof IMPACTORS)[number]['id']>('chicxulub');
  const [impactSpeed, setImpactSpeed] = useState('20');

  // Étoile
  const [starId, setStarId] = useState((stars[0] ?? allStars[0])?.id ?? '');
  const [starAction, setStarAction] = useState<'geante-rouge' | 'supernova' | 'trou-noir' | 'expulsion'>('geante-rouge');
  const [giantYears, setGiantYears] = useState('20');
  const star = sim.getBody(starId);
  const [remnantMass, setRemnantMass] = useState(() => String(+Math.min(1.4, (star?.mass ?? 1) * 0.3).toPrecision(2)));
  const [kick, setKick] = useState('30');

  // Impulsion
  const [impulseId, setImpulseId] = useState(selected && selected.kind !== 'planetesimal' ? selected.id : (targets[0] ?? movable[0])?.id ?? '');
  const [deltaV, setDeltaV] = useState('5');
  const [direction, setDirection] = useState<ImpulseDirection>('prograde');

  const impactorInfo = IMPACTORS.find((i) => i.id === impactor)!;
  const target = sim.getBody(targetId);
  const impactorMass = massSunFor(impactorInfo.diameterKm, impactorInfo.density);
  const previewMt = target ? impactEnergyJ(target.mass, impactorMass, parse(impactSpeed) * KM_S) / MEGATON_J : NaN;

  const trigger = () => {
    setError(null);
    switch (tab) {
      case 'intrus': {
        const q = parse(periapsis);
        const v = parse(intruderSpeed);
        const inc = parse(inclination);
        if (!(q > 0)) return setError('La distance au plus près doit être positive.');
        if (!(v > 0 && v <= 2000)) return setError('La vitesse doit être comprise entre 0 et 2 000 km/s.');
        if (!(inc >= 0 && inc <= 180)) return setError("L'inclinaison doit être comprise entre 0 et 180°.");
        let mass: number;
        let name: string;
        if (intruderType === 'trou-noir') {
          mass = parse(bhMass);
          if (!(mass > 0)) return setError('La masse du trou noir doit être positive.');
          name = `Trou noir (${num(mass, 2)} M☉)`;
        } else if (intruderType === 'planete') {
          mass = (parse(rogueMass) * JUPITER_MASS_EARTH * EARTH_MASS_SUN);
          if (!(mass > 0)) return setError('La masse doit être positive.');
          name = 'Planète vagabonde';
        } else {
          mass = SPECTRAL_CLASSES[intruderClass].mass;
          name = `Étoile de passage (${intruderClass})`;
        }
        const id = newId('intrus');
        const eta = sim.launchIntruder({
          id,
          name,
          type: intruderType,
          mass,
          spectralClass: intruderClass,
          periapsisAu: q,
          speedKmS: v,
          i: inc,
          Omega: random(0, 360),
          omega: random(0, 360),
        });
        return onDone(id, speedFor(eta));
      }
      case 'impact': {
        const v = parse(impactSpeed);
        if (!target) return setError('Choisissez une cible.');
        if (!(v > 0 && v <= 100)) return setError('La vitesse doit être comprise entre 0 et 100 km/s (les astéroïdes frappent la Terre entre 11 et 72 km/s).');
        const id = newId('impacteur');
        sim.launchImpactor({
          id,
          targetId: target.id,
          name: impactorInfo.label.split(' (')[0],
          diameterKm: impactorInfo.diameterKm,
          mass: impactorMass,
          speedKmS: v,
          azimuth: random(0, 360),
          elevation: random(-20, 20),
        });
        return onDone(target.id, 1);
      }
      case 'etoile': {
        if (!star) return setError('Choisissez une étoile.');
        if (starAction === 'geante-rouge') {
          const years = parse(giantYears);
          if (!(years > 0)) return setError('La durée doit être positive.');
          sim.startRedGiant(star.id, years);
          return onDone(star.id, speedFor(years));
        }
        if (starAction === 'supernova') {
          const m = parse(remnantMass);
          if (!(m > 0 && m < star.mass)) return setError(`La masse restante doit être comprise entre 0 et ${num(star.mass)} M☉.`);
          sim.supernova(star.id, m);
          return onDone(star.id, null);
        }
        if (starAction === 'trou-noir') {
          sim.collapseToBlackHole(star.id);
          return onDone(star.id, null);
        }
        const dv = parse(kick);
        if (!(dv > 0)) return setError("L'impulsion doit être positive.");
        sim.applyImpulse(star.id, dv, 'perpendiculaire');
        return onDone(star.id, null);
      }
      case 'impulsion': {
        const dv = parse(deltaV);
        if (!(dv > 0 && dv <= 1000)) return setError("L'impulsion doit être comprise entre 0 et 1 000 km/s.");
        if (!sim.getBody(impulseId)) return setError('Choisissez un corps.');
        sim.applyImpulse(impulseId, dv, direction);
        return onDone(impulseId, null);
      }
    }
  };

  const tabs: [Tab, string][] = [
    ['intrus', '🕳️ Intrus'],
    ['impact', '☄️ Impact'],
    ['etoile', '🌟 Destin de l’étoile'],
    ['impulsion', '🚀 Impulsion'],
  ];
  const lightStar = star && star.mass < 8 && starAction === 'supernova';

  return (
    <dialog ref={ref} className="dialog dialog--wide" onCancel={onCancel} aria-labelledby="events-title">
      <form
        method="dialog"
        onSubmit={(e) => {
          e.preventDefault();
          trigger();
        }}
      >
        <h2 id="events-title">Événements</h2>
        <div className="tabs" role="tablist">
          {tabs.map(([id, label]) => (
            <button key={id} type="button" role="tab" aria-selected={tab === id} className={tab === id ? 'is-active' : ''} onClick={() => setTab(id)}>
              {label}
            </button>
          ))}
        </div>

        {tab === 'intrus' && (
          <div className="tab-panel">
            <p className="hint">
              Un corps venu d'ailleurs traverse le système sur une trajectoire hyperbolique. Son attraction dévie, capture ou éjecte
              les planètes ; un trou noir déchire celles qui passent trop près (forces de marée).
            </p>
            <label className="field">
              <span>Intrus</span>
              <select value={intruderType} onChange={(e) => setIntruderType(e.target.value as typeof intruderType)}>
                <option value="trou-noir">Trou noir</option>
                <option value="etoile">Étoile</option>
                <option value="planete">Planète vagabonde</option>
              </select>
            </label>
            <div className="field-grid">
              {intruderType === 'trou-noir' && (
                <label className="field">
                  <span>Masse (M☉)</span>
                  <input inputMode="decimal" value={bhMass} onChange={(e) => setBhMass(e.target.value)} />
                </label>
              )}
              {intruderType === 'etoile' && (
                <label className="field">
                  <span>Classe</span>
                  <select value={intruderClass} onChange={(e) => setIntruderClass(e.target.value as SpectralClass)}>
                    {SPECTRAL_ORDER.map((c) => (
                      <option key={c} value={c}>
                        {SPECTRAL_CLASSES[c].label}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {intruderType === 'planete' && (
                <label className="field">
                  <span>Masse (M♃)</span>
                  <input inputMode="decimal" value={rogueMass} onChange={(e) => setRogueMass(e.target.value)} />
                </label>
              )}
              <label className="field">
                <span>Distance au plus près (UA)</span>
                <input inputMode="decimal" value={periapsis} onChange={(e) => setPeriapsis(e.target.value)} />
              </label>
              <label className="field">
                <span>Vitesse d'arrivée (km/s)</span>
                <input inputMode="decimal" value={intruderSpeed} onChange={(e) => setIntruderSpeed(e.target.value)} />
              </label>
              <label className="field">
                <span>Inclinaison (°)</span>
                <input inputMode="decimal" value={inclination} onChange={(e) => setInclination(e.target.value)} />
              </label>
            </div>
            <p className="hint">Les étoiles voisines du Soleil se croisent à 20–50 km/s. La vitesse de simulation est ajustée pour voir le passage.</p>
          </div>
        )}

        {tab === 'impact' && (
          <div className="tab-panel">
            <p className="hint">
              Un impacteur fonce sur la cible. Le journal donne l'énergie libérée, la taille du cratère et les conséquences. Un impact
              géant peut former une lune avec les débris, comme celui qui a créé la nôtre.
            </p>
            {targets.length === 0 ? (
              <p className="error">Aucune planète ni lune à viser dans ce système.</p>
            ) : (
              <>
                <label className="field">
                  <span>Cible</span>
                  <BodySelect bodies={targets} value={targetId} onChange={setTargetId} />
                </label>
                <label className="field">
                  <span>Impacteur</span>
                  <select value={impactor} onChange={(e) => setImpactor(e.target.value as typeof impactor)}>
                    {IMPACTORS.map((i) => (
                      <option key={i.id} value={i.id}>
                        {i.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>Vitesse relative (km/s)</span>
                  <input inputMode="decimal" value={impactSpeed} onChange={(e) => setImpactSpeed(e.target.value)} />
                </label>
                {Number.isFinite(previewMt) && <p className="hint">Énergie attendue : environ {num(previewMt, 2)} mégatonnes de TNT.</p>}
              </>
            )}
          </div>
        )}

        {tab === 'etoile' && (
          <div className="tab-panel">
            {allStars.length === 0 ? (
              <p className="error">Aucune étoile dans ce système.</p>
            ) : (
              <>
                <label className="field">
                  <span>Étoile</span>
                  <BodySelect bodies={allStars} value={starId} onChange={setStarId} />
                </label>
                <fieldset className="choices">
                  <legend className="visually-hidden">Événement</legend>
                  {(
                    [
                      ['geante-rouge', 'Géante rouge', "L'étoile gonfle, engloutit les planètes proches et perd de la masse : les orbites des autres s'élargissent. Elle finit en naine blanche. (Le Soleil, dans 5 milliards d'années.)"],
                      ['supernova', 'Supernova', "L'étoile perd brutalement sa masse. Les planètes gardent leur vitesse mais ne sont plus assez retenues : au-delà de 50 % de masse perdue, une orbite circulaire se défait."],
                      ['trou-noir', 'Effondrement en trou noir (même masse)', 'Les orbites ne changent pas du tout : la gravité ne dépend que de la masse. Mais le système plonge dans le noir et le froid.'],
                      ['expulsion', "Expulser l'étoile", "On donne un coup de vitesse à l'étoile. Les planètes rapides (proches) la suivent ; les lentes (lointaines) restent derrière."],
                    ] as const
                  ).map(([id, label, help]) => (
                    <label key={id} className={`choice ${starAction === id ? 'is-active' : ''}`}>
                      <input type="radio" name="star-action" checked={starAction === id} onChange={() => setStarAction(id)} />
                      <span>
                        <strong>{label}</strong>
                        <span className="hint">{help}</span>
                      </span>
                    </label>
                  ))}
                </fieldset>
                {star?.star?.remnant && starAction !== 'expulsion' && (
                  <p className="error">Cette étoile est déjà un astre mort ; seule l'expulsion reste possible.</p>
                )}
                {starAction === 'geante-rouge' && (
                  <label className="field">
                    <span>Durée de la phase (années simulées, accélérée)</span>
                    <input inputMode="decimal" value={giantYears} onChange={(e) => setGiantYears(e.target.value)} />
                  </label>
                )}
                {starAction === 'supernova' && (
                  <>
                    <label className="field">
                      <span>Masse restante (M☉) — sur {num(star?.mass ?? 0)} M☉</span>
                      <input inputMode="decimal" value={remnantMass} onChange={(e) => setRemnantMass(e.target.value)} />
                    </label>
                    <p className="hint">Moins de 1,2 M☉ : naine blanche · jusqu'à 3 M☉ : étoile à neutrons · au-delà : trou noir.</p>
                    {lightStar && <p className="hint">Dans la réalité, il faut au moins 8 M☉ pour exploser ainsi : ici, on joue au « et si ? ».</p>}
                  </>
                )}
                {starAction === 'expulsion' && (
                  <label className="field">
                    <span>Impulsion (km/s)</span>
                    <input inputMode="decimal" value={kick} onChange={(e) => setKick(e.target.value)} />
                  </label>
                )}
              </>
            )}
          </div>
        )}

        {tab === 'impulsion' && (
          <div className="tab-panel">
            <p className="hint">
              Un coup de vitesse, comme un moteur de fusée géant. Dans le sens du mouvement, l'orbite s'agrandit ; au-delà de la vitesse
              de libération (+41 % de la vitesse orbitale), le corps quitte le système. Les lunes suivent leur planète.
            </p>
            <label className="field">
              <span>Corps</span>
              <BodySelect bodies={movable} value={impulseId} onChange={setImpulseId} />
            </label>
            <div className="field-grid">
              <label className="field">
                <span>Impulsion (km/s)</span>
                <input inputMode="decimal" value={deltaV} onChange={(e) => setDeltaV(e.target.value)} />
              </label>
              <label className="field">
                <span>Direction</span>
                <select value={direction} onChange={(e) => setDirection(e.target.value as ImpulseDirection)}>
                  <option value="prograde">Dans le sens du mouvement</option>
                  <option value="retrograde">Contre le mouvement</option>
                  <option value="exterieur">Vers l'extérieur</option>
                  <option value="interieur">Vers l'intérieur</option>
                  <option value="perpendiculaire">Perpendiculaire à l'orbite</option>
                </select>
              </label>
            </div>
          </div>
        )}

        {error && <p className="error">{error}</p>}
        <div className="row">
          <button
            type="submit"
            className="primary"
            disabled={(tab === 'impact' && targets.length === 0) || (tab === 'etoile' && (!star || (!!star.star?.remnant && starAction !== 'expulsion')))}
          >
            Déclencher
          </button>
          <button type="button" onClick={onCancel}>
            Annuler
          </button>
        </div>
      </form>
    </dialog>
  );
}
