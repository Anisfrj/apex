import { useState } from 'react'
import { useInsiders } from '@/hooks/useData'
import { LoadingSpinner, ErrorState, EmptyState } from '@/components/LoadingState'

function fmt(n: number | null | undefined): string {
  if (n == null) return '—'
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(1)}K`
  return `$${n.toFixed(0)}`
}

function scoreColor(score: number | null | undefined): string {
  if (score == null) return 'text-zinc-500'
  if (score >= 80) return 'text-emerald-400'
  if (score >= 50) return 'text-amber-400'
  return 'text-red-400'
}

interface Props {
  onStockClick?: (symbol: string) => void
}

export default function InsidersPage({ onStockClick }: Props) {
  const [days, setDays] = useState(7)
  const [minAmount, setMinAmount] = useState(0)
  const { data, isLoading, error } = useInsiders(days, minAmount)

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorState message="Erreur chargement données initiés" />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Traqueur d'Initiés</h2>
          <p className="text-xs text-zinc-500 mt-0.5">
            SEC EDGAR Form 4 — Achats uniquement (Code P)
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            {[1, 7, 14, 30].map(d => (
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
          <div className="flex gap-1.5">
            {[0, 100000, 250000, 1000000].map(amt => (
              <button
                key={amt}
                onClick={() => setMinAmount(amt)}
                className={`px-3 py-1 rounded text-xs ${
                  minAmount === amt
                    ? 'bg-emerald-600 text-white'
                    : 'bg-surface-3 text-zinc-400 hover:text-zinc-200'
                }`}
              >
                {amt === 0 ? 'Tous' : `≥${fmt(amt)}`}
              </button>
            ))}
          </div>
        </div>
      </div>

      {!data?.length ? (
        <EmptyState message="Aucune transaction d'initié trouvée" />
      ) : (
        <div className="card p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 border-b border-zinc-800">
                  <th className="text-left py-3 px-4 font-medium">Symbole</th>
                  <th className="text-left py-3 px-4 font-medium">Entreprise</th>
                  <th className="text-left py-3 px-4 font-medium">Initié</th>
                  <th className="text-left py-3 px-4 font-medium">Titre</th>
                  <th className="text-right py-3 px-4 font-medium">Actions</th>
                  <th className="text-right py-3 px-4 font-medium">Prix</th>
                  <th className="text-right py-3 px-4 font-medium">Montant</th>
                  <th className="text-center py-3 px-4 font-medium">Score</th>
                  <th className="text-center py-3 px-4 font-medium">Label</th>
                  <th className="text-left py-3 px-4 font-medium">Raison rejet</th>
                  <th className="text-right py-3 px-4 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {data.map((tx, i) => (
                  <tr key={i} className="table-row">
                    <td className="py-2.5 px-4">
                      <button
                        onClick={() => onStockClick?.(tx.symbol)}
                        className="font-mono font-bold text-apex-400 hover:text-blue-300 hover:underline transition cursor-pointer"
                      >
                        {tx.symbol}
                      </button>
                    </td>
                    <td className="py-2.5 px-4 text-zinc-300 max-w-[180px] truncate">
                      {tx.company_name ?? '—'}
                    </td>
                    <td className="py-2.5 px-4 text-zinc-300 max-w-[150px] truncate">
                      {tx.insider_name}
                    </td>
                    <td className="py-2.5 px-4 text-zinc-500">
                      {tx.insider_title ?? '—'}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-zinc-300">
                      {tx.shares?.toLocaleString() ?? '—'}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-zinc-400">
                      {tx.price_per_share ? `$${tx.price_per_share.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono font-medium text-emerald-400">
                      {fmt(tx.total_value)}
                    </td>
                    <td className="py-2.5 px-4 text-center">
                      <span className={`font-mono ${scoreColor((tx as any).score)}`}>
                        {(tx as any).score != null ? (tx as any).score.toFixed(0) : '—'}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-center text-zinc-300">
                      {(tx as any).score_label ?? '—'}
                    </td>
                    <td className="py-2.5 px-4 text-zinc-500 max-w-[200px] truncate">
                      {tx.rejection_reason ?? '—'}
                    </td>
                    <td className="py-2.5 px-4 text-right text-zinc-500">
                      {tx.transaction_date ?? tx.filing_date}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-2 border-t border-zinc-800 text-[10px] text-zinc-600">
            {data.length} transaction(s) trouvée(s) — <span className="text-blue-400">Cliquez sur un symbole pour voir le détail</span>
          </div>
        </div>
      )}
    </div>
  )
}
