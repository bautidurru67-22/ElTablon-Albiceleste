'use client'

import { useEffect, useState } from 'react'

const API_URL = 'https://tablon-albiceleste-api-production-7173.up.railway.app/api/hoy'

export default function HoyPage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(API_URL)
      .then(res => res.json())
      .then(json => {
        setData(json.data)
        setLoading(false)
      })
  }, [])

  if (loading) return <div className="p-4">Cargando agenda...</div>

  const sections = data?.sections || []
  const summary = data?.summary || {}

  return (
    <div className="p-4 max-w-5xl mx-auto">

      {/* HEADER */}
      <h1 className="text-2xl font-bold mb-2">
        HOY – DONDE JUEGA ARGENTINA
      </h1>

      <p className="text-sm text-gray-500 mb-6">
        Actualizado: {data.updated_at}
      </p>

      {/* EN VIVO */}
      <Block
        title="🔴 EN VIVO"
        matches={data.matches.filter((m: any) => m.status === 'live')}
      />

      {/* SECCIONES */}
      {sections.map((section: any) => (
        <Block
          key={section.key}
          title={getTitle(section.key)}
          matches={section.items}
        />
      ))}

      {/* SIDEBAR SIMPLE */}
      <div className="mt-8 p-4 border rounded">
        <h3 className="font-bold mb-2">Resumen</h3>
        <p>En vivo: {summary.live}</p>
        <p>Próximos: {summary.upcoming}</p>
        <p>Finalizados: {summary.finished}</p>
        <p>Total: {summary.total}</p>
      </div>

    </div>
  )
}

/* ========================= */

function Block({ title, matches }: any) {
  if (!matches || matches.length === 0) return null

  return (
    <div className="mb-6">
      <h2 className="text-lg font-bold mb-2">{title}</h2>

      <div className="border rounded">
        {matches.map((m: any) => (
          <MatchRow key={m.id} match={m} />
        ))}
      </div>
    </div>
  )
}

function MatchRow({ match }: any) {
  return (
    <div className="flex justify-between border-b px-3 py-2 text-sm">

      <div>
        <div className="font-medium">
          {match.home_team} vs {match.away_team}
        </div>

        <div className="text-xs text-gray-500">
          {match.competition}
        </div>
      </div>

      <div className="text-right">
        <div>
          {match.status === 'live'
            ? `🔴 ${match.minute || ''}`
            : match.start_time || '-'}
        </div>

        <div className="text-xs text-gray-500">
          {match.tv || ''}
        </div>
      </div>

    </div>
  )
}

function getTitle(key: string) {
  switch (key) {
    case 'selecciones':
      return '🇦🇷 Selecciones nacionales'
    case 'exterior':
      return '🌍 Argentinos en el exterior'
    case 'ligas_locales':
      return '🏆 Ligas locales'
    case 'motorsport':
      return '🏁 Motorsport argentino'
    default:
      return key
  }
}
