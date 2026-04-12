// ============================================================
// FÚTBOL SCRAPER — MULTI-SOURCE
// Cascade de 5 fuentes:
//   1. Fotmob     (mejor cobertura ARG, logos, minuto live)
//   2. ESPN       (Liga Profesional oficial, confiable)
//   3. Sofascore  (internacional + suplemento)
//   4. TheSportsDB (fixtures + standings)
//   5. API-Football (si hay API key — más detalle)
// Nunca inventa datos. Si todo falla → vacío.
// ============================================================

import { fetchFotmob } from '../core/fotmob.adapter'
import { fetchESPN } from '../core/espn.adapter'
import { fetchSofascore } from '../core/sofascore.adapter'
import { fetchTSDB, fetchTSDBNext, TSDB_LEAGUES } from '../core/thesportsdb.adapter'
import { fetchApiFootball, fetchApiFootballLive, API_FOOTBALL_LEAGUES } from '../core/apifootball.adapter'
import { getOrFetch, TTL } from '../core/cache'
import type { ScraperResult, UnifiedMatch } from '../core/types'
import { OK_RESULT } from '../core/types'
import { todayART } from '../core/fetcher'

// Argentine league names for filter (lowercase)
const ARG_COMPETITION_KEYWORDS = [
  'liga profesional', 'primera nacional', 'copa argentina',
  'libertadores', 'sudamericana', 'argentina', 'torneo',
  'apertura', 'clausura', 'metropolitano', 'nacional b',
]

// ============================================================
// PUBLIC API
// ============================================================

export async function getFutbolHoy(date?: string): Promise<ScraperResult> {
  const d = date ?? todayART()
  return getOrFetch(`futbol:hoy:${d}`, () => scrapeAllFutbol(d), TTL.SCHEDULED)
}

export async function getFutbolLive(): Promise<ScraperResult> {
  return getOrFetch('futbol:live', () => scrapeLiveFutbol(), TTL.LIVE)
}

// Standings for Liga Profesional
export async function getLPStandings() {
  const { fetchTSDBStandings } = await import('../core/thesportsdb.adapter')
  return fetchTSDBStandings(TSDB_LEAGUES.ARG_PRIMERA)
}

// ============================================================
// SCRAPE ALL SOURCES
// ============================================================

async function scrapeAllFutbol(date: string): Promise<ScraperResult> {
  // All sources in parallel — never wait for one before the next
  const [fotmob, espnLp, espnArg2, espnCl, espnCs, sofa, tsdbLp, apifoot] = await Promise.allSettled([
    fetchFotmob(date),
    fetchESPN('futbol', 'lp', date),
    fetchESPN('futbol', 'arg2', date),
    fetchESPN('futbol', 'cl', date),
    fetchESPN('futbol', 'cs', date),
    fetchSofascore('futbol', date),
    fetchTSDB(TSDB_LEAGUES.ARG_PRIMERA, date),
    fetchApiFootball(API_FOOTBALL_LEAGUES.LP, date),    // only if API key set
  ])

  // Collect by source priority
  const sources: { name: string; matches: UnifiedMatch[]; ok: boolean }[] = [
    extract(fotmob,  'fotmob'),
    extract(espnLp,  'espn:lp'),
    extract(espnArg2,'espn:arg2'),
    extract(espnCl,  'espn:cl'),
    extract(espnCs,  'espn:cs'),
    extract(sofa,    'sofascore'),
    extract(tsdbLp,  'tsdb'),
    extract(apifoot, 'api-football'),
  ]

  const successCount = sources.filter(s => s.ok).length
  console.log(`[futbol] ${successCount}/${sources.length} sources succeeded for ${date}`)

  // Smart merge: most-data-wins deduplication
  const merged = smartMerge(sources.flatMap(s => s.matches))

  // Filter: only Argentine-relevant matches
  const argFiltered = merged.filter(isArgentineMatch)

  const sorted = sortByStatus(argFiltered)

  console.log(`[futbol] ${sorted.length} matches after filter (${merged.length} total merged)`)
  return OK_RESULT('combined', sorted)
}

async function scrapeLiveFutbol(): Promise<ScraperResult> {
  // For live: use fastest sources simultaneously
  const [fotmob, sofa, apiLive] = await Promise.allSettled([
    fetchFotmob(),
    fetchSofascore('futbol'),
    fetchApiFootballLive(API_FOOTBALL_LEAGUES.LP),
  ])

  const allLive: UnifiedMatch[] = [
    ...extract(fotmob, 'fotmob').matches,
    ...extract(sofa, 'sofascore').matches,
    ...extract(apiLive, 'api-football').matches,
  ].filter(m => m.status === 'LIVE' && isArgentineMatch(m))

  const deduped = smartMerge(allLive)
  return OK_RESULT('combined', sortByStatus(deduped))
}

