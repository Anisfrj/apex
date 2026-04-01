import { Loader2 } from 'lucide-react'

export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <Loader2 className="w-6 h-6 text-apex-500 animate-spin" />
    </div>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="text-center">
        <p className="text-red-400 text-sm">{message}</p>
        <p className="text-zinc-500 text-xs mt-1">Vérifiez la connexion au backend</p>
      </div>
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <p className="text-zinc-500 text-sm">{message}</p>
    </div>
  )
}
