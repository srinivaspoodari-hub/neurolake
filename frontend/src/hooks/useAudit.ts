/**
 * React Query Hooks for Audit Service
 */

import { useQuery } from '@tanstack/react-query'
import {
  auditService,
  AuditLogFilters,
  AuditLogEntry,
  AuditStats
} from '@/services/auditService'

// Query keys
export const auditKeys = {
  all: ['audit'] as const,
  logs: () => [...auditKeys.all, 'logs'] as const,
  log: (filters?: AuditLogFilters) => [...auditKeys.logs(), filters] as const,
  entry: (id: number) => [...auditKeys.all, 'entry', id] as const,
  userTrail: (userId: number) => [...auditKeys.all, 'user', userId] as const,
  stats: (params?: any) => [...auditKeys.all, 'stats', params] as const,
}

/**
 * Hook to fetch audit logs with filters
 */
export function useAuditLogs(filters?: AuditLogFilters) {
  return useQuery({
    queryKey: auditKeys.log(filters),
    queryFn: () => auditService.getAuditLogs(filters),
    refetchInterval: 10000, // Refresh every 10 seconds
  })
}

/**
 * Hook to fetch a specific audit log entry
 */
export function useAuditLogEntry(auditId: number) {
  return useQuery({
    queryKey: auditKeys.entry(auditId),
    queryFn: () => auditService.getAuditLogEntry(auditId),
    enabled: !!auditId,
  })
}

/**
 * Hook to fetch user audit trail
 */
export function useUserAuditTrail(
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
) {
  return useQuery({
    queryKey: [...auditKeys.userTrail(userId), params],
    queryFn: () => auditService.getUserAuditTrail(userId, params),
    enabled: !!userId,
  })
}

/**
 * Hook to fetch audit statistics
 */
export function useAuditStats(params?: {
  start_date?: string
  end_date?: string
  user_id?: number
}) {
  return useQuery({
    queryKey: auditKeys.stats(params),
    queryFn: () => auditService.getAuditStats(params),
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

/**
 * Hook to fetch recent activity
 */
export function useRecentActivity(limit: number = 50) {
  return useQuery({
    queryKey: [...auditKeys.logs(), 'recent', limit],
    queryFn: () => auditService.getRecentActivity(limit),
    refetchInterval: 5000, // Refresh every 5 seconds for recent activity
  })
}

/**
 * Hook to fetch failed actions
 */
export function useFailedActions(params?: {
  start_date?: string
  end_date?: string
  limit?: number
}) {
  return useQuery({
    queryKey: [...auditKeys.logs(), 'failed', params],
    queryFn: () => auditService.getFailedActions(params),
    refetchInterval: 10000,
  })
}

/**
 * Hook to get today's statistics
 */
export function useTodayStats() {
  return useQuery({
    queryKey: [...auditKeys.stats(), 'today'],
    queryFn: () => auditService.getTodayStats(),
    refetchInterval: 30000,
  })
}
