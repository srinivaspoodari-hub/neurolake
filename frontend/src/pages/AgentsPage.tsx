/**
 * Agents Dashboard Page
 *
 * View and manage AI agent tasks
 */

import React, { useState } from 'react'
import {
  useTasks,
  useAgentStats,
  useCreateTask,
  useCancelTask,
  useRetryTask
} from '@/hooks/useAgents'
import { Task, TaskCreate } from '@/services/agentsService'
import { formatDistanceToNow } from 'date-fns'

export default function AgentsPage() {
  const [selectedStatus, setSelectedStatus] = useState<Task['status'] | 'all'>('all')
  const [showCreateModal, setShowCreateModal] = useState(false)

  // Fetch tasks and stats
  const { data: tasksData, isLoading: tasksLoading } = useTasks(
    selectedStatus === 'all' ? {} : { status: selectedStatus }
  )
  const { data: stats, isLoading: statsLoading } = useAgentStats()

  // Mutations
  const createTask = useCreateTask()
  const cancelTask = useCancelTask()
  const retryTask = useRetryTask()

  const handleCreateTask = async (taskData: TaskCreate) => {
    try {
      await createTask.mutateAsync(taskData)
      setShowCreateModal(false)
    } catch (error) {
      console.error('Failed to create task:', error)
    }
  }

  const handleCancelTask = async (taskId: string) => {
    if (window.confirm('Are you sure you want to cancel this task?')) {
      try {
        await cancelTask.mutateAsync(taskId)
      } catch (error) {
        console.error('Failed to cancel task:', error)
      }
    }
  }

  const handleRetryTask = async (taskId: string) => {
    try {
      await retryTask.mutateAsync(taskId)
    } catch (error) {
      console.error('Failed to retry task:', error)
    }
  }

  const getStatusColor = (status: Task['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'running':
        return 'bg-blue-100 text-blue-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'cancelled':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getPriorityColor = (priority: Task['priority']) => {
    switch (priority) {
      case 'critical':
        return 'text-red-600 font-semibold'
      case 'high':
        return 'text-orange-600'
      case 'normal':
        return 'text-blue-600'
      case 'low':
        return 'text-gray-600'
      default:
        return 'text-gray-600'
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">AI Agents</h1>
        <p className="text-gray-600 mt-2">Manage and monitor agent tasks</p>
      </div>

      {/* Stats Cards */}
      {!statsLoading && stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Total Tasks</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">
              {stats.total_tasks}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Running</div>
            <div className="text-3xl font-bold text-blue-600 mt-2">
              {stats.tasks_by_status?.running || 0}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Completed</div>
            <div className="text-3xl font-bold text-green-600 mt-2">
              {stats.tasks_by_status?.completed || 0}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Success Rate</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">
              {stats.success_rate ? `${(stats.success_rate * 100).toFixed(1)}%` : 'N/A'}
            </div>
          </div>
        </div>
      )}

      {/* Actions Bar */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex items-center justify-between">
          {/* Status Filter */}
          <div className="flex gap-2">
            {['all', 'pending', 'running', 'completed', 'failed', 'cancelled'].map((status) => (
              <button
                key={status}
                onClick={() => setSelectedStatus(status as any)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  selectedStatus === status
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
                {status !== 'all' && stats?.tasks_by_status?.[status] && (
                  <span className="ml-2 text-xs opacity-75">
                    ({stats.tasks_by_status[status]})
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Create Task Button */}
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            + New Task
          </button>
        </div>
      </div>

      {/* Tasks List */}
      <div className="bg-white rounded-lg shadow">
        {tasksLoading ? (
          <div className="p-8 text-center text-gray-500">Loading tasks...</div>
        ) : !tasksData?.tasks || tasksData.tasks.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No tasks found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Task ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Priority
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {tasksData.tasks.map((task) => (
                  <tr key={task.task_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-mono text-gray-900">
                      {task.task_id.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {task.description}
                      {task.error && (
                        <div className="text-red-600 text-xs mt-1">
                          Error: {task.error}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(
                          task.status
                        )}`}
                      >
                        {task.status}
                      </span>
                    </td>
                    <td className={`px-6 py-4 text-sm ${getPriorityColor(task.priority)}`}>
                      {task.priority}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <div className="flex gap-2">
                        {(task.status === 'pending' || task.status === 'running') && (
                          <button
                            onClick={() => handleCancelTask(task.task_id)}
                            className="text-red-600 hover:text-red-900"
                            disabled={cancelTask.isPending}
                          >
                            Cancel
                          </button>
                        )}
                        {task.status === 'failed' && (
                          <button
                            onClick={() => handleRetryTask(task.task_id)}
                            className="text-blue-600 hover:text-blue-900"
                            disabled={retryTask.isPending}
                          >
                            Retry
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Info */}
        {tasksData && tasksData.total > 0 && (
          <div className="px-6 py-4 border-t border-gray-200 text-sm text-gray-500">
            Showing {tasksData.tasks.length} of {tasksData.total} tasks
          </div>
        )}
      </div>

      {/* Create Task Modal */}
      {showCreateModal && (
        <CreateTaskModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateTask}
          isLoading={createTask.isPending}
        />
      )}
    </div>
  )
}

// Create Task Modal Component
interface CreateTaskModalProps {
  onClose: () => void
  onCreate: (task: TaskCreate) => void
  isLoading: boolean
}

function CreateTaskModal({ onClose, onCreate, isLoading }: CreateTaskModalProps) {
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<Task['priority']>('normal')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (description.trim()) {
      onCreate({ description: description.trim(), priority })
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Create New Task</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={4}
              placeholder="Describe the task..."
              required
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Priority
            </label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as Task['priority'])}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              disabled={isLoading || !description.trim()}
            >
              {isLoading ? 'Creating...' : 'Create Task'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
