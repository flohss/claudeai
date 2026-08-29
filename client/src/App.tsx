import { useMemo, useState } from "react";
import CalendarView from "./CalendarView";
import type { SnapshotsResponse } from "./types";
import { formatTimestamp } from "./types";
import "./App.css";

export default function App() {
  const [urlInput, setUrlInput] = useState("");
  const [data, setData] = useState<SnapshotsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<number>(1);
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [selectedTimestamp, setSelectedTimestamp] = useState<string | null>(null);

  const years = useMemo(() => {
    if (!data) return [];
    return Object.keys(data.calendar).map(Number).sort((a, b) => a - b);
  }, [data]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setLoading(true);
    setError(null);
    setData(null);
    setSelectedYear(null);
    setSelectedDay(null);
    setSelectedTimestamp(null);

    try {
      const res = await fetch(`/api/snapshots?url=${encodeURIComponent(urlInput.trim())}`);
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.error ?? "Erreur inconnue");
      }
      const snapshotData = json as SnapshotsResponse;
      setData(snapshotData);

      const availableYears = Object.keys(snapshotData.calendar).map(Number).sort((a, b) => a - b);
      if (availableYears.length > 0) {
        const latestYear = availableYears[availableYears.length - 1];
        setSelectedYear(latestYear);
        const months = Object.keys(snapshotData.calendar[latestYear]).map(Number).sort((a, b) => a - b);
        setSelectedMonth(months[months.length - 1] ?? 1);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const dayTimestamps = useMemo(() => {
    if (!data || selectedYear === null || selectedDay === null) return [];
    const yearData = data.calendar[String(selectedYear)];
    const monthData = yearData?.[String(selectedMonth).padStart(2, "0")];
    const dayData = monthData?.[String(selectedDay).padStart(2, "0")];
    return dayData?.timestamps.slice().sort() ?? [];
  }, [data, selectedYear, selectedMonth, selectedDay]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Archives dans le temps</h1>
        <p className="subtitle">Naviguez dans l'historique archivé d'une page web par date</p>
      </header>

      <form className="search-form" onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="Entrez une URL, ex: example.com"
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? "Recherche..." : "Rechercher"}
        </button>
      </form>

      {error && <div className="error-banner">{error}</div>}

      {data && years.length === 0 && (
        <div className="empty-state">Aucune archive trouvée pour cette URL.</div>
      )}

      {data && years.length > 0 && selectedYear !== null && (
        <div className="results">
          <div className="year-tabs">
            {years.map((year) => (
              <button
                key={year}
                className={`year-tab ${year === selectedYear ? "active" : ""}`}
                onClick={() => {
                  setSelectedYear(year);
                  setSelectedDay(null);
                  setSelectedTimestamp(null);
                  const months = Object.keys(data.calendar[year]).map(Number).sort((a, b) => a - b);
                  setSelectedMonth(months[months.length - 1] ?? 1);
                }}
              >
                {year}
              </button>
            ))}
          </div>

          <CalendarView
            year={selectedYear}
            yearData={data.calendar[String(selectedYear)]}
            selectedMonth={selectedMonth}
            selectedDay={selectedDay}
            onSelectMonth={(month) => {
              setSelectedMonth(month);
              setSelectedDay(null);
              setSelectedTimestamp(null);
            }}
            onSelectDay={(day) => {
              setSelectedDay(day);
              setSelectedTimestamp(null);
            }}
          />

          {dayTimestamps.length > 0 && (
            <div className="timestamp-list">
              <h3>Instantanés du {selectedDay}/{String(selectedMonth).padStart(2, "0")}/{selectedYear}</h3>
              <div className="timestamp-chips">
                {dayTimestamps.map((ts) => (
                  <button
                    key={ts}
                    className={`timestamp-chip ${selectedTimestamp === ts ? "active" : ""}`}
                    onClick={() => setSelectedTimestamp(ts)}
                  >
                    {formatTimestamp(ts).split(" ")[1]}
                  </button>
                ))}
              </div>
            </div>
          )}

          {selectedTimestamp && (
            <div className="viewer">
              <div className="viewer-toolbar">
                <span>Affichage de l'archive du {formatTimestamp(selectedTimestamp)}</span>
                <a
                  href={`https://web.archive.org/web/${selectedTimestamp}/${data.url}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Ouvrir dans un nouvel onglet ↗
                </a>
              </div>
              <iframe
                title="Archive snapshot"
                src={`https://web.archive.org/web/${selectedTimestamp}/${data.url}`}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
