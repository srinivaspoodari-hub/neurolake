/**
 * Unified Dashboard - All NeuroLake Features in One Place
 *
 * Single dashboard with tabbed interface for all platform features
 */

import React, { useState } from 'react'
import { useDashboardStats, useRecentQueries } from '@/hooks/useDashboard'
import { useTasks, useAgentStats } from '@/hooks/useAgents'
import { useComplianceStats, useDetectPII, useMaskPII, usePolicies } from '@/hooks/useCompliance'
import { useAuditLogs, useAuditStats } from '@/hooks/useAudit'
import { usePipelines } from '@/hooks/usePipelines'
import { queryService } from '@/services/queryService'
import { agentsService } from '@/services/agentsService'
import { formatDistanceToNow } from 'date-fns'
import CatalogBrowser from '@/components/CatalogBrowser'
import JobsManagement from '@/components/JobsManagement'

type TabType = 'overview' | 'query' | 'agents' | 'compliance' | 'audit' | 'data' | 'pipelines' | 'jobs'

export default function UnifiedDashboard() {
  const [activeTab, setActiveTab] = useState<TabType>('overview')

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <h1 className="text-3xl font-bold text-gray-900">NeuroLake Data Platform</h1>
          <p className="text-gray-600 mt-1">Unified dashboard for all your data operations</p>
        </div>
      </div>

      {/* Statistics Overview - Always Visible */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        <GlobalStatistics />
      </div>

      {/* Main Content Area */}
      <div className="max-w-7xl mx-auto px-6 pb-6">
        <div className="bg-white rounded-lg shadow">
          {/* Tab Navigation */}
          <div className="border-b border-gray-200">
            <nav className="flex overflow-x-auto">
              {[
                { id: 'overview', label: '📊 Overview', icon: '📊' },
                { id: 'query', label: '🔍 Query', icon: '🔍' },
                { id: 'jobs', label: '⚡ Jobs & Ingestion', icon: '⚡' },
                { id: 'agents', label: '🤖 AI Agents', icon: '🤖' },
                { id: 'compliance', label: '🔒 Compliance', icon: '🔒' },
                { id: 'audit', label: '📝 Audit', icon: '📝' },
                { id: 'data', label: '📁 NUIC Catalog', icon: '📁' },
                { id: 'pipelines', label: '⚙️ Pipelines', icon: '⚙️' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as TabType)}
                  className={`px-6 py-4 text-sm font-medium border-b-2 whitespace-nowrap ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {activeTab === 'overview' && <OverviewTab />}
            {activeTab === 'query' && <QueryTab />}
            {activeTab === 'jobs' && <JobsManagement />}
            {activeTab === 'agents' && <AgentsTab />}
            {activeTab === 'compliance' && <ComplianceTab />}
            {activeTab === 'audit' && <AuditTab />}
            {activeTab === 'data' && <CatalogBrowser />}
            {activeTab === 'pipelines' && <PipelinesTab />}
          </div>
        </div>
      </div>
    </div>
  )
}

// Global Statistics Component
function GlobalStatistics() {
  const { data: dashStats } = useDashboardStats()
  const { data: agentStats } = useAgentStats()
  const { data: complianceStats } = useComplianceStats()
  const { data: auditStats } = useAuditStats()

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
      {/* Query Stats */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-xs text-gray-500">Total Queries</div>
        <div className="text-2xl font-bold text-blue-600">{dashStats?.totalQueries || 0}</div>
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-xs text-gray-500">Avg Time</div>
        <div className="text-2xl font-bold text-gray-900">{dashStats?.avgQueryTime || 'N/A'}</div>
      </div>

      {/* Agent Stats */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-xs text-gray-500">Active Tasks</div>
        <div className="text-2xl font-bold text-green-600">
          {(agentStats?.tasks_by_status?.running || 0) + (agentStats?.tasks_by_status?.pending || 0)}
        </div>
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-xs text-gray-500">Success Rate</div>
        <div className="text-2xl font-bold text-gray-900">
          {agentStats?.success_rate ? `${(agentStats.success_rate * 100).toFixed(0)}%` : 'N/A'}
        </div>
      </div>

      {/* Compliance Stats */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-xs text-gray-500">Policies</div>
        <div className="text-2xl font-bold text-purple-600">{complianceStats?.enabled_policies || 0}</div>
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-xs text-gray-500">Violations</div>
        <div className="text-2xl font-bold text-red-600">{complianceStats?.total_violations || 0}</div>
      </div>

      {/* Audit Stats */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-xs text-gray-500">Events Today</div>
        <div className="text-2xl font-bold text-gray-900">{auditStats?.total_events || 0}</div>
      </div>
      <div className="bg-white rounded-lg shadow p-4">
        <div className="text-xs text-gray-500">Failed Actions</div>
        <div className="text-2xl font-bold text-orange-600">{auditStats?.by_status?.failure || 0}</div>
      </div>
    </div>
  )
}

// Overview Tab - Quick Actions & Recent Activity
function OverviewTab() {
  const { data: recentQueries } = useRecentQueries(5)
  const { data: tasks } = useTasks({ limit: 5 })

  return (
    <div className="space-y-6">
      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-bold mb-4">🚀 Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <QuickActionCard
            title="Execute Query"
            description="Run SQL queries on your data"
            icon="🔍"
            color="blue"
          />
          <QuickActionCard
            title="Upload Data"
            description="Upload CSV, Parquet, or JSON files"
            icon="📤"
            color="green"
          />
          <QuickActionCard
            title="Detect PII"
            description="Scan text for sensitive information"
            icon="🔒"
            color="purple"
          />
        </div>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recent Queries */}
        <div>
          <h3 className="text-lg font-bold mb-3">Recent Queries</h3>
          <div className="space-y-2">
            {recentQueries?.map((query: any, idx: number) => (
              <div key={idx} className="bg-gray-50 rounded p-3">
                <div className="font-mono text-xs text-gray-600 truncate">{query.sql}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {query.executionTime}ms • {new Date(query.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}
            {(!recentQueries || recentQueries.length === 0) && (
              <div className="text-sm text-gray-500">No recent queries</div>
            )}
          </div>
        </div>

        {/* Recent Tasks */}
        <div>
          <h3 className="text-lg font-bold mb-3">Recent AI Tasks</h3>
          <div className="space-y-2">
            {tasks?.tasks?.slice(0, 5).map((task) => (
              <div key={task.task_id} className="bg-gray-50 rounded p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{task.description}</span>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    task.status === 'completed' ? 'bg-green-100 text-green-800' :
                    task.status === 'running' ? 'bg-blue-100 text-blue-800' :
                    task.status === 'failed' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {task.status}
                  </span>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                </div>
              </div>
            ))}
            {(!tasks?.tasks || tasks.tasks.length === 0) && (
              <div className="text-sm text-gray-500">No recent tasks</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function QuickActionCard({ title, description, icon, color }: any) {
  const colors: any = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    purple: 'bg-purple-50 border-purple-200 text-purple-700',
  }

  return (
    <div className={`border-2 rounded-lg p-4 ${colors[color]} hover:shadow-md transition-shadow cursor-pointer`}>
      <div className="text-3xl mb-2">{icon}</div>
      <h3 className="font-bold text-lg">{title}</h3>
      <p className="text-sm opacity-80">{description}</p>
    </div>
  )
}

// Query Tab
function QueryTab() {
  const [sql, setSql] = useState('SELECT * FROM sales_data LIMIT 10;')
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleExecute = async () => {
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await queryService.executeQuery({ sql })
      setResult(response)
    } catch (err: any) {
      setError(err.message || 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">SQL Query</label>
        <textarea
          value={sql}
          onChange={(e) => setSql(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
          rows={8}
          placeholder="Enter your SQL query here..."
        />
      </div>

      <button
        onClick={handleExecute}
        disabled={loading || !sql.trim()}
        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Executing...' : '▶ Execute Query'}
      </button>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="text-red-800 font-medium">Error</div>
          <div className="text-red-600 text-sm mt-1">{error}</div>
        </div>
      )}

      {result && (
        <div className="border rounded-lg">
          <div className="bg-gray-50 px-4 py-2 border-b">
            <div className="text-sm text-gray-600">
              ✓ Query executed successfully • {result.rowCount || 0} rows • {result.executionTime || 0}ms
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  {result.columns?.map((col: string) => (
                    <th key={col} className="px-4 py-2 text-left font-medium text-gray-700">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {result.data?.slice(0, 50).map((row: any, idx: number) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    {result.columns?.map((col: string) => (
                      <td key={col} className="px-4 py-2 text-gray-900">
                        {row[col] !== null ? String(row[col]) : <span className="text-gray-400">null</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// Agents Tab - Simplified from AgentsPage
function AgentsTab() {
  const { data: tasks } = useTasks({ limit: 20 })
  const [showCreate, setShowCreate] = useState(false)
  const [taskDesc, setTaskDesc] = useState('')
  const [priority, setPriority] = useState<'normal' | 'high'>('normal')

  const handleCreate = async () => {
    try {
      await agentsService.createTask({ description: taskDesc, priority })
      setTaskDesc('')
      setShowCreate(false)
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-bold">AI Agent Tasks</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + New Task
        </button>
      </div>

      {showCreate && (
        <div className="bg-gray-50 border rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2">
              <input
                type="text"
                value={taskDesc}
                onChange={(e) => setTaskDesc(e.target.value)}
                placeholder="Task description..."
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div className="flex gap-2">
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as any)}
                className="flex-1 px-3 py-2 border rounded-lg"
              >
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              <button
                onClick={handleCreate}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">Description</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Priority</th>
              <th className="px-4 py-3 text-left">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {tasks?.tasks?.map((task) => (
              <tr key={task.task_id} className="hover:bg-gray-50">
                <td className="px-4 py-3">{task.description}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    task.status === 'completed' ? 'bg-green-100 text-green-800' :
                    task.status === 'running' ? 'bg-blue-100 text-blue-800' :
                    task.status === 'failed' ? 'bg-red-100 text-red-800' :
                    'bg-yellow-100 text-yellow-800'
                  }`}>
                    {task.status}
                  </span>
                </td>
                <td className="px-4 py-3">{task.priority}</td>
                <td className="px-4 py-3 text-gray-500">
                  {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Compliance Tab - Simplified
function ComplianceTab() {
  const [text, setText] = useState('')
  const detectPII = useDetectPII()
  const maskPII = useMaskPII()
  const [masked, setMasked] = useState('')

  const handleDetect = async () => {
    await detectPII.mutateAsync({ text })
  }

  const handleMask = async () => {
    const result = await maskPII.mutateAsync({ text, anonymize: true })
    setMasked(result.masked_text)
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold">PII Detection & Masking</h2>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="w-full px-3 py-2 border rounded-lg"
        rows={4}
        placeholder="Paste text to check for PII... (e.g., 'Contact john@example.com or call 555-1234')"
      />

      <div className="flex gap-2">
        <button
          onClick={handleDetect}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Detect PII
        </button>
        <button
          onClick={handleMask}
          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
        >
          Mask PII
        </button>
      </div>

      {detectPII.data && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="font-medium text-blue-900 mb-2">
            {detectPII.data.found_pii
              ? `Found ${detectPII.data.pii_count} PII entities`
              : '✓ No PII detected'}
          </div>
          {detectPII.data.results?.map((item, idx) => (
            <div key={idx} className="text-sm text-blue-800 mt-1">
              • {item.entity_type}: "{item.text}" ({(item.confidence * 100).toFixed(0)}%)
            </div>
          ))}
        </div>
      )}

      {masked && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <div className="font-medium text-purple-900 mb-2">Masked Text:</div>
          <pre className="text-sm text-purple-800 whitespace-pre-wrap">{masked}</pre>
        </div>
      )}
    </div>
  )
}

// Audit Tab - Simplified
function AuditTab() {
  const { data: logs } = useAuditLogs({ limit: 20 })

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold">Recent Activity</h2>

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">Time</th>
              <th className="px-4 py-3 text-left">User</th>
              <th className="px-4 py-3 text-left">Action</th>
              <th className="px-4 py-3 text-left">Resource</th>
              <th className="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {logs?.logs?.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500">
                  {formatDistanceToNow(new Date(log.timestamp), { addSuffix: true })}
                </td>
                <td className="px-4 py-3">{log.username || 'System'}</td>
                <td className="px-4 py-3">
                  <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">
                    {log.action}
                  </span>
                </td>
                <td className="px-4 py-3">{log.resource_type}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    log.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {log.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Data Tab replaced with CatalogBrowser component (imported at top)

// Pipelines Tab
function PipelinesTab() {
  const { data: pipelines } = usePipelines()

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-bold">Data Pipelines</h2>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + New Pipeline
        </button>
      </div>

      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Schedule</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Last Run</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {pipelines?.pipelines?.map((pipeline) => (
              <tr key={pipeline.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{pipeline.name}</td>
                <td className="px-4 py-3 text-gray-600">{pipeline.schedule || 'Manual'}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    pipeline.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {pipeline.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">
                  {pipeline.last_run
                    ? formatDistanceToNow(new Date(pipeline.last_run), { addSuffix: true })
                    : 'Never'}
                </td>
              </tr>
            ))}
            {(!pipelines?.pipelines || pipelines.pipelines.length === 0) && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                  No pipelines created yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
