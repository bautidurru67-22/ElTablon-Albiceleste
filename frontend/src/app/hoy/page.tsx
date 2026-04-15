'use client'

import { useEffect, useMemo, useState } from 'react'

type Match = {
  id: string
  sport: string
  competition: string
  home_team: string
  away_team: string
  home_score?: number | null
  away_score?: number | null
  status: 'live' | 'upcoming' | 'finished' | string
  minute?: string | null
  start_time?: string | null
  tv?: string | null
  category?: string
}

type Section = {
  key: string
  title: string
  items: Match[]
}

type HoyData = {
  date: string
  updated_at: string
  matches: Match[]
  sections: Section[]
  summary?: {
    live: number
    upcoming: number
    finished: number
    total: number
  }
  stats?: {
    live: number
    upcoming: number
    finished: number
    total: number
  }
  by_sport?: Record<string, number>
}

export default function HoyPage() {
  const [data, setData] = useState<HoyData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        setLoading(true)
        setError(null)

        // Primero intenta por proxy interno de Vercel
        const urls = [
          '/api/proxy/api/hoy',
          'https://tablon-albiceleste-api-production-7173.up.railway.app/api/hoy',
        ]

        let lastError: string | null = null
        let json: any = null

        for (const url of urls) {
          try {
            const res = await fetch(url, {
              cache: 'no-store',
            })

            if (!res.ok) {
              throw new Error(`HTTP ${res.status}`)
            }

            json = await res.json()

            if (json?.ok && json?.data) {
              break
            } else {
              throw new Error('Respuesta inválida del backend')
            }
          } catch (e: any) {
            lastError = e?.message || 'Error desconocido'
          }
        }

        if (!json?.ok || !json?.data) {
          throw new Error(lastError || 'No se pudo cargar la agenda')
        }

        if (!cancelled) {
          setData(json.data)
        }
      } catch (e: any) {
        if (!cancelled) {
          setError(e?.message || 'No se pudo cargar la agenda')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    load()

    return () => {
      cancelled = true
    }
  }, [])

  const summary = useMemo(() => {
    return data?.summary || data?.stats || { live: 0, upcoming: 0, finished: 0, total: 0 }
  }, [data])

  const bySport = data?.by_sport || {}

  const liveMatches = (data?.matches || []).filter((m) => m.status === 'live')
  const sections = data?.sections || []

  return (
    <div className="max-w-[980px] mx-auto px-4 py-4">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h1 className="text-[18px] font-bold tracking-tight text-[#0b2c5f]">
            HOY - DONDE JUEGA ARGENTINA
          </h1>
          {data?.updated_at && (
            <p className="text-[11px] text-[#6b7280] mt-1">
              Actualizado: {formatUpdatedAt(data.updated_at)}
            </p>
          )}
        </div>

        {data?.date && (
          <div className="text-[11px] text-[#6b7280] whitespace-nowrap">
            {formatDateEs(data.date)}
          </div>
        )}
      </div>

      {loading && (
        <div className="text-[13px] text-[#111827]">
          Cargando agenda...
        </div>
      )}

      {!loading && error && (
        <div className="border border-red-200 bg-red-50 rounded px-3 py-3 text-[13px] text-red-700">
          No se pudo cargar la agenda. {error}
        </div>
      )}

      {!loading && !error && data && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_170px] gap-4">
          <div>
            <SectionBlock
              title="EN VIVO"
              accent="red"
              badgeCount={liveMatches.length}
              emptyText="Sin partidos en vivo."
              matches={liveMatches}
            />

            {sections.map((section) => (
              <SectionBlock
                key={section.key}
                title={getSectionTitle(section.key)}
                accent={getSectionAccent(section.key)}
                badgeCount={section.items?.length || 0}
                matches={section.items || []}
              />
            ))}
          </div>

          <aside className="space-y-3">
            <SidebarBox title="RESUMEN DE HOY">
              <SidebarRow label="En vivo" value={summary.live} />
              <SidebarRow label="Próximos" value={summary.upcoming} />
              <SidebarRow label="Finalizados" value={summary.finished} />
              <SidebarRow label="Total" value={summary.total} />
            </SidebarBox>

            <SidebarBox title="POR DEPORTE">
              {Object.keys(bySport).length === 0 ? (
                <div className="text-[11px] text-[#6b7280]">Sin datos.</div>
              ) : (
                Object.entries(bySport).map(([sport, count]) => (
                  <SidebarRow key={sport} label={sport} value={count} />
                ))
              )}
            </SidebarBox>
          </aside>
        </div>
      )}
    </div>
  )
}

