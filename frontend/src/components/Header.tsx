import Image from 'next/image'
import Link from 'next/link'
import styles from './Header.module.css'
import UserMenu from './UserMenu'

export default function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link href="/hoy" className={styles.logoLink}>
          <Image
            src="/branding/logo-el-tablon-albiceleste.png"
            alt="El Tablón Albiceleste"
            width={927}
            height={471}
            priority
            className={styles.logoImage}
          />
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
