import { apiFetch } from './client'
import type { DocumentOut, IngestStatus } from './types'

export function uploadDocuments(sessionId: string, files: File[]): Promise<{ documents: DocumentOut[]; ingestion_status: string }> {
  const form = new FormData()
  for (const file of files) form.append('files', file)

  return apiFetch(`/sessions/${sessionId}/documents`, {
    method: 'POST',
    body: form,
    isForm: true,
  })
}

export function getIngestStatus(sessionId: string): Promise<IngestStatus> {
  return apiFetch(`/sessions/${sessionId}/ingest/status`)
}

export function listDocuments(sessionId: string): Promise<DocumentOut[]> {
  return apiFetch(`/sessions/${sessionId}/documents`)
}
