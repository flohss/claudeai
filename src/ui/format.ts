import { DAYS_PER_YEAR } from '../physics/units';

const formatters = new Map<number, Intl.NumberFormat>();

/** Nombre au format français avec `digits` chiffres significatifs. */
export function num(value: number, digits = 3): string {
  if (!Number.isFinite(value)) return '—';
  let f = formatters.get(digits);
  if (!f) {
    f = new Intl.NumberFormat('fr-FR', { maximumSignificantDigits: digits });
    formatters.set(digits, f);
  }
  const abs = Math.abs(value);
  if (abs !== 0 && (abs < 1e-3 || abs >= 1e7)) {
    const [m, e] = value.toExponential(digits - 1).split('e');
    return `${m.replace('.', ',')} × 10${superscript(Number(e))}`;
  }
  return f.format(value);
}

const SUP: Record<string, string> = { '-': '⁻', '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹' };
const superscript = (n: number) => String(n).split('').map((c) => SUP[c] ?? c).join('');

/** Durée exprimée en années → texte lisible (heures, jours ou années). */
export function duration(years: number): string {
  const days = years * DAYS_PER_YEAR;
  if (days < 2) return `${num(days * 24)} h`;
  if (days < 2 * DAYS_PER_YEAR) return `${num(days)} jours`;
  return `${num(years)} ans`;
}

/** Temps écoulé depuis le début de la simulation. */
export function elapsed(years: number): string {
  const whole = Math.floor(years);
  const days = Math.floor((years - whole) * DAYS_PER_YEAR);
  return `${whole} an${whole > 1 ? 's' : ''}, ${days} j`;
}

export function speedLabel(daysPerSecond: number): string {
  if (daysPerSecond < DAYS_PER_YEAR) return `${num(daysPerSecond, 2)} j/s`;
  const years = daysPerSecond / DAYS_PER_YEAR;
  return `${num(years, 2)} an${years >= 2 ? 's' : ''}/s`;
}
