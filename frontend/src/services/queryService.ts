/**
 * Query Service
 *
 * Handles all query-related API calls:
 * - Execute queries
 * - Get query history
 * - Save queries
 * - Explain queries
 * - Cancel queries
 */

import apiClient from '@/lib/api'

// Types
export interface QueryRequest {
  sql: string
  database?: string
  limit?: number
  timeout?: number
  optimize?: boolean
  check_compliance?: boolean
}

export interface QueryResponse {
  success: boolean
  query_id: string
  data?: Record<string, any>[]
  columns?: string[]
  row_count: number
  execution_time_ms: number
  optimized: boolean
  compliance_checked: boolean
  compliance_warnings: string[]
  error?: string
}

export interface ExplainResponse {
  query: string
  plan: string
  estimated_cost?: number
  optimizations: string[]
}

export interface QueryHistory {
  query_id: string
  sql: string
  execution_time_ms: number
  row_count: number
  status: string
  timestamp: string
  error?: string
}

export interface SavedQuery {
  id: number
  name: string
  description?: string
  sql: string
  created_by: string
  created_at: string
  updated_at: string
  tags?: string[]
}

// Query Service
class QueryService {
  /**
   * Execute SQL query
   */
  async executeQuery(request: QueryRequest): Promise<QueryResponse> {
    const response = await apiClient.post<QueryResponse>('/api/v1/queries', request)
    return response.data
  }

  /**
   * Get query execution plan
   */
  async explainQuery(request: QueryRequest): Promise<ExplainResponse> {
    const response = await apiClient.post<ExplainResponse>('/api/v1/queries/explain', request)
    return response.data
  }

  /**
   * Get query execution history
   */
  async getQueryHistory(params?: {
    limit?: number
    offset?: number
  }): Promise<{
    queries: QueryHistory[]
    total: number
    limit: number
    offset: number
  }> {
    const response = await apiClient.get('/api/v1/queries/history', { params })
    return response.data
  }

  /**
   * Cancel running query
   */
  async cancelQuery(queryId: string): Promise<{
    query_id: string
    status: string
    message: string
  }> {
    const response = await apiClient.delete(`/api/v1/queries/${queryId}/cancel`)
    return response.data
  }

  /**
   * Save query for later use
   */
  async saveQuery(data: {
    name: string
    description?: string
    sql: string
    tags?: string[]
  }): Promise<SavedQuery> {
    const response = await apiClient.post<SavedQuery>('/api/v1/queries/saved', data)
    return response.data
  }

  /**
   * Get saved queries
   */
  async getSavedQueries(params?: {
    limit?: number
    offset?: number
    tag?: string
  }): Promise<{
    queries: SavedQuery[]
    total: number
  }> {
    const response = await apiClient.get('/api/v1/queries/saved', { params })
    return response.data
  }

  /**
   * Get saved query by ID
   */
  async getSavedQuery(id: number): Promise<SavedQuery> {
    const response = await apiClient.get<SavedQuery>(`/api/v1/queries/saved/${id}`)
    return response.data
  }

  /**
   * Update saved query
   */
  async updateSavedQuery(id: number, data: Partial<SavedQuery>): Promise<SavedQuery> {
    const response = await apiClient.put<SavedQuery>(`/api/v1/queries/saved/${id}`, data)
    return response.data
  }

  /**
   * Delete saved query
   */
  async deleteSavedQuery(id: number): Promise<void> {
    await apiClient.delete(`/api/v1/queries/saved/${id}`)
  }
}

// Export singleton instance
export const queryService = new QueryService()
export default queryService
