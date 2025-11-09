/**
 * Authentication Service
 *
 * Handles all authentication-related API calls:
 * - Login
 * - Logout
 * - Register
 * - Token refresh
 * - User management
 */

import apiClient from '@/lib/api'

// Types
export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
  is_superuser: boolean
  roles: string[]
  created_at: string
  last_login: string | null
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  full_name?: string
  roles?: string[]
}

export interface PasswordChangeRequest {
  old_password: string
  new_password: string
}

// Authentication Service
class AuthService {
  /**
   * Login user with username and password
   */
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/api/auth/login', credentials)
    return response.data
  }

  /**
   * Logout user (client-side only for now)
   */
  async logout(): Promise<void> {
    // In the future, could call server to invalidate token
    // await apiClient.post('/api/auth/logout')
    localStorage.removeItem('neurolake-auth')
  }

  /**
   * Register new user
   */
  async register(userData: RegisterRequest): Promise<User> {
    const response = await apiClient.post<User>('/api/auth/register', userData)
    return response.data
  }

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/api/auth/me')
    return response.data
  }

  /**
   * Update current user profile
   */
  async updateProfile(data: Partial<User>): Promise<User> {
    const response = await apiClient.put<User>('/api/auth/me', data)
    return response.data
  }

  /**
   * Change password
   */
  async changePassword(data: PasswordChangeRequest): Promise<void> {
    await apiClient.post('/api/auth/change-password', data)
  }

  /**
   * Verify JWT token is still valid
   */
  async verifyToken(): Promise<boolean> {
    try {
      await apiClient.get('/api/auth/verify')
      return true
    } catch {
      return false
    }
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/api/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  }
}

// Export singleton instance
export const authService = new AuthService()
export default authService
