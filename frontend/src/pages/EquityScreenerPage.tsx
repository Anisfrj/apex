import { useState } from 'react'

interface EquityFundamental {
  symbol: string
  company_name: string | null
  sector: string | null
  market_cap: number | null
  price: number | null
  pe_ratio: number | null
  roe: number | null
  sma_200: number | null
}

const SECTORS = [
  'Tous', 'Technology', 'Financials', 'Health Care',
  'Consumer Discretionary', 'Communication Services',
  'Industrials', 'Consumer Staples', 'Energy', 'Utilities',
  'Real Estate', 'Materials'
]

function fmt(v: number | null, digits = 2): string {
  if (v === null || v === undefined) return '-'
  return v.toFixed(digits)
}

function fmtB(v: number | null): string {
  if (v === null || v === undefined) return '-'
  if (v >= 1e12) return (v / 1e12).toFixed(1) + 'T'
  if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B'
  if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M'
  return v.toString()
}

export default function EquityScreenerPage() {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<EquityFundamental[]>([])
  const [sector, setSector] = useState('')
  const [minMarketCap, setMinMarketCap] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (sector && sector !== 'Tous') params.append('sector', sector)
      if (minMarketCap) params.append('min_market_cap', minMarketCap)
      const res = await fetch(`/api/screener/equities?${params.toString()}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const result = await res.json()
      setData(Array.isArray(result) ? result : [])
    } catch (err) {
      console.error(err)
      setError('Erreur lors de la recherche. Verifiez que le backend est disponible.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Screener Actions</h2>
          <p className="text-xs text-zinc-500 mt-0.5">S&amp;P 500 + NASDAQ 100 - yfinance gratuit</p>
        </div>
      </div>

      <div className="card p-4 space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Secteur</label>
            <select
              value={sector}
              onChange={(e) => setSector(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-300 rounded px-3 py-1.5 text-sm"
            >
              {SECTORS.map((s) => (
                <option key={s} value={s === 'Tous' ? '' : s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-zinc-400 mb-1 block">Market Cap Min (B)</label>
            <input
              type="number"
              value={minMarketCap}
              onChange={(e) => setMinMarketCap(e.target.value)}
              placeholder="ex: 10"
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-300 rounded px-3 py-1.5 text-sm"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleSearch}
              disabled={loading}
              className="w-full px-4 py-2 bg-apex-600 hover:bg-apex-700 text-white rounded transition disabled:opacity-50"
            >
              {loading ? 'Recherche...' : 'Rechercher'}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="card p-4 text-red-400 text-sm">{error}</div>
      )}

      {!loading && data.length === 0 && !error && (
        <div className="card p-8 text-center text-zinc-500 text-sm">
          Lancez une recherche pour afficher les actions.
        </div>
      )}

      {data.length > 0 && (
        <div className="card p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 border-b border-zinc-800">
                  <th className="text-left py-3 px-4 font-medium">Ticker</th>
                  <th className="text-left py-3 px-4 font-medium">Entreprise</th>
                  <th className="text-left py-3 px-4 font-medium">Secteur</th>
                  <th className="text-right py-3 px-4 font-medium">Prix</th>
                  <th className="text-right py-3 px-4 font-medium">Market Cap</th>
                  <th className="text-right py-3 px-4 font-medium">P/E</th>
                  <th className="text-right py-3 px-4 font-medium">ROE</th>
                  <th className="text-right py-3 px-4 font-medium">SMA 200</th>
                </tr>
              </thead>
              <tbody>
                {data.map((stock, i) => (
                  <tr key={i} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition">
                    <td className="py-2.5 px-4 font-mono font-bold text-apex-400">{stock.symbol}</td>
                    <td className="py-2.5 px-4 text-zinc-300">{stock.company_name ?? '-'}</td>
                    <td className="py-2.5 px-4 text-zinc-400 text-[10px]">{stock.sector ?? '-'}</td>
                    <td className="py-2.5 px-4 text-right text-zinc-300">${fmt(stock.price)}</td>
                    <td className="py-2.5 px-4 text-right text-zinc-300">{fmtB(stock.market_cap)}</td>
                    <td className="py-2.5 px-4 text-right text-zinc-300">{fmt(stock.pe_ratio, 1)}</td>
                    <td className="py-2.5 px-4 text-right text-zinc-300">{fmt(stock.roe ? stock.roe * 100 : null, 1)}%</td>
                    <td className="py-2.5 px-4 text-right text-zinc-300">${fmt(stock.sma_200)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-2 text-xs text-zinc-500 border-t border-zinc-800">
            {data.length} actions
          </div>
        </div>
      )}
    </div>
  )
}
