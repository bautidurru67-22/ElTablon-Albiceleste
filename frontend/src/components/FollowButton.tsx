'use client'
import { useState } from 'react'
import { useAuth } from '@/store/auth'
import styles from './FollowButton.module.css'

interface Props {
  tipo: 'equipo' | 'jugador'
  entityId: string
  label?: string
}

export default function FollowButton({ tipo, entityId, label }: Props) {
  const { user, isFavorite, addFavorite, removeFavorite } = useAuth()
  const [loading, setLoading] = useState(false)
  const following = isFavorite(tipo, entityId)

  if (!user) {
    return (
      <a href="/login" className={styles.btnGuest}>
        + Seguir
      </a>
    )
  }

  const toggle = async () => {
    setLoading(true)
    try {
      if (following) {
        await removeFavorite(tipo, entityId)
      } else {
        await addFavorite(tipo, entityId)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      className={`${styles.btn} ${following ? styles.following : styles.notFollowing}`}
      onClick={toggle}
      disabled={loading}
    >
      {loading ? '...' : following ? '✓ Siguiendo' : `+ Seguir${label ? ` ${label}` : ''}`}
    </button>
  )
}
