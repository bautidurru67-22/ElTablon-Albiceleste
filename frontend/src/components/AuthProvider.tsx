'use client'
import { useEffect } from 'react'
import { useAuth } from '@/store/auth'

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const hydrate = useAuth(s => s.hydrate)
  useEffect(() => { hydrate() }, [hydrate])
  return <>{children}</>
}
