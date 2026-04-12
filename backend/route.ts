import { NextResponse } from 'next/server'
import { todayART } from '@/lib/scrapers/core/fetcher'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

// ============================================================
// FALLBACK CHAIN DOCUMENTATION
// ============================================================
//
// FÚTBOL:
//   1. Fotmob      — cobertura ARG completa, logos HD, minuto live exacto
//   2. ESPN (LP)   — Liga Profesional Argentina, muy confiable
//   3. ESPN (CL/CS)— Copa Libertadores / Sudamericana
//   4. Sofascore   — internacional + suplemento
//   5. TheSportsDB — fixtures + standings
//   6. API-Football— si API_KEY disponible (100 req/día gratis)
//
// TENIS:
//   1. Sofascore   — ATP, WTA, Challenger, ITF
//   2. Livescore   — suplemento + sets
//   3. ESPN ATP/WTA— backup
//
// BÁSQUET:
//   1. ESPN (LNB)  — Liga Nacional Argentina
//   2. ESPN (NBA)  — NBA
//   3. Sofascore   — suplemento
//   4. Livescore   — cuartos detallados
//   5. TheSportsDB — LNB histórico
//
// RUGBY:
//   1. Sofascore   — principal (Super Rugby, URC, etc.)
//   2. Livescore   — suplemento
//   3. ESPN (SR)   — Super Rugby Américas
//
// HOCKEY:
//   1. Sofascore   — FIH Pro League (field-hockey slug)
//   2. Livescore   — suplemento
//
// Si TODAS fallan → devuelve [] con ok:false (nunca datos falsos)
// ============================================================

interface SourceCheck {
  name: string
  url: string
  headers?: Record<string, string>
  validate: (data: unknown) => boolean
}

const SOURCES: SourceCheck[] = [
  {
    name: 'sofascore',
    url: `https://api.sofascore.com/api/v1/sport/football/scheduled-events/${todayART()}`,
    headers: { 'Referer': 'https://www.sofascore.com/' },
    validate: (d: any) => Array.isArray(d?.events),
  },
  {
    name: 'espn:lp',
    url: `https://site.api.espn.com/apis/site/v2/sports/soccer/arg.1/scoreboard?dates=${todayART().replace(/-/g,'')}&limit=50`,
    validate: (d: any) => Array.isArray(d?.events),
  },
  {
    name: 'fotmob',
    url: `https://www.fotmob.com/api/matches?date=${todayART().replace(/-/g,'')}`,
    headers: { 'Referer': 'https://www.fotmob.com/' },
    validate: (d: any) => Array.isArray(d?.leagues),
  },
  {
    name: 'thesportsdb',
    url: `https://www.thesportsdb.com/api/v1/json/3/eventsday.php?d=${todayART()}&l=4406`,
    validate: (d: any) => d !== null,
  },
  {
    name: 'livescore',
    url: (() => {
      const [y,m,day] = todayART().split('-')
      return `https://prod-public-api.livescore.com/v1/api/getsporteventlist/soccer/${day}/${m}/${y}`
    })(),
    headers: { 'Referer': 'https://www.livescore.com/' },
    validate: (d: any) => Array.isArray(d?.Stages),
  },
]

async function checkSource(s: SourceCheck): Promise<{
  name: string; status: 'ok' | 'error' | 'timeout'
  latencyMs: number; detail?: string
}> {
  const t0 = Date.now()
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 6000)

  try {
    const res = await fetch(s.url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; TablonBot/1.0)',
        ...(s.headers ?? {}),
      },
      signal: controller.signal,
      next: { revalidate: 0 },
    })
    clearTimeout(timer)
    const latencyMs = Date.now() - t0

    if (!res.ok) {
      return { name: s.name, status: 'error', latencyMs, detail: `HTTP ${res.status}` }
    }

    const data = await res.json().catch(() => null)
    const valid = s.validate(data)

    return {
      name: s.name,
      status: valid ? 'ok' : 'error',
      latencyMs,
      detail: valid ? undefined : 'Unexpected response shape',
    }
  } catch (err: unknown) {
    clearTimeout(timer)
    const latencyMs = Date.now() - t0
    const msg = err instanceof Error ? err.message : String(err)
    const isTimeout = msg.includes('abort') || msg.includes('timeout')
    return { name: s.name, status: isTimeout ? 'timeout' : 'error', latencyMs, detail: msg }
  }
}

export async function GET() {
  const results = await Promise.all(SOURCES.map(checkSource))

  const allOk     = results.filter(r => r.status === 'ok').length
  const anyOk     = allOk > 0
  const overallOk = allOk >= 2  // at least 2 sources working = healthy

  return NextResponse.json({
    status:   overallOk ? 'healthy' : anyOk ? 'degraded' : 'down',
    date:     todayART(),
    sources:  results,
    summary: {
      ok:      allOk,
      error:   results.filter(r => r.status === 'error').length,
      timeout: results.filter(r => r.status === 'timeout').length,
      total:   results.length,
    },
    fallbackChain: {
      futbol:  ['fotmob', 'espn:lp', 'espn:arg2', 'espn:cl', 'sofascore', 'thesportsdb', 'api-football'],
      tenis:   ['sofascore', 'livescore', 'espn:atp', 'espn:wta'],
      basquet: ['espn:lnb', 'espn:nba', 'sofascore', 'livescore', 'thesportsdb'],
      rugby:   ['sofascore', 'livescore', 'espn:sr'],
      hockey:  ['sofascore (field-hockey)', 'livescore'],
    },
    note: 'Si todas las fuentes fallan, el endpoint devuelve [] (nunca datos inventados)',
    timestamp: new Date().toISOString(),
  })
}
