import Link from 'next/link'
import styles from './Header.module.css'
import UserMenu from './UserMenu'

export default function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link href="/hoy" className={styles.logoLink}>
          <div className={styles.logoMark}>
            <svg className={styles.logoIcon} viewBox="0 0 24 14" fill="none">
              <rect x="0" y="0" width="24" height="4.5" fill="#1a5fa8"/>
              <rect x="0" y="4.5" width="24" height="5" fill="#ffffff"/>
              <rect x="0" y="9.5" width="24" height="4.5" fill="#1a5fa8"/>
              <circle cx="12" cy="7" r="2.5" fill="#1a5fa8"/>
            </svg>
            <span className={styles.logoText}>El Tablón</span>
          </div>
        </Link>
        <div className={styles.right}>
          <button className={styles.iconBtn} aria-label="Buscar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
              <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
            </svg>
          </button>
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
