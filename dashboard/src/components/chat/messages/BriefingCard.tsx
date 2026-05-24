import { useState } from 'react'
import { ChevronDown, ChevronUp, Play } from 'lucide-react'
import type { BriefingMessage } from '../../../types'

interface Props { message: BriefingMessage }

export function BriefingCard({ message }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set([0]))

  const toggle = (i: number) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  return (
    <div className="bg-gradient-to-r from-friday-card to-neon-purple/5 border-l-4 border-neon-purple rounded-xl p-4">
      <div className="flex items-center gap-3 mb-3">
        <button className="w-7 h-7 rounded-full bg-neon-purple/20 text-neon-purple flex items-center justify-center hover:bg-neon-purple/30 transition-colors">
          <Play size={12} />
        </button>
        <h4 className="font-display text-neon-purple tracking-wider text-sm">Morning Briefing</h4>
        <span className="text-[10px] font-mono text-text-dim bg-friday-bg-deep px-2 py-0.5 rounded ml-auto">
          {message.date}
        </span>
      </div>

      <div className="space-y-1">
        {message.sections.map((sec, i) => (
          <div key={i} className="border border-border-cyan/30 rounded-lg overflow-hidden">
            <button
              onClick={() => toggle(i)}
              className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-friday-card-hover transition-colors"
            >
              <span className="text-xs font-semibold text-neon-cyan">{sec.title}</span>
              {expanded.has(i) ? <ChevronUp size={12} className="text-text-dim" /> : <ChevronDown size={12} className="text-text-dim" />}
            </button>
            {expanded.has(i) && (
              <div className="px-3 pb-2 text-xs text-text-secondary">
                {sec.content}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
