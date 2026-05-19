import { useState, useEffect } from 'react'
import { getMemoryStatus, type MemoryStatus } from '../api'

export default function MemoryPanel() {
  const [memory, setMemory] = useState<MemoryStatus | null>(null)
  const [status, setStatus] = useState('')

  useEffect(() => {
    const fetchMemory = async () => {
      try {
        const m = await getMemoryStatus()
        setMemory(m)
        setStatus('')
      } catch {
        setStatus('Unable to load memory data')
      }
    }
    fetchMemory()
    const interval = setInterval(fetchMemory, 5000)
    return () => clearInterval(interval)
  }, [])

  if (status && !memory) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-text-muted">{status}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
          <div className="text-xs text-text-muted mb-1">Profile</div>
          <div className="text-lg font-bold text-cyan-glow">{memory?.name ?? '--'}</div>
          <div className="text-xs text-text-muted">v{memory?.version ?? '--'}</div>
        </div>
        <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
          <div className="text-xs text-text-muted mb-1">Conversations Audited</div>
          <div className="text-lg font-bold text-cyan-glow">{memory?.conversations_audited?.toLocaleString() ?? '0'}</div>
        </div>
        <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
          <div className="text-xs text-text-muted mb-1">Last Updated</div>
          <div className="text-lg font-bold text-cyan-glow text-sm">
            {memory?.last_updated ? new Date(memory.last_updated).toLocaleDateString() : '--'}
          </div>
        </div>
      </div>

      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-cyan-glow mb-4">Memory Categories</h3>
        <div className="space-y-3">
          {(memory?.categories ?? []).map((cat) => (
            <div key={cat.name} className="flex items-center gap-3">
              <span className="text-sm text-text-primary w-32">{cat.name}</span>
              <div className="flex-1 bg-[#1a1a3a] rounded-full h-2 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(100, cat.confidence * 100)}%`,
                    background: cat.confidence > 0.7
                      ? 'linear-gradient(90deg, #22c55e, #00d4ff)'
                      : cat.confidence > 0.4
                      ? 'linear-gradient(90deg, #f59e0b, #00d4ff)'
                      : 'linear-gradient(90deg, #ef4444, #f59e0b)',
                    boxShadow: '0 0 10px rgba(0,212,255,0.3)',
                  }}
                />
              </div>
              <span className="text-xs text-text-muted w-12 text-right">
                {Math.round(cat.confidence * 100)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-cyan-glow mb-3">Knowledge Graph</h3>
        <div className="flex items-center justify-center h-48 border border-dashed border-cyan-muted/20 rounded-lg">
          <div className="text-center">
            <div className="text-3xl mb-2">🕸️</div>
            <p className="text-sm text-text-muted">3D Graph Visualization</p>
            <p className="text-xs text-text-muted mt-1">Connect to FRIDAY to render knowledge graph</p>
          </div>
        </div>
      </div>
    </div>
  )
}
