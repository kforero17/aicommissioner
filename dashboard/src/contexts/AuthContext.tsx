'use client'

import { createContext, useContext, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface User {
  id: string
  email: string
  name?: string
  hasCompletedOnboarding?: boolean
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string) => Promise<void>
  loginWithProvider: (provider: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    // Check for existing session
    const checkAuth = () => {
      const savedUser = localStorage.getItem('user')
      if (savedUser) {
        setUser(JSON.parse(savedUser))
      }
      setLoading(false)
    }
    checkAuth()
  }, [])

  const login = async (email: string) => {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    const newUser: User = {
      id: Math.random().toString(36).substr(2, 9),
      email,
      hasCompletedOnboarding: false
    }
    
    setUser(newUser)
    localStorage.setItem('user', JSON.stringify(newUser))
  }

  const loginWithProvider = async (provider: string) => {
    // Simulate OAuth flow
    await new Promise(resolve => setTimeout(resolve, 1500))
    
    const newUser: User = {
      id: Math.random().toString(36).substr(2, 9),
      email: `user@${provider}.com`,
      name: `${provider} User`,
      hasCompletedOnboarding: false
    }
    
    setUser(newUser)
    localStorage.setItem('user', JSON.stringify(newUser))
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem('user')
    router.push('/')
  }

  const value = {
    user,
    loading,
    login,
    loginWithProvider,
    logout,
    isAuthenticated: !!user
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
