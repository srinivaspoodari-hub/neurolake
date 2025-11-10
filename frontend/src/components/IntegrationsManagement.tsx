/**
 * Integrations Management Component
 *
 * Configure and manage external integrations:
 * - Google API (Drive, Sheets)
 * - Groq LLM (Natural Language to SQL, Chat)
 */

import React, { useState } from 'react'
import {
  useIntegrationsStatus,
  useGroqModels,
  useGroqChat,
  useGenerateSQLFromNL,
  useExplainSQL,
  useGoogleDriveFiles,
  useImportGoogleSheet,
} from '@/hooks/useIntegrations'

export default function IntegrationsManagement() {
  const [activeTab, setActiveTab] = useState<'overview' | 'google' | 'groq'>('overview')
  const { data: status } = useIntegrationsStatus()

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Integrations</h2>
          <p className="text-sm text-gray-600 mt-1">
            Configure external services: Google API, Groq LLM, and more
          </p>
        </div>

        {/* Status Overview */}
        {status && (
          <div className="mt-4 flex gap-3">
            <div
              className={`px-3 py-2 rounded-lg text-sm font-medium ${
                status.google.configured
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              Google API: {status.google.configured ? '✅ Connected' : '❌ Not configured'}
            </div>
            <div
              className={`px-3 py-2 rounded-lg text-sm font-medium ${
                status.groq.configured
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              Groq LLM: {status.groq.configured ? '✅ Connected' : '❌ Not configured'}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="mt-4 flex gap-4 border-b">
          {['overview', 'google', 'groq'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`px-4 py-2 font-medium capitalize ${
                activeTab === tab
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab === 'google' ? 'Google API' : tab === 'groq' ? 'Groq LLM' : tab}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'overview' && <OverviewTab status={status} />}
        {activeTab === 'google' && <GoogleTab />}
        {activeTab === 'groq' && <GroqTab />}
      </div>
    </div>
  )
}

// ============================================================================
// OVERVIEW TAB
// ============================================================================

function OverviewTab({ status }: any) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Google API Card */}
        <div className="bg-white border rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center text-2xl">
              🔵
            </div>
            <div>
              <h3 className="font-semibold text-lg">Google API</h3>
              <p className="text-sm text-gray-600">Drive & Sheets integration</p>
            </div>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Status:</span>
              <span className={status?.google.configured ? 'text-green-600' : 'text-red-600'}>
                {status?.google.configured ? 'Connected' : 'Not configured'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Credentials:</span>
              <span className={status?.google.hasCredentials ? 'text-green-600' : 'text-gray-400'}>
                {status?.google.hasCredentials ? 'Set' : 'Not set'}
              </span>
            </div>
          </div>
          <div className="mt-4 p-3 bg-blue-50 rounded text-xs text-blue-800">
            <strong>Features:</strong> Import data from Google Drive, sync Google Sheets, OAuth
            authentication
          </div>
        </div>

        {/* Groq LLM Card */}
        <div className="bg-white border rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center text-2xl">
              🤖
            </div>
            <div>
              <h3 className="font-semibold text-lg">Groq LLM</h3>
              <p className="text-sm text-gray-600">Ultra-fast AI inference</p>
            </div>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Status:</span>
              <span className={status?.groq.configured ? 'text-green-600' : 'text-red-600'}>
                {status?.groq.configured ? 'Connected' : 'Not configured'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">API Key:</span>
              <span className={status?.groq.hasApiKey ? 'text-green-600' : 'text-gray-400'}>
                {status?.groq.hasApiKey ? 'Set' : 'Not set'}
              </span>
            </div>
          </div>
          <div className="mt-4 p-3 bg-purple-50 rounded text-xs text-purple-800">
            <strong>Features:</strong> Natural language to SQL, SQL explanation, AI chat, query
            optimization
          </div>
        </div>
      </div>

      {/* Setup Instructions */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold text-lg mb-3">Quick Setup Guide</h3>
        <div className="space-y-4">
          <div>
            <h4 className="font-medium text-sm mb-2">1. Google API Setup</h4>
            <ol className="list-decimal list-inside text-sm text-gray-600 space-y-1 ml-2">
              <li>Go to Google Cloud Console</li>
              <li>Create a new project or select existing</li>
              <li>Enable Google Drive API and Google Sheets API</li>
              <li>Create OAuth 2.0 credentials</li>
              <li>Set environment variables: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET</li>
            </ol>
          </div>
          <div>
            <h4 className="font-medium text-sm mb-2">2. Groq LLM Setup</h4>
            <ol className="list-decimal list-inside text-sm text-gray-600 space-y-1 ml-2">
              <li>Sign up at console.groq.com</li>
              <li>Generate an API key</li>
              <li>Set environment variable: GROQ_API_KEY</li>
              <li>Restart the backend server</li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// GOOGLE TAB
// ============================================================================

function GoogleTab() {
  const [accessToken, setAccessToken] = useState('')
  const [showDrive, setShowDrive] = useState(false)

  return (
    <div className="space-y-6">
      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold text-lg mb-4">Google API Configuration</h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Access Token (for testing)
            </label>
            <input
              type="password"
              value={accessToken}
              onChange={(e) => setAccessToken(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              placeholder="Enter Google OAuth access token"
            />
            <p className="text-xs text-gray-500 mt-1">
              In production, use OAuth flow. For testing, you can paste an access token here.
            </p>
          </div>

          <div>
            <h4 className="font-medium text-sm mb-2">Environment Variables Required:</h4>
            <div className="bg-gray-100 p-3 rounded font-mono text-xs space-y-1">
              <div>GOOGLE_CLIENT_ID=your_client_id</div>
              <div>GOOGLE_CLIENT_SECRET=your_client_secret</div>
            </div>
          </div>

          <button
            onClick={() => setShowDrive(!showDrive)}
            disabled={!accessToken}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {showDrive ? 'Hide' : 'Browse'} Google Drive
          </button>
        </div>
      </div>

      {showDrive && accessToken && <GoogleDriveBrowser accessToken={accessToken} />}

      {/* Usage Example */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold text-lg mb-3">Google Sheets Import Example</h3>
        <div className="bg-gray-900 p-4 rounded text-sm font-mono text-gray-300 overflow-x-auto">
          <div className="text-green-400">// Import Google Sheet to NeuroLake table</div>
          <div className="mt-2">
            POST /api/v1/integrations/google/sheets/{'{'}spreadsheet_id{'}'}/import
          </div>
          <div className="mt-2 text-blue-400">
            {
              '{\n  "table_name": "customers",\n  "schema": "analytics",\n  "range": "Sheet1!A1:Z1000"\n}'
            }
          </div>
        </div>
      </div>
    </div>
  )
}

function GoogleDriveBrowser({ accessToken }: { accessToken: string }) {
  const { data: files, isLoading } = useGoogleDriveFiles(accessToken)

  if (isLoading) {
    return <div className="bg-white border rounded-lg p-6">Loading Google Drive files...</div>
  }

  return (
    <div className="bg-white border rounded-lg p-6">
      <h3 className="font-semibold text-lg mb-4">Google Drive Files</h3>
      <div className="space-y-2">
        {files && files.length > 0 ? (
          files.slice(0, 10).map((file) => (
            <div key={file.id} className="flex items-center justify-between p-3 border rounded">
              <div>
                <div className="font-medium">{file.name}</div>
                <div className="text-xs text-gray-500">{file.mimeType}</div>
              </div>
              <div className="text-sm text-gray-600">
                {file.size ? `${(file.size / 1024).toFixed(2)} KB` : 'N/A'}
              </div>
            </div>
          ))
        ) : (
          <p className="text-gray-500">No files found or invalid token</p>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// GROQ TAB
// ============================================================================

function GroqTab() {
  const { data: modelsData } = useGroqModels()
  const generateSQL = useGenerateSQLFromNL()
  const explainSQL = useExplainSQL()
  const chat = useGroqChat()

  const [nlQuestion, setNlQuestion] = useState('')
  const [sqlToExplain, setSqlToExplain] = useState('')
  const [chatMessage, setChatMessage] = useState('')

  const handleGenerateSQL = async () => {
    if (!nlQuestion.trim()) return
    await generateSQL.mutateAsync({ question: nlQuestion })
  }

  const handleExplainSQL = async () => {
    if (!sqlToExplain.trim()) return
    await explainSQL.mutateAsync({ sql: sqlToExplain })
  }

  const handleChat = async () => {
    if (!chatMessage.trim()) return
    await chat.mutateAsync({
      messages: [
        { role: 'system', content: 'You are a helpful AI assistant for data engineering.' },
        { role: 'user', content: chatMessage },
      ],
      model: 'llama3-70b-8192',
    })
  }

  return (
    <div className="space-y-6">
      {/* Configuration */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold text-lg mb-4">Groq LLM Configuration</h3>
        <div className="space-y-4">
          <div>
            <h4 className="font-medium text-sm mb-2">Environment Variable Required:</h4>
            <div className="bg-gray-100 p-3 rounded font-mono text-xs">
              GROQ_API_KEY=your_groq_api_key
            </div>
          </div>

          <div>
            <h4 className="font-medium text-sm mb-2">Available Models:</h4>
            {modelsData?.models && modelsData.models.length > 0 ? (
              <div className="space-y-2">
                {modelsData.models.map((model) => (
                  <div key={model.id} className="p-3 border rounded">
                    <div className="font-medium text-sm">{model.id}</div>
                    <div className="text-xs text-gray-600 mt-1">{model.description}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      Context: {model.context_window.toLocaleString()} tokens
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-3 bg-red-50 text-red-700 rounded text-sm">
                ❌ Groq API not configured. Set GROQ_API_KEY environment variable.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Natural Language to SQL */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold text-lg mb-4">Natural Language to SQL</h3>
        <div className="space-y-3">
          <textarea
            value={nlQuestion}
            onChange={(e) => setNlQuestion(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            rows={3}
            placeholder="Ask a question in plain English, e.g., 'Show me top 10 customers by revenue'"
          />
          <button
            onClick={handleGenerateSQL}
            disabled={generateSQL.isPending || !nlQuestion.trim()}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {generateSQL.isPending ? 'Generating...' : 'Convert to SQL'}
          </button>

          {generateSQL.data && (
            <div className="mt-4 p-4 bg-gray-900 rounded text-sm font-mono text-gray-300">
              <div className="text-green-400 mb-2">// Generated SQL:</div>
              <div className="text-blue-300">{generateSQL.data.sql}</div>
              <div className="mt-3 text-gray-400 text-xs">
                Confidence: {(generateSQL.data.confidence * 100).toFixed(0)}%
              </div>
              <div className="mt-1 text-gray-400 text-xs">{generateSQL.data.explanation}</div>
            </div>
          )}
        </div>
      </div>

      {/* SQL Explanation */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold text-lg mb-4">SQL Explanation</h3>
        <div className="space-y-3">
          <textarea
            value={sqlToExplain}
            onChange={(e) => setSqlToExplain(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
            rows={4}
            placeholder="Paste SQL query to get AI explanation..."
          />
          <button
            onClick={handleExplainSQL}
            disabled={explainSQL.isPending || !sqlToExplain.trim()}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {explainSQL.isPending ? 'Explaining...' : 'Explain SQL'}
          </button>

          {explainSQL.data && (
            <div className="mt-4 p-4 bg-blue-50 rounded">
              <div className="font-medium text-sm mb-2">Explanation:</div>
              <div className="text-sm text-gray-700">{explainSQL.data.explanation}</div>
              <div className="mt-2 text-xs text-gray-500">
                Complexity: {explainSQL.data.complexity}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Chat */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="font-semibold text-lg mb-4">AI Chat</h3>
        <div className="space-y-3">
          <textarea
            value={chatMessage}
            onChange={(e) => setChatMessage(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            rows={3}
            placeholder="Ask the AI anything about data engineering..."
          />
          <button
            onClick={handleChat}
            disabled={chat.isPending || !chatMessage.trim()}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {chat.isPending ? 'Thinking...' : 'Send Message'}
          </button>

          {chat.data && (
            <div className="mt-4 p-4 bg-purple-50 rounded">
              <div className="font-medium text-sm mb-2">AI Response:</div>
              <div className="text-sm text-gray-700">
                {chat.data.choices[0]?.message.content || 'No response'}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
