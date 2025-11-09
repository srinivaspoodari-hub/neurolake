/**
 * Catalog Service
 *
 * Handles all data catalog API calls:
 * - Browse assets
 * - Search metadata
 * - Get lineage
 * - Manage schemas
 */

import apiClient from '@/lib/api'

// Types
export interface CatalogAsset {
  id: string
  name: string
  type: 'table' | 'view' | 'file' | 'dataset'
  schema?: string
  description?: string
  tags?: string[]
  owner?: string
  created_at: string
  updated_at: string
  metadata?: Record<string, any>
}

export interface TableSchema {
  table_name: string
  schema_name: string
  columns: ColumnSchema[]
  row_count?: number
  size_bytes?: number
}

export interface ColumnSchema {
  name: string
  type: string
  nullable: boolean
  description?: string
}

export interface LineageNode {
  id: string
  name: string
  type: string
}

export interface LineageEdge {
  source: string
  target: string
  type: string
}

export interface Lineage {
  nodes: LineageNode[]
  edges: LineageEdge[]
}

// Catalog Service
class CatalogService {
  /**
   * Get all catalog assets
   */
  async getAssets(params?: {
    type?: string
    tag?: string
    search?: string
    limit?: number
    offset?: number
  }): Promise<{
    assets: CatalogAsset[]
    total: number
  }> {
    const response = await apiClient.get('/api/v1/catalog/assets', { params })
    return response.data
  }

  /**
   * Get asset by ID
   */
  async getAsset(assetId: string): Promise<CatalogAsset> {
    const response = await apiClient.get<CatalogAsset>(`/api/v1/catalog/assets/${assetId}`)
    return response.data
  }

  /**
   * Search catalog
   */
  async search(query: string, params?: {
    type?: string
    limit?: number
  }): Promise<{
    results: CatalogAsset[]
    total: number
  }> {
    const response = await apiClient.get('/api/v1/catalog/search', {
      params: { q: query, ...params },
    })
    return response.data
  }

  /**
   * Get table schema
   */
  async getTableSchema(schema: string, table: string): Promise<TableSchema> {
    const response = await apiClient.get<TableSchema>(
      `/api/v1/catalog/schemas/${schema}/tables/${table}`
    )
    return response.data
  }

  /**
   * Get data lineage for asset
   */
  async getLineage(assetId: string, params?: {
    direction?: 'upstream' | 'downstream' | 'both'
    depth?: number
  }): Promise<Lineage> {
    const response = await apiClient.get<Lineage>(
      `/api/v1/catalog/lineage/${assetId}`,
      { params }
    )
    return response.data
  }

  /**
   * Update asset metadata
   */
  async updateAsset(
    assetId: string,
    data: Partial<CatalogAsset>
  ): Promise<CatalogAsset> {
    const response = await apiClient.put<CatalogAsset>(
      `/api/v1/catalog/assets/${assetId}`,
      data
    )
    return response.data
  }

  /**
   * Add tags to asset
   */
  async addTags(assetId: string, tags: string[]): Promise<CatalogAsset> {
    const response = await apiClient.post<CatalogAsset>(
      `/api/v1/catalog/assets/${assetId}/tags`,
      { tags }
    )
    return response.data
  }

  /**
   * Remove tags from asset
   */
  async removeTags(assetId: string, tags: string[]): Promise<CatalogAsset> {
    const response = await apiClient.delete(
      `/api/v1/catalog/assets/${assetId}/tags`,
      { data: { tags } }
    )
    return response.data
  }

  /**
   * List all schemas in the catalog
   */
  async listSchemas(): Promise<SchemaInfo[]> {
    const response = await apiClient.get<{ schemas: SchemaInfo[] }>('/api/v1/catalog/schemas')
    return response.data.schemas
  }

  /**
   * List all tables in a schema
   */
  async listTables(schemaName: string): Promise<TableInfo[]> {
    const response = await apiClient.get<{ tables: TableInfo[] }>(
      `/api/v1/catalog/schemas/${schemaName}/tables`
    )
    return response.data.tables
  }

  /**
   * Get detailed table information
   */
  async getTableDetails(schemaName: string, tableName: string): Promise<TableDetails> {
    const response = await apiClient.get<TableDetails>(
      `/api/v1/catalog/schemas/${schemaName}/tables/${tableName}/details`
    )
    return response.data
  }

