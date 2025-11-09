/**
 * Agents Service
 *
 * Handles all agent task management operations
 */

import apiClient from '@/lib/api'

export interface TaskCreate {
  description: string
  priority?: 'low' | 'normal' | 'high' | 'critical'
  metadata?: Record<string, any>
}

export interface Task {
  task_id: string
  description: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  priority: 'low' | 'normal' | 'high' | 'critical'
  created_at: string
  started_at?: string
  completed_at?: string
  result?: Record<string, any>
  error?: string
  created_by_user_id: number
  metadata?: Record<string, any>
}

export interface TaskListResponse {
  tasks: Task[]
  total: number
  limit: number
  offset: number
}

export interface AgentStats {
  total_tasks: number
  tasks_by_status: Record<string, number>
  tasks_by_priority: Record<string, number>
  avg_completion_time_seconds?: number
  success_rate?: number
}

class AgentsService {
  /**
   * Submit a new task to the agent queue
   */
  async createTask(taskData: TaskCreate): Promise<Task> {
    const response = await apiClient.post<Task>('/api/v1/agents', taskData)
    return response.data
  }

  /**
   * List all tasks with optional filtering
   */
  async listTasks(params?: {
    status?: Task['status']
    priority?: Task['priority']
    limit?: number
    offset?: number
  }): Promise<TaskListResponse> {
    const response = await apiClient.get<TaskListResponse>('/api/v1/agents', { params })
    return response.data
  }

  /**
   * Get a specific task by ID
   */
  async getTask(taskId: string): Promise<Task> {
    const response = await apiClient.get<Task>(`/api/v1/agents/${taskId}`)
    return response.data
  }

  /**
   * Cancel a running or pending task
   */
  async cancelTask(taskId: string): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(`/api/v1/agents/${taskId}`)
    return response.data
  }

  /**
   * Retry a failed task
   */
  async retryTask(taskId: string): Promise<Task> {
    const response = await apiClient.post<Task>(`/api/v1/agents/${taskId}/retry`)
    return response.data
  }

  /**
   * Get agent system statistics (admin only)
   */
  async getStats(): Promise<AgentStats> {
    const response = await apiClient.get<AgentStats>('/api/v1/agents/stats')
    return response.data
  }

  /**
   * Poll for task completion
   * Useful for waiting on task results
   */
  async waitForCompletion(
    taskId: string,
    options?: {
      pollInterval?: number // milliseconds
      timeout?: number // milliseconds
    }
  ): Promise<Task> {
    const pollInterval = options?.pollInterval || 2000
    const timeout = options?.timeout || 60000
    const startTime = Date.now()

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const task = await this.getTask(taskId)

          // Check if task is in terminal state
          if (task.status === 'completed') {
            resolve(task)
            return
          }

          if (task.status === 'failed') {
            reject(new Error(task.error || 'Task failed'))
            return
          }

          if (task.status === 'cancelled') {
            reject(new Error('Task was cancelled'))
            return
          }

          // Check timeout
          if (Date.now() - startTime > timeout) {
            reject(new Error('Task polling timeout'))
            return
          }

          // Continue polling
          setTimeout(poll, pollInterval)
        } catch (error) {
          reject(error)
        }
      }

      poll()
    })
  }
}

export const agentsService = new AgentsService()
