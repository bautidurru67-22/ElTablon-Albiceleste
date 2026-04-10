export type MatchStatus = 'live' | 'upcoming' | 'finished'
export type ArgentinaRelevance = 'seleccion' | 'club_arg' | 'jugador_arg' | 'none'

export interface Match {
  id: string
  sport: string
  competition: string
  home_team: string
  away_team: string
  home_score: number | null
  away_score: number | null
  status: MatchStatus
  minute: string | null
  datetime: string | null
  start_time: string | null
  argentina_relevance: ArgentinaRelevance
  argentina_team: string | null
  broadcast: string | null
}
