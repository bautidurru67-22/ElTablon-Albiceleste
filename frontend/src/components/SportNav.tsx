'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import styles from './SportNav.module.css'

const NAV_ITEMS = [
  { label: 'Hoy', slug: '/hoy' },
  { label: 'Mi Tablero', slug: '/mi-tablero' },
  { label: 'Calendario', slug: '/calendario' },
  { label: 'Resultados', slug: '/resultados' },
  { label: 'Fútbol', slug: '/deporte/futbol' },
  { label: 'Tenis', slug: '/deporte/tenis' },
  { label: 'Básquet', slug: '/deporte/basquet' },
  { label: 'Rugby', slug: '/deporte/rugby' },
  { label: 'Hockey', slug: '/deporte/hockey' },
  { label: 'Vóley', slug: '/deporte/voley' },
  { label: 'Futsal', slug: '/deporte/futsal' },
  { label: 'Motorsport', slug: '/deporte/motorsport' },
]

export default function SportNav() {
  const pathname = usePathname()

  return (
    <nav className={styles.nav}>
      <div className={styles.inner}>
        {NAV_ITEMS.map((item) => {
          const isActive =
            pathname === item.slug ||
            (item.slug !== '/' && pathname.startsWith(item.slug))

          return (
            <Link
              key={item.slug}
              href={item.slug}
              className={`${styles.item} ${isActive ? styles.active : ''}`}
            >
              {item.label}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
