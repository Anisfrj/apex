import { useState, useMemo } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp, TrendingDown, Activity, Bell, Users,
  Target, Building2, Zap,
} from 'lucide-react'
import {
  useStatus, useMacro, useSectors, useInsiders, useAlerts, useIdeas,
} from '@/hooks/useData'
import { api } from '@/lib/api'
import type { IdeaRanked, InsiderScored, InsiderTx } from '@/lib/api'
import AISummaryCard from '@/components/AISummaryCard'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmtM(n: number | null | undefined): string {
  if (n == null) return '—'
  if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(1)}B`
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)}M`
  return n.toFixed(0)
}

type LabelKey = 'TOP_PICK' | 'WATCH' | 'HOLD'

function labelCfg(label: LabelKey) {
  const map = {
    TOP_PICK: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30', short: '🎯 TOP' },
    WATCH:    { bg: 'bg-amber-500/20',   text: 'text-amber-400',   border: 'border-amber-500/30',   short: '👁 WATCH' },
    HOLD:     { bg: 'bg-zinc-700/30',    text: 'text-zinc-400',    border: 'border-zinc-600/30',    short: '⏸ HOLD' },
  }
  return map[label]
}

function insiderSignalCfg(label: string) {
  if (label === 'STRONG_BUY') return { bg: 'bg-emerald-500/20', text: 'text-emerald-400', border: 'border-emerald-500/30' }
  if (label === 'WATCH')      return { bg: 'bg-amber-500/20',   text: 'text-amber-400',   border: 'border-amber-500/30' }
  return { bg: 'bg-zinc-700/30', text: 'text-zinc-400', border: 'border-zinc-600/30' }
}

function alertStatusCfg(status: string) {
  if (status === 'sent')            return 'bg-emerald-500/20 text-emerald-400'
  if (status.startsWith('rejected')) return 'bg-zinc-700/40 text-zinc-500'
  return 'bg-amber-500/20 text-amber-400'
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function KPICard({ label, value, color, sub, icon }: {
  label: string; value: string; color: string; sub: string; icon: ReactNode
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 px-3 py-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] text-zinc-500 uppercase tracking-wide">{label}</span>
        <span className="text-zinc-600">{icon}</span>
      </div>
      <div className={`text-lg font-mono font-bold ${color}`}>{value}</div>
      {sub && <div className="text-[10px] text-zinc-600 mt-0.5">{sub}</div>}
    </div>
  )
}