  /**
   * Get table DDL
   */
  async getTableDDL(schemaName: string, tableName: string): Promise<{ ddl: string }> {
    const response = await apiClient.get<{ ddl: string }>(
      `/api/v1/catalog/schemas/${schemaName}/tables/${tableName}/ddl`
    )
    return response.data
  }

  /**
   * Get table sample data
   */
  async getTableSample(
    schemaName: string,
    tableName: string,
    limit: number = 100
  ): Promise<{ columns: string[]; data: any[] }> {
    const response = await apiClient.get(
      `/api/v1/catalog/schemas/${schemaName}/tables/${tableName}/sample`,
      { params: { limit } }
    )
    return response.data
  }

  /**
   * Get table version history
   */
  async getTableVersions(schemaName: string, tableName: string): Promise<TableVersion[]> {
    const response = await apiClient.get<{ versions: TableVersion[] }>(
      `/api/v1/catalog/schemas/${schemaName}/tables/${tableName}/versions`
    )
    return response.data.versions
  }

  /**
   * Get table access permissions
   */
  async getTablePermissions(
    schemaName: string,
    tableName: string
  ): Promise<TablePermission[]> {
    const response = await apiClient.get<{ permissions: TablePermission[] }>(
      `/api/v1/catalog/schemas/${schemaName}/tables/${tableName}/permissions`
    )
    return response.data.permissions
  }

  /**
   * Grant table access to user/group
   */
  async grantAccess(
    schemaName: string,
    tableName: string,
    data: {
      principal_type: 'user' | 'group' | 'organization'
      principal_id: string | number
      permissions: string[]
    }
  ): Promise<void> {
    await apiClient.post(
      `/api/v1/catalog/schemas/${schemaName}/tables/${tableName}/permissions`,
      data
    )
  }

  /**
   * Revoke table access
   */
  async revokeAccess(
    schemaName: string,
    tableName: string,
    permissionId: number
  ): Promise<void> {
    await apiClient.delete(
      `/api/v1/catalog/schemas/${schemaName}/tables/${tableName}/permissions/${permissionId}`
    )
  }

  /**
   * Create new table
   */
  async createTable(
    schemaName: string,
    data: {
      name: string
      columns: Array<{ name: string; type: string; nullable?: boolean; description?: string }>
      description?: string
      format?: string
      location?: string
      properties?: Record<string, any>
    }
  ): Promise<TableDetails> {
    const response = await apiClient.post<TableDetails>(
      `/api/v1/catalog/schemas/${schemaName}/tables`,
      data
    )
    return response.data
  }

  /**
   * Delete table
   */
  async deleteTable(schemaName: string, tableName: string): Promise<void> {
    await apiClient.delete(`/api/v1/catalog/schemas/${schemaName}/tables/${tableName}`)
  }

  /**
   * Update table properties
   */
  async updateTableProperties(
    schemaName: string,
    tableName: string,
    properties: Record<string, any>
  ): Promise<TableDetails> {
    const response = await apiClient.patch<TableDetails>(
      `/api/v1/catalog/schemas/${schemaName}/tables/${tableName}`,
      { properties }
    )
    return response.data
  }
}

// Additional Types
export interface SchemaInfo {
  name: string
  database?: string
  description?: string
  table_count: number
  created_at: string
  owner?: string
}

export interface TableInfo {
  name: string
  schema: string
  type: 'table' | 'view' | 'external'
  format?: string
  row_count?: number
  size_bytes?: number
  created_at: string
  updated_at: string
  description?: string
}

export interface TableDetails {
  name: string
  schema: string
  database?: string
  type: 'table' | 'view' | 'external'
  format: string
  location?: string
  description?: string
  owner?: string
  created_by?: string
  created_at: string
  updated_at: string
  last_accessed?: string
  columns: ColumnSchema[]
  properties?: Record<string, any>
  statistics?: {
    row_count?: number
    size_bytes?: number
    file_count?: number
  }
  partitions?: Array<{ name: string; type: string }>
}

export interface TableVersion {
  version: number
  created_at: string
  created_by: string
  operation: 'CREATE' | 'UPDATE' | 'DELETE' | 'ALTER'
  changes?: Record<string, any>
  snapshot_id?: string
}

export interface TablePermission {
  id: number
  principal_type: 'user' | 'group' | 'organization'
  principal_id: string | number
  principal_name: string
  permissions: string[]
  granted_by?: string
  granted_at: string
}

// Export singleton instance
export const catalogService = new CatalogService()
export default catalogService
