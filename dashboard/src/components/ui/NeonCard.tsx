import clsx from 'clsx'
import type { ReactNode } from 'react'

interface NeonCardProps {
  children: ReactNode
  className?: string
  hover?: boolean
  onClick?: () => void
  padding?: string
}

export function NeonCard({ children, className, hover, onClick, padding = 'p-4' }: NeonCardProps) {
  return (
    <div
      className={clsx(
        'bg-friday-card border border-border-cyan rounded-xl',
        padding,
        hover && 'card-hover cursor-pointer',
        className,
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
    >
      {children}
    </div>
  )
}
