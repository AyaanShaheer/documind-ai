const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

const TOKEN_KEY = 'documind_access_token'
const EXPIRY_KEY = 'documind_token_expiry'

export interface LoginResponse {
  access_token: string
  id_token?: string
  expires_in: number
  token_type: string
}

export function getAccessToken(): string | null {
  const token = sessionStorage.getItem(TOKEN_KEY)
  const expiry = Number(sessionStorage.getItem(EXPIRY_KEY) ?? 0)

  if (!token || !expiry || Date.now() >= expiry) {
    clearSession()
    return null
  }

  return token
}

export function clearSession(): void {
  sessionStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(EXPIRY_KEY)
}

export async function signIn(
  username: string,
  password: string,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(data.detail ?? 'Unable to sign in. Please try again.')
  }

  const result = data as LoginResponse

  if (!result.access_token || !result.expires_in) {
    throw new Error('Authentication response was incomplete.')
  }

  sessionStorage.setItem(TOKEN_KEY, result.access_token)
  sessionStorage.setItem(
    EXPIRY_KEY,
    String(Date.now() + result.expires_in * 1000),
  )
}

export async function apiRequest(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(options.headers)
  const token = getAccessToken()

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  return fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  })
}
