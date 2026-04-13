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
          `/api/proxy/api/matches/today`,
          { cache: "no-store" }
        )

        if (!res.ok) {
          const body = await res.text()
          throw new Error(`Proxy ${res.status}: ${body}`)
        }

        const json = await res.json()

        // Soporta ambos formatos:
        // 1) array directo
        // 2) objeto con { matches: [...] }
        if (Array.isArray(json)) {
          setData(json)
        } else if (json?.matches && Array.isArray(json.matches)) {
          setData(json.matches)
        } else {
          setData([])
        }
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
        <pre>{JSON.stringify(data, null, 2)}</pre>
      )}
    </main>
  )
}
