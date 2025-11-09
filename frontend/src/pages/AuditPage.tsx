/**
 * Audit Logs Dashboard Page
 *
 * View and analyze system audit logs
 */

import React, { useState } from 'react'
import { useAuditLogs, useAuditStats, useRecentActivity } from '@/hooks/useAudit'
import { formatDistanceToNow } from 'date-fns'

export default function AuditPage() {
  const [filters, setFilters] = useState({
    action: '',
    status: '' as '' | 'success' | 'failure',
    resource_type: '',
    limit: 50
  })

  const { data: logsData, isLoading } = useAuditLogs(filters.status ? filters : { limit: filters.limit })
  const { data: stats } = useAuditStats()

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Audit Logs</h1>
        <p className="text-gray-600 mt-2">Monitor system activity and user actions</p>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Total Events</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">{stats.total_events}</div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Success Rate</div>
            <div className="text-3xl font-bold text-green-600 mt-2">
              {stats.by_status?.success && stats.total_events
                ? ((stats.by_status.success / stats.total_events) * 100).toFixed(1) + '%'
                : 'N/A'}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Failed Actions</div>
            <div className="text-3xl font-bold text-red-600 mt-2">
              {stats.by_status?.failure || 0}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm font-medium text-gray-500">Unique Users</div>
            <div className="text-3xl font-bold text-gray-900 mt-2">
              {Object.keys(stats.by_user || {}).length}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="">All</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
            <input
              type="text"
              value={filters.action}
              onChange={(e) => setFilters({ ...filters, action: e.target.value })}
              placeholder="e.g., query_execute"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Resource Type</label>
            <input
              type="text"
              value={filters.resource_type}
              onChange={(e) => setFilters({ ...filters, resource_type: e.target.value })}
              placeholder="e.g., table"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Limit</label>
            <select
              value={filters.limit}
              onChange={(e) => setFilters({ ...filters, limit: Number(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
              <option value="500">500</option>
            </select>
          </div>
        </div>
      </div>

      {/* Logs Table */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading logs...</div>
        ) : !logsData?.logs || logsData.logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No audit logs found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Timestamp
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Action
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Resource
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {logsData.logs.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {log.username || `User ${log.user_id}` || 'System'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div>
                        <div className="font-medium">{log.resource_type}</div>
                        {log.resource_name && (
                          <div className="text-xs text-gray-500">{log.resource_name}</div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          log.status === 'success'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {log.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {log.error_message ? (
                        <span className="text-red-600">{log.error_message}</span>
                      ) : log.changes ? (
                        <span className="text-gray-400">Has changes</span>
                      ) : (
                        '-'
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Info */}
        {logsData && logsData.total > 0 && (
          <div className="px-6 py-4 border-t border-gray-200 text-sm text-gray-500">
            Showing {logsData.logs.length} of {logsData.total} logs
          </div>
        )}
      </div>

      {/* Activity Statistics */}
      {stats && (
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Top Actions */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-bold mb-4">Top Actions</h3>
            <div className="space-y-2">
              {Object.entries(stats.by_action || {})
                .sort(([, a], [, b]) => b - a)
                .slice(0, 5)
                .map(([action, count]) => (
                  <div key={action} className="flex items-center justify-between">
                    <span className="text-sm font-mono">{action}</span>
                    <span className="text-sm font-bold text-gray-900">{count}</span>
                  </div>
                ))}
            </div>
          </div>

          {/* Top Resources */}
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-bold mb-4">Top Resources</h3>
            <div className="space-y-2">
              {Object.entries(stats.by_resource || {})
                .sort(([, a], [, b]) => b - a)
                .slice(0, 5)
                .map(([resource, count]) => (
                  <div key={resource} className="flex items-center justify-between">
                    <span className="text-sm">{resource}</span>
                    <span className="text-sm font-bold text-gray-900">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
