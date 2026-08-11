import { apiFetch } from './client'
import type { TokenResponse, User } from './types'

export function signup(email: string, password: string, name: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>('/auth/signup', {
    method: 'POST',
    body: { email, password, name },
    auth: false,
  })
}

export function login(email: string, password: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>('/auth/login', {
    method: 'POST',
    body: { email, password },
    auth: false,
  })
}

export function getMe(): Promise<User> {
  return apiFetch<User>('/auth/me')
}
