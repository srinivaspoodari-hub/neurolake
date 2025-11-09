/**
 * Pipelines Service
 *
 * Handles pipeline CRUD operations and execution management
 */

import apiClient from '@/lib/api'

export interface PipelineCreate {
  name: string
  description?: string
  schedule?: string
  config: Record<string, any>
  is_active?: boolean
}

export interface PipelineUpdate {
  name?: string
  description?: string
  schedule?: string
  config?: Record<string, any>
  is_active?: boolean
}

export interface Pipeline {
  id: number
  name: string
  description?: string
  schedule?: string
  config: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at?: string
  last_run?: string
  created_by_user_id: number
}

export interface PipelineListResponse {
  pipelines: Pipeline[]
  total: number
}

export interface PipelineExecution {
  id: number
  pipeline_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at?: string
  completed_at?: string
  error?: string
  result?: Record<string, any>
}

class PipelinesService {
  /**
   * List all pipelines
   */
  async listPipelines(params?: {
    is_active?: boolean
    limit?: number
    offset?: number
  }): Promise<PipelineListResponse> {
    const response = await apiClient.get<PipelineListResponse>('/api/v1/pipelines', { params })
    return response.data
  }

  /**
   * Get a specific pipeline by ID
   */
  async getPipeline(pipelineId: number): Promise<Pipeline> {
    const response = await apiClient.get<Pipeline>(`/api/v1/pipelines/${pipelineId}`)
    return response.data
  }

  /**
   * Create a new pipeline
   */
  async createPipeline(pipeline: PipelineCreate): Promise<Pipeline> {
    const response = await apiClient.post<Pipeline>('/api/v1/pipelines', pipeline)
    return response.data
  }

  /**
   * Update a pipeline
   */
  async updatePipeline(pipelineId: number, updates: PipelineUpdate): Promise<Pipeline> {
    const response = await apiClient.put<Pipeline>(`/api/v1/pipelines/${pipelineId}`, updates)
    return response.data
  }

  /**
   * Delete a pipeline
   */
  async deletePipeline(pipelineId: number): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(`/api/v1/pipelines/${pipelineId}`)
    return response.data
  }

  /**
   * Execute a pipeline manually
   */
  async executePipeline(pipelineId: number): Promise<PipelineExecution> {
    const response = await apiClient.post<PipelineExecution>(`/api/v1/pipelines/${pipelineId}/execute`)
    return response.data
  }

  /**
   * Get pipeline execution history
   */
  async getExecutionHistory(pipelineId: number, params?: {
    limit?: number
    offset?: number
  }): Promise<PipelineExecution[]> {
    const response = await apiClient.get<PipelineExecution[]>(
      `/api/v1/pipelines/${pipelineId}/executions`,
      { params }
    )
    return response.data
  }
}

export const pipelinesService = new PipelinesService()
