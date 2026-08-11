import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-[#f8f7fc]">
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
        <Link to="/dashboard" className="flex items-center gap-2 text-lg font-semibold text-brand-700">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">N</span>
          NoteMate
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">{user?.name}</span>
          <button
            onClick={logout}
            className="rounded-md border border-gray-200 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          >
            Log out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  )
}
