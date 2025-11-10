/**
 * NUIC Catalog Browser
 *
 * Comprehensive catalog interface with:
 * - Left: Schema/Table tree navigation
 * - Right: Table details with multiple tabs
 */

import React, { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import {
  useSchemas,
  useTables,
  useTableDetails,
  useTableDDL,
  useTableSample,
  useTableVersions,
  useTablePermissions,
  useCreateTable,
  useDeleteTable,
  useGrantAccess,
  useRevokeAccess,
} from '@/hooks/useCatalog'

type DetailTab = 'overview' | 'schema' | 'sample' | 'ddl' | 'properties' | 'access' | 'versions'

export default function CatalogBrowser() {
  const [selectedSchema, setSelectedSchema] = useState<string | null>(null)
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set())

  const { data: schemas, isLoading: schemasLoading } = useSchemas()

  const handleSchemaClick = (schemaName: string) => {
    const newExpanded = new Set(expandedSchemas)
    if (expandedSchemas.has(schemaName)) {
      newExpanded.delete(schemaName)
    } else {
      newExpanded.add(schemaName)
    }
    setExpandedSchemas(newExpanded)
    setSelectedSchema(schemaName)
  }

  const handleTableClick = (schemaName: string, tableName: string) => {
    setSelectedSchema(schemaName)
    setSelectedTable(tableName)
  }

  return (
    <div className="flex h-[calc(100vh-300px)] border rounded-lg overflow-hidden bg-white">
      {/* Left Sidebar - Tree Navigation */}
      <div className="w-80 border-r bg-gray-50 overflow-y-auto">
        <div className="p-4 border-b bg-white">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-lg">NUIC Catalog</h3>
            <button className="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700">
              + Schema
            </button>
          </div>
        </div>

        {schemasLoading ? (
          <div className="p-4 text-gray-500">Loading schemas...</div>
        ) : (
          <div className="p-2">
            {schemas?.map((schema) => (
              <SchemaTreeNode
                key={schema.name}
                schema={schema}
                isExpanded={expandedSchemas.has(schema.name)}
                isSelected={selectedSchema === schema.name}
                onSchemaClick={handleSchemaClick}
                onTableClick={handleTableClick}
                selectedTable={selectedTable}
              />
            ))}
            {(!schemas || schemas.length === 0) && (
              <div className="p-4 text-gray-500 text-sm">No schemas found</div>
            )}
          </div>
        )}
      </div>

      {/* Right Panel - Table Details */}
      <div className="flex-1 overflow-hidden">
        {selectedTable && selectedSchema ? (
          <TableDetailsPanel schemaName={selectedSchema} tableName={selectedTable} />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <div className="text-6xl mb-4">📊</div>
              <div className="text-lg font-medium">Select a table to view details</div>
              <div className="text-sm mt-2">Navigate the schema tree on the left</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Schema Tree Node Component
function SchemaTreeNode({
  schema,
  isExpanded,
  isSelected,
  onSchemaClick,
  onTableClick,
  selectedTable,
}: {
  schema: any
  isExpanded: boolean
  isSelected: boolean
  onSchemaClick: (name: string) => void
  onTableClick: (schema: string, table: string) => void
  selectedTable: string | null
}) {
  const { data: tables } = useTables(schema.name)

  return (
    <div className="mb-1">
      {/* Schema Header */}
      <div
        onClick={() => onSchemaClick(schema.name)}
        className={`flex items-center gap-2 px-3 py-2 rounded cursor-pointer hover:bg-gray-100 ${
          isSelected ? 'bg-blue-50 text-blue-700' : ''
        }`}
      >
        <span className="text-sm">{isExpanded ? '▼' : '▶'}</span>
        <span className="text-lg">📁</span>
        <div className="flex-1">
          <div className="font-medium">{schema.name}</div>
          <div className="text-xs text-gray-500">{schema.table_count} tables</div>
        </div>
      </div>

      {/* Tables List */}
      {isExpanded && (
        <div className="ml-8 mt-1">
          {tables?.map((table) => (
            <div
              key={table.name}
              onClick={() => onTableClick(schema.name, table.name)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded cursor-pointer hover:bg-gray-100 ${
                selectedTable === table.name ? 'bg-blue-100 text-blue-700' : ''
              }`}
            >
              <span className="text-base">{table.type === 'view' ? '👁️' : '📄'}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{table.name}</div>
                <div className="text-xs text-gray-500">
                  {table.format || 'NCF'} • {formatBytes(table.size_bytes)}
                </div>
              </div>
            </div>
          ))}
          {(!tables || tables.length === 0) && (
            <div className="px-3 py-2 text-xs text-gray-500">No tables</div>
          )}
        </div>
      )}
    </div>
  )
}

// Table Details Panel Component
function TableDetailsPanel({ schemaName, tableName }: { schemaName: string; tableName: string }) {
  const [activeTab, setActiveTab] = useState<DetailTab>('overview')
  const { data: details, isLoading } = useTableDetails(schemaName, tableName)
  const deleteTable = useDeleteTable()

  const handleDelete = async () => {
    if (confirm(`Are you sure you want to delete table "${tableName}"?`)) {
      await deleteTable.mutateAsync({ schemaName, tableName })
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Loading table details...</div>
      </div>
    )
  }

  if (!details) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-red-500">Table not found</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b p-4 bg-white">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold">{tableName}</h2>
            <div className="text-sm text-gray-600 mt-1">
              {schemaName} • {details.format} • {details.type}
            </div>
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">
              Query Table
            </button>
            <button
              onClick={handleDelete}
              className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b bg-white">
        <nav className="flex overflow-x-auto px-4">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'schema', label: 'Schema' },
            { id: 'sample', label: 'Sample Data' },
            { id: 'ddl', label: 'DDL' },
            { id: 'properties', label: 'Properties' },
            { id: 'access', label: 'Access Control' },
            { id: 'versions', label: 'Version History' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as DetailTab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
        {activeTab === 'overview' && <OverviewTab details={details} />}
        {activeTab === 'schema' && <SchemaTab details={details} />}
        {activeTab === 'sample' && <SampleDataTab schemaName={schemaName} tableName={tableName} />}
        {activeTab === 'ddl' && <DDLTab schemaName={schemaName} tableName={tableName} />}
        {activeTab === 'properties' && <PropertiesTab details={details} />}
        {activeTab === 'access' && <AccessControlTab schemaName={schemaName} tableName={tableName} />}
        {activeTab === 'versions' && <VersionHistoryTab schemaName={schemaName} tableName={tableName} />}
      </div>
    </div>
  )
}

// Overview Tab
function OverviewTab({ details }: { details: any }) {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg p-6">
        <h3 className="font-bold text-lg mb-4">Table Information</h3>
        <div className="grid grid-cols-2 gap-4">
          <InfoRow label="Name" value={details.name} />
          <InfoRow label="Schema" value={details.schema} />
          <InfoRow label="Type" value={details.type} />
          <InfoRow label="Format" value={details.format} />
          <InfoRow label="Owner" value={details.owner || 'N/A'} />
          <InfoRow label="Created By" value={details.created_by || 'N/A'} />
          <InfoRow
            label="Created"
            value={details.created_at ? formatDistanceToNow(new Date(details.created_at), { addSuffix: true }) : 'N/A'}
          />
          <InfoRow
            label="Last Modified"
            value={details.updated_at ? formatDistanceToNow(new Date(details.updated_at), { addSuffix: true }) : 'N/A'}
          />
          <InfoRow label="Location" value={details.location || 'N/A'} className="col-span-2" />
        </div>
      </div>

      {details.description && (
        <div className="bg-white rounded-lg p-6">
          <h3 className="font-bold text-lg mb-2">Description</h3>
          <p className="text-gray-700">{details.description}</p>
        </div>
      )}

      <div className="bg-white rounded-lg p-6">
        <h3 className="font-bold text-lg mb-4">Statistics</h3>
        <div className="grid grid-cols-3 gap-4">
          <StatCard label="Rows" value={formatNumber(details.statistics?.row_count)} />
          <StatCard label="Size" value={formatBytes(details.statistics?.size_bytes)} />
          <StatCard label="Files" value={formatNumber(details.statistics?.file_count)} />
        </div>
      </div>
    </div>
  )
}

// Schema Tab
function SchemaTab({ details }: { details: any }) {
  return (
    <div className="bg-white rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium">Column Name</th>
            <th className="px-4 py-3 text-left font-medium">Data Type</th>
            <th className="px-4 py-3 text-left font-medium">Nullable</th>
            <th className="px-4 py-3 text-left font-medium">Description</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {details.columns?.map((col: any, idx: number) => (
            <tr key={idx} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-mono text-blue-600">{col.name}</td>
              <td className="px-4 py-3 font-mono text-sm">{col.type}</td>
              <td className="px-4 py-3">
                {col.nullable ? (
                  <span className="text-green-600">✓</span>
                ) : (
                  <span className="text-red-600">✗</span>
                )}
              </td>
              <td className="px-4 py-3 text-gray-600">{col.description || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Sample Data Tab
function SampleDataTab({ schemaName, tableName }: { schemaName: string; tableName: string }) {
  const { data: sample, isLoading } = useTableSample(schemaName, tableName, 50)

  if (isLoading) {
    return <div className="text-gray-500">Loading sample data...</div>
  }

  if (!sample || !sample.data || sample.data.length === 0) {
    return (
      <div className="bg-white rounded-lg p-8 text-center text-gray-500">
        No sample data available
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              {sample.columns.map((col) => (
                <th key={col} className="px-4 py-3 text-left font-medium whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {sample.data.map((row, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                {sample.columns.map((col) => (
                  <td key={col} className="px-4 py-2 whitespace-nowrap">
                    {row[col] !== null && row[col] !== undefined ? String(row[col]) : (
                      <span className="text-gray-400">null</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-2 bg-gray-50 text-xs text-gray-600 border-t">
        Showing {sample.data.length} sample rows
      </div>
    </div>
  )
}

// DDL Tab
function DDLTab({ schemaName, tableName }: { schemaName: string; tableName: string }) {
  const { data: ddl, isLoading } = useTableDDL(schemaName, tableName)

  if (isLoading) {
    return <div className="text-gray-500">Loading DDL...</div>
  }

  return (
    <div className="bg-white rounded-lg p-4">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-bold">Table DDL</h3>
        <button
          onClick={() => navigator.clipboard.writeText(ddl?.ddl || '')}
          className="text-sm px-3 py-1 bg-gray-100 rounded hover:bg-gray-200"
        >
          Copy
        </button>
      </div>
      <pre className="bg-gray-900 text-gray-100 p-4 rounded overflow-x-auto text-sm">
        {ddl?.ddl || 'DDL not available'}
      </pre>
    </div>
  )
}

// Properties Tab
function PropertiesTab({ details }: { details: any }) {
  return (
    <div className="bg-white rounded-lg p-6">
      <h3 className="font-bold text-lg mb-4">Table Properties</h3>
      {details.properties && Object.keys(details.properties).length > 0 ? (
        <div className="space-y-2">
          {Object.entries(details.properties).map(([key, value]) => (
            <div key={key} className="flex border-b py-2">
              <div className="font-medium text-gray-700 w-1/3">{key}</div>
              <div className="text-gray-900 w-2/3">{String(value)}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-gray-500">No custom properties set</div>
      )}
    </div>
  )
}

// Access Control Tab
function AccessControlTab({ schemaName, tableName }: { schemaName: string; tableName: string }) {
  const { data: permissions, isLoading } = useTablePermissions(schemaName, tableName)
  const [showGrant, setShowGrant] = useState(false)
  const grantAccess = useGrantAccess()
  const revokeAccess = useRevokeAccess()

  const [grantForm, setGrantForm] = useState({
    principal_type: 'user' as 'user' | 'group' | 'organization',
    principal_id: '',
    permissions: [] as string[],
  })

  const handleGrant = async () => {
    await grantAccess.mutateAsync({
      schemaName,
      tableName,
      data: grantForm,
    })
    setShowGrant(false)
    setGrantForm({ principal_type: 'user', principal_id: '', permissions: [] })
  }

  const handleRevoke = async (permissionId: number) => {
    if (confirm('Revoke this access?')) {
      await revokeAccess.mutateAsync({ schemaName, tableName, permissionId })
    }
  }

  if (isLoading) {
    return <div className="text-gray-500">Loading permissions...</div>
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-bold text-lg">Access Permissions</h3>
          <button
            onClick={() => setShowGrant(!showGrant)}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            + Grant Access
          </button>
        </div>

        {showGrant && (
          <div className="mb-4 p-4 bg-gray-50 rounded border">
            <div className="grid grid-cols-3 gap-3 mb-3">
              <select
                value={grantForm.principal_type}
                onChange={(e) =>
                  setGrantForm({ ...grantForm, principal_type: e.target.value as any })
                }
                className="px-3 py-2 border rounded"
              >
                <option value="user">User</option>
                <option value="group">Group</option>
                <option value="organization">Organization</option>
              </select>
              <input
                type="text"
                placeholder="User/Group ID"
                value={grantForm.principal_id}
                onChange={(e) => setGrantForm({ ...grantForm, principal_id: e.target.value })}
                className="px-3 py-2 border rounded col-span-2"
              />
            </div>
            <div className="mb-3">
              <label className="text-sm font-medium mb-2 block">Permissions</label>
              <div className="flex gap-2 flex-wrap">
                {['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'ALTER', 'DROP'].map((perm) => (
                  <label key={perm} className="flex items-center gap-1 text-sm">
                    <input
                      type="checkbox"
                      checked={grantForm.permissions.includes(perm)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setGrantForm({
                            ...grantForm,
                            permissions: [...grantForm.permissions, perm],
                          })
                        } else {
                          setGrantForm({
                            ...grantForm,
                            permissions: grantForm.permissions.filter((p) => p !== perm),
                          })
                        }
                      }}
                    />
                    {perm}
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleGrant}
                className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700"
              >
                Grant
              </button>
              <button
                onClick={() => setShowGrant(false)}
                className="px-3 py-1.5 text-sm bg-gray-300 rounded hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Type</th>
              <th className="px-4 py-3 text-left font-medium">Principal</th>
              <th className="px-4 py-3 text-left font-medium">Permissions</th>
              <th className="px-4 py-3 text-left font-medium">Granted</th>
              <th className="px-4 py-3 text-left font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {permissions?.map((perm) => (
              <tr key={perm.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 capitalize">{perm.principal_type}</td>
                <td className="px-4 py-3 font-medium">{perm.principal_name}</td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 flex-wrap">
                    {perm.permissions.map((p) => (
                      <span key={p} className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs">
                        {p}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {formatDistanceToNow(new Date(perm.granted_at), { addSuffix: true })}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleRevoke(perm.id)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
            {(!permissions || permissions.length === 0) && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                  No permissions granted
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Version History Tab
function VersionHistoryTab({ schemaName, tableName }: { schemaName: string; tableName: string }) {
  const { data: versions, isLoading } = useTableVersions(schemaName, tableName)

  if (isLoading) {
    return <div className="text-gray-500">Loading version history...</div>
  }

  return (
    <div className="bg-white rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-medium">Version</th>
            <th className="px-4 py-3 text-left font-medium">Operation</th>
            <th className="px-4 py-3 text-left font-medium">Created By</th>
            <th className="px-4 py-3 text-left font-medium">Timestamp</th>
            <th className="px-4 py-3 text-left font-medium">Changes</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {versions?.map((version) => (
            <tr key={version.version} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-mono">v{version.version}</td>
              <td className="px-4 py-3">
                <span
                  className={`px-2 py-1 rounded text-xs ${
                    version.operation === 'CREATE'
                      ? 'bg-green-100 text-green-800'
                      : version.operation === 'UPDATE'
                      ? 'bg-blue-100 text-blue-800'
                      : version.operation === 'DELETE'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}
                >
                  {version.operation}
                </span>
              </td>
              <td className="px-4 py-3">{version.created_by}</td>
              <td className="px-4 py-3 text-gray-600">
                {formatDistanceToNow(new Date(version.created_at), { addSuffix: true })}
              </td>
              <td className="px-4 py-3">
                {version.changes ? (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-blue-600">View changes</summary>
                    <pre className="mt-2 bg-gray-100 p-2 rounded overflow-x-auto">
                      {JSON.stringify(version.changes, null, 2)}
                    </pre>
                  </details>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </td>
            </tr>
          ))}
          {(!versions || versions.length === 0) && (
            <tr>
              <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                No version history available
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

// Helper Components
function InfoRow({
  label,
  value,
  className = '',
}: {
  label: string
  value: string
  className?: string
}) {
  return (
    <div className={className}>
      <div className="text-sm text-gray-500">{label}</div>
      <div className="text-gray-900 font-medium">{value}</div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-50 rounded p-4 text-center">
      <div className="text-2xl font-bold text-blue-600">{value}</div>
      <div className="text-sm text-gray-600 mt-1">{label}</div>
    </div>
  )
}

// Helper Functions
function formatBytes(bytes?: number): string {
  if (!bytes) return 'N/A'
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

function formatNumber(num?: number): string | number {
  if (num === undefined || num === null) return 'N/A'
  return num.toLocaleString()
}
