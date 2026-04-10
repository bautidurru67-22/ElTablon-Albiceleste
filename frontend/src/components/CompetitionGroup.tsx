import MatchRow from './MatchRow'
import { Match } from '@/types/match'
import styles from './CompetitionGroup.module.css'

interface CompetitionGroupProps {
  competition: string
  matches: Match[]
  sport?: string
  compact?: boolean
}

export default function CompetitionGroup({ competition, matches, compact }: CompetitionGroupProps) {
  return (
    <div className={styles.group}>
      <div className={styles.header}>
        <span className={styles.name}>{competition}</span>
        <span className={styles.count}>{matches.length}</span>
      </div>
      {matches.map(m => (
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
          argentiniaTeam={m.argentina_team ?? undefined}
          compact={compact}
        />
      ))}
    </div>
  )
}
