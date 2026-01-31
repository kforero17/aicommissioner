'use client'

import { createContext, useContext, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface User {
  id: string
  email: string
  name?: string
  username?: string
  hasCompletedOnboarding?: boolean
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string) => Promise<void>
  loginWithProvider: (provider: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  const checkAuthWithBackend = async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const userData = await response.json()
        const mappedUser: User = {
          id: String(userData.id),
          email: userData.email || '',
          name: userData.username,
          username: userData.username,
          hasCompletedOnboarding: true
        }
        setUser(mappedUser)
        return mappedUser
      }
    } catch {
      // Auth check failed - user not logged in
    }
    setUser(null)
    return null
  }

  useEffect(() => {
    // Check auth status with backend on mount
    const checkAuth = async () => {
      await checkAuthWithBackend()
      setLoading(false)
    }
    checkAuth()
  }, [])

  const login = async (email: string) => {
    // Magic link login - would send email via backend
    await new Promise(resolve => setTimeout(resolve, 1500))
    // After magic link is clicked, backend sets cookie and we refresh user
    await checkAuthWithBackend()
  }

  const loginWithProvider = async (provider: string) => {
    if (provider === 'yahoo') {
      window.location.href = `${API_BASE}/auth/yahoo/login`
    } else if (provider === 'google') {
      window.location.href = `${API_BASE}/auth/google/login`
    } else if (provider === 'apple') {
      alert('Apple Sign-In coming soon!')
    }
  }

  const logout = async () => {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      })
    } catch {
      // Logout failed, but clear local state anyway
    }
    setUser(null)
    router.push('/')
  }

  const refreshUser = async () => {
    await checkAuthWithBackend()
  }

  const value = {
    user,
    loading,
    login,
    loginWithProvider,
    logout,
    isAuthenticated: !!user,
    refreshUser
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
