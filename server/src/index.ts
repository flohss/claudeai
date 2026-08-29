import express from "express";
import cors from "cors";

const app = express();
app.use(cors());

const CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx";

interface CalendarDay {
  timestamps: string[];
}

type CalendarMonth = Record<string, CalendarDay>; // day -> { timestamps }
type CalendarYear = Record<string, CalendarMonth>; // month -> CalendarMonth
type Calendar = Record<string, CalendarYear>; // year -> CalendarYear

function normalizeUrl(raw: string): string {
  const trimmed = raw.trim();
  if (!/^https?:\/\//i.test(trimmed)) {
    return `https://${trimmed}`;
  }
  return trimmed;
}

app.get("/api/snapshots", async (req, res) => {
  const rawUrl = req.query.url;
  if (typeof rawUrl !== "string" || rawUrl.trim() === "") {
    res.status(400).json({ error: "Missing required 'url' query parameter." });
    return;
  }

  const targetUrl = normalizeUrl(rawUrl);
  const cdxUrl = new URL(CDX_ENDPOINT);
  cdxUrl.searchParams.set("url", targetUrl);
  cdxUrl.searchParams.set("output", "json");
  cdxUrl.searchParams.set("fl", "timestamp,statuscode");
  cdxUrl.searchParams.set("collapse", "timestamp:8");
  cdxUrl.searchParams.set("filter", "statuscode:200");

  try {
    const upstream = await fetch(cdxUrl.toString());
    if (!upstream.ok) {
      res.status(502).json({ error: `Archive.org returned status ${upstream.status}` });
      return;
    }

    const rows = (await upstream.json()) as string[][];
    const calendar: Calendar = {};
    let total = 0;

    for (const row of rows.slice(1)) {
      const timestamp = row[0];
      if (!timestamp || timestamp.length < 8) continue;
      const year = timestamp.slice(0, 4);
      const month = timestamp.slice(4, 6);
      const day = timestamp.slice(6, 8);

      calendar[year] ??= {};
      calendar[year][month] ??= {};
      calendar[year][month][day] ??= { timestamps: [] };
      calendar[year][month][day].timestamps.push(timestamp);
      total += 1;
    }

    res.json({ url: targetUrl, total, calendar });
  } catch (err) {
    res.status(500).json({ error: "Failed to reach archive.org", detail: (err as Error).message });
  }
});

const PORT = process.env.PORT ? Number(process.env.PORT) : 3001;
app.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
});
