import { useRef } from 'react';

export type PresetId = 'solaire' | 'kepler16' | 'centaure' | 'aleatoire' | 'disque' | 'vide';

const PRESETS: [PresetId, string][] = [
  ['solaire', 'Système solaire'],
  ['kepler16', 'Kepler-16 — binaire serrée'],
  ['centaure', 'Alpha du Centaure — binaire large'],
  ['aleatoire', 'Système aléatoire'],
  ['disque', 'Disque protoplanétaire…'],
  ['vide', 'Étoile seule'],
];

interface Props {
  systemName: string;
  onPreset: (id: PresetId) => void;
  onReset: () => void;
  onSave: () => void;
  onLoad: (file: File) => void;
  onFrame: () => void;
  onShare: () => void;
  onEvents: () => void;
}

export function TopBar({ systemName, onPreset, onReset, onSave, onLoad, onFrame, onShare, onEvents }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  return (
    <header className="topbar">
      <div className="brand">
        <h1>Simulateur de système solaire</h1>
        <span className="system-name">{systemName}</span>
      </div>
      <nav className="actions">
        <label className="preset-select">
          <span className="visually-hidden">Préréglage</span>
          <select
            value=""
            onChange={(e) => {
              if (e.target.value) onPreset(e.target.value as PresetId);
            }}
          >
            <option value="">Nouveau système…</option>
            {PRESETS.map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="events-button" onClick={onEvents} title="Trou noir, impact, supernova, géante rouge…">
          ⚡ Événements
        </button>
        <div className="group">
          <button type="button" onClick={onReset} title="Revenir à l'état chargé">
            ↺ Réinitialiser
          </button>
          <button type="button" onClick={onFrame} title="Recentrer la caméra">
            ⌖ Recentrer
          </button>
        </div>
        <div className="group">
          <button type="button" className="primary" onClick={onShare}>
            🔗 Partager
          </button>
          <button type="button" onClick={onSave}>
            Sauvegarder
          </button>
          <button type="button" onClick={() => fileRef.current?.click()}>
            Charger…
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) onLoad(file);
              e.target.value = '';
            }}
          />
        </div>
      </nav>
    </header>
  );
}
