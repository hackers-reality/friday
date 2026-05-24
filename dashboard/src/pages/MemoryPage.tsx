import { useState } from 'react'
import { NeonCard } from '../components/ui/NeonCard'
import { NeonBadge } from '../components/ui/NeonBadge'
import { NeonButton } from '../components/ui/NeonButton'
import { EmptyState } from '../components/ui/EmptyState'
import { Search, Trash2 } from 'lucide-react'
import type { MemoryChunk } from '../types'

export function MemoryPage() {
  const [query, setQuery] = useState('')
  const [chunks, setChunks] = useState<MemoryChunk[]>([])
  const [loading, setLoading] = useState(false)

  const searchMemory = async () => {
    if (!query.trim()) return
    setLoading(true)
    try {
      const r = await fetch(`/api/memory/search?q=${encodeURIComponent(query)}`)
      const data = (await r.json()) as MemoryChunk[]
      setChunks(data)
    } catch { setChunks([]) }
    setLoading(false)
  }

  const deleteChunk = async (id: string) => {
    try {
      await fetch(`/api/memory/${id}`, { method: 'DELETE' })
      setChunks((c) => c.filter((x) => x.id !== id))
    } catch { /* offline */ }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">Memory Store</h2>

      {/* Search */}
      <div className="flex gap-2">
        <div className="flex-1 flex items-center gap-2 bg-friday-card border border-border-cyan rounded-lg px-3">
          <Search size={14} className="text-text-dim" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchMemory()}
            placeholder="Search memories..."
            className="flex-1 bg-transparent py-2 text-sm text-text-primary placeholder:text-text-muted outline-none"
          />
        </div>
        <NeonButton variant="primary" size="sm" onClick={searchMemory} disabled={loading}>
          {loading ? '...' : 'Search'}
        </NeonButton>
      </div>

      {/* Results */}
      {chunks.length === 0 ? (
        <EmptyState icon="🧠" title="Memory Vault" description="Search your vector memory store" />
      ) : (
        <div className="space-y-2">
          {chunks.map((chunk) => (
            <NeonCard key={chunk.id} padding="p-3">
              <p className="text-sm text-text-primary mb-2 line-clamp-3">{chunk.content}</p>
              <div className="flex items-center gap-2 flex-wrap">
                <NeonBadge color="cyan" size="sm">{chunk.category}</NeonBadge>
                <span className="text-[10px] text-text-muted font-mono">{chunk.source}</span>
                {chunk.distance !== undefined && (
                  <span className="text-[10px] text-text-dim font-mono ml-auto">{(1 - chunk.distance).toFixed(2)} relevance</span>
                )}
                <button onClick={() => deleteChunk(chunk.id)} className="text-text-muted hover:text-neon-red transition-colors ml-1">
                  <Trash2 size={12} />
                </button>
              </div>
            </NeonCard>
          ))}
        </div>
      )}
    </div>
  )
}
