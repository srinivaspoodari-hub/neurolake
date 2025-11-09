/**
 * React Query Hooks for Pipelines Service
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  pipelinesService,
  Pipeline,
  PipelineCreate,
  PipelineUpdate
} from '@/services/pipelinesService'

// Query keys
export const pipelinesKeys = {
  all: ['pipelines'] as const,
  lists: () => [...pipelinesKeys.all, 'list'] as const,
  list: (filters?: any) => [...pipelinesKeys.lists(), filters] as const,
  details: () => [...pipelinesKeys.all, 'detail'] as const,
  detail: (id: number) => [...pipelinesKeys.details(), id] as const,
  executions: (id: number) => [...pipelinesKeys.all, 'executions', id] as const,
}

/**
 * Hook to fetch all pipelines
 */
export function usePipelines(params?: {
  is_active?: boolean
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: pipelinesKeys.list(params),
    queryFn: () => pipelinesService.listPipelines(params),
  })
}

/**
 * Hook to fetch a specific pipeline
 */
export function usePipeline(pipelineId: number) {
  return useQuery({
    queryKey: pipelinesKeys.detail(pipelineId),
    queryFn: () => pipelinesService.getPipeline(pipelineId),
    enabled: !!pipelineId,
  })
}

/**
 * Hook to fetch pipeline execution history
 */
export function usePipelineExecutions(pipelineId: number, params?: {
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: [...pipelinesKeys.executions(pipelineId), params],
    queryFn: () => pipelinesService.getExecutionHistory(pipelineId, params),
    enabled: !!pipelineId,
    refetchInterval: 5000, // Refresh every 5 seconds
  })
}

/**
 * Hook to create a pipeline
 */
export function useCreatePipeline() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (pipeline: PipelineCreate) =>
      pipelinesService.createPipeline(pipeline),
    onSuccess: (newPipeline) => {
      queryClient.invalidateQueries({ queryKey: pipelinesKeys.lists() })
      queryClient.setQueryData(pipelinesKeys.detail(newPipeline.id), newPipeline)
    },
  })
}

/**
 * Hook to update a pipeline
 */
export function useUpdatePipeline() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, updates }: { id: number; updates: PipelineUpdate }) =>
      pipelinesService.updatePipeline(id, updates),
    onSuccess: (updatedPipeline) => {
      queryClient.setQueryData(pipelinesKeys.detail(updatedPipeline.id), updatedPipeline)
      queryClient.invalidateQueries({ queryKey: pipelinesKeys.lists() })
    },
  })
}

/**
 * Hook to delete a pipeline
 */
export function useDeletePipeline() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (pipelineId: number) =>
      pipelinesService.deletePipeline(pipelineId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: pipelinesKeys.lists() })
    },
  })
}

/**
 * Hook to execute a pipeline
 */
export function useExecutePipeline() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (pipelineId: number) =>
      pipelinesService.executePipeline(pipelineId),
    onSuccess: (_, pipelineId) => {
      queryClient.invalidateQueries({ queryKey: pipelinesKeys.executions(pipelineId) })
      queryClient.invalidateQueries({ queryKey: pipelinesKeys.detail(pipelineId) })
    },
  })
}

/**
 * Hook to get active pipelines
 */
export function useActivePipelines() {
  return usePipelines({ is_active: true })
}
