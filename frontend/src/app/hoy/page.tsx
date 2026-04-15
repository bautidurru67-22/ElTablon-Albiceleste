"use client";

import { useEffect, useMemo, useState } from "react";

type Match = {
  id: string;
  sport: string;
  competition: string;
  home_team: string;
  away_team: string;
  home_score?: number | null;
  away_score?: number | null;
  status: string;
  minute?: string | null;
  start_time?: string | null;
  tv?: string | null;
  category?: string;
};

type Section = {
  key: string;
  title: string;
  items: Match[];
};

type HoyData = {
  date: string;
  updated_at: string;
  matches: Match[];
  sections: Section[];
  stats: {
    live: number;
    upcoming: number;
    finished: number;
    total: number;
  };
  summary?: {
    live: number;
    upcoming: number;
    finished: number;
    total: number;
  };
  by_sport?: Record<string, number>;
};

export default function HoyPage() {
  const [data, setData] = useState<HoyData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/proxy/api/hoy", { cache: "no-store" })
      .then(async (res) => {
        const json = await res.json();
        if (!res.ok || !json?.ok || !json?.data) {
          throw new Error(json?.error || "No se pudo cargar la agenda");
        }
        setData(json.data);
      })
      .catch(() => setError("No se pudo cargar la agenda"));
  }, []);

  const summary = useMemo(() => {
    if (!data) {
      return { live: 0, upcoming: 0, finished: 0, total: 0 };
    }
    return data.summary || data.stats || { live: 0, upcoming: 0, finished: 0, total: 0 };
  }, [data]);

  if (error) {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: 20 }}>
        {error}
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: 20 }}>
        Cargando agenda...
      </div>
    );
  }

  const sections = data.sections || [];
  const liveMatches = (data.matches || []).filter((m) => m.status === "live");

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 20 }}>
      <h1 style={{ fontSize: 24, fontWeight: "bold", marginBottom: 4 }}>
        HOY - DONDE JUEGA ARGENTINA
      </h1>

      <div style={{ fontSize: 12, marginBottom: 16, lineHeight: 1.2 }}>
        <div>Actualizado: {formatUpdatedAt(data.updated_at)}</div>
        <div>{formatDateEs(data.date)}</div>
      </div>

      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <SectionBox
            title="EN VIVO"
            bg="#f8eaea"
            matches={liveMatches}
            emptyText="Sin partidos en vivo."
          />

          {sections.map((section) => (
            <SectionBox
              key={section.key}
              title={mapTitle(section.key, section.title)}
              bg="#efefef"
              matches={section.items || []}
            />
          ))}
        </div>

        <div style={{ width: 180 }}>
          <SidebarBox title="RESUMEN DE HOY">
            <SidebarRow label="En vivo" value={summary.live} />
            <SidebarRow label="Próximos" value={summary.upcoming} />
            <SidebarRow label="Finalizados" value={summary.finished} />
            <SidebarRow label="Total" value={summary.total} />
          </SidebarBox>

          {!!data.by_sport && Object.keys(data.by_sport).length > 0 && (
            <SidebarBox title="POR DEPORTE">
              {Object.entries(data.by_sport).map(([key, value]) => (
                <SidebarRow key={key} label={key} value={value} />
              ))}
            </SidebarBox>
          )}
        </div>
      </div>
    </div>
  );
}

function SectionBox({
  title,
  matches,
  bg,
  emptyText,
}: {
  title: string;
  matches: Match[];
  bg: string;
  emptyText?: string;
}) {
  if (!matches?.length && !emptyText) return null;

  return (
    <div style={{ border: "1px solid #d7d7d7", marginBottom: 10, background: "#fff" }}>
      <div style={{ background: bg, padding: "6px 8px", fontWeight: "bold" }}>
        {title}
      </div>

      {!matches?.length ? (
        <div style={{ padding: 10 }}>{emptyText}</div>
      ) : (
        matches.map((m, i) => <MatchRow key={`${m.id}-${i}`} match={m} />)
      )}
    </div>
  );
}

function MatchRow({ match }: { match: Match }) {
  const scoreVisible =
    match.home_score !== null &&
    match.home_score !== undefined &&
    match.away_score !== null &&
    match.away_score !== undefined;

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 12,
        padding: 10,
        borderTop: "1px solid #ececec",
      }}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 12, color: "#666", marginBottom: 2 }}>
          {match.competition || "Fútbol"}
        </div>
        <div style={{ fontSize: 13 }}>
          {match.home_team} vs {match.away_team}
        </div>
      </div>

      <div style={{ textAlign: "right", minWidth: 60 }}>
        <div style={{ fontWeight: "bold" }}>
          {scoreVisible ? `${match.home_score} - ${match.away_score}` : "-"}
        </div>
        <div style={{ fontSize: 12, color: "#666" }}>
          {match.status === "live" ? (match.minute || "EN VIVO") : (match.start_time || "-")}
        </div>
      </div>
    </div>
  );
}

function SidebarBox({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ border: "1px solid #d7d7d7", marginBottom: 10, background: "#fff" }}>
      <div style={{ padding: "6px 8px", fontWeight: "bold" }}>{title}</div>
      <div style={{ padding: "0 8px 8px 8px" }}>{children}</div>
    </div>
  );
}

function SidebarRow({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
      <span>{label}:</span>
      <span>{value}</span>
    </div>
  );
}

function mapTitle(key: string, fallback: string) {
  if (key === "selecciones") return "Selecciones nacionales";
  if (key === "ligas_locales") return "Ligas locales";
  if (key === "exterior") return "Argentinos en el exterior";
  if (key === "motorsport") return "Motorsport argentino";
  return fallback || key;
}

function formatDateEs(dateStr: string) {
  try {
    const date = new Date(`${dateStr}T12:00:00`);
    return date.toLocaleDateString("es-AR", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
  } catch {
    return dateStr;
  }
}

function formatUpdatedAt(updatedAt: string) {
  try {
    const date = new Date(updatedAt);
    return date.toLocaleString("es-AR", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return updatedAt;
  }
}