// ============================================================
// SMART MERGE — dedup by fingerprint, prefer richest data
// ============================================================

function smartMerge(matches: UnifiedMatch[]): UnifiedMatch[] {
  const seen = new Map<string, UnifiedMatch>()
  const STATUS_PRIO: Record<string, number> = { LIVE: 0, FINISHED: 1, SCHEDULED: 2, POSTPONED: 3, CANCELLED: 4 }
  // Source quality scores (higher = more trusted for this sport)
  const SOURCE_SCORE: Record<string, number> = {
    'api-football': 10,
    'fotmob':       9,
    'espn:lp':      8,
    'espn:arg2':    7,
    'espn:cl':      7,
    'espn:cs':      7,
    'sofascore':    6,
    'tsdb':         5,
    'thesportsdb':  5,
    'livescore':    4,
  }

  for (const m of matches) {
    const fp = matchFp(m)
    if (!seen.has(fp)) {
      seen.set(fp, m)
      continue
    }

    const existing = seen.get(fp)!
    const existingPrio = STATUS_PRIO[existing.status] ?? 5
    const newPrio = STATUS_PRIO[m.status] ?? 5
    const existingScore = SOURCE_SCORE[existing.source] ?? 0
    const newScore = SOURCE_SCORE[m.source] ?? 0

    // Replace if: better status, or same status but higher source quality, or has logo when existing doesn't
    const shouldReplace =
      newPrio < existingPrio ||
      (newPrio === existingPrio && newScore > existingScore) ||
      (newPrio === existingPrio && newScore === existingScore && m.homeTeam.logo && !existing.homeTeam.logo)

    if (shouldReplace) {
      // Merge best of both: keep logos from whichever has them
      seen.set(fp, {
        ...m,
        homeTeam: { ...m.homeTeam, logo: m.homeTeam.logo ?? existing.homeTeam.logo },
        awayTeam: { ...m.awayTeam, logo: m.awayTeam.logo ?? existing.awayTeam.logo },
        broadcast: [...new Set([...(m.broadcast ?? []), ...(existing.broadcast ?? [])])],
        venue: m.venue ?? existing.venue,
      })
    } else {
      // Keep existing but enrich with logos/venue from new
      seen.set(fp, {
        ...existing,
        homeTeam: { ...existing.homeTeam, logo: existing.homeTeam.logo ?? m.homeTeam.logo },
        awayTeam: { ...existing.awayTeam, logo: existing.awayTeam.logo ?? m.awayTeam.logo },
        broadcast: [...new Set([...(existing.broadcast ?? []), ...(m.broadcast ?? [])])],
        venue: existing.venue ?? m.venue,
      })
    }
  }

  return [...seen.values()]
}

// ============================================================
// HELPERS
// ============================================================

function extract(result: PromiseSettledResult<ScraperResult>, name: string) {
  if (result.status === 'fulfilled' && result.value.ok) {
    return { name, matches: result.value.matches, ok: true }
  }
  if (result.status === 'rejected') {
    console.warn(`[futbol] ${name} rejected:`, result.reason)
  }
  return { name, matches: [] as UnifiedMatch[], ok: false }
}

function isArgentineMatch(m: UnifiedMatch): boolean {
  if (m.isArgentineInvolved) return true
  if (m.country === 'Argentina') return true
  const comp = m.competition.toLowerCase()
  return ARG_COMPETITION_KEYWORDS.some(kw => comp.includes(kw))
}

function matchFp(m: UnifiedMatch): string {
  const h = normalizeTeamName(m.homeTeam.name)
  const a = normalizeTeamName(m.awayTeam.name)
  return `${m.date}:${h}:${a}`
}

function normalizeTeamName(name: string): string {
  return name
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+(club|cf|fc|sc|ac|united|city|river|plate|boca|juniors|de|la|el|los)\s*/gi, ' ')
    .replace(/[^a-z0-9]/g, '')
    .trim()
}

function sortByStatus(matches: UnifiedMatch[]): UnifiedMatch[] {
  const o = { LIVE: 0, SCHEDULED: 1, FINISHED: 2, POSTPONED: 3, CANCELLED: 4 }
  return [...matches].sort((a, b) => {
    const sd = (o[a.status] ?? 5) - (o[b.status] ?? 5)
    if (sd !== 0) return sd
    return a.time.localeCompare(b.time)
  })
}
