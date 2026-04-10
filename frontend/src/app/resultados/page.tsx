import { api } from '@/lib/api'
import { sortMatches, groupBySport, groupByCompetition, sl } from '@/lib/matches'
import { Match } from '@/types/match'
import SectionTitle from '@/components/SectionTitle'
import CompetitionGroup from '@/components/CompetitionGroup'
import SportBadge from '@/components/SportBadge'
import styles from './resultados.module.css'

export const revalidate = 60

export default async function ResultadosPage() {
  const all: Match[] = await api.matches.results()
  const results = sortMatches(all)

  const bySport  = groupBySport(results)
  const sports   = Object.keys(bySport)

  const today = new Date().toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  // Para sidebar: contar goles totales en fútbol
  const futbolMatches = bySport['futbol'] ?? []
  const totalGoals = futbolMatches.reduce(
    (acc, m) => acc + (m.home_score ?? 0) + (m.away_score ?? 0), 0
  )

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>Resultados</h1>
        <span className={styles.pageDate}>{today}</span>
      </div>

      {results.length === 0 ? (
        <div className={styles.empty}>
          <p>No hay resultados finalizados todavía.</p>
          <p className={styles.emptyHint}>Los resultados aparecen aquí a medida que terminan los partidos.</p>
        </div>
      ) : (
        <div className={styles.layout}>

          {/* Columna principal */}
          <div className={styles.main}>
            {sports.map(sport => {
              const sportMatches = bySport[sport]
              const byComp = groupByCompetition(sportMatches)
              return (
                <section key={sport} className={styles.section}>
                  <div className={styles.sportHeader}>
                    <SportBadge sport={sport} />
                    <span className={styles.sportTitle}>{sl(sport)}</span>
                    <span className={styles.sportCount}>{sportMatches.length} resultado{sportMatches.length !== 1 ? 's' : ''}</span>
                  </div>
                  {Object.entries(byComp).map(([comp, matches]) => (
                    <CompetitionGroup key={comp} competition={comp} matches={matches} />
                  ))}
                </section>
              )
            })}
          </div>

          {/* Sidebar */}
          <aside className={styles.sidebar}>

            {/* Resumen global */}
            <div className={styles.sideCard}>
              <SectionTitle>Resumen</SectionTitle>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>Total resultados</span>
                <span className={styles.statVal}>{results.length}</span>
              </div>
              <div className={styles.statRow}>
                <span className={styles.statLabel}>Deportes</span>
                <span className={styles.statVal}>{sports.length}</span>
              </div>
              {futbolMatches.length > 0 && (
                <div className={styles.statRow}>
                  <span className={styles.statLabel}>Goles totales</span>
                  <span className={styles.statVal}>{totalGoals}</span>
                </div>
              )}
            </div>

            {/* Por deporte */}
            <div className={styles.sideCard}>
              <SectionTitle>Por deporte</SectionTitle>
              {sports.map(sport => (
                <div key={sport} className={styles.sportRow}>
                  <span className={styles.sportRowName}>{sl(sport)}</span>
                  <span className={styles.sportRowCount}>{bySport[sport].length}</span>
                </div>
              ))}
            </div>

            {/* Tabla rápida fútbol */}
            {futbolMatches.length > 0 && (
              <div className={styles.sideCard}>
                <SectionTitle>Fútbol — Scores</SectionTitle>
                {futbolMatches.map(m => (
                  <div key={m.id} className={styles.scoreRow}>
                    <span className={styles.scoreTeams}>
                      <span className={m.home_score! > m.away_score! ? styles.scoreWinner : ''}>{m.home_team}</span>
                      <span className={styles.scoreLine}>{m.home_score}-{m.away_score}</span>
                      <span className={m.away_score! > m.home_score! ? styles.scoreWinner : ''}>{m.away_team}</span>
                    </span>
                    <span className={styles.scoreComp}>{m.competition}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Tenis si aplica */}
            {bySport['tenis'] && (
              <div className={styles.sideCard}>
                <SectionTitle>Tenis — Sets</SectionTitle>
                {bySport['tenis'].map(m => (
                  <div key={m.id} className={styles.scoreRow}>
                    <span className={styles.scoreTeams}>
                      <span className={m.home_score! > m.away_score! ? styles.scoreWinner : ''}>{m.home_team}</span>
                      <span className={styles.scoreLine}>{m.home_score}-{m.away_score}</span>
                      <span className={m.away_score! > m.home_score! ? styles.scoreWinner : ''}>{m.away_team}</span>
                    </span>
                    <span className={styles.scoreComp}>{m.competition}</span>
                  </div>
                ))}
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  )
}
