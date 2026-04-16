import { api } from '@/lib/api'
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

export default async function Page({ params }: Props) {
  const { sport, slug } = params

  const [groupedRaw, tableRaw] = await Promise.all([
    api.fixtures.groupedBySport(sport, { competition_slug: slug }),
    api.competitions.table(sport, slug),
  ])

  const grouped = normalizeGroupedFixtures(groupedRaw)
  const table = normalizeCompetitionTable(tableRaw, sport, slug)

  const live = grouped.live.map(toCompetitionFixture)
  const upcoming = grouped.upcoming.map(toCompetitionFixture)
  const finished = grouped.finished.map(toCompetitionFixture)

  const standingsGroups = groupStandingsByGroup(table.rows)

  return (
    <div className={styles.page}>
      <h1>{table.competition}</h1>

      <SectionTitle>Tabla de posiciones</SectionTitle>
      {standingsGroups.map((g) => (
        <div key={g.group ?? 'general'}>
          {g.group && <h3>{g.group}</h3>}
          {g.rows.map((r) => (
            <div key={r.team_name}>
              {r.position} - {r.team_name} ({r.points})
            </div>
          ))}
        </div>
      ))}

      <SectionTitle>Fixtures</SectionTitle>
      {[...live, ...upcoming, ...finished].map((m) => (
        <div key={m.id}>
          {m.home_team} vs {m.away_team}
        </div>
      ))}
    </div>
  )
}
