import { SPECTRAL_CLASSES, SPECTRAL_ORDER, habitableZone, snowLine } from '../physics/stars';
import type { Body, SpectralClass } from '../physics/types';
import { num } from './format';

interface Props {
  star: Body;
  onChangeClass: (c: SpectralClass) => void;
}

export function StarPanel({ star, onChangeClass }: Props) {
  const props = star.star!;
  const hz = habitableZone(props.luminosity);
  return (
    <section className="panel">
      <h2>Étoile</h2>
      <label className="field">
        <span>Classe spectrale</span>
        <select value={props.spectralClass} onChange={(e) => onChangeClass(e.target.value as SpectralClass)}>
          {SPECTRAL_ORDER.map((c) => (
            <option key={c} value={c}>
              {SPECTRAL_CLASSES[c].label}
            </option>
          ))}
        </select>
      </label>
      <p className="hint">{SPECTRAL_CLASSES[props.spectralClass].description}</p>
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
      <p className="hint">Changer de classe recalcule toutes les orbites autour de la nouvelle masse.</p>
    </section>
  );
}
