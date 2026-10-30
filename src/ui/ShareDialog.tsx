import { useEffect, useRef, useState } from 'react';
import { LONG_LINK_CHARS } from '../sim/share';
import { num } from './format';

interface Props {
  url: string;
  onClose: () => void;
}

/** Affiche le lien de partage et le copie dans le presse-papiers. */
export function ShareDialog({ url, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [copied, setCopied] = useState<boolean | null>(null);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      // Presse-papiers refusé (contexte non sécurisé, permission) : sélection manuelle.
      inputRef.current?.select();
      setCopied(false);
    }
  };

  useEffect(() => {
    ref.current?.showModal();
    inputRef.current?.select();
    void copy();
  }, []);

  return (
    <dialog ref={ref} className="dialog" onCancel={onClose} onClose={onClose} aria-labelledby="share-title">
      <h2 id="share-title">Partager ce système</h2>
      <p className="hint">
        Le lien contient tout le système dans son état actuel : la personne qui l'ouvre le retrouve exactement, sans compte ni
        installation. Rien n'est envoyé à un serveur.
      </p>
      <div className="with-button">
        <input ref={inputRef} readOnly value={url} aria-label="Lien de partage" onFocus={(e) => e.target.select()} />
        <button type="button" onClick={copy}>
          Copier
        </button>
      </div>
      <p className="hint" role="status">
        {copied === true && '✓ Lien copié dans le presse-papiers.'}
        {copied === false && 'Copie automatique impossible : le lien est sélectionné, copiez-le avec Ctrl+C (⌘+C).'}
      </p>
      {url.length > LONG_LINK_CHARS && (
        <p className="warning-box">
          Ce lien est long ({num(url.length, 2)} caractères) : certaines messageries risquent de le couper. Pour un gros système,
          « Sauvegarder » produit un fichier à envoyer à la place.
        </p>
      )}
      <div className="row">
        <button type="button" className="primary" onClick={onClose}>
          Fermer
        </button>
      </div>
    </dialog>
  );
}
