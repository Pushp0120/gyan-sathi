import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api, getToken, setToken } from '../services/api'
import type { User } from '../types'

interface AuthState {
  user: User | null
  loading: boolean
  loginWithToken: (token: string, user: User) => void
  logout: () => void
  refreshUser: () => Promise<void>
  updateUser: (u: Partial<User>) => void
}

const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  loginWithToken: () => {},
  logout: () => {},
  refreshUser: async () => {},
  updateUser: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await api<User>('/api/auth/me')
      setUser(me)
    } catch {
      setToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  const loginWithToken = useCallback((token: string, u: User) => {
    setToken(token)
    setUser(u)
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    window.location.href = '/login'
  }, [])

  const updateUser = useCallback((patch: Partial<User>) => {
    setUser((prev) => (prev ? { ...prev, ...patch } : prev))
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, loginWithToken, logout, refreshUser, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
