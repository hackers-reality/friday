import { useState } from 'react'
import { NeonButton } from '../components/ui/NeonButton'
import { NeonCard } from '../components/ui/NeonCard'
import { StatCard } from '../components/ui/StatCard'
import { Search, Radar } from 'lucide-react'

export function OSINTPage() {
  const [target, setTarget] = useState('')
  const [targetType, setTargetType] = useState('username')

  const handleScan = () => {
    if (!target.trim()) return
    fetch('/api/osint/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, target_type: targetType, tools: ['sherlock', 'spiderfoot'] }),
    }).catch(() => {})
  }

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">OSINT Scanner</h2>

      {/* Controls */}
      <NeonCard>
        <div className="space-y-3">
          <input
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            placeholder="Enter target..."
            className="w-full bg-friday-input border border-border-cyan rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-neon-cyan/40"
          />
          <div className="flex gap-2">
            <select
              value={targetType}
              onChange={(e) => setTargetType(e.target.value)}
              className="bg-friday-input border border-border-cyan rounded-lg px-3 py-2 text-sm text-text-primary outline-none"
            >
              {['username', 'email', 'ip', 'domain', 'image'].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <NeonButton variant="primary" size="sm" icon={<Radar size={14} />} onClick={handleScan}>
              Launch Scan
            </NeonButton>
          </div>
        </div>
      </NeonCard>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        <StatCard label="Entities" value={0} icon={<Search size={14} />} />
        <StatCard label="Links" value={0} />
        <StatCard label="Threats" value={0} color="#ff003c" />
      </div>

      {/* Graph placeholder */}
      <NeonCard className="min-h-48 flex items-center justify-center">
        <div className="text-center opacity-50">
          <span className="text-3xl block mb-2">🕸️</span>
          <p className="text-xs text-text-dim">Knowledge Graph will appear here after scan</p>
        </div>
      </NeonCard>
    </div>
  )
}
