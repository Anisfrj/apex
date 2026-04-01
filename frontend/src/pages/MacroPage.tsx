import { useState } from 'react'
import { useMacro } from '@/hooks/useData'
import { LoadingSpinner, ErrorState, EmptyState } from '@/components/LoadingState'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

const SERIES_INFO: Record<string, { label: string; color: string; description: string }> = {
  DFF: {
    label: 'Fed Funds Rate',
    color: '#0ea5e9',
    description: 'Taux directeur de la Réserve Fédérale — indicateur de politique monétaire',
  },
  T10Y2Y: {
    label: 'Spread 10Y-2Y',
    color: '#f59e0b',
    description: "Écart entre les taux 10 ans et 2 ans — inversé = signal récessif",
  },
  WM2NS: {
    label: 'M2 (Liquidité)',
    color: '#22c55e',
    description: 'Masse monétaire M2 — mesure de la liquidité globale dans le système',
  },
}

export default function MacroPage() {
  const [days, setDays] = useState(90)
  const { data, isLoading, error } = useMacro(undefined, days)

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorState message="Erreur chargement données macro" />
  if (!data?.length) return <EmptyState message="Aucune donnée macro — lancez la synchro FRED" />

  // Group by series
  const grouped: Record<string, { date: string; value: number }[]> = {}
  for (const d of data) {
    if (!grouped[d.series_id]) grouped[d.series_id] = []
    grouped[d.series_id].push({ date: d.date, value: d.value })
  }

  // Reverse for chart (chronological order)
  Object.values(grouped).forEach(arr => arr.reverse())

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Macroéconomie</h2>
          <p className="text-xs text-zinc-500 mt-0.5">Données FRED — Séries temporelles</p>
        </div>
        <div className="flex gap-1.5">
          {[30, 90, 180, 365].map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1 rounded text-xs ${
                days === d
                  ? 'bg-apex-600 text-white'
                  : 'bg-surface-3 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {d}j
            </button>
          ))}
        </div>
      </div>

      {Object.entries(SERIES_INFO).map(([seriesId, info]) => {
        const chartData = grouped[seriesId] || []
        const latestValue = chartData[chartData.length - 1]?.value

        return (
          <div key={seriesId} className="card">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-medium text-zinc-200">{info.label}</h3>
                <p className="text-[10px] text-zinc-500 mt-0.5">{info.description}</p>
              </div>
              {latestValue !== undefined && (
                <div className="text-right">
                  <p className="text-xl font-mono font-bold" style={{ color: info.color }}>
                    {seriesId === 'WM2NS' ? `${(latestValue / 1000).toFixed(1)}T` : `${latestValue.toFixed(2)}%`}
                  </p>
                  <p className="text-[10px] text-zinc-500">Dernière valeur</p>
                </div>
              )}
            </div>

            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10, fill: '#71717a' }}
                    tickFormatter={(v: string) => v.slice(5)}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: '#71717a' }}
                    width={60}
                    tickFormatter={(v: number) => seriesId === 'WM2NS' ? `${(v/1000).toFixed(0)}T` : `${v.toFixed(1)}`}
                  />
                  <Tooltip
                    contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '6px', fontSize: '12px' }}
                    labelStyle={{ color: '#a1a1aa' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke={info.color}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                  {seriesId === 'T10Y2Y' && (
                    <Line
                      type="monotone"
                      dataKey={() => 0}
                      stroke="#ef4444"
                      strokeWidth={1}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-xs text-zinc-500 text-center py-8">Pas de données</p>
            )}
          </div>
        )
      })}
    </div>
  )
}
