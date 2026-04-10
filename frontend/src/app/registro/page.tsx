'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/store/auth'
import styles from '../login/login.module.css'

export default function RegistroPage() {
  const router = useRouter()
  const register = useAuth(s => s.register)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [username, setUsername] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(email, password, username || undefined)
      router.push('/mi-tablero')
    } catch (err: any) {
      setError(err.message ?? 'Error al registrarse')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <h1 className={styles.title}>Registrarse</h1>
          <p className={styles.subtitle}>Creá tu cuenta y seguí a tu equipo</p>
        </div>

        <form onSubmit={submit} className={styles.form}>
          <div className={styles.field}>
            <label className={styles.label}>Usuario (opcional)</label>
            <input
              type="text"
              className={styles.input}
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="hincha_river"
              autoComplete="username"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Email</label>
            <input
              type="email"
              className={styles.input}
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="tu@email.com"
              required
              autoComplete="email"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>Contraseña (mín. 8 caracteres)</label>
            <input
              type="password"
              className={styles.input}
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>

          {error && <div className={styles.error}>{error}</div>}

          <button type="submit" className={styles.submit} disabled={loading}>
            {loading ? 'Creando cuenta...' : 'Crear cuenta'}
          </button>
        </form>

        <div className={styles.footer}>
          ¿Ya tenés cuenta?{' '}
          <Link href="/login" className={styles.link}>Ingresá</Link>
        </div>
      </div>
    </div>
  )
}
