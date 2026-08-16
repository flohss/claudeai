import { useEffect, useState } from 'react';

// Palette "papier / encre" (clair) et "ardoise / craie" (sombre). Les deux
// jeux de couleurs de tracé par défaut sont pensés pour rester lisibles sur
// leur fond respectif (encre foncée sur papier clair, craie claire sur
// ardoise sombre).

export const PALETTES = {
  light: {
    appBg: '#F3EFE6',
    toolbarBg: '#FBF9F3',
    panelBg: '#FFFFFF',
    border: '#E3DCC9',
    text: '#2A2620',
    textMuted: '#A19A85',
    activeBg: '#EAE3D1',
    hoverBg: '#F1EADA',
    paperBg: '#F3EFE6',
    paperLine: '#E4DCC8',
    paperMargin: '#D8B9A8',
    accent: '#1F6F63',
    accentText: '#FFFFFF',
    danger: '#A6432E',
    marqueeFill: 'rgba(31, 111, 99, 0.08)',
    marqueeStroke: '#1F6F63',
    penColors: [
      { name: 'Graphite', hex: '#2A2620' },
      { name: 'Rouille', hex: '#A6432E' },
      { name: 'Sarcelle', hex: '#1F6F63' },
      { name: 'Indigo', hex: '#2C3E66' },
      { name: 'Mousse', hex: '#4B6A45' },
    ],
  },
  dark: {
    appBg: '#1C1B18',
    toolbarBg: '#242320',
    panelBg: '#242320',
    border: '#3A382F',
    text: '#EDE7D9',
    textMuted: '#8B8676',
    activeBg: '#33312A',
    hoverBg: '#2B2A24',
    paperBg: '#211F1B',
    paperLine: '#332F27',
    paperMargin: '#5A4030',
    accent: '#4FBFA8',
    accentText: '#12211D',
    danger: '#E08064',
    marqueeFill: 'rgba(79, 191, 168, 0.12)',
    marqueeStroke: '#4FBFA8',
    penColors: [
      { name: 'Craie', hex: '#EDE7D9' },
      { name: 'Corail', hex: '#E08064' },
      { name: 'Sarcelle', hex: '#4FBFA8' },
      { name: 'Pervenche', hex: '#7C93D6' },
      { name: 'Sauge', hex: '#8FBF7A' },
    ],
  },
};

const THEME_KEY = 'atelier-theme-v1';

export function useTheme() {
  const [pref, setPref] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) || 'system';
    } catch {
      return 'system';
    }
  });
  const [systemDark, setSystemDark] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
      : false
  );

  useEffect(() => {
    if (!window.matchMedia) return;
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = (e) => setSystemDark(e.matches);
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(THEME_KEY, pref);
    } catch {
      // stockage indisponible — on ignore.
    }
  }, [pref]);

  const resolved = pref === 'system' ? (systemDark ? 'dark' : 'light') : pref;
  return { pref, setPref, resolved, colors: PALETTES[resolved] };
}
