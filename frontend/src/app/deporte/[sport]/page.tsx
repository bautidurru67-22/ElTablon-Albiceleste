import { api } from '@/lib/api'
import { sortMatches, groupByCompetition, sl } from '@/lib/matches'
import { Match } from '@/types/match'
import { Player } from '@/types/player'
import SectionTitle from '@/components/SectionTitle'
import CompetitionGroup from '@/components/CompetitionGroup'
import MatchRow from '@/components/MatchRow'
import SportBadge from '@/components/SportBadge'
import styles from './deporte.module.css'
import FollowButton from '@/components/FollowButton'

export const revalidate = 30

interface Props {
  params: { sport: string }
}

// Config por deporte: título, descripción, jugadores destacados (placeholder si no hay API)
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

// Jugadores placeholder por deporte — se reemplaza con API real en Prompt 6+
const SPORT_PLAYERS: Record<string, Array<{ name: string; detail: string; stat: string; flag: string }>> = {
  tenis: [
    { name: 'Francisco Cerúndolo',  detail: 'ATP #10',  stat: '15-6',  flag: '🇦🇷' },
    { name: 'Tomás Etcheverry',     detail: 'ATP #30',  stat: '9-6',   flag: '🇦🇷' },
    { name: 'Sebastián Báez',       detail: 'ATP #53',  stat: '16-6',  flag: '🇦🇷' },
    { name: 'Mariano Navone',       detail: 'ATP #68',  stat: '8-4',   flag: '🇦🇷' },
    { name: 'Horacio Zeballos',     detail: 'ATP Dobles #7', stat: '12-3', flag: '🇦🇷' },
  ],
  basquet: [
    { name: 'Facundo Campazzo',    detail: 'Dallas Mavericks · NBA',  stat: '14.2 pts', flag: '🇺🇸' },
    { name: 'Leandro Bolmaro',     detail: 'FC Barcelona · ACB',      stat: '11.8 pts', flag: '🇪🇸' },
    { name: 'Nico Laprovíttola',   detail: 'Laga Basket · ACB',       stat: '9.4 pts',  flag: '🇪🇸' },
  ],
  futbol: [
    { name: 'Lionel Messi',        detail: 'Inter Miami · MLS',       stat: '106 goles ARG', flag: '🇺🇸' },
    { name: 'Lautaro Martínez',    detail: 'Inter Milano · Serie A',  stat: '26 goles',      flag: '🇮🇹' },
    { name: 'Julián Álvarez',      detail: 'Atlético Madrid · LaLiga',stat: '18 goles',      flag: '🇪🇸' },
    { name: 'Alejandro Garnacho',  detail: 'Manchester United · PL',  stat: '12 goles',      flag: '🏴󠁧󠁢󠁥󠁮󠁧󠁿' },
  ],
  hockey: [
    { name: 'Las Leonas',          detail: 'Selección Femenina',       stat: '4 Mundiales',   flag: '🇦🇷' },
    { name: 'Los Leones',          detail: 'Selección Masculina',      stat: 'FIH Pro League', flag: '🇦🇷' },
    { name: 'Gonzalo Peillat',     detail: 'Alemania · International', stat: 'Olímpico 2016',  flag: '🇩🇪' },
  ],
  rugby: [
    { name: 'Los Pumas',           detail: 'Selección Argentina',       stat: '#5 World Rugby', flag: '🇦🇷' },
    { name: 'Nico Sánchez',        detail: 'Fly-half · Los Pumas',     stat: '867 pts ARG',   flag: '🇦🇷' },
    { name: 'Emiliano Boffelli',   detail: 'Edinburgh · URC',          stat: 'Top try scorer', flag: '🏴󠁧󠁢󠁳󠁣󠁴󠁿' },
  ],
  motorsport: [
    { name: 'Franco Colapinto',    detail: 'F1 — Alpine',              stat: 'Rookie 2024',   flag: '🇦🇷' },
  ],
  golf: [
    { name: 'Emiliano Grillo',     detail: 'PGA Tour',                 stat: 'OWGR #85',      flag: '🇺🇸' },
    { name: 'Fabián Gómez',        detail: 'PGA / Korn Ferry',         stat: 'OWGR #210',     flag: '🇺🇸' },
  ],
  boxeo: [
    { name: 'Brian Castaño',       detail: 'Súper Welter — AMB/CMB',  stat: 'Ex-campeón',    flag: '🇦🇷' },
  ],
  polo: [
    { name: 'Adolfo Cambiaso',     detail: 'La Dolfina',              stat: '10 de hándicap', flag: '🇦🇷' },
    { name: 'Facundo Pieres',      detail: 'Ellerstina',              stat: '10 de hándicap', flag: '🇦🇷' },
  ],
}

