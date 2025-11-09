/**
 * React Query Hooks for Agents Service
 */

import { useQuery, useMutation, useQueryClient, UseQueryOptions } from '@tanstack/react-query'
import { agentsService, Task, TaskCreate, AgentStats } from '@/services/agentsService'

// Query keys
export const agentsKeys = {
  all: ['agents'] as const,
  lists: () => [...agentsKeys.all, 'list'] as const,
  list: (filters?: any) => [...agentsKeys.lists(), filters] as const,
  details: () => [...agentsKeys.all, 'detail'] as const,
  detail: (id: string) => [...agentsKeys.details(), id] as const,
  stats: () => [...agentsKeys.all, 'stats'] as const,
}

/**
 * Hook to fetch all tasks
 */
export function useTasks(params?: {
  status?: Task['status']
  priority?: Task['priority']
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: agentsKeys.list(params),
    queryFn: () => agentsService.listTasks(params),
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  })
}

/**
 * Hook to fetch a specific task
 */
export function useTask(taskId: string, options?: UseQueryOptions<Task>) {
  return useQuery({
    queryKey: agentsKeys.detail(taskId),
    queryFn: () => agentsService.getTask(taskId),
    enabled: !!taskId,
    refetchInterval: (data) => {
      // Auto-refresh if task is running or pending
      if (data?.status === 'running' || data?.status === 'pending') {
        return 2000
      }
      return false
    },
    ...options,
  })
}

/**
 * Hook to fetch agent statistics
 */
export function useAgentStats() {
  return useQuery({
    queryKey: agentsKeys.stats(),
    queryFn: () => agentsService.getStats(),
    refetchInterval: 10000, // Refresh every 10 seconds
  })
}

/**
 * Hook to create a new task
 */
export function useCreateTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (taskData: TaskCreate) => agentsService.createTask(taskData),
    onSuccess: (newTask) => {
      // Invalidate task lists to show new task
      queryClient.invalidateQueries({ queryKey: agentsKeys.lists() })
      // Set the task data in cache
      queryClient.setQueryData(agentsKeys.detail(newTask.task_id), newTask)
    },
  })
}

/**
 * Hook to cancel a task
 */
export function useCancelTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (taskId: string) => agentsService.cancelTask(taskId),
    onSuccess: (_, taskId) => {
      // Invalidate specific task and list
      queryClient.invalidateQueries({ queryKey: agentsKeys.detail(taskId) })
      queryClient.invalidateQueries({ queryKey: agentsKeys.lists() })
    },
  })
}

/**
 * Hook to retry a failed task
 */
export function useRetryTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (taskId: string) => agentsService.retryTask(taskId),
    onSuccess: (newTask, taskId) => {
      // Update task in cache
      queryClient.setQueryData(agentsKeys.detail(taskId), newTask)
      queryClient.invalidateQueries({ queryKey: agentsKeys.lists() })
    },
  })
}

/**
 * Hook to wait for task completion
 */
export function useWaitForTask(taskId: string, options?: {
  enabled?: boolean
  pollInterval?: number
  timeout?: number
}) {
  return useQuery({
    queryKey: [...agentsKeys.detail(taskId), 'wait'],
    queryFn: () => agentsService.waitForCompletion(taskId, {
      pollInterval: options?.pollInterval,
      timeout: options?.timeout,
    }),
    enabled: options?.enabled ?? false,
    retry: false,
  })
}

/**
 * Custom hook to track multiple tasks
 */
export function useTasksWithStatus(status: Task['status']) {
  return useTasks({ status, limit: 100 })
}

/**
 * Custom hook for pending tasks
 */
export function usePendingTasks() {
  return useTasksWithStatus('pending')
}

/**
 * Custom hook for running tasks
 */
export function useRunningTasks() {
  return useTasksWithStatus('running')
}

/**
 * Custom hook for completed tasks
 */
export function useCompletedTasks() {
  return useTasksWithStatus('completed')
}

/**
 * Custom hook for failed tasks
 */
export function useFailedTasks() {
  return useTasksWithStatus('failed')
}
