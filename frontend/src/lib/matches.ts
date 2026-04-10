import { Match } from '@/types/match'

export const STATUS_ORDER = { live: 0, upcoming: 1, finished: 2 } as const

export function sortMatches(matches: Match[]): Match[] {
  return [...matches].sort((a, b) => {
    const s = STATUS_ORDER[a.status] - STATUS_ORDER[b.status]
    if (s !== 0) return s
    return (a.start_time ?? '').localeCompare(b.start_time ?? '')
  })
}

export function groupByCompetition(matches: Match[]): Record<string, Match[]> {
  return matches.reduce<Record<string, Match[]>>((acc, m) => {
    const key = m.competition
    if (!acc[key]) acc[key] = []
    acc[key].push(m)
    return acc
  }, {})
}

export function groupBySport(matches: Match[]): Record<string, Match[]> {
  return matches.reduce<Record<string, Match[]>>((acc, m) => {
    if (!acc[m.sport]) acc[m.sport] = []
    acc[m.sport].push(m)
    return acc
  }, {})
}

export function groupByRelevanceThenCompetition(matches: Match[]) {
  const sorted = sortMatches(matches)
  const seleccion = sorted.filter(m => m.argentina_relevance === 'seleccion')
  const club      = sorted.filter(m => m.argentina_relevance === 'club_arg')
  const jugador   = sorted.filter(m => m.argentina_relevance === 'jugador_arg')
  return { seleccion, club, jugador }
}

export const SPORT_LABELS: Record<string, string> = {
  futbol: 'Fútbol', tenis: 'Tenis', basquet: 'Básquet',
  hockey: 'Hockey', rugby: 'Rugby', voley: 'Vóley',
  boxeo: 'Boxeo', futsal: 'Futsal', polo: 'Polo',
  golf: 'Golf', handball: 'Handball', motorsport: 'Automovilismo',
  motogp: 'MotoGP', olimpicos: 'Olímpicos', esports: 'Esports',
  dakar: 'Dakar',
}

export function sl(sport: string) {
  return SPORT_LABELS[sport] ?? sport
}
