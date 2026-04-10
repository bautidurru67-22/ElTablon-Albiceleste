'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/store/auth'
import { api } from '@/lib/api'
import { Match } from '@/types/match'
import { sortMatches } from '@/lib/matches'
import MatchRow from '@/components/MatchRow'
import SectionTitle from '@/components/SectionTitle'
import SportBadge from '@/components/SportBadge'
import styles from './mi-tablero.module.css'

export default function MiTablerroPage() {
  const router = useRouter()
  const { user, favorites, isFavorite, removeFavorite, isLoading } = useAuth()

  const [matchesByEntity, setMatchesByEntity] = useState<Record<string, Match[]>>({})
  const [fetching, setFetching] = useState(false)

  // Redirigir si no autenticado
  useEffect(() => {
    if (!isLoading && !user) router.push('/login')
  }, [user, isLoading, router])

  // Cargar partidos para cada favorito
  useEffect(() => {
    if (!favorites.length) return
    const clubFavs = favorites.filter(f => f.tipo === 'equipo')
    if (!clubFavs.length) return

    setFetching(true)
    Promise.allSettled(
      clubFavs.map(f =>
        api.matches.club(f.entity_id).then(matches => ({ id: f.entity_id, matches }))
      )
    ).then(results => {
      const map: Record<string, Match[]> = {}
      results.forEach(r => {
        if (r.status === 'fulfilled') {
          map[r.value.id] = r.value.matches
        }
      })
      setMatchesByEntity(map)
    }).finally(() => setFetching(false))
  }, [favorites])

  if (!user) return null

  const teamFavs   = favorites.filter(f => f.tipo === 'equipo')
  const playerFavs = favorites.filter(f => f.tipo === 'jugador')

  const allFavMatches = sortMatches(
    Object.values(matchesByEntity).flat()
  )
  const liveMatches = allFavMatches.filter(m => m.status === 'live')

  const formatName = (slug: string) =>
    slug.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')

  return (
    <div className={styles.page}>

      {/* Header del tablero */}
      <div className={styles.pageHeader}>
        <div>
          <h1 className={styles.pageTitle}>Mi Tablero</h1>
          <p className={styles.pageSubtitle}>
            Bienvenido, <strong>{user.username ?? user.email.split('@')[0]}</strong>
          </p>
        </div>
        {liveMatches.length > 0 && (
          <span className={styles.liveAlert}>
            <span className={styles.liveDot} />
            {liveMatches.length} partido{liveMatches.length > 1 ? 's' : ''} en vivo
          </span>
        )}
      </div>

      <div className={styles.layout}>
        <div className={styles.main}>

          {/* Sin favoritos */}
          {favorites.length === 0 && (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>⭐</div>
              <h2 className={styles.emptyTitle}>Tu tablero está vacío</h2>
              <p className={styles.emptyText}>
                Seguí equipos y jugadores para ver su actividad aquí.
              </p>
              <Link href="/hoy" className={styles.emptyBtn}>
                Ver partidos de hoy →
              </Link>
            </div>
          )}

          {/* Partidos en vivo de equipos seguidos */}
          {liveMatches.length > 0 && (
            <section className={styles.section}>
              <SectionTitle live count={liveMatches.length}>
                En Vivo — Tus Equipos
              </SectionTitle>
              <div className={styles.matchList}>
                {liveMatches.map(m => (
                  <MatchRow
                    key={m.id}
                    sport={m.sport}
                    competition={m.competition}
                    homeTeam={m.home_team}
                    awayTeam={m.away_team}
                    homeScore={m.home_score}
                    awayScore={m.away_score}
                    status={m.status}
                    minute={m.minute}
                    startTime={m.start_time}
                    broadcast={m.broadcast ?? undefined}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Por equipo seguido */}
          {teamFavs.map(fav => {
            const matches = sortMatches(matchesByEntity[fav.entity_id] ?? [])
            const live     = matches.filter(m => m.status === 'live')
            const upcoming = matches.filter(m => m.status === 'upcoming')
            const finished = matches.filter(m => m.status === 'finished')
            const name     = formatName(fav.entity_id)
            return (
              <section key={fav.entity_id} className={styles.section}>
                <div className={styles.clubHeader}>
                  <div className={styles.clubAvatar}>{name.charAt(0)}</div>
                  <div className={styles.clubInfo}>
                    <Link href={`/club/${fav.entity_id}`} className={styles.clubName}>
                      {name}
                    </Link>
                    <div className={styles.clubMeta}>
                      {live.length > 0 && <span className={styles.liveBadge}>● En vivo</span>}
                      {matches.length === 0 && !fetching && (
                        <span className={styles.noActivity}>Sin actividad hoy</span>
                      )}
                    </div>
                  </div>
                  <button
                    className={styles.unfollowBtn}
                    onClick={() => removeFavorite('equipo', fav.entity_id)}
                    title="Dejar de seguir"
                  >
                    ✕
                  </button>
                </div>

                {matches.length > 0 && (
                  <div className={styles.matchList}>
                    {[...live, ...upcoming, ...finished].slice(0, 5).map(m => (
                      <MatchRow
                        key={m.id}
                        sport={m.sport}
                        competition={m.competition}
                        homeTeam={m.home_team}
                        awayTeam={m.away_team}
                        homeScore={m.home_score}
                        awayScore={m.away_score}
                        status={m.status}
                        minute={m.minute}
                        startTime={m.start_time}
                        broadcast={m.broadcast ?? undefined}
                        compact
                      />
                    ))}
                  </div>
                )}
              </section>
            )
          })}

          {/* Jugadores seguidos */}
          {playerFavs.length > 0 && (
            <section className={styles.section}>
              <SectionTitle count={playerFavs.length}>Jugadores Seguidos</SectionTitle>
              <div className={styles.playerGrid}>
                {playerFavs.map(fav => (
                  <div key={fav.id} className={styles.playerCard}>
                    <div className={styles.playerAvatar}>
                      {formatName(fav.entity_id).charAt(0)}
                    </div>
                    <div className={styles.playerInfo}>
                      <span className={styles.playerName}>{formatName(fav.entity_id)}</span>
                    </div>
                    <button
                      className={styles.unfollowBtn}
                      onClick={() => removeFavorite('jugador', fav.entity_id)}
                      title="Dejar de seguir"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* Sidebar */}
        <aside className={styles.sidebar}>
          <div className={styles.sideCard}>
            <SectionTitle>Mis Favoritos</SectionTitle>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Equipos seguidos</span>
              <span className={styles.statVal}>{teamFavs.length}</span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Jugadores seguidos</span>
              <span className={styles.statVal}>{playerFavs.length}</span>
            </div>
            <div className={styles.statRow}>
              <span className={styles.statLabel}>Partidos hoy</span>
              <span className={styles.statVal}>{allFavMatches.length}</span>
            </div>
          </div>

          {teamFavs.length > 0 && (
            <div className={styles.sideCard}>
              <SectionTitle>Equipos</SectionTitle>
              {teamFavs.map(f => (
                <div key={f.id} className={styles.favRow}>
                  <Link href={`/club/${f.entity_id}`} className={styles.favName}>
                    {formatName(f.entity_id)}
                  </Link>
                  <button
                    className={styles.unfollowSmall}
                    onClick={() => removeFavorite('equipo', f.entity_id)}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className={styles.sideCard}>
            <SectionTitle>Descubrir</SectionTitle>
            <Link href="/hoy" className={styles.discoverLink}>→ Partidos de hoy</Link>
            <Link href="/calendario" className={styles.discoverLink}>→ Calendario</Link>
            <Link href="/deporte/futbol" className={styles.discoverLink}>→ Fútbol</Link>
            <Link href="/deporte/tenis" className={styles.discoverLink}>→ Tenis</Link>
          </div>
        </aside>
      </div>
    </div>
  )
}
