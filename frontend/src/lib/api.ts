import { Match } from '@/types/match'
import { Player } from '@/types/player'
import { TokenResponse, Favorite } from '@/types/auth'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ---------------------------------------------------------------------------
// Core fetch — con soporte de auth token
// ---------------------------------------------------------------------------
async function apiFetch<T>(
  path: string,
  options: RequestInit & { revalidate?: number; token?: string } = {}
): Promise<T> {
  const { revalidate = 30, token, ...fetchOpts } = options
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(fetchOpts.headers ?? {}),
  }
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...fetchOpts,
      headers,
      next: fetchOpts.method ? undefined : { revalidate },
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail ?? `HTTP ${res.status}`)
    }
    return res.json()
  } catch (err) {
    // Server components: log + retornar vacío; client components: relanzar
    if (typeof window === 'undefined') {
      return [] as unknown as T
    }
    throw err
  }
}

// ---------------------------------------------------------------------------
// Public API (Server Components)
// ---------------------------------------------------------------------------
export const api = {
  matches: {
    live:      (sport?: string) => apiFetch<Match[]>(`/api/matches/live${sport ? `?sport=${sport}` : ''}`, { revalidate: 15 }),
    today:     (sport?: string) => apiFetch<Match[]>(`/api/matches/today${sport ? `?sport=${sport}` : ''}`, { revalidate: 60 }),
    results:   (sport?: string) => apiFetch<Match[]>(`/api/matches/results${sport ? `?sport=${sport}` : ''}`, { revalidate: 120 }),
    argentina: ()               => apiFetch<Match[]>('/api/matches/argentina', { revalidate: 30 }),
    club:      (id: string)     => apiFetch<Match[]>(`/api/matches/club/${id}`, { revalidate: 30 }),
  },

  competitions: {
    list: (sport: string) =>
      apiFetch<{ sport: string; items: Array<{ slug: string; label: string }> }>(
        `/api/competitions/${sport}`,
        { revalidate: 120 }
      ),

    fixture: (sport: string, slug: string) =>
      apiFetch<{
        sport: string
        slug: string
        competition: string
        updated_at: string
        count: number
        matches: Match[]
      }>(
        `/api/competitions/${sport}/${slug}/fixture`,
        { revalidate: 30 }
      ),

    table: (sport: string, slug: string) =>
      apiFetch<{
        sport: string
        slug: string
        competition: string
        updated_at: string
        rows: Array<Record<string, unknown>>
      }>(
        `/api/competitions/${sport}/${slug}/table`,
        { revalidate: 30 }
      ),

    scorers: (sport: string, slug: string) =>
      apiFetch<{
        sport: string
        slug: string
        competition: string
        updated_at: string
        rows: Array<Record<string, unknown>>
        note?: string
      }>(
        `/api/competitions/${sport}/${slug}/scorers`,
        { revalidate: 30 }
      ),
  },

  players: {
    abroad: () => apiFetch<Player[]>('/api/players/abroad', { revalidate: 300 }),
  },
}

// ---------------------------------------------------------------------------
// Auth API (Client Components — lanza errores)
// ---------------------------------------------------------------------------
export const authApi = {
  register: (email: string, password: string, username?: string) =>
    apiFetch<TokenResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, username }),
    }),

  login: (email: string, password: string) =>
    apiFetch<TokenResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: (token: string) =>
    apiFetch<TokenResponse['user']>('/api/auth/me', { token }),
}

// ---------------------------------------------------------------------------
// Favorites API (Client Components — requiere token)
// ---------------------------------------------------------------------------
export const favoritesApi = {
  list: (token: string) =>
    apiFetch<Favorite[]>('/api/favorites/', { token }),

  add: (token: string, tipo: 'equipo' | 'jugador', entity_id: string) =>
    apiFetch<Favorite>('/api/favorites/', {
      method: 'POST',
      token,
      body: JSON.stringify({ tipo, entity_id }),
    }),

  remove: (token: string, tipo: string, entity_id: string) =>
    apiFetch<void>(`/api/favorites/by-entity/${tipo}/${entity_id}`, {
      method: 'DELETE',
      token,
    }),

  check: (token: string, tipo: string, entity_id: string) =>
    apiFetch<{ is_favorite: boolean }>(`/api/favorites/check/${tipo}/${entity_id}`, { token }),
}

// Legacy
export async function fetchMatches(endpoint: string): Promise<Match[]> {
  return apiFetch<Match[]>(`/api/matches/${endpoint}`, { revalidate: 30 })
}
