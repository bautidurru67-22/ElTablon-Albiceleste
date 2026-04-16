import { Fixture, GroupedFixtures } from '@/types/fixture'
import { CompetitionTableResponse, StandingsRow } from '@/types/standings'
import SectionTitle from '@/components/SectionTitle'
import SportBadge from '@/components/SportBadge'
import { sl } from '@/lib/matches'
import styles from '@/app/deporte/[sport]/deporte.module.css'

export const revalidate = 30
export const dynamic = 'force-dynamic'

interface Props {
  params: { sport: string; slug: string }
}

type CompetitionFixture = {
  id: string
  competition: string
  home_team: string
  away_team: string
  home_score: number | null
  away_score: number | null
  status: Fixture['status']
  minute: string | null
  start_time: string | null
  broadcast: string | null
}

function toCompetitionFixture(f: Fixture): CompetitionFixture {
  return {
    id: f.id,
    competition: f.competition_name,
    home_team: f.home_team,
    away_team: f.away_team,
    home_score: f.home_score,
    away_score: f.away_score,
    status: f.status,
    minute: f.is_live ? 'EN VIVO' : null,
    start_time: f.start_time,
    broadcast: f.broadcasts?.join(' · ') ?? null,
  }
}

function normalizeGroupedFixtures(value: unknown): GroupedFixtures {
  const empty: GroupedFixtures = { live: [], upcoming: [], finished: [] }
  if (!value || typeof value !== 'object') return empty

  const obj = value as Record<string, unknown>
  return {
    live: Array.isArray(obj.live) ? (obj.live as Fixture[]) : [],
    upcoming: Array.isArray(obj.upcoming) ? (obj.upcoming as Fixture[]) : [],
    finished: Array.isArray(obj.finished) ? (obj.finished as Fixture[]) : [],
  }
}

function normalizeCompetitionTable(value: unknown, sport: string, slug: string): CompetitionTableResponse {
  const fallback: CompetitionTableResponse = {
    sport,
    slug,
    competition: slug.replace(/-/g, ' '),
    updated_at: new Date().toISOString(),
    rows: [],
  }

  if (!value || typeof value !== 'object') return fallback

  const obj = value as Record<string, unknown>
  return {
    sport: typeof obj.sport === 'string' ? obj.sport : fallback.sport,
    slug: typeof obj.slug === 'string' ? obj.slug : fallback.slug,
    competition: typeof obj.competition === 'string' ? obj.competition : fallback.competition,
    updated_at: typeof obj.updated_at === 'string' ? obj.updated_at : fallback.updated_at,
    rows: Array.isArray(obj.rows) ? (obj.rows as StandingsRow[]) : [],
  }
}

function groupStandingsByGroup(rows: StandingsRow[]) {
  const grouped = rows.reduce<Map<string, StandingsRow[]>>((acc, row) => {
    const key = row.group_name ?? '__single__'
    const list = acc.get(key) ?? []
    list.push(row)
    acc.set(key, list)
    return acc
  }, new Map())

  return Array.from(grouped.entries()).map(([key, rows]) => ({
    group: key === '__single__' ? null : key,
    rows,
  }))
}

