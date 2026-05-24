import { useState, useEffect } from 'react'
import { NeonCard } from '../components/ui/NeonCard'
import { NeonBadge } from '../components/ui/NeonBadge'
import { NeonButton } from '../components/ui/NeonButton'
import { Play, Save, Trash2, Plus, Code } from 'lucide-react'
import type { PyRunnerScript } from '../types'

export function PyRunnerPage() {
  const [scripts, setScripts] = useState<PyRunnerScript[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/pyrunner/scripts').then((r) => r.json()).then(setScripts).catch(() => {})
  }, [])

  const selected = scripts.find((s) => s.id === selectedId)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-display text-neon-cyan tracking-wider">PyRunner</h2>
        <NeonButton variant="primary" size="sm" icon={<Plus size={14} />}>New Script</NeonButton>
      </div>

      <div className="flex gap-3" style={{ minHeight: 300 }}>
        {/* Script list */}
        <div className="w-48 shrink-0 space-y-1">
          {scripts.length === 0 ? (
            <div className="text-xs text-text-dim text-center py-4">No scripts</div>
          ) : (
            scripts.map((s) => (
              <button
                key={s.id}
                onClick={() => setSelectedId(s.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors ${
                  s.id === selectedId ? 'bg-friday-card text-neon-cyan border border-border-cyan' : 'text-text-secondary hover:bg-friday-card-hover'
                }`}
              >
                <div className="font-medium truncate">{s.name}</div>
                {s.last_status && (
                  <NeonBadge color={s.last_status === 'success' ? 'green' : 'red'} size="sm">{s.last_status}</NeonBadge>
                )}
              </button>
            ))
          )}
        </div>

        {/* Editor area */}
        <NeonCard className="flex-1 flex flex-col">
          {selected ? (
            <>
              <div className="flex items-center gap-2 mb-2">
                <Code size={14} className="text-neon-cyan" />
                <span className="text-sm text-text-primary font-mono">{selected.name}</span>
                <div className="flex gap-1 ml-auto">
                  <NeonButton size="sm" icon={<Play size={12} />}>Run</NeonButton>
                  <NeonButton size="sm" icon={<Save size={12} />}>Save</NeonButton>
                </div>
              </div>
              <div className="flex-1 bg-friday-bg-deep rounded-lg p-4 font-mono text-sm text-text-secondary overflow-auto">
                <pre>{selected.code}</pre>
              </div>
              {selected.packages.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {selected.packages.map((p) => (
                    <NeonBadge key={p} color="purple" size="sm">{p}</NeonBadge>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center opacity-50">
              <div className="text-center">
                <Code size={32} className="text-text-dim mx-auto mb-2" />
                <p className="text-xs text-text-dim">Select a script or create a new one</p>
              </div>
            </div>
          )}
        </NeonCard>
      </div>
    </div>
  )
}
