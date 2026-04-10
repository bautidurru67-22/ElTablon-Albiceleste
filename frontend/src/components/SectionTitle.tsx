import styles from './SectionTitle.module.css'

interface SectionTitleProps {
  children: React.ReactNode
  live?: boolean
  count?: number
}

export default function SectionTitle({ children, live, count }: SectionTitleProps) {
  return (
    <div className={styles.title}>
      {live && <span className={styles.dot} />}
      <span>{children}</span>
      {count !== undefined && <span className={styles.count}>{count}</span>}
    </div>
  )
}
