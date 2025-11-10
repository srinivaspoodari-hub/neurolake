/**
 * Jobs Management Hooks
 *
 * React Query hooks for data ingestion and job management:
 * - Job CRUD operations
 * - Execution control
 * - Live monitoring
 * - Compute configuration
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult } from '@tanstack/react-query'
import { jobsService } from '@/services/jobsService'
import type {
  Job,
  JobCreate,
  JobExecution,
  LogEntry,
  JobMetrics,
  ComputeConfig,
  ComputePreset,
  SourceType,
  SourceConfig
} from '@/services/jobsService'

// ============================================================================
// QUERY KEYS
// ============================================================================

export const jobsKeys = {
  all: ['jobs'] as const,
  lists: () => [...jobsKeys.all, 'list'] as const,
  list: (filters?: Record<string, any>) => [...jobsKeys.lists(), filters] as const,
  details: () => [...jobsKeys.all, 'detail'] as const,
  detail: (id: string) => [...jobsKeys.details(), id] as const,
  executions: (id: string) => [...jobsKeys.detail(id), 'executions'] as const,
  logs: (id: string, level?: string) => [...jobsKeys.detail(id), 'logs', level] as const,
  metrics: (id: string) => [...jobsKeys.detail(id), 'metrics'] as const,
  presets: () => [...jobsKeys.all, 'presets'] as const,
  sources: () => [...jobsKeys.all, 'sources'] as const,
}

// ============================================================================
// JOB MANAGEMENT HOOKS
// ============================================================================

export function useJobs(filters?: { status?: string; tag?: string; limit?: number; offset?: number }) {
  return useQuery({
    queryKey: jobsKeys.list(filters),
    queryFn: () => jobsService.listJobs(filters),
    staleTime: 30000, // 30 seconds
  })
}

export function useJob(jobId: string) {
  return useQuery({
    queryKey: jobsKeys.detail(jobId),
    queryFn: () => jobsService.getJob(jobId),
    enabled: !!jobId,
    staleTime: 10000, // 10 seconds
  })
}

export function useCreateJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: JobCreate) => jobsService.createJob(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: jobsKeys.lists() })
    },
  })
}

export function useDeleteJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: string) => jobsService.deleteJob(jobId),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: jobsKeys.lists() })
      queryClient.removeQueries({ queryKey: jobsKeys.detail(jobId) })
    },
  })
}

// ============================================================================
// JOB EXECUTION HOOKS
// ============================================================================

export function useStartJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: string) => jobsService.startJob(jobId),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: jobsKeys.detail(jobId) })
      queryClient.invalidateQueries({ queryKey: jobsKeys.executions(jobId) })
      queryClient.invalidateQueries({ queryKey: jobsKeys.logs(jobId) })
    },
  })
}

export function useStopJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: string) => jobsService.stopJob(jobId),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: jobsKeys.detail(jobId) })
      queryClient.invalidateQueries({ queryKey: jobsKeys.logs(jobId) })
    },
  })
}

export function useJobExecutions(jobId: string, limit: number = 50) {
  return useQuery({
    queryKey: jobsKeys.executions(jobId),
    queryFn: () => jobsService.getJobExecutions(jobId, limit),
    enabled: !!jobId,
    staleTime: 10000,
  })
}

// ============================================================================
// MONITORING HOOKS
// ============================================================================

export function useJobLogs(
  jobId: string,
  params?: { level?: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG'; limit?: number }
) {
  return useQuery({
    queryKey: jobsKeys.logs(jobId, params?.level),
    queryFn: () => jobsService.getJobLogs(jobId, params),
    enabled: !!jobId,
    refetchInterval: 5000, // Auto-refresh every 5 seconds for live logs
    staleTime: 0, // Always fetch fresh logs
  })
}

export function useJobMetrics(jobId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: jobsKeys.metrics(jobId),
    queryFn: () => jobsService.getJobMetrics(jobId),
    enabled: enabled && !!jobId,
    refetchInterval: 3000, // Auto-refresh every 3 seconds for real-time metrics
    staleTime: 0, // Always fetch fresh metrics
  })
}

// ============================================================================
// COMPUTE CONFIGURATION HOOKS
// ============================================================================

export function useUpdateComputeConfig() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ jobId, config }: { jobId: string; config: ComputeConfig }) =>
      jobsService.updateComputeConfig(jobId, config),
    onSuccess: (_, { jobId }) => {
      queryClient.invalidateQueries({ queryKey: jobsKeys.detail(jobId) })
    },
  })
}

export function useComputePresets() {
  return useQuery({
    queryKey: jobsKeys.presets(),
    queryFn: () => jobsService.getComputePresets(),
    staleTime: Infinity, // Presets don't change frequently
  })
}

// ============================================================================
// DATA SOURCES HOOKS
// ============================================================================

export function useAvailableSources() {
  return useQuery({
    queryKey: jobsKeys.sources(),
    queryFn: () => jobsService.listAvailableSources(),
    staleTime: Infinity, // Available sources don't change
  })
}

export function useTestSourceConnection() {
  return useMutation({
    mutationFn: (sourceConfig: SourceConfig) => jobsService.testSourceConnection(sourceConfig),
  })
}

// ============================================================================
// CONVENIENCE HOOKS
// ============================================================================

/**
 * Get running jobs count
 */
export function useRunningJobsCount() {
  const { data: jobs } = useJobs({ status: 'running' })
  return jobs?.filter((j) => j.status === 'running').length || 0
}

/**
 * Get failed jobs count
 */
export function useFailedJobsCount() {
  const { data: jobs } = useJobs({ status: 'failed' })
  return jobs?.filter((j) => j.status === 'failed').length || 0
}

/**
 * Combined hook for job details, logs, and metrics
 */
export function useJobMonitoring(jobId: string) {
  const job = useJob(jobId)
  const logs = useJobLogs(jobId)
  const metrics = useJobMetrics(jobId, job.data?.status === 'running')
  const executions = useJobExecutions(jobId)

  return {
    job,
    logs,
    metrics,
    executions,
    isLoading: job.isLoading || logs.isLoading,
    error: job.error || logs.error || metrics.error,
  }
}
