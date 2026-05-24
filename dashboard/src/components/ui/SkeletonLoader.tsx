import clsx from 'clsx'

interface SkeletonLoaderProps { lines?: number; className?: string }

const widths = ['w-full', 'w-4/5', 'w-3/5', 'w-[90%]', 'w-[70%]']

export function SkeletonLoader({ lines = 3, className }: SkeletonLoaderProps) {
  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={clsx('h-3 bg-friday-card-hover rounded animate-pulse', widths[i % widths.length])} />
      ))}
    </div>
  )
}
