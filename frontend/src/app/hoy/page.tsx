"use client"

import { useEffect, useState } from "react"

type Match = {
  id: string
  sport: string
  competition: string
  home_team: string
  away_team: string
  home_score?: number | null
  away_score?: number | null
  status: string
  minute?: string | null
  datetime?: string | null
  start_time?: string | null
  argentina_relevance?: string | null
  argentina_team?: string | null
  broadcast?: string | null
}

export default function Home() {
  const [data, setData] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(
          `/api/proxy/api/hoy`,
          { cache: "no-store" }
        )

        if (!res.ok) {
          const body = await res.text()
          throw new Error(`Proxy ${res.status}: ${body}`)
        }

        const json = await res.json()

        let parsed: Match[] = []
        if (Array.isArray(json)) {
          parsed = json
        } else if (json?.matches && Array.isArray(json.matches)) {
          parsed = json.matches
        } else if (json?.en_vivo || json?.proximos || json?.finalizados) {
          parsed = [...(json.en_vivo || []), ...(json.proximos || []), ...(json.finalizados || [])]
        }

        if (parsed.length === 0) {
          const fallback = await fetch(`/api/proxy/api/matches/today`, { cache: "no-store" })
          if (fallback.ok) {
            const fallbackJson = await fallback.json()
            parsed = Array.isArray(fallbackJson)
              ? fallbackJson
              : (Array.isArray(fallbackJson?.matches) ? fallbackJson.matches : [])
          }
        }

        setData(parsed)
      } catch (error) {
        console.error("Error:", error)
        setError(error instanceof Error ? error.message : "Error inesperado")
        setData([])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const live = data.filter((m) => m.status === "live")
  const upcoming = data.filter((m) => m.status === "upcoming")
  const finished = data.filter((m) => m.status === "finished")

  return (
    <main style={{ padding: "24px" }}>
      <h1>HOY - Agenda deportiva</h1>

      {loading ? (
        <p>Cargando...</p>
      ) : error ? (
        <p style={{ color: "crimson" }}>Error cargando partidos: {error}</p>
      ) : data.length === 0 ? (
        <p>No hay partidos para mostrar.</p>
      ) : (
        <div style={{ display: "grid", gap: 18 }}>
          <section>
            <h2 style={{ marginBottom: 8 }}>En vivo ({live.length})</h2>
            {live.length === 0 ? <p>Sin partidos en vivo.</p> : (
              <ul>
                {live.map((m) => (
                  <li key={m.id}>
                    <strong>{m.home_team}</strong> {m.home_score ?? "-"} - {m.away_score ?? "-"} <strong>{m.away_team}</strong>
                    {" · "}
                    {m.minute ?? "EN VIVO"}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2 style={{ marginBottom: 8 }}>Próximos ({upcoming.length})</h2>
            {upcoming.length === 0 ? <p>Sin próximos partidos.</p> : (
              <ul>
                {upcoming.map((m) => (
                  <li key={m.id}>
                    <strong>{m.home_team}</strong> vs <strong>{m.away_team}</strong>
                    {" · "}
                    {m.start_time ?? "Horario a confirmar"}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2 style={{ marginBottom: 8 }}>Finalizados ({finished.length})</h2>
            {finished.length === 0 ? <p>Sin finalizados.</p> : (
              <ul>
                {finished.map((m) => (
                  <li key={m.id}>
                    <strong>{m.home_team}</strong> {m.home_score ?? "-"} - {m.away_score ?? "-"} <strong>{m.away_team}</strong>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </main>
  )
}
