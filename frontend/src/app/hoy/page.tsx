'use client'

import { useEffect, useState, useCallback } from 'react'
import { sortMatches, groupByCompetition, groupBySport, sl } from '@/lib/matches'
import { Match } from '@/types/match'
import styles from './hoy.module.css'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// Sport badge colors
const SPORT_COLORS: Record<string, string> = {
  futbol: '#1d4ed8', tenis: '#15803d', basquet: '#c2410c',
  hockey: '#0e7490', rugby: '#6d28d9', voley: '#854d0e',
  boxeo: '#be123c', futsal: '#7c3aed', golf: '#065f46',
  handball: '#86198f', motorsport: '#334155', motogp: '#9f1239',
}
const SPORT_BG: Record<string, string> = {
  futbol: '#dbeafe', tenis: '#dcfce7', basquet: '#ffedd5',
  hockey: '#ccfbf1', rugby: '#ede9fe', voley: '#fef9c3',
  boxeo: '#fee2e2', futsal: '#f3e8ff', golf: '#ecfdf5',
  handball: '#fdf4ff', motorsport: '#f1f5f9', motogp: '#fff1f2',
}

function SportBadge({ sport }: { sport: string }) {
  return (
    <span style={{
      fontFamily: "'Barlow Condensed', sans-serif",
      fontSize: 9, fontWeight: 700, textTransform: 'uppercase' as const,
      letterSpacing: '.4px', padding: '2px 6px', borderRadius: 3,
      background: SPORT_BG[sport] || '#f1f5f9',
      color: SPORT_COLORS[sport] || '#334155',
      whiteSpace: 'nowrap' as const, flexShrink: 0,
    }}>
      {sl(sport)}
    </span>
  )
}

