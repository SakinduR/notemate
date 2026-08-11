const API_BASE = '/api'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function getToken(): string | null {
  return localStorage.getItem('notemate_token')
}

interface RequestOptions {
  method?: string
  body?: unknown
  auth?: boolean
  isForm?: boolean
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true, isForm = false } = options

  const headers: Record<string, string> = {}
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }
  if (!isForm && body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: isForm ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const errBody = await res.json()
      detail = errBody.detail ?? detail
    } catch {
      // response wasn't JSON -- fall back to statusText
    }
    throw new ApiError(res.status, typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function authHeader(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export { API_BASE, getToken }
