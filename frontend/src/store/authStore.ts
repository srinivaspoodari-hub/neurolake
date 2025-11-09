import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authService, type User as ApiUser } from '@/services/authService'
import { getErrorMessage } from '@/lib/api'

interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  is_active: boolean
  is_superuser: boolean
  roles: string[]
}

interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  setUser: (user: User, token: string, refreshToken?: string) => void
  clearError: () => void
  checkAuth: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authService.login({ username, password })

          const user: User = {
            id: response.user.id,
            username: response.user.username,
            email: response.user.email,
            full_name: response.user.full_name,
            is_active: response.user.is_active,
            is_superuser: response.user.is_superuser,
            roles: response.user.roles,
          }

          set({
            user,
            token: response.access_token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          })
        } catch (error) {
          const message = getErrorMessage(error)
          set({
            user: null,
            token: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
            error: message,
          })
          throw new Error(message)
        }
      },

      logout: async () => {
        try {
          await authService.logout()
        } catch (error) {
          console.error('Logout error:', error)
        } finally {
          set({
            user: null,
            token: null,
            refreshToken: null,
            isAuthenticated: false,
            error: null,
          })
        }
      },

      setUser: (user: User, token: string, refreshToken?: string) => {
        set({
          user,
          token,
          refreshToken: refreshToken || get().refreshToken,
          isAuthenticated: true,
          error: null,
        })
      },

      clearError: () => {
        set({ error: null })
      },

      checkAuth: async () => {
        const token = get().token
        if (!token) {
          set({ isAuthenticated: false })
          return
        }

        try {
          const isValid = await authService.verifyToken()
          if (!isValid) {
            // Try to refresh token
            const refreshToken = get().refreshToken
            if (refreshToken) {
              const response = await authService.refreshToken(refreshToken)
              const user: User = {
                id: response.user.id,
                username: response.user.username,
                email: response.user.email,
                full_name: response.user.full_name,
                is_active: response.user.is_active,
                is_superuser: response.user.is_superuser,
                roles: response.user.roles,
              }
              set({
                user,
                token: response.access_token,
                refreshToken: response.refresh_token,
                isAuthenticated: true,
              })
            } else {
              // No refresh token, logout
              get().logout()
            }
          }
        } catch (error) {
          console.error('Auth check failed:', error)
          get().logout()
        }
      },
    }),
    {
      name: 'neurolake-auth',
    }
  )
)
