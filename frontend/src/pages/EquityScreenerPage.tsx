import { useState } from 'react'
import { LoadingSpinner, ErrorState } from '@/components/LoadingState'

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

export default function EquityScreenerPage() {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<EquityFundamental[]>([])
  const [sector, setSector] = useState('')
  const [minMarketCap, setMinMarketCap] = useState('')

  const handleSearch = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (sector) params.append('sector', sector)
      if (minMarketCap) params.append('min_market_cap', minMarketCap)
      
      const res = await fetch(`/api/screener/equities?${params.toString()}`)
      const result = await res.json()
      setData(result)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Screener Actions</h2>
          <p className="text-xs text-zinc-500 mt-0.5">S&P 500 + NASDAQ 100 — yfinance gratuit</p>
        </div>
      </div>

      {/* Filtres */}
      <div className="card p-4 space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <div>
            abel className="text-xs text-zinc-400 mb-1 block">Secteur</label>
            <select 
              value={sector} 
              onChange={(e) => setSector(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-300 rounded px-3 py-2 text-sm"
            >
              <option value="">Tous</option>
              <option value="Technology">Technology</option>
              <option value="Financials">Financials</option>
              <option value="Health Care">Health Care</option>
              <option value="Consumer Discretionary">Consumer Discretionary</option>
              <option value="Communication Services">Communication Services</option>
              <option value="Industrials">Industrials</option>
              <option value="Consumer Staples">Consumer Staples</option>
              <option value="Energy">Energy</option>
              <option value="Utilities">Utilities</option>
              <option value="Real Estate">Real Estate</option>
              <option value="Materials">Materials</option>
            </select>
          </div>
          <div>
            abel className="text-xs text-zinc-400 mb-1 block">Market Cap Min</label>
            <input 
              type="number" 
              value={minMarketCap}
              onChange={(e) => setMinMarketCap(e.target.value)}
              placeholder="Ex: 1000000000"
              className="w-full bg-zinc-800 border border-zinc-700 text-zinc-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="flex items-end">
            <button 
              onClick={handleSearch}
              className="w-full px-4 py-2 bg-apex-600 hover:bg-apex-700 text-white rounded transition text-sm font-medium"
            >
              Rechercher
            </button>
          </div>
        </div>
      </div>

      {/* Résultats */}
      {loading ? (
        <LoadingSpinner />
      ) : data.length === 0 ? (
        <div className="card p-8 text-center text-zinc-500 text-sm">
          Aucun résultat. Lancez une recherche pour voir les actions.
        </div>
      ) : (
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
                  <tr key={i} className="table-row">
                    <td className="py-2.5 px-4 font-mono font-bold text-apex-400">{stock.symbol}</td>
                    <td className="py-2.5 px-4 text-zinc-300">{stock.company_name ?? '—'}</td>
                    <td className="py-2.5 px-4 text-zinc-400 text-[10px]">{stock.sector ?? '—'}</td>
                    <td className="py-2.5 px-4 text-right font-mono text-zinc-300">
                      {stock.price ? `$${stock.price.toFixed(2)}` : '—'}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-zinc-400">
                      {stock.market_cap ? `${(stock.market_cap / 1e9).toFixed(1)}B` : '—'}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-zinc-300">
                      {stock.pe_ratio ? stock.pe_ratio.toFixed(1) : '—'}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-zinc-300">
                      {stock.roe ? `${(stock.roe * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono text-zinc-400">
                      {stock.sma_200 ? `$${stock.sma_200.toFixed(2)}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-2 border-t border-zinc-800 text-[10px] text-zinc-600">
            {data.length} action(s) trouvée(s)
          </div>
        </div>
      )}
    </div>
  )
}
