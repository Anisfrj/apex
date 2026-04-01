import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import MacroPage from './pages/MacroPage'
import SectorsPage from './pages/SectorsPage'
import CryptoPage from './pages/CryptoPage'
import InsidersPage from './pages/InsidersPage'
import AlertsPage from './pages/AlertsPage'
import IdeasPage from './pages/IdeasPage'
type Page = 'dashboard' | 'macro' | 'sectors' | 'crypto' | 'insiders' | 'alerts'

export default function App() {
  const [page, setPage] = useState<Page>('dashboard')

  const renderPage = () => {
    switch (page) {
      case 'dashboard': return <Dashboard />
      case 'macro': return <MacroPage />
      case 'sectors': return <SectorsPage />
      case 'crypto': return <CryptoPage />
      case 'insiders': return <InsidersPage />
      case 'alerts': return <AlertsPage />
      case 'ideas' : return <IdeasPage />
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar activePage={page} onNavigate={setPage} />
      <main className="flex-1 overflow-y-auto p-6">
        {renderPage()}
      </main>
    </div>
  )
}
