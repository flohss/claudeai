import { useRef } from 'react';

interface Props {
  systemName: string;
  onSolar: () => void;
  onRandom: () => void;
  onEmpty: () => void;
  onReset: () => void;
  onSave: () => void;
  onLoad: (file: File) => void;
  onFrame: () => void;
}

export function TopBar({ systemName, onSolar, onRandom, onEmpty, onReset, onSave, onLoad, onFrame }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  return (
    <header className="topbar">
      <div className="brand">
        <h1>Simulateur de système solaire</h1>
        <span className="system-name">{systemName}</span>
      </div>
      <nav className="actions">
        <div className="group" role="group" aria-label="Préréglages">
          <button type="button" onClick={onSolar}>Système solaire</button>
          <button type="button" onClick={onRandom}>🎲 Aléatoire</button>
          <button type="button" onClick={onEmpty}>Étoile seule</button>
        </div>
        <div className="group">
          <button type="button" onClick={onReset} title="Revenir à l'état chargé">↺ Réinitialiser</button>
          <button type="button" onClick={onFrame} title="Recentrer la caméra">⌖ Recentrer</button>
        </div>
        <div className="group">
          <button type="button" onClick={onSave}>Sauvegarder</button>
          <button type="button" onClick={() => fileRef.current?.click()}>Charger…</button>
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
