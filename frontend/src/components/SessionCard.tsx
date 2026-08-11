import { Link } from 'react-router-dom'
import type { StudySession } from '../api/types'

const STATUS_LABEL: Record<string, string> = {
  empty: 'No documents yet',
  ingesting: 'Processing documents…',
  ready: 'Ready',
  failed: 'Ingestion failed',
}

const STATUS_COLOR: Record<string, string> = {
  empty: 'text-gray-400',
  ingesting: 'text-amber-600',
  ready: 'text-emerald-600',
  failed: 'text-rose-600',
}

export function SessionCard({ session }: { session: StudySession }) {
  const created = new Date(session.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })

  return (
    <Link
      to={`/sessions/${session.id}`}
      className="flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition hover:shadow-md"
    >
      <h3 className="mb-1 font-semibold text-gray-900">{session.name}</h3>
      <p className="mb-3 text-xs text-gray-400">
        Created {created} · {session.document_count} document{session.document_count === 1 ? '' : 's'}
      </p>
      <p className={`mb-4 text-sm font-medium ${STATUS_COLOR[session.ingestion_status]}`}>
        {STATUS_LABEL[session.ingestion_status]}
      </p>
      <span className="mt-auto inline-block rounded-lg bg-brand-50 px-3 py-1.5 text-center text-sm font-medium text-brand-700">
        {session.ingestion_status === 'ready' ? 'Resume Chat' : 'Open Session'}
      </span>
    </Link>
  )
}
