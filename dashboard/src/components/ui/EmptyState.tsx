interface EmptyStateProps { icon: string; title: string; description: string }

export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 opacity-60 text-center">
      <span className="text-4xl mb-3">{icon}</span>
      <h3 className="text-lg font-display text-text-secondary tracking-wider mb-1">{title}</h3>
      <p className="text-sm text-text-dim max-w-xs">{description}</p>
    </div>
  )
}
