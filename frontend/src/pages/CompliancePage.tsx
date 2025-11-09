/**
 * Compliance Dashboard Page
 *
 * PII detection, policy management, and compliance checking
 */

import React, { useState } from 'react'
import {
  usePolicies,
  useComplianceStats,
  useDetectPII,
  useMaskPII,
  useCreatePolicy,
  useDeletePolicy,
  useUpdatePolicy,
  useViolations
} from '@/hooks/useCompliance'

export default function CompliancePage() {
  const [activeTab, setActiveTab] = useState<'detect' | 'policies' | 'violations'>('detect')

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Compliance & PII Detection</h1>
        <p className="text-gray-600 mt-2">Manage data compliance and detect sensitive information</p>
      </div>

      {/* Statistics Cards */}
      <StatsCards />

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {[
              { id: 'detect', label: 'PII Detection' },
              { id: 'policies', label: 'Policies' },
              { id: 'violations', label: 'Violations' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-6 py-4 text-sm font-medium border-b-2 ${
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
      </div>

      {/* Tab Content */}
      {activeTab === 'detect' && <PIIDetectionTab />}
      {activeTab === 'policies' && <PoliciesTab />}
      {activeTab === 'violations' && <ViolationsTab />}
    </div>
  )
}

// Statistics Cards Component
function StatsCards() {
  const { data: stats, isLoading } = useComplianceStats()

  if (isLoading || !stats) {
    return <div className="mb-8">Loading statistics...</div>
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm font-medium text-gray-500">Total Policies</div>
        <div className="text-3xl font-bold text-gray-900 mt-2">{stats.total_policies}</div>
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm font-medium text-gray-500">Active Policies</div>
        <div className="text-3xl font-bold text-green-600 mt-2">{stats.enabled_policies}</div>
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm font-medium text-gray-500">Total Violations</div>
        <div className="text-3xl font-bold text-red-600 mt-2">{stats.total_violations}</div>
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm font-medium text-gray-500">PII Detection</div>
        <div className="text-sm text-gray-900 mt-2">
          {stats.presidio_enabled ? '✅ Presidio Enabled' : '⚠️ Regex Only'}
        </div>
      </div>
    </div>
  )
}

// PII Detection Tab
function PIIDetectionTab() {
  const [text, setText] = useState('')
  const detectPII = useDetectPII()
  const maskPII = useMaskPII()
  const [maskedText, setMaskedText] = useState('')

  const handleDetect = async () => {
    try {
      await detectPII.mutateAsync({ text })
    } catch (error) {
      console.error('Detection failed:', error)
    }
  }

  const handleMask = async (anonymize: boolean) => {
    try {
      const result = await maskPII.mutateAsync({ text, anonymize })
      setMaskedText(result.masked_text)
    } catch (error) {
      console.error('Masking failed:', error)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-xl font-bold mb-4">Detect PII in Text</h2>

      {/* Input */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Text to Analyze
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          rows={6}
          placeholder="Paste text here... e.g., 'Contact John at john@example.com or call 555-1234'"
        />
      </div>

      {/* Actions */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={handleDetect}
          disabled={!text.trim() || detectPII.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {detectPII.isPending ? 'Detecting...' : 'Detect PII'}
        </button>
        <button
          onClick={() => handleMask(false)}
          disabled={!text.trim() || maskPII.isPending}
          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
        >
          Mask PII
        </button>
        <button
          onClick={() => handleMask(true)}
          disabled={!text.trim() || maskPII.isPending}
          className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
        >
          Anonymize PII
        </button>
      </div>

      {/* Results */}
      {detectPII.data && (
        <div className="border-t pt-4">
          <h3 className="font-bold mb-2">Detection Results</h3>
          {detectPII.data.found_pii ? (
            <div>
              <p className="text-sm text-gray-600 mb-3">
                Found {detectPII.data.pii_count} PII entities: {detectPII.data.pii_types.join(', ')}
              </p>
              <div className="space-y-2">
                {detectPII.data.results.map((item, idx) => (
                  <div key={idx} className="bg-yellow-50 border border-yellow-200 rounded p-3">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-yellow-800">{item.entity_type}</span>
                      <span className="text-sm text-yellow-600">{(item.confidence * 100).toFixed(0)}% confidence</span>
                    </div>
                    <div className="text-sm text-gray-700 mt-1">"{item.text}"</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-green-600">✅ No PII detected</p>
          )}
        </div>
      )}

      {/* Masked Result */}
      {maskedText && (
        <div className="border-t pt-4 mt-4">
          <h3 className="font-bold mb-2">Masked Text</h3>
          <div className="bg-gray-50 border rounded p-3">
            <pre className="text-sm whitespace-pre-wrap">{maskedText}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

// Policies Tab
function PoliciesTab() {
  const { data: policiesData, isLoading } = usePolicies()
  const deletePolicy = useDeletePolicy()
  const updatePolicy = useUpdatePolicy()
  const [showCreateModal, setShowCreateModal] = useState(false)

  const handleTogglePolicy = async (name: string, enabled: boolean) => {
    try {
      await updatePolicy.mutateAsync({ name, updates: { enabled: !enabled } })
    } catch (error) {
      console.error('Failed to toggle policy:', error)
    }
  }

  const handleDeletePolicy = async (name: string) => {
    if (window.confirm(`Delete policy "${name}"?`)) {
      try {
        await deletePolicy.mutateAsync(name)
      } catch (error) {
        console.error('Failed to delete policy:', error)
      }
    }
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="p-6 border-b flex items-center justify-between">
        <h2 className="text-xl font-bold">Compliance Policies</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + Create Policy
        </button>
      </div>

      {/* Policies List */}
      {isLoading ? (
        <div className="p-8 text-center text-gray-500">Loading policies...</div>
      ) : !policiesData?.policies || policiesData.policies.length === 0 ? (
        <div className="p-8 text-center text-gray-500">No policies found</div>
      ) : (
        <div className="divide-y">
          {policiesData.policies.map((policy) => (
            <div key={policy.name} className="p-6 hover:bg-gray-50">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-gray-900">{policy.name}</h3>
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      policy.severity === 'critical' ? 'bg-red-100 text-red-800' :
                      policy.severity === 'error' ? 'bg-orange-100 text-orange-800' :
                      policy.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {policy.severity}
                    </span>
                    <span className="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">
                      {policy.policy_type}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{policy.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleTogglePolicy(policy.name, policy.enabled)}
                    className={`px-3 py-1 text-sm rounded ${
                      policy.enabled
                        ? 'bg-green-100 text-green-800 hover:bg-green-200'
                        : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                    }`}
                  >
                    {policy.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                  <button
                    onClick={() => handleDeletePolicy(policy.name)}
                    className="px-3 py-1 text-sm text-red-600 hover:text-red-900"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreatePolicyModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  )
}

// Violations Tab
function ViolationsTab() {
  const { data: violationsData, isLoading } = useViolations({ limit: 100 })

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b">
        <h2 className="text-xl font-bold">Policy Violations</h2>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-gray-500">Loading violations...</div>
      ) : !violationsData?.violations || violationsData.violations.length === 0 ? (
        <div className="p-8 text-center text-gray-500">No violations recorded</div>
      ) : (
        <div className="divide-y">
          {violationsData.violations.map((violation, idx) => (
            <div key={idx} className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-gray-900">{violation.policy_name}</span>
                    <span className={`px-2 py-1 text-xs rounded-full ${
                      violation.severity === 'critical' ? 'bg-red-100 text-red-800' :
                      violation.severity === 'error' ? 'bg-orange-100 text-orange-800' :
                      violation.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {violation.severity}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{violation.description}</p>
                  {violation.data_context && (
                    <pre className="text-xs text-gray-500 mt-2 bg-gray-50 p-2 rounded">
                      {violation.data_context}
                    </pre>
                  )}
                </div>
                <span className="text-sm text-gray-500">
                  {new Date(violation.timestamp).toLocaleString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Create Policy Modal
function CreatePolicyModal({ onClose }: { onClose: () => void }) {
  const createPolicy = useCreatePolicy()
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    policy_type: 'pii_protection' as const,
    template: 'no_pii' as const,
    severity: 'error' as const,
    parameters: {}
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createPolicy.mutateAsync(formData)
      onClose()
    } catch (error) {
      console.error('Failed to create policy:', error)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Create Policy</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              required
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Template</label>
            <select
              value={formData.template}
              onChange={(e) => setFormData({ ...formData, template: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="no_pii">No PII Allowed</option>
              <option value="no_empty_data">No Empty Data</option>
              <option value="max_length">Maximum Length</option>
              <option value="min_length">Minimum Length</option>
              <option value="contains_keyword">Contains Keyword</option>
            </select>
          </div>

          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">Severity</label>
            <select
              value={formData.severity}
              onChange={(e) => setFormData({ ...formData, severity: e.target.value as any })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              disabled={createPolicy.isPending}
            >
              {createPolicy.isPending ? 'Creating...' : 'Create Policy'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
