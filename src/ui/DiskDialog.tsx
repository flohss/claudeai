import { useEffect, useRef, useState } from 'react';
import { SPECTRAL_CLASSES, SPECTRAL_ORDER, snowLine } from '../physics/stars';
import type { SpectralClass } from '../physics/types';
import { defaultDiskParams, type DiskParams } from '../sim/disk';
import { num } from './format';

interface Props {
  onStart: (params: DiskParams) => void;
  onCancel: () => void;
}

const parse = (s: string) => Number(s.replace(',', '.'));

/** Paramètres du disque protoplanétaire avant de lancer la formation. */
export function DiskDialog({ onStart, onCancel }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [cls, setCls] = useState<SpectralClass>('G');
  const [values, setValues] = useState(() => toStrings(defaultDiskParams('G')));
  const [gas, setGas] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    ref.current?.showModal();
  }, []);

  const changeClass = (c: SpectralClass) => {
    setCls(c);
    setValues(toStrings(defaultDiskParams(c)));
  };
  const set = (k: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) => setValues({ ...values, [k]: e.target.value });
  const snow = snowLine(SPECTRAL_CLASSES[cls].luminosity);

  return (
    <dialog ref={ref} className="dialog" onCancel={onCancel} aria-labelledby="disk-title">
      <form
        method="dialog"
        onSubmit={(e) => {
          e.preventDefault();
          const p: DiskParams = {
            ...defaultDiskParams(cls),
            count: Math.round(parse(values.count)),
            massEarth: parse(values.massEarth),
            innerAu: parse(values.innerAu),
            outerAu: parse(values.outerAu),
            accretionScale: parse(values.accretionScale),
            gas,
          };
          if (!(p.count >= 10 && p.count <= 400)) return setError('Choisissez entre 10 et 400 planétésimaux.');
          if (!(p.massEarth > 0)) return setError('La masse du disque doit être positive.');
          if (!(p.innerAu > 0 && p.outerAu > p.innerAu * 1.2)) return setError("Le bord extérieur doit être nettement au-delà du bord intérieur.");
          if (!(p.accretionScale >= 1 && p.accretionScale <= 3000)) return setError("Le facteur d'accrétion doit être compris entre 1 et 3000.");
          onStart(p);
        }}
      >
        <h2 id="disk-title">Disque protoplanétaire</h2>
        <p className="hint">
          Des centaines de petits corps tournent autour d'une jeune étoile. En se percutant, ils fusionnent et grossissent : des
          protoplanètes apparaissent, puis des planètes. Au-delà de la ligne des glaces ({num(snow)} UA ici), la glace rend le disque
          plus massif et les noyaux assez gros capturent le gaz pour devenir des géantes.
        </p>
        <label className="field">
          <span>Étoile</span>
          <select value={cls} onChange={(e) => changeClass(e.target.value as SpectralClass)}>
            {SPECTRAL_ORDER.map((c) => (
              <option key={c} value={c}>
                {SPECTRAL_CLASSES[c].label}
              </option>
            ))}
          </select>
        </label>
        <div className="field-grid">
          <label className="field">
            <span>Planétésimaux</span>
            <input inputMode="numeric" value={values.count} onChange={set('count')} />
          </label>
          <label className="field">
            <span>Masse solide (M⊕)</span>
            <input inputMode="decimal" value={values.massEarth} onChange={set('massEarth')} />
          </label>
          <label className="field">
            <span>Bord intérieur (UA)</span>
            <input inputMode="decimal" value={values.innerAu} onChange={set('innerAu')} />
          </label>
          <label className="field">
            <span>Bord extérieur (UA)</span>
            <input inputMode="decimal" value={values.outerAu} onChange={set('outerAu')} />
          </label>
          <label className="field">
            <span>Facteur d'accrétion</span>
            <input inputMode="numeric" value={values.accretionScale} onChange={set('accretionScale')} />
          </label>
          <label className="check field-check">
            <input type="checkbox" checked={gas} onChange={(e) => setGas(e.target.checked)} /> Gaz (formation de géantes)
          </label>
        </div>
        <p className="hint">
          Modèle accéléré : la formation réelle prend des millions d'années. Ici, le rayon de capture des corps est multiplié par le
          facteur d'accrétion et le gaz se dissipe après 300 ans, pour voir le résultat en quelques minutes. Plus de planétésimaux,
          c'est plus réaliste mais plus lent.
        </p>
        {error && <p className="error">{error}</p>}
        <div className="row">
          <button type="submit" className="primary">
            Lancer la formation
          </button>
          <button type="button" onClick={onCancel}>
            Annuler
          </button>
        </div>
      </form>
    </dialog>
  );
}

function toStrings(p: DiskParams) {
  const fr = (n: number) => String(n).replace('.', ',');
  return { count: String(p.count), massEarth: fr(p.massEarth), innerAu: fr(p.innerAu), outerAu: fr(p.outerAu), accretionScale: String(p.accretionScale) };
}
