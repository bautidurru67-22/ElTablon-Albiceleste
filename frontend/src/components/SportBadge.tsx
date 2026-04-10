import styles from './SportBadge.module.css'

const SPORT_COLORS: Record<string, string> = {
  futbol:    'blue',
  tenis:     'green',
  basquet:   'orange',
  hockey:    'teal',
  rugby:     'purple',
  voley:     'yellow',
  boxeo:     'red',
  default:   'gray',
}

const SPORT_LABELS: Record<string, string> = {
  futbol: 'Fútbol', tenis: 'Tenis', basquet: 'Básquet',
  hockey: 'Hockey', rugby: 'Rugby', voley: 'Vóley',
  boxeo: 'Boxeo', futsal: 'Futsal', polo: 'Polo',
  golf: 'Golf', handball: 'Handball', motorsport: 'Autom.',
  motogp: 'MotoGP', olimpicos: 'Olímpicos', esports: 'Esports',
}

export function sportLabel(sport: string): string {
  return SPORT_LABELS[sport] ?? sport
}

interface SportBadgeProps { sport: string }

export default function SportBadge({ sport }: SportBadgeProps) {
  const color = SPORT_COLORS[sport] ?? SPORT_COLORS.default
  return (
    <span className={`${styles.badge} ${styles[color]}`}>
      {sportLabel(sport)}
    </span>
  )
}
