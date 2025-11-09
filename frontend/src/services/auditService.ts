/**
 * Audit Service
 *
 * Handles audit log viewing and compliance monitoring
 */

import apiClient from '@/lib/api'

export interface AuditLogEntry {
  id: number
  user_id?: number
  username?: string
  action: string
  resource_type: string
  resource_id?: string
  resource_name?: string
  status: 'success' | 'failure'
  ip_address?: string
  user_agent?: string
  changes?: Record<string, any>
  error_message?: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface AuditLogListResponse {
  logs: AuditLogEntry[]
  total: number
  limit: number
  offset: number
}

export interface AuditLogFilters {
  user_id?: number
  action?: string
  resource_type?: string
  resource_id?: string
  status?: 'success' | 'failure'
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}

export interface AuditStats {
  total_events: number
  by_action: Record<string, number>
  by_resource: Record<string, number>
  by_status: Record<string, number>
  by_user: Record<string, number>
  time_range: {
    start_date?: string
    end_date?: string
  }
}

class AuditService {
  /**
   * Get audit logs with optional filtering
   */
  async getAuditLogs(filters?: AuditLogFilters): Promise<AuditLogListResponse> {
    const response = await apiClient.get<AuditLogListResponse>(
      '/api/v1/audit',
      { params: filters }
    )
    return response.data
  }

  /**
   * Get audit trail for a specific user
   */
  async getUserAuditTrail(
    userId: number,
    params?: {
      action?: string
      resource_type?: string
      status?: 'success' | 'failure'
      start_date?: string
      end_date?: string
      limit?: number
      offset?: number
    }
  ): Promise<AuditLogListResponse> {
    const response = await apiClient.get<AuditLogListResponse>(
      `/api/v1/audit/users/${userId}`,
      { params }
    )
    return response.data
  }

  /**
   * Get a specific audit log entry by ID
   */
  async getAuditLogEntry(auditId: number): Promise<AuditLogEntry> {
    const response = await apiClient.get<AuditLogEntry>(
      `/api/v1/audit/${auditId}`
    )
    return response.data
  }

  /**
   * Get audit statistics summary
   */
  async getAuditStats(params?: {
    start_date?: string
    end_date?: string
    user_id?: number
  }): Promise<AuditStats> {
    const response = await apiClient.get<AuditStats>(
      '/api/v1/audit/stats/summary',
      { params }
    )
    return response.data
  }

  /**
   * Helper: Get recent activity (last 24 hours)
   */
  async getRecentActivity(limit: number = 50): Promise<AuditLogEntry[]> {
    const now = new Date()
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000)

    const response = await this.getAuditLogs({
      start_date: yesterday.toISOString(),
      end_date: now.toISOString(),
      limit,
      offset: 0
    })

    return response.logs
  }

  /**
   * Helper: Get failed actions (for security monitoring)
   */
  async getFailedActions(params?: {
    start_date?: string
    end_date?: string
    limit?: number
  }): Promise<AuditLogEntry[]> {
    const response = await this.getAuditLogs({
      status: 'failure',
      ...params,
    })

    return response.logs
  }

  /**
   * Helper: Get user activity for a date range
   */
  async getUserActivity(
    userId: number,
    startDate: Date,
    endDate: Date
  ): Promise<AuditLogEntry[]> {
    const response = await this.getUserAuditTrail(userId, {
      start_date: startDate.toISOString(),
      end_date: endDate.toISOString(),
    })

    return response.logs
  }

  /**
   * Helper: Search audit logs by action
   */
  async searchByAction(
    action: string,
    params?: {
      start_date?: string
      end_date?: string
      limit?: number
    }
  ): Promise<AuditLogEntry[]> {
    const response = await this.getAuditLogs({
      action,
      ...params,
    })

    return response.logs
  }

  /**
   * Helper: Get audit logs for a specific resource
   */
  async getResourceAuditTrail(
    resourceType: string,
    resourceId: string,
    params?: {
      start_date?: string
      end_date?: string
      limit?: number
    }
  ): Promise<AuditLogEntry[]> {
    const response = await this.getAuditLogs({
      resource_type: resourceType,
      resource_id: resourceId,
      ...params,
    })

    return response.logs
  }

  /**
   * Helper: Get statistics for today
   */
  async getTodayStats(): Promise<AuditStats> {
    const now = new Date()
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate())

    return this.getAuditStats({
      start_date: startOfDay.toISOString(),
      end_date: now.toISOString(),
    })
  }

  /**
   * Helper: Format audit log entry for display
   */
  formatAuditEntry(entry: AuditLogEntry): string {
    const timestamp = new Date(entry.timestamp).toLocaleString()
    const user = entry.username || `User ${entry.user_id}` || 'System'
    const status = entry.status === 'success' ? '✓' : '✗'
    const resource = entry.resource_name || entry.resource_id || entry.resource_type

    return `[${timestamp}] ${status} ${user} - ${entry.action} on ${resource}`
  }
}

export const auditService = new AuditService()
