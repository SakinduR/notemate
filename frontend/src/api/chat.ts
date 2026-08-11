import { API_BASE, apiFetch, authHeader } from './client'
import type { ChatResponse, Citation } from './types'

export function sendChat(sessionId: string, query: string): Promise<ChatResponse> {
  return apiFetch(`/sessions/${sessionId}/chat`, { method: 'POST', body: { query } })
}

export interface StreamHandlers {
  onTrace?: (node: string, message: string) => void
  onFinal?: (answer: string, citations: Citation[]) => void
  onError?: (message: string) => void
}

/**
 * The backend's /chat/stream endpoint is SSE over a POST request with an
 * Authorization header -- the browser's native EventSource only supports
 * GET with no custom headers, so it can't be used here. This reads the
 * response body as a stream instead and parses the same "event: X\ndata:
 * Y\n\n" framing by hand.
 */
export async function streamChat(sessionId: string, query: string, handlers: StreamHandlers, signal?: AbortSignal): Promise<void> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: JSON.stringify({ query }),
    signal,
  })

  if (!res.ok || !res.body) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      // not JSON, keep statusText
    }
    handlers.onError?.(detail)
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let separatorIndex: number
    while ((separatorIndex = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, separatorIndex)
      buffer = buffer.slice(separatorIndex + 2)

      let eventType = 'message'
      let data = ''
      for (const line of rawEvent.split('\n')) {
        if (line.startsWith('event: ')) eventType = line.slice(7)
        else if (line.startsWith('data: ')) data = line.slice(6)
      }
      if (!data) continue

      const parsed = JSON.parse(data)
      if (eventType === 'trace') handlers.onTrace?.(parsed.node, parsed.message)
      else if (eventType === 'final') handlers.onFinal?.(parsed.answer, parsed.citations)
      else if (eventType === 'error') handlers.onError?.(parsed.message)
    }
  }
}
