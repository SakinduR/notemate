export interface User {
  id: string
  email: string
  name: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export type IngestionStatus = 'empty' | 'ingesting' | 'ready' | 'failed'

export interface StudySession {
  id: string
  name: string
  document_count: number
  created_at: string
  ingestion_status: IngestionStatus
}

export interface DocumentOut {
  id: string
  file_name: string
  size_bytes: number
  source_type: string | null
  uploaded_at: string
}

export interface IngestStatus {
  session_id: string
  status: IngestionStatus
  documents_ingested: number
  error: string | null
}

export interface Citation {
  file_name: string
  page: string
}

export interface ChatResponse {
  answer: string
  citations: Citation[]
  trace: string[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
}
