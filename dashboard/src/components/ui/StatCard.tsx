import { TrendingUp, TrendingDown } from 'lucide-react'
import type { ReactNode } from 'react'

interface StatCardProps {
  label: string
  value: string | number
  delta?: number
  icon?: ReactNode
  color?: string
}

export function StatCard({ label, value, delta, icon, color }: StatCardProps) {
  return (
    <div className="bg-friday-card border border-border-cyan rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        {icon && <span className="text-text-dim">{icon}</span>}
        <span className="text-xs text-text-dim uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-2xl font-display" style={{ color: color ?? '#00f5ff' }}>
        {value}
      </div>
      {delta !== undefined && (
        <div className={`flex items-center gap-1 mt-1 text-xs font-mono ${delta >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
          {delta >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          <span>{delta >= 0 ? '+' : ''}{delta}</span>
        </div>
      )}
    </div>
  )
}
