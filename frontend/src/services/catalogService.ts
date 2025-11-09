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
}

// Export singleton instance
export const catalogService = new CatalogService()
export default catalogService
