import Link from 'next/link'
import { api } from '@/lib/api'
import styles from './deporte.module.css'

export const revalidate = 30
export const dynamic = 'force-dynamic'

const COMPETITIONS: Record<string, Array<{slug: string; label: string}>> = {
  futbol: [
    { slug: 'liga-profesional-argentina', label: 'Liga Profesional' },
    { slug: 'primera-nacional', label: 'Primera Nacional' },
    { slug: 'b-metro', label: 'B Metro' },
    { slug: 'primera-c', label: 'Primera C' },
    { slug: 'federal-a', label: 'Federal A' },
    { slug: 'copa-argentina', label: 'Copa Argentina' },
  ],
  basquet: [
    { slug: 'liga-nacional', label: 'Liga Nacional' },
    { slug: 'liga-argentina', label: 'Liga Argentina' },
    { slug: 'liga-federal', label: 'Liga Federal' },
  ],
}

export default async function Page({ params, searchParams }: { params: { sport: string }, searchParams?: { comp?: string, tab?: string } }) {
  const sport = params.sport
  const comps = COMPETITIONS[sport] || []
  if (!comps.length) return <div className={styles.page}><p>Deporte sin competencias configuradas.</p></div>

  const activeComp = searchParams?.comp || comps[0].slug
  const activeTab = searchParams?.tab || 'fixture'
  const data = await api.competitions.overview(sport, activeComp)
  const fixtures = (data.fixtures || []) as any[]
  const standings = (data.standings || []) as any[]
  const results = fixtures.filter(f => f.status === 'finalizado')

  return <div className={styles.page}>
    <h1 className={styles.sportTitle}>{sport === 'futbol' ? 'Fútbol Argentino' : 'Básquet Argentino'}</h1>
    <div className={styles.compTabs}>{comps.map(c => <Link key={c.slug} href={`/deporte/${sport}?comp=${c.slug}`} className={activeComp===c.slug?styles.compTabActive:styles.compTab}>{c.label}</Link>)}</div>
    <div className={styles.compTabs}>
      <Link href={`/deporte/${sport}?comp=${activeComp}&tab=fixture`} className={activeTab==='fixture'?styles.compTabActive:styles.compTab}>Fixture</Link>
      <Link href={`/deporte/${sport}?comp=${activeComp}&tab=tabla`} className={activeTab==='tabla'?styles.compTabActive:styles.compTab}>Tabla</Link>
      <Link href={`/deporte/${sport}?comp=${activeComp}&tab=resultados`} className={activeTab==='resultados'?styles.compTabActive:styles.compTab}>Resultados</Link>
    </div>
    <p className={styles.sportSubtitle}>Fuente: {data.source_used || 'Sin datos'} · Actualizado: {new Date(data.updated_at).toLocaleString('es-AR')}</p>

    {!!data.error && <div className={styles.noMatches}><p>{data.error}</p></div>}

    <div className={styles.layout}>
      <section className={styles.section}>
        {activeTab !== 'tabla' && (activeTab === 'resultados' ? results : fixtures).map(f => (
          <div key={f.id} className={styles.matchTableRow}>
            <span>{f.datetime_arg ? new Date(f.datetime_arg).toLocaleString('es-AR') : '—'}</span>
            <span>{f.home_team} {f.home_score ?? ''} - {f.away_score ?? ''} {f.away_team}</span>
            <span>{f.status}</span>
          </div>
        ))}
      </section>
      <aside className={styles.sidebar}>
        {activeTab !== 'fixture' && standings.map((r, i) => (
          <div key={`${r.team_name}-${i}`} className={styles.compRow}>
            <span>{r.position}. {r.team_name}</span>
            <span>{sport==='futbol' ? r.points : (r.points ?? r.percentage ?? '-')}</span>
          </div>
        ))}
      </aside>
    </div>
  </div>
}
