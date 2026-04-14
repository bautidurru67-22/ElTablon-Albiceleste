import Link from 'next/link'
import { api } from '@/lib/api'
import { sortMatches, groupByCompetition, sl } from '@/lib/matches'
import { Match } from '@/types/match'
import { Player } from '@/types/player'
import SectionTitle from '@/components/SectionTitle'
import CompetitionGroup from '@/components/CompetitionGroup'
import SportBadge from '@/components/SportBadge'
import styles from './deporte.module.css'
import FollowButton from '@/components/FollowButton'

export const revalidate = 30
export const dynamic = 'force-dynamic'

interface Props {
  params: { sport: string }
  searchParams?: { comp?: string }
}

const SPORT_CONFIG: Record<string, {
  title: string
  subtitle: string
  rankingLabel?: string
  hasPlayers: boolean
}> = {
  futbol:   { title: 'Fútbol Argentino',   subtitle: 'Selección · Liga Profesional · Copas',  rankingLabel: 'Goleadores', hasPlayers: true },
  tenis:    { title: 'Tenis Argentino',     subtitle: 'ATP · WTA · Challenger · Copa Davis',    rankingLabel: 'Ranking ATP', hasPlayers: true },
  basquet:  { title: 'Básquet Argentino',   subtitle: 'Liga Nacional · NBA · FIBA',            rankingLabel: 'Estadísticas', hasPlayers: true },
  hockey:   { title: 'Hockey Argentino',    subtitle: 'Las Leonas · Los Leones · Pro League', rankingLabel: 'FIH Ranking', hasPlayers: true },
  rugby:    { title: 'Rugby Argentino',     subtitle: 'Los Pumas · URBA · SuperRugby Américas', rankingLabel: 'World Rugby Ranking', hasPlayers: true },
  voley:    { title: 'Vóley Argentino',     subtitle: 'Las Panteras · Liga de Voleibol', hasPlayers: false },
  boxeo:    { title: 'Boxeo Argentino',     subtitle: 'Veladas y Campeonatos Mundiales', hasPlayers: true },
  futsal:   { title: 'Futsal Argentino',    subtitle: 'Liga Nacional · Selección', hasPlayers: false },
  golf:     { title: 'Golf Argentino',      subtitle: 'PGA Tour · DP World Tour', rankingLabel: 'OWGR Ranking', hasPlayers: true },
  polo:     { title: 'Polo Argentino',      subtitle: 'Triple Corona · Abierto de Palermo', hasPlayers: true },
  handball: { title: 'Handball Argentino',  subtitle: 'IHF · Liga Argentina', hasPlayers: false },
  motorsport:{ title: 'Automovilismo ARG',  subtitle: 'F1 · Turismo Carretera · Rally', hasPlayers: true },
  motogp:   { title: 'MotoGP',             subtitle: 'Pilotos argentinos en el mundo', hasPlayers: true },
  dakar:    { title: 'Rally Dakar',         subtitle: 'Pilotos y equipos argentinos', hasPlayers: false },
  esports:  { title: 'Esports Argentino',   subtitle: 'CS2 · Valorant · LoL · FC', hasPlayers: false },
}

const SPORT_PLAYERS: Record<string, Array<{ name: string; detail: string; stat: string; flag: string }>> = {
  basquet: [
    { name: 'Facundo Campazzo', detail: 'Dallas Mavericks · NBA', stat: '14.2 pts', flag: '🇺🇸' },
    { name: 'Leandro Bolmaro', detail: 'FC Barcelona · ACB', stat: '11.8 pts', flag: '🇪🇸' },
    { name: 'Nicolás Laprovíttola', detail: 'Laga Basket · ACB', stat: '9.4 pts', flag: '🇪🇸' },
  ],
  futbol: [
    { name: 'Lautaro Martínez', detail: 'Inter Milano · Serie A', stat: '26 goles', flag: '🇮🇹' },
    { name: 'Julián Álvarez', detail: 'Atlético Madrid · LaLiga', stat: '18 goles', flag: '🇪🇸' },
    { name: 'Alejandro Garnacho', detail: 'Manchester United · PL', stat: '12 goles', flag: '🏴' },
  ],
}

