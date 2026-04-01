import { Shield, AlertTriangle, Zap, Loader2 } from 'lucide-react'
import { useAISummary } from '@/hooks/useData'

interface Props {
  symbol: string
}

export default function AISummaryCard({ symbol }: Props) {
  const { data, isLoading, error } = useAISummary(symbol)

  if (isLoading) {
    return (
      <div className="col-span-3 flex items-center justify-center h-32 rounded-xl border border-zinc-800 bg-zinc-900/50">
        <Loader2 className="animate-spin text-zinc-500 mr-3" size={20} />
        <span className="text-zinc-400 text-sm">Analyse IA en cours pour {symbol}</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="col-span-3 flex items-center justify-center h-20 rounded-xl border border-red-900/30 bg-red-950/20">
        <span className="text-red-400 text-sm">Analyse IA indisponible</span>
      </div>
    )
  }

  const cards = [
    {
      title: 'The Moat',
      label: 'Avantage Concurrentiel',
      icon: Shield,
      points: data.moat.filter(Boolean),
      border: 'border-emerald-500/20 hover:border-emerald-500/50',
      iconColor: 'text-emerald-400',
      dotColor: 'bg-emerald-400',
    },
    {
      title: 'Red Flags',
      label: 'Risques',
      icon: AlertTriangle,
      points: data.risks.filter(Boolean),
      border: 'border-red-500/20 hover:border-red-500/50',
      iconColor: 'text-red-400',
      dotColor: 'bg-red-400',
    },
    {
      title: 'Catalysts',
      label: 'Catalyseurs',
      icon: Zap,
      points: data.catalysts.filter(Boolean),
      border: 'border-amber-500/20 hover:border-amber-500/50',
      iconColor: 'text-amber-400',
      dotColor: 'bg-amber-400',
    },
  ]

  return (
    <>
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <div
            key={card.title}
            className={'rounded-xl border bg-zinc-900/60 backdrop-blur-sm p-5 shadow-lg transition-all duration-200 ' + card.border}
          >
            <div className="flex items-center gap-2 mb-4">
              <Icon size={16} className={card.iconColor} />
              <span className="text-sm font-semibold text-zinc-200">{card.label}</span>
            </div>
            <ul className="space-y-2">
              {card.points.map((point, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-zinc-400">
                  <span className={'mt-1.5 h-1.5 w-1.5 rounded-full shrink-0 ' + card.dotColor} />
                  {point}
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </>
  )
}
