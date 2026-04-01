interface StatusBadgeProps {
  status: boolean | null
  trueLabel?: string
  falseLabel?: string
  nullLabel?: string
}

export default function StatusBadge({
  status,
  trueLabel = 'Oui',
  falseLabel = 'Non',
  nullLabel = '—',
}: StatusBadgeProps) {
  if (status === null || status === undefined) {
    return <span className="text-zinc-500 text-xs">{nullLabel}</span>
  }
  return status ? (
    <span className="badge-green">{trueLabel}</span>
  ) : (
    <span className="badge-red">{falseLabel}</span>
  )
}
