import { api } from '@/lib/api'
import { sortMatches, groupByCompetition, groupBySport, sl } from '@/lib/matches'
import { Match } from '@/types/match'
import SectionTitle from '@/components/SectionTitle'
import CompetitionGroup from '@/components/CompetitionGroup'
import MatchRow from '@/components/MatchRow'
import SportBadge from '@/components/SportBadge'
import styles from './hoy.module.css'

export const revalidate = 30

export default async function HoyPage() {
  const all: Match[] = await api.matches.argentina()
  const sorted = sortMatches(all)

  const live     = sorted.filter(m => m.status === 'live')
  const upcoming = sorted.filter(m => m.status === 'upcoming')
  const finished = sorted.filter(m => m.status === 'finished')

  const liveByComp     = groupByCompetition(live)
  const upcomingByComp = groupByCompetition(upcoming)
  const finByComp      = groupByCompetition(finished)

  const bySport  = groupBySport(sorted)
  const sports   = Object.keys(bySport)

  const today = new Date().toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>Argentinos en Acción Hoy</h1>
        <span className={styles.pageDate}>{today}</span>
      </div>

      <div className={styles.layout}>
        {/* Columna principal */}
        <div className={styles.main}>

          {/* EN VIVO */}
          {live.length > 0 && (
            <section className={styles.section}>
              <SectionTitle live count={live.length}>En Vivo</SectionTitle>
              {Object.entries(liveByComp).map(([comp, matches]) => (
                <CompetitionGroup key={comp} competition={comp} matches={matches} />
              ))}
            </section>
          )}

          {/* PRÓXIMOS */}
          {upcoming.length > 0 && (
            <section className={styles.section}>
              <SectionTitle count={upcoming.length}>Próximos</SectionTitle>
              {Object.entries(upcomingByComp).map(([comp, matches]) => (
                <CompetitionGroup key={comp} competition={comp} matches={matches} />
              ))}
            </section>
          )}

          {/* FINALIZADOS */}
          {finished.length > 0 && (
            <section className={styles.section}>
              <SectionTitle count={finished.length}>Finalizados</SectionTitle>
              {Object.entries(finByComp).map(([comp, matches]) => (
                <CompetitionGroup key={comp} competition={comp} matches={matches} />
              ))}
            </section>
          )}

          {all.length === 0 && (
            <div className={styles.empty}>
              <p>No hay partidos argentinos registrados para hoy.</p>
              <p className={styles.emptyHint}>Los datos se actualizan cada 45 segundos.</p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <aside className={styles.sidebar}>
          {/* Resumen */}
          <div className={styles.sideCard}>
            <SectionTitle>Resumen del día</SectionTitle>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>En vivo</span>
              <span className={styles.statVal} style={{ color: 'var(--color-live)' }}>{live.length}</span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Próximos</span>
              <span className={styles.statVal}>{upcoming.length}</span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Finalizados</span>
              <span className={styles.statVal}>{finished.length}</span>
            </div>
            <div className={`${styles.statRow} ${styles.total}`}>
              <span className={styles.statLabel}>Total</span>
              <span className={styles.statVal}>{all.length}</span>
            </div>
          </div>

          {/* Deportes activos */}
          <div className={styles.sideCard}>
            <SectionTitle>Deportes hoy</SectionTitle>
            {sports.map(sport => {
              const ms = bySport[sport]
              const liveC = ms.filter(m => m.status === 'live').length
              return (
                <div key={sport} className={styles.sportRow}>
                  <div className={styles.sportLeft}>
                    {liveC > 0 && <span className={styles.liveDot} />}
                    <span className={styles.sportName}>{sl(sport)}</span>
                  </div>
                  <span className={styles.sportCount}>{ms.length}</span>
                </div>
              )
            })}
          </div>

          {/* Partidos en vivo destacados */}
          {live.length > 0 && (
            <div className={styles.sideCard}>
              <SectionTitle live>En vivo ahora</SectionTitle>
              {live.slice(0, 5).map(m => (
                <div key={m.id} className={styles.liveItem}>
                  <span className={styles.liveItemSport}><SportBadge sport={m.sport} /></span>
                  <span className={styles.liveItemMatch}>{m.home_team} - {m.away_team}</span>
                  {m.home_score != null && (
                    <span className={styles.liveItemScore}>{m.home_score}-{m.away_score}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