export default async function DeportePage({ params }: Props) {
  const sport = params.sport
  const config = SPORT_CONFIG[sport] ?? {
    title: `${sl(sport)} Argentino`,
    subtitle: 'Equipos y jugadores argentinos',
    hasPlayers: false,
  }

  // Datos en paralelo
  const [allToday, liveMatches, playersAbroad] = await Promise.all([
    api.matches.today(sport),
    api.matches.live(sport),
    config.hasPlayers ? api.players.abroad() : Promise.resolve([]),
  ])

  const sorted   = sortMatches(allToday)
  const live     = sorted.filter(m => m.status === 'live')
  const upcoming = sorted.filter(m => m.status === 'upcoming')
  const finished = sorted.filter(m => m.status === 'finished')
  const byComp   = groupByCompetition(sorted)

  // Jugadores de este deporte
  const sportPlayers = SPORT_PLAYERS[sport] ?? []
  const abroadForSport: Player[] = (playersAbroad as Player[]).filter(p => p.sport === sport)

  const today = new Date().toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  return (
    <div className={styles.page}>
      {/* Sport header */}
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

      <div className={styles.layout}>
        <div className={styles.main}>

          {/* EN VIVO */}
          {live.length > 0 && (
            <section className={styles.section}>
              <SectionTitle live count={live.length}>En Vivo</SectionTitle>
              {Object.entries(groupByCompetition(live)).map(([comp, matches]) => (
                <CompetitionGroup key={comp} competition={comp} matches={matches} />
              ))}
            </section>
          )}

          {/* PARTIDOS DEL DÍA — tabla densa */}
          {sorted.length > 0 ? (
            <section className={styles.section}>
              <SectionTitle count={sorted.length}>Partidos del Día</SectionTitle>
              <div className={styles.matchTable}>
                <div className={styles.matchTableHeader}>
                  <span>Hora</span>
                  <span>Competencia</span>
                  <span className={styles.colTeams}>Partido</span>
                  <span className={styles.colBcast}>Donde ver</span>
                </div>
                {sorted.map(m => (
                  <div key={m.id} className={`${styles.matchTableRow} ${m.status === 'live' ? styles.rowLive : m.status === 'finished' ? styles.rowFinished : ''}`}>
                    <span className={styles.colTime}>
                      {m.status === 'live' ? (
                        <span className={styles.liveMin}>
                          <span className={styles.dot} />
                          {m.minute ?? 'EN VIVO'}
                        </span>
                      ) : m.status === 'finished' ? (
                        <span className={styles.finalTag}>Final</span>
                      ) : (
                        <span className={styles.timeStr}>{m.start_time ?? '–'}</span>
                      )}
                    </span>
                    <span className={styles.colComp}>{m.competition}</span>
                    <span className={styles.colTeams}>
                      <span className={m.status === 'finished' && (m.home_score ?? 0) > (m.away_score ?? 0) ? styles.winner : ''}>
                        {m.home_team}
                      </span>
                      {m.home_score != null ? (
                        <span className={styles.scoreInline}>{m.home_score}-{m.away_score}</span>
                      ) : (
                        <span className={styles.vsInline}>vs</span>
                      )}
                      <span className={m.status === 'finished' && (m.away_score ?? 0) > (m.home_score ?? 0) ? styles.winner : ''}>
                        {m.away_team}
                      </span>
                    </span>
                    <span className={styles.colBcast}>{m.broadcast ?? '–'}</span>
                  </div>
                ))}
              </div>
            </section>
          ) : (
            <div className={styles.noMatches}>
              <p>No hay partidos de {config.title} para hoy.</p>
            </div>
          )}

          {/* JUGADORES DESTACADOS */}
          {sportPlayers.length > 0 && (
            <section className={styles.section}>
              <SectionTitle>Jugadores Destacados</SectionTitle>
              <div className={styles.playersGrid}>
                {sportPlayers.map(p => (
                  <div key={p.name} className={styles.playerCard}>
                    <div className={styles.playerAvatar}>
                      {p.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
                    </div>
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

          {/* ARGENTINOS EN EL MUNDO — desde API real */}
          {abroadForSport.length > 0 && (
            <section className={styles.section}>
              <SectionTitle>Argentinos en el Mundo</SectionTitle>
              <div className={styles.abroadGrid}>
                {abroadForSport.map(p => (
                  <div key={p.id} className={`${styles.playerCard} ${p.playing_today ? styles.playerCardPlaying : ''}`}>
                    <div className={styles.playerAvatar}>
                      {p.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
                    </div>
                    <div className={styles.playerInfo}>
                      <span className={styles.playerName}>
                        {p.name}
                        {p.playing_today && <span className={styles.playingBadge}>HOY</span>}
                      </span>
                      <FollowButton tipo="jugador" entityId={p.id} />
                      <span className={styles.playerDetail}>{p.team} · {p.league} {p.flag}</span>
                    </div>
                    <div className={styles.playerStat}>
                      <span className={styles.playerStatVal}>{p.stat_value}</span>
                      <span className={styles.playerStatLabel}>{p.stat_label}</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Sidebar */}
        <aside className={styles.sidebar}>

          {/* Stats del día */}
          <div className={styles.sideCard}>
            <SectionTitle>Hoy en {sl(sport)}</SectionTitle>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>En vivo</span>
              <span className={styles.statVal} style={{ color: live.length > 0 ? 'var(--color-live)' : undefined }}>
                {live.length}
              </span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Próximos</span>
              <span className={styles.statVal}>{upcoming.length}</span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Finalizados</span>
              <span className={styles.statVal}>{finished.length}</span>
            </div>
          </div>

          {/* Competencias del día */}
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

          {/* Ranking placeholder */}
          {config.rankingLabel && (
            <div className={styles.sideCard}>
              <SectionTitle>{config.rankingLabel}</SectionTitle>
              {sportPlayers.slice(0, 4).map((p, i) => (
                <div key={p.name} className={styles.rankRow}>
                  <span className={styles.rankPos}>{i + 1}</span>
                  <span className={styles.rankName}>{p.name}</span>
                  <span className={styles.rankStat}>{p.stat}</span>
                </div>
              ))}
              {sportPlayers.length === 0 && (
                <p className={styles.placeholder}>Datos completos próximamente.</p>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
