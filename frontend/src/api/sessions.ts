import { apiFetch } from './client'
import type { StudySession } from './types'

export function listSessions(): Promise<{ sessions: StudySession[] }> {
  return apiFetch('/sessions')
}

export function createSession(name: string): Promise<StudySession> {
  return apiFetch('/sessions', { method: 'POST', body: { name } })
}

export function getSession(sessionId: string): Promise<StudySession> {
  return apiFetch(`/sessions/${sessionId}`)
}

export function renameSession(sessionId: string, name: string): Promise<StudySession> {
  return apiFetch(`/sessions/${sessionId}`, { method: 'PATCH', body: { name } })
}

export function deleteSession(sessionId: string): Promise<void> {
  return apiFetch(`/sessions/${sessionId}`, { method: 'DELETE' })
}
