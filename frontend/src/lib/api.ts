/**
 * NeuroLake API Client
 *
 * Centralized Axios instance for all API calls with:
 * - Automatic JWT token injection
 * - Request/response interceptors
 * - Error handling
 * - Request retry logic
 */

import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const API_TIMEOUT = 30000 // 30 seconds

// Create Axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - Add authentication token
apiClient.interceptors.request.use(
  (config) => {
    // Get token from localStorage
    const authData = localStorage.getItem('neurolake-auth')
    if (authData) {
      try {
        const parsed = JSON.parse(authData)
        const token = parsed.state?.token
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
      } catch (error) {
        console.error('Failed to parse auth data:', error)
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - Handle errors globally
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    // Handle 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      // Clear auth state and redirect to login
      localStorage.removeItem('neurolake-auth')

      // Optionally try to refresh token here
      // For now, just reject and let the app handle redirect
      return Promise.reject(error)
    }

    // Handle network errors
    if (!error.response) {
      console.error('Network error:', error.message)
      return Promise.reject({
        message: 'Network error. Please check your connection.',
        error,
      })
    }

    // Handle other errors
    const errorMessage = error.response?.data?.detail ||
                         error.response?.data?.message ||
                         error.message ||
                         'An unexpected error occurred'

    return Promise.reject({
      message: errorMessage,
      status: error.response?.status,
      data: error.response?.data,
      error,
    })
  }
)

// Helper function to get error message
export const getErrorMessage = (error: unknown): string => {
  if (typeof error === 'string') return error
  if (error && typeof error === 'object' && 'message' in error) {
    return String(error.message)
  }
  return 'An unexpected error occurred'
}

// Export the configured client
export default apiClient
