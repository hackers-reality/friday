import clsx from 'clsx'
import type { ReactNode } from 'react'

interface TooltipProps { content: string; children: ReactNode; position?: 'top' | 'right' | 'bottom' | 'left' }

const posMap = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-1.5',
  right: 'left-full top-1/2 -translate-y-1/2 ml-1.5',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-1.5',
  left: 'right-full top-1/2 -translate-y-1/2 mr-1.5',
}

export function Tooltip({ content, children, position = 'top' }: TooltipProps) {
  return (
    <span className="relative inline-block group">
      {children}
      <span className={clsx('absolute hidden group-hover:block bg-friday-card-hover text-text-primary text-xs rounded-lg px-2.5 py-1.5 whitespace-nowrap z-50 shadow-lg border border-border-cyan pointer-events-none', posMap[position])}>
        {content}
      </span>
    </span>
  )
}
