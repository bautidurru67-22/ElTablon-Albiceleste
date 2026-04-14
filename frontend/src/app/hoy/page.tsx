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
    </div>
  )
}

export default function Home() {
  const [data, setData] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`/api/proxy/api/hoy`, { cache: "no-store" })
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
      } catch (err) {
        console.error("Error:", err)
        setError(err instanceof Error ? err.message : "Error inesperado")
        setData([])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const live = useMemo(() => data.filter((m) => m.status === "live"), [data])
  const upcoming = useMemo(() => data.filter((m) => m.status === "upcoming"), [data])
  const finished = useMemo(() => data.filter((m) => m.status === "finished"), [data])

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
          </aside>
        </div>
      )}
    </div>
  )
}
