import { useState, useEffect, useRef } from 'react'
import { useSystemStore } from '../stores/useSystemStore'
import { NeonButton } from '../components/ui/NeonButton'
import { NeonBadge } from '../components/ui/NeonBadge'
import { ScrollText, Download, ArrowDown } from 'lucide-react'
import clsx from 'clsx'

const levelColor: Record<string, string> = {
  DEBUG: 'text-text-dim',
  INFO: 'text-neon-cyan',
  WARN: 'text-neon-yellow',
  ERROR: 'text-neon-red',
}

export function LogsPage() {
  const logs = useSystemStore((s) => s.logs)
  const [levelFilter, setLevelFilter] = useState('ALL')
  const [moduleFilter, setModuleFilter] = useState('')
  const [searchFilter, setSearchFilter] = useState('')
  const [autoScroll, setAutoScroll] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  const filtered = logs.filter((log) => {
    if (levelFilter !== 'ALL' && log.level !== levelFilter) return false
    if (moduleFilter && !log.module.toLowerCase().includes(moduleFilter.toLowerCase())) return false
    if (searchFilter && !log.message.toLowerCase().includes(searchFilter.toLowerCase())) return false
    return true
  })

  useEffect(() => {
    if (autoScroll) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [filtered.length, autoScroll])

  const downloadLogs = () => {
    const text = filtered.map((l) => `[${l.timestamp}] [${l.level}] [${l.module}] ${l.message}`).join('\n')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'friday-logs.txt'; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="h-full flex flex-col p-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-4">
        <ScrollText size={20} className="text-neon-cyan" />
        <h1 className="text-lg font-display text-neon-cyan tracking-wider">System Logs</h1>
        <NeonBadge color="cyan" size="sm">{filtered.length}</NeonBadge>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-3 flex-wrap">
        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-xs text-text-primary outline-none"
        >
          {['ALL', 'DEBUG', 'INFO', 'WARN', 'ERROR'].map((l) => <option key={l}>{l}</option>)}
        </select>
        <input
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
          placeholder="Module..."
          className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-xs text-text-primary placeholder:text-text-muted outline-none w-28"
        />
        <input
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
          placeholder="Search..."
          className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-xs text-text-primary placeholder:text-text-muted outline-none flex-1"
        />
        <NeonButton size="sm" onClick={() => setAutoScroll(!autoScroll)} icon={<ArrowDown size={12} />}>
          {autoScroll ? 'Auto' : 'Manual'}
        </NeonButton>
        <NeonButton size="sm" onClick={downloadLogs} icon={<Download size={12} />}>Download</NeonButton>
      </div>

      {/* Log display */}
      <div className="flex-1 bg-friday-bg-deep border border-border-cyan rounded-xl p-3 overflow-y-auto font-mono text-xs leading-relaxed">
        {filtered.length === 0 ? (
          <div className="text-text-dim text-center py-8">No logs matching filters</div>
        ) : (
          filtered.map((log, i) => (
            <div key={i} className={clsx('py-0.5', levelColor[log.level])}>
              <span className="text-text-muted">[{new Date(log.timestamp).toLocaleTimeString()}]</span>{' '}
              <span className={levelColor[log.level]}>[{log.level}]</span>{' '}
              <span className="text-text-dim">[{log.module}]</span>{' '}
              {log.message}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
