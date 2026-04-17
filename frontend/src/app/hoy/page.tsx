import { Suspense } from "react";

async function getData() {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BASE_URL || ""}/api/proxy/api/hoy`,
    {
      cache: "no-store",
    }
  );

  if (!res.ok) {
    throw new Error("Error fetching /hoy");
  }

  return res.json();
}

export default async function HoyPage() {
  const json = await getData();

  const data = json?.data || {};
  const matches = data.matches || [];
  const sections = data.sections || [];

  // 🔥 CLAVE: usar hero del backend
  const featured = data.hero || matches[0];

  return (
    <div style={{ padding: 20 }}>
      {/* HEADER INFO */}
      <div style={{ marginBottom: 20 }}>
        <span>PORTADA / HOY</span>
        <span style={{ marginLeft: 10 }}>{data.date}</span>
      </div>

      {/* HERO */}
      {featured && (
        <div
          style={{
            border: "1px solid #ddd",
            borderRadius: 10,
            padding: 20,
            marginBottom: 20,
          }}
        >
          <div style={{ fontSize: 12, color: "#888" }}>
            {featured.status?.toUpperCase()}
          </div>

          <div style={{ fontSize: 22, fontWeight: "bold" }}>
            {featured.home_team} vs {featured.away_team}
          </div>

          <div style={{ fontSize: 14, color: "#666" }}>
            {featured.competition}
          </div>

          <div style={{ marginTop: 10 }}>
            {featured.start_time || "-"}
          </div>
        </div>
      )}

      {/* SECTIONS */}
      <div style={{ display: "flex", gap: 20 }}>
        {sections.map((section: any) => (
          <div
            key={section.key}
            style={{
              flex: 1,
              border: "1px solid #ddd",
              borderRadius: 10,
              padding: 10,
            }}
          >
            <div style={{ fontWeight: "bold", marginBottom: 10 }}>
              {section.title} ({section.items.length})
            </div>

            {section.items.length === 0 && (
              <div style={{ color: "#999" }}>Sin eventos</div>
            )}

            {section.items.map((m: any) => (
              <div
                key={m.id}
                style={{
                  border: "1px solid #eee",
                  borderRadius: 6,
                  padding: 8,
                  marginBottom: 8,
                }}
              >
                <div>
                  {m.home_team} vs {m.away_team}
                </div>
                <div style={{ fontSize: 12, color: "#666" }}>
                  {m.competition}
                </div>
                <div style={{ fontSize: 12 }}>{m.start_time || "-"}</div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
