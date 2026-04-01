import { useState } from 'react'
import { useAlerts } from '@/hooks/useData'
import { LoadingSpinner, ErrorState, EmptyState } from '@/components/LoadingState'
import { Filter } from 'lucide-react'

export default function AlertsPage() {
  const [typeFilter, setTypeFilter] = useState<string | undefined>()
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const { data, isLoading, error } = useAlerts(typeFilter, statusFilter, 100)

  if (isLoading) return <LoadingSpinner />
  if (error) return <ErrorState message="Erreur chargement historique alertes" />

  const total = data?.length ?? 0
  const sent = data?.filter(a => a.status === 'sent').length ?? 0
  const pending = data?.filter(a => a.status === 'pending_send').length ?? 0
  const rejected = data?.filter(a => a.status.startsWith('rejected')).length ?? 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-zinc-100">Historique des Alertes</h2>
          <p className="text-xs text-zinc-500 mt-0.5">Journal complet du moteur de filtrage</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card">
          <div className="card-header">Total</div>
          <div className="stat-value">{total}</div>
        </div>
        <div className="card">
          <div className="card-header">Envoyées</div>
          <div className="stat-value text-emerald-400">{sent}</div>
        </div>
        <div className="card">
          <div className="card-header">En attente envoi</div>
          <div className="stat-value text-amber-400">{pending}</div>
        </div>
        <div className="card">
          <div className="card-header">Rejetées</div>
          <div className="stat-value text-red-400">{rejected}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <Filter className="w-3 h-3 text-zinc-500" />
          <span className="text-xs text-zinc-500">Type:</span>
          {[undefined, 'equity', 'crypto'].map(t => (
            <button
              key={t ?? 'all'}
              onClick={() => setTypeFilter(t)}
              className={`px-3 py-1 rounded text-xs ${
                typeFilter === t
                  ? 'bg-apex-600 text-white'
                  : 'bg-surface-3 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {t ?? 'Tous'}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Statut:</span>
          {[
            undefined,
            'sent',
            'pending_send',
            'rejected_fcf',
            'rejected_roic',
            'rejected_sector',
            'rejected_dilution',
          ].map(s => (
            <button
              key={s ?? 'all'}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded text-xs ${
                statusFilter === s
                  ? 'bg-apex-600 text-white'
                  : 'bg-surface-3 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {s ?? 'Tous'}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {!data?.length ? (
        <EmptyState message="Aucune alerte dans l'historique" />
      ) : (
        <div className="card p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 border-b border-zinc-800">
                  <th className="text-left py-3 px-4 font-medium">Type</th>
                  <th className="text-left py-3 px-4 font-medium">Symbole</th>
                  <th className="text-left py-3 px-4 font-medium">Score</th>
                  <th className="text-left py-3 px-4 font-medium">Secteur</th>
                  <th className="text-left py-3 px-4 font-medium">Déclencheur</th>
                  <th className="text-left py-3 px-4 font-medium">Statut</th>
                  <th className="text-left py-3 px-4 font-medium">Détails</th>
                  <th className="text-right py-3 px-4 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {data.map(a => {
                  let details: Record<string, any> = {}
                  try {
                    if (a.details) details = JSON.parse(a.details)
                  } catch {}

                  return (
                    <tr key={a.id} className="table-row">
                      <td className="py-2.5 px-4">
                        <span className={a.alert_type === 'equity' ? 'badge-blue' : 'badge-yellow'}>
                          {a.alert_type}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 font-mono font-medium text-zinc-200">
                        {a.symbol}
                      </td>
                      <td className="py-2.5 px-4 text-zinc-300">
                        {a.score != null ? a.score.toFixed(1) : '—'}
                      </td>
                      <td className="py-2.5 px-4 text-zinc-400">
                        {a.sector_name ?? '—'}
                      </td>
                      <td className="py-2.5 px-4 text-zinc-400">{a.trigger}</td>
                      <td className="py-2.5 px-4">
                        <span
                          className={
                            a.status === 'sent'
                              ? 'badge-green'
                              : a.status === 'pending_send'
                              ? 'badge-amber'
                              : a.status.startsWith('rejected')
                              ? 'badge-red'
                              : 'badge-yellow'
                          }
                        >
                          {a.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-zinc-500 max-w-[300px]">
                        {Object.entries(details).map(([k, v]) => (
                          <span key={k} className="mr-3">
                            <span className="text-zinc-600">{k}:</span>{' '}
                            <span className="font-mono text-zinc-400">
                              {typeof v === 'number' ? v.toLocaleString() : String(v)}
                            </span>
                          </span>
                        ))}
                      </td>
                      <td className="py-2.5 px-4 text-right text-zinc-500">
                        {a.created_at ? new Date(a.created_at).toLocaleString('fr-FR') : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
