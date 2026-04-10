import { api } from '@/lib/api'
import { sortMatches, groupBySport, sl } from '@/lib/matches'
import { Match } from '@/types/match'
import SectionTitle from '@/components/SectionTitle'
import MatchRow from '@/components/MatchRow'
import SportBadge from '@/components/SportBadge'
import styles from './club.module.css'
import FollowButton from '@/components/FollowButton'

export const revalidate = 30

interface Props {
  params: { id: string }
}

function formatClubName(id: string) {
  return id
    .split('-')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export default async function ClubPage({ params }: Props) {
  const clubId   = params.id
  const clubName = formatClubName(clubId)

  const matches: Match[] = await api.matches.club(clubId)
  const sorted   = sortMatches(matches)

  const live     = sorted.filter(m => m.status === 'live')
  const upcoming = sorted.filter(m => m.status === 'upcoming')
  const finished = sorted.filter(m => m.status === 'finished')
  const bySport  = groupBySport(sorted)
  const sports   = Object.keys(bySport)

  const totalSports   = sports.length
  const liveCount     = live.length
  const todayCount    = sorted.length

  return (
    <div className={styles.page}>
      {/* Club header */}
      <div className={styles.clubHeader}>
        <div className={styles.clubAvatar}>
          {clubName.charAt(0).toUpperCase()}
        </div>
        <div className={styles.clubInfo}>
          <h1 className={styles.clubName}>{clubName}</h1>
          <FollowButton tipo="equipo" entityId={clubId} />
          <div className={styles.clubMeta}>
            <span className={styles.clubMetaItem}>
              {totalSports} deporte{totalSports !== 1 ? 's' : ''} activo{totalSports !== 1 ? 's' : ''}
            </span>
            {liveCount > 0 && (
              <span className={styles.clubLive}>● {liveCount} en vivo</span>
            )}
          </div>
          <div className={styles.clubSports}>
            {sports.map(s => <SportBadge key={s} sport={s} />)}
          </div>
        </div>
      </div>

      <div className={styles.layout}>
        <div className={styles.main}>

          {/* Partido destacado — en vivo */}
          {live.length > 0 && (
            <section className={styles.section}>
              <SectionTitle live>En Vivo Ahora</SectionTitle>
              {live.map(m => (
                <div key={m.id} className={styles.featuredMatch}>
                  <div className={styles.featuredTop}>
                    <SportBadge sport={m.sport} />
                    <span className={styles.featuredComp}>{m.competition}</span>
                    <span className={styles.featuredMin}>● {m.minute ?? 'En vivo'}</span>
                  </div>
                  <div className={styles.featuredTeams}>
                    <span className={styles.featuredTeam}>{m.home_team}</span>
                    {m.home_score != null ? (
                      <div className={styles.featuredScore}>
                        <span className={styles.fNum}>{m.home_score}</span>
                        <span className={styles.fSep}>-</span>
                        <span className={styles.fNum}>{m.away_score}</span>
                      </div>
                    ) : (
                      <span className={styles.featuredVs}>vs</span>
                    )}
                    <span className={`${styles.featuredTeam} ${styles.right}`}>{m.away_team}</span>
                  </div>
                  {m.broadcast && (
                    <div className={styles.featuredBcast}>{m.broadcast}</div>
                  )}
                </div>
              ))}
            </section>
          )}

          {/* Por deporte */}
          {sports.map(sport => {
            const sportMatches = bySport[sport]
            const sportLive     = sportMatches.filter(m => m.status === 'live')
            const sportUpcoming = sportMatches.filter(m => m.status === 'upcoming')
            const sportFinished = sportMatches.filter(m => m.status === 'finished')
            return (
              <section key={sport} className={styles.section}>
                <SectionTitle
                  live={sportLive.length > 0}
                  count={sportMatches.length}
                >
                  {sl(sport)}
                </SectionTitle>

                {sportUpcoming.length > 0 && (
                  <div className={styles.subSection}>
                    <div className={styles.subLabel}>Próximos</div>
                    <div className={styles.matchList}>
                      {sportUpcoming.map(m => (
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
                          compact
                        />
                      ))}
                    </div>
                  </div>
                )}

                {sportFinished.length > 0 && (
                  <div className={styles.subSection}>
                    <div className={styles.subLabel}>Últimos resultados</div>
                    <div className={styles.matchList}>
                      {sportFinished.map(m => (
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
                          compact
                        />
                      ))}
                    </div>
                  </div>
                )}
              </section>
            )
          })}

          {sorted.length === 0 && (
            <div className={styles.empty}>
              <p>No hay actividad registrada para <strong>{clubName}</strong> hoy.</p>
              <p className={styles.emptyHint}>Probá buscando por nombre exacto: /club/racing-club, /club/river-plate, /club/boca-juniors</p>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <aside className={styles.sidebar}>
          <div className={styles.sideCard}>
            <SectionTitle>Actividad del Club</SectionTitle>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Partidos hoy</span>
              <span className={styles.statVal}>{todayCount}</span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>En vivo</span>
              <span className={styles.statVal} style={{ color: 'var(--color-live)' }}>{liveCount}</span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Próximos</span>
              <span className={styles.statVal}>{upcoming.length}</span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Finalizados</span>
              <span className={styles.statVal}>{finished.length}</span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Deportes activos</span>
              <span className={styles.statVal}>{totalSports}</span>
            </div>
          </div>

          {upcoming.length > 0 && (
            <div className={styles.sideCard}>
              <SectionTitle>Agenda importante</SectionTitle>
              {upcoming.slice(0, 5).map(m => (
                <div key={m.id} className={styles.agendaItem}>
                  <span className={styles.agendaTime}>{m.start_time ?? '–'}</span>
                  <div className={styles.agendaInfo}>
                    <span className={styles.agendaMatch}>{m.home_team} vs {m.away_team}</span>
                    <span className={styles.agendaComp}>{m.competition}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {finished.length > 0 && (
            <div className={styles.sideCard}>
              <SectionTitle>Últimos resultados</SectionTitle>
              {finished.slice(0, 4).map(m => (
                <div key={m.id} className={styles.resultItem}>
                  <span className={styles.resultTeams}>{m.home_team} {m.home_score}-{m.away_score} {m.away_team}</span>
                  <span className={styles.resultComp}>{m.competition}</span>
                </div>
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
