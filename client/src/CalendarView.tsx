import type { CalendarYear } from "./types";
import { MONTH_NAMES, daysInMonth, firstWeekdayOfMonth } from "./types";

interface Props {
  year: number;
  yearData: CalendarYear;
  selectedMonth: number;
  selectedDay: number | null;
  onSelectMonth: (month: number) => void;
  onSelectDay: (day: number) => void;
}

const WEEKDAY_LABELS = ["Lu", "Ma", "Me", "Je", "Ve", "Sa", "Di"];

export default function CalendarView({
  year,
  yearData,
  selectedMonth,
  selectedDay,
  onSelectMonth,
  onSelectDay,
}: Props) {
  const monthKey = String(selectedMonth).padStart(2, "0");
  const monthData = yearData[monthKey] ?? {};
  const totalDays = daysInMonth(year, selectedMonth);
  const leadingBlanks = firstWeekdayOfMonth(year, selectedMonth);

  const monthsWithData = new Set(
    Object.keys(yearData).map((m) => Number(m))
  );

  const cells: (number | null)[] = [
    ...Array(leadingBlanks).fill(null),
    ...Array.from({ length: totalDays }, (_, i) => i + 1),
  ];

  return (
    <div className="calendar-view">
      <div className="month-tabs">
        {MONTH_NAMES.map((name, idx) => {
          const monthNum = idx + 1;
          const hasData = monthsWithData.has(monthNum);
          return (
            <button
              key={name}
              className={`month-tab ${monthNum === selectedMonth ? "active" : ""} ${hasData ? "has-data" : ""}`}
              disabled={!hasData}
              onClick={() => onSelectMonth(monthNum)}
              title={hasData ? name : `${name} — aucune archive`}
            >
              {name.slice(0, 3)}
            </button>
          );
        })}
      </div>

      <div className="weekday-row">
        {WEEKDAY_LABELS.map((w) => (
          <div key={w} className="weekday-label">{w}</div>
        ))}
      </div>

      <div className="day-grid">
        {cells.map((day, idx) => {
          if (day === null) {
            return <div key={`blank-${idx}`} className="day-cell blank" />;
          }
          const dayKey = String(day).padStart(2, "0");
          const dayData = monthData[dayKey];
          const hasSnapshots = !!dayData;
          const isSelected = selectedDay === day;
          return (
            <button
              key={day}
              className={`day-cell ${hasSnapshots ? "has-snapshots" : "empty"} ${isSelected ? "selected" : ""}`}
              disabled={!hasSnapshots}
              onClick={() => onSelectDay(day)}
              title={hasSnapshots ? `${dayData.timestamps.length} archive(s)` : "Aucune archive"}
            >
              {day}
            </button>
          );
        })}
      </div>
    </div>
  );
}
