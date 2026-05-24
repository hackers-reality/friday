import { useState, useEffect, useRef } from 'react'
import { useSystemStore } from '../../stores/useSystemStore'
import type { Agent } from '../../types'
import clsx from 'clsx'

interface Props {
  query: string
  onSelect: (agent: Agent) => void
  onClose: () => void
}

const statusDot: Record<string, string> = {
  idle: 'bg-neon-green',
  running: 'bg-neon-yellow',
  completed: 'bg-neon-cyan',
  failed: 'bg-neon-red',
  offline: 'bg-text-muted',
}

export function MentionDropdown({ query, onSelect, onClose }: Props) {
  const agents = useSystemStore((s) => s.agents)
  const [selected, setSelected] = useState(0)
  const ref = useRef<HTMLDivElement>(null)

  const filtered = agents.filter((a) => a.name.toLowerCase().includes(query.toLowerCase()))

  useEffect(() => { setSelected(0) }, [query])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); setSelected((s) => Math.min(s + 1, filtered.length - 1)) }
      else if (e.key === 'ArrowUp') { e.preventDefault(); setSelected((s) => Math.max(s - 1, 0)) }
      else if (e.key === 'Enter' && filtered[selected]) { e.preventDefault(); onSelect(filtered[selected]) }
      else if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [filtered, selected, onSelect, onClose])

  if (filtered.length === 0) return null

  return (
    <div ref={ref} className="absolute bottom-full left-0 mb-1 w-64 bg-friday-card border border-border-cyan rounded-lg shadow-xl max-h-48 overflow-y-auto z-40">
      {filtered.map((agent, i) => (
        <button
          key={agent.id}
          className={clsx(
            'w-full flex items-center gap-2 px-3 py-2 text-left transition-colors',
            i === selected ? 'bg-neon-cyan/10' : 'hover:bg-friday-card-hover',
          )}
          onClick={() => onSelect(agent)}
          onMouseEnter={() => setSelected(i)}
        >
          <span className={clsx('w-2 h-2 rounded-full shrink-0', statusDot[agent.status] ?? 'bg-text-muted')} />
          <span className="text-sm text-text-primary truncate">{agent.name}</span>
          <span className="text-[10px] font-mono text-text-dim ml-auto">{agent.model}</span>
        </button>
      ))}
    </div>
  )
}
