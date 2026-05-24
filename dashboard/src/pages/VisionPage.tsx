import { useState } from 'react'
import { NeonButton } from '../components/ui/NeonButton'
import { NeonCard } from '../components/ui/NeonCard'
import { StatCard } from '../components/ui/StatCard'
import { ProgressBar } from '../components/ui/ProgressBar'
import { Eye, Camera } from 'lucide-react'
import type { CameraSnapshot, CVLabel } from '../types'

export function VisionPage() {
  const [snapshot, setSnapshot] = useState<CameraSnapshot | null>(null)
  const [query, setQuery] = useState('')

  const grabFrame = async () => {
    try {
      const r = await fetch('/api/camera/snapshot')
      const data = (await r.json()) as CameraSnapshot
      setSnapshot(data)
    } catch { /* offline */ }
  }

  const askScene = async () => {
    if (!query.trim()) return
    try {
      await fetch('/api/vision/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query }) })
    } catch { /* offline */ }
  }

  const faces = snapshot?.cv_labels.filter((l) => l.type === 'face').length ?? 0
  const hands = snapshot?.cv_labels.filter((l) => l.type === 'hand').length ?? 0
  const objects = snapshot?.cv_labels.filter((l) => l.type === 'object').length ?? 0

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">Vision</h2>

      {/* Camera Feed */}
      <NeonCard className="relative overflow-hidden">
        {snapshot ? (
          <img src={`data:image/jpeg;base64,${snapshot.image_base64}`} alt="Camera" className="w-full rounded-lg" />
        ) : (
          <div className="flex items-center justify-center h-40 opacity-50">
            <Eye size={32} className="text-text-dim" />
          </div>
        )}
      </NeonCard>

      <div className="flex gap-2">
        <NeonButton variant="primary" size="sm" icon={<Camera size={14} />} onClick={grabFrame}>Grab Frame</NeonButton>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && askScene()}
          placeholder="Ask about the scene..."
          className="flex-1 bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted outline-none"
        />
      </div>

      {/* Detection counters */}
      <div className="grid grid-cols-3 gap-2">
        <StatCard label="Faces" value={faces} color="#00f5ff" />
        <StatCard label="Hands" value={hands} color="#b400ff" />
        <StatCard label="Objects" value={objects} color="#00ff88" />
      </div>

      {/* CV labels */}
      {snapshot && snapshot.cv_labels.length > 0 && (
        <NeonCard>
          <h3 className="text-xs text-text-dim uppercase tracking-wider mb-2">Detections</h3>
          <div className="space-y-2">
            {snapshot.cv_labels.map((lbl: CVLabel, i: number) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-xs text-text-primary w-24 truncate">{lbl.label}</span>
                <ProgressBar value={lbl.confidence * 100} color="cyan" />
              </div>
            ))}
          </div>
        </NeonCard>
      )}
    </div>
  )
}
