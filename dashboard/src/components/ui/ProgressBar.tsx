import clsx from 'clsx'

interface ProgressBarProps { value: number; color?: 'cyan' | 'green' | 'red' | 'yellow'; label?: string; showPercent?: boolean }

const colorMap = { cyan: 'bg-neon-cyan', green: 'bg-neon-green', red: 'bg-neon-red', yellow: 'bg-neon-yellow' }

export function ProgressBar({ value, color = 'cyan', label, showPercent }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div>
      {(label || showPercent) && (
        <div className="flex justify-between text-xs text-text-dim mb-1">
          {label && <span>{label}</span>}
          {showPercent && <span className="font-mono">{clamped}%</span>}
        </div>
      )}
      <div className="w-full bg-friday-bg-deep rounded-full h-2 overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-300 ease-out', colorMap[color])}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  )
}