function MetricPill({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] text-zinc-600 uppercase tracking-wide">{label}</span>
      <span className={`text-xs font-mono font-semibold ${color}`}>{value}</span>
    </div>
  )
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [selectedTicker, setSelectedTicker] = useState<string>('AAPL')
  const [ideaFilter, setIdeaFilter]         = useState<'ALL' | LabelKey>('ALL')
  const [selectedIdea, setSelectedIdea]     = useState<IdeaRanked | null>(null)

  // ── Data hooks ─────────────────────────────────────────────────────────────
  const { data: statusData }  = useStatus()
  const { data: macroData }   = useMacro(undefined, 5)
  const { data: sectorsData } = useSectors()
  const { data: ideasData }   = useIdeas(undefined, 100)
  const { data: insidersData } = useInsiders(7, 250_000)
  const { data: alertsData }  = useAlerts(undefined, undefined, 15)

  // Insiders scorés (pas de hook dédié → useQuery direct)
  const { data: insidersScoredData } = useQuery({
    queryKey: ['insiders-scored', 7, 50_000, 30],
    queryFn: () => api.getInsidersScored({ days: 7, min_amount: 50_000, min_score: 30 }),
    staleTime: 5 * 60_000,
  })

  // ── Computed: Macro ─────────────────────────────────────────────────────────
  const macro = useMemo(() => {
    const out: Record<string, number | null> = { DFF: null, T10Y2Y: null }
    const seen = new Set<string>()
    for (const row of macroData ?? []) {
      if (!seen.has(row.series_id) && row.series_id in out) {
        out[row.series_id] = row.value
        seen.add(row.series_id)
      }
    }
    return out
  }, [macroData])

  // ── Computed: Sector breadth ────────────────────────────────────────────────
  const breadth = useMemo(() => {
    if (!sectorsData?.length) return { above: 0, total: 0, top: null as typeof sectorsData[0] | null, worst: null as typeof sectorsData[0] | null }
    const sorted = [...sectorsData].sort((a, b) => (b.relative_strength_30d ?? 0) - (a.relative_strength_30d ?? 0))
    return {
      above:  sectorsData.filter(s => s.above_sma200).length,
      total:  sectorsData.length,
      top:    sorted[0],
      worst:  sorted[sorted.length - 1],
    }
  }, [sectorsData])

  // ── Computed: Ideas filtered + sorted ──────────────────────────────────────
  const filteredIdeas = useMemo(() => {
    const list = !ideasData ? [] : ideaFilter === 'ALL' ? ideasData : ideasData.filter(i => i.final_label === ideaFilter)
    return [...list].sort((a, b) => b.score_final_adjusted - a.score_final_adjusted)
  }, [ideasData, ideaFilter])

  // ── Computed: dynamic ticker list (ideas + insiders) ───────────────────────
  const tickerList = useMemo(() => {
    const s = new Set<string>()
    ideasData?.forEach(i => s.add(i.symbol))
    insidersData?.forEach(i => s.add(i.symbol))
    return Array.from(s).sort()
  }, [ideasData, insidersData])

  // ── Computed: display insiders (scored preferred) ──────────────────────────
  type AnyInsider = InsiderScored | InsiderTx
  const displayInsiders: AnyInsider[] = useMemo(
    () => (insidersScoredData?.length ? insidersScoredData : insidersData ?? []),
    [insidersScoredData, insidersData],
  )

  // ── Counts ─────────────────────────────────────────────────────────────────
  const topPickCount  = ideasData?.filter(i => i.final_label === 'TOP_PICK').length ?? 0
  const watchCount    = ideasData?.filter(i => i.final_label === 'WATCH').length ?? 0
  const insiderCount  = insidersData?.length ?? 0
  const yieldInverted = macro.T10Y2Y !== null && macro.T10Y2Y < 0

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 p-4 space-y-4">

      {/* ═══════════════ HEADER ═══════════════ */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-sm font-black tracking-widest text-zinc-100 uppercase">APEX</span>
          <span className="text-xs text-zinc-600 tracking-wide">/ Intelligence Financière</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-500">
          <span>Stocks: <span className="text-zinc-300">{statusData?.modules?.stocks?.records ?? '—'}</span></span>
          <span>Insiders: <span className="text-zinc-300">{statusData?.modules?.insiders?.records ?? '—'}</span></span>
          <span>Alertes: <span className="text-zinc-300">{statusData?.alerts_total ?? '—'}</span></span>
          <span>{new Date().toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' })}</span>
        </div>
      </div>

      {/* ═══════════════ MARKET PULSE BAR ═══════════════ */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <KPICard
          label="Fed Rate"
          value={macro.DFF != null ? `${macro.DFF}%` : '—'}
          color="text-zinc-300"
          sub="DFF FRED"
          icon={<Activity size={13} />}
        />
        <KPICard
          label="Yield Curve"
          value={macro.T10Y2Y != null ? `${macro.T10Y2Y.toFixed(2)}%` : '—'}
          color={yieldInverted ? 'text-red-400' : 'text-emerald-400'}
          sub={yieldInverted ? '⚠ Inversée' : '10Y-2Y OK'}
          icon={yieldInverted ? <TrendingDown size={13} /> : <TrendingUp size={13} />}
        />
        <KPICard
          label="Breadth"
          value={breadth.total > 0 ? `${breadth.above}/${breadth.total}` : '—'}
          color={breadth.above >= 6 ? 'text-emerald-400' : breadth.above >= 4 ? 'text-amber-400' : 'text-red-400'}
          sub="secteurs SMA200"
          icon={<Building2 size={13} />}
        />
        <KPICard
          label="Top Secteur"
          value={breadth.top?.sector_name?.replace('Select Sector SPDR', '').replace('Fund', '').trim() ?? '—'}
          color="text-emerald-400"
          sub={breadth.top ? `RS ${(breadth.top.relative_strength_30d ?? 0).toFixed(1)}%` : ''}
          icon={<TrendingUp size={13} />}
        />
        <KPICard
          label="Retardataire"
          value={breadth.worst?.sector_name?.replace('Select Sector SPDR', '').replace('Fund', '').trim() ?? '—'}
          color="text-red-400"
          sub={breadth.worst ? `RS ${(breadth.worst.relative_strength_30d ?? 0).toFixed(1)}%` : ''}
          icon={<TrendingDown size={13} />}
        />
        <KPICard
          label="TOP PICK"
          value={String(topPickCount)}
          color="text-emerald-400"
          sub={`${watchCount} WATCH`}
          icon={<Target size={13} />}
        />
        <KPICard
          label="Insiders 7j"
          value={String(insiderCount)}
          color="text-amber-400"
          sub="achats >250k$"
          icon={<Users size={13} />}
        />
        <KPICard
          label="Alertes Total"
          value={String(statusData?.alerts_total ?? '—')}
          color="text-blue-400"
          sub="envoyées"
          icon={<Bell size={13} />}
        />
      </div>

      {/* ═══════════════ MAIN GRID — Screener + AI ═══════════════ */}
      <div className="grid grid-cols-12 gap-4">

        {/* ── SCREENER LIVE ── */}
        <div className="col-span-12 lg:col-span-5 rounded-xl border border-zinc-800 bg-zinc-900/60 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 shrink-0">
            <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
              <Zap size={14} className="text-amber-400" />
              APEX Screener
            </h2>
            <div className="flex gap-1">
              {(['ALL', 'TOP_PICK', 'WATCH', 'HOLD'] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setIdeaFilter(f)}
                  className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                    ideaFilter === f ? 'bg-zinc-700 text-zinc-100' : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {f === 'ALL' ? 'Tous' : f === 'TOP_PICK' ? '🎯' : f === 'WATCH' ? '👁' : '⏸'}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-y-auto flex-1" style={{ maxHeight: 420 }}>
            {!ideasData ? (
              <div className="flex items-center justify-center h-32 text-zinc-500 text-sm">Chargement…</div>
            ) : filteredIdeas.length === 0 ? (
              <div className="flex items-center justify-center h-32 text-zinc-500 text-sm">Aucun résultat</div>
            ) : (
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-zinc-900 border-b border-zinc-800 z-10">
                  <tr className="text-zinc-500">
                    <th className="text-left px-3 py-2">Ticker</th>
                    <th className="text-left px-2 py-2 hidden sm:table-cell">Secteur</th>
                    <th className="text-right px-2 py-2">Score</th>
                    <th className="text-center px-2 py-2">Label</th>
                    <th className="text-right px-2 py-2 hidden md:table-cell">ROIC</th>
                    <th className="text-right px-2 py-2 hidden md:table-cell">Target</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredIdeas.map(idea => {
                    const cfg       = labelCfg(idea.final_label)
                    const isActive  = idea.symbol === selectedTicker
                    return (
                      <tr
                        key={idea.id}
                        onClick={() => { setSelectedTicker(idea.symbol); setSelectedIdea(idea) }}
                        className={`cursor-pointer border-b border-zinc-800/50 transition-colors hover:bg-zinc-800/40 ${
                          isActive ? 'bg-zinc-800/60 border-l-2 border-l-emerald-500' : ''
                        }`}
                      >
                        <td className="px-3 py-2 font-mono font-semibold text-zinc-100">{idea.symbol}</td>
                        <td className="px-2 py-2 hidden sm:table-cell text-zinc-500 truncate max-w-[80px]">
                          {idea.sector?.split(' ')[0] ?? '—'}
                        </td>
                        <td className="px-2 py-2 text-right">
                          <span className={`font-mono font-semibold ${
                            idea.score_final_adjusted >= 70 ? 'text-emerald-400'
                            : idea.score_final_adjusted >= 50 ? 'text-amber-400'
                            : 'text-zinc-400'
                          }`}>
                            {idea.score_final_adjusted}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-center">
                          <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
                            {cfg.short}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-right hidden md:table-cell">
                          <span className={idea.roic != null && idea.roic > 15 ? 'text-emerald-400' : 'text-zinc-400'}>
                            {idea.roic != null ? `${idea.roic.toFixed(1)}%` : '—'}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-right hidden md:table-cell text-zinc-400">
                          {idea.target_price != null ? `$${idea.target_price.toFixed(0)}` : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* ── AI ANALYSIS PANEL ── */}
        <div className="col-span-12 lg:col-span-7 space-y-3">
          {/* Ticker header + selector + mini fundamentals */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 px-4 py-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-3">
                <span className="text-2xl font-mono font-black text-zinc-100">{selectedTicker}</span>
                {selectedIdea && (
                  <>
                    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-bold border ${
                      labelCfg(selectedIdea.final_label).bg
                    } ${labelCfg(selectedIdea.final_label).text} ${labelCfg(selectedIdea.final_label).border}`}>
                      {selectedIdea.final_label}
                    </span>
                    <span className="text-xs text-zinc-500">{selectedIdea.sector ?? ''}</span>
                  </>
                )}
              </div>
              <select
                value={selectedTicker}
                onChange={e => {
                  const sym = e.target.value
                  setSelectedTicker(sym)
                  setSelectedIdea(ideasData?.find(i => i.symbol === sym) ?? null)
                }}
                className="bg-zinc-800 border border-zinc-700 rounded-lg px-2 py-1.5 text-xs text-zinc-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              >
                {(tickerList.length > 0 ? tickerList : ['AAPL', 'MSFT', 'NVDA', 'META', 'GOOGL']).map(t => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            {selectedIdea && (
              <div className="mt-3 pt-3 border-t border-zinc-800 flex flex-wrap gap-5">
                <MetricPill
                  label="Score"
                  value={String(selectedIdea.score_final_adjusted)}
                  color={selectedIdea.score_final_adjusted >= 70 ? 'text-emerald-400' : 'text-amber-400'}
                />
                <MetricPill
                  label="ROIC"
                  value={selectedIdea.roic != null ? `${selectedIdea.roic.toFixed(1)}%` : '—'}
                  color={selectedIdea.roic != null && selectedIdea.roic > 15 ? 'text-emerald-400' : 'text-zinc-400'}
                />
                <MetricPill
                  label="FCF"
                  value={fmtM(selectedIdea.free_cash_flow)}
                  color="text-zinc-300"
                />
                <MetricPill
                  label="P/E TTM"
                  value={selectedIdea.pe_ttm != null ? selectedIdea.pe_ttm.toFixed(1) : '—'}
                  color="text-zinc-300"
                />
                <MetricPill
                  label="Rev CAGR 3Y"
                  value={selectedIdea.rev_cagr_3y != null ? `${selectedIdea.rev_cagr_3y.toFixed(1)}%` : '—'}
                  color={selectedIdea.rev_cagr_3y != null && selectedIdea.rev_cagr_3y > 10 ? 'text-emerald-400' : 'text-zinc-400'}
                />
                {selectedIdea.target_price != null && (
                  <MetricPill label="Target" value={`$${selectedIdea.target_price.toFixed(0)}`} color="text-blue-400" />
                )}
                {selectedIdea.stop_loss != null && (
                  <MetricPill label="Stop" value={`$${selectedIdea.stop_loss.toFixed(0)}`} color="text-red-400" />
                )}
                {selectedIdea.thesis_summary && (
                  <p className="w-full text-xs text-zinc-500 italic border-t border-zinc-800 pt-2 mt-1">
                    "{selectedIdea.thesis_summary}"
                  </p>
                )}
              </div>
            )}
          </div>

          {/* AI Summary Cards — AISummaryCard renders 3 sub-cards inside a fragment */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <AISummaryCard symbol={selectedTicker} />
          </div>
        </div>
      </div>

      {/* ═══════════════ BOTTOM GRID ═══════════════ */}
      <div className="grid grid-cols-12 gap-4">

        {/* ── INSIDERS ── */}
        <div className="col-span-12 lg:col-span-5 rounded-xl border border-zinc-800 bg-zinc-900/60 overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center gap-2">
            <Users size={14} className="text-amber-400" />
            <h2 className="text-sm font-semibold text-zinc-100">
              Insiders 7 jours <span className="text-zinc-500 font-normal text-xs">(&gt;250k$)</span>
            </h2>
          </div>
          <div className="overflow-y-auto" style={{ maxHeight: 280 }}>
            {displayInsiders.length === 0 ? (
              <div className="flex items-center justify-center h-24 text-zinc-500 text-sm">
                {!insidersData ? 'Chargement…' : 'Aucun insider'}
              </div>
            ) : (
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-zinc-900 border-b border-zinc-800 z-10">
                  <tr className="text-zinc-500">
                    <th className="text-left px-3 py-2">Ticker</th>
                    <th className="text-left px-2 py-2 hidden sm:table-cell">Nom</th>
                    <th className="text-right px-2 py-2">Montant</th>
                    <th className="text-center px-2 py-2">Signal</th>
                  </tr>
                </thead>
                <tbody>
                  {displayInsiders.slice(0, 15).map((tx, i) => {
                    const isScored     = 'insider_score' in tx
                    const signalLabel  = isScored ? (tx as InsiderScored).signal_label : null
                    const signalCfg    = signalLabel ? insiderSignalCfg(signalLabel) : null
                    return (
                      <tr
                        key={i}
                        onClick={() => setSelectedTicker(tx.symbol)}
                        className="cursor-pointer border-b border-zinc-800/50 hover:bg-zinc-800/40 transition-colors"
                      >
                        <td className="px-3 py-2 font-mono font-semibold text-zinc-100">{tx.symbol}</td>
                        <td className="px-2 py-2 hidden sm:table-cell text-zinc-500 truncate max-w-[110px]">
                          {tx.insider_name}
                        </td>
                        <td className="px-2 py-2 text-right text-amber-400 font-mono">
                          ${fmtM(tx.total_value ?? 0)}
                        </td>
                        <td className="px-2 py-2 text-center">
                          {signalCfg && signalLabel ? (
                            <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-bold border ${signalCfg.bg} ${signalCfg.text} ${signalCfg.border}`}>
                              {signalLabel}
                            </span>
                          ) : (
                            <span className="text-zinc-600 text-[10px]">
                              {'passed_filters' in tx && tx.passed_filters ? '✓' : '—'}
                            </span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* ── SECTORS RADAR ── */}
        <div className="col-span-12 lg:col-span-3 rounded-xl border border-zinc-800 bg-zinc-900/60 overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center gap-2">
            <Building2 size={14} className="text-blue-400" />
            <h2 className="text-sm font-semibold text-zinc-100">Radar Sectoriel</h2>
          </div>
          <div className="overflow-y-auto p-3 space-y-2" style={{ maxHeight: 280 }}>
            {!sectorsData ? (
              <div className="text-zinc-500 text-sm text-center py-8">Chargement…</div>
            ) : sectorsData.map(s => {
              const rs     = s.relative_strength_30d ?? 0
              const barPct = Math.min(100, Math.max(0, (rs + 20) * 2.5))
              const name   = s.sector_name.replace('Select Sector SPDR', '').replace('Fund', '').trim()
              return (
                <div key={s.symbol} className="flex flex-col gap-1">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-zinc-400 truncate max-w-[110px]">{name}</span>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-mono ${rs > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {rs > 0 ? '+' : ''}{rs.toFixed(1)}%
                      </span>
                      <span className={`h-1.5 w-1.5 rounded-full ${s.above_sma200 ? 'bg-emerald-400' : 'bg-red-400'}`} />
                    </div>
                  </div>
                  <div className="h-1 rounded-full bg-zinc-800">
                    <div
                      className={`h-full rounded-full transition-all ${rs > 0 ? 'bg-emerald-500/60' : 'bg-red-500/60'}`}
                      style={{ width: `${barPct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* ── ALERTS ── */}
        <div className="col-span-12 lg:col-span-4 rounded-xl border border-zinc-800 bg-zinc-900/60 overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center gap-2">
            <Bell size={14} className="text-blue-400" />
            <h2 className="text-sm font-semibold text-zinc-100">Alertes Récentes</h2>
          </div>
          <div className="overflow-y-auto" style={{ maxHeight: 280 }}>
            {!alertsData ? (
              <div className="flex items-center justify-center h-24 text-zinc-500 text-sm">Chargement…</div>
            ) : alertsData.length === 0 ? (
              <div className="flex items-center justify-center h-24 text-zinc-500 text-sm">Aucune alerte</div>
            ) : (
              <div className="divide-y divide-zinc-800/50">
                {alertsData.map(alert => (
                  <div key={alert.id} className="px-4 py-2.5 hover:bg-zinc-800/30 transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-zinc-100">{alert.symbol}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${alertStatusCfg(alert.status)}`}>
                          {alert.status}
                        </span>
                      </div>
                      <span className="text-[10px] text-zinc-600 shrink-0">
                        {alert.created_at
                          ? new Date(alert.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
                          : ''}
                      </span>
                    </div>
                    <p className="text-xs text-zinc-500 mt-0.5 truncate">{alert.trigger}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
