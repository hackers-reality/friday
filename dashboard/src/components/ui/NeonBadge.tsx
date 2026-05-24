import clsx from 'clsx'
import type { ReactNode } from 'react'

interface NeonBadgeProps { children: ReactNode; color: 'cyan' | 'purple' | 'red' | 'yellow' | 'green' | 'orange'; size?: 'sm' | 'md' }

const colorMap = {
  cyan: 'bg-neon-cyan/15 text-neon-cyan',
  purple: 'bg-neon-purple/15 text-neon-purple',
  red: 'bg-neon-red/15 text-neon-red',
  yellow: 'bg-neon-yellow/15 text-neon-yellow',
  green: 'bg-neon-green/15 text-neon-green',
  orange: 'bg-neon-orange/15 text-neon-orange',
}

export function NeonBadge({ children, color, size = 'md' }: NeonBadgeProps) {
  return (
    <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full font-mono uppercase tracking-wider', colorMap[color], size === 'sm' ? 'text-[10px]' : 'text-xs')}>
      {children}
    </span>
  )
}
