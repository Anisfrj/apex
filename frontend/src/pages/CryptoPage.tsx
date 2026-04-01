import { useState } from 'react'
import { useCrypto } from '@/hooks/useData'
import { LoadingSpinner, ErrorState, EmptyState } from '@/components/LoadingState'
import { ArrowUpDown } from 'lucide-react'

function fmt(n: number | null | undefined, prefix = '$'): string {
  if (n == null) return '—'
  if (Math.abs(n) >= 1e9) return `${prefix}${(n / 1e9).toFixed(2)}B`
  if (Math.abs(n) >= 1e6) return `${prefix}${(n / 1e6).toFixed(2)}M`
  if (Math.abs(n) >= 1e3) return `${prefix}${(n / 1e3).toFixed(1)}K`
  return `${prefix}${n.toFixed(0)}`
}

const SORT_OPTIONS = [
  { value: 'tvl', label: 'TVL' },
  { value: 'tvl_change_1d', label: 'TVL 24h%' },
  { value: 'mcap_fdv_ratio', label: 'MCap/FDV' },
  { value: 'fees_24h', label: 'Fees 24h' },
]

export default function CryptoPage() {
  const [sortBy, setSortBy] = useState('tvl')
  const { data, isLoading, error } = useCrypto(sortBy, 100)

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorState message="Erreur chargement données crypto" />
  if (!data?.length) return <EmptyState message="Aucune donnée crypto — lancez la synchro DeFiLlama" />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Screener Crypto</h2>
          <p className="text-xs text-zinc-500 mt-0.5">Top protocoles DeFi — DeFiLlama</p>
        </div>
        <div className="flex items-center gap-1.5">
          <ArrowUpDown className="w-3 h-3 text-zinc-500" />
          {SORT_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setSortBy(opt.value)}
              className={`px-3 py-1 rounded text-xs ${
                sortBy === opt.value
                  ? 'bg-apex-600 text-white'
                  : 'bg-surface-3 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-zinc-500 border-b border-zinc-800">
                <th className="text-left py-3 px-4 font-medium">#</th>
                <th className="text-left py-3 px-4 font-medium">Protocole</th>
                <th className="text-left py-3 px-4 font-medium">Chain</th>
                <th className="text-left py-3 px-4 font-medium">Catégorie</th>
                <th className="text-right py-3 px-4 font-medium">TVL</th>
                <th className="text-right py-3 px-4 font-medium">TVL 24h</th>
                <th className="text-right py-3 px-4 font-medium">TVL 7j</th>
                <th className="text-right py-3 px-4 font-medium">MCap</th>
                <th className="text-right py-3 px-4 font-medium">FDV</th>
                <th className="text-right py-3 px-4 font-medium">MCap/FDV</th>
                <th className="text-right py-3 px-4 font-medium">Fees 24h</th>
              </tr>
            </thead>
            <tbody>
              {data.map((p, i) => (
                <tr key={`${p.protocol}-${i}`} className="table-row">
                  <td className="py-2.5 px-4 text-zinc-500">{i + 1}</td>
                  <td className="py-2.5 px-4 font-medium text-zinc-200">{p.protocol}</td>
                  <td className="py-2.5 px-4 text-zinc-400">{p.chain ?? '—'}</td>
                  <td className="py-2.5 px-4">
                    <span className="badge-blue">{p.category ?? '—'}</span>
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono text-zinc-200">
                    {fmt(p.tvl)}
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono">
                    <span className={(p.tvl_change_1d ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                      {p.tvl_change_1d != null ? `${p.tvl_change_1d >= 0 ? '+' : ''}${p.tvl_change_1d.toFixed(1)}%` : '—'}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono">
                    <span className={(p.tvl_change_7d ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                      {p.tvl_change_7d != null ? `${p.tvl_change_7d >= 0 ? '+' : ''}${p.tvl_change_7d.toFixed(1)}%` : '—'}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono text-zinc-300">{fmt(p.mcap)}</td>
                  <td className="py-2.5 px-4 text-right font-mono text-zinc-400">{fmt(p.fdv)}</td>
                  <td className="py-2.5 px-4 text-right font-mono">
                    <span className={
                      (p.mcap_fdv_ratio ?? 0) >= 0.4 ? 'text-emerald-400' :
                      (p.mcap_fdv_ratio ?? 0) >= 0.2 ? 'text-amber-400' : 'text-red-400'
                    }>
                      {p.mcap_fdv_ratio?.toFixed(2) ?? '—'}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono text-zinc-300">
                    {fmt(p.fees_24h)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
