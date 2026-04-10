import Link from 'next/link'
import styles from './Header.module.css'
import UserMenu from './UserMenu'

export default function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link href="/hoy" className={styles.logoLink}>
          <div className={styles.logoFull}>
            <span className={styles.logoPrefix}>El Tablón</span>
            <span className={styles.logoName}>ALBICELESTE</span>
          </div>
          <div className={styles.logoShort}>
            <span className={styles.logoPrefix}>El</span>
            <span className={styles.logoName}>TABLÓN</span>
          </div>
        </Link>
        <div className={styles.right}>
          <span className={styles.flag}>🇦🇷</span>
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
