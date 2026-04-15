"use client"

import { useEffect, useMemo, useState } from "react"
import styles from "./hoy.module.css"

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

function matchLabel(m: Match) {
  if (m.status === "live") return m.minute ?? "EN VIVO"
  if (m.status === "finished") return "Final"
  return m.start_time ?? "A confirmar"
}

function MatchItem({ m }: { m: Match }) {
  const hasConfirmedTime = Boolean(m.start_time && m.start_time !== "A confirmar")
  return (
    <div className={styles.itemRow}>
      <div className={styles.itemTop}>
        <span className={styles.itemComp}>{m.competition || m.sport}</span>
        <span className={styles.itemMeta}>{matchLabel(m)}</span>
      </div>
      <div className={styles.itemTeams}>
        <span className={styles.team}>{m.home_team}</span>
        <span className={styles.score}>{m.home_score ?? "-"} - {m.away_score ?? "-"}</span>
        <span className={styles.team}>{m.away_team}</span>
      </div>
      <div className={styles.itemSubMeta}>
        <span className={styles.sportTag}>{m.sport}</span>
        <span className={styles.timeTag}>{hasConfirmedTime ? "Horario confirmado" : "Horario a confirmar"}</span>
        <span className={styles.tvTag}>TV: {m.broadcast ?? "Sin confirmar"}</span>
      </div>
    </div>
  )
}

