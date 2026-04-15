"use client";

import { useEffect, useState } from "react";

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
};

export default function HoyPage() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/proxy/api/hoy", { cache: "no-store" })
      .then((r) => r.json())
      .then((json) => {
        setMatches(json?.data?.matches || []);
        setLoading(false);
      });
  }, []);

  const live = matches.filter((m) => m.status === "live");
  const upcoming = matches.filter((m) => m.status === "upcoming");
  const finished = matches.filter((m) => m.status === "finished");

  const hero =
    live[0] || upcoming[0] || matches[0];

  if (loading) return <div style={{ padding: 20 }}>Cargando...</div>;

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 20 }}>

      {/* HERO */}
      {hero && (
        <div
          style={{
            background: "#eaf3ff",
            padding: 20,
            borderRadius: 10,
            marginBottom: 20,
            border: "1px solid #d0e2ff"
          }}
        >
          <div style={{ fontSize: 12, color: "#0070f3", marginBottom: 6 }}>
            {hero.status === "live" ? "EN VIVO" : "PRÓXIMO"}
          </div>

          <div style={{ fontSize: 18, fontWeight: "bold" }}>
            {hero.home_team} vs {hero.away_team}
          </div>

          <div style={{ fontSize: 14, color: "#555" }}>
            {hero.competition}
          </div>
        </div>
      )}

      {/* BLOQUES */}
      <Block title="EN VIVO" matches={live} empty="Sin partidos en vivo" />
      <Block title="PRÓXIMOS" matches={upcoming} />
      <Block title="FINALIZADOS" matches={finished} />
    </div>
  );
}

function Block({
  title,
  matches,
  empty
}: {
  title: string;
  matches: Match[];
  empty?: string;
}) {
  return (
    <div style={{ marginBottom: 20 }}>
      <h3 style={{ marginBottom: 10 }}>{title}</h3>

      {matches.length === 0 && empty && (
        <div style={{ color: "#888" }}>{empty}</div>
      )}

      {matches.map((m) => (
        <div
          key={m.id}
          style={{
            border: "1px solid #eee",
            padding: 10,
            borderRadius: 8,
            marginBottom: 8
          }}
        >
          <div style={{ fontWeight: "bold" }}>
            {m.home_team} vs {m.away_team}
          </div>

          <div style={{ fontSize: 12, color: "#666" }}>
            {m.competition}
          </div>

          <div style={{ fontSize: 13 }}>
            {m.home_score != null
              ? `${m.home_score} - ${m.away_score}`
              : m.start_time}
          </div>
        </div>
      ))}
    </div>
  );
}
