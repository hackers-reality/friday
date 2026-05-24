import { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, MessageSquare, Mic, Bot, Eye, Brain, Shield, ScrollText, Settings, Globe, Youtube, BarChart3, Monitor, Calendar, Terminal, Package, ClipboardList } from 'lucide-react'

const PAGES = [
  { icon: MessageSquare, label: 'Chat', path: '/' },
  { icon: Mic, label: 'Voice', path: '/voice' },
  { icon: ClipboardList, label: 'Tasks', path: '/tasks' },
  { icon: Bot, label: 'Agents', path: '/agents' },
  { icon: Search, label: 'OSINT', path: '/osint' },
  { icon: Globe, label: 'Browser', path: '/browser' },
  { icon: Eye, label: 'Vision', path: '/vision' },
  { icon: Brain, label: 'Memory', path: '/memory' },
  { icon: Youtube, label: 'YouTube', path: '/youtube' },
  { icon: Package, label: 'Takeout', path: '/takeout' },
  { icon: BarChart3, label: 'Analytics', path: '/analytics' },
  { icon: Monitor, label: 'Devices', path: '/devices' },
  { icon: Calendar, label: 'Scheduler', path: '/scheduler' },
  { icon: Terminal, label: 'PyRunner', path: '/pyrunner' },
  { icon: Shield, label: 'Security', path: '/security' },
  { icon: ScrollText, label: 'Logs', path: '/logs' },
  { icon: Settings, label: 'Settings', path: '/settings' },
]

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  const filtered = PAGES.filter((p) => p.label.toLowerCase().includes(query.toLowerCase()))

  const close = useCallback(() => { setOpen(false); setQuery(''); setSelected(0) }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setOpen((v) => !v)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50)
  }, [open])

  const execute = (index: number) => {
    const item = filtered[index]
    if (item) { navigate(item.path); close() }
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelected((s) => Math.min(s + 1, filtered.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSelected((s) => Math.max(s - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); execute(selected) }
    else if (e.key === 'Escape') close()
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={close} />
          <motion.div
            className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-md z-50 bg-friday-card border border-border-cyan rounded-2xl shadow-2xl overflow-hidden"
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border-cyan">
              <Search size={16} className="text-text-dim shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => { setQuery(e.target.value); setSelected(0) }}
                onKeyDown={handleKey}
                placeholder="Search pages..."
                className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none"
              />
              <kbd className="text-[10px] font-mono text-text-muted bg-friday-bg-deep px-1.5 py-0.5 rounded">ESC</kbd>
            </div>
            <div className="max-h-64 overflow-y-auto py-1">
              {filtered.length === 0 && (
                <div className="text-sm text-text-dim text-center py-4">No results</div>
              )}
              {filtered.map((item, i) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.path}
                    className={`w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors ${i === selected ? 'bg-neon-cyan/10 text-neon-cyan' : 'text-text-secondary hover:bg-friday-card-hover'}`}
                    onClick={() => execute(i)}
                    onMouseEnter={() => setSelected(i)}
                  >
                    <Icon size={16} />
                    <span>{item.label}</span>
                  </button>
                )
              })}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