function MatchRow({ m }: { m: Match }) {
  const isLive = m.status === 'live'
  const isFin = m.status === 'finished'
  const hasScore = m.home_score != null && m.away_score != null
  const hw = isFin && hasScore && m.home_score! > m.away_score!
  const aw = isFin && hasScore && m.away_score! > m.home_score!

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '56px 58px 1fr 68px',
      alignItems: 'center', gap: 5, padding: '6px 13px',
      borderBottom: '0.5px solid #e4eaf3',
      background: isLive ? '#fff8f8' : '#fff',
      fontSize: 11, cursor: 'pointer',
    }}>
      {/* Time */}
      <div>
        {isLive ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10, fontWeight: 800, color: '#c8202a' }}>
            <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#c8202a', flexShrink: 0, animation: 'bk 1s ease-in-out infinite', display: 'inline-block' }} />
            {m.minute || 'VIVO'}
          </span>
        ) : m.status === 'finished' ? (
          <span style={{ fontFamily: "'Barlow Condensed',sans-serif", fontSize: 9, textTransform: 'uppercase' as const, letterSpacing: '.4px', color: '#94a3b8', background: '#f1f5f9', padding: '2px 5px', borderRadius: 3 }}>FINAL</span>
        ) : (
          <span style={{ fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700, fontSize: 12, color: '#3a8fd1' }}>{m.start_time || '--:--'}</span>
        )}
      </div>
      {/* Sport */}
      <SportBadge sport={m.sport} />
      {/* Teams + Score */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, minWidth: 0 }}>
        <span style={{ flex: 1, fontWeight: hw ? 700 : 600, color: hw ? '#0d3260' : '#0f172a', whiteSpace: 'nowrap' as const, overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {m.home_team}
        </span>
        {hasScore ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 2, flexShrink: 0 }}>
            <span style={{ fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 800, fontSize: 14, padding: '1px 4px', borderRadius: 3, background: isLive ? '#0d3260' : '#e8eef7', color: isLive ? '#fff' : '#0d3260', minWidth: 19, textAlign: 'center' as const }}>{m.home_score}</span>
            <span style={{ fontSize: 10, color: '#94a3b8' }}>-</span>
            <span style={{ fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 800, fontSize: 14, padding: '1px 4px', borderRadius: 3, background: isLive ? '#0d3260' : '#e8eef7', color: isLive ? '#fff' : '#0d3260', minWidth: 19, textAlign: 'center' as const }}>{m.away_score}</span>
          </div>
        ) : (
          <span style={{ fontSize: 10, color: '#94a3b8', padding: '0 3px', flexShrink: 0 }}>vs</span>
        )}
        <span style={{ flex: 1, fontWeight: aw ? 700 : 600, color: aw ? '#0d3260' : '#0f172a', textAlign: 'right' as const, whiteSpace: 'nowrap' as const, overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {m.away_team}
        </span>
      </div>
      {/* Broadcast */}
      <div style={{ fontSize: 9, color: '#94a3b8', textAlign: 'right' as const, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>{m.broadcast || ''}</div>
    </div>
  )
}

function CompGroup({ comp, matches }: { comp: string; matches: Match[] }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 13px', background: '#f5f8fd', borderBottom: '0.5px solid #e4eaf3' }}>
        <span style={{ fontFamily: "'Barlow Condensed',sans-serif", fontSize: 10, fontWeight: 700, textTransform: 'uppercase' as const, letterSpacing: '.5px', color: '#0d3260' }}>{comp}</span>
        <span style={{ fontSize: 9, fontWeight: 700, background: '#0d3260', color: '#fff', borderRadius: 10, padding: '1px 6px' }}>{matches.length}</span>
      </div>
      {matches.map(m => <MatchRow key={m.id} m={m} />)}
    </div>
  )
}

export default function HoyPage() {
  const [matches, setMatches] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState('')
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/matches/argentina`, {
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-cache' },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: Match[] = await res.json()
      setMatches(data)
      setError('')
      setLastUpdate(new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // cada 30s
    return () => clearInterval(interval)
  }, [fetchData])

  const sorted = sortMatches(matches)
  const live = sorted.filter(m => m.status === 'live')
  const sel = sorted.filter(m => m.argentina_relevance === 'seleccion')
  const ext = sorted.filter(m => m.argentina_relevance === 'jugador_arg')
  const loc = sorted.filter(m => m.argentina_relevance === 'club_arg')
  const bySport = groupBySport(sorted)
  const today = new Date().toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })

  const Section = ({ title, ms, hdClass }: { title: string; ms: Match[]; hdClass: string }) => {
    if (!ms.length) return null
    const byComp = groupByCompetition(ms)
    return (
      <div className={styles.section}>
        <div className={`${styles.secHd} ${styles[hdClass]}`}>
          <div className={styles.secHdL}>
            {ms.some(m => m.status === 'live') && <span className={styles.liDot} />}
            <span className={styles.secTi}>{title}</span>
          </div>
          <span className={styles.secBadge}>{ms.length}</span>
        </div>
        <div className={styles.secBody}>
          {Object.entries(byComp).map(([comp, cms]) => <CompGroup key={comp} comp={comp} matches={cms} />)}
        </div>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <style>{`@keyframes bk{0%,100%{opacity:1}50%{opacity:.3}}`}</style>

      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Argentinos en acción hoy</h1>
          <span className={styles.pageDate}>{today}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {loading && <span style={{ fontSize: 11, color: '#94a3b8' }}>Actualizando…</span>}
          {lastUpdate && !loading && (
            <span style={{ fontSize: 10, color: '#94a3b8', display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
              {lastUpdate}
            </span>
          )}
          {error && <span style={{ fontSize: 11, color: '#ef4444' }}>Error: {error}</span>}
        </div>
      </div>

      <div className={styles.layout}>
        <div className={styles.main}>
          {loading && matches.length === 0 && (
            <div className={styles.empty}>
              <div className={styles.spinner} />
              <p>Cargando datos en tiempo real…</p>
              <p className={styles.emptyHint}>Conectando con Promiedos, LNB, Sofascore…</p>
            </div>
          )}

          {!loading && matches.length === 0 && !error && (
            <div className={styles.empty}>
              <p>No hay partidos argentinos registrados para hoy.</p>
              <p className={styles.emptyHint}>Los datos se actualizan cada 30 segundos.</p>
              <button onClick={fetchData} style={{ marginTop: 8, padding: '6px 14px', fontSize: 12, cursor: 'pointer', border: '1px solid #d8e2ef', borderRadius: 5, background: '#fff' }}>
                Reintentar
              </button>
            </div>
          )}

          {live.length > 0 && (
            <div className={styles.section}>
              <div className={`${styles.secHd} ${styles.secHdLive}`}>
                <div className={styles.secHdL}>
                  <span className={styles.liDot} />
                  <span className={styles.secTi} style={{ color: '#c8202a' }}>En vivo ahora</span>
                </div>
                <span className={`${styles.secBadge} ${styles.badgeLive}`}>{live.length} partidos</span>
              </div>
              <div className={styles.secBody}>
                {Object.entries(groupByCompetition(live)).map(([comp, ms]) => <CompGroup key={comp} comp={comp} matches={ms} />)}
              </div>
            </div>
          )}

          <Section title="🇦🇷 Selecciones nacionales" ms={sel.filter(m => m.status !== 'live')} hdClass="secHdSel" />
          <Section title="🌎 Argentinos en el exterior" ms={ext.filter(m => m.status !== 'live')} hdClass="secHdExt" />
          <Section title="🏟 Ligas locales" ms={loc.filter(m => m.status !== 'live')} hdClass="secHdLoc" />
        </div>

        <aside className={styles.sidebar}>
          <div className={styles.sideCard}>
            <div className={styles.sideCardTitle}>Resumen del día</div>
            {[
              { label: 'En vivo', val: live.length, red: true },
              { label: 'Próximos', val: sorted.filter(m => m.status === 'upcoming').length, red: false },
              { label: 'Finalizados', val: sorted.filter(m => m.status === 'finished').length, red: false },
              { label: 'Total', val: sorted.length, red: false, bold: true },
            ].map(r => (
              <div key={r.label} className={styles.statRow} style={r.bold ? { fontWeight: 700 } : {}}>
                <span className={styles.statLabel}>{r.label}</span>
                <span className={styles.statVal} style={r.red && r.val > 0 ? { color: '#c8202a' } : {}}>{r.val}</span>
              </div>
            ))}
          </div>

          {live.length > 0 && (
            <div className={styles.sideCard}>
              <div className={styles.sideCardTitle} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#c8202a', animation: 'bk 1.2s ease-in-out infinite', display: 'inline-block' }} />
                En vivo ahora
              </div>
              {live.slice(0, 5).map(m => (
                <div key={m.id} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '4px 0', borderBottom: '0.5px solid #e4eaf3', fontSize: 10 }}>
                  <SportBadge sport={m.sport} />
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>{m.home_team} - {m.away_team}</span>
                  {m.home_score != null && <span style={{ fontFamily: "'Barlow Condensed',sans-serif", fontWeight: 700, color: '#c8202a', flexShrink: 0 }}>{m.home_score}-{m.away_score}</span>}
                </div>
              ))}
            </div>
          )}

          {Object.keys(bySport).length > 0 && (
            <div className={styles.sideCard}>
              <div className={styles.sideCardTitle}>Deportes hoy</div>
              {Object.entries(bySport).sort((a, b) => b[1].length - a[1].length).map(([sport, ms]) => {
                const lv = ms.filter(m => m.status === 'live').length
                return (
                  <div key={sport} className={styles.statRow}>
                    <span className={styles.statLabel} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      {lv > 0 && <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#c8202a', animation: 'bk 1.2s ease-in-out infinite', display: 'inline-block' }} />}
                      {sl(sport)}
                    </span>
                    <span className={styles.statVal}>{ms.length}</span>
                  </div>
                )
              })}
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
