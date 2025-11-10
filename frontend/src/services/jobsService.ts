/**
 * Jobs Service
 *
 * Comprehensive data ingestion and job management API:
 * - Multi-source ingestion (S3, FTP, HTTP, Google Drive, local, Kafka, databases)
 * - Batch and streaming processing
 * - Compute configuration (autoscaling, Photon, optimizations)
 * - Live job monitoring and logs
 * - User-specific scheduling
 */

import apiClient from '@/lib/api'

// ============================================================================
// TYPES
// ============================================================================

export interface SourceConfig {
  source_type: 's3' | 'ftp' | 'http' | 'google_drive' | 'local' | 'kafka' | 'database'
  connection_params: Record<string, any>
  file_pattern?: string
  schema_inference: boolean
}

export interface ComputeConfig {
  cluster_mode: 'single' | 'multi-node' | 'serverless'
  instance_type: 'standard' | 'memory_optimized' | 'compute_optimized'
  min_workers: number
  max_workers: number
  autoscaling_enabled: boolean
  photon_enabled: boolean
  adaptive_query_execution: boolean
  dynamic_partition_pruning: boolean
  cbo_enabled: boolean
  spark_conf?: Record<string, string>
}

export interface ProcessingConfig {
  mode: 'batch' | 'streaming'
  format: 'csv' | 'json' | 'parquet' | 'avro' | 'delta' | 'auto'
  batch_size?: number
  checkpoint_enabled: boolean
  watermark?: string
  trigger?: string
}

export interface ScheduleConfig {
  enabled: boolean
  cron_expression?: string
  timezone: string
  start_date?: string
  end_date?: string
  max_retries: number
  retry_delay_seconds: number
}

export interface JobCreate {
  job_name: string
  description?: string
  source_config: SourceConfig
  destination_schema: string
  destination_table: string
  processing_config: ProcessingConfig
  compute_config: ComputeConfig
  schedule_config?: ScheduleConfig
  tags?: string[]
  role_access?: string[]
}

export interface Job {
  job_id: string
  job_name: string
  description?: string
  status: 'created' | 'running' | 'completed' | 'failed' | 'cancelled'
  created_by: string
  created_at: string
  updated_at: string
  source_config: SourceConfig
  destination: string
  processing_config: ProcessingConfig
  compute_config: ComputeConfig
  schedule_config?: ScheduleConfig
  last_run?: string
  next_run?: string
  runs_count: number
  success_count: number
  failure_count: number
  tags: string[]
}

export interface JobExecution {
  execution_id: string
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  started_at: string
  completed_at?: string
  duration_seconds?: number
  records_processed: number
  records_failed: number
  bytes_processed: number
  error_message?: string
  metrics: Record<string, any>
}

export interface LogEntry {
  timestamp: string
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG'
  message: string
  metadata?: Record<string, any>
}

export interface JobMetrics {
  job_id: string
  status: string
  metrics: {
    records_processed: number
    records_failed: number
    throughput_rps: number
    bytes_processed: number
    active_workers: number
    cpu_utilization: number
    memory_utilization: number
    photon_acceleration: boolean
    cache_hit_rate: number
    shuffle_bytes: number
  }
  timestamp: string
}

export interface ComputePreset {
  name: string
  description: string
  config: ComputeConfig
}

export interface SourceType {
  type: string
  name: string
  params: string[]
  formats: string[]
  batch: boolean
  streaming: boolean
}

// ============================================================================
// SERVICE
// ============================================================================

class JobsService {
  private readonly baseUrl = '/api/v1/jobs'

  // ========== JOB MANAGEMENT ==========

  async createJob(data: JobCreate): Promise<Job> {
    const response = await apiClient.post(this.baseUrl, data)
    return response.data
  }

  async listJobs(params?: {
    status?: string
    tag?: string
    limit?: number
    offset?: number
  }): Promise<Job[]> {
    const response = await apiClient.get(this.baseUrl, { params })
    return response.data
  }

  async getJob(jobId: string): Promise<Job> {
    const response = await apiClient.get(`${this.baseUrl}/${jobId}`)
    return response.data
  }

  async deleteJob(jobId: string): Promise<{ status: string; message: string }> {
    const response = await apiClient.delete(`${this.baseUrl}/${jobId}`)
    return response.data
  }

  // ========== JOB EXECUTION ==========

  async startJob(jobId: string): Promise<JobExecution> {
    const response = await apiClient.post(`${this.baseUrl}/${jobId}/start`)
    return response.data
  }

  async stopJob(jobId: string): Promise<{ status: string; message: string }> {
    const response = await apiClient.post(`${this.baseUrl}/${jobId}/stop`)
    return response.data
  }

  async getJobExecutions(
    jobId: string,
    limit: number = 50
  ): Promise<{ job_id: string; executions: JobExecution[]; total_count: number }> {
    const response = await apiClient.get(`${this.baseUrl}/${jobId}/executions`, {
      params: { limit }
    })
    return response.data
  }

  // ========== LOGS & MONITORING ==========

  async getJobLogs(
    jobId: string,
    params?: {
      level?: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG'
      limit?: number
    }
  ): Promise<LogEntry[]> {
    const response = await apiClient.get(`${this.baseUrl}/${jobId}/logs`, { params })
    return response.data
  }

  async getJobMetrics(jobId: string): Promise<JobMetrics> {
    const response = await apiClient.get(`${this.baseUrl}/${jobId}/metrics`)
    return response.data
  }

  // ========== COMPUTE CONFIGURATION ==========

  async updateComputeConfig(jobId: string, config: ComputeConfig): Promise<Job> {
    const response = await apiClient.patch(`${this.baseUrl}/${jobId}/compute`, config)
    return response.data
  }

  async getComputePresets(): Promise<{ presets: ComputePreset[] }> {
    const response = await apiClient.get(`${this.baseUrl}/compute/presets`)
    return response.data
  }

  // ========== DATA SOURCES ==========

  async listAvailableSources(): Promise<{ sources: SourceType[] }> {
    const response = await apiClient.get(`${this.baseUrl}/sources/available`)
    return response.data
  }

  async testSourceConnection(
    sourceConfig: SourceConfig
  ): Promise<{
    status: string
    message: string
    details: Record<string, any>
  }> {
    const response = await apiClient.post(`${this.baseUrl}/sources/test`, sourceConfig)
    return response.data
  }
}

export const jobsService = new JobsService()
export default jobsService