const COMP_FILTERS: Record<string, Array<{ slug: string; label: string; keywords: string[] }>> = {
  futbol: [
    { slug: 'liga-profesional', label: 'Liga Profesional', keywords: ['liga profesional', 'lpf', 'superliga'] },
    { slug: 'primera-nacional', label: 'Primera Nacional', keywords: ['primera nacional'] },
    { slug: 'copa-argentina', label: 'Copa Argentina', keywords: ['copa argentina'] },
    { slug: 'reserva', label: 'Reserva', keywords: ['reserva'] },
    { slug: 'femenina', label: '1era División Femenina', keywords: ['femenina'] },
    { slug: 'juveniles', label: 'Juveniles', keywords: ['juvenil'] },
    { slug: 'b-metro', label: 'B Metro', keywords: ['b metro', 'primera b'] },
    { slug: 'federal-a', label: 'Federal A', keywords: ['federal a'] },
    { slug: 'federal-b', label: 'Federal B', keywords: ['federal b', 'regional amateur'] },
    { slug: 'primera-c', label: 'Primera C', keywords: ['primera c'] },
    { slug: 'promocional', label: 'Promocional Amateur', keywords: ['promocional'] },
    { slug: 'libertadores', label: 'Copa Libertadores', keywords: ['libertadores'] },
    { slug: 'sudamericana', label: 'Copa Sudamericana', keywords: ['sudamericana'] },
    { slug: 'mundial', label: 'Mundial', keywords: ['world cup', 'mundial'] },
  ],
  basquet: [
    { slug: 'liga-nacional', label: 'Liga Nacional', keywords: ['liga nacional', 'lnb'] },
    { slug: 'liga-argentina', label: 'Liga Argentina', keywords: ['liga argentina'] },
    { slug: 'liga-federal', label: 'Liga Federal', keywords: ['liga federal'] },
    { slug: 'copa-super20', label: 'Copa Súper 20', keywords: ['super 20', 'súper 20'] },
    { slug: 'nba', label: 'NBA', keywords: ['nba'] },
    { slug: 'fiba', label: 'FIBA', keywords: ['fiba'] },
    { slug: 'seleccion', label: 'Selección', keywords: ['selección', 'selection'] },
  ],
}

function matchesByCompetition(matches: Match[], active: string, filters: Array<{slug: string; keywords: string[]}>): Match[] {
  if (!active || active === 'all') return matches
  const f = filters.find(x => x.slug === active)
  if (!f) return matches
  return matches.filter(m => {
    const c = (m.competition || '').toLowerCase()
    return f.keywords.some(k => c.includes(k))
  })
}