function SectionBlock({
  title,
  matches,
  badgeCount,
  accent,
  emptyText,
}: {
  title: string
  matches: Match[]
  badgeCount?: number
  accent?: 'red' | 'green' | 'blue' | 'neutral'
  emptyText?: string
}) {
  const accentClasses =
    accent === 'red'
      ? 'border-l-red-500'
      : accent === 'green'
      ? 'border-l-green-500'
      : accent === 'blue'
      ? 'border-l-blue-500'
      : 'border-l-slate-400'

  return (
    <section className="mb-3">
      <div className={`border border-[#c9d5e6] border-l-4 ${accentClasses} rounded-t bg-white`}>
        <div className="flex items-center justify-between px-3 py-2 border-b border-[#dbe4f0]">
          <h2 className="text-[13px] font-bold tracking-wide text-[#111827] uppercase">
            {title}
          </h2>
          <span className="min-w-[18px] h-[18px] px-1 rounded-full border border-[#9fc0e8] bg-[#eef6ff] text-[10px] leading-[16px] text-[#295a9b] text-center">
            {badgeCount || 0}
          </span>
        </div>

        {matches.length === 0 ? (
          <div className="px-3 py-2 text-[11px] text-[#6b7280]">
            {emptyText || 'Sin datos.'}
          </div>
        ) : (
          <div>
            {matches.map((match, idx) => (
              <MatchRow key={`${match.id}-${idx}`} match={match} />
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

function MatchRow({ match }: { match: Match }) {
  const isLive = match.status === 'live'
  const isFinished = match.status === 'finished'
  const scoreVisible =
    match.home_score !== null &&
    match.home_score !== undefined &&
    match.away_score !== null &&
    match.away_score !== undefined

  return (
    <div className="grid grid-cols-[1fr_auto_1fr_auto] items-center gap-2 px-3 py-2 border-b last:border-b-0 border-[#e5edf7] text-[12px] bg-white">
      <div>
        <div className="text-[10px] uppercase tracking-wide text-[#5b6b82] mb-1">
          {match.competition || 'Fútbol'}
        </div>
        <div className="text-[#111827]">{match.home_team}</div>
      </div>

      <div className="text-center font-bold text-[#0b2c5f] min-w-[40px]">
        {scoreVisible ? `${match.home_score} - ${match.away_score}` : '---'}
      </div>

      <div className="text-[#111827]">{match.away_team}</div>

      <div className="text-right min-w-[72px]">
        <div className="text-[11px] font-semibold text-[#111827]">
          {isLive ? (match.minute || 'EN VIVO') : match.start_time || '-'}
        </div>
        <div className="text-[10px] text-[#6b7280]">
          {isLive ? 'EN VIVO' : isFinished ? 'FINAL' : (match.tv || '')}
        </div>
      </div>
    </div>
  )
}

function SidebarBox({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="border border-[#c9d5e6] rounded bg-white">
      <div className="px-3 py-2 border-b border-[#dbe4f0] text-[11px] font-bold tracking-[1px] text-[#5b6b82] uppercase">
        {title}
      </div>
      <div className="px-3 py-2">{children}</div>
    </div>
  )
}

function SidebarRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex justify-between items-center text-[12px] py-1 border-b last:border-b-0 border-[#eef3f8]">
      <span className="text-[#4b5563]">{label}</span>
      <span className="font-semibold text-[#111827]">{value}</span>
    </div>
  )
}

function getSectionTitle(key: string) {
  switch (key) {
    case 'selecciones':
      return 'SELECCIONES NACIONALES'
    case 'exterior':
      return 'ARGENTINOS EN EL EXTERIOR'
    case 'ligas_locales':
      return 'LIGAS LOCALES'
    case 'motorsport':
      return 'MOTORSPORT ARGENTINO'
    default:
      return key.toUpperCase()
  }
}

function getSectionAccent(key: string): 'red' | 'green' | 'blue' | 'neutral' {
  switch (key) {
    case 'selecciones':
      return 'blue'
    case 'exterior':
      return 'green'
    case 'ligas_locales':
      return 'blue'
    case 'motorsport':
      return 'green'
    default:
      return 'neutral'
  }
}

function formatDateEs(dateStr: string) {
  try {
    const date = new Date(`${dateStr}T12:00:00`)
    return date.toLocaleDateString('es-AR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    })
  } catch {
    return dateStr
  }
}

function formatUpdatedAt(updatedAt: string) {
  try {
    const date = new Date(updatedAt)
    return date.toLocaleString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return updatedAt
  }
}
