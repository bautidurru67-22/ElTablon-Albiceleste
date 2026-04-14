import { api } from '@/lib/api'
import { sortMatches, groupBySport, sl } from '@/lib/matches'
import { Match } from '@/types/match'
import SectionTitle from '@/components/SectionTitle'
import CompetitionGroup from '@/components/CompetitionGroup'
import MatchRow from '@/components/MatchRow'
import styles from './calendario.module.css'

export const revalidate = 60
export const dynamic = 'force-dynamic'

const DAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
const SPORTS_FILTER = ['Todos', 'Fútbol', 'Tenis', 'Básquet', 'Hockey', 'Rugby']

function getWeekDays() {
  const today = new Date()
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today)
    d.setDate(today.getDate() + i - 1)
    return {
      label: i === 1 ? 'Hoy' : DAYS[d.getDay() === 0 ? 6 : d.getDay() - 1],
      day: d.getDate(),
      isToday: i === 1,
      date: d,
    }
  })
}

export default async function CalendarioPage() {
  const [allMatches, liveMatches] = await Promise.all([
    api.matches.today(),
    api.matches.live(),
  ])

  const sorted  = sortMatches(allMatches)
  const argOnly = sorted.filter(m => m.argentina_relevance !== 'none')
  const bySport = groupBySport(sorted)
  const weekDays = getWeekDays()

  const today = new Date().toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  })

  return (
    <div className={styles.page}>
      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>📅 Calendario Deportivo</h1>
        <span className={styles.tz}>Zona horaria: ARG (UTC-3)</span>
      </div>

      {/* Selector de días */}
      <div className={styles.daySelector}>
        <span className={styles.daySelectorLabel}>Mostrar:</span>
        <div className={styles.days}>
          {weekDays.map((d, i) => (
            <div key={i} className={`${styles.day} ${d.isToday ? styles.dayActive : ''}`}>
              <span className={styles.dayLabel}>{d.label}</span>
              <span className={styles.dayNum}>{d.day}</span>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.layout}>
        <div className={styles.main}>

          {/* Partidos destacados — en vivo primero */}
          {liveMatches.length > 0 && (
            <section className={styles.section}>
              <SectionTitle live count={liveMatches.length}>Partidos Destacados — En Vivo</SectionTitle>
              <div className={styles.featuredGrid}>
                {liveMatches.slice(0, 4).map(m => (
                  <div key={m.id} className={styles.featuredCard}>
                    <div className={styles.featuredComp}>{m.competition}</div>
                    <div className={styles.featuredTeams}>
                      <span>{m.home_team}</span>
                      {m.home_score != null ? (
                        <span className={styles.featuredScore}>{m.home_score} - {m.away_score}</span>
                      ) : (
                        <span className={styles.featuredVs}>vs</span>
                      )}
                      <span>{m.away_team}</span>
                    </div>
                    <div className={styles.featuredMeta}>
                      <span className={styles.liveTag}>● {m.minute ?? 'En vivo'}</span>
                      {m.broadcast && <span className={styles.bcast}>{m.broadcast}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Argentinos en acción hoy */}
          <section className={styles.section}>
            <SectionTitle count={argOnly.length}>Argentinos en Acción Hoy</SectionTitle>
            {argOnly.length > 0 ? (
              <div className={styles.matchList}>
                {argOnly.map(m => (
                  <MatchRow
                    key={m.id}
                    sport={m.sport}
                    competition={m.competition}
                    homeTeam={m.home_team}
                    awayTeam={m.away_team}
                    homeScore={m.home_score}
                    awayScore={m.away_score}
                    status={m.status}
                    minute={m.minute}
                    startTime={m.start_time}
                    broadcast={m.broadcast ?? undefined}
                  />
                ))}
              </div>
            ) : (
              <p className={styles.empty}>Sin partidos argentinos para hoy.</p>
            )}
          </section>

          {/* Por deporte */}
          {Object.entries(bySport).map(([sport, matches]) => (
            <section key={sport} className={styles.section}>
              <SectionTitle count={matches.length}>{sl(sport)}</SectionTitle>
              <div className={styles.matchList}>
                {matches.map(m => (
                  <MatchRow
                    key={m.id}
                    sport={m.sport}
                    competition={m.competition}
                    homeTeam={m.home_team}
                    awayTeam={m.away_team}
                    homeScore={m.home_score}
                    awayScore={m.away_score}
                    status={m.status}
                    minute={m.minute}
                    startTime={m.start_time}
                    broadcast={m.broadcast ?? undefined}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>

        {/* Sidebar */}
        <aside className={styles.sidebar}>
          {/* Filtro por deporte */}
          <div className={styles.sideCard}>
            <SectionTitle>Filtrar por deporte</SectionTitle>
            <div className={styles.sportFilters}>
              {SPORTS_FILTER.map(s => (
                <span key={s} className={`${styles.sportFilter} ${s === 'Todos' ? styles.sportFilterActive : ''}`}>
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* Días históricos placeholder */}
          <div className={styles.sideCard}>
            <SectionTitle>Días Históricos</SectionTitle>
            <div className={styles.histItem}>
              <span className={styles.histBullet}>●</span>
              <span>Argentina vs Nigeria — Gol de Cani (Mundial 1994)</span>
            </div>
            <div className={styles.histItem}>
              <span className={styles.histBullet}>●</span>
              <span>Boca 3-1 Real Madrid — Final Copa Intercontinental 2000</span>
            </div>
            <p className={styles.placeholder}>Datos históricos completos próximamente.</p>
          </div>

          {/* Cumpleaños placeholder */}
          <div className={styles.sideCard}>
            <SectionTitle>Cumpleaños Destacados</SectionTitle>
            <p className={styles.placeholder}>Próximamente: cumpleaños de atletas y clubes argentinos.</p>
          </div>
        </aside>
      </div>
    </div>
  )
}
