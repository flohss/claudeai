import { DAYS_PER_YEAR } from '../physics/units';

export { num } from '../format';
import { num } from '../format';

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
