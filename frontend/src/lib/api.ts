import { Match } from '@/types/match'
import { Player } from '@/types/player'
import { TokenResponse, Favorite } from '@/types/auth'

const API_BASE = process.env.NEXT_PUBLIC_API_URL
const IS_SERVER = typeof window === 'undefined'
const CLIENT_PROXY_BASE = '/api/proxy'
let hasWarnedMisconfig = false

function warnIfApiMisconfigured() {
  if (!IS_SERVER || hasWarnedMisconfig) return

  const isVercelRuntime = Boolean(process.env.VERCEL_URL)
  if (!API_BASE && isVercelRuntime) {
    hasWarnedMisconfig = true
    console.error(
      '[el-tablon] NEXT_PUBLIC_API_URL no está configurada en Vercel.'
    )
  }
}

function getServerProxyTarget(path: string): string | null {
  const vercelUrl = process.env.VERCEL_URL
  if (!vercelUrl) return null
  return `https://${vercelUrl}${CLIENT_PROXY_BASE}${path}`
}

// ---------------------------------------------------------------------------
// Core fetch — con soporte de auth token
// ---------------------------------------------------------------------------
async function apiFetch<T>(
  path: string,
  options: RequestInit & { revalidate?: number; token?: string } = {}
): Promise<T> {
  warnIfApiMisconfigured()
  const { revalidate = 30, token, ...fetchOpts } = options
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(fetchOpts.headers ?? {}),
  }
  try {
    const primaryTarget = IS_SERVER ? (API_BASE ? `${API_BASE}${path}` : '') : `${CLIENT_PROXY_BASE}${path}`
    if (!primaryTarget) {
      throw new Error('NEXT_PUBLIC_API_URL missing on server runtime')
    }

    let res = await fetch(primaryTarget, {
      ...fetchOpts,
      headers,
      next: fetchOpts.method ? undefined : { revalidate },
    })

    // En server, fallback al proxy interno si el backend directo falla.
    if (!res.ok && IS_SERVER) {
      const fallback = getServerProxyTarget(path)
      if (fallback) {
        res = await fetch(fallback, {
          ...fetchOpts,
          headers,
          cache: 'no-store',
        })
      }
    }

    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail ?? `HTTP ${res.status}`)
    }
    return res.json()
  } catch (err) {
    // Server components: log + retornar vacío; client components: relanzar
    if (IS_SERVER) {
      console.error(`[el-tablon] Error consultando ${path}`, err)
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
