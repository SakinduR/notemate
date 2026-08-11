import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { SessionCard } from '../components/SessionCard'
import { listSessions } from '../api/sessions'
import type { StudySession } from '../api/types'

export function DashboardPage() {
  const [sessions, setSessions] = useState<StudySession[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listSessions()
      .then((res) => setSessions(res.sessions))
      .catch(() => setError('Could not load your sessions. Please try again.'))
  }, [])

  return (
    <Layout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Your Study Sessions</h1>
          <p className="text-sm text-gray-500">Upload files to start a conversational agent session.</p>
        </div>
        <Link
          to="/sessions/new"
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          + New
        </Link>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}

      {sessions === null && !error && <p className="text-sm text-gray-400">Loading…</p>}

      {sessions && sessions.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="mb-3 text-gray-500">You don't have any study sessions yet.</p>
          <Link to="/sessions/new" className="font-medium text-brand-600 hover:underline">
            Create your first session
          </Link>
        </div>
      )}

      {sessions && sessions.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sessions.map((s) => (
            <SessionCard key={s.id} session={s} />
          ))}
          <Link
            to="/sessions/new"
            className="flex min-h-[160px] flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 text-gray-400 transition hover:border-brand-400 hover:text-brand-600"
          >
            <span className="mb-1 text-2xl">+</span>
            Create New Session
          </Link>
        </div>
      )}
    </Layout>
  )
}
