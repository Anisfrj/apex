// frontend/src/pages/IdeasPage.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, IdeaRanked } from '../lib/api'

const LABEL_CONFIG = {
  TOP_PICK: { color: 'text-orange-400 bg-orange-400/10 border-orange-400/30', icon: '🔥', label: 'TOP PICK' },
  WATCH:    { color: 'text-blue-400 bg-blue-400/10 border-blue-400/30',       icon: '👀', label: 'WATCH' },
  HOLD:     { color: 'text-gray-400 bg-gray-400/10 border-gray-400/30',       icon: '⏸', label: 'HOLD' },
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 90 ? 'bg-orange-500' : score >= 75 ? 'bg-blue-500' : 'bg-gray-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-white font-mono text-sm font-bold">{score}</span>
    </div>
  )
}

function IdeaDetailModal({ idea, onClose }: { idea: IdeaRanked & { signals?: any[] }; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-white font-bold text-2xl font-mono">{idea.symbol}</span>
              <span className={`text-xs px-2 py-1 rounded border font-bold ${LABEL_CONFIG[idea.final_label].color}`}>
                {LABEL_CONFIG[idea.final_label].icon} {LABEL_CONFIG[idea.final_label].label}
              </span>
            </div>
            <p className="text-gray-400 text-sm mt-1">{idea.sector ?? '—'} {idea.sector_etf ? `· ${idea.sector_etf}` : ''}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl">✕</button>
        </div>

        <div className="p-6 space-y-6">
          {/* Scores */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <p className="text-gray-400 text-xs mb-1">Score Final</p>
              <p className="text-orange-400 font-bold text-2xl">{idea.score_final_adjusted}</p>
              <p className="text-gray-500 text-xs">/100</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <p className="text-gray-400 text-xs mb-1">Conviction</p>
              <p className="text-blue-400 font-bold text-2xl">{idea.conviction_score}</p>
              <p className="text-gray-500 text-xs">/100</p>
            </div>
            <div className="bg-gray-800 rounded-lg p-4 text-center">
              <p className="text-gray-400 text-xs mb-1">Risque</p>
              <p className={`font-bold text-2xl ${(idea.risk_score ?? 0) >= 60 ? 'text-red-400' : 'text-green-400'}`}>
                {idea.risk_score}
              </p>
              <p className="text-gray-500 text-xs">/100</p>
            </div>
          </div>

          {/* Thèse */}
          <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
            <p className="text-gray-400 text-xs font-bold uppercase mb-2">📋 Thèse</p>
            <p className="text-gray-200 text-sm leading-relaxed">{idea.thesis_summary}</p>
          </div>

          {/* Fondamentaux */}
          <div>
            <p className="text-gray-400 text-xs font-bold uppercase mb-3">📊 Fondamentaux</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'PE TTM',       value: idea.pe_ttm?.toFixed(1) ?? 'N/A' },
                { label: 'ROIC',         value: idea.roic != null ? `${idea.roic.toFixed(1)}%` : 'N/A' },
                { label: 'FCF',          value: idea.free_cash_flow != null ? `$${(idea.free_cash_flow / 1e6).toFixed(1)}M` : 'N/A' },
                { label: 'Rev CAGR 3y',  value: idea.rev_cagr_3y != null ? `${idea.rev_cagr_3y.toFixed(1)}%` : 'N/A' },
                { label: 'Market Cap',   value: idea.market_cap != null ? `$${(idea.market_cap / 1e6).toFixed(0)}M` : 'N/A' },
                { label: 'Action',       value: (idea.recommended_action ?? '—').toUpperCase() },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between bg-gray-800 rounded px-3 py-2">
                  <span className="text-gray-400 text-sm">{label}</span>
                  <span className="text-white text-sm font-mono font-bold">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Contexte marché */}
          <div>
            <p className="text-gray-400 text-xs font-bold uppercase mb-3">🌍 Contexte Marché</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex justify-between bg-gray-800 rounded px-3 py-2">
                <span className="text-gray-400 text-sm">Secteur SMA200</span>
                <span className={`text-sm font-bold ${idea.sector_above_sma200 ? 'text-green-400' : 'text-red-400'}`}>
                  {idea.sector_above_sma200 ? '✅ Au-dessus' : '❌ En-dessous'}
                </span>
              </div>
              <div className="flex justify-between bg-gray-800 rounded px-3 py-2">
                <span className="text-gray-400 text-sm">RS 30j</span>
                <span className="text-white text-sm font-mono font-bold">
                  {idea.sector_rs30d?.toFixed(4) ?? 'N/A'}
                </span>
              </div>
              <div className="flex justify-between bg-gray-800 rounded px-3 py-2">
                <span className="text-gray-400 text-sm">Yield Curve</span>
                <span className={`text-sm font-bold ${(idea.yield_curve ?? 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {idea.yield_curve?.toFixed(2) ?? 'N/A'}%
                </span>
              </div>
              <div className="flex justify-between bg-gray-800 rounded px-3 py-2">
                <span className="text-gray-400 text-sm">Signal</span>
                <span className="text-orange-400 text-sm font-bold">{idea.signal_label ?? 'N/A'}</span>
              </div>
            </div>
          </div>

          {/* Entry / Target / SL */}
          {(idea.entry_zone_min || idea.target_price || idea.stop_loss) && (
            <div>
              <p className="text-gray-400 text-xs font-bold uppercase mb-3">🎯 Niveaux de Prix</p>
              <div className="grid grid-cols-3 gap-3">
                {idea.entry_zone_min && (
                  <div className="bg-blue-900/30 border border-blue-700/40 rounded px-3 py-2 text-center">
                    <p className="text-blue-400 text-xs">Entrée</p>
                    <p className="text-white font-bold">${idea.entry_zone_min} – ${idea.entry_zone_max}</p>
                  </div>
                )}
                {idea.target_price && (
                  <div className="bg-green-900/30 border border-green-700/40 rounded px-3 py-2 text-center">
                    <p className="text-green-400 text-xs">Target</p>
                    <p className="text-white font-bold">${idea.target_price}</p>
                  </div>
                )}
                {idea.stop_loss && (
                  <div className="bg-red-900/30 border border-red-700/40 rounded px-3 py-2 text-center">
                    <p className="text-red-400 text-xs">Stop Loss</p>
                    <p className="text-white font-bold">${idea.stop_loss}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function IdeaRow({ idea, onClick }: { idea: IdeaRanked; onClick: () => void }) {
  const cfg = LABEL_CONFIG[idea.final_label]
  return (
    <tr
      className="border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer transition-colors"
      onClick={onClick}
    >
      <td className="px-4 py-3">
        <span className="text-white font-bold font-mono">{idea.symbol}</span>
      </td>
      <td className="px-4 py-3">
        <span className={`text-xs px-2 py-1 rounded border font-bold ${cfg.color}`}>
          {cfg.icon} {cfg.label}
        </span>
      </td>
      <td className="px-4 py-3">
        <ScoreBar score={idea.score_final_adjusted} />
      </td>
      <td className="px-4 py-3 text-gray-300 text-sm">
        {idea.sector ?? '—'}
        {idea.sector_etf && <span className="text-gray-500 ml-1">({idea.sector_etf})</span>}
      </td>
      <td className="px-4 py-3 font-mono text-sm">
        {idea.pe_ttm != null
          ? <span className={idea.pe_ttm < 15 ? 'text-green-400' : idea.pe_ttm > 30 ? 'text-red-400' : 'text-gray-300'}>
              {idea.pe_ttm.toFixed(1)}x
            </span>
          : <span className="text-gray-600">N/A</span>
        }
      </td>
      <td className="px-4 py-3 font-mono text-sm">
        {idea.roic != null
          ? <span className={idea.roic >= 10 ? 'text-green-400' : 'text-red-400'}>
              {idea.roic.toFixed(1)}%
            </span>
          : <span className="text-gray-600">N/A</span>
        }
      </td>
      <td className="px-4 py-3 font-mono text-sm">
        {idea.free_cash_flow != null
          ? <span className={idea.free_cash_flow >= 0 ? 'text-green-400' : 'text-red-400'}>
              ${(idea.free_cash_flow / 1e6).toFixed(1)}M
            </span>
          : <span className="text-gray-600">N/A</span>
        }
      </td>
      <td className="px-4 py-3">
        <span className={`text-xs font-bold ${idea.sector_above_sma200 ? 'text-green-400' : 'text-red-400'}`}>
          {idea.sector_above_sma200 == null ? '—' : idea.sector_above_sma200 ? '✅' : '❌'}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className="text-green-400 text-xs font-bold uppercase">
          {idea.recommended_action ?? '—'}
        </span>
      </td>
    </tr>
  )
}

export default function IdeasPage() {
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null)
  const [selectedIdea, setSelectedIdea] = useState<IdeaRanked | null>(null)
  const [minScore, setMinScore] = useState(0)

  const { data: ideas = [], isLoading } = useQuery({
    queryKey: ['ideas', selectedLabel, minScore],
    queryFn: () => api.getIdeas({
      label: selectedLabel ?? undefined,
      min_score: minScore
    }),
    refetchInterval: 60_000
  })

  const { data: ideaDetail } = useQuery({
    queryKey: ['idea-detail', selectedIdea?.id],
    queryFn: () => selectedIdea ? api.getIdeaDetail(selectedIdea.id) : null,
    enabled: !!selectedIdea
  })

  const counts = {
    TOP_PICK: ideas.filter(i => i.final_label === 'TOP_PICK').length,
    WATCH:    ideas.filter(i => i.final_label === 'WATCH').length,
    HOLD:     ideas.filter(i => i.final_label === 'HOLD').length,
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-white text-2xl font-bold">Ideas & Opportunités</h1>
        <p className="text-gray-400 text-sm">Dossiers d'investissement consolidés — Score multi-facteurs</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'TOP PICKS', count: counts.TOP_PICK, color: 'text-orange-400', bg: 'border-orange-400/20' },
          { label: 'WATCH',     count: counts.WATCH,    color: 'text-blue-400',   bg: 'border-blue-400/20' },
          { label: 'HOLD',      count: counts.HOLD,     color: 'text-gray-400',   bg: 'border-gray-400/20' },
        ].map(({ label, count, color, bg }) => (
          <button
            key={label}
            onClick={() => setSelectedLabel(selectedLabel === label.replace(' ', '_') ? null : label.replace(' ', '_'))}
            className={`bg-gray-900 border ${bg} rounded-xl p-5 text-left hover:bg-gray-800 transition-colors ${
              selectedLabel === label.replace(' ', '_') ? 'ring-1 ring-white/20' : ''
            }`}
          >
            <p className="text-gray-400 text-xs uppercase font-bold">{label}</p>
            <p className={`${color} text-4xl font-bold mt-1`}>{count}</p>
          </button>
        ))}
      </div>

      {/* Filtres */}
      <div className="flex items-center gap-4">
        <div className="flex gap-2">
          {[
            { key: null,       label: 'Tous' },
            { key: 'TOP_PICK', label: '🔥 Top Picks' },
            { key: 'WATCH',    label: '👀 Watch' },
            { key: 'HOLD',     label: '⏸ Hold' },
          ].map(({ key, label }) => (
            <button
              key={String(key)}
              onClick={() => setSelectedLabel(key)}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                selectedLabel === key
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Score minimum slider */}
        <div className="flex items-center gap-3 ml-auto">
          <span className="text-gray-400 text-sm">Score min :</span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            className="w-32 accent-blue-500"
          />
          <span className="text-white font-mono text-sm w-8">{minScore}</span>
        </div>
      </div>

      {/* Tableau */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-gray-400">
            Chargement...
          </div>
        ) : ideas.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-gray-500">
            Aucune idea trouvée
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-800/50">
                {[
                  'Symbole', 'Label', 'Score', 'Secteur',
                  'PE', 'ROIC', 'FCF', 'SMA200', 'Action'
                ].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-gray-400 text-xs font-bold uppercase">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ideas.map(idea => (
                <IdeaRow
                  key={idea.id}
                  idea={idea}
                  onClick={() => setSelectedIdea(idea)}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal détail */}
      {selectedIdea && ideaDetail && (
        <IdeaDetailModal
          idea={ideaDetail}
          onClose={() => setSelectedIdea(null)}
        />
      )}
    </div>
  )
}
