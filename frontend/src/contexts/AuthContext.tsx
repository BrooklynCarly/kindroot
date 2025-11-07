import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface User {
  email: string
  name: string
  picture?: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: () => void
  logout: () => void
  setAuthToken: (token: string) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check for token in localStorage on mount
    const storedToken = localStorage.getItem('auth_token')
    if (storedToken) {
      setToken(storedToken)
      fetchUserInfo(storedToken)
    } else {
      // Check URL for token (from OAuth callback)
      const urlParams = new URLSearchParams(window.location.search)
      const urlToken = urlParams.get('token')
      if (urlToken) {
        setAuthToken(urlToken)
        // Clean up URL
        window.history.replaceState({}, document.title, window.location.pathname)
      } else {
        setIsLoading(false)
      }
    }
  }, [])

  const fetchUserInfo = async (authToken: string) => {
    try {
      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
      } else {
        // Token is invalid, clear it
        localStorage.removeItem('auth_token')
        setToken(null)
      }
    } catch (error) {
      console.error('Failed to fetch user info:', error)
      localStorage.removeItem('auth_token')
      setToken(null)
    } finally {
      setIsLoading(false)
    }
  }

  const setAuthToken = (newToken: string) => {
    setToken(newToken)
    localStorage.setItem('auth_token', newToken)
    fetchUserInfo(newToken)
  }

  const login = () => {
    // Redirect to backend OAuth login endpoint
    window.location.href = `${API_URL}/api/auth/login`
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('auth_token')
  }

  const value = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    isLoading,
    login,
    logout,
    setAuthToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
