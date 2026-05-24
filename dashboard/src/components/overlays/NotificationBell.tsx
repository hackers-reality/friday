import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Bell, X, AlertTriangle, Info, AlertCircle } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useSystemStore } from '../../stores/useSystemStore'

const severityIcon = {
  info: <Info size={14} className="text-neon-cyan" />,
  warn: <AlertTriangle size={14} className="text-neon-yellow" />,
  error: <AlertCircle size={14} className="text-neon-red" />,
  critical: <AlertCircle size={14} className="text-neon-red" />,
}

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const alerts = useSystemStore((s) => s.alerts)
  const dismiss = useSystemStore((s) => s.dismissAlert)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const undismissed = alerts.filter((a) => !a.dismissed)

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen((v) => !v)} className="relative text-text-dim hover:text-neon-cyan transition-colors">
        <Bell size={16} />
        {undismissed.length > 0 && (
          <span className="absolute -top-1.5 -right-1.5 min-w-4 h-4 bg-neon-red text-white text-[10px] font-mono rounded-full flex items-center justify-center">
            {undismissed.length}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className="absolute right-0 top-full mt-2 w-80 bg-friday-card border border-border-cyan rounded-xl shadow-2xl z-50 overflow-hidden"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            <div className="px-3 py-2 border-b border-border-cyan flex items-center justify-between">
              <span className="text-xs font-display text-neon-cyan tracking-wider">Alerts</span>
              {undismissed.length > 0 && (
                <button
                  onClick={() => undismissed.forEach((a) => dismiss(a.id))}
                  className="text-[10px] text-text-dim hover:text-neon-cyan transition-colors"
                >
                  Clear All
                </button>
              )}
            </div>
            <div className="max-h-72 overflow-y-auto">
              {undismissed.length === 0 ? (
                <div className="text-sm text-text-dim text-center py-6">No alerts</div>
              ) : (
                undismissed.map((alert) => (
                  <div key={alert.id} className="flex items-start gap-2.5 px-3 py-2.5 border-b border-border-cyan/30 hover:bg-friday-card-hover transition-colors">
                    <span className="mt-0.5 shrink-0">{severityIcon[alert.severity]}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-text-primary truncate">{alert.message}</p>
                      <span className="text-[10px] text-text-muted font-mono">
                        {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                      </span>
                    </div>
                    <button onClick={() => dismiss(alert.id)} className="text-text-muted hover:text-text-primary shrink-0">
                      <X size={12} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
