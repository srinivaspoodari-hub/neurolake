/**
 * Data Service
 *
 * Handles all data-related API calls:
 * - Browse schemas and tables
 * - Preview data
 * - Upload data
 * - Bulk operations
 */

import apiClient from '@/lib/api'

// Types
export interface Schema {
  name: string
  table_count: number
  created_at?: string
}

export interface Table {
  name: string
  schema: string
  type: string
  row_count?: number
  size_bytes?: number
  created_at: string
  updated_at: string
}

export interface TablePreview {
  columns: string[]
  data: Record<string, any>[]
  total_rows: number
  preview_rows: number
}

export interface TableStats {
  row_count: number
  size_bytes: number
  column_count: number
  created_at: string
  updated_at: string
  last_accessed: string
}

// Data Service
class DataService {
  /**
   * Get all schemas
   */
  async getSchemas(): Promise<Schema[]> {
    const response = await apiClient.get<Schema[]>('/api/v1/data/schemas')
    return response.data
  }

  /**
   * Get tables in schema
   */
  async getTables(schema: string = 'public'): Promise<Table[]> {
    const response = await apiClient.get<Table[]>(`/api/v1/data/schemas/${schema}/tables`)
    return response.data
  }

  /**
   * Get table details
   */
  async getTable(schema: string, table: string): Promise<Table> {
    const response = await apiClient.get<Table>(
      `/api/v1/data/schemas/${schema}/tables/${table}`
    )
    return response.data
  }

  /**
   * Preview table data
   */
  async previewTable(
    schema: string,
    table: string,
    params?: {
      limit?: number
      offset?: number
    }
  ): Promise<TablePreview> {
    const response = await apiClient.get<TablePreview>(
      `/api/v1/data/schemas/${schema}/tables/${table}/preview`,
      { params }
    )
    return response.data
  }

  /**
   * Get table statistics
   */
  async getTableStats(schema: string, table: string): Promise<TableStats> {
    const response = await apiClient.get<TableStats>(
      `/api/v1/data/schemas/${schema}/tables/${table}/stats`
    )
    return response.data
  }

  /**
   * Upload CSV file
   */
  async uploadCsv(
    file: File,
    options?: {
      schema?: string
      table_name?: string
      delimiter?: string
      has_header?: boolean
    }
  ): Promise<{
    success: boolean
    table_name: string
    rows_imported: number
  }> {
    const formData = new FormData()
    formData.append('file', file)
    if (options) {
      Object.entries(options).forEach(([key, value]) => {
        formData.append(key, String(value))
      })
    }

    const response = await apiClient.post('/api/v1/data/upload/csv', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  /**
   * Upload Parquet file
   */
  async uploadParquet(
    file: File,
    options?: {
      schema?: string
      table_name?: string
    }
  ): Promise<{
    success: boolean
    table_name: string
    rows_imported: number
  }> {
    const formData = new FormData()
    formData.append('file', file)
    if (options) {
      Object.entries(options).forEach(([key, value]) => {
        formData.append(key, String(value))
      })
    }

    const response = await apiClient.post('/api/v1/data/upload/parquet', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  }

  /**
   * Create new table
   */
  async createTable(data: {
    schema: string
    table_name: string
    columns: { name: string; type: string }[]
    description?: string
  }): Promise<Table> {
    const response = await apiClient.post<Table>('/api/v1/data/tables', data)
    return response.data
  }

  /**
   * Delete table
   */
  async deleteTable(schema: string, table: string): Promise<void> {
    await apiClient.delete(`/api/v1/data/schemas/${schema}/tables/${table}`)
  }

  /**
   * Optimize table
   */
  async optimizeTable(
    schema: string,
    table: string,
    options?: {
      z_order_by?: string[]
      vacuum?: boolean
    }
  ): Promise<{
    success: boolean
    message: string
    duration_ms: number
  }> {
    const response = await apiClient.post(
      `/api/v1/data/schemas/${schema}/tables/${table}/optimize`,
      options
    )
    return response.data
  }

  /**
   * Bulk insert data
   */
  async bulkInsert(
    schema: string,
    table: string,
    data: Record<string, any>[]
  ): Promise<{
    success: boolean
    rows_inserted: number
  }> {
    const response = await apiClient.post(
      `/api/v1/data/schemas/${schema}/tables/${table}/bulk-insert`,
      { data }
    )
    return response.data
  }
}

// Export singleton instance
export const dataService = new DataService()
export default dataService
