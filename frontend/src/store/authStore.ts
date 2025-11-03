import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  name: string
  email: string
  role: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User, token: string) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: async (email: string, password: string) => {
        // Mock login - replace with actual API call
        const mockUser: User = {
          id: '1',
          name: 'John Doe',
          email,
          role: 'admin',
        }
        const mockToken = 'mock-jwt-token'

        set({
          user: mockUser,
          token: mockToken,
          isAuthenticated: true,
        })
      },
      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        })
      },
      setUser: (user: User, token: string) => {
        set({
          user,
          token,
          isAuthenticated: true,
        })
      },
    }),
    {
      name: 'neurolake-auth',
    }
  )
)
