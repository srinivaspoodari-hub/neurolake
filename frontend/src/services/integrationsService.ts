/**
 * Integrations Service
 *
 * External integrations for Google API and Groq LLM:
 * - Google Drive & Sheets
 * - Groq LLM (Natural Language to SQL, Chat, SQL Explain)
 */

import apiClient from '@/lib/api'

// ============================================================================
// TYPES
// ============================================================================

// Google API Types
export interface GoogleAuthResponse {
  access_token: string
  refresh_token?: string
  token_type: string
  expires_in: number
  scope: string
}

export interface GoogleDriveFile {
  id: string
  name: string
  mimeType: string
  size?: number
  createdTime: string
  modifiedTime: string
  webViewLink?: string
}

export interface GoogleSheetData {
  spreadsheetId: string
  title: string
  sheets: Array<{ name: string; index: number }>
  data?: any[][]
}

// Groq LLM Types
export interface GroqChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface GroqChatRequest {
  messages: GroqChatMessage[]
  model?: string
  temperature?: number
  max_tokens?: number
}

export interface GroqChatResponse {
  id: string
  model: string
  choices: Array<{
    message: GroqChatMessage
    finish_reason: string
  }>
  usage: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

export interface GroqSQLRequest {
  question: string
  schema_context?: string
  model?: string
}

export interface GroqSQLResponse {
  question: string
  sql: string
  confidence: number
  explanation: string
  tables_used: string[]
}

export interface GroqModel {
  id: string
  name: string
  context_window: number
  description: string
}

// ============================================================================
// SERVICE
// ============================================================================

class IntegrationsService {
  private readonly baseUrl = '/api/v1/integrations'

  // ========== GOOGLE API ==========

  async googleAuth(code: string, redirectUri: string): Promise<GoogleAuthResponse> {
    const response = await apiClient.post(`${this.baseUrl}/google/auth`, {
      code,
      redirect_uri: redirectUri,
    })
    return response.data
  }

  async listGoogleDriveFiles(
    accessToken: string,
    folderId?: string,
    maxResults: number = 100
  ): Promise<GoogleDriveFile[]> {
    const response = await apiClient.get(`${this.baseUrl}/google/drive/files`, {
      params: { access_token: accessToken, folder_id: folderId, max_results: maxResults },
    })
    return response.data.files
  }

  async downloadGoogleDriveFile(fileId: string, accessToken: string): Promise<any> {
    const response = await apiClient.get(
      `${this.baseUrl}/google/drive/files/${fileId}/download`,
      {
        params: { access_token: accessToken },
      }
    )
    return response.data
  }

  async getGoogleSheet(
    spreadsheetId: string,
    accessToken: string,
    range?: string
  ): Promise<GoogleSheetData> {
    const response = await apiClient.get(`${this.baseUrl}/google/sheets/${spreadsheetId}`, {
      params: { access_token: accessToken, range },
    })
    return response.data
  }

  async importGoogleSheet(
    spreadsheetId: string,
    accessToken: string,
    tableName: string,
    schema: string,
    range?: string
  ): Promise<{ status: string; message: string; rows_imported: number }> {
    const response = await apiClient.post(
      `${this.baseUrl}/google/sheets/${spreadsheetId}/import`,
      {
        access_token: accessToken,
        table_name: tableName,
        schema,
        range,
      }
    )
    return response.data
  }

  // ========== GROQ LLM ==========

  async groqChat(request: GroqChatRequest): Promise<GroqChatResponse> {
    const response = await apiClient.post(`${this.baseUrl}/groq/chat`, request)
    return response.data
  }

  async generateSQLFromNaturalLanguage(
    question: string,
    schemaContext?: string,
    model: string = 'llama3-70b-8192'
  ): Promise<GroqSQLResponse> {
    const response = await apiClient.post(`${this.baseUrl}/groq/sql/generate`, {
      question,
      schema_context: schemaContext,
      model,
    })
    return response.data
  }

  async explainSQL(
    sql: string,
    model: string = 'llama3-70b-8192'
  ): Promise<{ sql: string; explanation: string; complexity: string }> {
    const response = await apiClient.post(`${this.baseUrl}/groq/sql/explain`, {
      sql,
      model,
    })
    return response.data
  }

  async listGroqModels(): Promise<{ models: GroqModel[] }> {
    const response = await apiClient.get(`${this.baseUrl}/groq/models`)
    return response.data
  }

  // ========== CONFIGURATION STATUS ==========

  async getIntegrationsStatus(): Promise<{
    google: { configured: boolean; hasCredentials: boolean }
    groq: { configured: boolean; hasApiKey: boolean }
  }> {
    // Check if integrations are configured by trying to list models/check status
    try {
      const groqModels = await this.listGroqModels()
      return {
        google: {
          configured: false, // Would need backend endpoint to check
          hasCredentials: false,
        },
        groq: {
          configured: groqModels.models.length > 0,
          hasApiKey: groqModels.models.length > 0,
        },
      }
    } catch {
      return {
        google: { configured: false, hasCredentials: false },
        groq: { configured: false, hasApiKey: false },
      }
    }
  }
}

export const integrationsService = new IntegrationsService()
export default integrationsService
