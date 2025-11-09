/**
 * React Query Hooks for Compliance Service
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  complianceService,
  PIIDetectionRequest,
  PIIDetectionResponse,
  PIIMaskRequest,
  PolicyCreateRequest,
  Policy,
  ComplianceCheckRequest,
  ComplianceStats
} from '@/services/complianceService'

// Query keys
export const complianceKeys = {
  all: ['compliance'] as const,
  policies: () => [...complianceKeys.all, 'policies'] as const,
  policy: (name: string) => [...complianceKeys.policies(), name] as const,
  violations: () => [...complianceKeys.all, 'violations'] as const,
  stats: () => [...complianceKeys.all, 'stats'] as const,
}

/**
 * Hook to fetch all policies
 */
export function usePolicies(params?: {
  policy_type?: string
  enabled_only?: boolean
}) {
  return useQuery({
    queryKey: complianceKeys.policies(),
    queryFn: () => complianceService.listPolicies(params),
  })
}

/**
 * Hook to fetch a specific policy
 */
export function usePolicy(policyName: string) {
  return useQuery({
    queryKey: complianceKeys.policy(policyName),
    queryFn: () => complianceService.getPolicy(policyName),
    enabled: !!policyName,
  })
}

/**
 * Hook to fetch compliance statistics
 */
export function useComplianceStats() {
  return useQuery({
    queryKey: complianceKeys.stats(),
    queryFn: () => complianceService.getStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

/**
 * Hook to fetch violations
 */
export function useViolations(params?: {
  severity?: 'info' | 'warning' | 'error' | 'critical'
  limit?: number
}) {
  return useQuery({
    queryKey: [...complianceKeys.violations(), params],
    queryFn: () => complianceService.getViolations(params),
  })
}

/**
 * Hook to detect PII
 */
export function useDetectPII() {
  return useMutation({
    mutationFn: (request: PIIDetectionRequest) =>
      complianceService.detectPII(request),
  })
}

/**
 * Hook to mask PII
 */
export function useMaskPII() {
  return useMutation({
    mutationFn: (request: PIIMaskRequest) =>
      complianceService.maskPII(request),
  })
}

/**
 * Hook to create a policy
 */
export function useCreatePolicy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: PolicyCreateRequest) =>
      complianceService.createPolicy(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: complianceKeys.policies() })
    },
  })
}

/**
 * Hook to update a policy
 */
export function useUpdatePolicy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ name, updates }: { name: string; updates: any }) =>
      complianceService.updatePolicy(name, updates),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: complianceKeys.policy(variables.name) })
      queryClient.invalidateQueries({ queryKey: complianceKeys.policies() })
    },
  })
}

/**
 * Hook to delete a policy
 */
export function useDeletePolicy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (policyName: string) =>
      complianceService.deletePolicy(policyName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: complianceKeys.policies() })
    },
  })
}

/**
 * Hook to check compliance
 */
export function useCheckCompliance() {
  return useMutation({
    mutationFn: (request: ComplianceCheckRequest) =>
      complianceService.checkCompliance(request),
  })
}

/**
 * Hook to clear violations
 */
export function useClearViolations() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => complianceService.clearViolations(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: complianceKeys.violations() })
      queryClient.invalidateQueries({ queryKey: complianceKeys.stats() })
    },
  })
}
