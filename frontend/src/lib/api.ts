/**
 * API client — fetches from FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

async function fetchAPI<T>(
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<T> {
  const url = new URL(`${API_BASE}${endpoint}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) {
        url.searchParams.set(k, String(v))
      }
    })
  }
  const res = await fetch(url.toString())
  if (!res.ok) {
    throw new Error(`API Error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

async function postAPI(endpoint: string): Promise<any> {
  const res = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' })
  if (!res.ok) throw new Error(`API Error: ${res.status}`)
  return res.json()
}

// ── Types existants ────────────────────────────────────

export interface MacroData {
  series_id: string
  date: string
  value: number
}

export interface SectorData {
  symbol: string
  sector_name: string
  close_price: number
  sma_200: number | null
  relative_strength_30d: number | null
  above_sma200: boolean | null
  date: string
}

export interface StockFundamental {
  symbol: string
  period: string
  fiscal_date: string
  free_cash_flow: number | null
  roic: number | null
  operating_cash_flow: number | null
  capital_expenditures: number | null
  invested_capital: number | null
  company_name: string | null
  sector: string | null
}

export interface CryptoData {
  protocol: string
  tvl: number | null
  tvl_change_1d: number | null
  tvl_change_7d: number | null
  mcap: number | null
  fdv: number | null
  mcap_fdv_ratio: number | null
  fees_24h: number | null
  fees_7d: number | null
  revenue_24h: number | null
  chain: string | null
  category: string | null
  date: string
}

export interface InsiderTx {
  symbol: string
  company_name: string | null
  insider_name: string
  insider_title: string | null
  transaction_date: string | null
  transaction_code: string | null        // ex: "P" (Purchase), "S" (Sale), "A" (Award)
  acquired_disposed: 'A' | 'D' | null   // Acquired ou Disposed
  shares: number | null
  price_per_share: number | null
  total_value: number | null
  filing_date: string
  passed_filters: boolean | null
  alert_sent: boolean
  rejection_reason: string | null
}

export interface AlertLogEntry {
  id: string
  alert_type: string
  symbol: string
  trigger: string
  status: string
  details: string | null
  created_at: string | null
}

export interface SystemStatus {
  modules: Record<string, { records: number; last_update?: string }>
  alerts_total: number
}

// ── Nouveaux types (ideas, insiders scorés, alerts enrichies) ─────

export interface IdeaRanked {
  id: number
  symbol: string
  conviction_score: number
  risk_score: number
  recommended_action: string
  status: string
  thesis_summary: string
  pe_ttm: number | null
  roic: number | null
  free_cash_flow: number | null
  rev_cagr_3y: number | null
  market_cap: number | null
  sector: string | null
  sector_etf: string | null
  sector_above_sma200: boolean | null
  sector_rs30d: number | null
  yield_curve: number | null
  score_final_adjusted: number
  final_label: 'TOP_PICK' | 'WATCH' | 'HOLD'
  signal_label: string | null
  signal_strength: number | null
  filing_date: string | null
  entry_zone_min: number | null
  entry_zone_max: number | null
  target_price: number | null
  stop_loss: number | null
  created_at: string
}

export interface InsiderScored {
  symbol: string
  company_name: string
  insider_name: string
  insider_title: string
  transaction_code: string | null
  acquired_disposed: 'A' | 'D' | null
  total_value: number
  roic: number | null
  free_cash_flow: number | null
  pe_ttm: number | null
  sector: string | null
  insider_score: number
  signal_label: 'STRONG_BUY' | 'WATCH' | 'WEAK' | 'IGNORE'
  filing_date: string
}

// Enrichi côté backend (si tu as une vue dédiée)
export interface AlertEnriched extends AlertLogEntry {
  score?: number | null
  sector_name?: string | null
}

export interface AISummary {
  symbol: string
  moat: string[]
  risks: string[]
  catalysts: string[]
}

// ── API client ─────────────────────────────────────────

export const api = {
  // Statut système & macro
  getStatus: () => fetchAPI<SystemStatus>('/status'),
  getMacro: (params?: { series_id?: string; days?: string }) =>
    fetchAPI<MacroData[]>('/macro', params),
  getSectors: () => fetchAPI<SectorData[]>('/sectors'),

  // Fondamentaux actions / crypto
  getStock: (symbol: string) => fetchAPI<StockFundamental[]>(`/stocks/${symbol}`),
  getCrypto: (params?: { sort_by?: string; limit?: string }) =>
    fetchAPI<CryptoData[]>('/crypto', params),

  // Insiders brut
  getInsiders: (params?: { days?: string; min_amount?: string }) =>
    fetchAPI<InsiderTx[]>('/insiders', params),

  // Alertes brutes
  getAlerts: (params?: { alert_type?: string; status?: string; limit?: string }) =>
    fetchAPI<AlertLogEntry[]>('/alerts', params),

  // Idées (v_ideas_ranked)
  getIdeas: (params?: {
    label?: string
    sector?: string
    min_score?: number
    limit?: number
  }) =>
    fetchAPI<IdeaRanked[]>('/ideas', {
      label: params?.label,
      sector: params?.sector,
      min_score: params?.min_score,
      limit: params?.limit,
    }),

  getIdeaDetail: (id: number) =>
    fetchAPI<IdeaRanked & { signals: any[] }>(`/ideas/${id}`),

  // Insiders scorés (v_insider_scored)
  getInsidersScored: (params?: {
    min_score?: number
    days?: number
    min_amount?: number
  }) =>
    fetchAPI<InsiderScored[]>('/insiders/scored', {
      min_score: params?.min_score,
      days: params?.days,
      min_amount: params?.min_amount,
    }),

  // Alertes enrichies (score + secteur, pending_send, etc.)
  getAlertsEnriched: (params?: { status?: string; limit?: number }) =>
    fetchAPI<AlertEnriched[]>('/alerts/enriched', {
      status: params?.status,
      limit: params?.limit,
    }),
  // Résumé IA d'un ticker (Groq LLM)
  getAISummary: (symbol: string) =>
    fetchAPI<AISummary>(`/stocks/${symbol}/ai-summary`),
  

  // Triggers manuels
  triggerSyncMacro: () => postAPI('/trigger/sync-macro'),
  triggerSyncSectors: () => postAPI('/trigger/sync-sectors'),
  triggerSyncCrypto: () => postAPI('/trigger/sync-crypto'),
  triggerScanInsiders: () => postAPI('/trigger/scan-insiders'),
  triggerEquityAlerts: () => postAPI('/trigger/process-equity-alerts'),
  triggerCryptoAlerts: () => postAPI('/trigger/process-crypto-alerts'),
}
