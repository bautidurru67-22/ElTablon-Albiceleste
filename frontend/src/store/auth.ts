'use client'
import { create } from 'zustand'
import { User, Favorite } from '@/types/auth'
import { authApi, favoritesApi } from '@/lib/api'

const TOKEN_KEY = 'ta_token'

interface AuthState {
  user: User | null
  token: string | null
  favorites: Favorite[]
  isLoading: boolean

  // Actions
  login:    (email: string, password: string) => Promise<void>
  register: (email: string, password: string, username?: string) => Promise<void>
  logout:   () => void
  hydrate:  () => Promise<void>

  // Favorites
  loadFavorites:   () => Promise<void>
  addFavorite:     (tipo: 'equipo' | 'jugador', entity_id: string) => Promise<void>
  removeFavorite:  (tipo: string, entity_id: string) => Promise<void>
  isFavorite:      (tipo: string, entity_id: string) => boolean
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  favorites: [],
  isLoading: false,

  login: async (email, password) => {
    const res = await authApi.login(email, password)
    localStorage.setItem(TOKEN_KEY, res.access_token)
    set({ user: res.user, token: res.access_token })
    await get().loadFavorites()
  },

  register: async (email, password, username) => {
    const res = await authApi.register(email, password, username)
    localStorage.setItem(TOKEN_KEY, res.access_token)
    set({ user: res.user, token: res.access_token, favorites: [] })
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    set({ user: null, token: null, favorites: [] })
  },

  hydrate: async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
    if (!token) { set({ isLoading: false }); return }
    set({ isLoading: true })
    try {
      const user = await authApi.me(token)
      set({ user, token })
      await get().loadFavorites()
    } catch {
      localStorage.removeItem(TOKEN_KEY)
      set({ user: null, token: null, favorites: [] })
    } finally {
      set({ isLoading: false })
    }
  },

  loadFavorites: async () => {
    const { token } = get()
    if (!token) return
    try {
      const favs = await favoritesApi.list(token)
      set({ favorites: favs })
    } catch {
      set({ favorites: [] })
    }
  },

  addFavorite: async (tipo, entity_id) => {
    const { token } = get()
    if (!token) throw new Error('No autenticado')
    const fav = await favoritesApi.add(token, tipo, entity_id)
    set(s => ({ favorites: [fav, ...s.favorites] }))
  },

  removeFavorite: async (tipo, entity_id) => {
    const { token } = get()
    if (!token) throw new Error('No autenticado')
    await favoritesApi.remove(token, tipo, entity_id)
    set(s => ({
      favorites: s.favorites.filter(f => !(f.tipo === tipo && f.entity_id === entity_id))
    }))
  },

  isFavorite: (tipo, entity_id) => {
    return get().favorites.some(f => f.tipo === tipo && f.entity_id === entity_id)
  },
}))
