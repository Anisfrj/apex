import { useState, useEffect } from 'react'
import { api, StockFundamental, InsiderTx, AISummary, SectorData } from '../lib/api'

interface Props {
  symbol: string
  onBack: () => void
}

function fmt(n: number | null | undefined, decimals = 2) {
  if (n == null) return '—'
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(1)}B`
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`
  return `$${n.toFixed(decimals)}`
}

export default function StockDetailPage({ symbol, onBack }: Props) {
  const [fundamentals, setFundamentals] = useState<StockFundamental | null>(null)
  const [insiders, setInsiders] = useState<InsiderTx[]>([])
  const [aiSummary, setAiSummary] = useState<AISummary | null>(null)
  const [sector, setSector] = useState<SectorData | null>(null)
  const [loading, setLoading] = useState(true)
  const [aiLoading, setAiLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setAiLoading(true)

    Promise.all([
      api.getStock(symbol),
      api.getInsiders({ days: '90' }),
      api.getSectors(),
    ]).then(([stocks, insiderData, sectors]) => {
      setFundamentals(stocks[0] ?? null)
      setInsiders(insiderData.filter(i => i.symbol === symbol))
      const matchSector = sectors.find(s => {
        const sectorMap: Record<string, string> = {
          XLE: 'Energy', XLU: 'Utilities', XLC: 'Communication Services',
          XLK: 'Technology', XLB: 'Materials', XLF: 'Financials',
          XLY: 'Consumer Discretionary', XLV: 'Health Care',
          XLP: 'Consumer Staples', XLRE: 'Real Estate', XLI: 'Industrials',
        }
        return sectorMap[s.symbol] === (stocks[0]?.sector ?? '')
      })
      setSector(matchSector ?? null)
      setLoading(false)
    }).catch(() => setLoading(false))

    api.getAISummary(symbol)
      .then(data => { setAiSummary(data); setAiLoading(false) })
      .catch(() => setAiLoading(false))
  }, [symbol])

  const rs = sector?.relative_strength_30d
  const aboveMm200 = sector?.above_sma200
  const rsColor = rs == null ? 'text-gray-400' : rs >= 1.01 ? 'text-green-400' : rs <= 0.99 ? 'text-red-400' : 'text-yellow-400'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={onBack}
          className="px-3 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm transition"
        >
          ← Retour
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">{symbol}</h1>
          {fundamentals?.company_name && (
            <p className="text-gray-400 text-sm">{fundamentals.company_name}</p>
          )}
        </div>
        {fundamentals?.sector && (
          <span className="ml-auto px-3 py-1 bg-blue-900/50 text-blue-300 rounded-full text-sm border border-blue-700">
            {fundamentals.sector}
          </span>
        )}
      </div>

      {loading ? (
        <div className="text-gray-400 text-center py-12">Chargement...</div>
      ) : (
        <>
          {/* KPI Bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">Free Cash Flow</p>
              <p className="text-white text-xl font-bold">{fmt(fundamentals?.free_cash_flow)}</p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">ROIC</p>
              <p className="text-white text-xl font-bold">
                {fundamentals?.roic != null ? `${(fundamentals.roic * 100).toFixed(1)}%` : '—'}
              </p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">RS Sectorielle 30j</p>
              <p className={`text-xl font-bold ${rsColor}`}>
                {rs != null ? rs.toFixed(4) : '—'}
              </p>
            </div>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">Secteur ETF vs MM200</p>
              <p className={`text-xl font-bold ${aboveMm200 ? 'text-green-400' : aboveMm200 === false ? 'text-red-400' : 'text-gray-400'}`}>
                {aboveMm200 == null ? '—' : aboveMm200 ? 'Au-dessus' : 'En-dessous'}
              </p>
            </div>
          </div>

          {/* AI Summary + Insiders grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* AI Summary */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
                <span className="text-purple-400">★</span> AI Executive Summary
              </h2>
              {aiLoading ? (
                <p className="text-gray-400 text-sm">Analyse en cours...</p>
              ) : aiSummary ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-green-400 text-xs font-semibold uppercase tracking-wide mb-2">Avantages compétitifs (Moat)</p>
                    <ul className="space-y-1">
                      {aiSummary.moat.map((m, i) => (
                        <li key={i} className="text-gray-300 text-sm flex gap-2"><span className="text-green-400 mt-0.5">✓</span>{m}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-red-400 text-xs font-semibold uppercase tracking-wide mb-2">Risques</p>
                    <ul className="space-y-1">
                      {aiSummary.risks.map((r, i) => (
                        <li key={i} className="text-gray-300 text-sm flex gap-2"><span className="text-red-400 mt-0.5">⚠</span>{r}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-blue-400 text-xs font-semibold uppercase tracking-wide mb-2">Catalyseurs</p>
                    <ul className="space-y-1">
                      {aiSummary.catalysts.map((c, i) => (
                        <li key={i} className="text-gray-300 text-sm flex gap-2"><span className="text-blue-400 mt-0.5">→</span>{c}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500 text-sm">Données IA non disponibles.</p>
              )}
            </div>

            {/* Insiders */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-white font-semibold mb-4">Transactions Initiés (90j)</h2>
              {insiders.length === 0 ? (
                <p className="text-gray-500 text-sm">Aucune transaction trouvée.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-gray-400 border-b border-gray-800">
                        <th className="text-left pb-2">Initié</th>
                        <th className="text-left pb-2">Titre</th>
                        <th className="text-right pb-2">Montant</th>
                        <th className="text-right pb-2">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {insiders.slice(0, 8).map((ins, i) => (
                        <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                          <td className="py-2 text-gray-300">{ins.insider_name}</td>
                          <td className="py-2 text-gray-400 text-xs">{ins.insider_title ?? '—'}</td>
                          <td className="py-2 text-right text-green-400 font-mono">
                            {ins.total_value != null ? fmt(ins.total_value) : '—'}
                          </td>
                          <td className="py-2 text-right text-gray-400">
                            {ins.transaction_date?.slice(0, 10) ?? ins.filing_date?.slice(0, 10)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Fundamentals detail */}
          {fundamentals && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <h2 className="text-white font-semibold mb-4">Fondamentaux</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-400 text-xs uppercase mb-1">Cash Flow Opérationnel</p>
                  <p className="text-white font-mono">{fmt(fundamentals.operating_cash_flow)}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-xs uppercase mb-1">Capex</p>
                  <p className="text-white font-mono">{fmt(fundamentals.capital_expenditures)}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-xs uppercase mb-1">Capital Investi</p>
                  <p className="text-white font-mono">{fmt(fundamentals.invested_capital)}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-xs uppercase mb-1">Période</p>
                  <p className="text-white">{fundamentals.fiscal_date?.slice(0, 10) ?? '—'}</p>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
