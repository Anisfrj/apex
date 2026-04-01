import { useState } from 'react'
import {
  useStatus,
  useMacro,
  useSectors,
  useInsiders,
  useAlerts,
  useIdeas,
} from '@/hooks/useData'
import { LoadingSpinner, ErrorState } from '@/components/LoadingState'
import StatusBadge from '@/components/StatusBadge'
import {
  Activity,
  Database,
  Bell,
  TrendingUp,
  TrendingDown,
  Star,
} from 'lucide-react'
import AISummaryCard from '@/components/AISummaryCard'

function formatNum(n: number | null | undefined): string {
  if (n == null) return '\u2014'
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(1)}B`
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(1)}K`
  return `$${n.toFixed(0)}`
}

const TOP_PICK_SCORE_THRESHOLD = 75

export default function Dashboard() {
  const [selectedTicker, setSelectedTicker] = useState<string>('AAPL')
  const status = useStatus()
  const macro = useMacro(undefined, 30)
  const sectors = useSectors()
  const insiders = useInsiders(7, 250000)
  const alerts = useAlerts(undefined, undefined, 10)
  const ideas = useIdeas(undefined, 10)

  if (status.isLoading) return <LoadingSpinner />
  if (status.error) return <ErrorState message="Erreur chargement statut systeme" />

  const statusData = status.data
  const macroData = macro.data || []
  const sectorData = sectors.data || []
  const insiderData = insiders.data || []
  const alertData = alerts.data || []
  const ideasData = ideas.data || []

  const latestDFF = macroData.find(d => d.series_id === 'DFF')
  const latestT10Y2Y = macroData.find(d => d.series_id === 'T10Y2Y')
  const latestM2 = macroData.find(d => d.series_id === 'WM2NS')
  const sectorsAbove = sectorData.filter(s => s.above_sma200 === true).length
  const sectorsTotal = sectorData.length
  const topPicks = ideasData.filter(i => (i.score_final_adjusted ?? 0) >= TOP_PICK_SCORE_THRESHOLD)
  const topPicksCount = topPicks.length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Vue Globale</h2>
          <p className="text-xs text-zinc-500 mt-0.5">Synthese du cockpit d'analyse</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-xs text-zinc-500">
            <Activity className="w-3 h-3" />
            Auto-refresh 60s
          </span>
        </div>
      </div>

      {/* AI Executive Summary */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-zinc-200">AI Executive Summary</h2>
          <select
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value)}
            className="ml-auto bg-zinc-800 border border-zinc-700 text-zinc-300 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-zinc-500"
          >
            {['AAPL', 'MSFT', 'NVDA', 'META', 'GOOGL', 'AMZN'].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <AISummaryCard symbol={selectedTicker} />
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-5 gap-4">
        <div className="card">
          <div className="card-header">Fed Funds Rate</div>
          <div className="stat-value">
            {latestDFF ? `${latestDFF.value.toFixed(2)}%` : '\u2014'}
          </div>
          <div className="stat-label">Taux directeur</div>
        </div>
        <div className="card">
          <div className="card-header">Courbe des Taux</div>
          <div className="stat-value">
            {latestT10Y2Y ? (
              <span className={latestT10Y2Y.value < 0 ? 'text-red-400' : 'text-emerald-400'}>
                {latestT10Y2Y.value.toFixed(2)}%
              </span>
            ) : '\u2014'}
          </div>
          <div className="stat-label">
            10Y-2Y Spread {latestT10Y2Y?.value && latestT10Y2Y.value < 0 ? '(Inversee)' : ''}
          </div>
        </div>
        <div className="card">
          <div className="card-header">Secteurs MM200</div>
          <div className="stat-value">
            <span className={sectorsAbove > sectorsTotal / 2 ? 'text-emerald-400' : 'text-amber-400'}>
              {sectorsAbove}/{sectorsTotal}
            </span>
          </div>
          <div className="stat-label">Tendance sectorielle</div>
        </div>
        <div className="card">
          <div className="card-header">Alertes Envoyees</div>
          <div className="stat-value">{statusData?.alerts_total ?? '\u2014'}</div>
          <div className="stat-label">Total historique</div>
        </div>
        <div className="card">
          <div className="card-header flex items-center gap-1">
            <Star className="w-3 h-3 text-amber-400" />
            Top Picks
          </div>
          <div className="stat-value text-amber-400">{topPicksCount}</div>
          <div className="stat-label">Score superieur a {TOP_PICK_SCORE_THRESHOLD}</div>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-2 gap-4">
        {/* Sector Radar */}
        <div className="card">
          <div className="card-header flex items-center justify-between">
            <span>Radar Sectoriel</span>
            <span className="text-[10px] text-zinc-600 normal-case tracking-normal">Force Relative 30j</span>
          </div>
          <div className="space-y-1.5">
            {sectorData.slice(0, 6).map(s => (
              <div key={s.symbol} className="flex items-center justify-between py-1">
                <div className="flex items-center gap-2">
                  <StatusBadge status={s.above_sma200} trueLabel="up" falseLabel="dn" />
                  <span className="text-xs text-zinc-300 font-medium">{s.symbol}</span>
                  <span className="text-[10px] text-zinc-500">{s.sector_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-zinc-400">
                    RS: {s.relative_strength_30d?.toFixed(3) ?? '\u2014'}
                  </span>
                  {(s.relative_strength_30d ?? 0) > 1 ? (
                    <TrendingUp className="w-3 h-3 text-emerald-400" />
                  ) : (
                    <TrendingDown className="w-3 h-3 text-red-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Picks */}
        <div className="card">
          <div className="card-header flex items-center gap-2">
            <Star className="w-3 h-3 text-amber-400" />
            Top Picks
          </div>
          {topPicks.length === 0 ? (
            <p className="text-xs text-zinc-500 py-4 text-center">Aucune idee au-dessus du seuil</p>
          ) : (
            <div className="space-y-2">
              {topPicks.slice(0, 5).map((idea, i) => (
                <div key={idea.id ?? i} className="flex items-center justify-between py-1 border-b border-zinc-800/30 last:border-0">
                  <div className="flex flex-col">
                    <span className="text-xs font-medium text-zinc-200">{idea.symbol}</span>
                    <span className="text-[10px] text-zinc-500">{idea.sector ?? '\u2014'}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-amber-400">
                      {idea.score_final_adjusted?.toFixed(1) ?? '\u2014'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent Alerts */}
      <div className="card">
        <div className="card-header flex items-center gap-2">
          <Bell className="w-3 h-3" />
          Dernieres Alertes
        </div>
        {alertData.length === 0 ? (
          <p className="text-xs text-zinc-500 py-4 text-center">Aucune alerte enregistree</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 border-b border-zinc-800">
                  <th className="text-left py-2 font-medium">Type</th>
                  <th className="text-left py-2 font-medium">Symbole</th>
                  <th className="text-left py-2 font-medium">Declencheur</th>
                  <th className="text-left py-2 font-medium">Statut</th>
                  <th className="text-left py-2 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {alertData.map(a => (
                  <tr key={a.id} className="table-row">
                    <td className="py-2">
                      <span className={a.alert_type === 'equity' ? 'badge-blue' : 'badge-yellow'}>
                        {a.alert_type}
                      </span>
                    </td>
                    <td className="py-2 font-mono text-zinc-300">{a.symbol}</td>
                    <td className="py-2 text-zinc-400">{a.trigger}</td>
                    <td className="py-2">
                      <span className={
                        a.status === 'sent' ? 'badge-green' :
                        a.status === 'pending_send' ? 'badge-amber' :
                        a.status.startsWith('rejected') ? 'badge-red' : 'badge-yellow'
                      }>
                        {a.status}
                      </span>
                    </td>
                    <td className="py-2 text-zinc-500">
                      {a.created_at ? new Date(a.created_at).toLocaleString('fr-FR') : '\u2014'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* System Status */}
      <div className="card">
        <div className="card-header flex items-center gap-2">
          <Database className="w-3 h-3" />
          Etat du Systeme
        </div>
        {statusData && (
          <div className="grid grid-cols-5 gap-3">
            {Object.entries(statusData.modules).map(([key, mod]) => (
              <div key={key} className="bg-surface-3 rounded-md p-3">
                <p className="text-[10px] text-zinc-500 uppercase">{key}</p>
                <p className="text-sm font-mono text-zinc-200 mt-1">{mod.records}</p>
                {mod.last_update && mod.last_update !== 'None' && (
                  <p className="text-[10px] text-zinc-600 mt-0.5 truncate">{mod.last_update}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
