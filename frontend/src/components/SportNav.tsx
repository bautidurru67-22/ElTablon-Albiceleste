'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import styles from './SportNav.module.css'

const NAV_ITEMS = [
  { label: 'Hoy',        slug: '/hoy' },
  { label: 'Mi Tablero', slug: '/mi-tablero' },
  { label: 'Calendario', slug: '/calendario' },
  { label: 'Resultados', slug: '/resultados' },
  { label: 'Fútbol',     slug: '/deporte/futbol' },
  { label: 'Tenis',      slug: '/deporte/tenis' },
  { label: 'Básquet',    slug: '/deporte/basquet' },
  { label: 'Hockey',     slug: '/deporte/hockey' },
  { label: 'Rugby',      slug: '/deporte/rugby' },
  { label: 'Vóley',      slug: '/deporte/voley' },
  { label: 'Futsal',     slug: '/deporte/futsal' },
  { label: 'Boxeo',      slug: '/deporte/boxeo' },
  { label: 'Polo',       slug: '/deporte/polo' },
  { label: 'Golf',       slug: '/deporte/golf' },
  { label: 'Handball',   slug: '/deporte/handball' },
  { label: 'Esports',    slug: '/deporte/esports' },
  { label: 'Dakar',      slug: '/deporte/dakar' },
]

export default function SportNav() {
  const pathname = usePathname()

  return (
    <nav className={styles.nav}>
      <div className={styles.inner}>
        {NAV_ITEMS.map((item) => {
          // Activo si pathname coincide exactamente o empieza con el slug (para sub-rutas)
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
