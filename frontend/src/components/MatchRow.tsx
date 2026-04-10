import SportBadge from './SportBadge'
import styles from './MatchRow.module.css'

interface MatchRowProps {
  sport: string
  competition: string
  homeTeam: string
  awayTeam: string
  homeScore?: number | null
  awayScore?: number | null
  status: 'live' | 'upcoming' | 'finished'
  minute?: string | null
  startTime?: string | null
  broadcast?: string | null
  argentiniaTeam?: string | null
  compact?: boolean
}

export default function MatchRow({
  sport, competition, homeTeam, awayTeam,
  homeScore, awayScore, status, minute, startTime,
  broadcast, argentiniaTeam, compact,
}: MatchRowProps) {
  const hasScore = homeScore != null && awayScore != null

  return (
    <div className={`${styles.row} ${compact ? styles.compact : ''}`}>
      {/* Time / status */}
      <div className={styles.time}>
        {status === 'live' ? (
          <span className={styles.liveBadge}>
            <span className={styles.dot} /> {minute ?? 'EN VIVO'}
          </span>
        ) : status === 'upcoming' ? (
          <span className={styles.timeText}>{startTime ?? '–'}</span>
        ) : (
          <span className={styles.finalText}>Final</span>
        )}
      </div>

      {/* Sport badge */}
      {!compact && (
        <div className={styles.sport}>
          <SportBadge sport={sport} />
        </div>
      )}

      {/* Teams + score */}
      <div className={styles.teams}>
        <span className={`${styles.team} ${status === 'finished' && hasScore && homeScore! > awayScore! ? styles.winner : ''}`}>
          {homeTeam}
        </span>
        {hasScore ? (
          <div className={styles.score}>
            <span className={`${styles.num} ${status === 'live' ? styles.liveNum : ''}`}>{homeScore}</span>
            <span className={styles.sep}>-</span>
            <span className={`${styles.num} ${status === 'live' ? styles.liveNum : ''}`}>{awayScore}</span>
          </div>
        ) : (
          <span className={styles.vs}>vs</span>
        )}
        <span className={`${styles.team} ${styles.right} ${status === 'finished' && hasScore && awayScore! > homeScore! ? styles.winner : ''}`}>
          {awayTeam}
        </span>
      </div>

      {/* Broadcast — solo si existe */}
      {broadcast && !compact && (
        <div className={styles.broadcast}>{broadcast}</div>
      )}
    </div>
  )
}
