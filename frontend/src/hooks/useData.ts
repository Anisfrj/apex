/**
 * TanStack Query hooks for all data modules.
 */

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export function useStatus() {
  return useQuery({
    queryKey: ['status'],
    queryFn: api.getStatus,
    refetchInterval: 30_000,
  })
}

export function useMacro(seriesId?: string, days: number = 90) {
  return useQuery({
    queryKey: ['macro', seriesId, days],
    queryFn: () => api.getMacro({
      ...(seriesId ? { series_id: seriesId } : {}),
      days: String(days),
    }),
  })
}

export function useSectors() {
  return useQuery({
    queryKey: ['sectors'],
    queryFn: api.getSectors,
  })
}

export function useCrypto(sortBy: string = 'tvl', limit: number = 50) {
  return useQuery({
    queryKey: ['crypto', sortBy, limit],
    queryFn: () => api.getCrypto({ sort_by: sortBy, limit: String(limit) }),
  })
}

/** Insiders bruts — /api/insiders (pas de score) */
export function useInsiders(days: number = 7, minAmount: number = 0) {
  return useQuery({
    queryKey: ['insiders', days, minAmount],
    queryFn: () => api.getInsiders({
      days: String(days),
      min_amount: String(minAmount),
    }),
  })
}

/** Insiders scorés — /api/insiders/scored (avec insider_score + signal_label) */
export function useInsidersScored(
  minScore: number = 30,
  days: number = 7,
  minAmount: number = 50_000,
) {
  return useQuery({
    queryKey: ['insiders-scored', minScore, days, minAmount],
    queryFn: () => api.getInsidersScored({
      min_score: minScore,
      days,
      min_amount: minAmount,
    }),
    staleTime: 60_000,
  })
}

export function useAlerts(alertType?: string, status?: string, limit: number = 50) {
  return useQuery({
    queryKey: ['alerts', alertType, status, limit],
    queryFn: () => api.getAlerts({
      ...(alertType ? { alert_type: alertType } : {}),
      ...(status ? { status } : {}),
      limit: String(limit),
    }),
  })
}

import type { IdeaRanked } from '@/lib/api'

export function useIdeas(label?: string, limit: number = 10) {
  return useQuery<IdeaRanked[]>({
    queryKey: ['ideas', { label, limit }],
    queryFn: () =>
      api.getIdeas({
        label,
        limit,
      }),
    staleTime: 60_000,
  })
}
export function useAISummary(symbol: string) {
  return useQuery({
    queryKey: ['ai-summary', symbol],
    queryFn: () => api.getAISummary(symbol),
    enabled: !!symbol,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })
}
