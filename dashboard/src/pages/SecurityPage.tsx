import { useState, useEffect } from 'react'
import { NeonCard } from '../components/ui/NeonCard'
import { NeonBadge } from '../components/ui/NeonBadge'
import { NeonButton } from '../components/ui/NeonButton'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { Shield, Plus, Trash2, Key } from 'lucide-react'
import type { SidecarToken, AuditEntry } from '../types'

export function SecurityPage() {
  const [tokens, setTokens] = useState<SidecarToken[]>([])
  const [audit, setAudit] = useState<AuditEntry[]>([])
  const [revoking, setRevoking] = useState<string | null>(null)
  const [showGen, setShowGen] = useState(false)
  const [newDevice, setNewDevice] = useState('')

  useEffect(() => {
    fetch('/api/security/tokens').then((r) => r.json()).then(setTokens).catch(() => {})
    fetch('/api/security/audit').then((r) => r.json()).then(setAudit).catch(() => {})
  }, [])

  const revoke = async (prefix: string) => {
    await fetch(`/api/security/tokens/${prefix}`, { method: 'DELETE' }).catch(() => {})
    setTokens((t) => t.filter((x) => x.token_prefix !== prefix))
    setRevoking(null)
  }

  const sevColor: Record<string, 'cyan' | 'yellow' | 'red'> = { info: 'cyan', warn: 'yellow', error: 'red', critical: 'red' }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <Shield size={20} className="text-neon-cyan" />
        <h1 className="text-lg font-display text-neon-cyan tracking-wider">Security Center</h1>
      </div>

      {/* API Tokens */}
      <NeonCard>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-display text-text-primary tracking-wider">Sidecar Tokens</h2>
          <NeonButton variant="primary" size="sm" icon={<Plus size={14} />} onClick={() => setShowGen(!showGen)}>Generate</NeonButton>
        </div>

        {showGen && (
          <div className="flex gap-2 mb-4">
            <input value={newDevice} onChange={(e) => setNewDevice(e.target.value)} placeholder="Device name" className="flex-1 bg-friday-input border border-border-cyan rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none" />
            <NeonButton variant="primary" size="sm" icon={<Key size={14} />}>Generate</NeonButton>
          </div>
        )}

        {tokens.length === 0 ? (
          <p className="text-sm text-text-dim">No tokens issued</p>
        ) : (
          <div className="space-y-2">
            {tokens.map((tok) => (
              <div key={tok.token_prefix} className="flex items-center justify-between bg-friday-bg-deep rounded-lg px-3 py-2">
                <div>
                  <span className="text-sm text-text-primary">{tok.device_name}</span>
                  <span className="text-xs font-mono text-text-dim ml-2">{tok.token_prefix}****</span>
                </div>
                <div className="flex items-center gap-2">
                  {tok.capabilities.map((c) => <NeonBadge key={c} color="purple" size="sm">{c}</NeonBadge>)}
                  <button onClick={() => setRevoking(tok.token_prefix)} className="text-text-muted hover:text-neon-red transition-colors">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </NeonCard>

      {/* Audit Log */}
      <NeonCard>
        <h2 className="text-sm font-display text-text-primary tracking-wider mb-3">Audit Log</h2>
        {audit.length === 0 ? (
          <p className="text-sm text-text-dim">No audit entries</p>
        ) : (
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {audit.map((entry) => (
              <div key={entry.id} className="flex items-center gap-3 text-xs py-1.5 border-b border-border-cyan/30">
                <span className="font-mono text-text-muted w-36 shrink-0">{new Date(entry.timestamp).toLocaleString()}</span>
                <NeonBadge color={sevColor[entry.severity] ?? 'cyan'} size="sm">{entry.severity}</NeonBadge>
                <span className="text-text-secondary truncate">{entry.action}</span>
                <span className="text-text-dim ml-auto shrink-0">{entry.source}</span>
              </div>
            ))}
          </div>
        )}
      </NeonCard>

      <ConfirmDialog
        isOpen={revoking !== null}
        onClose={() => setRevoking(null)}
        onConfirm={() => revoking && revoke(revoking)}
        title="Revoke Token"
        message="This will permanently revoke this sidecar token. The device will lose access."
        confirmText="Revoke"
        variant="danger"
      />
    </div>
  )
}
