import {
  LayoutDashboard,
  Globe,
  BarChart3,
  Bitcoin,
  UserCheck,
  Bell,
  Zap,
} from 'lucide-react'

type Page = 'dashboard' | 'macro' | 'sectors' | 'crypto' | 'insiders' | 'alerts' | 'screener'

const NAV_ITEMS: { id: Page; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'dashboard', label: 'Vue Globale', icon: LayoutDashboard },
  { id: 'macro', label: 'Macroéconomie', icon: Globe },
  { id: 'sectors', label: 'Radar Sectoriel', icon: BarChart3 },
  { id: 'crypto', label: 'Screener Crypto', icon: Bitcoin },
  { id: 'insiders', label: 'Traqueur Initiés', icon: UserCheck },
  { id: 'alerts', label: 'Historique Alertes', icon: Bell },
    { id: 'screener', label: 'Screener Actions', icon: BarChart3 },
]

interface SidebarProps {
  activePage: Page
  onNavigate: (page: Page) => void
}

export default function Sidebar({ activePage, onNavigate }: SidebarProps) {
  return (
    <aside className="w-56 bg-surface-1 border-r border-zinc-800 flex flex-col h-screen shrink-0">
      {/* Logo */}
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-apex-600 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-zinc-100 tracking-tight">APEX</h1>
            <p className="text-[10px] text-zinc-500 leading-tight">Screener Top-Down</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-0.5">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onNavigate(id)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
              activePage === id
                ? 'bg-apex-600/15 text-apex-400'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-surface-3'
            }`}
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-zinc-800">
        <p className="text-[10px] text-zinc-600 text-center">v1.0 — Données auto-refresh 60s</p>
      </div>
    </aside>
  )
}
