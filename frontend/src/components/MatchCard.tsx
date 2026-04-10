import styles from './MatchCard.module.css'

interface MatchCardProps {
  sport: string
  competition: string
  homeTeam: string
  awayTeam: string
  homeScore?: number | null
  awayScore?: number | null
  status: 'live' | 'upcoming' | 'finished'
  minute?: string | null
  startTime?: string | null
  argentiniaTeam?: string | null
  broadcast?: string | null
}

export default function MatchCard({
  competition,
  homeTeam,
  awayTeam,
  homeScore,
  awayScore,
  status,
  minute,
  startTime,
  argentiniaTeam,
  broadcast,
}: MatchCardProps) {
  const hasScore = homeScore !== null && homeScore !== undefined

  return (
    <div className={styles.card}>
      <div className={styles.top}>
        <span className={styles.competition}>{competition}</span>
        <span className={`${styles.badge} ${styles[status]}`}>
          {status === 'live' ? minute || 'En vivo' : status === 'upcoming' ? startTime || 'Próximo' : 'Final'}
        </span>
      </div>

      <div className={styles.teams}>
        <span className={styles.team}>{homeTeam}</span>

        {hasScore ? (
          <div className={styles.score}>
            <span className={styles.scoreNum}>{homeScore}</span>
            <span className={styles.scoreSep}>-</span>
            <span className={styles.scoreNum}>{awayScore}</span>
          </div>
        ) : (
          <span className={styles.vs}>vs</span>
        )}

        <span className={`${styles.team} ${styles.teamRight}`}>{awayTeam}</span>
      </div>

      {(argentiniaTeam || broadcast) && (
        <div className={styles.meta}>
          {argentiniaTeam && <span className={styles.argTag}>🇦🇷 {argentiniaTeam}</span>}
          {broadcast && <span className={styles.broadcast}>{broadcast}</span>}
        </div>
      )}
    </div>
  )
}
