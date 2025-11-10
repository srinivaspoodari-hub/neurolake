/**
 * Jobs Management Component
 *
 * Comprehensive UI for data ingestion and job management:
 * - Multi-source job creation wizard
 * - Live job monitoring dashboard
 * - Compute configuration panel
 * - Real-time logs viewer
 */

import React, { useState, useEffect } from 'react'
import {
  useJobs,
  useJob,
  useCreateJob,
  useDeleteJob,
  useStartJob,
  useStopJob,
  useJobMonitoring,
  useComputePresets,
  useAvailableSources,
  useUpdateComputeConfig,
  useTestSourceConnection,
} from '@/hooks/useJobs'
import type { JobCreate, SourceConfig, ComputeConfig, ProcessingConfig, ScheduleConfig } from '@/services/jobsService'

export default function JobsManagement() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [showCreateWizard, setShowCreateWizard] = useState(false)
  const [filterStatus, setFilterStatus] = useState<string>('')

  const { data: jobs, isLoading } = useJobs({ status: filterStatus || undefined })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading jobs...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Jobs & Ingestion</h2>
            <p className="text-sm text-gray-600 mt-1">
              Manage data ingestion from multiple sources with batch and streaming processing
            </p>
          </div>
          <button
            onClick={() => setShowCreateWizard(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            + Create Job
          </button>
        </div>

        {/* Filters */}
        <div className="mt-4 flex gap-4">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">All Status</option>
            <option value="created">Created</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>

          {jobs && (
            <div className="flex gap-4 text-sm">
              <span className="px-3 py-2 bg-blue-50 text-blue-700 rounded-lg">
                Total: {jobs.length}
              </span>
              <span className="px-3 py-2 bg-green-50 text-green-700 rounded-lg">
                Running: {jobs.filter((j) => j.status === 'running').length}
              </span>
              <span className="px-3 py-2 bg-red-50 text-red-700 rounded-lg">
                Failed: {jobs.filter((j) => j.status === 'failed').length}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Jobs List */}
        <div className="w-96 border-r bg-gray-50 overflow-y-auto">
          {jobs && jobs.length > 0 ? (
            <div className="divide-y">
              {jobs.map((job) => (
                <JobCard
                  key={job.job_id}
                  job={job}
                  isSelected={selectedJobId === job.job_id}
                  onClick={() => setSelectedJobId(job.job_id)}
                />
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-500">
              <p className="mb-2">No jobs found</p>
              <p className="text-sm">Create your first job to get started</p>
            </div>
          )}
        </div>

        {/* Job Details / Monitoring */}
        <div className="flex-1 overflow-y-auto">
          {selectedJobId ? (
            <JobMonitoringPanel jobId={selectedJobId} />
          ) : (
            <EmptyState />
          )}
        </div>
      </div>

      {/* Create Job Wizard Modal */}
      {showCreateWizard && (
        <CreateJobWizard onClose={() => setShowCreateWizard(false)} />
      )}
    </div>
  )
}

// ============================================================================
// JOB CARD
// ============================================================================

function JobCard({ job, isSelected, onClick }: any) {
  const statusColors = {
    created: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-yellow-100 text-yellow-800',
  }

  return (
    <div
      onClick={onClick}
      className={`p-4 cursor-pointer hover:bg-gray-100 transition-colors ${
        isSelected ? 'bg-blue-50 border-l-4 border-l-blue-600' : ''
      }`}
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-semibold text-gray-900">{job.job_name}</h3>
        <span className={`px-2 py-1 text-xs rounded-full ${statusColors[job.status]}`}>
          {job.status}
        </span>
      </div>
      <p className="text-sm text-gray-600 mb-2">{job.description || 'No description'}</p>
      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span>📁 {job.source_config.source_type}</span>
        <span>⚡ {job.processing_config.mode}</span>
        {job.compute_config.photon_enabled && <span>🚀 Photon</span>}
      </div>
      <div className="mt-2 text-xs text-gray-400">
        Runs: {job.runs_count} | Success: {job.success_count} | Failed: {job.failure_count}
      </div>
    </div>
  )
}

// ============================================================================
// JOB MONITORING PANEL
// ============================================================================

function JobMonitoringPanel({ jobId }: { jobId: string }) {
  const { job, logs, metrics } = useJobMonitoring(jobId)
  const [activeTab, setActiveTab] = useState<'overview' | 'logs' | 'metrics' | 'compute'>('overview')
  const startJob = useStartJob()
  const stopJob = useStopJob()
  const deleteJob = useDeleteJob()

  if (job.isLoading) {
    return <div className="p-8">Loading job details...</div>
  }

  if (!job.data) {
    return <div className="p-8">Job not found</div>
  }

  const jobData = job.data

  return (
    <div className="h-full flex flex-col">
      {/* Job Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{jobData.job_name}</h2>
            <p className="text-sm text-gray-600 mt-1">{jobData.description}</p>
          </div>
          <div className="flex gap-2">
            {jobData.status === 'created' || jobData.status === 'completed' || jobData.status === 'failed' ? (
              <button
                onClick={() => startJob.mutate(jobId)}
                disabled={startJob.isPending}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                ▶ Start Job
              </button>
            ) : null}
            {jobData.status === 'running' && (
              <button
                onClick={() => stopJob.mutate(jobId)}
                disabled={stopJob.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                ⏹ Stop Job
              </button>
            )}
            <button
              onClick={() => {
                if (confirm('Are you sure you want to delete this job?')) {
                  deleteJob.mutate(jobId)
                }
              }}
              disabled={jobData.status === 'running'}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
            >
              🗑 Delete
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 border-b">
          {['overview', 'logs', 'metrics', 'compute'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`px-4 py-2 font-medium capitalize ${
                activeTab === tab
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'overview' && <OverviewTab job={jobData} />}
        {activeTab === 'logs' && <LogsTab logs={logs.data || []} isLoading={logs.isLoading} />}
        {activeTab === 'metrics' && <MetricsTab metrics={metrics.data} isLoading={metrics.isLoading} />}
        {activeTab === 'compute' && <ComputeTab job={jobData} jobId={jobId} />}
      </div>
    </div>
  )
}

// ============================================================================
// OVERVIEW TAB
// ============================================================================

function OverviewTab({ job }: any) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-6">
        {/* Source Configuration */}
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-3">Source Configuration</h3>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-gray-600">Source Type</dt>
              <dd className="font-medium">{job.source_config.source_type}</dd>
            </div>
            <div>
              <dt className="text-gray-600">Schema Inference</dt>
              <dd className="font-medium">{job.source_config.schema_inference ? 'Enabled' : 'Disabled'}</dd>
            </div>
          </dl>
        </div>

        {/* Destination */}
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-3">Destination</h3>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-gray-600">Table</dt>
              <dd className="font-medium font-mono text-blue-600">{job.destination}</dd>
            </div>
          </dl>
        </div>

        {/* Processing Config */}
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-3">Processing</h3>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-gray-600">Mode</dt>
              <dd className="font-medium capitalize">{job.processing_config.mode}</dd>
            </div>
            <div>
              <dt className="text-gray-600">Format</dt>
              <dd className="font-medium uppercase">{job.processing_config.format}</dd>
            </div>
            <div>
              <dt className="text-gray-600">Checkpointing</dt>
              <dd className="font-medium">{job.processing_config.checkpoint_enabled ? 'Enabled' : 'Disabled'}</dd>
            </div>
          </dl>
        </div>

        {/* Statistics */}
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-3">Statistics</h3>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-gray-600">Total Runs</dt>
              <dd className="font-medium">{job.runs_count}</dd>
            </div>
            <div>
              <dt className="text-gray-600">Successful</dt>
              <dd className="font-medium text-green-600">{job.success_count}</dd>
            </div>
            <div>
              <dt className="text-gray-600">Failed</dt>
              <dd className="font-medium text-red-600">{job.failure_count}</dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Schedule */}
      {job.schedule_config?.enabled && (
        <div className="bg-white border rounded-lg p-4">
          <h3 className="font-semibold text-gray-900 mb-3">Schedule</h3>
          <dl className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <dt className="text-gray-600">Cron Expression</dt>
              <dd className="font-medium font-mono">{job.schedule_config.cron_expression}</dd>
            </div>
            <div>
              <dt className="text-gray-600">Timezone</dt>
              <dd className="font-medium">{job.schedule_config.timezone}</dd>
            </div>
            <div>
              <dt className="text-gray-600">Max Retries</dt>
              <dd className="font-medium">{job.schedule_config.max_retries}</dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// LOGS TAB
// ============================================================================

function LogsTab({ logs, isLoading }: any) {
  const [levelFilter, setLevelFilter] = useState<string>('')

  const filteredLogs = levelFilter
    ? logs.filter((log: any) => log.level === levelFilter)
    : logs

  const levelColors = {
    INFO: 'text-blue-600',
    WARN: 'text-yellow-600',
    ERROR: 'text-red-600',
    DEBUG: 'text-gray-600',
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Live Job Logs</h3>
        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          className="px-3 py-1 border border-gray-300 rounded text-sm"
        >
          <option value="">All Levels</option>
          <option value="INFO">INFO</option>
          <option value="WARN">WARN</option>
          <option value="ERROR">ERROR</option>
          <option value="DEBUG">DEBUG</option>
        </select>
      </div>

      <div className="bg-gray-900 rounded-lg p-4 font-mono text-sm h-96 overflow-y-auto">
        {isLoading ? (
          <div className="text-gray-400">Loading logs...</div>
        ) : filteredLogs.length > 0 ? (
          filteredLogs.map((log: any, idx: number) => (
            <div key={idx} className="mb-1 text-gray-300">
              <span className="text-gray-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
              {' '}
              <span className={levelColors[log.level as keyof typeof levelColors]}>[{log.level}]</span>
              {' '}
              <span>{log.message}</span>
            </div>
          ))
        ) : (
          <div className="text-gray-500">No logs available</div>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// METRICS TAB
// ============================================================================

function MetricsTab({ metrics, isLoading }: any) {
  if (isLoading) {
    return <div>Loading metrics...</div>
  }

  if (!metrics) {
    return <div>No metrics available</div>
  }

  const m = metrics.metrics

  return (
    <div className="space-y-6">
      <h3 className="font-semibold text-gray-900">Real-time Metrics</h3>

      <div className="grid grid-cols-3 gap-4">
        <MetricCard label="Records Processed" value={m.records_processed.toLocaleString()} color="blue" />
        <MetricCard label="Records Failed" value={m.records_failed.toLocaleString()} color="red" />
        <MetricCard label="Throughput" value={`${m.throughput_rps.toLocaleString()} rec/s`} color="green" />
        <MetricCard label="Bytes Processed" value={formatBytes(m.bytes_processed)} color="purple" />
        <MetricCard label="Active Workers" value={m.active_workers.toString()} color="indigo" />
        <MetricCard label="CPU Utilization" value={`${m.cpu_utilization.toFixed(1)}%`} color="orange" />
        <MetricCard label="Memory Utilization" value={`${m.memory_utilization.toFixed(1)}%`} color="pink" />
        <MetricCard label="Cache Hit Rate" value={`${(m.cache_hit_rate * 100).toFixed(1)}%`} color="teal" />
        <MetricCard
          label="Photon Acceleration"
          value={m.photon_acceleration ? 'Enabled' : 'Disabled'}
          color={m.photon_acceleration ? 'green' : 'gray'}
        />
      </div>
    </div>
  )
}

function MetricCard({ label, value, color }: any) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700',
    red: 'bg-red-50 text-red-700',
    green: 'bg-green-50 text-green-700',
    purple: 'bg-purple-50 text-purple-700',
    indigo: 'bg-indigo-50 text-indigo-700',
    orange: 'bg-orange-50 text-orange-700',
    pink: 'bg-pink-50 text-pink-700',
    teal: 'bg-teal-50 text-teal-700',
    gray: 'bg-gray-50 text-gray-700',
  }

  return (
    <div className={`p-4 rounded-lg ${colors[color]}`}>
      <div className="text-sm font-medium opacity-80">{label}</div>
      <div className="text-2xl font-bold mt-1">{value}</div>
    </div>
  )
}

// ============================================================================
// COMPUTE TAB
// ============================================================================

function ComputeTab({ job, jobId }: any) {
  const config = job.compute_config
  const { data: presetsData } = useComputePresets()
  const updateConfig = useUpdateComputeConfig()

  const [editedConfig, setEditedConfig] = useState<ComputeConfig>(config)

  const handleSave = () => {
    updateConfig.mutate({ jobId, config: editedConfig })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-900">Compute Configuration</h3>
        <button
          onClick={handleSave}
          disabled={updateConfig.isPending || job.status === 'running'}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          Save Changes
        </button>
      </div>

      {/* Presets */}
      {presetsData && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Quick Presets</label>
          <div className="grid grid-cols-2 gap-3">
            {presetsData.presets.map((preset) => (
              <button
                key={preset.name}
                onClick={() => setEditedConfig(preset.config)}
                className="p-3 border border-gray-300 rounded-lg hover:border-blue-500 text-left"
              >
                <div className="font-medium text-sm">{preset.name}</div>
                <div className="text-xs text-gray-600 mt-1">{preset.description}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Configuration Form */}
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Cluster Mode</label>
            <select
              value={editedConfig.cluster_mode}
              onChange={(e) => setEditedConfig({ ...editedConfig, cluster_mode: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="single">Single Node</option>
              <option value="multi-node">Multi-Node</option>
              <option value="serverless">Serverless</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Instance Type</label>
            <select
              value={editedConfig.instance_type}
              onChange={(e) => setEditedConfig({ ...editedConfig, instance_type: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            >
              <option value="standard">Standard</option>
              <option value="memory_optimized">Memory Optimized</option>
              <option value="compute_optimized">Compute Optimized</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Min Workers</label>
            <input
              type="number"
              value={editedConfig.min_workers}
              onChange={(e) => setEditedConfig({ ...editedConfig, min_workers: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              min="1"
              max="100"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Workers</label>
            <input
              type="number"
              value={editedConfig.max_workers}
              onChange={(e) => setEditedConfig({ ...editedConfig, max_workers: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              min="1"
              max="1000"
            />
          </div>
        </div>

        {/* Toggles */}
        <div className="space-y-3">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={editedConfig.autoscaling_enabled}
              onChange={(e) => setEditedConfig({ ...editedConfig, autoscaling_enabled: e.target.checked })}
              className="mr-2"
            />
            <span className="text-sm font-medium">Enable Autoscaling</span>
          </label>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={editedConfig.photon_enabled}
              onChange={(e) => setEditedConfig({ ...editedConfig, photon_enabled: e.target.checked })}
              className="mr-2"
            />
            <span className="text-sm font-medium">🚀 Enable Photon Engine (Query Acceleration)</span>
          </label>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={editedConfig.adaptive_query_execution}
              onChange={(e) => setEditedConfig({ ...editedConfig, adaptive_query_execution: e.target.checked })}
              className="mr-2"
            />
            <span className="text-sm font-medium">Adaptive Query Execution (AQE)</span>
          </label>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={editedConfig.dynamic_partition_pruning}
              onChange={(e) => setEditedConfig({ ...editedConfig, dynamic_partition_pruning: e.target.checked })}
              className="mr-2"
            />
            <span className="text-sm font-medium">Dynamic Partition Pruning (DPP)</span>
          </label>

          <label className="flex items-center">
            <input
              type="checkbox"
              checked={editedConfig.cbo_enabled}
              onChange={(e) => setEditedConfig({ ...editedConfig, cbo_enabled: e.target.checked })}
              className="mr-2"
            />
            <span className="text-sm font-medium">Cost-Based Optimizer (CBO)</span>
          </label>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// CREATE JOB WIZARD
// ============================================================================

function CreateJobWizard({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState<Partial<JobCreate>>({
    job_name: '',
    description: '',
    source_config: {
      source_type: 's3',
      connection_params: {},
      schema_inference: true,
    },
    destination_schema: 'default',
    destination_table: '',
    processing_config: {
      mode: 'batch',
      format: 'auto',
      checkpoint_enabled: true,
    },
    compute_config: {
      cluster_mode: 'single',
      instance_type: 'standard',
      min_workers: 1,
      max_workers: 10,
      autoscaling_enabled: true,
      photon_enabled: false,
      adaptive_query_execution: true,
      dynamic_partition_pruning: true,
      cbo_enabled: true,
    },
    tags: [],
  })

  const createJob = useCreateJob()
  const { data: sourcesData } = useAvailableSources()

  const handleSubmit = () => {
    createJob.mutate(formData as JobCreate, {
      onSuccess: () => {
        onClose()
      },
    })
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">Create New Job</h2>
          <p className="text-sm text-gray-600 mt-1">Step {step} of 4</p>
        </div>

        <div className="p-6">
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Basic Information</h3>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Job Name</label>
                <input
                  type="text"
                  value={formData.job_name}
                  onChange={(e) => setFormData({ ...formData, job_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  placeholder="e.g., Customer Data Import"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  rows={3}
                  placeholder="Optional description"
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Source Configuration</h3>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Source Type</label>
                <select
                  value={formData.source_config?.source_type}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      source_config: {
                        ...formData.source_config!,
                        source_type: e.target.value as any,
                      },
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                >
                  {sourcesData?.sources.map((source) => (
                    <option key={source.type} value={source.type}>
                      {source.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Destination Schema</label>
                  <input
                    type="text"
                    value={formData.destination_schema}
                    onChange={(e) => setFormData({ ...formData, destination_schema: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Destination Table</label>
                  <input
                    type="text"
                    value={formData.destination_table}
                    onChange={(e) => setFormData({ ...formData, destination_table: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Processing Configuration</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Processing Mode</label>
                  <select
                    value={formData.processing_config?.mode}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        processing_config: {
                          ...formData.processing_config!,
                          mode: e.target.value as any,
                        },
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="batch">Batch</option>
                    <option value="streaming">Streaming</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">File Format</label>
                  <select
                    value={formData.processing_config?.format}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        processing_config: {
                          ...formData.processing_config!,
                          format: e.target.value as any,
                        },
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="auto">Auto-detect</option>
                    <option value="csv">CSV</option>
                    <option value="json">JSON</option>
                    <option value="parquet">Parquet</option>
                    <option value="avro">Avro</option>
                    <option value="delta">Delta</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Compute Resources</h3>
              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.compute_config?.photon_enabled}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        compute_config: {
                          ...formData.compute_config!,
                          photon_enabled: e.target.checked,
                        },
                      })
                    }
                    className="mr-2"
                  />
                  <span className="text-sm font-medium">🚀 Enable Photon Engine (Recommended for large datasets)</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.compute_config?.autoscaling_enabled}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        compute_config: {
                          ...formData.compute_config!,
                          autoscaling_enabled: e.target.checked,
                        },
                      })
                    }
                    className="mr-2"
                  />
                  <span className="text-sm font-medium">Enable Autoscaling</span>
                </label>
              </div>
            </div>
          )}
        </div>

        <div className="p-6 border-t flex justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <div className="flex gap-2">
            {step > 1 && (
              <button
                onClick={() => setStep(step - 1)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Previous
              </button>
            )}
            {step < 4 ? (
              <button
                onClick={() => setStep(step + 1)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Next
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={createJob.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {createJob.isPending ? 'Creating...' : 'Create Job'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// EMPTY STATE
// ============================================================================

function EmptyState() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center text-gray-500">
        <p className="text-lg mb-2">Select a job to view details</p>
        <p className="text-sm">or create a new job to get started</p>
      </div>
    </div>
  )
}

// ============================================================================
// UTILITIES
// ============================================================================

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`
}
