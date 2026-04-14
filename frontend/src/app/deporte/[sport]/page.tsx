import { api } from '@/lib/api'
import { sortMatches, groupByCompetition, sl } from '@/lib/matches'
import { Player } from '@/types/player'
import SectionTitle from '@/components/SectionTitle'
import CompetitionGroup from '@/components/CompetitionGroup'
import SportBadge from '@/components/SportBadge'
import styles from './deporte.module.css'
import FollowButton from '@/components/FollowButton'

export const revalidate = 30

interface Props {
  params: { sport: string }
  searchParams?: { competition?: string }
}

const SPORT_CONFIG: Record<string, { title: string; subtitle: string; rankingLabel?: string; hasPlayers: boolean }> = {
  futbol: { title: 'Fútbol Argentino', subtitle: 'Selección · Liga Profesional · Copas', rankingLabel: 'Goleadores', hasPlayers: true },
  tenis: { title: 'Tenis Argentino', subtitle: 'ATP · WTA · Challenger · Copa Davis', rankingLabel: 'Ranking ATP', hasPlayers: true },
  basquet: { title: 'Básquet Argentino', subtitle: 'Liga Nacional · NBA · FIBA', rankingLabel: 'Estadísticas', hasPlayers: true },
  hockey: { title: 'Hockey Argentino', subtitle: 'Las Leonas · Los Leones · Pro League', rankingLabel: 'FIH Ranking', hasPlayers: true },
  rugby: { title: 'Rugby Argentino', subtitle: 'Los Pumas · URBA · SuperRugby Américas', rankingLabel: 'World Rugby Ranking', hasPlayers: true },
  voley: { title: 'Vóley Argentino', subtitle: 'Las Panteras · Liga de Voleibol', hasPlayers: false },
  boxeo: { title: 'Boxeo Argentino', subtitle: 'Veladas y Campeonatos Mundiales', hasPlayers: true },
  futsal: { title: 'Futsal Argentino', subtitle: 'Liga Nacional · Selección', hasPlayers: false },
  golf: { title: 'Golf Argentino', subtitle: 'PGA Tour · DP World Tour', rankingLabel: 'OWGR Ranking', hasPlayers: true },
  polo: { title: 'Polo Argentino', subtitle: 'Triple Corona · Abierto de Palermo', hasPlayers: true },
  handball: { title: 'Handball Argentino', subtitle: 'IHF · Liga Argentina', hasPlayers: false },
  motorsport: { title: 'Automovilismo ARG', subtitle: 'F1 · Turismo Carretera · Rally', hasPlayers: true },
  motogp: { title: 'MotoGP', subtitle: 'Pilotos argentinos en el mundo', hasPlayers: true },
  dakar: { title: 'Rally Dakar', subtitle: 'Pilotos y equipos argentinos', hasPlayers: false },
  esports: { title: 'Esports Argentino', subtitle: 'CS2 · Valorant · LoL · FC', hasPlayers: false },
}

