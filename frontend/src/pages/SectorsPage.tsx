import { useSectors } from '@/hooks/useData'
import { LoadingSpinner, ErrorState, EmptyState } from '@/components/LoadingState'
import StatusBadge from '@/components/StatusBadge'
import { TrendingUp, TrendingDown } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

export default function SectorsPage() {
  const { data, isLoading, error } = useSectors()

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorState message="Erreur chargement données sectorielles" />
  if (!data?.length) return <EmptyState message="Aucune donnée sectorielle — lancez la synchro secteurs" />

  const chartData = data.map(s => ({
    symbol: s.symbol,
    rs: s.relative_strength_30d ?? 0,
    above: s.above_sma200,
  }))

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-zinc-100">Radar Sectoriel</h2>
        <p className="text-xs text-zinc-500 mt-0.5">ETF GICS — Force Relative 30j vs SPY + MM200</p>
      </div>

      {/* RS Bar Chart */}
      <div className="card">
        <div className="card-header">Force Relative vs S&P 500 (30 jours)</div>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 10, fill: '#71717a' }}
              domain={['dataMin - 0.02', 'dataMax + 0.02']}
            />
            <YAxis
              type="category"
              dataKey="symbol"
              tick={{ fontSize: 11, fill: '#a1a1aa', fontFamily: 'JetBrains Mono' }}
              width={50}
            />
            <Tooltip
              contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '6px', fontSize: '12px' }}
              formatter={(value: number) => [value.toFixed(4), 'Force Relative']}
            />
            <Bar dataKey="rs" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.rs > 1 ? '#22c55e' : entry.rs > 0.98 ? '#f59e0b' : '#ef4444'}
                  fillOpacity={0.7}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="flex items-center gap-4 mt-2 text-[10px] text-zinc-500">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> RS {"> "}1 = Surperformance</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500 inline-block" /> RS ~1 = Neutre</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500 inline-block" /> RS {"< "}1 = Sous-performance</span>
        </div>
      </div>

      {/* Sector Table */}
      <div className="card">
        <div className="card-header">Détails par Secteur</div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-zinc-500 border-b border-zinc-800">
                <th className="text-left py-2 font-medium">ETF</th>
                <th className="text-left py-2 font-medium">Secteur</th>
                <th className="text-right py-2 font-medium">Prix</th>
                <th className="text-right py-2 font-medium">MM200</th>
                <th className="text-center py-2 font-medium">{">"} MM200</th>
                <th className="text-right py-2 font-medium">Force Relative</th>
                <th className="text-center py-2 font-medium">Tendance</th>
                <th className="text-right py-2 font-medium">Date</th>
              </tr>
            </thead>
            <tbody>
              {data.map(s => (
                <tr key={s.symbol} className="table-row">
                  <td className="py-2.5 font-mono font-medium text-zinc-200">{s.symbol}</td>
                  <td className="py-2.5 text-zinc-400">{s.sector_name}</td>
                  <td className="py-2.5 text-right font-mono text-zinc-300">
                    ${s.close_price?.toFixed(2)}
                  </td>
                  <td className="py-2.5 text-right font-mono text-zinc-400">
                    {s.sma_200 ? `$${s.sma_200.toFixed(2)}` : '—'}
                  </td>
                  <td className="py-2.5 text-center">
                    <StatusBadge status={s.above_sma200} />
                  </td>
                  <td className="py-2.5 text-right font-mono">
                    <span className={(s.relative_strength_30d ?? 0) > 1 ? 'text-emerald-400' : 'text-red-400'}>
                      {s.relative_strength_30d?.toFixed(4) ?? '—'}
                    </span>
                  </td>
                  <td className="py-2.5 text-center">
                    {(s.relative_strength_30d ?? 0) > 1 ? (
                      <TrendingUp className="w-3.5 h-3.5 text-emerald-400 inline" />
                    ) : (
                      <TrendingDown className="w-3.5 h-3.5 text-red-400 inline" />
                    )}
                  </td>
                  <td className="py-2.5 text-right text-zinc-500">{s.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
