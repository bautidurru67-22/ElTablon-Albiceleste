'use client'
import { useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/store/auth'
import styles from './UserMenu.module.css'

export default function UserMenu() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)

  if (!user) {
    return (
      <Link href="/login" className={styles.loginBtn}>
        Ingresar
      </Link>
    )
  }

  return (
    <div className={styles.wrapper}>
      <button className={styles.avatar} onClick={() => setOpen(o => !o)}>
        {(user.username ?? user.email).charAt(0).toUpperCase()}
      </button>
      {open && (
        <div className={styles.dropdown}>
          <div className={styles.email}>{user.email}</div>
          <Link href="/mi-tablero" className={styles.item} onClick={() => setOpen(false)}>
            Mi Tablero
          </Link>
          <button className={styles.itemBtn} onClick={() => { logout(); setOpen(false) }}>
            Cerrar sesión
          </button>
        </div>
      )}
    </div>
  )
}
