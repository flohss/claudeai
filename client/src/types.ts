export interface CalendarDay {
  timestamps: string[];
}

export type CalendarMonth = Record<string, CalendarDay>;
export type CalendarYear = Record<string, CalendarMonth>;
export type Calendar = Record<string, CalendarYear>;

export interface SnapshotsResponse {
  url: string;
  total: number;
  calendar: Calendar;
}

export const MONTH_NAMES = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
];

export function formatTimestamp(ts: string): string {
  const year = ts.slice(0, 4);
  const month = ts.slice(4, 6);
  const day = ts.slice(6, 8);
  const hour = ts.slice(8, 10);
  const minute = ts.slice(10, 12);
  const second = ts.slice(12, 14);
  return `${day}/${month}/${year} ${hour}:${minute}:${second}`;
}

export function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate();
}

export function firstWeekdayOfMonth(year: number, month: number): number {
  const jsDay = new Date(year, month - 1, 1).getDay();
  return (jsDay + 6) % 7;
}
