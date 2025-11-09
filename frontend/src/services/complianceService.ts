/**
 * Compliance Service
 *
 * Handles PII detection, policy management, and compliance checking
 */

import apiClient from '@/lib/api'

export interface PIIDetectionRequest {
  text: string
  language?: string
  threshold?: number
  entities?: string[]
}

export interface PIIDetectionResult {
  entity_type: string
  text: string
  start: number
  end: number
  confidence: number
  context?: string
  metadata?: Record<string, any>
}

export interface PIIDetectionResponse {
  found_pii: boolean
  pii_count: number
  pii_types: string[]
  results: PIIDetectionResult[]
}

export interface PIIMaskRequest {
  text: string
  mask_char?: string
  anonymize?: boolean
}

export interface PIIMaskResponse {
  original_length: number
  masked_text: string
  pii_found: number
}

export interface PolicyCreateRequest {
  name: string
  policy_type: 'access_control' | 'data_retention' | 'pii_protection' | 'encryption' | 'audit' | 'custom'
  description: string
  template: 'no_pii' | 'no_empty_data' | 'max_length' | 'min_length' | 'contains_keyword' | 'not_contains_keyword' | 'regex_match'
  severity?: 'info' | 'warning' | 'error' | 'critical'
  parameters?: Record<string, any>
}

export interface Policy {
  name: string
  policy_type: string
  description: string
  severity: string
  enabled: boolean
  created_at: string
  metadata?: Record<string, any>
}

export interface PolicyListResponse {
  policies: Policy[]
  total: number
}

export interface PolicyUpdateRequest {
  enabled?: boolean
  description?: string
}

export interface ComplianceCheckRequest {
  data: string
  policy_names?: string[]
}

export interface ComplianceCheckResponse {
  compliant: boolean
  violations: Array<{
    policy_name: string
    severity: string
    description: string
    data_context?: string
    timestamp: string
    metadata?: Record<string, any>
  }>
  policies_checked: number
  timestamp: string
}

export interface Violation {
  policy_name: string
  severity: string
  description: string
  data_context?: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface ViolationListResponse {
  violations: Violation[]
  total: number
}

export interface ComplianceStats {
  total_policies: number
  enabled_policies: number
  disabled_policies: number
  total_violations: number
  violations_by_severity: Record<string, number>
  policies_by_type: Record<string, number>
  presidio_enabled: boolean
  supported_entities: number
}

class ComplianceService {
  /**
   * Detect PII in text
   */
  async detectPII(request: PIIDetectionRequest): Promise<PIIDetectionResponse> {
    const response = await apiClient.post<PIIDetectionResponse>(
      '/api/v1/compliance/detect-pii',
      request
    )
    return response.data
  }

  /**
   * Mask or anonymize PII in text
   */
  async maskPII(request: PIIMaskRequest): Promise<PIIMaskResponse> {
    const response = await apiClient.post<PIIMaskResponse>(
      '/api/v1/compliance/mask-pii',
      request
    )
    return response.data
  }

  /**
   * List all compliance policies
   */
  async listPolicies(params?: {
    policy_type?: string
    enabled_only?: boolean
  }): Promise<PolicyListResponse> {
    const response = await apiClient.get<PolicyListResponse>(
      '/api/v1/compliance/policies',
      { params }
    )
    return response.data
  }

  /**
   * Create a new policy from template
   */
  async createPolicy(request: PolicyCreateRequest): Promise<Policy> {
    const response = await apiClient.post<Policy>(
      '/api/v1/compliance/policies',
      request
    )
    return response.data
  }

  /**
   * Get a specific policy by name
   */
  async getPolicy(policyName: string): Promise<Policy> {
    const response = await apiClient.get<Policy>(
      `/api/v1/compliance/policies/${policyName}`
    )
    return response.data
  }

  /**
   * Update a policy
   */
  async updatePolicy(
    policyName: string,
    request: PolicyUpdateRequest
  ): Promise<Policy> {
    const response = await apiClient.put<Policy>(
      `/api/v1/compliance/policies/${policyName}`,
      request
    )
    return response.data
  }

  /**
   * Delete a policy
   */
  async deletePolicy(policyName: string): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(
      `/api/v1/compliance/policies/${policyName}`
    )
    return response.data
  }

  /**
   * Check data compliance against policies
   */
  async checkCompliance(request: ComplianceCheckRequest): Promise<ComplianceCheckResponse> {
    const response = await apiClient.post<ComplianceCheckResponse>(
      '/api/v1/compliance/check',
      request
    )
    return response.data
  }

  /**
   * Get recent policy violations
   */
  async getViolations(params?: {
    severity?: 'info' | 'warning' | 'error' | 'critical'
    limit?: number
  }): Promise<ViolationListResponse> {
    const response = await apiClient.get<ViolationListResponse>(
      '/api/v1/compliance/violations',
      { params }
    )
    return response.data
  }

  /**
   * Clear all recorded violations
   */
  async clearViolations(): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(
      '/api/v1/compliance/violations'
    )
    return response.data
  }

  /**
   * Get compliance system statistics
   */
  async getStats(): Promise<ComplianceStats> {
    const response = await apiClient.get<ComplianceStats>(
      '/api/v1/compliance/stats'
    )
    return response.data
  }

  /**
   * Helper: Check if text contains PII
   */
  async containsPII(text: string): Promise<boolean> {
    const result = await this.detectPII({ text })
    return result.found_pii
  }

  /**
   * Helper: Get a quick masked version of text
   */
  async quickMask(text: string, anonymize: boolean = false): Promise<string> {
    const result = await this.maskPII({ text, anonymize })
    return result.masked_text
  }

  /**
   * Helper: Validate data against all enabled policies
   */
  async validateData(data: string): Promise<{
    isValid: boolean
    violations: Violation[]
  }> {
    const result = await this.checkCompliance({ data })
    return {
      isValid: result.compliant,
      violations: result.violations,
    }
  }
}

export const complianceService = new ComplianceService()
