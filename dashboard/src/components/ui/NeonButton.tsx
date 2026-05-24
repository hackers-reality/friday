import clsx from 'clsx'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface NeonButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  icon?: ReactNode
}

const variants = {
  primary: 'bg-neon-cyan text-friday-bg hover:brightness-110 active:scale-95',
  secondary: 'bg-transparent border border-border-cyan text-neon-cyan hover:bg-neon-cyan/10',
  danger: 'bg-neon-red/20 border border-neon-red/30 text-neon-red hover:bg-neon-red/30',
}

const sizes = {
  sm: 'text-xs px-2.5 py-1.5',
  md: 'text-sm px-4 py-2',
  lg: 'text-base px-6 py-2.5',
}

export function NeonButton({
  variant = 'secondary', size = 'md', icon, children, className, ...props
}: NeonButtonProps) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed',
        variants[variant], sizes[size], className,
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  )
}
