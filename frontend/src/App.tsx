import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import MacroPage from './pages/MacroPage'
import SectorsPage from './pages/SectorsPage'
import CryptoPage from './pages/CryptoPage'
import InsidersPage from './pages/InsidersPage'
import AlertsPage from './pages/AlertsPage'
import IdeasPage from './pages/IdeasPage'
import StockDetailPage from './pages/StockDetailPage'
import EquityScreenerPage from './pages/EquityScreenerPage'

type Page = 'dashboard' | 'macro' | 'sectors' | 'crypto' | 'insiders' | 'alerts' | 'ideas' | 'screener'

export default function App() {
  const [page, setPage] = useState<Page>('dashboard')
  const [selectedStock, setSelectedStock] = useState<string | null>(null)

  const handleStockClick = (symbol: string) => {
    setSelectedStock(symbol)
  }

  const handleBackFromStock = () => {
    setSelectedStock(null)
  }

  const renderPage = () => {
    if (selectedStock) {
      return <StockDetailPage symbol={selectedStock} onBack={handleBackFromStock} />
    }
    switch (page) {
      case 'dashboard': return <Dashboard onStockClick={handleStockClick} />
      case 'macro': return <MacroPage />
      case 'sectors': return <SectorsPage />
      case 'crypto': return <CryptoPage />
      case 'insiders': return <InsidersPage onStockClick={handleStockClick} />
      case 'alerts': return <AlertsPage />
      case 'ideas': return <IdeasPage />
              case 'screener': return <EquityScreenerPage />
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar activePage={page} onNavigate={(p) => { setSelectedStock(null); setPage(p as Page) }} />
      <main className="flex-1 overflow-y-auto p-6">
        {renderPage()}
      </main>
    </div>
  )
}