export default async function DeportePage({ params, searchParams }: Props) {
  const sport = params.sport
  const config = SPORT_CONFIG[sport] ?? {
    title: `${sl(sport)} Argentino`,
    subtitle: 'Equipos y jugadores argentinos',
    hasPlayers: false,
  }

  const selectedCompetition = searchParams?.competition ?? (sport === 'futbol' ? 'liga-profesional' : 'liga-nacional')

  const [allToday, playersAbroad, basketballOverview, footballOverview] = await Promise.all([
    api.matches.today(sport),
    config.hasPlayers ? api.players.abroad() : Promise.resolve([]),
    sport === 'basquet' ? api.basketball.overview(selectedCompetition) : Promise.resolve(null),
    sport === 'futbol' ? api.football.overview(selectedCompetition) : Promise.resolve(null),
  ])

  const sorted = sortMatches(allToday)
  const live = sorted.filter((m) => m.status === 'live')
  const upcoming = sorted.filter((m) => m.status === 'upcoming')
  const finished = sorted.filter((m) => m.status === 'finished')
  const byComp = groupByCompetition(sorted)
  const abroadForSport: Player[] = (playersAbroad as Player[]).filter((p) => p.sport === sport)

  const today = new Date().toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <div className={styles.page}>
      <div className={styles.sportHeader}>
        <div className={styles.sportHeaderLeft}>
          <div className={styles.sportIcon}><SportBadge sport={sport} /></div>
          <div>
            <h1 className={styles.sportTitle}>{config.title}</h1>
            <p className={styles.sportSubtitle}>{config.subtitle}</p>
          </div>
        </div>
        <div className={styles.sportHeaderRight}>
          {live.length > 0 && <span className={styles.liveIndicator}><span className={styles.liveDot} />{live.length} en vivo</span>}
          <span className={styles.dateLabel}>{today}</span>
        </div>
      </div>

      {sport === 'futbol' && footballOverview && (
        <section className={styles.section}>
          <div className={styles.basketHeaderRow}>
            <SectionTitle>Fixture y Tabla</SectionTitle>
            <div className={styles.compLinks}>
              <a href="?competition=liga-profesional" className={selectedCompetition === 'liga-profesional' ? styles.compActive : ''}>Liga Profesional</a>
              <a href="?competition=primera-nacional" className={selectedCompetition === 'primera-nacional' ? styles.compActive : ''}>Primera Nacional</a>
              <a href="?competition=copa-argentina" className={selectedCompetition === 'copa-argentina' ? styles.compActive : ''}>Copa Argentina</a>
            </div>
          </div>

          <div className={styles.twoColBasket}>
            <div className={styles.sideCard}>
              <SectionTitle>Tabla ({footballOverview.competition_label})</SectionTitle>
              {footballOverview.standings.length === 0 ? (
                <p className={styles.placeholder}>Sin tabla disponible (revisar API_FOOTBALL_KEY).</p>
              ) : (
                <div className={styles.standingsTable}>
                  <div className={styles.standingHead}><span>#</span><span>Equipo</span><span>PJ</span><span>PTS</span></div>
                  {footballOverview.standings.map((row) => (
                    <div className={styles.standingRow} key={`${row.position}-${row.team}`}>
                      <span>{row.position}</span>
                      <span className={styles.standingTeam}>{row.team}</span>
                      <span>{row.played ?? '–'}</span>
                      <span>{row.points ?? '–'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className={styles.sideCard}>
              <SectionTitle>Fixture ({footballOverview.fixtures.length})</SectionTitle>
              {footballOverview.fixtures.length === 0 ? (
                <p className={styles.placeholder}>Sin fixtures para mostrar en esta competencia.</p>
              ) : (
                <div className={styles.fixtureList}>
                  {footballOverview.fixtures.map((m, idx) => (
                    <div className={styles.fixtureRow} key={`${m.home}-${m.away}-${idx}`}>
                      <span className={styles.fixtureTeams}>{m.home} vs {m.away}</span>
                      <span className={styles.fixtureMeta}>
                        {m.home_score != null ? `${m.home_score}-${m.away_score}` : (m.round || 'Próximo')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {sport === 'basquet' && basketballOverview && (
        <section className={styles.section}>
          <div className={styles.basketHeaderRow}>
            <SectionTitle>Tabla y Fixture</SectionTitle>
            <div className={styles.compLinks}>
              <a href="?competition=liga-nacional" className={selectedCompetition === 'liga-nacional' ? styles.compActive : ''}>Liga Nacional</a>
              <a href="?competition=liga-argentina" className={selectedCompetition === 'liga-argentina' ? styles.compActive : ''}>Liga Argentina</a>
              <a href="?competition=liga-federal" className={selectedCompetition === 'liga-federal' ? styles.compActive : ''}>Liga Federal</a>
            </div>
          </div>

          <div className={styles.twoColBasket}>
            <div className={styles.sideCard}>
              <SectionTitle>Tabla ({basketballOverview.competition_label})</SectionTitle>
              {basketballOverview.standings.length === 0 ? (
                <p className={styles.placeholder}>Sin tabla disponible en este momento.</p>
              ) : (
                <div className={styles.standingsTable}>
                  <div className={styles.standingHead}><span>#</span><span>Equipo</span><span>PJ</span><span>PTS</span></div>
                  {basketballOverview.standings.map((row) => (
                    <div className={styles.standingRow} key={`${row.position}-${row.team}`}>
                      <span>{row.position}</span>
                      <span className={styles.standingTeam}>{row.team}</span>
                      <span>{row.pj ?? '–'}</span>
                      <span>{row.pts ?? '–'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className={styles.sideCard}>
              <SectionTitle>Fixture ({basketballOverview.fixtures.length})</SectionTitle>
              {basketballOverview.fixtures.length === 0 ? (
                <p className={styles.placeholder}>Sin partidos disponibles para este torneo.</p>
              ) : (
                <div className={styles.fixtureList}>
                  {basketballOverview.fixtures.slice(0, 16).map((m, idx) => (
                    <div className={styles.fixtureRow} key={`${m.home}-${m.away}-${idx}`}>
                      <span className={styles.fixtureTeams}>{m.home} vs {m.away}</span>
                      <span className={styles.fixtureMeta}>
                        {m.status === 'finished' && m.home_score != null ? `${m.home_score}-${m.away_score}` : (m.start_time || 'A confirmar')}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      <div className={styles.layout}>
        <div className={styles.main}>
          {live.length > 0 && (
            <section className={styles.section}>
              <SectionTitle live count={live.length}>En Vivo</SectionTitle>
              {Object.entries(groupByCompetition(live)).map(([comp, matches]) => (
                <CompetitionGroup key={comp} competition={comp} matches={matches} />
              ))}
            </section>
          )}

          {sorted.length > 0 ? (
            <section className={styles.section}>
              <SectionTitle count={sorted.length}>Partidos del Día</SectionTitle>
              <div className={styles.matchTable}>
                <div className={styles.matchTableHeader}><span>Hora</span><span>Competencia</span><span className={styles.colTeams}>Partido</span><span className={styles.colBcast}>Donde ver</span></div>
                {sorted.map((m) => (
                  <div key={m.id} className={`${styles.matchTableRow} ${m.status === 'live' ? styles.rowLive : m.status === 'finished' ? styles.rowFinished : ''}`}>
                    <span className={styles.colTime}>{m.status === 'live' ? <span className={styles.liveMin}><span className={styles.dot} />{m.minute ?? 'EN VIVO'}</span> : m.status === 'finished' ? <span className={styles.finalTag}>Final</span> : <span className={styles.timeStr}>{m.start_time ?? '–'}</span>}</span>
                    <span className={styles.colComp}>{m.competition}</span>
                    <span className={styles.colTeams}>
                      <span className={m.status === 'finished' && (m.home_score ?? 0) > (m.away_score ?? 0) ? styles.winner : ''}>{m.home_team}</span>
                      {m.home_score != null ? <span className={styles.scoreInline}>{m.home_score}-{m.away_score}</span> : <span className={styles.vsInline}>vs</span>}
                      <span className={m.status === 'finished' && (m.away_score ?? 0) > (m.home_score ?? 0) ? styles.winner : ''}>{m.away_team}</span>
                    </span>
                    <span className={styles.colBcast}>{m.broadcast ?? '–'}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : (
            <div className={styles.noMatches}><p>No hay partidos de {config.title} para hoy.</p></div>
          )}

          {abroadForSport.length > 0 && (
            <section className={styles.section}>
              <SectionTitle>Argentinos en el Mundo</SectionTitle>
              <div className={styles.abroadGrid}>
                {abroadForSport.map((p) => (
                  <div key={p.id} className={`${styles.playerCard} ${p.playing_today ? styles.playerCardPlaying : ''}`}>
                    <div className={styles.playerAvatar}>{p.name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()}</div>
                    <div className={styles.playerInfo}>
                      <span className={styles.playerName}>{p.name}{p.playing_today && <span className={styles.playingBadge}>HOY</span>}</span>
                      <FollowButton tipo="jugador" entityId={p.id} />
                      <span className={styles.playerDetail}>{p.team} · {p.league} {p.flag}</span>
                    </div>
                    <div className={styles.playerStat}><span className={styles.playerStatVal}>{p.stat_value}</span><span className={styles.playerStatLabel}>{p.stat_label}</span></div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        <aside className={styles.sidebar}>
          <div className={styles.sideCard}>
            <SectionTitle>Hoy en {sl(sport)}</SectionTitle>
            <div className={styles.statRow}><span className={styles.statLabel}>En vivo</span><span className={styles.statVal} style={{ color: live.length > 0 ? 'var(--color-live)' : undefined }}>{live.length}</span></div>
            <div className={styles.statRow}><span className={styles.statLabel}>Próximos</span><span className={styles.statVal}>{upcoming.length}</span></div>
            <div className={styles.statRow}><span className={styles.statLabel}>Finalizados</span><span className={styles.statVal}>{finished.length}</span></div>
          </div>

          {Object.keys(byComp).length > 0 && (
            <div className={styles.sideCard}>
              <SectionTitle>Competencias</SectionTitle>
              {Object.entries(byComp).map(([comp, matches]) => (
                <div key={comp} className={styles.compRow}><span className={styles.compName}>{comp}</span><span className={styles.compCount}>{matches.length}</span></div>
              ))}
            </div>
          )}

          {config.rankingLabel && (
            <div className={styles.sideCard}>
              <SectionTitle>{config.rankingLabel}</SectionTitle>
              {abroadForSport.slice(0, 4).map((p, i) => (
                <div key={p.id} className={styles.rankRow}><span className={styles.rankPos}>{i + 1}</span><span className={styles.rankName}>{p.name}</span><span className={styles.rankStat}>{p.stat_value}</span></div>
              ))}
              {abroadForSport.length === 0 && <p className={styles.placeholder}>Sin datos reales disponibles para hoy.</p>}
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
