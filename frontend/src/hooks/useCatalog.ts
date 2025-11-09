/**
 * React Query Hooks for Catalog Service
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  catalogService,
  SchemaInfo,
  TableInfo,
  TableDetails,
  TableVersion,
  TablePermission,
} from '@/services/catalogService'

// Query keys
export const catalogKeys = {
  all: ['catalog'] as const,
  schemas: () => [...catalogKeys.all, 'schemas'] as const,
  schema: (name: string) => [...catalogKeys.schemas(), name] as const,
  tables: (schemaName: string) => [...catalogKeys.schema(schemaName), 'tables'] as const,
  table: (schemaName: string, tableName: string) =>
    [...catalogKeys.tables(schemaName), tableName] as const,
  tableDetails: (schemaName: string, tableName: string) =>
    [...catalogKeys.table(schemaName, tableName), 'details'] as const,
  tableDDL: (schemaName: string, tableName: string) =>
    [...catalogKeys.table(schemaName, tableName), 'ddl'] as const,
  tableSample: (schemaName: string, tableName: string) =>
    [...catalogKeys.table(schemaName, tableName), 'sample'] as const,
  tableVersions: (schemaName: string, tableName: string) =>
    [...catalogKeys.table(schemaName, tableName), 'versions'] as const,
  tablePermissions: (schemaName: string, tableName: string) =>
    [...catalogKeys.table(schemaName, tableName), 'permissions'] as const,
}

/**
 * Hook to fetch all schemas
 */
export function useSchemas() {
  return useQuery({
    queryKey: catalogKeys.schemas(),
    queryFn: () => catalogService.listSchemas(),
  })
}

/**
 * Hook to fetch tables in a schema
 */
export function useTables(schemaName: string) {
  return useQuery({
    queryKey: catalogKeys.tables(schemaName),
    queryFn: () => catalogService.listTables(schemaName),
    enabled: !!schemaName,
  })
}

/**
 * Hook to fetch table details
 */
export function useTableDetails(schemaName: string, tableName: string) {
  return useQuery({
    queryKey: catalogKeys.tableDetails(schemaName, tableName),
    queryFn: () => catalogService.getTableDetails(schemaName, tableName),
    enabled: !!(schemaName && tableName),
  })
}

/**
 * Hook to fetch table DDL
 */
export function useTableDDL(schemaName: string, tableName: string) {
  return useQuery({
    queryKey: catalogKeys.tableDDL(schemaName, tableName),
    queryFn: () => catalogService.getTableDDL(schemaName, tableName),
    enabled: !!(schemaName && tableName),
  })
}

/**
 * Hook to fetch table sample data
 */
export function useTableSample(schemaName: string, tableName: string, limit: number = 100) {
  return useQuery({
    queryKey: [...catalogKeys.tableSample(schemaName, tableName), limit],
    queryFn: () => catalogService.getTableSample(schemaName, tableName, limit),
    enabled: !!(schemaName && tableName),
  })
}

/**
 * Hook to fetch table versions
 */
export function useTableVersions(schemaName: string, tableName: string) {
  return useQuery({
    queryKey: catalogKeys.tableVersions(schemaName, tableName),
    queryFn: () => catalogService.getTableVersions(schemaName, tableName),
    enabled: !!(schemaName && tableName),
  })
}

/**
 * Hook to fetch table permissions
 */
export function useTablePermissions(schemaName: string, tableName: string) {
  return useQuery({
    queryKey: catalogKeys.tablePermissions(schemaName, tableName),
    queryFn: () => catalogService.getTablePermissions(schemaName, tableName),
    enabled: !!(schemaName && tableName),
  })
}

/**
 * Hook to create a table
 */
export function useCreateTable() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      schemaName,
      data,
    }: {
      schemaName: string
      data: {
        name: string
        columns: Array<{ name: string; type: string; nullable?: boolean; description?: string }>
        description?: string
        format?: string
        location?: string
        properties?: Record<string, any>
      }
    }) => catalogService.createTable(schemaName, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: catalogKeys.tables(variables.schemaName) })
      queryClient.invalidateQueries({ queryKey: catalogKeys.schemas() })
    },
  })
}

/**
 * Hook to delete a table
 */
export function useDeleteTable() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ schemaName, tableName }: { schemaName: string; tableName: string }) =>
      catalogService.deleteTable(schemaName, tableName),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: catalogKeys.tables(variables.schemaName) })
      queryClient.removeQueries({
        queryKey: catalogKeys.table(variables.schemaName, variables.tableName),
      })
    },
  })
}

/**
 * Hook to update table properties
 */
export function useUpdateTableProperties() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      schemaName,
      tableName,
      properties,
    }: {
      schemaName: string
      tableName: string
      properties: Record<string, any>
    }) => catalogService.updateTableProperties(schemaName, tableName, properties),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: catalogKeys.tableDetails(variables.schemaName, variables.tableName),
      })
    },
  })
}

/**
 * Hook to grant table access
 */
export function useGrantAccess() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      schemaName,
      tableName,
      data,
    }: {
      schemaName: string
      tableName: string
      data: {
        principal_type: 'user' | 'group' | 'organization'
        principal_id: string | number
        permissions: string[]
      }
    }) => catalogService.grantAccess(schemaName, tableName, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: catalogKeys.tablePermissions(variables.schemaName, variables.tableName),
      })
    },
  })
}

/**
 * Hook to revoke table access
 */
export function useRevokeAccess() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      schemaName,
      tableName,
      permissionId,
    }: {
      schemaName: string
      tableName: string
      permissionId: number
    }) => catalogService.revokeAccess(schemaName, tableName, permissionId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: catalogKeys.tablePermissions(variables.schemaName, variables.tableName),
      })
    },
  })
}
