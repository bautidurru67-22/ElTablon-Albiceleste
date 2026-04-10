export interface User {
  id: string
  email: string
  username: string | null
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Favorite {
  id: number
  tipo: 'equipo' | 'jugador'
  entity_id: string
  created_at: string
}
