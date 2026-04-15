"use client";

import { useEffect, useState } from "react";

export default function HoyPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/proxy/api/hoy")
      .then((res) => res.json())
      .then((json) => {
        if (!json.ok) throw new Error("error");
        setData(json.data);
      })
      .catch(() => setError("No se pudo cargar la agenda"));
  }, []);

  if (error) {
    return <div style={{ padding: 20 }}>{error}</div>;
  }

  if (!data) {
    return <div style={{ padding: 20 }}>Cargando agenda...</div>;
  }

  const sections = data.sections || [];

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 20 }}>
      <h1 style={{ fontSize: 24, fontWeight: "bold" }}>
        HOY - DONDE JUEGA ARGENTINA
      </h1>

      <div style={{ display: "flex", gap: 20 }}>
        
        {/* MAIN */}
        <div style={{ flex: 1 }}>
          
          {/* EN VIVO */}
          <div style={{ border: "1px solid #ddd", marginTop: 10 }}>
            <div style={{ background: "#ffecec", padding: 8, fontWeight: "bold" }}>
              EN VIVO
            </div>
            {data.stats.live === 0 && (
              <div style={{ padding: 10 }}>Sin partidos en vivo.</div>
            )}
          </div>

          {/* SECTIONS */}
          {sections.map((section: any) => (
            <div key={section.key} style={{ border: "1px solid #ddd", marginTop: 10 }}>
              
              <div style={{ background: "#eee", padding: 8, fontWeight: "bold" }}>
                {section.title}
              </div>

              {section.items.map((m: any, i: number) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: 10,
                    borderTop: "1px solid #eee",
                  }}
                >
                  <div>
                    <div style={{ fontSize: 12, color: "#666" }}>
                      {m.competition}
                    </div>
                    <div>
                      {m.home_team} vs {m.away_team}
                    </div>
                  </div>

                  <div style={{ textAlign: "right" }}>
                    <div>
                      {m.home_score} - {m.away_score}
                    </div>
                    <div style={{ fontSize: 12 }}>
                      {m.start_time || "-"}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* SIDEBAR */}
        <div style={{ width: 220 }}>
          <div style={{ border: "1px solid #ddd", padding: 10 }}>
            <div style={{ fontWeight: "bold" }}>RESUMEN DE HOY</div>
            <div>En vivo: {data.stats.live}</div>
            <div>Próximos: {data.stats.upcoming}</div>
            <div>Finalizados: {data.stats.finished}</div>
          </div>
        </div>

      </div>
    </div>
  );
}
