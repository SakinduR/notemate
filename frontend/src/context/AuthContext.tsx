import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getMe, login as apiLogin, signup as apiSignup } from '../api/auth'
import type { User } from '../api/types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const TOKEN_KEY = 'notemate_token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      setLoading(false)
      return
    }
    getMe()
      .then(setUser)
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const res = await apiLogin(email, password)
    localStorage.setItem(TOKEN_KEY, res.access_token)
    setUser(res.user)
  }

  async function signup(email: string, password: string, name: string) {
    const res = await apiSignup(email, password, name)
    localStorage.setItem(TOKEN_KEY, res.access_token)
    setUser(res.user)
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