export default async function DeportePage({ params, searchParams }: Props) {
  const sport = params.sport
  const config = SPORT_CONFIG[sport] ?? {
    title: `${sl(sport)} Argentino`,
    subtitle: 'Equipos y jugadores argentinos',
    hasPlayers: false,
  }

  const tabs = COMP_FILTERS[sport] ?? []
  const activeComp = searchParams?.comp || 'all'

  const [allToday, playersAbroad] = await Promise.all([
    api.matches.today(sport),
    config.hasPlayers ? api.players.abroad() : Promise.resolve([]),
  ])

  const sortedRaw = sortMatches(allToday)
  const sorted = matchesByCompetition(sortedRaw, activeComp, tabs)

  const live = sorted.filter(m => m.status === 'live')
  const upcoming = sorted.filter(m => m.status === 'upcoming')
  const finished = sorted.filter(m => m.status === 'finished')
  const byComp = groupByCompetition(sorted)

  const sportPlayers = SPORT_PLAYERS[sport] ?? []
  const abroadForSport: Player[] = (playersAbroad as Player[]).filter(p => p.sport === sport)

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
          {live.length > 0 && (
            <span className={styles.liveIndicator}>
              <span className={styles.liveDot} />
              {live.length} en vivo
            </span>
          )}
          <span className={styles.dateLabel}>{today}</span>
        </div>
      </div>

      {tabs.length > 0 && (
        <div className={styles.compTabs}>
          <Link href={`/deporte/${sport}`} className={activeComp === 'all' ? styles.compTabActive : styles.compTab}>
            Todas
          </Link>
          {tabs.map(t => (
            <Link
              key={t.slug}
              href={`/deporte/${sport}?comp=${t.slug}`}
              className={activeComp === t.slug ? styles.compTabActive : styles.compTab}
            >
              {t.label}
            </Link>
          ))}
        </div>
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
                <div className={styles.matchTableHeader}>
                  <span>Hora</span>
                  <span>Competencia</span>
                  <span className={styles.colTeams}>Partido</span>
                  <span className={styles.colBcast}>Dónde ver</span>
                </div>
                {sorted.map(m => (
                  <div key={m.id} className={`${styles.matchTableRow} ${m.status === 'live' ? styles.rowLive : m.status === 'finished' ? styles.rowFinished : ''}`}>
                    <span className={styles.colTime}>
                      {m.status === 'live' ? (
                        <span className={styles.liveMin}><span className={styles.dot} />{m.minute ?? 'EN VIVO'}</span>
                      ) : m.status === 'finished' ? (
                        <span className={styles.finalTag}>Final</span>
                      ) : (
                        <span className={styles.timeStr}>{m.start_time ?? '–'}</span>
                      )}
                    </span>
                    <span className={styles.colComp}>{m.competition}</span>
                    <span className={styles.colTeams}>
                      <span>{m.home_team}</span>
                      {m.home_score != null ? <span className={styles.scoreInline}>{m.home_score}-{m.away_score}</span> : <span className={styles.vsInline}>vs</span>}
                      <span>{m.away_team}</span>
                    </span>
                    <span className={styles.colBcast}>{m.broadcast ?? '–'}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : (
            <div className={styles.noMatches}>
              <p>No hay partidos para mostrar en esta competencia.</p>
            </div>
          )}

          {sportPlayers.length > 0 && (
            <section className={styles.section}>
              <SectionTitle>{config.rankingLabel ?? 'Jugadores destacados'}</SectionTitle>
              <div className={styles.playersGrid}>
                {sportPlayers.map(p => (
                  <div key={p.name} className={styles.playerCard}>
                    <div className={styles.playerAvatar}>{p.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}</div>
                    <div className={styles.playerInfo}>
                      <span className={styles.playerName}>{p.name} <span className={styles.playerFlag}>{p.flag}</span></span>
                      <span className={styles.playerDetail}>{p.detail}</span>
                    </div>
                    <div className={styles.playerStat}>{p.stat}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {abroadForSport.length > 0 && (
            <section className={styles.section}>
              <SectionTitle>Argentinos en el Mundo</SectionTitle>
              <div className={styles.playersGrid}>
                {abroadForSport.map(p => (
                  <div key={p.id} className={styles.playerCard}>
                    <div className={styles.playerAvatar}>{p.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}</div>
                    <div className={styles.playerInfo}>
                      <span className={styles.playerName}>{p.name}</span>
                      <FollowButton tipo="jugador" entityId={p.id} />
                      <span className={styles.playerDetail}>{p.team} · {p.league} {p.flag}</span>
                    </div>
                    <div className={styles.playerStat}>{p.stat_value}</div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        <aside className={styles.sidebar}>
                 <aside className={styles.sidebar}>
          <div className={styles.sideCard}>
            <SectionTitle>Hoy en {sl(sport)}</SectionTitle>
            <div className={styles.statRow}><span className={styles.statLabel}>En vivo</span><span className={styles.statVal}>{live.length}</span></div>
            <div className={styles.statRow}><span className={styles.statLabel}>Próximos</span><span className={styles.statVal}>{upcoming.length}</span></div>
            <div className={styles.statRow}><span className={styles.statLabel}>Finalizados</span><span className={styles.statVal}>{finished.length}</span></div>
          </div>

          {Object.keys(byComp).length > 0 && (
            <div className={styles.sideCard}>
              <SectionTitle>Competencias</SectionTitle>
              {Object.entries(byComp).map(([comp, matches]) => (
                <div key={comp} className={styles.compRow}>
                  <span className={styles.compName}>{comp}</span>
                  <span className={styles.compCount}>{matches.length}</span>
                </div>
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
