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

const isLive = (m: Match) => {
  const s = (m.status || "").toLowerCase()
  return ["live", "en vivo", "in_progress", "playing"].some((k) => s.includes(k)) || !!m.minute
}

const isFinished = (m: Match) => {
  const s = (m.status || "").toLowerCase()
  return ["finished", "final", "ft", "ended"].some((k) => s.includes(k))
}

function score(v?: number | null) {
  return v === undefined || v === null ? "-" : String(v)
}

export default function Home() {
  const [data, setData] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/matches/today`, { cache: "no-store" })
        const json = await res.json()

        if (Array.isArray(json)) {
          setData(json)
        } else if (json?.matches && Array.isArray(json.matches)) {
          setData(json.matches)
        } else {
          setData([])
        }
      } catch (error) {
        console.error("Error:", error)
        setData([])
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  const grouped = useMemo(() => {
    const live = data.filter(isLive)
    const finished = data.filter((m) => !isLive(m) && isFinished(m))
    const upcoming = data.filter((m) => !isLive(m) && !isFinished(m))
    return { live, upcoming, finished }
  }, [data])

  const cards = [...grouped.live, ...grouped.upcoming, ...grouped.finished]

  return (
    <section className={styles.page}>
      <div className={styles.layout}>
        <aside className={styles.sidebar}>
          <div className={styles.sideTitle}>PARTIDOS DE HOY</div>
          <div className={styles.sideItem}><span className={styles.liveDot} /> En vivo ({grouped.live.length})</div>
          <div className={styles.sideItem}>Próximos ({grouped.upcoming.length})</div>
          <div className={styles.sideItem}>Finalizados ({grouped.finished.length})</div>
        </aside>

        <div className={styles.centerCol}>
          <header className={styles.pageHeader}>
            <h1 className={styles.pageTitle}>HOY - Agenda deportiva</h1>
            <span className={styles.badge}>{cards.length} partidos</span>
          </header>

          {loading ? (
            <div className={styles.empty}>Cargando partidos...</div>
          ) : cards.length === 0 ? (
            <div className={styles.empty}>No hay partidos para mostrar.</div>
          ) : (
            <div className={styles.cards}>
              {cards.map((m) => (
                <article key={m.id} className={styles.matchCard}>
                  <div className={styles.cardHeader}>
                    <span className={styles.comp}>{m.competition || "Competencia"}</span>
                    <span className={isLive(m) ? styles.liveBadge : styles.statusBadge}>
                      {isLive(m) ? `EN VIVO ${m.minute ?? ""}`.trim() : (m.status || "Programado")}
                    </span>
                  </div>

                  <div className={styles.teamsRow}>
                    <div className={styles.team}>{m.home_team}</div>
                    <div className={styles.score}>{score(m.home_score)} - {score(m.away_score)}</div>
                    <div className={styles.teamAway}>{m.away_team}</div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