function FixturesBlock({ title, fixtures }: { title: string; fixtures: CompetitionFixture[] }) {
  if (fixtures.length === 0) return null

  return (
    <section className={styles.section}>
      <SectionTitle count={fixtures.length}>{title}</SectionTitle>
      <div className={styles.matchTable}>
        <div className={styles.matchTableHeader}>
          <span>Hora</span>
          <span>Competencia</span>
          <span className={styles.colTeams}>Partido</span>
          <span className={styles.colBcast}>Dónde ver</span>
        </div>
        {fixtures.map((m) => (
          <div
            key={m.id}
            className={`${styles.matchTableRow} ${
              m.status === 'live' ? styles.rowLive : m.status === 'finished' ? styles.rowFinished : ''
            }`}
          >
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
              <span>{m.home_team}</span>
              {m.home_score != null ? (
                <span className={styles.scoreInline}>
                  {m.home_score}-{m.away_score}
                </span>
              ) : (
                <span className={styles.vsInline}>vs</span>
              )}
              <span>{m.away_team}</span>
            </span>
            <span className={styles.colBcast}>{m.broadcast ?? '–'}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export default async function Page({ params }: Props) {
  const { sport, slug } = params
  const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

  async function fetchGrouped() {
    try {
      const res = await fetch(
        `${API_BASE}/api/matches/fixtures/${sport}?competition_slug=${slug}&grouped=true`,
        { cache: 'no-store' }
      )
      if (!res.ok) return { live: [], upcoming: [], finished: [] }
      return await res.json()
    } catch {
      return { live: [], upcoming: [], finished: [] }
    }
  }

  async function fetchTable() {
    try {
      const res = await fetch(
        `${API_BASE}/api/competitions/${sport}/${slug}/table`,
        { cache: 'no-store' }
      )
      if (!res.ok) {
        return {
          sport,
          slug,
          competition: slug.replace(/-/g, ' '),
          updated_at: new Date().toISOString(),
          rows: [],
        }
      }
      return await res.json()
    } catch {
      return {
        sport,
        slug,
        competition: slug.replace(/-/g, ' '),
        updated_at: new Date().toISOString(),
        rows: [],
      }
    }
  }

  const [groupedRaw, tableRaw] = await Promise.all([fetchGrouped(), fetchTable()])

  const grouped = normalizeGroupedFixtures(groupedRaw)
  const table = normalizeCompetitionTable(tableRaw, sport, slug)

  const live = grouped.live.map(toCompetitionFixture)
  const upcoming = grouped.upcoming.map(toCompetitionFixture)
  const finished = grouped.finished.map(toCompetitionFixture)
  const totalFixtures = live.length + upcoming.length + finished.length

  const standingsGroups = groupStandingsByGroup(table.rows)
  const today = new Date().toLocaleDateString('es-AR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

  return (
    <div className={styles.page}>
      <div className={styles.sportHeader}>
        <div className={styles.sportHeaderLeft}>
          <div className={styles.sportIcon}>
            <SportBadge sport={sport} />
          </div>
          <div>
            <h1 className={styles.sportTitle}>{table.competition}</h1>
            <p className={styles.sportSubtitle}>
              {sl(sport)} · {slug}
            </p>
          </div>
        </div>
        <div className={styles.sportHeaderRight}>
          <span className={styles.dateLabel}>{today}</span>
        </div>
      </div>

      <div className={styles.layout}>
        <div className={styles.main}>
          <section className={styles.section}>
            <SectionTitle>Tabla de posiciones</SectionTitle>
            {table.rows.length === 0 ? (
              <div className={styles.noMatches}>
                <p>Sin tabla disponible para esta competencia por ahora.</p>
              </div>
            ) : (
              standingsGroups.map((groupBlock) => (
                <div key={groupBlock.group ?? 'general'} className={styles.matchTable}>
                  {groupBlock.group ? <h3 className={styles.compName}>{groupBlock.group}</h3> : null}
                  <div className={styles.matchTableHeader}>
                    <span>Pos</span>
                    <span>Equipo</span>
                    <span>PJ</span>
                    <span>G</span>
                    <span>E</span>
                    <span>P</span>
                    <span>GF</span>
                    <span>GC</span>
                    <span>DG</span>
                    <span>Pts</span>
                  </div>
                  {groupBlock.rows.map((row) => (
                    <div
                      key={`${groupBlock.group ?? 'general'}-${row.team_name}`}
                      className={styles.matchTableRow}
                    >
                      <span>{row.position}</span>
                      <span>{row.team_name}</span>
                      <span>{row.played}</span>
                      <span>{row.won}</span>
                      <span>{row.drawn}</span>
                      <span>{row.lost}</span>
                      <span>{row.goals_for}</span>
                      <span>{row.goals_against}</span>
                      <span>{row.goal_diff}</span>
                      <span>{row.points}</span>
                    </div>
                  ))}
                </div>
              ))
            )}
          </section>

          {totalFixtures === 0 ? (
            <section className={styles.section}>
              <SectionTitle>Fixtures</SectionTitle>
              <div className={styles.noMatches}>
                <p>Sin fixtures disponibles para esta competencia por ahora.</p>
              </div>
            </section>
          ) : (
            <>
              <FixturesBlock title="En Vivo" fixtures={live} />
              <FixturesBlock title="Próximos" fixtures={upcoming} />
              <FixturesBlock title="Finalizados" fixtures={finished} />
            </>
          )}
        </div>

        <aside className={styles.sidebar}>
          <div className={styles.sideCard}>
            <SectionTitle>Resumen</SectionTitle>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>En vivo</span>
              <span className={styles.statVal}>{live.length}</span>
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
              <span className={styles.statLabel}>Equipos en tabla</span>
              <span className={styles.statVal}>{table.rows.length}</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
