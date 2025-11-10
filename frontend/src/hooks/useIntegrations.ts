/**
 * Integrations Hooks
 *
 * React Query hooks for Google API and Groq LLM integrations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { integrationsService } from '@/services/integrationsService'
import type {
  GoogleDriveFile,
  GoogleSheetData,
  GroqChatRequest,
  GroqChatResponse,
  GroqSQLResponse,
  GroqModel,
} from '@/services/integrationsService'

// ============================================================================
// QUERY KEYS
// ============================================================================

export const integrationsKeys = {
  all: ['integrations'] as const,
  google: () => [...integrationsKeys.all, 'google'] as const,
  googleDrive: (accessToken: string) =>
    [...integrationsKeys.google(), 'drive', accessToken] as const,
  googleSheet: (spreadsheetId: string, accessToken: string) =>
    [...integrationsKeys.google(), 'sheet', spreadsheetId, accessToken] as const,
  groq: () => [...integrationsKeys.all, 'groq'] as const,
  groqModels: () => [...integrationsKeys.groq(), 'models'] as const,
  status: () => [...integrationsKeys.all, 'status'] as const,
}

// ============================================================================
// GOOGLE API HOOKS
// ============================================================================

export function useGoogleAuth() {
  return useMutation({
    mutationFn: ({ code, redirectUri }: { code: string; redirectUri: string }) =>
      integrationsService.googleAuth(code, redirectUri),
  })
}

export function useGoogleDriveFiles(accessToken: string, folderId?: string) {
  return useQuery({
    queryKey: integrationsKeys.googleDrive(accessToken),
    queryFn: () => integrationsService.listGoogleDriveFiles(accessToken, folderId),
    enabled: !!accessToken,
    staleTime: 60000, // 1 minute
  })
}

export function useDownloadGoogleDriveFile() {
  return useMutation({
    mutationFn: ({ fileId, accessToken }: { fileId: string; accessToken: string }) =>
      integrationsService.downloadGoogleDriveFile(fileId, accessToken),
  })
}

export function useGoogleSheet(spreadsheetId: string, accessToken: string, range?: string) {
  return useQuery({
    queryKey: integrationsKeys.googleSheet(spreadsheetId, accessToken),
    queryFn: () => integrationsService.getGoogleSheet(spreadsheetId, accessToken, range),
    enabled: !!spreadsheetId && !!accessToken,
    staleTime: 60000, // 1 minute
  })
}

export function useImportGoogleSheet() {
  return useMutation({
    mutationFn: ({
      spreadsheetId,
      accessToken,
      tableName,
      schema,
      range,
    }: {
      spreadsheetId: string
      accessToken: string
      tableName: string
      schema: string
      range?: string
    }) =>
      integrationsService.importGoogleSheet(
        spreadsheetId,
        accessToken,
        tableName,
        schema,
        range
      ),
  })
}

// ============================================================================
// GROQ LLM HOOKS
// ============================================================================

export function useGroqChat() {
  return useMutation({
    mutationFn: (request: GroqChatRequest) => integrationsService.groqChat(request),
  })
}

export function useGenerateSQLFromNL() {
  return useMutation({
    mutationFn: ({
      question,
      schemaContext,
      model,
    }: {
      question: string
      schemaContext?: string
      model?: string
    }) => integrationsService.generateSQLFromNaturalLanguage(question, schemaContext, model),
  })
}

export function useExplainSQL() {
  return useMutation({
    mutationFn: ({ sql, model }: { sql: string; model?: string }) =>
      integrationsService.explainSQL(sql, model),
  })
}

export function useGroqModels() {
  return useQuery({
    queryKey: integrationsKeys.groqModels(),
    queryFn: () => integrationsService.listGroqModels(),
    staleTime: Infinity, // Models don't change frequently
  })
}

// ============================================================================
// STATUS HOOKS
// ============================================================================

export function useIntegrationsStatus() {
  return useQuery({
    queryKey: integrationsKeys.status(),
    queryFn: () => integrationsService.getIntegrationsStatus(),
    staleTime: 30000, // 30 seconds
  })
}
