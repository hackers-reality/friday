import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Play, X } from 'lucide-react'
import type { BriefingData } from '../../types'
import { NeonButton } from '../ui/NeonButton'

interface Props { data: BriefingData | null; onDismiss: () => void }

export function BriefingOverlay({ data, onDismiss }: Props) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set([0]))
  const [countdown, setCountdown] = useState(30)

  useEffect(() => {
    if (!data) return
    setCountdown(30)
    const id = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) { onDismiss(); return 0 }
        return c - 1
      })
    }, 1000)
    return () => clearInterval(id)
  }, [data, onDismiss])

  const toggle = (i: number) => {
    setExpanded((prev) => { const n = new Set(prev); n.has(i) ? n.delete(i) : n.add(i); return n })
  }

  return (
    <AnimatePresence>
      {data && (
        <>
          <motion.div className="fixed inset-0 bg-friday-bg-deep/80 backdrop-blur z-50" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onDismiss} />
          <motion.div
            className="fixed top-0 left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 mt-8"
            initial={{ opacity: 0, y: -100 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -100 }}
          >
            <div className="bg-friday-card border border-border-purple rounded-2xl p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <button className="w-8 h-8 rounded-full bg-neon-purple/20 text-neon-purple flex items-center justify-center">
                    <Play size={14} />
                  </button>
                  <h2 className="font-display text-neon-purple tracking-wider">Morning Briefing</h2>
                  <span className="text-xs font-mono text-text-dim bg-friday-bg-deep px-2 py-0.5 rounded">{data.date}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-text-muted">{countdown}s</span>
                  <button onClick={onDismiss} className="text-text-dim hover:text-text-primary"><X size={16} /></button>
                </div>
              </div>
              <div className="space-y-2 mb-4">
                {data.sections.map((sec, i) => (
                  <div key={i} className="border border-border-cyan/30 rounded-lg overflow-hidden">
                    <button onClick={() => toggle(i)} className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-friday-card-hover">
                      <span className="text-sm font-semibold text-neon-cyan">{sec.title}</span>
                      {expanded.has(i) ? <ChevronUp size={14} className="text-text-dim" /> : <ChevronDown size={14} className="text-text-dim" />}
                    </button>
                    {expanded.has(i) && <div className="px-3 pb-3 text-sm text-text-secondary">{sec.content}</div>}
                  </div>
                ))}
              </div>
              <div className="flex justify-end gap-2">
                <NeonButton variant="secondary" size="sm" onClick={onDismiss}>Dismiss</NeonButton>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