export default function Home() {
  const [data, setData] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sourceUsed, setSourceUsed] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true

    const fetchData = async () => {
      const parseMatches = (json: any): Match[] => {
        if (Array.isArray(json)) return json
        if (json?.data) return parseMatches(json.data)
        if (json?.matches && Array.isArray(json.matches)) return json.matches
        if (json?.en_vivo || json?.proximos || json?.finalizados) {
          return [...(json.en_vivo || []), ...(json.proximos || []), ...(json.finalizados || [])]
        }
        return []
      }

      const fetchEndpoint = async (url: string, timeoutMs = 8000): Promise<Match[]> => {
        const controller = new AbortController()
        const timer = setTimeout(() => controller.abort(), timeoutMs)
        const res = await fetch(url, { cache: "no-store", signal: controller.signal })
        clearTimeout(timer)

        if (!res.ok) {
          const body = await res.text()
          throw new Error(`${url} -> ${res.status}: ${body}`)
        }
        const json = await res.json()
        return parseMatches(json)
      }

      try {
        const errors: string[] = []
        const apiBase = process.env.NEXT_PUBLIC_API_URL ?? ""
        const endpoints = [
          "/api/proxy/api/hoy",
          "/api/proxy/api/matches/today",
          ...(apiBase ? [`${apiBase}/api/hoy`, `${apiBase}/api/matches/today`] : []),
        ]

        for (const url of endpoints) {
          try {
            const parsed = await fetchEndpoint(url)
            // Si el endpoint responde OK, usamos el contrato aunque venga vacío.
            // Evita colgarse pasando a fallbacks lentos.
            if (mounted) {
              setData(parsed)
              setError(null)
              setSourceUsed(url)
            }
            return
          } catch (e) {
            const msg = e instanceof Error ? e.message : "Error desconocido"
            errors.push(msg)
          }
        }

        // Si ninguna ruta respondió con datos, mostramos vacío controlado.
        if (mounted) {
          setData([])
          setSourceUsed(null)
          if (errors.length) {
            setError(errors.join(" | "))
          } else {
            setError(null)
          }
        }
      } catch (err) {
        console.error("Error:", err)
        if (mounted) {
          setError(err instanceof Error ? err.message : "Error inesperado")
          setData([])
          setSourceUsed(null)
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    fetchData()

    return () => {
      mounted = false
    }
  }, [])

  const live = useMemo(() => data.filter((m) => m.status === "live"), [data])
  const upcoming = useMemo(() => data.filter((m) => m.status === "upcoming"), [data])
  const finished = useMemo(() => data.filter((m) => m.status === "finished"), [data])
  const bySport = useMemo(() => {
    return data.reduce<Record<string, number>>((acc, m) => {
      acc[m.sport] = (acc[m.sport] ?? 0) + 1
      return acc
    }, {})
  }, [data])

  const today = new Date().toLocaleDateString("es-AR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  })

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>HOY - Agenda deportiva</h1>
        <span className={styles.pageDate}>{today}</span>
      </header>
      <div className={styles.emptyHint}>layout_hoy: v2.2</div>
      {!loading && (
        <div className={styles.emptyHint}>
          Fuente usada: <strong>{sourceUsed ?? 'sin datos'}</strong>
        </div>
      )}

      {loading ? (
        <div className={styles.empty}>
          <div className={styles.spinner} />
          Cargando agenda...
        </div>
      ) : error ? (
        <div className={styles.empty}>
          Error cargando agenda: {error}
          <div className={styles.emptyHint}>Revisá API_URL/BACKEND_URL y el deploy del backend.</div>
        </div>
      ) : data.length === 0 ? (
        <div className={styles.empty}>
          No hay partidos para mostrar.
          <div className={styles.emptyHint}>Intentá nuevamente en unos minutos.</div>
        </div>
      ) : (
        <div className={styles.layout}>
          <main className={styles.main}>
            <section className={styles.section}>
              <div className={`${styles.secHd} ${styles.secHdLive}`}>
                <div className={styles.secHdL}>
                  <span className={styles.liDot} />
                  <span className={styles.secTi}>En vivo</span>
                </div>
                <span className={`${styles.secBadge} ${styles.badgeLive}`}>{live.length}</span>
              </div>
              <div className={styles.secBody}>
                {live.length === 0 ? <p className={styles.emptyHint}>Sin partidos en vivo.</p> : live.map((m) => <MatchItem key={m.id} m={m} />)}
              </div>
            </section>

            <section className={styles.section}>
              <div className={`${styles.secHd} ${styles.secHdExt}`}>
                <div className={styles.secHdL}><span className={styles.secTi}>Próximos</span></div>
                <span className={styles.secBadge}>{upcoming.length}</span>
              </div>
              <div className={styles.secBody}>
                {upcoming.length === 0 ? <p className={styles.emptyHint}>Sin próximos partidos.</p> : upcoming.map((m) => <MatchItem key={m.id} m={m} />)}
              </div>
            </section>

            <section className={styles.section}>
              <div className={`${styles.secHd} ${styles.secHdLoc}`}>
                <div className={styles.secHdL}><span className={styles.secTi}>Finalizados</span></div>
                <span className={styles.secBadge}>{finished.length}</span>
              </div>
              <div className={styles.secBody}>
                {finished.length === 0 ? <p className={styles.emptyHint}>Sin finalizados.</p> : finished.map((m) => <MatchItem key={m.id} m={m} />)}
              </div>
            </section>
          </main>

          <aside className={styles.sidebar}>
            <div className={styles.sideCard}>
              <div className={styles.sideCardTitle}>Resumen de Hoy</div>
              <div className={styles.statRow}><span className={styles.statLabel}>En vivo</span><span className={styles.statVal}>{live.length}</span></div>
              <div className={styles.statRow}><span className={styles.statLabel}>Próximos</span><span className={styles.statVal}>{upcoming.length}</span></div>
              <div className={styles.statRow}><span className={styles.statLabel}>Finalizados</span><span className={styles.statVal}>{finished.length}</span></div>
              <div className={styles.statRow}><span className={styles.statLabel}>Total</span><span className={styles.statVal}>{data.length}</span></div>
            </div>
            <div className={styles.sideCard}>
              <div className={styles.sideCardTitle}>Por deporte</div>
              {Object.keys(bySport).length === 0 ? (
                <p className={styles.emptyHint}>Sin deportes activos.</p>
              ) : (
                Object.entries(bySport)
                  .sort((a, b) => b[1] - a[1])
                  .map(([sport, count]) => (
                    <div key={sport} className={styles.statRow}>
                      <span className={styles.statLabel}>{sport}</span>
                      <span className={styles.statVal}>{count}</span>
                    </div>
                  ))
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}
