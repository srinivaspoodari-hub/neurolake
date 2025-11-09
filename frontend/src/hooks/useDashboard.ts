/**
 * Dashboard Data Hook
 *
 * Custom hook for fetching dashboard statistics and data
 * Uses React Query for caching and automatic refetching
 */

import { useQuery } from '@tanstack/react-query'
import { queryService } from '@/services/queryService'
import { dataService } from '@/services/dataService'

export interface DashboardStats {
  totalQueries: number
  activePipelines: number
  dataProcessed: string
  avgQueryTime: string
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async (): Promise<DashboardStats> => {
      // Fetch query history to calculate stats
      const queryHistory = await queryService.getQueryHistory({ limit: 1000 })

      // Calculate total queries
      const totalQueries = queryHistory.total

      // Calculate average query time
      const avgTime = queryHistory.queries.length > 0
        ? queryHistory.queries.reduce((sum, q) => sum + q.execution_time_ms, 0) / queryHistory.queries.length
        : 0

      // For now, return mock data for pipelines and data processed
      // These will be replaced when pipeline and metrics APIs are implemented
      return {
        totalQueries,
        activePipelines: 0, // TODO: Fetch from pipelines API
        dataProcessed: '0 TB', // TODO: Fetch from metrics API
        avgQueryTime: `${Math.round(avgTime)}ms`,
      }
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  })
}

export function useRecentQueries(limit: number = 5) {
  return useQuery({
    queryKey: ['queries', 'recent', limit],
    queryFn: async () => {
      const result = await queryService.getQueryHistory({ limit, offset: 0 })
      return result.queries
    },
    refetchInterval: 10000, // Refetch every 10 seconds
  })
}

export function useTableList() {
  return useQuery({
    queryKey: ['tables', 'list'],
    queryFn: async () => {
      const schemas = await dataService.getSchemas()

      // Fetch tables from each schema
      const allTables = await Promise.all(
        schemas.map(async (schema) => {
          const tables = await dataService.getTables(schema.name)
          return tables.map(table => ({ ...table, schema: schema.name }))
        })
      )

      return allTables.flat()
    },
    refetchInterval: 60000, // Refetch every minute
  })
}
